"""admin_metrics.py — v0.64.0 (ROADMAP-v0.54-to-v1.0 §5.1 + §5.6)

In-process helpers for the admin dashboard:

- A rolling p95 latency buffer (capped at 1024 samples) for DB response time
  in the last 5 minutes. The dashboard polls every 30s; recomputing p95 from
  scratch each poll is wasteful under load — the buffer keeps it O(N log N)
  with N capped.
- A 60s cache for the system-health detail payload.
- Helpers to compute the 8 stat-card metrics + 7-day deltas from existing
  tables.

Public API
----------
``record_db_latency_ms(ms)``         — call after every connect() block
``db_p95_ms(window_seconds=300)``     — p95 of the rolling buffer
``compute_metrics(db)``                — 8 stat cards with 7-day deltas
``compute_system_status(db, health)``  — green/yellow/red banner
"""
from __future__ import annotations
import bisect
import threading
import time
from collections import deque
from typing import Any, Dict, Deque, List, Optional


_LOCK = threading.Lock()
_LATENCY_SAMPLES: Deque = deque()  # (timestamp_ms, latency_ms)
_LATENCY_CAP = 1024

_HEALTH_DETAIL_CACHE: Optional[Dict[str, Any]] = None
_HEALTH_DETAIL_AT: float = 0.0
_HEALTH_DETAIL_TTL = 60.0

_METRIC_TABLES = frozenset({"users", "invitations", "assets", "background_jobs"})
_METRIC_DATE_COLUMNS = frozenset({"created_at"})
_METRIC_SUM_COLUMNS = frozenset({"size"})


def record_db_latency_ms(ms: float) -> None:
    """Record one DB round-trip latency observation."""
    try:
        now = time.time()
        with _LOCK:
            _LATENCY_SAMPLES.append((now, float(ms)))
            if len(_LATENCY_SAMPLES) > _LATENCY_CAP:
                # Drop oldest; keep most-recent window
                while len(_LATENCY_SAMPLES) > _LATENCY_CAP:
                    _LATENCY_SAMPLES.popleft()
    except Exception:
        pass


def db_p95_ms(window_seconds: float = 300.0) -> float:
    cutoff = time.time() - window_seconds
    with _LOCK:
        samples = [s[1] for s in _LATENCY_SAMPLES if s[0] >= cutoff]
    if not samples:
        return 0.0
    samples.sort()
    # Nearest-rank p95 (NIST convention) — index = ceil(0.95*N) - 1
    idx = max(0, min(len(samples) - 1, int(round(0.95 * len(samples))) - 1))
    return float(samples[idx])


def _row_count(db, table: str) -> int:
    if table not in _METRIC_TABLES:
        raise ValueError("unsupported metric table")
    try:
        row = db.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()
        return int(row["c"] if row else 0)
    except Exception:
        return 0


def _count_since(db, table: str, column: str, since_ms: int) -> int:
    if table not in _METRIC_TABLES or column not in _METRIC_DATE_COLUMNS:
        raise ValueError("unsupported metric identifier")
    try:
        row = db.execute(f"SELECT COUNT(*) c FROM {table} WHERE {column}>=?", (since_ms,)).fetchone()
        return int(row["c"] if row else 0)
    except Exception:
        return 0


def _sum_since(db, table: str, column: str, since_ms: int) -> int:
    if table not in _METRIC_TABLES or column not in _METRIC_SUM_COLUMNS:
        raise ValueError("unsupported metric identifier")
    try:
        row = db.execute(f"SELECT COALESCE(SUM({column}),0) c FROM {table} WHERE {column}>=?", (since_ms,)).fetchone()
        return int(row["c"] if row else 0)
    except Exception:
        return 0


def _count_action_since(db, action: str, since_ms: int) -> int:
    try:
        row = db.execute(
            "SELECT COUNT(*) c FROM audit_events WHERE action=? AND created_at>=?",
            (action, since_ms),
        ).fetchone()
        return int(row["c"] if row else 0)
    except Exception:
        return 0


def _count_audit_actions_since(db, actions: List[str], since_ms: int) -> int:
    if not actions:
        return 0
    placeholders = ",".join("?" for _ in actions)
    try:
        row = db.execute(
            f"SELECT COUNT(*) c FROM audit_events WHERE action IN ({placeholders}) AND created_at>=?",
            tuple(actions) + (since_ms,),
        ).fetchone()
        return int(row["c"] if row else 0)
    except Exception:
        return 0


