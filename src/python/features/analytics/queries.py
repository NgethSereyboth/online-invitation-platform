"""features/analytics/queries.py — v0.68.0 (ROADMAP-v0.54-to-v1.0 §6.5)

Read-side queries for the creator analytics dashboard.

Every function is read-only (no schema writes, no audit). All return
plain JSON-serializable dicts so the HTTP handlers can pass them
straight through to ``self.json(200, ...)``.

The dashboard response shape (§6.5):

    {
      "stats": {
        "totalViews": int,            # count of sessions
        "uniqueRecipients": int,      # distinct recipient_id
        "avgDurationMs": int,         # mean session duration
        "rsvpConversion": float,      # submitted / opened × 100
        "deltas": {                   # delta vs previous 7 days (signed)
          "totalViews": float,
          "uniqueRecipients": float,
          "avgDurationMs": float,
          "rsvpConversion": float
        }
      },
      "timeseries": {                  # 30-day line chart (and RSVP overlay)
        "days": ["YYYY-MM-DD", ...],
        "views": [int, ...],
        "rsvps": [int, ...]
      },
      "funnel": [
        {"step": "view", "count": int, "pct": float},
        {"step": "rsvp.open", "count": int, "pct": float},
        {"step": "rsvp.submit", "count": int, "pct": float}
      ],
      "topReferrers": [                # masks <3 as "Other"
        {"domain": str, "count": int}
      ],
      "scrollDepth": {                 # horizontal bar 0..100%
        "average": float,
        "buckets": [{"pct": int, "count": int}]
      },
      "deviceSplit": [                 # donut chart
        {"label": str, "value": int, "color": str}
      ],
      "countrySplit": [                # top 5 list
        {"code": str, "count": int}
      ]
    }

The creations table (§6.5 fifth row) is returned by
``account_creations_table`` and supports sort + filter on the
server side so large accounts stay responsive.
"""
from __future__ import annotations

import time
from typing import Optional

from .model import ensure_schema, EVENT_TYPES


def _now_ms() -> int:
    return int(time.time() * 1000)


def _extract_event_date(doc: dict) -> int:
    """Best-effort extraction of the event date from the document JSON.

    The invitation document schema stores the event date under various
    paths depending on the version (fields.eventDate, meta.eventDate,
    settings.eventDate). Returns 0 if not found.
    """
    if not isinstance(doc, dict):
        return 0
    candidates = (
        doc.get("fields", {}).get("eventDate"),
        doc.get("meta", {}).get("eventDate"),
        doc.get("settings", {}).get("eventDate"),
        doc.get("eventDate"),
    )
    for v in candidates:
        if v:
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
    return 0


def _utc_day(ts_ms: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts_ms / 1000))


def _last_n_days(now_ms: int, n: int) -> list[str]:
    """Return the last ``n`` day strings (UTC), oldest first."""
    out = []
    for i in range(n - 1, -1, -1):
        out.append(_utc_day(now_ms - i * 24 * 60 * 60 * 1000))
    return out


