"""Outbound HTTP resilience for the eInvite backend (Sprint 7).

Every server-side call to a third party goes through :func:`request`,
:func:`get_json` or :func:`post_json`.  The policy is deliberately small and
standard-library only, matching the rest of the backend:

* **Separate timeouts.** ``connect_timeout`` bounds DNS/TCP/TLS setup and
  ``read_timeout`` bounds waiting for the response.  Both are configurable:

  =========================================  =======  =====================
  Environment variable                       Default  Meaning
  =========================================  =======  =====================
  ``EINVITE_OUTBOUND_CONNECT_TIMEOUT``       2.0 s    connect/TLS deadline
  ``EINVITE_OUTBOUND_READ_TIMEOUT``          5.0 s    response deadline
  ``EINVITE_OUTBOUND_CIRCUIT_FAILURES``      3        failures before open
  ``EINVITE_OUTBOUND_CIRCUIT_COOLDOWN``      30 s     open -> half-open
  =========================================  =======  =====================

* **Bounded responses.** ``max_bytes`` (default 2 MB) stops a chatty provider
  from filling memory.

* **Circuit breaker.** Transport errors and 5xx answers count against a host.
  After the failure threshold the breaker opens and calls fail fast for the
  cooldown, then a single half-open probe decides whether to close it again.
  A 4xx is a reachable provider and never opens the breaker.

The module never logs request data or credentials; callers log the failure with
the request's ``X-Request-ID``.  Test-only fault injection lives in
``tests/sprint7_resilience_test.py`` and its local HTTP fixture — production
code has no "chaos" switch.
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import urlsplit

DEFAULT_CONNECT_TIMEOUT = 2.0
DEFAULT_READ_TIMEOUT = 5.0
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_CIRCUIT_FAILURES = 3
DEFAULT_CIRCUIT_COOLDOWN = 30.0


class OutboundError(RuntimeError):
    """A request to a third party failed without leaking its URL or payload."""

    def __init__(self, message: str, *, kind: str = "transport", status: Optional[int] = None):
        super().__init__(message)
        self.kind = kind
        self.status = status

    @property
    def retryable(self) -> bool:
        return self.kind in {"timeout", "transport", "circuit_open"} or bool(
            self.status is not None and int(self.status) in {408, 425, 429, 500, 502, 503, 504}
        )


class CircuitOpenError(OutboundError):
    """The breaker is open, so the call was refused without touching the network."""

    def __init__(self, key: str, retry_after: float):
        super().__init__(
            f"Outbound circuit is open for {key}; retry in {max(0.0, retry_after):.0f}s",
            kind="circuit_open",
        )
        self.key = key
        self.retry_after = max(0.0, retry_after)


def _env_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def _env_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def connect_timeout() -> float:
    """Seconds allowed for DNS, TCP and TLS setup."""
    return _env_float("EINVITE_OUTBOUND_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT, 0.2, 10.0)


def read_timeout() -> float:
    """Seconds allowed for the peer to produce a response."""
    return _env_float("EINVITE_OUTBOUND_READ_TIMEOUT", DEFAULT_READ_TIMEOUT, 0.5, 30.0)


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: Mapping[str, str]

    def json(self):
        try:
            return json.loads(self.body or b"{}")
        except (TypeError, ValueError) as exc:
            raise OutboundError("Third-party response was not valid JSON", kind="malformed", status=self.status) from exc


class CircuitBreaker:
    """Thread-safe per-key circuit breaker with one half-open probe."""

    def __init__(self, failures: Optional[int] = None, cooldown: Optional[float] = None):
        self.failures = failures if failures is not None else _env_int(
            "EINVITE_OUTBOUND_CIRCUIT_FAILURES", DEFAULT_CIRCUIT_FAILURES, 1, 100
        )
        self.cooldown = cooldown if cooldown is not None else _env_float(
            "EINVITE_OUTBOUND_CIRCUIT_COOLDOWN", DEFAULT_CIRCUIT_COOLDOWN, 0.05, 600.0
        )
        self._lock = threading.Lock()
        self._state: dict[str, dict[str, float | int | bool]] = {}

    def _entry(self, key: str) -> dict[str, float | int | bool]:
        return self._state.setdefault(
            key, {"failures": 0, "opened_at": 0.0, "probing": False}
        )

    def allow(self, key: str) -> bool:
        """Return True when a call may proceed (closed, or the one half-open probe)."""
        now = time.monotonic()
        with self._lock:
            entry = self._entry(key)
            if int(entry["failures"]) < self.failures:
                return True
            if now - float(entry["opened_at"]) < self.cooldown:
                return False
            if bool(entry["probing"]):
                return False
            entry["probing"] = True
            return True

    def record_success(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            entry = self._entry(key)
            entry["failures"] = int(entry["failures"]) + 1
            entry["probing"] = False
            if int(entry["failures"]) >= self.failures:
                entry["opened_at"] = now

    def retry_after(self, key: str) -> float:
        with self._lock:
            entry = self._state.get(key)
            if not entry or int(entry["failures"]) < self.failures:
                return 0.0
            return max(0.0, self.cooldown - (time.monotonic() - float(entry["opened_at"])))

    def state(self, key: str) -> str:
        with self._lock:
            entry = self._state.get(key)
            if not entry or int(entry["failures"]) < self.failures:
                return "closed"
            return "half-open" if bool(entry["probing"]) else "open"

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._state.clear()
            else:
                self._state.pop(key, None)


_BREAKER = CircuitBreaker()


def breaker() -> CircuitBreaker:
    """Return the process-wide breaker used by the backend call sites."""
    return _BREAKER


def _validate_target(scheme: str, host, username, password) -> None:
    """Reject non-http(s), hostless and credential-bearing URLs."""
    if scheme not in {"http", "https"} or not host:
        raise OutboundError("Outbound URL must be an absolute http(s) URL", kind="invalid")
    if username or password:
        raise OutboundError("Outbound URL must not embed credentials", kind="invalid")


def _target_port(scheme: str, port):
    """Return the explicit port, or the scheme default."""
    if port:
        return port
    return 443 if scheme == "https" else 80


def _target_path(parsed):
    """Return the request path with its query string, defaulting to '/'."""
    path = parsed.path
    if not path:
        path = "/"
    if parsed.query:
        return path + "?" + parsed.query
    return path


def _parse_target(url: str):
    """Validate an outbound URL and split it into scheme/host/port/path."""
    parsed = urlsplit(str(url))
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    _validate_target(scheme, host, parsed.username, parsed.password)
    return scheme, str(host), _target_port(scheme, parsed.port), _target_path(parsed)


def _resolve_breaker(host: str, port: int, key: Optional[str], instance: Optional[CircuitBreaker]):
    """Resolve the caller's breaker/key overrides against the process default."""
    return key or f"{host}:{port}", instance or _BREAKER


