"""features/analytics/model.py — v0.67.0 (ROADMAP-v0.54-to-v1.0 §6.1, §6.2)

Schema + ingestion helpers for first-party creator analytics.

Tables
------
``analytics_sessions``
    id              TEXT PRIMARY KEY        — 128-bit hex (session_id)
    invitation_id   TEXT NOT NULL
    recipient_id    TEXT                     — nullable; opaque guest id
    started_at      INTEGER NOT NULL         — unix ms
    ended_at        INTEGER                  — NULL until view.end received
    duration_ms     INTEGER                  — ended_at - started_at
    max_scroll_pct  INTEGER                  — 0..100
    country_code    TEXT                     — coarse IP-derived, never raw IP
    referrer_domain TEXT                     — normalized, NULL if direct
    device_type     TEXT                     — 'mobile' | 'tablet' | 'desktop'
    created_at      INTEGER NOT NULL

``analytics_events``
    id              INTEGER PRIMARY KEY AUTOINCREMENT
    session_id      TEXT NOT NULL
    invitation_id   TEXT NOT NULL
    event_type      TEXT NOT NULL            — one of EVENT_TYPES
    payload_json    TEXT                     — small; capped at 1KB
    created_at      INTEGER NOT NULL

``analytics_summary_daily``
    invitation_id         TEXT NOT NULL
    day                   TEXT NOT NULL      — 'YYYY-MM-DD'
    unique_sessions       INTEGER NOT NULL
    total_views           INTEGER NOT NULL
    avg_duration_ms       INTEGER NOT NULL
    p95_duration_ms       INTEGER NOT NULL
    rsvp_submitted        INTEGER NOT NULL
    rsvp_abandoned        INTEGER NOT NULL
    gallery_opens         INTEGER NOT NULL
    album_uploads         INTEGER NOT NULL
    PRIMARY KEY (invitation_id, day)

The 11 event types (ROADMAP §6.1):
    invitation.view, invitation.view.end, invitation.gallery.open,
    invitation.rsvp.open, invitation.rsvp.submit, invitation.rsvp.abandon,
    invitation.link.click, invitation.signup.claim, invitation.poll.vote,
    invitation.album.upload, invitation.gift.claim

Public API
----------
``ensure_schema(db)``
    Idempotent CREATE TABLE / CREATE INDEX for the three tables.

``upsert_session(db, session_id, invitation_id, started_at, ...)``
    Insert or update a session row. Called on every ``invitation.view``
    event. Country/referrer/device are derived from request metadata by
    the caller (the HTTP handler) so this module stays DB-only.

``insert_event(db, session_id, invitation_id, event_type, payload, ts)``
    Insert one event row. Validates type. Caps payload JSON at 1KB.

``record_event_batch(db, batch)``
    Validate + persist a full batch from ``POST /api/analytics/events``.
    Returns ``{"sessionId": str, "events": int, "sessionCreated": bool,
    "sessionEnded": bool}``. Updates analytics_sessions if a
    ``invitation.view`` is present, and updates ended_at + duration_ms
    + max_scroll_pct if ``invitation.view.end`` is present.

``list_active_sessions(db, invitation_id, since_ms)``
    Return sessions for an invitation with no ended_at OR ended_at >= since_ms.

``close_session(db, session_id, ended_at, duration_ms, max_scroll_pct)``
    Mark a session as ended (called on ``invitation.view.end`` event and by
    the background ``close_idle_sessions`` job).

``purge_invitation_analytics(db, invitation_id)``
    Delete all sessions + events for an invitation.

``set_invitation_analytics_enabled(db, invitation_id, enabled)``
    Flip the ``analytics_enabled`` column on ``invitations`` (added by this
    version).

``is_invitation_analytics_enabled(db, invitation_id)``
    True if the column is missing OR set to 1.

Validation
----------
- session_id: hex string of length >= 32 (128-bit minimum).
- invitation_id: must exist in ``invitations``.
- event_type: must be one of EVENT_TYPES.
- payload_json: capped at 1024 bytes after json.dumps.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Optional, Iterable

# --- Constants ----------------------------------------------------------

EVENT_TYPES = frozenset({
    "invitation.view",
    "invitation.view.end",
    "invitation.gallery.open",
    "invitation.rsvp.open",
    "invitation.rsvp.submit",
    "invitation.rsvp.abandon",
    "invitation.link.click",
    "invitation.signup.claim",
    "invitation.poll.vote",
    "invitation.album.upload",
    "invitation.gift.claim",
})

SESSION_IDLE_TIMEOUT_MS = 30 * 60 * 1000          # 30 min — close idle sessions
SESSION_SPAM_WINDOW_MS = 24 * 60 * 60 * 1000       # 24h — delete sessions with no events
RETENTION_DEFAULT_DAYS = 365                        # EINVITE_ANALYTICS_RETENTION_DAYS

MAX_EVENTS_PER_BATCH = 20
MAX_PAYLOAD_JSON_BYTES = 1024                       # 1 KB cap per event payload
SESSION_ID_RE = re.compile(r"^[A-Fa-f0-9]{32,}$")  # 128-bit hex minimum

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS analytics_sessions(
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL,
  recipient_id TEXT,
  started_at INTEGER NOT NULL,
  ended_at INTEGER,
  duration_ms INTEGER,
  max_scroll_pct INTEGER,
  country_code TEXT,
  referrer_domain TEXT,
  device_type TEXT,
  created_at INTEGER NOT NULL
)""",
    "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_invitation ON analytics_sessions(invitation_id, started_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_recipient ON analytics_sessions(recipient_id)",
    """CREATE TABLE IF NOT EXISTS analytics_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  invitation_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT,
  created_at INTEGER NOT NULL
)""",
    "CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_events_invitation_type ON analytics_events(invitation_id, event_type, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS analytics_summary_daily(
  invitation_id TEXT NOT NULL,
  day TEXT NOT NULL,
  unique_sessions INTEGER NOT NULL,
  total_views INTEGER NOT NULL,
  avg_duration_ms INTEGER NOT NULL,
  p95_duration_ms INTEGER NOT NULL,
  rsvp_submitted INTEGER NOT NULL,
  rsvp_abandoned INTEGER NOT NULL,
  gallery_opens INTEGER NOT NULL,
  album_uploads INTEGER NOT NULL,
  PRIMARY KEY (invitation_id, day)
)""",
]


# --- Schema -------------------------------------------------------------

def ensure_schema(db) -> None:
    """Create the three analytics tables + indices if missing."""
    for stmt in SCHEMA_STATEMENTS:
        db.execute(stmt)


# --- Helpers ------------------------------------------------------------

def _now_ms() -> int:
    return int(time.time() * 1000)


def _normalize_referrer_domain(value: Optional[str]) -> Optional[str]:
    """Extract the registrable domain from a referrer URL.

    Returns ``None`` for direct traffic (no referrer) or unparseable values.
    The result is the bare hostname (e.g. ``facebook.com``) so referrers are
    aggregated correctly across full URLs.
    """
    if not value:
        return None
    s = str(value).strip().lower()
    if not s or s.startswith("javascript:"):
        return None
    if "://" not in s:
        s = "https://" + s
    try:
        from urllib.parse import urlparse
        host = urlparse(s).hostname or ""
    except Exception:
        host = ""
    if not host or "." not in host:
        return None
    # Strip leading 'www.' for aggregation; keep other subdomains so
    # e.g. m.facebook.com is still distinguishable if needed.
    if host.startswith("www."):
        host = host[4:]
    return host[:160] or None


def _normalize_device_type(value: Optional[str]) -> str:
    """Coerce a User-Agent-derived device class into the canonical enum."""
    if not value:
        return "desktop"
    s = str(value).strip().lower()
    if "mobile" in s or "android" in s or "iphone" in s:
        return "mobile"
    if "tablet" in s or "ipad" in s:
        return "tablet"
    return "desktop"


def _validate_session_id(session_id: Any) -> str:
    if not isinstance(session_id, str):
        raise ValueError("session_id must be a string")
    sid = session_id.strip().lower()
    if not SESSION_ID_RE.match(sid):
        raise ValueError("session_id must be a hex string of length >= 32")
    return sid


def _validate_event_type(event_type: Any) -> str:
    if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
        raise ValueError(f"Unsupported event_type: {event_type!r}")
    return event_type


def _normalize_payload(payload: Any) -> str:
    """Serialize + cap the payload JSON to 1KB."""
    if payload is None:
        payload = {}
    if not isinstance(payload, (dict, list, str, int, float, bool)):
        payload = {}
    s = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(s.encode("utf-8")) > MAX_PAYLOAD_JSON_BYTES:
        # Truncate the JSON rather than refusing the event — losing a bit of
        # payload fidelity is better than dropping the entire event.
        s = s[:MAX_PAYLOAD_JSON_BYTES - 4] + "..."
    return s


# --- Sessions -----------------------------------------------------------

def upsert_session(db, session_id: str, invitation_id: str, *,
                   recipient_id: Optional[str] = None,
                   started_at: int,
                   country_code: Optional[str] = None,
                   referrer_domain: Optional[str] = None,
                   device_type: str = "desktop") -> bool:
    """Insert or update a session row. Returns True if a new row was created.

    On a duplicate session_id (same tab reloaded), we update the started_at
    + context fields but NEVER reopen an ended session.
    """
    sid = _validate_session_id(session_id)
    if not invitation_id:
        raise ValueError("invitation_id is required")
    ref = _normalize_referrer_domain(referrer_domain)
    dev = _normalize_device_type(device_type)
    cc = (str(country_code or "").strip().upper()[:2]) or None
    rid = str(recipient_id).strip()[:120] if recipient_id else None
    existing = db.execute(
        "SELECT id, ended_at FROM analytics_sessions WHERE id=?",
        (sid,)
    ).fetchone()
    if existing is None:
        db.execute(
            "INSERT INTO analytics_sessions"
            "(id, invitation_id, recipient_id, started_at, ended_at, duration_ms, "
            " max_scroll_pct, country_code, referrer_domain, device_type, created_at) "
            "VALUES(?,?,?,?,NULL,NULL,NULL,?,?,?,?)",
            (sid, invitation_id, rid, int(started_at), cc, ref, dev, _now_ms())
        )
        return True
    # Don't reopen an already-ended session — keep the original ended_at.
    if existing["ended_at"] is None:
        db.execute(
            "UPDATE analytics_sessions SET invitation_id=?, recipient_id=?, "
            "started_at=?, country_code=COALESCE(?, country_code), "
            "referrer_domain=COALESCE(?, referrer_domain), device_type=? "
            "WHERE id=? AND ended_at IS NULL",
            (invitation_id, rid, int(started_at), cc, ref, dev, sid)
        )
    return False


def close_session(db, session_id: str, ended_at: int, *,
                  duration_ms: Optional[int] = None,
                  max_scroll_pct: Optional[int] = None) -> bool:
    """Mark a session as ended. Returns True if a row was updated."""
    sid = _validate_session_id(session_id)
    started = db.execute(
        "SELECT started_at FROM analytics_sessions WHERE id=?", (sid,)
    ).fetchone()
    if not started:
        return False
    if duration_ms is None:
        duration_ms = max(0, int(ended_at) - int(started["started_at"]))
    if max_scroll_pct is None:
        # Preserve existing max_scroll_pct if a new one wasn't provided.
        max_scroll_pct = db.execute(
            "SELECT max_scroll_pct FROM analytics_sessions WHERE id=?", (sid,)
        ).fetchone()["max_scroll_pct"]
    db.execute(
        "UPDATE analytics_sessions SET ended_at=?, duration_ms=?, max_scroll_pct=? "
        "WHERE id=? AND ended_at IS NULL",
        (int(ended_at), int(duration_ms), int(max_scroll_pct or 0), sid)
    )
    return True


def insert_event(db, session_id: str, invitation_id: str, *,
                 event_type: str, payload: Any = None, ts: Optional[int] = None) -> int:
    """Insert one event row. Returns the new event id."""
    sid = _validate_session_id(session_id)
    et = _validate_event_type(event_type)
    if not invitation_id:
        raise ValueError("invitation_id is required")
    payload_json = _normalize_payload(payload)
    created_at = int(ts if ts is not None else _now_ms())
    cur = db.execute(
        "INSERT INTO analytics_events"
        "(session_id, invitation_id, event_type, payload_json, created_at) "
        "VALUES(?,?,?,?,?)",
        (sid, invitation_id, et, payload_json, created_at)
    )
    return int(cur.lastrowid if hasattr(cur, "lastrowid") else 0)


def record_event_batch(db, *, session_id: str, invitation_id: str,
                       events: Iterable[dict],
                       recipient_id: Optional[str] = None,
                       country_code: Optional[str] = None,
                       referrer_domain: Optional[str] = None,
                       device_type: str = "desktop") -> dict:
    """Validate + persist a batch of events from POST /api/analytics/events.

    Returns ``{"sessionId": str, "events": int, "sessionCreated": bool,
    "sessionEnded": bool}``. Idempotent: invalid events are skipped; the
    batch transaction is the caller's responsibility (``server.py`` wraps
    ``connect()`` which commits on success).
    """
    sid = _validate_session_id(session_id)
    if not invitation_id:
        raise ValueError("invitation_id is required")
    events = list(events or [])[:MAX_EVENTS_PER_BATCH]
    if not events:
        return {"sessionId": sid, "events": 0, "sessionCreated": False, "sessionEnded": False}
    session_created = False
    session_ended = False
    inserted = 0
    for ev in events:
        if not isinstance(ev, dict):
            continue
        et = ev.get("type")
        try:
            et_valid = _validate_event_type(et)
        except ValueError:
            continue
        ts = int(ev.get("ts") or _now_ms())
        payload = ev.get("payload") or {}
        if et_valid == "invitation.view":
            session_created = upsert_session(
                db, sid, invitation_id,
                recipient_id=recipient_id,
                started_at=ts,
                country_code=country_code,
                referrer_domain=payload.get("referrer") or referrer_domain,
                device_type=payload.get("viewport") or device_type,
            )
            # When the session was just created we capture the recipient_id
            # from the payload too (the public page sends it as a query param).
            if not session_created and recipient_id:
                db.execute(
                    "UPDATE analytics_sessions SET recipient_id=COALESCE(?, recipient_id) "
                    "WHERE id=? AND recipient_id IS NULL",
                    (str(recipient_id).strip()[:120] or None, sid)
                )
        elif et_valid == "invitation.view.end":
            p = payload or {}
            duration_ms = p.get("duration_ms")
            max_scroll = p.get("max_scroll_pct") or p.get("scroll_depth_pct")
            session_ended = close_session(
                db, sid, ts,
                duration_ms=int(duration_ms) if duration_ms is not None else None,
                max_scroll_pct=int(max_scroll) if max_scroll is not None else None,
            )
        # Insert the event row (even for view.end; clients may want raw events).
        try:
            insert_event(
                db, sid, invitation_id,
                event_type=et_valid, payload=payload, ts=ts,
            )
            inserted += 1
        except ValueError:
            continue
    return {
        "sessionId": sid,
        "events": inserted,
        "sessionCreated": bool(session_created),
        "sessionEnded": bool(session_ended),
    }


def list_active_sessions(db, invitation_id: str, since_ms: int) -> list[dict]:
    """Return sessions for an invitation with no ended_at OR ended_at >= since_ms."""
    ensure_schema(db)
    rows = db.execute(
        "SELECT id, started_at, ended_at, duration_ms, max_scroll_pct, "
        "       country_code, referrer_domain, device_type "
        "FROM analytics_sessions "
        "WHERE invitation_id=? AND (ended_at IS NULL OR ended_at >= ?) "
        "ORDER BY started_at DESC",
        (invitation_id, int(since_ms))
    ).fetchall()
    return [dict(r) for r in rows]


def purge_invitation_analytics(db, invitation_id: str) -> dict:
    """Delete all sessions + events for an invitation.

    Returns ``{"sessionsDeleted": int, "eventsDeleted": int}``.
    Used by the host "Delete my analytics data" button (§6.8).
    """
    ensure_schema(db)
    e = db.execute(
        "DELETE FROM analytics_events WHERE invitation_id=?",
        (invitation_id,)
    ).rowcount
    s = db.execute(
        "DELETE FROM analytics_sessions WHERE invitation_id=?",
        (invitation_id,)
    ).rowcount
    db.execute(
        "DELETE FROM analytics_summary_daily WHERE invitation_id=?",
        (invitation_id,)
    )
    return {"sessionsDeleted": int(s), "eventsDeleted": int(e)}


def set_invitation_analytics_enabled(db, invitation_id: str, enabled: bool) -> bool:
    """Set ``invitations.analytics_enabled`` (column added by this version)."""
    try:
        cols = {row["name"] for row in db.execute("PRAGMA table_info(invitations)")}
    except Exception:
        cols = set()
    if "analytics_enabled" not in cols:
        db.execute(
            "ALTER TABLE invitations ADD COLUMN analytics_enabled INTEGER NOT NULL DEFAULT 1"
        )
    changed = db.execute(
        "UPDATE invitations SET analytics_enabled=? WHERE id=?",
        (1 if enabled else 0, invitation_id)
    ).rowcount
    return bool(changed)


def is_invitation_analytics_enabled(db, invitation_id: str) -> bool:
    """True if the per-invitation flag is missing OR set to 1."""
    try:
        row = db.execute(
            "SELECT analytics_enabled FROM invitations WHERE id=?",
            (invitation_id,)
        ).fetchone()
    except Exception:
        return True  # column missing — default to enabled
    if not row:
        return True
    try:
        return int(row["analytics_enabled"]) != 0
    except Exception:
        return True
