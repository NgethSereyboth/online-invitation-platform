"""SMS delivery channel — Twilio-compatible REST adapter.

Uses the Twilio Programmable SMS REST API
(``POST {api_origin}/Accounts/{sid}/Messages.json`` with HTTP Basic auth).
Any Twilio-compatible gateway (e.g. Telnyx, Vonage SMS with a Twilio-shaped
shim) will work — the only contract is the request/response shape.

Environment variables (all optional — channel reports ``skipped`` if missing):

* ``EINVITE_SMS_ACCOUNT_SID`` — Twilio account SID.
* ``EINVITE_SMS_AUTH_TOKEN`` — Twilio auth token.
* ``EINVITE_SMS_FROM`` — Sender phone (E.164).
* ``EINVITE_SMS_API_ORIGIN`` — Override the default ``https://api.twilio.com``
  (set this for self-hosted Twilio-compatible gateways).
"""
from __future__ import annotations
import base64
from typing import Any, Dict

from .base import DeliveryChannel, SendResult, _env, _require_http_url


class SmsChannel(DeliveryChannel):
    name = "sms"

    def __init__(self):
        self.account_sid = _env("EINVITE_SMS_ACCOUNT_SID")
        self.auth_token = _env("EINVITE_SMS_AUTH_TOKEN")
        self.from_number = _env("EINVITE_SMS_FROM")
        self.api_origin = _env("EINVITE_SMS_API_ORIGIN", "https://api.twilio.com")

    def available(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def label_en(self) -> str:
        return "SMS"

    def label_km(self) -> str:
        return "SMS"

    def _send(self, invitation_id: str, recipient: str, message: str,
              channel_config: Dict[str, Any]) -> SendResult:
        url = f"{self.api_origin.rstrip('/')}/Accounts/{self.account_sid}/Messages.json"
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        # Twilio's canonical wire format is form-encoded. The shared resilience
        # form helper supplies configured connect/read deadlines, a bounded
        # response and the per-host breaker while preserving that wire shape.
        from core import resilience
        data = resilience.post_form(
            _require_http_url(url),
            {
                "To": recipient,
                "From": channel_config.get("from") or self.from_number,
                "Body": message[:1600],
            },
            headers={"Authorization": f"Basic {auth}"},
            max_bytes=1_000_000,
        )
        if data.get("_error"):
            return SendResult(channel=self.name, status="failed", error=data["_error"],
                              retryable=bool(data.get("_retryable")))
        if data.get("error_code") or data.get("status") == "failed":
            return SendResult(channel=self.name, status="failed",
                              error=str(data.get("error_message") or data))
        sid = str(data.get("sid") or "")
        if not sid:
            return SendResult(channel=self.name, status="failed",
                              error="Provider response did not include a message SID",
                              raw=data)
        provider_status = str(data.get("status") or "").lower()
        if provider_status in {"queued", "accepted", "scheduled", "sending"}:
            status = "queued"
        elif provider_status in {"sent", "delivered"}:
            status = "sent"
        else:
            return SendResult(channel=self.name, status="failed",
                              error=f"Unrecognized provider status: {provider_status or 'missing'}",
                              provider_message_id=sid, raw=data)
        return SendResult(channel=self.name, status=status,
                          provider_message_id=sid, raw=data)
