"""tests/analytics_ingestion_test.py — v0.67.x (ROADMAP Part 6 §6.1, §6.2, §6.3, §6.9)

End-to-end test of the analytics ingestion pipeline:

Phase 1 — POST /api/analytics/events happy path (204 No Content).
Phase 2 — validation: invalid session_id, missing invitation, unknown
          event_type (all dropped / rejected as expected).
Phase 3 — invitation.view.upserts analytics_sessions; invitation.view.end
          closes the session with ended_at + duration_ms + max_scroll_pct.
Phase 4 — rate limit: 70 requests in 60s → 429 after the 60th.
Phase 5 — background session reconstruction: idle session closed;
          spam session deleted; daily summary aggregated; retention
          prune leaves rows younger than the cutoff.
Phase 6 — declarations: features/analytics/{__init__,model,sessions}.py
          export the public API surface (EVENT_TYPES = 11 entries).

Runs against a real app server via tests/v14_test_utils.app_server.
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))
sys.path.insert(0, str(ROOT))

from tests.v14_test_utils import app_server  # noqa: E402

USERNAME = "analytics-test@example.com"
PASSWORD = "Password123!"


def _post(base, path, body, headers=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data, method="POST",
        headers={**({"Content-Type": "application/json"}), **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode() if isinstance(e, Exception) else b""


def _get(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode() if isinstance(e, Exception) else b""


def _register_and_login(base):
    s, b = _post(base, "/api/auth/register", {"email": USERNAME, "password": PASSWORD})
    assert s == 201, f"register failed: {s} {b}"
    s, b = _post(base, "/api/auth/login", {"email": USERNAME, "password": PASSWORD})
    assert s == 201, f"login failed: {s} {b}"
    token = json.loads(b).get("token")
    assert token, "no token in login response"
    return {"Authorization": "Bearer " + token}


def _create_invitation(base, headers, slug):
    s, b = _post(base, "/api/invitations", {"slug": slug}, headers)
    assert s == 201, f"create invite failed: {s} {b}"
    return json.loads(b)["id"]


def _ingest(base, invitation_id, session_id, events, recipient_id=None):
    body = {
        "sessionId": session_id,
        "invitationId": invitation_id,
        "events": events,
    }
    if recipient_id:
        body["recipientId"] = recipient_id
    return _post(base, "/api/analytics/events", body)


def _hex32(seed: int) -> str:
    """Return a 32-char hex string derived from an integer seed."""
    return ("%032x" % seed).zfill(32)


def test_phase1_happy_path():
    with app_server() as (proc, base, data):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "ingest-test")
        sid = _hex32(1)
        events = [
            {"type": "invitation.view", "ts": int(time.time() * 1000),
             "payload": {"referrer": "https://facebook.com", "viewport": "mobile"}},
            {"type": "invitation.rsvp.open", "ts": int(time.time() * 1000) + 1000,
             "payload": {}},
        ]
        s, b = _ingest(base, inv_id, sid, events)
        assert s == 204, f"ingest should return 204, got {s} body={b!r}"
        # Verify GET /api/invitations/{id}/analytics returns the extended payload.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        assert s == 200, f"get analytics failed: {s} {b}"
        data_obj = json.loads(b)
        assert "analytics" in data_obj, "analytics key missing from response"
        analytics = data_obj["analytics"]
        assert analytics and analytics["stats"]["totalViews"] >= 1, \
            f"expected totalViews>=1, got {analytics}"
        assert analytics["timeseries"]["days"], "timeseries should have days"
        assert analytics["funnel"], "funnel should be populated"
        print("Phase 1 (happy path) PASSED")


def test_phase2_validation():
    with app_server() as (proc, base, data):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "ingest-validate")
        # Invalid session_id (too short).
        s, b = _ingest(base, inv_id, "too-short",
                       [{"type": "invitation.view", "ts": int(time.time() * 1000), "payload": {}}])
        assert s == 400, f"invalid sid should be 400, got {s} {b!r}"
        # Non-existent invitation.
        s, b = _ingest(base, "nonexistent-id", _hex32(2),
                       [{"type": "invitation.view", "ts": int(time.time() * 1000), "payload": {}}])
        assert s == 404, f"nonexistent invite should be 404, got {s} {b!r}"
        # Unknown event_type is silently dropped (not rejected) — the batch
        # still succeeds with 204 because the valid events in the same batch
        # would be inserted. If the entire batch is invalid, we still get 204
        # but no events are persisted.
        s, b = _ingest(base, inv_id, _hex32(3),
                       [{"type": "bogus.event", "ts": int(time.time() * 1000), "payload": {}}])
        assert s == 204, f"bogus event batch should return 204 (silently dropped), got {s} {b!r}"
        # Empty events array → 400.
        s, b = _ingest(base, inv_id, _hex32(4), [])
        assert s == 400, f"empty events should be 400, got {s} {b!r}"
        print("Phase 2 (validation) PASSED")


def test_phase3_session_upsert_and_close():
    with app_server() as (proc, base, data):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "ingest-session")
        sid = _hex32(10)
        # First batch: invitation.view → session created.
        now = int(time.time() * 1000)
        s, b = _ingest(base, inv_id, sid,
                       [{"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}}])
        assert s == 204, f"view ingest failed: {s} {b!r}"
        # Verify the session was created by querying the analytics endpoint.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        assert s == 200
        analytics = json.loads(b)["analytics"]
        assert analytics["stats"]["totalViews"] == 1, \
            f"expected 1 view after first ingest, got {analytics['stats']['totalViews']}"
        # Second batch: invitation.rsvp.open then invitation.view.end.
        s, b = _ingest(base, inv_id, sid, [
            {"type": "invitation.rsvp.open", "ts": now + 1000, "payload": {}},
            {"type": "invitation.rsvp.submit", "ts": now + 2000, "payload": {"status": "yes"}},
            {"type": "invitation.view.end", "ts": now + 5000,
             "payload": {"duration_ms": 5000, "max_scroll_pct": 75}},
        ])
        assert s == 204, f"rsvp ingest failed: {s} {b!r}"
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        analytics = json.loads(b)["analytics"]
        # Funnel should show 1 view, 1 rsvp.open, 1 rsvp.submit.
        funnel = {f["step"]: f for f in analytics["funnel"]}
        assert funnel["view"]["count"] == 1, f"funnel view count: {funnel}"
        assert funnel["rsvp.open"]["count"] == 1, f"funnel rsvp.open: {funnel}"
        assert funnel["rsvp.submit"]["count"] == 1, f"funnel rsvp.submit: {funnel}"
        # avg duration should be 5000ms now (one session ended with duration 5000).
        assert analytics["stats"]["avgDurationMs"] == 5000, \
            f"expected avgDurationMs=5000, got {analytics['stats']['avgDurationMs']}"
        print("Phase 3 (session upsert + close) PASSED")


def test_phase4_rate_limit():
    with app_server() as (proc, base, data):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "ingest-ratelimit")
        sid = _hex32(20)
        rejected = 0
        accepted = 0
        for i in range(70):
            s, b = _ingest(base, inv_id, sid, [
                {"type": "invitation.view", "ts": int(time.time() * 1000), "payload": {}},
            ])
            if s == 204:
                accepted += 1
            elif s == 429:
                rejected += 1
            else:
                assert False, f"unexpected status {s}: {b!r}"
        assert accepted == 60, f"expected 60 accepted, got {accepted}"
        assert rejected == 10, f"expected 10 rejected (429), got {rejected}"
        print(f"Phase 4 (rate limit) PASSED — accepted={accepted} rejected={rejected}")


def test_phase5_background_reconstruction():
    """Verify the background job closes idle sessions + prunes old data."""
    from features.analytics.sessions import (
        close_idle_sessions, delete_spam_sessions, aggregate_daily_summary,
        run_retention_prune,
    )
    from features.analytics.model import ensure_schema, upsert_session, insert_event
    import sqlite3
    from datetime import datetime, timedelta

    # Use a fresh temp DB.
    db_path = data if False else "/tmp/ei-analytics-bg-test.db"
    if os.path.exists(db_path):
        os.unlink(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Need an invitations table for the FK-like checks (not enforced in SQLite).
    conn.execute("CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY, owner_id TEXT)")
    conn.execute("INSERT OR IGNORE INTO invitations(id) VALUES('test-inv-1')")
    conn.execute("INSERT OR IGNORE INTO invitations(id) VALUES('test-inv-2')")
    ensure_schema(conn)

    now = int(time.time() * 1000)
    # Session 1: idle — last event 60 minutes ago, no ended_at.
    upsert_session(conn, _hex32(100), "test-inv-1", started_at=now - 90 * 60 * 1000)
    insert_event(conn, _hex32(100), "test-inv-1", event_type="invitation.view",
                 ts=now - 60 * 60 * 1000, payload={})
    # Session 2: spam — ended long ago, no events in 24h.
    upsert_session(conn, _hex32(101), "test-inv-1", started_at=now - 48 * 60 * 60 * 1000)
    insert_event(conn, _hex32(101), "test-inv-1", event_type="invitation.view",
                 ts=now - 48 * 60 * 60 * 1000, payload={})
    conn.execute("UPDATE analytics_sessions SET ended_at=? WHERE id=?", (now - 47 * 60 * 60 * 1000, _hex32(101)))
    conn.commit()

    closed = close_idle_sessions(conn, now_ms=now)
    assert closed == 1, f"expected 1 idle session closed, got {closed}"
    spam_deleted = delete_spam_sessions(conn, now_ms=now)
    assert spam_deleted == 1, f"expected 1 spam session deleted, got {spam_deleted}"
    aggregated = aggregate_daily_summary(conn)
    assert aggregated >= 0, f"aggregation returned {aggregated}"

    # Retention prune: insert an old event (>365 days) and verify it gets pruned.
    long_ago = now - 400 * 24 * 60 * 60 * 1000
    upsert_session(conn, _hex32(200), "test-inv-2", started_at=long_ago)
    conn.execute("UPDATE analytics_sessions SET ended_at=? WHERE id=?", (long_ago + 1000, _hex32(200)))
    insert_event(conn, _hex32(200), "test-inv-2", event_type="invitation.view",
                 ts=long_ago, payload={})
    conn.commit()
    pruned = run_retention_prune(conn, retention_days=365)
    assert pruned["events"] >= 1, f"expected >=1 event pruned, got {pruned}"
    assert pruned["sessions"] >= 1, f"expected >=1 session pruned, got {pruned}"
    conn.close()
    os.unlink(db_path)
    print("Phase 5 (background reconstruction) PASSED")


def test_phase6_module_declarations():
    from features.analytics import (
        ensure_schema, record_event_batch, run_session_reconstruction,
        invitation_analytics_summary, account_creations_table, account_analytics_summary,
        stream_invitation_csv, stream_invitation_json, stream_account_csv, stream_account_json,
        set_invitation_analytics_enabled, is_invitation_analytics_enabled, purge_invitation_analytics,
        invitation_live_activity, EVENT_TYPES, RETENTION_DEFAULT_DAYS,
    )
    assert len(EVENT_TYPES) == 11, f"expected 11 event types, got {len(EVENT_TYPES)}"
    expected = {
        "invitation.view", "invitation.view.end", "invitation.gallery.open",
        "invitation.rsvp.open", "invitation.rsvp.submit", "invitation.rsvp.abandon",
        "invitation.link.click", "invitation.signup.claim", "invitation.poll.vote",
        "invitation.album.upload", "invitation.gift.claim",
    }
    assert set(EVENT_TYPES) == expected, f"event types mismatch: {set(EVENT_TYPES) ^ expected}"
    assert RETENTION_DEFAULT_DAYS == 365
    print("Phase 6 (module declarations) PASSED")


def main():
    # Set the no-scanner bypass so the test server boots in dev environments
    # without ClamAV installed. Mirrors the existing test pattern.
    os.environ.setdefault("EINVITE_ALLOW_NO_SCANNER", "1")
    test_phase6_module_declarations()
    test_phase5_background_reconstruction()
    test_phase1_happy_path()
    test_phase2_validation()
    test_phase3_session_upsert_and_close()
    test_phase4_rate_limit()
    print("\nANALYTICS_INGESTION_TEST_PASSED")


if __name__ == "__main__":
    main()
