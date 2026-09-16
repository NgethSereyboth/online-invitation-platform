"""features/analytics/export.py — v0.69.0 (ROADMAP-v0.54-to-v1.0 §6.8)

Streamed CSV / JSON export of raw analytics data.

Routes:
    GET /api/invitations/{id}/analytics/export?format=csv|json
    GET /api/account/analytics/export?format=csv|json

CSV:
    UTF-8 BOM (so Excel opens UTF-8 correctly), RFC-4180 quoting.
    One row per session with joined event counts:
      session_id, invitation_id, recipient_id, started_at, ended_at,
      duration_ms, max_scroll_pct, country_code, referrer_domain,
      device_type, view_count, rsvp_open_count, rsvp_submit_count,
      gallery_open_count, album_upload_count, link_click_count

JSON:
    { "invitation": {...}, "sessions": [...], "events": [...] }

The generator functions yield byte chunks suitable for chunked transfer
encoding; the HTTP handler writes them to ``self.wfile`` directly.

Public API
----------
``stream_invitation_csv(db, invitation_id)``
    Generator yielding ``bytes`` chunks.

``stream_invitation_json(db, invitation_id)``
    Generator yielding ``bytes`` chunks (already JSON-encoded).

``stream_account_csv(db, owner_id)``
    Generator yielding ``bytes`` chunks. Concatenates one CSV across
    every invitation owned by the account.

``stream_account_json(db, owner_id)``
    Generator yielding ``bytes`` chunks.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Iterable, Iterator

from .model import ensure_schema


CSV_HEADERS = [
    "session_id", "invitation_id", "recipient_id",
    "started_at", "ended_at", "duration_ms",
    "max_scroll_pct", "country_code", "referrer_domain", "device_type",
    "view_count", "rsvp_open_count", "rsvp_submit_count",
    "gallery_open_count", "album_upload_count", "link_click_count",
]


def _csv_field(value) -> str:
    """RFC-4180 quoting: quote if the field contains comma, quote, newline."""
    s = "" if value is None else str(value)
    if any(c in s for c in (",", '"', "\n", "\r")):
        return '"' + s.replace('"', '""') + '"'
    return s


def _csv_row(values: Iterable) -> str:
    return ",".join(_csv_field(v) for v in values) + "\r\n"


def _event_counts_for_session(db, session_id: str) -> dict:
    """Return counts per event_type for a session."""
    rows = db.execute(
        "SELECT event_type, COUNT(*) AS n FROM analytics_events "
        "WHERE session_id=? GROUP BY event_type",
        (session_id,)
    ).fetchall()
    counts = {r["event_type"]: int(r["n"]) for r in rows}
    return {
        "view": counts.get("invitation.view", 0),
        "rsvp_open": counts.get("invitation.rsvp.open", 0),
        "rsvp_submit": counts.get("invitation.rsvp.submit", 0),
        "gallery_open": counts.get("invitation.gallery.open", 0),
        "album_upload": counts.get("invitation.album.upload", 0),
        "link_click": counts.get("invitation.link.click", 0),
    }


def _sessions_for_invitation(db, invitation_id: str) -> list:
    return db.execute(
        "SELECT id, invitation_id, recipient_id, started_at, ended_at, "
        "       duration_ms, max_scroll_pct, country_code, referrer_domain, device_type "
        "FROM analytics_sessions WHERE invitation_id=? "
        "ORDER BY started_at ASC",
        (invitation_id,)
    ).fetchall()


def _events_for_invitation(db, invitation_id: str) -> list:
    return db.execute(
        "SELECT id, session_id, invitation_id, event_type, payload_json, created_at "
        "FROM analytics_events WHERE invitation_id=? "
        "ORDER BY created_at ASC LIMIT 50000",
        (invitation_id,)
    ).fetchall()


def _invitation_row(db, invitation_id: str) -> dict:
    row = db.execute(
        "SELECT id, slug, is_published, archived, updated_at, draft_json "
        "FROM invitations WHERE id=?",
        (invitation_id,)
    ).fetchone()
    if not row:
        return {"id": invitation_id}
    try:
        doc = json.loads(row["draft_json"] or "{}")
    except Exception:
        doc = {}
    title = (
        doc.get("fields", {}).get("names") or
        doc.get("meta", {}).get("title") or
        "Untitled invitation"
    )
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": title,
        "isPublished": bool(row["is_published"]),
        "archived": bool(row["archived"]),
        "updatedAt": int(row["updated_at"] or 0),
    }


def stream_invitation_csv(db, invitation_id: str) -> Iterator[bytes]:
    """Yield CSV byte chunks for one invitation's analytics."""
    ensure_schema(db)
    yield b"\xef\xbb\xbf"  # UTF-8 BOM
    yield _csv_row(CSV_HEADERS).encode("utf-8")
    sessions = _sessions_for_invitation(db, invitation_id)
    for s in sessions:
        counts = _event_counts_for_session(db, s["id"])
        yield _csv_row([
            s["id"], s["invitation_id"], s["recipient_id"] or "",
            s["started_at"], s["ended_at"] or "",
            s["duration_ms"] or 0,
            s["max_scroll_pct"] or 0,
            s["country_code"] or "",
            s["referrer_domain"] or "",
            s["device_type"] or "",
            counts["view"],
            counts["rsvp_open"],
            counts["rsvp_submit"],
            counts["gallery_open"],
            counts["album_upload"],
            counts["link_click"],
        ]).encode("utf-8")


