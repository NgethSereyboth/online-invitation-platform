"""Channel registry — maps ``name`` -> ``DeliveryChannel`` singleton.

Adapters register themselves at import time via :func:`register_channel`.
The HTTP layer calls :func:`available_channels` to render the host UI and
:func:`get_channel` to dispatch. Adding a new channel is a one-line
``register_channel("foo", FooChannel())`` call — no server.py change.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .base import DeliveryChannel, ChannelError
from .email_channel import EmailChannel, register_email_sender  # re-export
from .sms_channel import SmsChannel
from .whatsapp_channel import WhatsAppChannel
from .telegram_channel import TelegramChannel


_REGISTRY: Dict[str, DeliveryChannel] = {}


def register_channel(channel: DeliveryChannel) -> None:
    """Register a channel adapter by its ``name`` attribute.

    Idempotent — registering the same name twice replaces the prior instance.
    """
    if not channel.name:
        raise ChannelError("Channel must declare a non-empty name")
    _REGISTRY[channel.name] = channel


def get_channel(name: str) -> Optional[DeliveryChannel]:
    """Return the registered adapter, or ``None`` when not registered."""
    return _REGISTRY.get(str(name or "").lower())


def available_channels() -> List[str]:
    """Return names of all registered adapters that report ``available()``.

    Order is deterministic (sorted by name) so the host UI is stable. The
    email channel is always present because the package auto-registers it.
    """
    return sorted(name for name, channel in _REGISTRY.items() if channel.available())


def channel_metadata() -> List[Dict[str, Any]]:
    """Return the descriptor list for the host delivery dialog UI."""
    # Always emit every registered channel — the host UI needs to show "not
    # configured yet" entries so the host knows which env vars to set.
    return [
        {**channel.metadata(), "name": name}
        for name, channel in sorted(_REGISTRY.items())
    ]


# --- Default registration -------------------------------------------------
# The email channel is always available (default SMTP path). SMS / WhatsApp
# / Telegram are registered too — they report ``available() == False`` when
# their env vars are missing, so the dispatch loop gracefully skips them.

register_channel(EmailChannel())
register_channel(SmsChannel())
register_channel(WhatsAppChannel())
register_channel(TelegramChannel())


__all__ = [
    "register_channel",
    "register_email_sender",
    "get_channel",
    "available_channels",
    "channel_metadata",
]
