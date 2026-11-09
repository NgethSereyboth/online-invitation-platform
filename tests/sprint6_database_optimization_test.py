"""Sprint 6 — database layer optimization evidence.

Pins the four production PRAGMAs on every fresh connection, the per-request
statement budget of the hottest read/write endpoints, the query plans behind
pagination and search, the removal of the per-guest RSVP lookup, and 50
concurrent readers against a real server process.

Statement counts are measured on the wire through the opt-in
``X-DB-Query-Count`` header (``EINVITE_DB_QUERY_COUNT=1``) fed by
``core.db_metrics``, so a handler that opens several ``connect()`` blocks
cannot hide statements from the count.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src" / "python"))

from v14_test_utils import app_server  # noqa: E402

ENV = {
    "EINVITE_DEV_AUTH_TOKENS": "1",
    "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
    "EINVITE_ALLOW_NO_SCANNER": "1",
    "EINVITE_DB_QUERY_COUNT": "1",
}

PRAGMAS = ("journal_mode", "synchronous", "busy_timeout", "foreign_keys")
EXPECTED_PRAGMAS = {
    "journal_mode": "wal",
    "synchronous": 1,  # NORMAL
    "busy_timeout": 5000,
    "foreign_keys": 1,
}

# The pre-optimization guest query, kept here as the "before" half of the
# N+1 proof: a correlated lookup per guest row that cannot use an index
# because ``lower()`` wraps both sides of the comparison.
LEGACY_GUEST_SQL = (
    "SELECT g.id,g.name,g.slug,g.phone,g.email,g.group_name,g.household_id,g.tags_json,"
    "g.table_name,g.seat_label,g.delivery_status,g.opened_at,g.token_salt,g.token_version,"
    "g.token_expires_at,g.token_revoked_at,g.created_at,g.checked_in,g.checked_in_at,"
    "(SELECT status FROM rsvps r WHERE r.invitation_id=g.invitation_id AND lower(r.name)=lower(g.name) "
    "ORDER BY created_at DESC LIMIT 1) rsvp_status "
    "FROM guests g WHERE g.invitation_id=? ORDER BY g.created_at DESC"
)


def _json(base, method, path, body=None, token=None, timeout=30):
    payload = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}"), response.headers
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}"), error.headers


def _register(base, email):
    status, payload, _ = _json(base, "POST", "/api/auth/register",
                               {"email": email, "password": "Test1234!Pass"})
    assert status == 201, payload
    return payload["token"], payload["user"]["id"]


def _document(names="Sprint Six"):
    return {
        "schemaVersion": 14,
        "eventType": "Wedding",
        "fields": {"names": names, "date": "2026-12-27", "venue": "Grand Hall"},
        "objects": {},
        "designPages": [],
        "settings": {"rsvpEnabled": True},
    }


def _statement_count(base, method, path, token, body=None):
    status, payload, headers = _json(base, method, path, body=body, token=token)
    assert status in (200, 201), (status, payload)
    raw = headers.get("X-DB-Query-Count")
    assert raw is not None and raw.isdigit(), (path, dict(headers))
    return int(raw)


def _connect(path):
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    return db


def _plan(db, sql, params=()):
    return [row["detail"] for row in db.execute("EXPLAIN QUERY PLAN " + sql, params)]


def _is_full_table_scan(plan):
    """True only for an unindexed table scan; index-range scans are fine."""
    return any(detail in {"SCAN i", "SCAN g", "SCAN invitations", "SCAN guests"} for detail in plan)


def test_pragmas_are_applied_on_every_new_connection(tmp_path, monkeypatch):
    monkeypatch.setenv("EINVITE_DATA_DIR", str(tmp_path))
    import server

    # Three fresh connections in a row: the per-connection PRAGMAs must be
    # re-applied each time, not just on the first one that bootstraps the file.
    for _ in range(3):
        with server.connect_sqlite() as db:
            observed = {name: db.execute(f"PRAGMA {name}").fetchone()[0] for name in PRAGMAS}
        assert observed == EXPECTED_PRAGMAS, observed

    # WAL is a persistent database property; a connection opened outside the
    # helper still sees it, which is what lets readers and the writer coexist.
    raw = sqlite3.connect(str(tmp_path / "invites.db"))
    try:
        assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert raw.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        raw.close()


def test_connection_lifecycle_closes_and_does_not_hold_transactions(tmp_path, monkeypatch):
    monkeypatch.setenv("EINVITE_DATA_DIR", str(tmp_path))
    import server

    # The one-time schema pass runs DDL; finish it first so the check below
    # measures a normal request connection, not schema bootstrap.
    with server.connect_sqlite() as db:
        db.execute("SELECT 1")

    with server.connect_sqlite() as db:
        assert db.execute("SELECT 1").fetchone()[0] == 1
        # A read must not leave an open write transaction behind the request.
        assert db.in_transaction is False

    with pytest.raises(sqlite3.ProgrammingError):
        db.execute("SELECT 1")

    with sqlite3.connect(str(tmp_path / "invites.db")) as check:
        check.execute("CREATE TABLE IF NOT EXISTS rollback_probe(id TEXT)")
        check.commit()

    with pytest.raises(RuntimeError):
        with server.connect_sqlite() as db:
            db.execute("INSERT INTO rollback_probe(id) VALUES('x')")
            raise RuntimeError("boom")

    with sqlite3.connect(str(tmp_path / "invites.db")) as check:
        assert check.execute("SELECT COUNT(*) FROM rollback_probe").fetchone()[0] == 0


def test_hot_endpoint_statement_budget():
    with app_server(ENV) as (_process, base, _data):
        token, _user_id = _register(base, "sprint6-counts@example.test")
        status, created, _ = _json(base, "POST", "/api/invitations",
                                   {"slug": "sprint6-counts", "document": _document()}, token)
        assert status == 201, created
        invite_id = created["id"]
        status, guest, _ = _json(base, "POST", f"/api/invitations/{invite_id}/guests",
                                 {"name": "Counted Guest"}, token)
        assert status == 201, guest

        # Warm the 60s settings cache and the session's last_seen_at write so
        # the measured requests reflect steady-state, not first-request setup.
        _statement_count(base, "GET", "/api/invitations", token)

        counts = {
            "list_invitations": _statement_count(base, "GET", "/api/invitations", token),
            "get_invitation": _statement_count(base, "GET", f"/api/invitations/{invite_id}", token),
            "get_guests": _statement_count(base, "GET", f"/api/invitations/{invite_id}/guests", token),
            "check_in_guest": _statement_count(
                base, "PUT", f"/api/invitations/{invite_id}/guests/{guest['id']}/check-in",
                token, {"checkedIn": True},
            ),
        }

    assert counts["list_invitations"] <= 2, counts
    assert counts["get_invitation"] <= 2, counts
    assert counts["get_guests"] <= 3, counts
    assert counts["check_in_guest"] <= 3, counts
    print("SPRINT6_STATEMENT_COUNTS", json.dumps(counts, sort_keys=True))


def test_pagination_search_and_guest_plans_use_indexes():
    with app_server(ENV) as (_process, base, data):
        token, user_id = _register(base, "sprint6-plans@example.test")
        status, created, _ = _json(base, "POST", "/api/invitations",
                                   {"slug": "sprint6-plans", "document": _document()}, token)
        assert status == 201, created
        invite_id = created["id"]

        db = _connect(data / "invites.db")
        try:
            now = int(time.time() * 1000)
            db.executemany(
                "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,is_published) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    (
                        f"plan-inv-{i}",
                        f"plan-slug-{i}",
                        json.dumps(_document(f"Plan Couple {i}")),
                        now - i * 1000,
                        "plan-owner",
                        i % 2,
                        i % 3 == 0,
                    )
                    for i in range(400)
                ),
            )
            db.executemany(
                "INSERT INTO invitation_collaborators(invitation_id,user_id,role,created_at) "
                "VALUES(?,?,?,?)",
                ((f"plan-inv-{i}", "plan-collab", "viewer", now) for i in range(0, 400, 8)),
            )
            db.executemany(
                "INSERT INTO rsvps(id,invitation_id,publication_id,guest_id,name,normalized_name,"
                "status,guest_count,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    (
                        f"plan-rsvp-{i}",
                        f"plan-inv-{i % 400}",
                        "plan-pub",
                        None,
                        f"Guest {i}",
                        f"guest {i}",
                        "Yes, joyfully",
                        1,
                        now - i * 500,
                    )
                    for i in range(800)
                ),
            )
            db.commit()
            db.execute("ANALYZE")
            db.commit()

            import server

            plan_cases = [
                ("all", ""),
                ("published", ""),
                ("draft", ""),
                ("archived", ""),
                ("all", "Plan Couple 12"),
            ]
            for status_filter, search in plan_cases:
                sql, params = server.invitation_list_statement("plan-owner", status_filter, search)
                plan = _plan(db, sql, (*params, 20, 0))
                assert not _is_full_table_scan(plan), (status_filter, search, plan)
                assert any("SEARCH i" in detail for detail in plan), (status_filter, search, plan)
                # The per-row RSVP count is a covering-index lookup, not a scan.
                assert not any(detail == "SCAN r" for detail in plan), (status_filter, search, plan)
                assert any("idx_rsvps_invitation" in detail for detail in plan), (status_filter, search, plan)

            # The N+1 that mattered: 1,200 guests × 1,200 RSVPs in one
            # invitation. The legacy query re-scans the RSVP rows for every
            # guest; the new one aggregates the invitation's RSVPs once.
            db.executemany(
                "INSERT INTO guests(id,invitation_id,name,slug,token,created_at) VALUES(?,?,?,?,?,?)",
                ((f"bench-guest-{i}", invite_id, f"Bench Guest {i}", f"bench-guest-{i}",
                  f"bench-token-{i}", now - i) for i in range(1200)),
            )
            db.executemany(
                "INSERT INTO rsvps(id,invitation_id,publication_id,guest_id,name,normalized_name,"
                "status,guest_count,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    (f"bench-rsvp-{i}", invite_id, "bench-pub", None, f"Bench Guest {i}",
                     f"bench guest {i}", "Yes, joyfully", 1, now - i)
                    for i in range(1200)
                ),
            )
            db.commit()
            db.execute("ANALYZE")
            db.commit()

            legacy_plan = _plan(db, LEGACY_GUEST_SQL, (invite_id,))
            assert any("CORRELATED" in detail for detail in legacy_plan), legacy_plan

            guest_sql, guest_params = server.guest_list_statement(user_id, invite_id)
            guest_plan = _plan(db, guest_sql, guest_params)
            assert not any("rsvps" in detail.lower() for detail in guest_plan), guest_plan
            assert any("idx_guests_invitation" in detail for detail in guest_plan), guest_plan

            rsvp_sql, rsvp_params = server.guest_rsvp_statement(invite_id)
            rsvp_plan = _plan(db, rsvp_sql, rsvp_params)
            assert not any(detail == "SCAN rsvps" for detail in rsvp_plan), rsvp_plan
            assert any("idx_rsvps_invitation" in detail for detail in rsvp_plan), rsvp_plan

            def legacy_lookup(repeats=2):
                best = float("inf")
                count = 0
                for _ in range(repeats):
                    started = time.perf_counter()
                    count = len(db.execute(LEGACY_GUEST_SQL, (invite_id,)).fetchall())
                    best = min(best, time.perf_counter() - started)
                return best, count

            def batched_lookup(repeats=5):
                best = float("inf")
                count = 0
                for _ in range(repeats):
                    started = time.perf_counter()
                    guest_rows = db.execute(guest_sql, guest_params).fetchall()
                    latest = {}
                    for rsvp in db.execute(rsvp_sql, rsvp_params).fetchall():
                        latest.setdefault(rsvp["lookup_name"], rsvp["status"])
                    for row in guest_rows:
                        latest.get((row["name"] or "").lower())
                    best = min(best, time.perf_counter() - started)
                    count = len(guest_rows)
                return best, count

            legacy_seconds, legacy_rows = legacy_lookup()
            new_seconds, new_rows = batched_lookup()
            assert legacy_rows == new_rows == 1200
            assert new_seconds < legacy_seconds / 3, (legacy_seconds, new_seconds)
            print("SPRINT6_GUEST_LOOKUP_SECONDS",
                  json.dumps({"legacy": legacy_seconds, "optimized": new_seconds}))
        finally:
            db.close()


def test_fifty_concurrent_read_requests_have_no_locked_database():
    with app_server(ENV) as (_process, base, data):
        token, _user_id = _register(base, "sprint6-concurrency@example.test")
        status, created, _ = _json(base, "POST", "/api/invitations",
                                   {"slug": "sprint6-concurrency", "document": _document()}, token)
        assert status == 201, created
        invite_id = created["id"]
        for index in range(3):
            status, guest, _ = _json(base, "POST", f"/api/invitations/{invite_id}/guests",
                                     {"name": f"Concurrent Guest {index}"}, token)
            assert status == 201, guest

        paths = (
            "/api/invitations",
            f"/api/invitations/{invite_id}",
            f"/api/invitations/{invite_id}/guests?limit=50",
        )

        def read(index):
            return _json(base, "GET", paths[index % len(paths)], token=token, timeout=30)

        with ThreadPoolExecutor(max_workers=50) as pool:
            results = list(pool.map(read, range(50)))

        failures = [(status, payload) for status, payload, _headers in results if status != 200]
        assert not failures, failures[:3]
        assert not any("database is locked" in json.dumps(payload).lower()
                       for _status, payload, _headers in results)

        log = (data / "server-test.log").read_text(encoding="utf-8", errors="replace").lower()
        assert "database is locked" not in log

        check = _connect(data / "invites.db")
        try:
            assert check.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            check.close()