def invitation_analytics_summary(db, invitation_id: str, *, days: int = 30) -> dict:
    """Top-level dashboard response for a single invitation."""
    ensure_schema(db)
    days = max(1, min(days, 365))
    now = _now_ms()
    period_start = now - days * 24 * 60 * 60 * 1000
    prev_start = period_start - days * 24 * 60 * 60 * 1000

    # ---- 4 stat cards (current + previous period for delta) ----------
    def _period_stats(start: int, end: int) -> dict:
        rows = db.execute(
            "SELECT id, recipient_id, duration_ms, max_scroll_pct "
            "FROM analytics_sessions "
            "WHERE invitation_id=? AND started_at>=? AND started_at<?",
            (invitation_id, start, end)
        ).fetchall()
        total_views = len(rows)
        unique_recipients = len({r["recipient_id"] for r in rows if r["recipient_id"]})
        durations = [int(r["duration_ms"] or 0) for r in rows if r["duration_ms"] is not None]
        avg_dur = int(sum(durations) / len(durations)) if durations else 0
        rsvp_open = db.execute(
            "SELECT COUNT(*) AS n FROM analytics_events "
            "WHERE invitation_id=? AND event_type='invitation.rsvp.open' "
            "  AND created_at>=? AND created_at<?",
            (invitation_id, start, end)
        ).fetchone()["n"]
        rsvp_submit = db.execute(
            "SELECT COUNT(*) AS n FROM analytics_events "
            "WHERE invitation_id=? AND event_type='invitation.rsvp.submit' "
            "  AND created_at>=? AND created_at<?",
            (invitation_id, start, end)
        ).fetchone()["n"]
        rsvp_conv = round((rsvp_submit / rsvp_open) * 100, 1) if rsvp_open else 0.0
        return {
            "totalViews": total_views,
            "uniqueRecipients": unique_recipients,
            "avgDurationMs": avg_dur,
            "rsvpConversion": rsvp_conv,
        }
    cur = _period_stats(period_start, now)
    prev = _period_stats(prev_start, period_start)

    def _delta(c: int | float, p: int | float) -> float:
        if not p:
            return 100.0 if c else 0.0
        return round(((c - p) / p) * 100, 1)

    deltas = {
        "totalViews": _delta(cur["totalViews"], prev["totalViews"]),
        "uniqueRecipients": _delta(cur["uniqueRecipients"], prev["uniqueRecipients"]),
        "avgDurationMs": _delta(cur["avgDurationMs"], prev["avgDurationMs"]),
        "rsvpConversion": round(cur["rsvpConversion"] - prev["rsvpConversion"], 1),
    }

    # ---- 30-day time-series (views + RSVPs overlay) -----------------
    days_list = _last_n_days(now, days)
    ts_rows = db.execute(
        "SELECT event_type, created_at FROM analytics_events "
        "WHERE invitation_id=? AND created_at>=? "
        "  AND event_type IN ('invitation.view', 'invitation.rsvp.submit')",
        (invitation_id, period_start)
    ).fetchall()
    views_by_day = {d: 0 for d in days_list}
    rsvps_by_day = {d: 0 for d in days_list}
    for r in ts_rows:
        day = _utc_day(int(r["created_at"]))
        if day in views_by_day:
            if r["event_type"] == "invitation.view":
                views_by_day[day] += 1
            elif r["event_type"] == "invitation.rsvp.submit":
                rsvps_by_day[day] += 1

    # ---- Drop-off funnel -------------------------------------------
    funnel_view = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events "
        "WHERE invitation_id=? AND event_type='invitation.view'",
        (invitation_id,)
    ).fetchone()["n"]
    funnel_rsvp_open = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events "
        "WHERE invitation_id=? AND event_type='invitation.rsvp.open'",
        (invitation_id,)
    ).fetchone()["n"]
    funnel_rsvp_submit = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events "
        "WHERE invitation_id=? AND event_type='invitation.rsvp.submit'",
        (invitation_id,)
    ).fetchone()["n"]
    base = max(1, funnel_view)
    funnel = [
        {"step": "view", "count": int(funnel_view),
         "pct": round(100.0, 1)},
        {"step": "rsvp.open", "count": int(funnel_rsvp_open),
         "pct": round((funnel_rsvp_open / base) * 100, 1)},
        {"step": "rsvp.submit", "count": int(funnel_rsvp_submit),
         "pct": round((funnel_rsvp_submit / base) * 100, 1)},
    ]

    # ---- Top referrers (mask <3 as "Other") --------------------------
    ref_rows = db.execute(
        "SELECT referrer_domain, COUNT(*) AS n "
        "FROM analytics_sessions "
        "WHERE invitation_id=? AND referrer_domain IS NOT NULL AND referrer_domain<>'' "
        "GROUP BY referrer_domain ORDER BY n DESC",
        (invitation_id,)
    ).fetchall()
    top_refs = []
    other_count = 0
    for r in ref_rows:
        if int(r["n"]) < 3:
            other_count += int(r["n"])
        else:
            top_refs.append({"domain": r["referrer_domain"], "count": int(r["n"])})
    if other_count:
        top_refs.append({"domain": "Other", "count": other_count})

    # ---- Scroll depth (avg + buckets 0-25 / 25-50 / 50-75 / 75-100) -
    scroll_rows = db.execute(
        "SELECT max_scroll_pct FROM analytics_sessions "
        "WHERE invitation_id=? AND max_scroll_pct IS NOT NULL",
        (invitation_id,)
    ).fetchall()
    scrolls = [int(r["max_scroll_pct"]) for r in scroll_rows]
    avg_scroll = round(sum(scrolls) / len(scrolls), 1) if scrolls else 0.0
    buckets = [
        {"pct": 25, "count": sum(1 for s in scrolls if s < 25)},
        {"pct": 50, "count": sum(1 for s in scrolls if 25 <= s < 50)},
        {"pct": 75, "count": sum(1 for s in scrolls if 50 <= s < 75)},
        {"pct": 100, "count": sum(1 for s in scrolls if s >= 75)},
    ]

    # ---- Device split (donut) ----------------------------------------
    dev_rows = db.execute(
        "SELECT device_type, COUNT(*) AS n "
        "FROM analytics_sessions WHERE invitation_id=? "
        "GROUP BY device_type",
        (invitation_id,)
    ).fetchall()
    dev_colors = {"mobile": "#3b82f6", "tablet": "#a855f7", "desktop": "#10b981"}
    dev_total = sum(int(r["n"]) for r in dev_rows) or 1
    device_split = [
        {"label": (r["device_type"] or "desktop"),
         "value": int(r["n"]),
         "color": dev_colors.get(r["device_type"], "#64748b")}
        for r in dev_rows
    ]
    if not device_split:
        device_split = [{"label": "desktop", "value": 0, "color": dev_colors["desktop"]}]

    # ---- Country split (top 5) ---------------------------------------
    country_rows = db.execute(
        "SELECT country_code, COUNT(*) AS n "
        "FROM analytics_sessions "
        "WHERE invitation_id=? AND country_code IS NOT NULL AND country_code<>'' "
        "GROUP BY country_code ORDER BY n DESC LIMIT 5",
        (invitation_id,)
    ).fetchall()
    country_split = [{"code": r["country_code"], "count": int(r["n"])} for r in country_rows]

    return {
        "stats": {**cur, "deltas": deltas},
        "timeseries": {
            "days": days_list,
            "views": [views_by_day.get(d, 0) for d in days_list],
            "rsvps": [rsvps_by_day.get(d, 0) for d in days_list],
        },
        "funnel": funnel,
        "topReferrers": top_refs,
        "scrollDepth": {"average": avg_scroll, "buckets": buckets},
        "deviceSplit": device_split,
        "countrySplit": country_split,
        "deviceTotal": dev_total,
    }


