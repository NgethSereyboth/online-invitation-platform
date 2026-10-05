"""settings.py — runtime settings store.

Small key-value configuration that admins can change without a deploy.
Values are stored as TEXT and parsed by the caller. Cached for 60s;
writes invalidate the cache so changes are visible to the next request.
"""
from __future__ import annotations
import threading
import time
from typing import Any, Dict, List, Optional

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at INTEGER NOT NULL,
  updated_by TEXT NOT NULL DEFAULT ''
)""",
]

CACHE_TTL_SECONDS = 60.0

_lock = threading.Lock()
_cache: Optional[Dict[str, Dict[str, Any]]] = None
_cache_at: float = 0.0


def ensure_schema(db) -> None:
    for stmt in SCHEMA_STATEMENTS:
        db.execute(stmt)


def _load_snapshot(db) -> Dict[str, Dict[str, Any]]:
    snap: Dict[str, Dict[str, Any]] = {}
    try:
        rows = db.execute("SELECT key,value,updated_at,updated_by FROM settings").fetchall()
    except Exception:
        rows = []
    for r in rows:
        snap[r["key"]] = {
            "key": r["key"],
            "value": str(r["value"]),
            "updatedAt": int(r["updated_at"] or 0),
            "updatedBy": r["updated_by"] or "",
        }
    return snap


def _snapshot(db) -> Dict[str, Dict[str, Any]]:
    global _cache, _cache_at
    now = time.time()
    with _lock:
        if _cache is None or (now - _cache_at) > CACHE_TTL_SECONDS:
            _cache = _load_snapshot(db)
            _cache_at = now
        return _cache


def invalidate_cache() -> None:
    global _cache, _cache_at
    with _lock:
        _cache = None
        _cache_at = 0.0


def get_setting(db, key: str, default: Optional[str] = None) -> Optional[str]:
    entry = _snapshot(db).get(key)
    return entry["value"] if entry else default


def get_setting_int(db, key: str, default: int) -> int:
    raw = get_setting(db, key, None)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def set_setting(db, key: str, value: str, updated_by: str) -> Dict[str, Any]:
    now = int(time.time() * 1000)
    db.execute(
        "INSERT INTO settings(key,value,updated_at,updated_by) VALUES(?,?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
        (key, str(value), now, str(updated_by or "")[:120]),
    )
    invalidate_cache()
    return {"key": key, "value": str(value), "updatedAt": now, "updatedBy": str(updated_by or "")}


def list_settings(db) -> List[Dict[str, Any]]:
    return [dict(v) for v in _snapshot(db).values()]