def _resolve_timeouts(connect_s: Optional[float], read_s: Optional[float]):
    """Resolve explicit per-call deadlines against the configured defaults."""
    effective_connect = connect_timeout() if connect_s is None else max(0.05, float(connect_s))
    effective_read = read_timeout() if read_s is None else max(0.05, float(read_s))
    return effective_connect, effective_read


def _read_bounded(response, max_bytes: int, host: str):
    """Read at most ``max_bytes`` and return status/body/headers."""
    limit = int(max_bytes)
    raw = response.read(limit + 1)
    if len(raw) > limit:
        raise OutboundError(
            f"{host} response exceeded the {limit} byte limit",
            kind="too_large", status=int(response.status),
        )
    return int(response.status), bytes(raw or b""), dict(response.getheaders())


def _exchange(connection_class, host: str, port: int, method: str, path: str,
              body: Optional[bytes], headers: Optional[Mapping[str, str]],
              connect_s: float, read_s: float, max_bytes: int):
    """Open one connection, apply the read deadline and bound the response."""
    connection = connection_class(host, port, timeout=connect_s)
    try:
        connection.connect()
        if connection.sock is not None:
            connection.sock.settimeout(read_s)
        connection.request(method.upper(), path, body=body, headers=dict(headers or {}))
        return _read_bounded(connection.getresponse(), max_bytes, host)
    finally:
        connection.close()


