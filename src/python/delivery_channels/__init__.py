"""Multi-channel delivery abstraction (Phase 2a — feature #5).

This package provides a pluggable ``DeliveryChannel`` interface so the host
platform can dispatch invitation messages through email (default SMTP path) and
optional SMS / WhatsApp / Telegram adapters without touching the core
``server.py`` delivery code. New channels are added by registering an adapter
in ``registry.py`` — the server-side dispatch loop calls
``registry.get_channel(name).send(...)`` and remains unchanged.

Design contract (frozen by ROADMAP section 5 "Multi-channel delivery"):

* Every channel adapter subclasses :class:`DeliveryChannel` and implements
  :meth:`send` returning a :class:`SendResult` (never raises on a transport
  error — it returns ``status="failed"`` with the exception string).
* Channels that require credentials degrade gracefully: if the relevant
  environment variables are not set, the channel reports
  ``status="skipped"`` rather than crashing the dispatch loop. The caller
  can therefore iterate ``available_channels()`` and still send via the
  remaining providers.
* Email remains the default channel and reuses the existing SMTP pipeline
  (``server.send_platform_email``) so a deployment without any additional
  configuration continues to work unchanged.
* No third-party SDK is imported at module load time — adapters use
  ``urllib.request`` (stdlib) so the platform stays build-tool-free per
  ROADMAP ground rule 4 and never gains a hard dependency on Twilio /
  WhatsApp / Telegram SDKs.

Public API:

    >>> from delivery_channels import get_channel, available_channels
    >>> get_channel("sms").send(invitation_id, recipient, message, cfg)
    SendResult(channel='sms', status='sent', provider_message_id='SM123', error='')
    >>> available_channels()
    ['email', 'sms']
"""
from __future__ import annotations
from .base import DeliveryChannel, SendResult, ChannelError
from .email_channel import register_email_sender
from .registry import get_channel, available_channels, register_channel, channel_metadata

__all__ = [
    "DeliveryChannel",
    "SendResult",
    "ChannelError",
    "get_channel",
    "available_channels",
    "register_channel",
    "register_email_sender",
    "channel_metadata",
]
