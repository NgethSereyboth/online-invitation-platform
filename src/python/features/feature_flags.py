"""feature_flags.py — v0.64.3 (ROADMAP-v0.54-to-v1.0 §5.4)

Feature-flag store + 60s in-memory cache.

A ``feature_flags`` table overrides the defaults defined in code. The cache
holds the full flag snapshot for at most ``CACHE_TTL_SECONDS``; reads are O(1)
after the first DB hit. Writes invalidate the cache so an admin toggle is
visible to the next request.

Public API
----------
``DEFAULT_FLAGS``  — ``{key: {"value": bool, "description": str, "tier": str|None}}``
``ensure_schema(db)``
``get_flag(db, key)``              — single flag (with default fallback)
``list_flags(db)``                  — all flags as ``[{key,value,description,updatedAt,updatedBy}]``
``public_flags_for_tier(db, tier)`` — only flags whose ``tier`` matches ``None`` or the caller's tier
``set_flag(db, key, value, updated_by, description=None)``
``invalidate_cache()``
``is_enabled(db, key)``             — convenience bool getter

Schema
------
``feature_flags(key TEXT PRIMARY KEY, value INTEGER NOT NULL, description TEXT NOT NULL DEFAULT '', tier TEXT, updated_at INTEGER NOT NULL, updated_by TEXT NOT NULL DEFAULT '')``
"""
from __future__ import annotations
import threading
import time
from typing import Any, Dict, List, Optional


SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS feature_flags(
  key TEXT PRIMARY KEY,
  value INTEGER NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  tier TEXT,
  updated_at INTEGER NOT NULL,
  updated_by TEXT NOT NULL DEFAULT ''
)""",
]

CACHE_TTL_SECONDS = 60.0


# Default flag values. ``tier`` of ``None`` means "applies to every tier".
DEFAULT_FLAGS: Dict[str, Dict[str, Any]] = {
    "ai_agent_enabled":             {"value": True,  "description": "Master switch for the AI creative agent",                 "tier": None},
    "canva_bridge_enabled":          {"value": True,  "description": "Allow Canva import/export bridge",                       "tier": None},
    "plugin_marketplace_enabled":    {"value": True,  "description": "Allow installing signed plugins from the marketplace",  "tier": "creator"},
    "collaboration_v52_enabled":     {"value": True,  "description": "Use the Y.js CRDT V52 collaboration protocol",          "tier": None},
    "analytics_enabled":             {"value": True,  "description": "Creator analytics tracking",                            "tier": "free"},
    "analytics_live_enabled":        {"value": False, "description": "Live activity polling on creator dashboard",               "tier": "creator"},
    "guest_album_enabled":           {"value": True,  "description": "Guest photo album on public invitation pages",         "tier": None},
    "guest_signup_sheets_enabled":   {"value": True,  "description": "Guest sign-up sheets",                                   "tier": None},
    "guest_polls_enabled":           {"value": True,  "description": "Guest polls",                                            "tier": None},
    "guest_gift_registry_enabled":   {"value": True,  "description": "Guest gift registry",                                    "tier": None},
    "multi_channel_delivery_enabled":{"value": True,  "description": "SMS/WhatsApp/Telegram delivery channels",              "tier": "creator"},
    "maintenance_mode":              {"value": False, "description": "Return 503 to non-admins (maintenance window)",         "tier": None},
}


_lock = threading.Lock()
_cache: Optional[Dict[str, Dict[str, Any]]] = None
_cache_at: float = 0.0


def ensure_schema(db) -> None:
    for stmt in SCHEMA_STATEMENTS:
        db.execute(stmt)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _load_snapshot(db) -> Dict[str, Dict[str, Any]]:
    """Read the DB rows; merge with defaults so unknown keys always fall back."""
    snapshot: Dict[str, Dict[str, Any]] = {}
    for key, meta in DEFAULT_FLAGS.items():
        snapshot[key] = {
            "key": key,
            "value": bool(meta["value"]),
            "description": meta["description"],
            "tier": meta.get("tier"),
            "updatedAt": 0,
            "updatedBy": "",
            "source": "default",
        }
    try:
        rows = db.execute("SELECT key,value,description,tier,updated_at,updated_by FROM feature_flags").fetchall()
    except Exception:
        rows = []
    for r in rows:
        key = r["key"]
        if key not in snapshot:
            snapshot[key] = {
                "key": key,
                "value": bool(r["value"]),
                "description": r["description"] or "",
                "tier": r["tier"],
                "updatedAt": int(r["updated_at"] or 0),
                "updatedBy": r["updated_by"] or "",
                "source": "db",
            }
        else:
            entry = snapshot[key]
            entry["value"] = bool(r["value"])
            entry["description"] = r["description"] or entry["description"]
            entry["tier"] = r["tier"] if r["tier"] is not None else entry["tier"]
            entry["updatedAt"] = int(r["updated_at"] or 0)
            entry["updatedBy"] = r["updated_by"] or ""
            entry["source"] = "db"
    return snapshot


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


def get_flag(db, key: str) -> Optional[Dict[str, Any]]:
    snap = _snapshot(db)
    return snap.get(key)


def is_enabled(db, key: str) -> bool:
    flag = get_flag(db, key)
    return bool(flag["value"]) if flag else bool(DEFAULT_FLAGS.get(key, {}).get("value", False))


def list_flags(db) -> List[Dict[str, Any]]:
    snap = _snapshot(db)
    return [dict(v) for v in snap.values()]


def public_flags_for_tier(db, tier: Optional[str]) -> Dict[str, bool]:
    snap = _snapshot(db)
    out: Dict[str, bool] = {}
    for key, entry in snap.items():
        flag_tier = entry.get("tier")
        # Maintenance mode is intentionally excluded from the public list —
        # it is read explicitly by the maintenance middleware.
        if key == "maintenance_mode":
            continue
        if flag_tier is None or (tier and flag_tier == tier):
            out[key] = bool(entry["value"])
    return out


def set_flag(db, key: str, value: bool, updated_by: str, description: Optional[str] = None) -> Dict[str, Any]:
    if key not in DEFAULT_FLAGS:
        # Allow ad-hoc keys (typed once, then they persist). Default value False.
        DEFAULT_FLAGS[key] = {"value": False, "description": description or "", "tier": None}
    meta = DEFAULT_FLAGS[key]
    now = _now_ms()
    desc = description if description is not None else meta["description"]
    db.execute(
        "INSERT INTO feature_flags(key,value,description,tier,updated_at,updated_by) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,description=excluded.description,tier=excluded.tier,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
        (key, 1 if value else 0, desc, meta.get("tier"), now, str(updated_by or "")[:120]),
    )
    invalidate_cache()
    entry = get_flag(db, key) or {}
    return {
        "key": key,
        "value": bool(value),
        "description": desc,
        "tier": meta.get("tier"),
        "updatedAt": now,
        "updatedBy": str(updated_by or ""),
    }
