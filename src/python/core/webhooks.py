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
import time
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
