"""Outbound webhook signing (ROADMAP-v0.54-to-v1.0 §4.6).

Outbound webhooks (billing, AI events, RSVP callbacks) are signed with
HMAC-SHA256 so the receiver can verify the origin. Each webhook destination
has its own secret (stored encrypted via ``core.crypto.encrypt_field`` when
at rest). The signature carries a millisecond-precision timestamp so the
receiver can reject replays older than 5 minutes.

Header layout::

    X-EInvite-Signature: t=<ts>,v1=<hex-hmac>

Where ``t`` is the Unix-ms timestamp and ``v1`` is the HMAC-SHA256 of
``f"{ts}.{body}"`` using the webhook secret as the key. The receiver splits
the header, recomputes the HMAC over ``f"{ts}.{body}"``, and compares it
constant-time with ``v1``. This mirrors Stripe's signing scheme so receivers
using Stripe-style verifiers can drop in our header with minimal change.

Usage (sender side)::

    from core.webhooks import sign_webhook, build_headers
    body = json.dumps(event).encode("utf-8")
    headers = build_headers(body, secret)
    requests.post(url, data=body, headers=headers)

Usage (receiver side, in any language)::

    sig = request.headers["X-EInvite-Signature"]
    # sig = "t=1700000000000,v1=abcdef..."
    ts, _, v1 = sig.partition(",v1=")
    ts = ts[2:]  # strip "t="
    expected = hmac_sha256(secret, f"{ts}.{body}".encode()).hex()
    if not constant_time_eq(expected, v1): reject
    if abs(now_ms - int(ts)) > 5 * 60 * 1000: reject  # replay protection
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import ipaddress
import random
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

# Webhook receivers must reject signatures older than this (replay protection).
DEFAULT_TOLERANCE_MS = 5 * 60 * 1000  # 5 minutes

# Header name. Multiple ``,v1=`` segments are NOT supported (single secret per
# webhook destination). The ``t=`` prefix lets us add ``v2=`` later (e.g.
# SHA-3) without breaking old verifiers.
SIGNATURE_HEADER = "X-EInvite-Signature"
TIMESTAMP_HEADER = "X-EInvite-Timestamp"


def _now_ms() -> int:
    return int(time.time() * 1000)


def sign_webhook(body: bytes, secret: str, timestamp_ms: Optional[int] = None) -> str:
    """Return the ``X-EInvite-Signature`` value for ``body`` + ``secret``.

    Format: ``t=<ts>,v1=<hex>`` where ``hex = HMAC-SHA256(secret, t.body)``.
    The body must be the EXACT bytes that will be sent on the wire — not a
    re-serialized JSON, since re-serialization can change field order and
    invalidate the signature.

    Args:
        body: The request body bytes.
        secret: The webhook destination's secret (per-destination, stored
            encrypted at rest).
        timestamp_ms: Optional override (defaults to ``now()``). Used by tests
            and by the replay-verification test path.

    Returns:
        The header value, ready to be sent as ``X-EInvite-Signature: <value>``.
    """
    if not isinstance(body, (bytes, bytearray)):
        raise TypeError("body must be bytes; pass the EXACT wire payload")
    if not secret:
        raise ValueError("webhook secret must be non-empty")
    ts = int(timestamp_ms if timestamp_ms is not None else _now_ms())
    payload = f"{ts}.".encode("ascii") + bytes(body)
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def build_headers(body: bytes, secret: str, timestamp_ms: Optional[int] = None) -> dict:
    """Return the full header dict to send alongside the webhook body."""
    ts = int(timestamp_ms if timestamp_ms is not None else _now_ms())
    return {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: sign_webhook(body, secret, ts),
        TIMESTAMP_HEADER: str(ts),
    }


def verify_signature(body: bytes, signature_header: str, secret: str,
                     tolerance_ms: int = DEFAULT_TOLERANCE_MS,
                     now_ms: Optional[int] = None) -> bool:
    """Return True iff ``signature_header`` is valid for ``body`` + ``secret``.

    Constant-time on both the HMAC compare and the timestamp window check.
    Rejects if:
      - the header is malformed (missing ``t=`` or ``v1=``)
      - the HMAC does not match
      - the timestamp is older than ``tolerance_ms`` (replay protection)
      - the timestamp is in the future (clock-skew attack)
    """
    if not isinstance(body, (bytes, bytearray)):
        return False
    if not signature_header or not secret:
        return False
    # Parse ``t=<ts>,v1=<hex>``.
    parts = signature_header.split(",")
    if len(parts) < 2:
        return False
    ts_str = parts[0]
    v1_str = ",".join(parts[1:])  # tolerate any stray commas in v1
    if not ts_str.startswith("t=") or not v1_str.startswith("v1="):
        return False
    try:
        ts = int(ts_str[2:])
    except (TypeError, ValueError):
        return False
    provided = v1_str[3:]
    expected_payload = f"{ts}.".encode("ascii") + bytes(body)
    expected = hmac.new(secret.encode("utf-8"), expected_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        return False
    now = int(now_ms if now_ms is not None else _now_ms())
    if ts > now + 30_000:  # 30s clock-skew tolerance
        return False
    if (now - ts) > tolerance_ms:
        return False
    return True


def generate_webhook_secret() -> str:
    """Return a fresh 32-byte URL-safe webhook secret.

    Used by the webhook-destination creation flow when the operator does not
    supply a secret explicitly. The secret is then persisted encrypted via
    ``core.crypto.encrypt_field``.
    """
    import secrets as _secrets
    return _secrets.token_urlsafe(32)


#: Statuses worth retrying: rate limiting, transient server/edge failures.
#: Every other 4xx is final — an identical retry would be rejected identically.
RETRYABLE_STATUSES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
DEFAULT_ATTEMPTS = 5
DEFAULT_BACKOFF_BASE_S = 1.0
MAX_BACKOFF_S = 30.0
#: Delivery limits from the work order (D-6): a slow or chatty receiver must not
#: hold the worker, and a huge response body must not be buffered.
DEFAULT_TIMEOUT_S = 5.0
DEFAULT_CONNECT_TIMEOUT_S = 2.0
MAX_RESPONSE_BYTES = 64 * 1024
#: Backoff between queue attempts is 1, 2, 4, 8 s (the fifth attempt is final).
QUEUE_BACKOFF_BASE_S = 1.0
QUEUE_MAX_ATTEMPTS = 5


def _addresses(host: str, port: int) -> list:
    """Resolve ``host`` to every address, so a mixed answer cannot slip through."""
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ValueError(f"Webhook host cannot be resolved: {exc}") from exc
    seen = []
    for info in infos:
        address = info[4][0]
        if address not in seen:
            seen.append(address)
    if not seen:
        raise ValueError("Webhook host resolved to no address")
    return seen


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified)


def validate_destination(url: str, *, allow_private: bool = False) -> dict:
    """Return ``{url, scheme, host, port, path, ips}`` for a deliverable URL.

    The D-6 rules, in one place so the account route and the delivery worker
    cannot drift: an absolute URL, **https only** (a deliberate private receiver
    may use ``http`` through ``allow_private``), no userinfo, and no address in
    the private / loopback / link-local / reserved / multicast / unspecified
    ranges. ``169.254.169.254`` (cloud metadata) is link-local and refused by the
    same test. Every resolved address must pass, so a mixed DNS answer fails.
    """
    endpoint = str(url or "").strip()
    parsed = urllib.parse.urlsplit(endpoint)
    scheme = parsed.scheme.lower()
    if not allow_private and scheme != "https":
        raise ValueError("Webhook URL must be https")
    if scheme not in {"http", "https"}:
        raise ValueError("Webhook URL must be an absolute http(s) URL")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("Webhook URL must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ValueError("Webhook URL must not embed credentials")
    port = parsed.port or (443 if scheme == "https" else 80)
    addresses = _addresses(parsed.hostname, port)
    if not allow_private:
        for address in addresses:
            if not _is_public(address):
                raise ValueError("Webhook URL must not point at a private or loopback address")
    return {
        "url": endpoint,
        "scheme": scheme,
        "host": parsed.hostname,
        "port": port,
        "path": parsed.path or "/",
        "query": parsed.query,
        "ips": addresses,
    }


def _read_capped(response, limit: int = MAX_RESPONSE_BYTES) -> bytes:
    """Read at most ``limit`` bytes: the receiver's reply is only a health signal."""
    data = response.read(limit)
    return bytes(data or b"")


