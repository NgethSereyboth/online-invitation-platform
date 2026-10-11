"""features/analytics/sessions.py — v0.67.0–v0.69.1
(ROADMAP-v0.54-to-v1.0 §6.4 + §6.10)

Background job: session reconstruction + retention cleanup.

Runs every 5 minutes (the server boots a single thread that calls
``run_session_reconstruction`` on that cadence; ``server.py`` owns the
scheduler loop). Each invocation:

1. Closes sessions that have been idle >30 min
   (``SESSION_IDLE_TIMEOUT_MS``) — sets ``ended_at = last_event_ts + 30min``
   and ``duration_ms = ended_at - started_at``.

2. Deletes sessions with no events in the last 24h
   (``SESSION_SPAM_WINDOW_MS``) — spam cleanup. Sessions that ended
   (have ``ended_at``) and have no events in the spam window are also
   pruned; we never delete a session that's still active.

3. Aggregates per-invitation counts into ``analytics_summary_daily``.
   One row per (invitation_id, day). The aggregation covers the day
   that just completed (UTC); it's idempotent — running twice for the
   same day overwrites the row.

4. (§6.10) Prunes analytics older than
   ``EINVITE_ANALYTICS_RETENTION_DAYS`` (default 365). Deletes events
   first, then sessions, then daily summaries. Never deletes a session
   that's still active (no ``ended_at``).

5. Logs prune counts to the audit log so the operator can see the
   retention policy working.

Public API
----------
``run_session_reconstruction(db)``
    Full pass: close idle → delete spam → aggregate → prune. Returns a
    dict of counts for logging/audit.

``close_idle_sessions(db, now_ms=None)``
    Mark idle sessions ended. Returns count closed.

``delete_spam_sessions(db, now_ms=None)``
    Delete sessions with no events in 24h. Returns count deleted.

``aggregate_daily_summary(db, day=None, invitation_id=None)``
    Build / refresh the daily summary rows. ``day`` is 'YYYY-MM-DD' (UTC);
    defaults to yesterday so the day is fully complete.

``run_retention_prune(db, retention_days=None)``
    Delete analytics older than the retention window. Returns a dict of
    counts per table.
"""
from __future__ import annotations

import os
import time
from typing import Optional

