#!/usr/bin/env python3
"""V54.31 phase-4b — Y.js dual-write + V31→V52 migration test (ROADMAP-V2 §4.2).

Verifies Phase A (dual-write) of the V31→V52 CRDT migration:
  1. With EINVITE_COLLAB_V52_DUALWRITE=1, a V52 update POST writes to BOTH
     collaboration_updates_v52 AND collaboration_updates (V31 table).
  2. A V31 update POST writes to collaboration_updates (V31 table).
  3. The V52 snapshot endpoint returns migratedFrom='v31' when no V52
     history exists yet (Phase A migration marker).
  4. After a V52 update, migratedFrom is None (V52 history exists).
  5. The V31 endpoint still works (V31 remains authoritative for reads
     during Phase A).
  6. V52 update idempotency: re-posting same (client_id, clock) returns
     duplicate=true (not a new row).

Run: ``PYTHONPATH=src/python:. EINVITE_COLLAB_V52_DUALWRITE=1 python3 tests/v52_dualwrite_migration_test.py``
"""

from __future__ import annotations
import os
import sys
import time
import json
import base64
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))
from v14_test_utils import app_server  # type: ignore


def _do(opener, method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=10) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


def register(base: str, email: str, password: str = "Test1234!Pass") -> dict:
    body = json.dumps({"email": email, "password": password, "name": email.split("@")[0]}).encode()
    req = urllib.request.Request(f"{base}/api/auth/register", data=body, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


def login_session(base: str, email: str, password: str = "Test1234!Pass"):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(f"{base}/api/auth/login", data=body, method="POST",
                                  headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=10) as r:
        data = json.loads(r.read())
    return opener, data


def post_v31_update(opener, base: str, invite_id: str, actor: str, clock: int) -> dict:
    return _do(opener, "POST", f"{base}/api/invitations/{invite_id}/collaboration/v31/updates", {
        "actor": actor,
        "epoch": 1,
        "updates": [{
            "id": f"v31-{actor}-{clock}",
            "actor": actor,
            "clock": clock,
            "type": "set",
            "path": ["title"],
            "payload": {"value": f"Edit {clock}"},
            "timestamp": int(time.time() * 1000),
            "origin": "test",
        }],
    })


def post_v52_update(opener, base: str, invite_id: str, client_id: str, clock: int) -> dict:
    update_bytes = bytes([0, 1, 2, clock % 256, 0, 0, 0, 0])
    return _do(opener, "POST", f"{base}/api/invitations/{invite_id}/collaboration/v52/updates", {
        "clientId": client_id,
        "clock": clock,
        "update": base64.b64encode(update_bytes).decode("ascii"),
        "epoch": 1,
    })


def get_v52_snapshot(opener, base: str, invite_id: str) -> dict:
    return _do(opener, "GET", f"{base}/api/invitations/{invite_id}/collaboration/v52/snapshot")


def get_v31_snapshot(opener, base: str, invite_id: str) -> dict:
    return _do(opener, "GET", f"{base}/api/invitations/{invite_id}/collaboration/v31/snapshot")


def create_invitation(opener, base: str) -> str:
    data = _do(opener, "POST", f"{base}/api/invitations", {"title": "Dual-write test", "eventType": "wedding"})
    return data.get("id") or data.get("invitationId")


def main() -> int:
    with app_server(extra_env={"EINVITE_COLLAB_V52_DUALWRITE": "1"}) as (process, base, data_dir):
        email = f"dualwrite-{int(time.time())}@einvite.test"
        reg = register(base, email)
        if not reg.get("user") and not reg.get("ok"):
            print(f"[WARN] register response: {reg}")
        opener, login_data = login_session(base, email)
        if not login_data.get("user") and not login_data.get("ok"):
            print(f"FAIL: login failed: {login_data}")
            return 1
        print("[OK] host account registered + logged in")

        invite_id = create_invitation(opener, base)
        if not invite_id:
            print(f"FAIL: could not create invitation; response={invite_id}")
            return 1
        print(f"[OK] created invitation {invite_id}")

        # Phase A1: V31 update first (simulates existing V31 history)
        v31_resp = post_v31_update(opener, base, invite_id, "alice", 1)
        if not v31_resp.get("acknowledged"):
            print(f"FAIL: V31 update not acknowledged: {v31_resp}")
            return 1
        print(f"[OK] V31 update posted (revision={v31_resp.get('revision')})")

        # Phase A2: V52 snapshot should return migratedFrom='v31' (no V52 history yet)
        snap = get_v52_snapshot(opener, base, invite_id)
        if snap.get("migratedFrom") != "v31":
            print(f"FAIL: V52 snapshot migratedFrom should be 'v31', got: {snap.get('migratedFrom')}")
            return 1
        print(f"[OK] V52 snapshot returns migratedFrom='v31' (no V52 history yet)")

        # Phase A3: V31 endpoint still works (V31 is authoritative during Phase A)
        v31_snap = get_v31_snapshot(opener, base, invite_id)
        if v31_snap.get("epoch") != 1:
            print(f"FAIL: V31 snapshot epoch mismatch: {v31_snap.get('epoch')}")
            return 1
        v31_rev_before = v31_snap.get("revision", 0)
        print(f"[OK] V31 endpoint still works (epoch={v31_snap.get('epoch')}, revision={v31_rev_before})")

        # Phase A4: Post a V52 update — with DUALWRITE=1, it should ALSO write to V31
        v52_resp = post_v52_update(opener, base, invite_id, "bob", 1)
        if not v52_resp.get("acknowledged"):
            print(f"FAIL: V52 update not acknowledged: {v52_resp}")
            return 1
        if not v52_resp.get("dualWrite"):
            print(f"FAIL: V52 update should have dualWrite=true when EINVITE_COLLAB_V52_DUALWRITE=1, got: {v52_resp}")
            return 1
        print(f"[OK] V52 update posted (revision={v52_resp.get('revision')}, dualWrite={v52_resp.get('dualWrite')})")

        # Phase A5: After V52 update, migratedFrom should be None (V52 history exists)
        snap2 = get_v52_snapshot(opener, base, invite_id)
        if snap2.get("migratedFrom") is not None:
            print(f"FAIL: V52 snapshot migratedFrom should be None after V52 history exists, got: {snap2.get('migratedFrom')}")
            return 1
        print(f"[OK] V52 snapshot migratedFrom=None after V52 history exists (revision={snap2.get('revision')})")

        # Phase A6: V31 snapshot should now include the dual-written V31 row
        # (the V52 update's dual-write inserts a V31 row marked yjsDualWrite=True).
        # The V31 MAX(revision) may not advance (revision is per-table), but the
        # row should be present in the V31 updates list.
        v31_snap2 = get_v31_snapshot(opener, base, invite_id)
        v31_updates = v31_snap2.get("updates") or []
        dual_write_rows = [u for u in v31_updates if u.get("payload", {}).get("yjsDualWrite") is True]
        if not dual_write_rows:
            print(f"FAIL: V31 snapshot should include the dual-written row (yjsDualWrite=True), got updates: {[u.get('payload') for u in v31_updates]}")
            return 1
        print(f"[OK] V31 snapshot includes {len(dual_write_rows)} dual-written row(s) from V52 update")

        # Phase A7: Idempotency — posting the same V52 update twice should not duplicate
        v52_resp2 = post_v52_update(opener, base, invite_id, "bob", 1)
        if not v52_resp2.get("duplicate"):
            print(f"FAIL: re-posting same V52 update should return duplicate=true, got: {v52_resp2}")
            return 1
        print(f"[OK] V52 idempotency: duplicate re-post returns duplicate=true")

        # Phase A8: V52 snapshot should now list the V52 update
        snap3 = get_v52_snapshot(opener, base, invite_id)
        updates = snap3.get("updates") or []
        if not updates:
            print(f"FAIL: V52 snapshot should have updates after the V52 POST, got: {updates}")
            return 1
        print(f"[OK] V52 snapshot has {len(updates)} update(s)")

    print()
    print("V52_DUALWRITE_MIGRATION_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
