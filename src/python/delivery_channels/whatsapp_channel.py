"""WhatsApp delivery channel — WhatsApp Business Cloud API adapter.

Uses the Meta WhatsApp Cloud API
(``POST https://graph.facebook.com/v20.0/{phone_number_id}/messages`` with
``Bearer`` auth). Docs: https://developers.facebook.com/docs/whatsapp/cloud-api.

Environment variables (all optional — channel reports ``skipped`` if missing):

* ``EINVITE_WHATSAPP_TOKEN`` — Permanent or system-user access token.
* ``EINVITE_WHATSAPP_PHONE_NUMBER_ID`` — Phone number ID from the Meta
  Business Manager.
* ``EINVITE_WHATSAPP_API_VERSION`` — API version, default ``v20.0``.

Note: the WhatsApp Cloud API only delivers "template" messages to recipients
who have not messaged the business in the last 24h. The adapter sends a
``text`` message body — this is intentional for invitation delivery because
the guest initiated the conversation by RSVP-ing. For cold lists, the host
should pre-approve a WhatsApp template and use the dedicated template endpoint
(out of scope for Phase 2a — tracked as a follow-up).
"""
from __future__ import annotations
from typing import Any, Dict

from .base import DeliveryChannel, SendResult, _env


class WhatsAppChannel(DeliveryChannel):
    name = "whatsapp"

    def __init__(self):
        self.token = _env("EINVITE_WHATSAPP_TOKEN")
        self.phone_number_id = _env("EINVITE_WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = _env("EINVITE_WHATSAPP_API_VERSION", "v20.0")

    def available(self) -> bool:
        return bool(self.token and self.phone_number_id)

    def label_en(self) -> str:
        return "WhatsApp"

    def label_km(self) -> str:
        return "WhatsApp"

    def _send(self, invitation_id: str, recipient: str, message: str,
              channel_config: Dict[str, Any]) -> SendResult:
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(recipient).lstrip("+"),
            "type": "text",
            "text": {"body": message[:4096]},
        }
        import urllib.request, urllib.error, json
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={
                                         "Authorization": f"Bearer {self.token}",
                                         "Content-Type": "application/json",
                                     }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read() or b"{}"
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = {"_raw": raw.decode("utf-8", errors="replace")}
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
        if parsed.get("_error"):
            return SendResult(channel=self.name, status="failed", error=parsed["_error"])
        if parsed.get("error"):
            err = parsed["error"]
            return SendResult(channel=self.name, status="failed",
                              error=str(err.get("message") or err))
        msg_id = ""
        try:
            msg_id = str(parsed["messages"][0]["id"])
        except Exception:
            pass
        return SendResult(channel=self.name, status="sent",
                          provider_message_id=msg_id, raw=parsed)
