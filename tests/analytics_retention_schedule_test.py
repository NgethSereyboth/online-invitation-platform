#!/usr/bin/env python3
"""B-2 — the retention prune runs daily, is logged, and is audited (ROADMAP §6.8).

The reconciliation row said `run_retention_prune` has no caller; it is in fact the
last step of `run_session_reconstruction`, which the server calls every 5 minutes.
Two halves were still missing against the bullet's wording ("Retention cleanup
runs daily and is logged"):

* the prune ran every 5 minutes rather than daily — cheap, but not what the row
  says, and it makes the audit trail 288 rows/day instead of 1;
* nothing wrote an audit row, although `sessions.py`'s own docstring claimed it.

This test drives the scheduler with an injected clock — 23 h must do nothing,
25 h must prune once, 26 h must do nothing again — and asserts the audit callback
fires exactly once per actual run. The server-side log line is covered end to end
by `tests/lt_7_2_retention_scheduler_test.py`.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src" / "python"))

from features.analytics.model import ensure_schema  # noqa: E402
from features.analytics.sessions import (  # noqa: E402
    RETENTION_INTERVAL_DEFAULT_HOURS,
    maybe_run_retention,
    retention_interval_ms,
    run_session_reconstruction,
)

HOUR_MS = 60 * 60 * 1000
DAY_MS = 24 * HOUR_MS
NOW = 1_800_000_000_000


@pytest.fixture(autouse=True)
def _one_day_window(monkeypatch):
    """Pin the retention window so the seeded 3-day-old row is expired."""
    monkeypatch.setenv("EINVITE_ANALYTICS_RETENTION_DAYS", "1")


def _open(tmp_path: Path):
    db = sqlite3.connect(str(tmp_path / "invites.db"), timeout=10)
    db.row_factory = sqlite3.Row
    ensure_schema(db)
    return db


def _seed_expired_event(db, created_at: int) -> None:
    db.execute(
        "INSERT INTO analytics_events(session_id,invitation_id,event_type,payload_json,created_at)"
        " VALUES(?,?,?,?,?)",
        ("a" * 32, "inv-1", "invitation.view", "{}", created_at),
    )
    db.commit()


def test_retention_is_daily_with_an_injected_clock(tmp_path):
    db = _open(tmp_path)
    _seed_expired_event(db, NOW - 3 * DAY_MS)
    audit_rows = []

    first = maybe_run_retention(db, last_run_ms=0, now_ms=NOW, audit=audit_rows.append)
    assert first is not None, "the first pass must prune (nothing has run yet)"
    assert first["events"] == 1
    assert first["ranAtMs"] == NOW
    assert isinstance(first["durationMs"], int) and first["durationMs"] >= 0
    assert len(audit_rows) == 1

    at_23h = maybe_run_retention(
        db, last_run_ms=first["ranAtMs"], now_ms=NOW + 23 * HOUR_MS, audit=audit_rows.append
    )
    assert at_23h is None, "23 h is inside the 24 h window: nothing may run"
    assert len(audit_rows) == 1, "a throttled pass must not audit"

    at_25h = maybe_run_retention(
        db, last_run_ms=first["ranAtMs"], now_ms=NOW + 25 * HOUR_MS, audit=audit_rows.append
    )
    assert at_25h is not None, "25 h is past the window: the prune must run again"
    assert at_25h["events"] == 0
    assert len(audit_rows) == 2

    at_26h = maybe_run_retention(
        db, last_run_ms=at_25h["ranAtMs"], now_ms=NOW + 26 * HOUR_MS, audit=audit_rows.append
    )
    assert at_26h is None
    assert len(audit_rows) == 2, "one audit row per actual run, not per pass"


def test_retention_interval_is_configurable_and_floor_is_one_hour(tmp_path, monkeypatch):
    monkeypatch.delenv("EINVITE_ANALYTICS_RETENTION_INTERVAL_HOURS", raising=False)
    assert retention_interval_ms() == int(RETENTION_INTERVAL_DEFAULT_HOURS * HOUR_MS)

    monkeypatch.setenv("EINVITE_ANALYTICS_RETENTION_INTERVAL_HOURS", "2")
    assert retention_interval_ms() == 2 * HOUR_MS

    # A zero/negative interval would mean "prune on every 5-minute pass"; the
    # floor keeps the documented cadence and the audit trail bounded.
    monkeypatch.setenv("EINVITE_ANALYTICS_RETENTION_INTERVAL_HOURS", "0")
    assert retention_interval_ms() == HOUR_MS

    monkeypatch.setenv("EINVITE_ANALYTICS_RETENTION_INTERVAL_HOURS", "not-a-number")
    assert retention_interval_ms() == int(RETENTION_INTERVAL_DEFAULT_HOURS * HOUR_MS)

    # The interval is read at call time, so the injected value reaches the gate.
    db = _open(tmp_path)
    _seed_expired_event(db, NOW - 3 * DAY_MS)
    monkeypatch.setenv("EINVITE_ANALYTICS_RETENTION_INTERVAL_HOURS", "2")
    assert maybe_run_retention(db, last_run_ms=NOW, now_ms=NOW + 3 * HOUR_MS) is not None


def test_reconstruction_can_skip_the_prune(tmp_path):
    db = _open(tmp_path)
    _seed_expired_event(db, NOW - 3 * DAY_MS)

    result = run_session_reconstruction(db, now_ms=NOW, prune=False)
    assert "pruned" not in result
    remaining = db.execute(
        "SELECT COUNT(*) FROM analytics_events WHERE created_at < ?", (NOW - DAY_MS,)
    ).fetchone()[0]
    assert remaining == 1, "prune=False must leave retention rows untouched"

    pruned = run_session_reconstruction(db, now_ms=NOW)
    assert pruned["pruned"]["events"] == 1, "the default path still prunes"
