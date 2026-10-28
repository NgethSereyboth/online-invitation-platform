#!/usr/bin/env python3
"""LT-7.2 step 8 — analytics retention scheduler runs and is logged (ROADMAP §6.10/§6.8).

The reconciliation row said `run_retention_prune` has no caller; it is in fact the
last step of `run_session_reconstruction`, which the server's
`analytics_reconstruction_loop` calls every 300 s. What was genuinely missing is
the per-run log the bullet requires ("Retention cleanup runs daily and is
logged"), so this test proves both halves against a real server process:

* seed one *ended* session older than the retention window that still has one
  event inside the last 24 h, so the spam pass deliberately will NOT delete it —
  only the retention prune can;
* seed one expired event and one expired daily summary;
* seed one fresh event as the control that must survive;
* boot `src/python/server.py` with `EINVITE_ANALYTICS_RETENTION_DAYS=1` and wait
  for the loop's first pass;
* assert the expired rows are gone, the controls remain, and the server log
  carries one `analytics_retention_run` line with the prune counts and exactly
  one `analytics.retention_pruned` audit row.

Since B-2 the prune is gated to its own interval (default 24 h), so this test's
45 s window can only observe the first pass — the 23 h/25 h behaviour is covered
with an injected clock in `tests/analytics_retention_schedule_test.py`.

Prints ``LT_7_2_RETENTION_SCHEDULER_PASSED`` on success.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src" / "python"))
sys.path.insert(0, str(REPO / "tests"))

from v14_test_utils import free_port, process_options, stop_process, temporary_data, wait_http  # noqa: E402

DAY_MS = 24 * 60 * 60 * 1000


def _count(db_file: Path, sql: str, params=()) -> int:
    connection = sqlite3.connect(str(db_file))
    try:
        return int(connection.execute(sql, params).fetchone()[0])
    finally:
        connection.close()


def _seed(db_file: Path, now: int) -> dict:
    """Seed expired + control rows. Returns the assertion windows."""
    from features.analytics.model import ensure_schema

    old = now - 3 * DAY_MS
    old_session = "b" * 32
    old_day = time.strftime("%Y-%m-%d", time.gmtime((now - 3 * DAY_MS) / 1000))
    connection = sqlite3.connect(str(db_file))
    try:
        ensure_schema(connection)
        # An ended session that still has one recent event: the spam pass keeps
        # it (event inside the 24 h window), so only retention can remove it.
        connection.execute(
            "INSERT INTO analytics_sessions(id,invitation_id,started_at,ended_at,duration_ms,created_at)"
            " VALUES(?,?,?,?,?,?)",
            (old_session, "inv-old", now - 4 * DAY_MS, old, 60_000, now - 4 * DAY_MS),
        )
        connection.execute(
            "INSERT INTO analytics_events(session_id,invitation_id,event_type,payload_json,created_at)"
            " VALUES(?,?,?,?,?)",
            (old_session, "inv-old", "invitation.view", "{}", now - 60 * 60 * 1000),
        )
        # Expired event on the same session: only retention can remove it.
        connection.execute(
            "INSERT INTO analytics_events(session_id,invitation_id,event_type,payload_json,created_at)"
            " VALUES(?,?,?,?,?)",
            (old_session, "inv-old", "invitation.gallery.open", "{}", old),
        )
        connection.execute(
            "INSERT INTO analytics_summary_daily(invitation_id,day,unique_sessions,total_views,"
            "avg_duration_ms,p95_duration_ms,rsvp_submitted,rsvp_abandoned,gallery_opens,album_uploads)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("inv-old", old_day, 1, 2, 1000, 1000, 0, 0, 1, 0),
        )
        # Control: a fresh event that must survive the prune.
        connection.execute(
            "INSERT INTO analytics_events(session_id,invitation_id,event_type,payload_json,created_at)"
            " VALUES(?,?,?,?,?)",
            ("c" * 32, "inv-fresh", "invitation.view", "{}", now),
        )
        connection.commit()
    finally:
        connection.close()
    return {"old_day": old_day, "old_session": old_session}


def test_retention_scheduler_runs_and_logs():
    with temporary_data("einvite-lt-7-2-retention-") as data_dir:
        db_file = data_dir / "invites.db"
        log_file = data_dir / "server.log"
        now = int(time.time() * 1000)
        seeded = _seed(db_file, now)

        port = free_port()
        base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": str(data_dir),
            "EINVITE_ANALYTICS_RETENTION_DAYS": "1",
            "EINVITE_ALLOW_NO_SCANNER": "1",
            "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
            "PYTHONPATH": os.pathsep.join([str(REPO / "src" / "python"), str(REPO)]),
        }
        log_handle = log_file.open("w", encoding="utf-8", buffering=1)
        process = subprocess.Popen(
            [sys.executable, "-u", str(REPO / "src" / "python" / "server.py"),
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=REPO, env=env, stdout=log_handle, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", **process_options(),
        )
        try:
            wait_http(base + "/api/health", timeout=24.0, process=process)
            cutoff = now - DAY_MS
            deadline = time.time() + 45
            while time.time() < deadline:
                pruned = (
                    _count(db_file, "SELECT COUNT(*) FROM analytics_events WHERE created_at < ?", (cutoff,)) == 0
                    and _count(db_file, "SELECT COUNT(*) FROM analytics_sessions WHERE ended_at IS NOT NULL AND ended_at < ?", (cutoff,)) == 0
                    and _count(db_file, "SELECT COUNT(*) FROM analytics_summary_daily WHERE day < ?", (seeded["old_day"],)) == 0
                )
                if pruned:
                    break
                time.sleep(0.5)
            assert pruned, "retention prune did not run within 45 s of startup"

            # Controls: the fresh event and the session's recent event survive.
            assert _count(db_file, "SELECT COUNT(*) FROM analytics_events WHERE invitation_id='inv-fresh'") == 1
            assert _count(
                db_file,
                "SELECT COUNT(*) FROM analytics_events WHERE session_id=? AND created_at >= ?",
                (seeded["old_session"], cutoff),
            ) == 1

            log_handle.flush()
            lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if "analytics_retention_run" in line]
            assert lines, "no analytics_retention_run line in the server log"
            run = json.loads(lines[-1])
            assert run["event"] == "analytics_retention_run", run
            assert (run.get("prunedEvents") or 0) >= 1, run
            assert (run.get("prunedSessions") or 0) == 1, run
            assert (run.get("prunedSummaries") or 0) == 1, run
            assert (run.get("retentionDays") or 0) == 1, run
            # B-2: each actual prune also leaves one audit row, so the run
            # outlives the log file. The 24 h gate means the 45 s window can
            # only contain the first pass.
            audit_rows = _count(db_file, "SELECT COUNT(*) FROM audit_events WHERE action='analytics.retention_pruned'")
            assert audit_rows == 1, f"expected exactly one retention audit row, got {audit_rows}"
            print("[OK] retention prune ran on the server's first pass and was logged:", json.dumps(run, ensure_ascii=False), flush=True)
        finally:
            stop_process(process)
            try:
                log_handle.close()
            except Exception:
                pass
    print("LT_7_2_RETENTION_SCHEDULER_PASSED", flush=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))
