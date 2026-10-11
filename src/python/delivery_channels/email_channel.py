"""Email delivery channel — the default adapter that reuses the existing SMTP path.

This adapter deliberately does NOT import ``server.send_platform_email`` at
module load time. The HTTP layer wires the function in via
``register_email_sender`` so the ``delivery_channels`` package stays
importable in isolation (which keeps the test suite and the contract test
simple). When no sender is registered the channel reports ``skipped`` so
the dispatch loop can still attempt other channels.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional

from .base import DeliveryChannel, SendResult


# Module-level injection point. Set by ``server.py`` at boot so the email
# adapter calls the existing SMTP path without taking a hard import cycle
# (server.py is huge and we don't want delivery_channels → server →
# delivery_channels recursion).
_EMAIL_SENDER: Optional[Callable[[str, str, str], bool]] = None


def register_email_sender(fn: Callable[[str, str, str], bool]) -> None:
    """Inject the existing SMTP sender (server.send_platform_email)."""
    global _EMAIL_SENDER
    _EMAIL_SENDER = fn


class EmailChannel(DeliveryChannel):
    name = "email"

    def available(self) -> bool:
        # The adapter is "available" when a sender has been wired in.
        return _EMAIL_SENDER is not None

    def label_en(self) -> str:
        return "Email"

    def label_km(self) -> str:
        return "អ៊ីមែល"

    def _send(self, invitation_id: str, recipient: str, message: str,
              channel_config: Dict[str, Any]) -> SendResult:
        sender = _EMAIL_SENDER
        if sender is None:
            return SendResult(channel=self.name, status="skipped",
                              error="Email sender is not wired")
        subject = str(channel_config.get("subject") or "You are invited")
        try:
            ok = bool(sender(recipient, subject, message))
        except Exception as exc:
            return SendResult(channel=self.name, status="failed",
                              error=f"{type(exc).__name__}: {exc}")
        if ok:
            return SendResult(channel=self.name, status="sent",
                              provider_message_id="smtp")
        # SMTP not configured (server.send_platform_email returns False when
        # EINVITE_SMTP_HOST / EINVITE_MAIL_FROM is missing). Treat as queued
        # so the dispatch loop records the attempt without failing the batch.
        return SendResult(channel=self.name, status="queued",
                          error="SMTP not configured; message queued for retry")