def request(
    method: str,
    url: str,
    *,
    body: Optional[bytes] = None,
    headers: Optional[Mapping[str, str]] = None,
    connect_timeout_s: Optional[float] = None,
    read_timeout_s: Optional[float] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    breaker_key: Optional[str] = None,
    breaker_instance: Optional[CircuitBreaker] = None,
    use_breaker: bool = True,
) -> Response:
    """Perform one bounded HTTP request and return its status, body and headers.

    Raises :class:`CircuitOpenError` before any network I/O when the breaker is
    open, and :class:`OutboundError` for timeouts, transport errors, 5xx
    answers, oversized responses, invalid URLs and malformed JSON (through
    :meth:`Response.json`).  The exception message names only the host, never
    credentials or the path.
    """
    scheme, host, port, path = _parse_target(url)
    key, active_breaker = _resolve_breaker(host, port, breaker_key, breaker_instance)
    if use_breaker and not active_breaker.allow(key):
        raise CircuitOpenError(key, active_breaker.retry_after(key))

    connect_s, read_s = _resolve_timeouts(connect_timeout_s, read_timeout_s)
    connection_class = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    try:
        status, raw, response_headers = _exchange(
            connection_class, host, port, method, path, body, headers,
            connect_s, read_s, max_bytes,
        )
    except OutboundError:
        raise
    except (socket.timeout, TimeoutError) as exc:
        active_breaker.record_failure(key)
        raise OutboundError(f"{host} timed out", kind="timeout") from exc
    except ssl.SSLError as exc:
        active_breaker.record_failure(key)
        raise OutboundError(f"{host} TLS handshake failed", kind="transport") from exc
    except (OSError, http.client.HTTPException) as exc:
        active_breaker.record_failure(key)
        raise OutboundError(f"{host} request failed ({type(exc).__name__})", kind="transport") from exc

    if status >= 500:
        active_breaker.record_failure(key)
        # A 5xx is a failed outbound call for every caller that wants a result
        # (AI, billing, messaging, geocoding); expose its status on the
        # exception so callers can distinguish it from a timeout.
        raise OutboundError(f"{host} returned HTTP {status}", kind="server", status=status)
    active_breaker.record_success(key)
    return Response(status, raw, response_headers)


def _raise_for_http_error(status: int) -> None:
    """Treat any 4xx/5xx as a failed provider call for JSON helpers."""
    if status >= 400:
        raise OutboundError(f"Third-party endpoint returned HTTP {status}", kind="client", status=status)


def get_json(url: str, **kwargs):
    """GET ``url`` and parse its JSON body."""
    response = request("GET", url, **kwargs)
    _raise_for_http_error(response.status)
    return response.json()


def post_json(url: str, payload, **kwargs):
    """POST a JSON ``payload`` and parse the JSON body.

    ``payload`` may be a mapping (serialized here) or raw bytes (sent as-is).
    """
    if isinstance(payload, (bytes, bytearray)):
        body = bytes(payload)
    else:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    headers.update(dict(kwargs.pop("headers", {}) or {}))
    response = request("POST", url, body=body, headers=headers, **kwargs)
    _raise_for_http_error(response.status)
    return response.json()