def invitation_analytics_timeseries(db, invitation_id: str, *, days: int = 30) -> dict:
    """Standalone 30/90-day time-series endpoint (used by chart toggle)."""
    ensure_schema(db)
    days = max(1, min(days, 365))
    now = _now_ms()
    period_start = now - days * 24 * 60 * 60 * 1000
    days_list = _last_n_days(now, days)
    rows = db.execute(
        "SELECT event_type, created_at FROM analytics_events "
        "WHERE invitation_id=? AND created_at>=? "
        "  AND event_type IN ('invitation.view', 'invitation.rsvp.submit')",
        (invitation_id, period_start)
    ).fetchall()
    views_by_day = {d: 0 for d in days_list}
    rsvps_by_day = {d: 0 for d in days_list}
    for r in rows:
        day = _utc_day(int(r["created_at"]))
        if day in views_by_day:
            if r["event_type"] == "invitation.view":
                views_by_day[day] += 1
            elif r["event_type"] == "invitation.rsvp.submit":
                rsvps_by_day[day] += 1
    return {
        "days": days_list,
        "views": [views_by_day.get(d, 0) for d in days_list],
        "rsvps": [rsvps_by_day.get(d, 0) for d in days_list],
    }


def invitation_top_referrers(db, invitation_id: str) -> list[dict]:
    ensure_schema(db)
    rows = db.execute(
        "SELECT referrer_domain, COUNT(*) AS n "
        "FROM analytics_sessions "
        "WHERE invitation_id=? AND referrer_domain IS NOT NULL AND referrer_domain<>'' "
        "GROUP BY referrer_domain ORDER BY n DESC",
        (invitation_id,)
    ).fetchall()
    out = []
    other = 0
    for r in rows:
        if int(r["n"]) < 3:
            other += int(r["n"])
        else:
            out.append({"domain": r["referrer_domain"], "count": int(r["n"])})
    if other:
        out.append({"domain": "Other", "count": other})
    return out


def invitation_device_split(db, invitation_id: str) -> list[dict]:
    ensure_schema(db)
    rows = db.execute(
        "SELECT device_type, COUNT(*) AS n "
        "FROM analytics_sessions WHERE invitation_id=? GROUP BY device_type",
        (invitation_id,)
    ).fetchall()
    dev_colors = {"mobile": "#3b82f6", "tablet": "#a855f7", "desktop": "#10b981"}
    return [
        {"label": (r["device_type"] or "desktop"),
         "value": int(r["n"]),
         "color": dev_colors.get(r["device_type"], "#64748b")}
        for r in rows
    ]


