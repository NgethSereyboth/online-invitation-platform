#!/usr/bin/env python3
"""LT-3.9 — automatic version snapshots on the server-side draft save (D-7).

Two halves, one behaviour:

* **Policy, with an injected clock.** `features/invitation_versions` is the
  unused data layer the roadmap asked to wire in. Its auto-snapshot rule is
  "content hash changed AND at least 5 minutes since the last auto snapshot,
  capped at 50, skipped with a log line above 2 MB". The clock is passed in, so
  this half drives 31 simulated minutes of editing against a real SQLite
  connection instead of sleeping.
* **Wiring, against a real server process.** A draft save creates one snapshot,
  an identical save creates none, a second change inside five minutes creates
  none, and restoring the auto snapshot through the existing restore-as-draft
  endpoint returns a draft byte-equal to the snapshot. Temp data dir only.

Prints ``LT_3_9_AUTO_VERSIONS_PASSED`` on success.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for _root in (REPO, REPO / "src" / "python", REPO / "tests"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from features import invitation_versions  # noqa: E402
from v14_test_utils import free_port, process_options, stop_process, temporary_data, wait_http  # noqa: E402

BASE_MS = 1_700_000_000_000
MINUTE_MS = 60_000


def _db():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _count(db, invitation_id="inv-auto"):
    return int(
        db.execute(
            "SELECT COUNT(*) FROM invitation_versions WHERE invitation_id=?",
            (invitation_id,),
        ).fetchone()[0]
    )


def _doc(name: str) -> str:
    return json.dumps({"schemaVersion": 13, "fields": {"names": name}})


def _capture(db, name: str, minute: int, **kwargs):
    return invitation_versions.capture_auto_snapshot(
        db,
        "inv-auto",
        _doc(name),
        author_id="user-1",
        now_ms=BASE_MS + minute * MINUTE_MS,
        **kwargs,
    )


def test_policy_clock_gap_cap_and_size(capsys):
    db = _db()
    # 6 content changes across 31 simulated minutes, each >= 5 min apart.
    for index, minute in enumerate((0, 5, 10, 15, 20, 31)):
        result = _capture(db, f"Revision {index}", minute)
        assert result["created"] is True, (index, result)
        assert result["reason"] == "created", result
    assert _count(db) == 6

    # Unchanged content is never snapshotted, however long the gap.
    unchanged = _capture(db, "Revision 5", 41)
    assert unchanged == {"created": False, "reason": "unchanged", "id": None}, unchanged
    assert _count(db) == 6

    # A real change 11 minutes after the last snapshot is stored…
    changed = _capture(db, "Revision 6", 42)
    assert changed["created"] is True, changed

    # …but the next one two minutes later is too soon.
    too_soon = _capture(db, "Revision 7", 44)
    assert too_soon["created"] is False and too_soon["reason"] == "too_soon", too_soon
    assert _count(db) == 7

    # Exactly five minutes after the last snapshot is allowed, then again.
    boundary = _capture(db, "Revision 8", 47)
    assert boundary["created"] is True, boundary
    exact = _capture(db, "Revision 9", 52)
    assert exact["created"] is True, exact

    # The cap is 50, oldest pruned first.
    ids = [row["id"] for row in db.execute("SELECT id FROM invitation_versions ORDER BY created_at ASC")]
    for step in range(60):
        _capture(db, f"Bulk {step}", 60 + step * 6)
    assert invitation_versions.MAX_SNAPSHOTS_PER_INVITATION == 50
    assert _count(db) == 50, _count(db)
    surviving = {row["id"] for row in db.execute("SELECT id FROM invitation_versions")}
    assert ids[0] not in surviving, "oldest snapshot should have been pruned"

    # Over 2 MB is skipped with a log line, not stored.
    huge = json.dumps({"fields": {"blob": "x" * 2_200_000}})
    before = _count(db)
    oversized = invitation_versions.capture_auto_snapshot(
        db, "inv-big", huge, author_id="user-1", now_ms=BASE_MS
    )
    assert oversized == {"created": False, "reason": "size", "id": None}, oversized
    assert _count(db, "inv-big") == 0
    assert _count(db) == before
    log = capsys.readouterr().out
    assert "auto snapshot skipped" in log and "inv-big" in log, log


def _req(base: str, path: str, method: str = "GET", body=None, token: str | None = None, expected: int = 200):
    import urllib.error
    import urllib.request

    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    if status != expected:
        raise AssertionError((method, path, status, expected, raw[:300]))
    return json.loads(raw or b"{}")


def _auto_rows(base: str, invitation_id: str, token: str):
    rows = _req(base, f"/api/invitations/{invitation_id}/versions", token=token)
    return [row for row in rows if row.get("isAuto")]


def test_draft_save_snapshots_and_restores():
    with temporary_data("einvite-lt-3-9-auto-") as data_dir:
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": str(data_dir),
            "EINVITE_DEV_AUTH_TOKENS": "1",
            "PYTHONPATH": os.pathsep.join([str(REPO / "src" / "python"), str(REPO)]),
        }
        process = subprocess.Popen(
            [sys.executable, "-u", str(REPO / "src" / "python" / "server.py"),
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", **process_options(),
        )
        try:
            wait_http(base + "/api/health", timeout=24.0, process=process)
            owner = _req(
                base, "/api/auth/register", "POST",
                {"email": "auto-versions@example.com", "password": "strong-auto-password"},
                expected=201,
            )
            token = owner["token"]
            document = {"schemaVersion": 13, "fields": {"names": "Created Draft"}, "objects": {}, "designPages": [],
                        "sectionOrder": ["events"], "settings": {"rsvpEnabled": False, "openingEnabled": False},
                        "events": [{"id": "main", "name": "Ceremony", "date": "2027-01-10", "time": "10:00",
                                    "venue": "Hall", "enabled": True}]}
            invite = _req(base, "/api/invitations", "POST",
                          {"slug": "lt-3-9-auto", "document": document}, token=token, expected=201)
            invitation_id = invite["id"]

            saved = dict(document, fields={"names": "Auto Saved"})
            _req(base, f"/api/invitations/{invitation_id}", "PUT", {"document": saved}, token=token)
            rows = _auto_rows(base, invitation_id, token)
            assert len(rows) == 1, rows
            assert rows[0]["version"] == "auto" and rows[0]["isAuto"] is True, rows
            assert isinstance(rows[0]["id"], str) and rows[0]["id"], rows

            # Same content again: no second snapshot.
            _req(base, f"/api/invitations/{invitation_id}", "PUT", {"document": saved}, token=token)
            assert len(_auto_rows(base, invitation_id, token)) == 1

            # A real change inside five minutes: still no second snapshot.
            later = dict(document, fields={"names": "Later Draft"})
            _req(base, f"/api/invitations/{invitation_id}", "PUT", {"document": later}, token=token)
            assert len(_auto_rows(base, invitation_id, token)) == 1

            # Restore-as-draft through the existing endpoint, by snapshot id.
            restored = _req(base, f"/api/invitations/{invitation_id}/restore-version", "POST",
                            {"version": rows[0]["id"]}, token=token)
            assert restored["document"]["fields"]["names"] == "Auto Saved", restored
            snapshot = _req(base, f"/api/invitations/{invitation_id}/versions/{rows[0]['id']}", token=token)
            current = _req(base, f"/api/invitations/{invitation_id}", token=token)
            assert current["document"] == snapshot["document"], (current["document"], snapshot["document"])
            assert current["document"]["fields"]["names"] == "Auto Saved"
        finally:
            stop_process(process)
            if process.stderr:
                err = process.stderr.read()
                if err and process.returncode not in (0, -15):
                    print(err, file=sys.stderr)
    print("LT_3_9_AUTO_VERSIONS_PASSED", flush=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))
