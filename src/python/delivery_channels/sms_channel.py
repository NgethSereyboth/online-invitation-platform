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

from .base import DeliveryChannel, SendResult, _env, _post_json


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
        # URL-encoded form body — Twilio accepts JSON too, but form is the
        # canonical Twilio shape and avoids nested-JSON quirks.
        from urllib.parse import urlencode
        body = urlencode({
            "To": recipient,
            "From": channel_config.get("from") or self.from_number,
            "Body": message[:1600],  # Twilio max per segment is 1600 chars
        })
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        # Use _post_json's machinery but with a form body — implement inline.
        import urllib.request, urllib.error
        req = urllib.request.Request(url, data=body.encode("utf-8"),
                                     headers={
                                         "Authorization": f"Basic {auth}",
                                         "Content-Type": "application/x-www-form-urlencoded",
                                         "Accept": "application/json",
                                     }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                payload = response.read() or b"{}"
                try:
                    data = __import__("json").loads(payload)
                except Exception:
                    data = {"_raw": payload.decode("utf-8", errors="replace")}
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return SendResult(channel=self.name, status="failed",
                              error=f"HTTP {exc.code}: {err_body}")
        except Exception as exc:
            return SendResult(channel=self.name, status="failed",
                              error=f"{type(exc).__name__}: {exc}")
        if data.get("_error"):
            return SendResult(channel=self.name, status="failed", error=data["_error"])
        if data.get("error_code") or data.get("status") == "failed":
            return SendResult(channel=self.name, status="failed",
                              error=str(data.get("error_message") or data))
        sid = str(data.get("sid") or "")
        status = "sent" if data.get("status") in {"sent", "delivered", "queued"} else "queued"
        return SendResult(channel=self.name, status=status,
                          provider_message_id=sid, raw=data)
