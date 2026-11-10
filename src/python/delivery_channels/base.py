"""Abstract base class + value types for multi-channel delivery adapters.

Kept intentionally small (stdlib-only). The server's HTTP layer only depends
on this interface — never on a concrete channel implementation — so the
``delivery_channels`` registry can be extended at deployment time without
touching ``server.py``.
"""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


VALID_STATUSES = {"queued", "sent", "failed", "skipped"}


class ChannelError(Exception):
    """Raised for adapter-configuration errors that should not be retried.

    Adapter implementations should NOT raise this from ``send()`` on a
    transport failure — return ``SendResult(status="failed", error=...)``
    instead so the dispatch loop can continue with the next recipient /
    channel. Reserve ``ChannelError`` for hard configuration mistakes
    surfaced by ``available()``.
    """


@dataclass
class SendResult:
    """Normalized delivery attempt outcome.

    Attributes:
        channel: The adapter name (``"email"``, ``"sms"``, …).
        status: One of ``VALID_STATUSES``. ``skipped`` is returned when the
            adapter is unconfigured (env missing) — the dispatch loop treats
            this as "no attempt made for this recipient/channel pair".
        provider_message_id: Provider-side message identifier (Twilio SID,
            WhatsApp message id, Telegram message_id). Empty string when
            not available or when the send failed.
        error: Human-readable error message. Empty string on success.
        raw: Optional provider response dict kept for audit logging.
        retryable: True when a transient transport/5xx failure means the host
            may hand this message to the durable outbound retry queue.
    """
    channel: str
    status: str
    provider_message_id: str = ""
    error: str = ""
    raw: Optional[Dict[str, Any]] = None
    retryable: bool = False

    def __post_init__(self):
        if self.status not in VALID_STATUSES:
            raise ChannelError(f"Invalid SendResult status: {self.status!r}")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Drop None raw to keep audit log compact.
        if data.get("raw") is None:
            data.pop("raw", None)
        return data


class DeliveryChannel:
    """Abstract base class for every delivery adapter.

    Subclasses MUST set ``name`` (a short lowercase identifier used in the
    registry and the ``delivery_attempts.channel`` column) and override
    :meth:`available` + :meth:`_send`. They MUST NOT raise from ``send()``;
    transport failures are reported via :class:`SendResult`.
    """

    name: str = ""

    def available(self) -> bool:
        """Return True when the channel is configured and ready to send."""
        return False

    def metadata(self) -> Dict[str, Any]:
        """Return a small descriptor for the host UI.

        Default implementation returns ``{"name": self.name, "available":
        bool, "configured": bool}``. Subclasses may extend with extra
        fields (e.g. ``sender`` for SMS, ``botUsername`` for Telegram).
        """
        return {
            "name": self.name,
            "available": self.available(),
            "configured": self.available(),
            "label_en": self.label_en(),
            "label_km": self.label_km(),
        }

    def label_en(self) -> str:
        return self.name.capitalize()

    def label_km(self) -> str:
        # Default to the English label; subclasses override.
        return self.label_en()

    def send(self, invitation_id: str, recipient: str, message: str,
             channel_config: Optional[Dict[str, Any]] = None) -> SendResult:
        """Deliver ``message`` to ``recipient`` via this channel.

        Args:
            invitation_id: Echoed in audit logs for traceability; not used
                by the provider.
            recipient: Channel-appropriate address — email address for
                email, E.164 phone for SMS/WhatsApp, numeric Telegram
                chat id for Telegram.
            message: Plain-text message body (already rendered, may include
                a signed invitation URL).
            channel_config: Optional per-invocation overrides (e.g. custom
                sender ID, locale). Adapters merge this over their env
                defaults.

        Returns:
            :class:`SendResult`. Never raises — transport errors land in
            ``status="failed"`` with ``error`` populated.
        """
        try:
            if not self.available():
                return SendResult(channel=self.name, status="skipped",
                                  error=f"{self.name} channel is not configured")
            recipient = str(recipient or "").strip()
            message = str(message or "")
            if not recipient:
                return SendResult(channel=self.name, status="skipped",
                                  error="Recipient is empty")
            return self._send(invitation_id, recipient, message, channel_config or {})
        except Exception as exc:  # pragma: no cover — defensive net
            return SendResult(channel=self.name, status="failed",
                              error=f"{type(exc).__name__}: {exc}")

    def _send(self, invitation_id: str, recipient: str, message: str,
              channel_config: Dict[str, Any]) -> SendResult:  # pragma: no cover - abstract
        raise NotImplementedError


def _env(name: str, default: str = "") -> str:
    """Read an environment variable as a stripped string (helper)."""
    return str(os.environ.get(name, default) or "").strip()


def _require_http_url(url: str) -> str:
    """Reject non-network URL schemes before passing a URL to urllib."""
    parsed = urlsplit(str(url or ""))
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("delivery endpoint must use http or https")
    return str(url)


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None,
               timeout: float = 12.0) -> Dict[str, Any]:
    """POST JSON and return the parsed JSON response (or an error dict).

    Used by the SMS/WhatsApp/Telegram adapters — never raises. A non-2xx
    response is returned as ``{"_error": "...", "_status": int}`` so the
    caller can surface it as a failed ``SendResult``.
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    try:
        from core import resilience
        response = resilience.request(
            "POST", _require_http_url(url), body=data, headers=req_headers,
            max_bytes=1_000_000, read_timeout_s=float(timeout),
        )
        raw = response.body or b"{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"_raw": raw.decode("utf-8", errors="replace")}
        if response.status >= 400:
            parsed = {**(parsed if isinstance(parsed, dict) else {"_raw": parsed}),
                      "_error": f"HTTP {response.status}", "_status": response.status,
                      "_retryable": False}
        return parsed
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}",
                "_kind": getattr(exc, "kind", "transport"),
                "_retryable": bool(getattr(exc, "retryable", False))}