def invitation_country_split(db, invitation_id: str, *, limit: int = 5) -> list[dict]:
    ensure_schema(db)
    rows = db.execute(
        "SELECT country_code, COUNT(*) AS n "
        "FROM analytics_sessions "
        "WHERE invitation_id=? AND country_code IS NOT NULL AND country_code<>'' "
        "GROUP BY country_code ORDER BY n DESC LIMIT ?",
        (invitation_id, int(limit))
    ).fetchall()
    return [{"code": r["country_code"], "count": int(r["n"])} for r in rows]


def invitation_funnel(db, invitation_id: str) -> list[dict]:
    ensure_schema(db)
    view = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events "
        "WHERE invitation_id=? AND event_type='invitation.view'",
        (invitation_id,)
    ).fetchone()["n"]
    rsvp_open = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events "
        "WHERE invitation_id=? AND event_type='invitation.rsvp.open'",
        (invitation_id,)
    ).fetchone()["n"]
    rsvp_submit = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS n FROM analytics_events "
        "WHERE invitation_id=? AND event_type='invitation.rsvp.submit'",
        (invitation_id,)
    ).fetchone()["n"]
    base = max(1, view)
    return [
        {"step": "view", "count": int(view), "pct": round(100.0, 1)},
        {"step": "rsvp.open", "count": int(rsvp_open), "pct": round((rsvp_open / base) * 100, 1)},
        {"step": "rsvp.submit", "count": int(rsvp_submit), "pct": round((rsvp_submit / base) * 100, 1)},
    ]


def invitation_scroll_depth(db, invitation_id: str) -> dict:
    ensure_schema(db)
    rows = db.execute(
        "SELECT max_scroll_pct FROM analytics_sessions "
        "WHERE invitation_id=? AND max_scroll_pct IS NOT NULL",
        (invitation_id,)
    ).fetchall()
    scrolls = [int(r["max_scroll_pct"]) for r in rows]
    avg = round(sum(scrolls) / len(scrolls), 1) if scrolls else 0.0
    return {
        "average": avg,
        "buckets": [
            {"pct": 25, "count": sum(1 for s in scrolls if s < 25)},
            {"pct": 50, "count": sum(1 for s in scrolls if 25 <= s < 50)},
            {"pct": 75, "count": sum(1 for s in scrolls if 50 <= s < 75)},
            {"pct": 100, "count": sum(1 for s in scrolls if s >= 75)},
        ],
    }


def invitation_live_activity(db, invitation_id: str) -> dict:
    """Return active sessions + last event timestamp for live polling."""
    ensure_schema(db)
    now = _now_ms()
    cutoff = now - 5 * 60 * 1000  # active = had an event in last 5 min
    active = db.execute(
        "SELECT COUNT(DISTINCT s.id) AS n "
        "FROM analytics_sessions s "
        "LEFT JOIN analytics_events e ON e.session_id = s.id "
        "WHERE s.invitation_id=? AND (s.ended_at IS NULL OR s.ended_at >= ?) "
        "  AND (e.created_at IS NULL OR e.created_at >= ?)",
        (invitation_id, cutoff, cutoff)
    ).fetchone()
    last = db.execute(
        "SELECT MAX(created_at) AS last FROM analytics_events WHERE invitation_id=?",
        (invitation_id,)
    ).fetchone()
    return {
        "activeSessions": int(active["n"] if active and active["n"] is not None else 0),
        "lastEventAt": int(last["last"]) if last and last["last"] is not None else None,
    }


