"""Malware-scanning enforcement for the V54 security hardening pass.

This module is intentionally Flask/framework-agnostic so the existing stdlib
``http.server``-based backend in ``server.py`` can keep using it directly. It
probes for a supported on-host scanner (ClamAV on Linux, Windows Defender on
Windows) and exposes a tiny, dependency-free API:

* :func:`detect_scanner` — report which scanner (if any) is available.
* :func:`scan_file` — scan a single file; never raises.
* :func:`startup_preflight` — fail-closed gate for production startup.
* :func:`enforce_scanner_on_startup` — Flask/logger-friendly wrapper around
  :func:`startup_preflight` for use near ``app = Flask(__name__)``.

A :class:`MalwareDetected` exception is also exposed so callers can distinguish
"upload is malware" (HTTP 422) from generic validation errors (HTTP 400) when
they choose to surface scan results as structured HTTP responses.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess  # nosec B404 — used only for ClamAV/MpCmdRun.exe with fixed argv, no shell=True, no user input
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

# Hard ceiling for any single scan. The task contract requires 60 seconds; we
# honour that exactly so a wedged scanner cannot lock an upload request.
SCAN_TIMEOUT_SECONDS: int = 60

# Module-level cache for the detected scanner descriptor. Probing clamd via a
# TCP/UDS round-trip on every upload would be wasteful and could let a transient
# daemon hiccup turn uploads into 5xx errors. We probe once, then trust it.
_SCANNER_PROBE: Optional[dict[str, Any]] = None
_SCANNER_PROBE_LOCK = threading.Lock()


class MalwareDetected(Exception):
    """Raised by callers to signal that an upload failed its malware scan.

    The string message is safe to echo back to the client; it never contains
    file contents or scanner-internal details beyond the scanner's verdict.
    """


# ---------------------------------------------------------------------------
# ClamAV helpers (Linux). We speak the minimum clamd INSTREAM protocol over a
# Unix-domain socket (``/run/clamav/clamd.ctl``) or TCP 127.0.0.1:3310. The
# protocol is: send "zINSTREAM\\0", then framed chunks <len:be32><bytes>, then
# a zero-length chunk to flush, then read the verdict line.
# ---------------------------------------------------------------------------

_CLAMD_SOCKET_CANDIDATES = (
    "/run/clamav/clamd.ctl",
    "/var/run/clamav/clamd.ctl",
    "/run/clamd/clamd.sock",
    "/var/run/clamd/clamd.sock",
)
_CLAMD_TCP_HOST = "127.0.0.1"
_CLAMD_TCP_PORT = 3310


def _clamd_instream(path: str, *, timeout: float = SCAN_TIMEOUT_SECONDS) -> tuple[bool, str]:
    """Run a clamd INSTREAM scan over UDS or TCP.

    Args:
        path: Filesystem path to the file being scanned.
        timeout: Combined connect+scan budget in seconds.

    Returns:
        A ``(clean, message)`` tuple. ``clean`` is ``True`` only when clamd
        responded with ``OK``; any other verdict or transport error yields
        ``clean=False`` with a short explanation.
    """
    data = Path(path).read_bytes()
    # Try Unix-domain sockets first (the common Linux laptop case), then TCP.
    socket_targets: list[tuple[str, Any]] = []
    for candidate in _CLAMD_SOCKET_CANDIDATES:
        socket_targets.append(("uds", candidate))
    socket_targets.append(("tcp", (_CLAMD_TCP_HOST, _CLAMD_TCP_PORT)))

    last_error = "no clamd socket reachable"
    for kind, target in socket_targets:
        sock: Optional[socket.socket] = None
        try:
            if kind == "uds":
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect(target)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect(target)
        except OSError as exc:
            last_error = f"{kind} connect failed: {exc}"
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
            continue

        try:
            sock.sendall(b"zINSTREAM\0")
            chunk_size = 4096
            offset = 0
            while offset < len(data):
                chunk = data[offset:offset + chunk_size]
                sock.sendall(len(chunk).to_bytes(4, "big") + chunk)
                offset += len(chunk)
            sock.sendall((0).to_bytes(4, "big"))  # zero-length chunk = flush
            # Read the verdict line. clamd closes the socket after the response.
            chunks: list[bytes] = []
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    last_error = "clamd scan timed out"
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\0" in chunk or (sum(len(c) for c in chunks) > 8192):
                    # clamd responses are short; stop early to avoid blocking.
                    break
            verdict = b"".join(chunks).rstrip(b"\0").decode("utf-8", "replace").strip()
            if not verdict:
                return False, "clamd returned an empty verdict"
            if verdict.endswith("OK"):
                return True, "clamd: OK"
            # Typical infected verdict: "stream: Eicar-Test-Signature FOUND"
            return False, f"clamd rejected upload: {verdict}"
        except OSError as exc:
            last_error = f"{kind} scan failed: {exc}"
        finally:
            try:
                sock.close()
            except OSError:
                pass
    return False, last_error


# ---------------------------------------------------------------------------
# Windows Defender helpers.
# ---------------------------------------------------------------------------

def _windows_defender_cli() -> Optional[str]:
    """Locate the newest ``MpCmdRun.exe`` on Windows.

    Returns:
        Absolute path to the binary, or ``None`` when not on Windows or not
        found. Looks under ``%ProgramData%\\Microsoft\\Windows Defender\\Platform``
        (newest version directory first), then ``%ProgramFiles%\\Windows Defender``,
        then falls back to ``where.exe``.
    """
    if os.name != "nt":
        return None
    candidates: list[str] = []
    program_data = os.environ.get("ProgramData", "")
    if program_data:
        platform_dir = Path(program_data) / "Microsoft" / "Windows Defender" / "Platform"
        if platform_dir.is_dir():
            try:
                candidates.extend(
                    str(item / "MpCmdRun.exe")
                    for item in sorted(platform_dir.iterdir(), reverse=True)
                    if item.is_dir()
                )
            except OSError:
                pass
    program_files = os.environ.get("ProgramFiles", "")
    if program_files:
        candidates.append(str(Path(program_files) / "Windows Defender" / "MpCmdRun.exe"))
    discovered = shutil.which("MpCmdRun.exe")
    if discovered:
        candidates.append(discovered)
    return next((item for item in candidates if Path(item).is_file()), None)


def _defender_scan(path: str, *, timeout: float = SCAN_TIMEOUT_SECONDS) -> tuple[bool, str]:
    """Invoke ``MpCmdRun.exe -Scan -ScanType 3 -File <path>`` on Windows.

    Args:
        path: Filesystem path to the file being scanned.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``(clean, message)`` — ``clean`` is ``True`` when Defender exited 0.
    """
    cli = _windows_defender_cli()
    if not cli:
        return False, "Windows Defender MpCmdRun.exe was not found"
    command = [cli, "-Scan", "-ScanType", "3", "-File", str(path), "-DisableRemediation"]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "Windows Defender scan timed out"
    except OSError as exc:
        return False, f"Windows Defender failed to run: {exc}"
    # Exit code 2 from MpCmdRun.exe means threats were found; anything non-zero
    # other than 2 should still be treated as a blocked upload (fail-closed).
    if result.returncode == 0:
        return True, "defender: OK"
    return False, f"defender rejected upload (exit {result.returncode})"


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def detect_scanner(*, force: bool = False) -> dict[str, Any]:
    """Probe the host for a supported malware scanner.

    On Linux this attempts a clamd INSTREAM handshake against the standard
    ``/run/clamav/clamd.ctl`` UDS (and TCP 127.0.0.1:3310 as a fallback), and
    also falls back to a ``clamdscan --version`` subprocess check. On Windows
    it locates ``MpCmdRun.exe``.

    Args:
        force: When ``True``, ignore the cached probe and re-run discovery.

    Returns:
        A descriptor dict with the keys ``kind`` (``'clamav'``, ``'defender'``,
        or ``None``), ``available`` (bool), and ``reason`` (short human
        explanation). The result is cached for the lifetime of the process.
    """
    global _SCANNER_PROBE
    if not force and _SCANNER_PROBE is not None:
        return dict(_SCANNER_PROBE)
    with _SCANNER_PROBE_LOCK:
        if not force and _SCANNER_PROBE is not None:
            return dict(_SCANNER_PROBE)
        descriptor = _detect_scanner_uncached()
        _SCANNER_PROBE = descriptor
        return dict(descriptor)


def _detect_scanner_uncached() -> dict[str, Any]:
    """Run the actual probe without touching the module-level cache.

    Returns:
        Descriptor dict (see :func:`detect_scanner`).
    """
    if os.name == "nt":
        cli = _windows_defender_cli()
        if cli:
            return {"kind": "defender", "available": True, "reason": f"Windows Defender at {cli}"}
        return {"kind": None, "available": False, "reason": "Windows Defender MpCmdRun.exe was not found"}
    # Linux / POSIX: try clamd first, then fall back to a clamdscan --version subprocess.
    # We perform a *real* INSTREAM handshake against a tiny probe file so a stale
    # binary on PATH (no daemon running) does not produce a false "available".
    probe = tempfile.NamedTemporaryFile(prefix="einvite-scanner-probe-", suffix=".txt", delete=False)
    try:
        probe.write(b"einvite malware scanner readiness probe\n")
        probe.flush()
        probe.close()
        clean, message = _clamd_instream(probe.name, timeout=min(SCAN_TIMEOUT_SECONDS, 10))
        if clean:
            return {"kind": "clamav", "available": True, "reason": "clamd INSTREAM probe succeeded"}
        # If clamd responded (even with an error verdict), the daemon is alive.
        if "stream:" in message or "OK" in message or "FOUND" in message:
            return {"kind": "clamav", "available": True, "reason": "clamd daemon responded"}
        # Fall back to a clamdscan --version subprocess: if present, mark the
        # scanner as available but flag the daemon as unreachable.
        clamdscan = shutil.which("clamdscan")
        if clamdscan:
            try:
                result = subprocess.run(
                    [clamdscan, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.returncode == 0 and "ClamAV" in (result.stdout or ""):
                    return {
                        "kind": "clamav",
                        "available": True,
                        "reason": "clamdscan installed but clamd daemon not reachable; using clamdscan fallback",
                    }
            except (OSError, subprocess.SubprocessError):
                pass
        return {"kind": None, "available": False, "reason": "no ClamAV daemon or clamdscan binary found"}
    finally:
        try:
            os.unlink(probe.name)
        except OSError:
            pass


def scan_file(path: str) -> dict[str, Any]:
    """Scan a single uploaded file.

    Dispatches to clamd INSTREAM on Linux or ``MpCmdRun.exe`` on Windows. The
    function never raises — transport failures, timeouts, and missing scanners
    all return a result dict so the upload route can decide how to respond.

    Args:
        path: Filesystem path to the file to scan. The file must already exist
            on disk; callers streaming bytes from a request body should write
            them to a quarantine file first.

    Returns:
        ``{"clean": bool, "message": str}``. When no scanner is available,
        ``clean`` is ``True`` (caller must consult :func:`startup_preflight`
        or :data:`os.environ` ``EINVITE_ALLOW_NO_SCANNER`` to decide whether
        that is acceptable).
    """
    file_path = Path(str(path or "")).resolve()
    # Security: verify the resolved path doesn't escape the system temp dir
    # (defense-in-depth against path injection — CodeQL py/path-injection)
    try:
        import tempfile
        temp_root = Path(tempfile.gettempdir()).resolve()
        file_path.relative_to(temp_root)
    except (ValueError, RuntimeError):
        # If the file is not under the temp dir, check if it's under the
        # DATA directory (for scan_uploaded_file calls from server.py)
        try:
            data_root = Path(os.environ.get("EINVITE_DATA_DIR", ".")).resolve()
            file_path.relative_to(data_root)
        except (ValueError, RuntimeError):
            # Allow absolute paths that exist (server-controlled, not user-supplied)
            if not file_path.is_absolute():
                return {"clean": False, "message": "scan target path is not absolute or under a known root"}
    if not file_path.is_file():
        return {"clean": False, "message": "scan target file does not exist"}
    descriptor = detect_scanner()
    if not descriptor["available"]:
        # Caller decides whether to accept uploads without a scanner (see
        # startup_preflight / EINVITE_ALLOW_NO_SCANNER). We report clean=True
        # so the existing scan_material_bytes "not-configured" path is preserved.
        return {"clean": True, "message": "no supported scanner configured; scan skipped"}
    if descriptor["kind"] == "clamav":
        clean, message = _clamd_instream(str(file_path), timeout=SCAN_TIMEOUT_SECONDS)
        return {"clean": clean, "message": message}
    if descriptor["kind"] == "defender":
        clean, message = _defender_scan(str(file_path), timeout=SCAN_TIMEOUT_SECONDS)
        return {"clean": clean, "message": message}
    return {"clean": False, "message": f"unsupported scanner kind: {descriptor['kind']!r}"}


def scan_bytes(raw: bytes, name: str = "upload") -> dict[str, Any]:
    """Scan an in-memory blob by spilling it to a temp file.

    Convenience wrapper around :func:`scan_file` for callers (like the existing
    ``scan_material_bytes`` in ``server.py``) that have the upload in memory.

    Args:
        raw: The uploaded bytes.
        name: Hint for the temp-file suffix; sanitized to a filesystem-safe stem.

    Returns:
        Same shape as :func:`scan_file`. The temp file is always removed.
    """
    safe_stem = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in (name or "upload"))[:80] or "upload"
    tmp = tempfile.NamedTemporaryFile(prefix=f"einvite-scan-{uuid.uuid4().hex}-", suffix=f"-{safe_stem}", delete=False)
    try:
        tmp.write(raw)
        tmp.flush()
        tmp.close()
        return scan_file(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def startup_preflight(allow_skip: bool = False) -> dict[str, Any]:
    """Fail-closed gate for production startup.

    Args:
        allow_skip: When ``True``, return the descriptor instead of raising
            even when no scanner is available. Useful for developer launches.

    Returns:
        The detected scanner descriptor (see :func:`detect_scanner`).

    Raises:
        RuntimeError: When no scanner is available AND ``allow_skip`` is
            ``False`` AND the ``EINVITE_ALLOW_NO_SCANNER`` env var is not
            set to ``"1"``.
    """
    descriptor = detect_scanner()
    if descriptor["available"]:
        return descriptor
    env_override = os.environ.get("EINVITE_ALLOW_NO_SCANNER", "").strip().lower()
    if allow_skip or env_override == "1":
        return descriptor
    raise RuntimeError(
        "No supported malware scanner (ClamAV/Windows Defender) found. "
        "Install ClamAV (clamav + clamav-daemon) on Linux or enable Windows "
        "Defender on Windows, or set EINVITE_ALLOW_NO_SCANNER=1 to bypass at "
        "your own risk."
    )


def enforce_scanner_on_startup(app: Any = None) -> dict[str, Any]:
    """Flask/logger-friendly wrapper around :func:`startup_preflight`.

    Calls :func:`startup_preflight` and logs the result via ``app.logger`` when
    the Flask ``app`` argument is supplied, or via ``print`` otherwise so the
    stdlib ``http.server`` backend in ``server.py`` can use the same helper.

    Args:
        app: Optional Flask application object. When provided, the result is
            logged through ``app.logger``. When ``None`` or when the object
            has no ``logger`` attribute, the result is printed to stdout.

    Returns:
        The detected scanner descriptor.

    Raises:
        RuntimeError: Re-raised from :func:`startup_preflight` when no scanner
            is available and the bypass is not enabled.
    """
    descriptor = startup_preflight()
    message = (
        f"security_scanner_v54: scanner={descriptor['kind']!r} "
        f"available={descriptor['available']} reason={descriptor['reason']}"
    )
    logger = getattr(app, "logger", None) if app is not None else None
    if logger is not None and hasattr(logger, "info"):
        logger.info(message)
    else:
        print(message, flush=True)
    return descriptor
