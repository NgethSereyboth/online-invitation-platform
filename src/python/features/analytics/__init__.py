"""features/analytics/__init__.py — v0.67.0 (ROADMAP-v0.54-to-v1.0 Part 6)

Creator analytics & insights — first-party, privacy-preserving, retention-limited.

Submodules
----------
``model``     — schema + ingestion helpers (analytics_sessions, analytics_events).
``sessions``  — background job: close idle sessions, prune old events,
                aggregate per-invitation daily summaries.
``queries``  — read-side rollups for the dashboard + creations table.
``export``   — streamed CSV / JSON exports.

Design principles (ROADMAP §6.0):
- Privacy first. No third-party trackers. No cookies for tracking. All data
  stored on the operator's own infrastructure.
- Honest numbers. Never inflate. Unique opens are unique per recipient link
  (or per session_id for public links). Session duration is measured.
- Bilingual reports. Every metric label has EN+KH.
- Exportable. Hosts can download raw event data as CSV/JSON.
- Retention-limited. Events auto-prune after
  ``EINVITE_ANALYTICS_RETENTION_DAYS`` (default 365).

Public API
----------
``ensure_schema(db)``
    Idempotent CREATE TABLE / CREATE INDEX for analytics_sessions,
    analytics_events, analytics_summary_daily. Calls ``model.ensure_schema``
    and is the single entrypoint used by ``server.connect_sqlite()`` /
    ``_ensure_postgres_schema()``.

``enable_invitation_analytics(db, invitation_id, enabled)``
    Set ``invitations.analytics_enabled`` (column added by this version).
    Defaults to enabled (1). Hosts may turn it off per invitation; the public
    page then sends no events.

``is_invitation_analytics_enabled(db, invitation_id)``
    Check the per-invitation flag. Returns True if missing or 1.

``purge_invitation_analytics(db, invitation_id)``
    Delete all analytics_sessions + analytics_events for an invitation.
    Used by the host "delete my analytics data" button.
"""
from __future__ import annotations

from .model import (
    EVENT_TYPES,
    SESSION_IDLE_TIMEOUT_MS,
    SESSION_SPAM_WINDOW_MS,
    RETENTION_DEFAULT_DAYS,
    ensure_schema,
    upsert_session,
    insert_event,
    close_session,
    record_event_batch,
    list_active_sessions,
    purge_invitation_analytics,
    set_invitation_analytics_enabled,
    is_invitation_analytics_enabled,
)
from .sessions import (
    run_session_reconstruction,
    run_retention_prune,
    aggregate_daily_summary,
    close_idle_sessions,
    delete_spam_sessions,
)
from .queries import (
    invitation_analytics_summary,
    invitation_analytics_timeseries,
    invitation_top_referrers,
    invitation_device_split,
    invitation_country_split,
    invitation_funnel,
    invitation_live_activity,
    account_creations_table,
    account_analytics_summary,
    invitation_scroll_depth,
)
from .export import (
    stream_invitation_csv,
    stream_invitation_json,
    stream_account_csv,
    stream_account_json,
)

__all__ = [
    "EVENT_TYPES",
    "SESSION_IDLE_TIMEOUT_MS",
    "SESSION_SPAM_WINDOW_MS",
    "RETENTION_DEFAULT_DAYS",
    "ensure_schema",
    "upsert_session",
    "insert_event",
    "close_session",
    "record_event_batch",
    "list_active_sessions",
    "purge_invitation_analytics",
    "set_invitation_analytics_enabled",
    "is_invitation_analytics_enabled",
    "run_session_reconstruction",
    "run_retention_prune",
    "aggregate_daily_summary",
    "close_idle_sessions",
    "delete_spam_sessions",
    "invitation_analytics_summary",
    "invitation_analytics_timeseries",
    "invitation_top_referrers",
    "invitation_device_split",
    "invitation_country_split",
    "invitation_funnel",
    "invitation_live_activity",
    "account_creations_table",
    "account_analytics_summary",
    "invitation_scroll_depth",
    "stream_invitation_csv",
    "stream_invitation_json",
    "stream_account_csv",
    "stream_account_json",
]

VERSION = "0.69.1"