def compute_metrics(db, started_at: float, now_ms: Optional[int] = None) -> Dict[str, Any]:
    """Compute the 8 dashboard stat-card metrics with 7-day deltas."""
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    seven_days_ago = now_ms - 7 * 24 * 60 * 60 * 1000
    twenty_four_hours_ago = now_ms - 24 * 60 * 60 * 1000
    five_min_ago = now_ms - 5 * 60 * 1000

    total_users = _row_count(db, "users")
    users_7d = _count_since(db, "users", "created_at", seven_days_ago)
    total_invitations = _row_count(db, "invitations")
    invitations_7d = _count_since(db, "invitations", "created_at", seven_days_ago)

    # Active sessions now (sessions that have not expired)
    try:
        active_sessions = int(db.execute("SELECT COUNT(*) c FROM sessions WHERE expires_at>?", (now_ms,)).fetchone()["c"])
    except Exception:
        active_sessions = 0

    # Storage used / total quota (sum of asset sizes; quota is informational only)
    try:
        storage_row = db.execute("SELECT COALESCE(SUM(size),0) c FROM assets").fetchone()
        storage_used = int(storage_row["c"] if storage_row else 0)
    except Exception:
        storage_used = 0
    storage_quota = 5 * 1024 * 1024 * 1024  # 5GB default cap; informational
    storage_7d = _sum_since(db, "assets", "size", seven_days_ago)

    failed_logins_24h = _count_audit_actions_since(db, ["login.failed", "login.account_locked"], twenty_four_hours_ago)
    rate_limit_hits_24h = _count_action_since(db, "rate_limit.hit", twenty_four_hours_ago)
    job_queue_depth = _row_count(db, "background_jobs")
    # DB p95 (5 min window) — read from the in-memory rolling buffer.
    db_p95 = db_p95_ms(300)

    return {
        "cards": [
            {"key": "users",              "label": "Total users",                "label_km": "អ្នកប្រើរួម",        "value": total_users,        "delta7d": users_7d,         "unit": "count"},
            {"key": "invitations",        "label": "Total invitations",           "label_km": "ការអញ្ជើញរួម",      "value": total_invitations,  "delta7d": invitations_7d,   "unit": "count"},
            {"key": "activeSessions",     "label": "Active sessions",             "label_km": "សessianសកម្ម",        "value": active_sessions,    "delta7d": None,             "unit": "count"},
            {"key": "storage",            "label": "Storage used",                 "label_km": "ទំហំប្រើប្រាស់",      "value": storage_used,       "delta7d": storage_7d,       "unit": "bytes", "total": storage_quota},
            {"key": "failedLogins",       "label": "Failed logins (24h)",         "label_km": "ការឡុកអិនបរាជ័យ (២៤ម៉)", "value": failed_logins_24h,  "delta7d": None,             "unit": "count"},
            {"key": "rateLimitHits",      "label": "Rate-limit hits (24h)",       "label_km": "ការរឹតបន្តឹង (២៤ម៉)",   "value": rate_limit_hits_24h, "delta7d": None,            "unit": "count"},
            {"key": "jobQueueDepth",      "label": "Background jobs queued",      "label_km": "ការងារផ្ទៃខាងក្រោយ",   "value": job_queue_depth,    "delta7d": None,             "unit": "count"},
            {"key": "dbP95",              "label": "DB response p95 (5min)",     "label_km": "p95 របស់ DB (៥នាទី)",   "value": round(db_p95, 2),   "delta7d": None,             "unit": "ms"},
        ],
        "uptimeSeconds": int(time.time() - started_at),
        "computedAt": now_ms,
    }


def compute_system_status(metrics_payload: Dict[str, Any], health_detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return ``{status, level, messages:[]}`` where level is green/yellow/red."""
    messages: List[str] = []
    level = "green"

    # Critical checks (red)
    if health_detail:
        checks = health_detail.get("checks", {})
        # Database unreachable = red
        db_check = checks.get("database", {})
        if not db_check.get("ok", True):
            level = "red"
            messages.append("Database connection failed — " + str(db_check.get("error", "unknown")))
        # Disk >90% full = red
        disk_check = checks.get("disk", {})
        if disk_check.get("ok") is False and disk_check.get("usedPercent", 0) >= 90:
            level = "red"
            messages.append(f"Disk is {int(disk_check.get('usedPercent', 0))}% full")
        # Backup >48h old = red
        backup_check = checks.get("backup", {})
        if backup_check.get("ok") is False and backup_check.get("ageHours", 0) >= 48:
            if level != "red":
                level = "yellow"
            messages.append(f"Last backup is {int(backup_check.get('ageHours', 0))}h old")
        # Single warning (yellow) — e.g. backup >25h
        if level != "red":
            for warn_key in ("malware_scanner", "smtp", "redis", "object_storage"):
                check = checks.get(warn_key, {})
                if check.get("ok") is False and not check.get("critical", False):
                    level = "yellow"
                    messages.append(f"{warn_key} check warning: " + str(check.get("error", "unavailable")))
                    break

    if not messages:
        messages.append("All systems operational")

    return {
        "status": level,
        "level": level,
        "messages": messages,
        "computedAt": metrics_payload.get("computedAt"),
    }


def get_health_detail_cache() -> Optional[Dict[str, Any]]:
    global _HEALTH_DETAIL_CACHE, _HEALTH_DETAIL_AT
    with _LOCK:
        if _HEALTH_DETAIL_CACHE is None or (time.time() - _HEALTH_DETAIL_AT) > _HEALTH_DETAIL_TTL:
            return None
        return _HEALTH_DETAIL_CACHE


def set_health_detail_cache(payload: Dict[str, Any]) -> None:
    global _HEALTH_DETAIL_CACHE, _HEALTH_DETAIL_AT
    with _LOCK:
        _HEALTH_DETAIL_CACHE = payload
        _HEALTH_DETAIL_AT = time.time()
