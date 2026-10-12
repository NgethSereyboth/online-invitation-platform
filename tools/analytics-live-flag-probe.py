#!/usr/bin/env python3
"""analytics-live-flag-probe.py — prove the two analytics paths the shipped
suites cannot reach (Goal 1, evidence).

Why this exists
---------------
tests/analytics_reports_test.py::test_phase6_live_endpoint_feature_flag checks
the *flag-off* branch (403) and then tries to flip the flag by POSTing
``/api/admin/feature-flags``. That write route is PUT-only, requires
``role=admin`` and takes ``{"updates": [{key, value}]}``, so the test's own
200-branch can never execute and it prints "skipped" instead. This probe
exercises the branch directly against a real server:

  1. boot the app server with the repository's own harness,
  2. register + login a host, create an invitation (both anonymous guests),
  3. ingest a view through POST /api/analytics/events,
  4. GET the live endpoint   -> expect 403 code=feature_disabled,
  5. promote that user to admin in the server's SQLite file,
  6. PUT /api/admin/feature-flags {analytics_live_enabled: true},
  7. GET the live endpoint again -> expect 200 with activeSessions/lastEventAt,
  8. a second user asks for the first user's invitation -> expect 404.

Usage:  .venv/bin/python tools/analytics-live-flag-probe.py
Exit code 0 means every expectation above held.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))
sys.path.insert(0, str(ROOT))

from tests.v14_test_utils import app_server  # noqa: E402

os.environ.setdefault("EINVITE_ALLOW_NO_SCANNER", "1")
PASSWORD = "Password123!"
CHECKS: list[tuple[str, bool, str]] = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok), detail))
    print(f"[{'ok' if ok else 'FAIL'}] {label} {detail}".rstrip(), flush=True)


def call(base, path, *, method="GET", body=None, headers=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"} if data is not None else {}
    hdrs.update(headers or {})
    if token:
        hdrs["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as exc:  # noqa: BLE001 - probe reports transport failures verbatim
        return None, str(exc).encode()


def register_and_login(base, email):
    s, b = call(base, "/api/auth/register", method="POST", body={"email": email, "password": PASSWORD})
    assert s == 201, f"register {s} {b!r}"
    s, b = call(base, "/api/auth/login", method="POST", body={"email": email, "password": PASSWORD})
    assert s == 201, f"login {s} {b!r}"
    return json.loads(b)["token"]


def main():
    with app_server() as (_proc, base, data):
        host_token = register_and_login(base, "live-probe-host@example.com")
        other_token = register_and_login(base, "live-probe-other@example.com")
        s, b = call(base, "/api/invitations", method="POST", body={"slug": "live-probe"}, token=host_token)
        assert s == 201, f"create invitation {s} {b!r}"
        inv_id = json.loads(b)["id"]

        sid = "%032x" % 7
        now = int(time.time() * 1000)
        s, b = call(base, "/api/analytics/events", method="POST",
                    body={"sessionId": sid, "invitationId": inv_id,
                          "events": [{"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}}]})
        check("ingest accepted (204) before the flag is touched", s == 204, f"status={s}")

        s, b = call(base, f"/api/invitations/{inv_id}/analytics/live", token=host_token)
        body = json.loads(b) if b[:1] == b"{" else {}
        check("live is 403 feature_disabled by default",
              s == 403 and body.get("code") == "feature_disabled", f"status={s} body={body}")

        # Promote the host to admin in the server's own database (the harness
        # gives no admin-registration route; role is a column on users).
        db_path = Path(data) / "invites.db"
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE users SET role='admin' WHERE email=?", ("live-probe-host@example.com",))
        conn.commit()
        conn.close()

        s, b = call(base, "/api/admin/feature-flags", method="PUT",
                    body={"updates": [{"key": "analytics_live_enabled", "value": True}]}, token=host_token)
        check("admin PUT flips analytics_live_enabled", s == 200, f"status={s} body={b[:160]!r}")

        s, b = call(base, f"/api/invitations/{inv_id}/analytics/live", token=host_token)
        payload = json.loads(b) if s == 200 else {}
        check("live returns 200 with activeSessions + lastEventAt once the flag is on",
              s == 200 and "activeSessions" in payload and "lastEventAt" in payload,
              f"status={s} body={payload}")

        s, b = call(base, f"/api/invitations/{inv_id}/analytics/live", token=other_token)
        check("live is 404 for a non-host", s == 404, f"status={s}")

        # The ingest route must not leak a deleted invitation's analytics.
        s, b = call(base, "/api/analytics/events", method="POST",
                    body={"sessionId": "%032x" % 8, "invitationId": "does-not-exist",
                          "events": [{"type": "invitation.view", "ts": now, "payload": {}}]})
        check("ingest for an unknown invitation is 404", s == 404, f"status={s}")

        # A malformed batch is rejected, not silently stored.
        s, b = call(base, "/api/analytics/events", method="POST",
                    body={"sessionId": "short", "invitationId": inv_id,
                          "events": [{"type": "invitation.view", "ts": now, "payload": {}}]})
        check("ingest with an invalid sessionId is 400", s == 400, f"status={s}")

    failed = [label for label, ok, _ in CHECKS if not ok]
    print(f"\nANALYTICS_LIVE_FLAG_PROBE: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