def account_creations_table(db, owner_id: str, *,
                             sort: str = "updatedAt",
                             order: str = "desc",
                             status_filter: Optional[str] = None,
                             date_from: Optional[int] = None,
                             date_to: Optional[int] = None,
                             limit: int = 100,
                             offset: int = 0) -> dict:
    """The per-account creations table (§6.5 fifth row)."""
    ensure_schema(db)
    sort_map = {
        "title": "title",
        "eventDate": "event_date",
        "status": "status",
        "views": "views",
        "avgDurationMs": "avg_dur",
        "rsvps": "rsvps",
        "conversion": "conversion",
        "updatedAt": "updated_at",
    }
    sort_col = sort_map.get(sort, "updated_at")
    if order.lower() == "asc":
        order_dir = "ASC"
    else:
        order_dir = "DESC"
    where = ["i.owner_id=?", "i.deleted_at IS NULL"]
    params: list = [owner_id]
    if status_filter in ("draft", "published", "archived"):
        if status_filter == "draft":
            where.append("i.is_published=0")
            where.append("i.archived=0")
        elif status_filter == "published":
            where.append("i.is_published=1")
            where.append("i.archived=0")
        elif status_filter == "archived":
            where.append("i.archived=1")
    if date_from:
        where.append("i.updated_at>=?")
        params.append(int(date_from))
    if date_to:
        where.append("i.updated_at<=?")
        params.append(int(date_to))
    where_clause = " AND ".join(where)
    # Aggregate analytics per invitation in one query.
    sql = (
        "SELECT i.id AS id, i.slug AS slug, i.draft_json AS draft_json, "
        "       i.is_published AS is_published, i.archived AS archived, "
        "       i.updated_at AS updated_at, "
        "       COALESCE(a.views, 0) AS views, "
        "       COALESCE(a.avg_dur, 0) AS avg_dur, "
        "       COALESCE(a.rsvps, 0) AS rsvps, "
        "       CASE WHEN a.views > 0 THEN "
        "         ROUND(100.0 * a.rsvps / a.views, 1) ELSE 0.0 END AS conversion, "
        "       a.last_activity AS last_activity "
        "FROM invitations i "
        "LEFT JOIN ("
        "  SELECT s.invitation_id AS invitation_id, "
        "         COUNT(DISTINCT s.id) AS views, "
        "         AVG(s.duration_ms) AS avg_dur, "
        "         SUM(CASE WHEN e.event_type='invitation.rsvp.submit' THEN 1 ELSE 0 END) AS rsvps, "
        "         MAX(e.created_at) AS last_activity "
        "  FROM analytics_sessions s "
        "  LEFT JOIN analytics_events e ON e.session_id = s.id "
        "  GROUP BY s.invitation_id"
        ") a ON a.invitation_id = i.id "
        f"WHERE {where_clause} "
        f"ORDER BY {sort_col} {order_dir} LIMIT ? OFFSET ?"
    )
    params.append(int(limit))
    params.append(int(offset))
    rows = db.execute(sql, params).fetchall()
    items = []
    for r in rows:
        try:
            doc = r["draft_json"] and __import__("json").loads(r["draft_json"]) or {}
        except Exception:
            doc = {}
        title = (
            doc.get("fields", {}).get("names") or
            doc.get("meta", {}).get("title") or
            "Untitled invitation"
        )
        status = "archived" if r["archived"] else ("published" if r["is_published"] else "draft")
        items.append({
            "id": r["id"],
            "slug": r["slug"],
            "title": title,
            "eventDate": int(_extract_event_date(doc) or 0),
            "status": status,
            "views": int(r["views"] or 0),
            "avgDurationMs": int(r["avg_dur"] or 0),
            "rsvps": int(r["rsvps"] or 0),
            "conversion": float(r["conversion"] or 0.0),
            "lastActivity": int(r["last_activity"] or 0),
            "updatedAt": int(r["updated_at"] or 0),
        })
    return {
        "items": items,
        "sort": sort,
        "order": order_dir.lower(),
        "limit": int(limit),
        "offset": int(offset),
        "count": len(items),
    }


def account_analytics_summary(db, owner_id: str) -> dict:
    """Account-level rollup (§6.5 — GET /api/account/analytics/summary)."""
    ensure_schema(db)
    rows = db.execute(
        "SELECT i.id AS id, "
        "       COALESCE(a.views, 0) AS views, "
        "       COALESCE(a.rsvps, 0) AS rsvps "
        "FROM invitations i "
        "LEFT JOIN ("
        "  SELECT s.invitation_id AS invitation_id, "
        "         COUNT(DISTINCT s.id) AS views, "
        "         SUM(CASE WHEN e.event_type='invitation.rsvp.submit' THEN 1 ELSE 0 END) AS rsvps "
        "  FROM analytics_sessions s "
        "  LEFT JOIN analytics_events e ON e.session_id = s.id "
        "  GROUP BY s.invitation_id"
        ") a ON a.invitation_id = i.id "
        "WHERE i.owner_id=? AND i.deleted_at IS NULL",
        (owner_id,)
    ).fetchall()
    total_invitations = len(rows)
    total_views = sum(int(r["views"] or 0) for r in rows)
    total_rsvps = sum(int(r["rsvps"] or 0) for r in rows)
    avg_views = round(total_views / total_invitations, 1) if total_invitations else 0.0
    return {
        "totalInvitations": total_invitations,
        "totalViews": total_views,
        "totalRsvps": total_rsvps,
        "averageViewsPerInvitation": avg_views,
        "accountConversion": round((total_rsvps / total_views) * 100, 1) if total_views else 0.0,
    }