def stream_invitation_json(db, invitation_id: str) -> Iterator[bytes]:
    """Yield JSON byte chunks for one invitation's analytics."""
    ensure_schema(db)
    invitation = _invitation_row(db, invitation_id)
    sessions = _sessions_for_invitation(db, invitation_id)
    events = _events_for_invitation(db, invitation_id)
    payload = {
        "invitation": invitation,
        "sessions": [
            {
                "id": s["id"],
                "invitationId": s["invitation_id"],
                "recipientId": s["recipient_id"],
                "startedAt": int(s["started_at"] or 0),
                "endedAt": int(s["ended_at"]) if s["ended_at"] is not None else None,
                "durationMs": int(s["duration_ms"] or 0) if s["duration_ms"] is not None else None,
                "maxScrollPct": int(s["max_scroll_pct"] or 0) if s["max_scroll_pct"] is not None else None,
                "countryCode": s["country_code"],
                "referrerDomain": s["referrer_domain"],
                "deviceType": s["device_type"],
            }
            for s in sessions
        ],
        "events": [
            {
                "id": int(e["id"]),
                "sessionId": e["session_id"],
                "invitationId": e["invitation_id"],
                "type": e["event_type"],
                "payload": json.loads(e["payload_json"] or "{}"),
                "createdAt": int(e["created_at"] or 0),
            }
            for e in events
        ],
    }
    yield json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def stream_account_csv(db, owner_id: str) -> Iterator[bytes]:
    """Yield CSV byte chunks for every invitation owned by the account."""
    ensure_schema(db)
    yield b"\xef\xbb\xbf"
    yield _csv_row(CSV_HEADERS).encode("utf-8")
    invitations = db.execute(
        "SELECT id FROM invitations WHERE owner_id=? AND deleted_at IS NULL "
        "ORDER BY updated_at DESC",
        (owner_id,)
    ).fetchall()
    for inv in invitations:
        for chunk in stream_invitation_csv(db, inv["id"]):
            # Skip the BOM + header — already yielded once at the top.
            if chunk == b"\xef\xbb\xbf":
                continue
            try:
                decoded = chunk.decode("utf-8")
            except Exception:
                continue
            if decoded == _csv_row(CSV_HEADERS):
                continue
            yield chunk


def stream_account_json(db, owner_id: str) -> Iterator[bytes]:
    """Yield JSON byte chunks for every invitation owned by the account."""
    ensure_schema(db)
    invitations = db.execute(
        "SELECT id FROM invitations WHERE owner_id=? AND deleted_at IS NULL "
        "ORDER BY updated_at DESC",
        (owner_id,)
    ).fetchall()
    yield b'{"invitations":['
    first = True
    for inv in invitations:
        if not first:
            yield b","
        first = False
        # Stream each invitation's JSON object as a single chunk.
        for chunk in stream_invitation_json(db, inv["id"]):
            yield chunk
    yield b"]}"
