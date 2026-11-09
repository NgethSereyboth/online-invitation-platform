#!/usr/bin/env python3
"""QA deep-dive regression tests for session lifecycle and rapid login.

The existing lockout test proves the 5-failure/15-minute window. This test adds
the two gaps found in the QA audit: logout must delete the server-side session
(not only clear the cookie), and an idle non-admin session must stop resolving.
It also drives ten rapid failures end-to-end so the lockout cannot regress into
a 500 or an unbounded counter.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from v14_test_utils import app_server

PASSWORD = "QA-Deep-Dive-Passw0rd!"


def request(base: str, path: str, method: str = "GET", body=None, token: str = ""):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def register(base: str, email: str):
    status, payload = request(base, "/api/auth/register", "POST", {"email": email, "password": PASSWORD})
    assert status == 201, (status, payload)
    assert payload.get("token"), payload
    return payload["token"], payload["user"]


def test_logout_and_idle_session_invalidation():
    with app_server() as (_proc, base, data):
        token, _user = register(base, "qa-session-logout@example.com")
        assert request(base, "/api/auth/me", token=token)[0] == 200
        status, payload = request(base, "/api/auth/logout", "POST", {}, token=token)
        assert status == 200 and payload.get("signedOut") is True, (status, payload)
        status, payload = request(base, "/api/auth/me", token=token)
        assert status == 200 and payload.get("user") is None, (status, payload)
        with sqlite3.connect(Path(data) / "invites.db") as db:
            remaining = db.execute("SELECT COUNT(*) FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()[0]
        assert remaining == 0, remaining

        idle_token, _user = register(base, "qa-session-idle@example.com")
        assert request(base, "/api/auth/me", token=idle_token)[0] == 200
        token_hash = hashlib.sha256(idle_token.encode()).hexdigest()
        old = int(time.time() * 1000) - 8 * 24 * 60 * 60 * 1000
        with sqlite3.connect(Path(data) / "invites.db") as db:
            db.execute("UPDATE sessions SET last_seen_at=? WHERE token_hash=?", (old, token_hash))
            db.commit()
        status, payload = request(base, "/api/auth/me", token=idle_token)
        assert status == 200 and payload.get("user") is None, (status, payload)


def test_ten_rapid_failures_stay_bounded():
    with app_server() as (_proc, base, _data):
        register(base, "qa-rapid-login@example.com")
        statuses = [
            request(base, "/api/auth/login", "POST", {"email": "qa-rapid-login@example.com", "password": "wrong-password"})[0]
            for _ in range(10)
        ]
        assert statuses[:5] == [401] * 5, statuses
        assert all(status in {401, 423} for status in statuses), statuses
        assert 423 in statuses, statuses