from .model import (
    SESSION_IDLE_TIMEOUT_MS,
    SESSION_SPAM_WINDOW_MS,
    RETENTION_DEFAULT_DAYS,
    ensure_schema,
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _utc_day(ts_ms: int) -> str:
    """Format a millisecond timestamp as 'YYYY-MM-DD' in UTC."""
    return time.strftime("%Y-%m-%d", time.gmtime(ts_ms / 1000))


def close_idle_sessions(db, now_ms: Optional[int] = None) -> int:
    """Close sessions that have been idle > SESSION_IDLE_TIMEOUT_MS.

    Sets ``ended_at = last_event_ts + 30min`` and computes ``duration_ms``.
    Returns the count of sessions closed.
    """
    ensure_schema(db)
    now = int(now_ms or _now_ms())
    cutoff = now - SESSION_IDLE_TIMEOUT_MS
    # Find sessions still open whose latest event is older than the cutoff.
    rows = db.execute(
        "SELECT s.id AS sid, s.started_at AS started, "
        "       (SELECT MAX(e.created_at) FROM analytics_events e WHERE e.session_id = s.id) AS last_ts, "
        "       s.max_scroll_pct AS scroll "
        "FROM analytics_sessions s "
        "WHERE s.ended_at IS NULL "
        "  AND (SELECT MAX(e.created_at) FROM analytics_events e WHERE e.session_id = s.id) < ?",
        (cutoff,)
    ).fetchall()
    closed = 0
    for row in rows:
        last_ts = int(row["last_ts"] or row["started"])
        ended_at = last_ts + SESSION_IDLE_TIMEOUT_MS
        duration = max(0, ended_at - int(row["started"]))
        scroll = int(row["scroll"] or 0)
        db.execute(
            "UPDATE analytics_sessions SET ended_at=?, duration_ms=?, max_scroll_pct=? "
            "WHERE id=? AND ended_at IS NULL",
            (ended_at, duration, scroll, row["sid"])
        )
        closed += 1
    return closed


def delete_spam_sessions(db, now_ms: Optional[int] = None) -> int:
    """Delete sessions with no events in the last 24h.

    Sessions that are still active (no ``ended_at``) are NEVER deleted
    even if they have no recent events — that's the close-idle path's
    job. Returns the count of sessions deleted.
    """
    ensure_schema(db)
    now = int(now_ms or _now_ms())
    cutoff = now - SESSION_SPAM_WINDOW_MS
    rows = db.execute(
        "SELECT s.id AS sid FROM analytics_sessions s "
        "WHERE s.ended_at IS NOT NULL "
        "  AND NOT EXISTS (SELECT 1 FROM analytics_events e "
        "                  WHERE e.session_id = s.id AND e.created_at >= ?)",
        (cutoff,)
    ).fetchall()
    deleted = 0
    for row in rows:
        db.execute(
            "DELETE FROM analytics_events WHERE session_id=?",
            (row["sid"],)
        )
        db.execute(
            "DELETE FROM analytics_sessions WHERE id=? AND ended_at IS NOT NULL",
            (row["sid"],)
        )
        deleted += 1
    return deleted


def _percentile(values: list[int], pct: float) -> int:
    """Compute a percentile (0..1) of a list of integers."""
    if not values:
        return 0
    xs = sorted(values)
    if len(xs) == 1:
        return int(xs[0])
    k = (len(xs) - 1) * pct
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return int(xs[f])
    return int(round(xs[f] + (xs[c] - xs[f]) * (k - f)))


def aggregate_daily_summary(db, *, day: Optional[str] = None,
                            invitation_id: Optional[str] = None) -> int:
    """Build / refresh analytics_summary_daily rows.

    Computes one row per (invitation_id, day). Defaults to yesterday's
    UTC day so the day is fully complete; callers may pass an explicit
    ``day`` ('YYYY-MM-DD') or an explicit ``invitation_id`` to scope.

    Returns the count of rows upserted.
    """
    ensure_schema(db)
    now = _now_ms()
    target_day = day or _utc_day(now - 24 * 60 * 60 * 1000)
    # Day boundaries in UTC ms.
    day_start = int(time.mktime(time.strptime(target_day, "%Y-%m-%d"))) * 1000
    day_end = day_start + 24 * 60 * 60 * 1000
    params: list = [day_start, day_end]
    invite_clause = ""
    if invitation_id:
        invite_clause = " AND invitation_id=?"
        params = [invitation_id, day_start, day_end]
    rows = db.execute(
        f"SELECT invitation_id, "
        f"       COUNT(DISTINCT id) AS unique_sessions, "
        f"       COUNT(*) AS total_rows, "
        f"       AVG(duration_ms) AS avg_dur, "
        f"       MAX(max_scroll_pct) AS max_scroll "
        f"FROM analytics_sessions "
        f"WHERE started_at >= ? AND started_at < ?{invite_clause} "
        f"GROUP BY invitation_id",
        params
    ).fetchall()
    upserted = 0
    for row in rows:
        inv_id = row["invitation_id"]
        sessions = db.execute(
            "SELECT id, duration_ms FROM analytics_sessions "
            "WHERE invitation_id=? AND started_at >= ? AND started_at < ?",
            (inv_id, day_start, day_end)
        ).fetchall()
        durations = [int(s["duration_ms"] or 0) for s in sessions if s["duration_ms"] is not None]
        avg_dur = int(sum(durations) / len(durations)) if durations else 0
        p95_dur = _percentile(durations, 0.95)
        # Count event types via the events table.
        event_counts = {}
        for et, key in (
            ("invitation.view", "total_views"),
            ("invitation.rsvp.submit", "rsvp_submitted"),
            ("invitation.rsvp.abandon", "rsvp_abandoned"),
            ("invitation.gallery.open", "gallery_opens"),
            ("invitation.album.upload", "album_uploads"),
        ):
            r = db.execute(
                "SELECT COUNT(*) AS n FROM analytics_events "
                "WHERE invitation_id=? AND event_type=? AND created_at >= ? AND created_at < ?",
                (inv_id, et, day_start, day_end)
            ).fetchone()
            event_counts[key] = int(r["n"] if r else 0)
        db.execute(
            "INSERT OR REPLACE INTO analytics_summary_daily"
            "(invitation_id, day, unique_sessions, total_views, avg_duration_ms, "
            " p95_duration_ms, rsvp_submitted, rsvp_abandoned, gallery_opens, album_uploads) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (inv_id, target_day, int(row["unique_sessions"]),
             event_counts["total_views"], avg_dur, p95_dur,
             event_counts["rsvp_submitted"], event_counts["rsvp_abandoned"],
             event_counts["gallery_opens"], event_counts["album_uploads"])
        )
        upserted += 1
    return upserted


def run_retention_prune(db, retention_days: Optional[int] = None) -> dict:
    """Delete analytics older than the retention window.

    Order: events → sessions → daily summaries. Never deletes a session
    that's still active (no ``ended_at``).

    Returns ``{"events": int, "sessions": int, "summaries": int,
    "retentionDays": int, "cutoffMs": int}``.
    """
    ensure_schema(db)
    days = int(retention_days or os.environ.get("EINVITE_ANALYTICS_RETENTION_DAYS")
               or RETENTION_DEFAULT_DAYS)
    days = max(1, days)
    cutoff = _now_ms() - days * 24 * 60 * 60 * 1000
    e = db.execute(
        "DELETE FROM analytics_events WHERE created_at < ?",
        (cutoff,)
    ).rowcount
    s = db.execute(
        "DELETE FROM analytics_sessions WHERE ended_at IS NOT NULL AND ended_at < ?",
        (cutoff,)
    ).rowcount
    # Daily summaries: prune by the day string. We delete rows whose day
    # string is lexicographically before the cutoff day.
    cutoff_day = _utc_day(cutoff)
    d = db.execute(
        "DELETE FROM analytics_summary_daily WHERE day < ?",
        (cutoff_day,)
    ).rowcount
    return {
        "events": int(e),
        "sessions": int(s),
        "summaries": int(d),
        "retentionDays": days,
        "cutoffMs": int(cutoff),
    }


def run_session_reconstruction(db, *, now_ms: Optional[int] = None) -> dict:
    """Full background pass: close-idle → delete-spam → aggregate → prune.

    Returns a dict of counts suitable for audit logging.
    """
    closed = close_idle_sessions(db, now_ms)
    spam_deleted = delete_spam_sessions(db, now_ms)
    aggregated = aggregate_daily_summary(db)
    pruned = run_retention_prune(db)
    return {
        "closedIdleSessions": closed,
        "deletedSpamSessions": spam_deleted,
        "aggregatedRows": aggregated,
        "pruned": pruned,
    }
