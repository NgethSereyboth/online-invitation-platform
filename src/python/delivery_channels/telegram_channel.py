"""Telegram delivery channel — Bot API adapter.

Uses the official Telegram Bot API (``POST https://api.telegram.org/bot{token}/sendMessage``).
Docs: https://core.telegram.org/bots/api#sendmessage.

Environment variables (all optional — channel reports ``skipped`` if missing):

* ``EINVITE_TELEGRAM_BOT_TOKEN`` — Bot token from ``@BotFather``.

Recipients are numeric chat ids (``channel_config["chat_id"]`` overrides
``recipient`` if the host wants to test against a known chat). The
``parse_mode`` defaults to ``"HTML"`` so invitation snippets can include
``<a href="...">`` links to the public invitation URL.
"""
from __future__ import annotations
from typing import Any, Dict

from core import resilience
from .base import DeliveryChannel, SendResult, _env, _require_http_url, _post_json


class TelegramChannel(DeliveryChannel):
    name = "telegram"

    def __init__(self):
        self.bot_token = _env("EINVITE_TELEGRAM_BOT_TOKEN")
        self.api_origin = _env("EINVITE_TELEGRAM_API_ORIGIN", "https://api.telegram.org")

    def available(self) -> bool:
        return bool(self.bot_token)

    def label_en(self) -> str:
        return "Telegram"

    def label_km(self) -> str:
        return "តេលេក្រាម"

    def _send(self, invitation_id: str, recipient: str, message: str,
              channel_config: Dict[str, Any]) -> SendResult:
        url = f"{self.api_origin.rstrip('/')}/bot{self.bot_token}/sendMessage"
        chat_id = str(channel_config.get("chat_id") or recipient)
        payload = {
            "chat_id": chat_id,
            "text": message[:4096],
            "parse_mode": str(channel_config.get("parse_mode") or "HTML"),
            "disable_web_page_preview": bool(channel_config.get("disable_preview", False)),
        }
        parsed = _post_json(_require_http_url(url), payload,
                            timeout=float(resilience.read_timeout()))
        if parsed.get("_error"):
            return SendResult(channel=self.name, status="failed", error=parsed["_error"],
                              retryable=bool(parsed.get("_retryable")))
        if not parsed.get("ok"):
            return SendResult(channel=self.name, status="failed",
                              error=str(parsed.get("description") or parsed))
        msg_id = ""
        try:
            msg_id = str(parsed["result"]["message_id"])
        except Exception:
            pass
        return SendResult(channel=self.name, status="sent",
                          provider_message_id=msg_id, raw=parsed)