def _connect_pinned(scheme: str, host: str, port: int, ip: str, timeout: float) -> socket.socket:
    """Open the TCP (and TLS) connection to the validated address, not a fresh DNS answer.

    Pinning the address closes the resolve-then-connect window a rebinding host
    would exploit. TLS still verifies the certificate against ``host`` (SNI and
    ``check_hostname``), so pinning cannot be used to bypass certificate checks.
    """
    sock = socket.create_connection((ip, port), timeout=timeout)
    if scheme != "https":
        return sock
    context = ssl.create_default_context()
    try:
        return context.wrap_socket(sock, server_hostname=host)
    except Exception:
        sock.close()
        raise


def _post_pinned(destination: dict, body: bytes, headers: dict, timeout: float,
                 connect_timeout: Optional[float] = None) -> int:
    """POST once to the pinned address and return the status. No redirects.

    ``http.client`` never follows ``3xx`` responses — it returns the status — so a
    redirect stays a final, non-2xx answer instead of a second request to a host
    the SSRF check never saw.
    """
    host, port = destination["host"], destination["port"]
    ip = destination["ips"][0]
    path = destination["path"] + ("?" + destination["query"] if destination.get("query") else "")
    connect_timeout = min(float(timeout), float(connect_timeout or timeout))
    connection = http.client.HTTPConnection(host, port, timeout=connect_timeout)
    connection.sock = _connect_pinned(destination["scheme"], host, port, ip, connect_timeout)
    connection.sock.settimeout(float(timeout))  # read deadline, independent of connect
    try:
        default_port = 443 if destination["scheme"] == "https" else 80
        connection.putrequest("POST", path, skip_host=True, skip_accept_encoding=True)
        connection.putheader("Host", host if port == default_port else f"{host}:{port}")
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        _read_capped(response)
        return int(response.status)
    finally:
        connection.close()