def _read_wire_response(response, limit: int, host: str) -> bytes:
    """Read a urllib response with the same body cap as :func:`request`.

    ``urllib`` is retained for form-encoded providers because Twilio-compatible
    gateways expose the canonical wire format that way. The socket deadline is
    tightened to the read budget after the headers arrive.
    """
    try:
        raw = response.read(limit + 1)
    except TypeError:  # small test doubles implement read() without a size
        raw = response.read()
    if len(raw) > limit:
        raise OutboundError(
            f"{host} response exceeded the {limit} byte limit",
            kind="too_large",
            status=int(getattr(response, "status", 0) or 0),
        )
    return bytes(raw or b"")


def _form_failure(message: str, kind: str, status: Optional[int] = None) -> dict:
    result = {"_error": message, "_kind": kind, "_retryable": True}
    if status is not None:
        result["_status"] = status
    return result


def _form_transport(
    url: str,
    body: bytes,
    headers: dict,
    connect_s: float,
    read_s: float,
    max_bytes: int,
    host: str,
    key: str,
    breaker: CircuitBreaker,
):
    """Run the urllib exchange and map transport errors to retry metadata."""
    try:
        wire = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(wire, timeout=connect_s) as response:
            try:  # separate read deadline after DNS/TCP/TLS and headers
                response.fp.raw._sock.settimeout(read_s)
            except Exception:
                pass
            status = int(getattr(response, "status", 200) or 200)
            return status, _read_wire_response(response, int(max_bytes), host), None
    except urllib.error.HTTPError as exc:
        try:
            raw = _read_wire_response(exc, int(max_bytes), host)
        except Exception:
            raw = b""
        return int(exc.code), raw, None
    except (socket.timeout, TimeoutError):
        breaker.record_failure(key)
        return 0, b"", _form_failure(f"{host} timed out", "timeout")
    except (OSError, http.client.HTTPException) as exc:
        breaker.record_failure(key)
        return 0, b"", _form_failure(
            f"{host} request failed ({type(exc).__name__})", "transport"
        )


def _form_response(status: int, raw: bytes) -> dict:
    try:
        parsed = json.loads(raw or b"{}")
    except (TypeError, ValueError):
        parsed = {"_raw": raw.decode("utf-8", errors="replace")}
    if not isinstance(parsed, dict):
        parsed = {"_raw": parsed}
    if status >= 400:
        parsed = {**parsed, "_error": f"HTTP {status}", "_status": status, "_retryable": False}
    return parsed


def post_form(
    url: str,
    payload,
    *,
    headers: Optional[Mapping[str, str]] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    connect_timeout_s: Optional[float] = None,
    read_timeout_s: Optional[float] = None,
    breaker_key: Optional[str] = None,
    breaker_instance: Optional[CircuitBreaker] = None,
):
    """POST a form body through the shared timeout and breaker policy.

    This is the form-encoded sibling of :func:`post_json` for Twilio-compatible
    gateways. It uses the configured connect/read deadlines and the per-host
    breaker; the response body is capped. A 5xx or transport error returns
    ``_retryable=True`` so the channel can hand the message to the durable
    retry queue. A 4xx is final and is returned as an error dictionary rather
    than opening the breaker.
    """
    _scheme, host, port, _path = _parse_target(url)
    key, active_breaker = _resolve_breaker(host, port, breaker_key, breaker_instance)
    if not active_breaker.allow(key):
        return _form_failure(f"Circuit open for {host}; retry later", "circuit_open")
    connect_s, read_s = _resolve_timeouts(connect_timeout_s, read_timeout_s)
    body = urllib.parse.urlencode(payload or {}).encode("utf-8")
    request_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    request_headers.update(dict(headers or {}))
    status, raw, error = _form_transport(
        url, body, request_headers, connect_s, read_s, int(max_bytes),
        host, key, active_breaker,
    )
    if error is not None:
        return error
    if status >= 500:
        active_breaker.record_failure(key)
        return _form_failure(f"HTTP {status}", "server", status)
    active_breaker.record_success(key)
    return _form_response(status, raw)
