"""reports.py — v0.66.0 (ROADMAP-v0.54-to-v1.0 §5.9)

User-facing abuse reports + admin queue.

A user reports an abusive invitation or another user. Admins see a queue and
resolve each report. Resolving a report writes an audit event linking the
report to the action taken.

Tables
------
``reports``
    id              TEXT PRIMARY KEY
    reporter_id     TEXT NOT NULL
    target_type     TEXT NOT NULL  -- 'invitation' | 'user'
    target_id       TEXT NOT NULL
    reason          TEXT NOT NULL  -- spam | harassment | impersonation | illegal_content | other
    body            TEXT NOT NULL DEFAULT ''
    status          TEXT NOT NULL DEFAULT 'open'
                                    -- open | investigating | resolved_actioned | resolved_no_action | duplicate
    resolved_by     TEXT
    resolved_at     INTEGER
    resolution_note TEXT NOT NULL DEFAULT ''
    created_at      INTEGER NOT NULL

Public API
----------
``REASON_VALUES``         — tuple of allowed reasons
``STATUS_VALUES``         — tuple of allowed statuses
``ensure_schema(db)``
``create_report(db, reporter_id, target_type, target_id, reason, body)``
``list_reports(db, status=None, target_type=None, limit=100, cursor=None)``
``get_report(db, report_id)``
``resolve_report(db, report_id, status, resolved_by, resolution_note)``
``count_reports_by_reporter_24h(db, reporter_id)``
"""
from __future__ import annotations
import time
import uuid
from typing import Any, List, Optional, Tuple


SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS reports(
  id TEXT PRIMARY KEY,
  reporter_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open',
  resolved_by TEXT,
  resolved_at INTEGER,
  resolution_note TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
)""",
    "CREATE INDEX IF NOT EXISTS idx_reports_status_created ON reports(status,created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_reports_target ON reports(target_type,target_id,created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_reports_reporter ON reports(reporter_id,created_at DESC)",
]

REASON_VALUES: Tuple[str, ...] = (
    "spam", "harassment", "impersonation", "illegal_content", "other",
)

STATUS_VALUES: Tuple[str, ...] = (
    "open", "investigating", "resolved_actioned", "resolved_no_action", "duplicate",
)

RESOLVED_STATUSES: Tuple[str, ...] = (
    "resolved_actioned", "resolved_no_action", "duplicate",
)


def ensure_schema(db) -> None:
    for stmt in SCHEMA_STATEMENTS:
        db.execute(stmt)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _validate_reason(reason: str) -> str:
    reason = str(reason or "").strip().lower()
    if reason not in REASON_VALUES:
        raise ValueError(f"Invalid report reason; must be one of: {', '.join(REASON_VALUES)}")
    return reason


def _validate_target_type(target_type: str) -> str:
    target_type = str(target_type or "").strip().lower()
    if target_type not in {"invitation", "user"}:
        raise ValueError("target_type must be 'invitation' or 'user'")
    return target_type


def create_report(db, reporter_id: str, target_type: str, target_id: str, reason: str, body: str) -> Dict[str, Any]:
    if not reporter_id:
        raise ValueError("reporter_id is required")
    target_type = _validate_target_type(target_type)
    target_id = str(target_id or "").strip()
    if not target_id:
        raise ValueError("target_id is required")
    reason = _validate_reason(reason)
    body = str(body or "")[:4000]
    report_id = str(uuid.uuid4())
    now = _now_ms()
    db.execute(
        "INSERT INTO reports(id,reporter_id,target_type,target_id,reason,body,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (report_id, reporter_id, target_type, target_id, reason, body, "open", now),
    )
    return {
        "id": report_id,
        "reporterId": reporter_id,
        "targetType": target_type,
        "targetId": target_id,
        "reason": reason,
        "body": body,
        "status": "open",
        "createdAt": now,
    }


def list_reports(db, status: Optional[str] = None, target_type: Optional[str] = None,
                 limit: int = 100, cursor: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    limit = max(1, min(int(limit or 100), 200))
    params: List[Any] = []
    clauses: List[str] = []
    if status:
        clauses.append("status=?"); params.append(status)
    if target_type:
        clauses.append("target_type=?"); params.append(target_type)
    if cursor:
        clauses.append("created_at<?"); params.append(int(cursor))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    rows = db.execute(
        f"SELECT id,reporter_id,target_type,target_id,reason,body,status,resolved_by,resolved_at,resolution_note,created_at "
        f"FROM reports{where} ORDER BY created_at DESC LIMIT ?",
        tuple(params),
    ).fetchall()
    items = [_row_to_dict(r) for r in rows]
    next_cursor = items[-1]["createdAt"] if len(items) >= limit else None
    return items, next_cursor


def get_report(db, report_id: str) -> Optional[Dict[str, Any]]:
    row = db.execute(
        "SELECT id,reporter_id,target_type,target_id,reason,body,status,resolved_by,resolved_at,resolution_note,created_at "
        "FROM reports WHERE id=?",
        (report_id,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def resolve_report(db, report_id: str, status: str, resolved_by: str, resolution_note: str = "") -> Dict[str, Any]:
    status = str(status or "").strip().lower()
    if status not in STATUS_VALUES:
        raise ValueError(f"Invalid report status; must be one of: {', '.join(STATUS_VALUES)}")
    now = _now_ms()
    changed = db.execute(
        "UPDATE reports SET status=?,resolved_by=?,resolved_at=?,resolution_note=? WHERE id=?",
        (status, str(resolved_by or "")[:120], now, str(resolution_note or "")[:2000], report_id),
    ).rowcount
    if not changed:
        raise LookupError("Report not found")
    report = get_report(db, report_id) or {}
    return {**report, "status": status, "resolvedBy": resolved_by, "resolvedAt": now, "resolutionNote": resolution_note}


def count_reports_by_reporter_24h(db, reporter_id: str) -> int:
    cutoff = _now_ms() - 24 * 60 * 60 * 1000
    row = db.execute(
        "SELECT COUNT(*) c FROM reports WHERE reporter_id=? AND created_at>=?",
        (reporter_id, cutoff),
    ).fetchone()
    return int(row["c"] if row else 0)


def _row_to_dict(r) -> Dict[str, Any]:
    return {
        "id": r["id"],
        "reporterId": r["reporter_id"],
        "targetType": r["target_type"],
        "targetId": r["target_id"],
        "reason": r["reason"],
        "body": r["body"],
        "status": r["status"],
        "resolvedBy": r["resolved_by"] or "",
        "resolvedAt": r["resolved_at"],
        "resolutionNote": r["resolution_note"] or "",
        "createdAt": r["created_at"],
    }