def deliver(url: str, body: bytes, secret: str, *,
            attempts: int = DEFAULT_ATTEMPTS,
            timeout: float = DEFAULT_TIMEOUT_S,
            backoff_base: float = DEFAULT_BACKOFF_BASE_S,
            allow_private: bool = False,
            connect_timeout: Optional[float] = DEFAULT_CONNECT_TIMEOUT_S,
            sleep=None,
            opener=None,
            timestamp_ms: Optional[int] = None) -> dict:
    """POST ``body`` to ``url`` signed with ``secret``, retrying with backoff.

    Each attempt is freshly signed (new timestamp), so a retry minutes later
    still falls inside the receiver's replay window. Every attempt re-validates
    the URL (https, public address) and connects to the address it just checked
    — a DNS change between attempts cannot redirect the delivery. Retries
    transport errors, 429 and 5xx up to ``attempts`` total tries with
    exponential backoff (``backoff_base * 2**(n-1)``, capped at 30 s, plus up to
    25 % jitter). ``3xx`` is final and never followed.

    ``sleep``/``opener`` exist for tests. With ``opener`` the pinned transport is
    bypassed, so the URL is still validated but the socket is the caller's; the
    product never passes one.

    Returns ``{"ok": bool, "status": int | None, "attempts": int,
    "error": str | None}``. Never raises for delivery failures.
    """
    if not url:
        raise ValueError("webhook url must be non-empty")
    if not secret:
        raise ValueError("webhook secret must be non-empty")
    body = bytes(body)
    sleep = sleep or time.sleep
    last_status: Optional[int] = None
    last_error: Optional[str] = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        try:
            destination = validate_destination(url, allow_private=allow_private)
        except ValueError as exc:
            return {"ok": False, "status": None, "attempts": attempt, "error": f"invalid destination: {exc}"}
        ts = int(timestamp_ms) if timestamp_ms is not None else _now_ms()
        headers = build_headers(body, secret, ts)
        try:
            if opener is not None:
                request = urllib.request.Request(url, data=body, method="POST", headers=headers)
                with opener(request, timeout=timeout) as response:
                    status = int(getattr(response, "status", 0) or 0)
                    try:
                        _read_capped(response)
                    except Exception:
                        pass
            else:
                status = _post_pinned(destination, body, headers, timeout, connect_timeout)
            if status not in RETRYABLE_STATUSES:
                return {
                    "ok": 200 <= status < 300,
                    "status": status,
                    "attempts": attempt,
                    "error": None if 200 <= status < 300 else f"HTTP {status}",
                }
            last_status, last_error = status, f"HTTP {status}"
        except urllib.error.HTTPError as exc:  # only reachable through ``opener``
            status = int(exc.code)
            if status not in RETRYABLE_STATUSES:
                return {"ok": False, "status": status, "attempts": attempt, "error": f"HTTP {status}"}
            last_status, last_error = status, f"HTTP {status}"
        except Exception as exc:  # DNS, refused, timeout, TLS, a refused redirect — all retryable
            last_status, last_error = None, f"{type(exc).__name__}: {exc}"
        if attempt < attempts:
            delay = min(MAX_BACKOFF_S, backoff_base * (2 ** (attempt - 1)))
            delay *= 1 + random.random() * 0.25
            sleep(delay)
    return {"ok": False, "status": last_status, "attempts": int(attempts), "error": last_error}
