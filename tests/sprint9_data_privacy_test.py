#!/usr/bin/env python3
"""Sprint 9 — data export, account erasure, retention and log redaction.

The tests run the real HTTP server except for the retention and error-log
units, which call the production functions directly against the same SQLite
schema. No external provider or network service is involved.
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "Sprint9-Passw0rd-2026"


def _http(base, path, method="GET", body=None, headers=None):
    raw = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(base + path, data=raw, method=method,
                                     headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def _json(base, path, method="GET", body=None, headers=None):
    status, response_headers, raw = _http(base, path, method, body, headers)
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        payload = {}
    return status, response_headers, payload


def _register(base, email):
    status, headers, payload = _json(base, "/api/auth/register", "POST",
                                     {"email": email, "password": PASSWORD}, {"Origin": base})
    assert status == 201, (status, payload)
    values = headers.get_all("Set-Cookie") or []
    cookies = "; ".join(value.split(";", 1)[0] for value in values if "=" in value)
    return payload["token"], cookies, payload["csrfToken"]


def _me(base, token):
    status, _, payload = _json(base, "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert status == 200, (status, payload)
    return payload


def _create_invitation(base, token, slug, date="2030-01-01"):
    document = {
        "schemaVersion": 13,
        "fields": {"names": slug, "date": date, "venue": "Privacy Hall"},
        "objects": {},
        "designPages": [],
        "settings": {"rsvpEnabled": True},
    }
    status, _, payload = _json(base, "/api/invitations", "POST",
                               {"slug": slug, "document": document},
                               {"Authorization": f"Bearer {token}", "Origin": base})
    assert status == 201, (status, payload)
    return payload["id"]


@contextlib.contextmanager
def _connect(path):
    connection = sqlite3.connect(str(path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _seed_guest(db, invite_id, name, email, phone, note="private note"):
    guest_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO guests(id,invitation_id,name,phone,email,group_name,tags_json,token,created_at)"
        " VALUES(?,?,?,?,?,'Family','[]',?,?)",
        (guest_id, invite_id, name, phone, email, uuid.uuid4().hex, int(time.time() * 1000)),
    )
    db.execute(
        "INSERT INTO rsvps(id,invitation_id,publication_id,guest_id,name,normalized_name,status,"
        "guest_count,note,created_at,updated_at,answers_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), invite_id, "pub-1", guest_id, name, name.lower(), "attending", 2,
         note, int(time.time() * 1000), int(time.time() * 1000), json.dumps({"meal": "vegan"})),
    )
    return guest_id


def test_export_contains_only_the_callers_data():
    from v14_test_utils import app_server

    with app_server() as (_process, base, data):
        token_a, _, _ = _register(base, "privacy-a@example.com")
        token_b, _, _ = _register(base, "privacy-b@example.com")
        invite_a = _create_invitation(base, token_a, "privacy-export-a")
        invite_b = _create_invitation(base, token_b, "privacy-export-b")
        with _connect(data / "invites.db") as db:
            _seed_guest(db, invite_a, "Alice Guest", "alice@example.com", "+15550001111")
            _seed_guest(db, invite_b, "Bob Guest", "bob@example.com", "+15550002222")
            owner_a = _me(base, token_a)["user"]["id"]
            db.execute("INSERT INTO user_templates(id,owner_id,name,category,document_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                       (str(uuid.uuid4()), owner_a, "Private template", "Wedding", "{}", int(time.time() * 1000), int(time.time() * 1000)))
        status, headers, exported = _json(base, "/api/user/data-export",
                                          headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200, (status, exported)
        assert exported["account"]["email"] == "privacy-a@example.com"
        assert [item["id"] for item in exported["invitations"]] == [invite_a]
        assert any(item["email"] == "alice@example.com" for item in exported["guests"])
        assert all(item["email"] != "bob@example.com" for item in exported["guests"])
        assert all(item["id"] != invite_b for item in exported["rsvps"])
        assert any(item["name"] == "Private template" for item in exported["templates"])
        assert headers.get("Cache-Control") == "private, no-store"


def test_account_deletion_requires_auth_csrf_and_password_then_anonymizes():
    from v14_test_utils import app_server

    with app_server() as (_process, base, data):
        token, cookies, csrf = _register(base, "delete-me@example.com")
        private_invite = _create_invitation(base, token, "delete-private", "2030-01-01")
        public_invite = _create_invitation(base, token, "delete-public", "2020-01-01")
        from core.outbound_queue import ensure_schema as ensure_outbound_schema
        ensure_outbound_schema(lambda: _connect(data / "invites.db"))
        with _connect(data / "invites.db") as db:
            db.execute("UPDATE invitations SET is_published=1 WHERE id=?", (public_invite,))
            db.execute("INSERT INTO outbound_retry_queue(id,invitation_id,channel,recipient,message_text,next_attempt_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                       (str(uuid.uuid4()), public_invite, "email", "public@example.com", "Public Person", 0, 0, 0))
            _seed_guest(db, private_invite, "Private Person", "private@example.com", "+15550003333")
            _seed_guest(db, public_invite, "Public Person", "public@example.com", "+15550004444")
        # Authentication is required before the body is read.
        status, _, _ = _json(base, "/api/user/account", "DELETE", {"password": PASSWORD},
                             {"Origin": base})
        assert status == 401
        # A valid session without CSRF must be rejected.
        status, _, _ = _json(base, "/api/user/account", "DELETE", {"password": PASSWORD},
                             {"Origin": base, "Cookie": cookies})
        assert status == 403
        # A valid CSRF token with the wrong password must not erase anything.
        status, _, _ = _json(base, "/api/user/account", "DELETE", {"password": "wrong-password"},
                             {"Origin": base, "Cookie": cookies, "X-CSRF-Token": csrf})
        assert status == 401
        status, _, result = _json(base, "/api/user/account", "DELETE", {"password": PASSWORD},
                                  {"Origin": base, "Cookie": cookies, "X-CSRF-Token": csrf})
        assert status == 200, result
        assert result["deleted"] is True and result["loginDisabled"] is True
        # The account cannot log in after the response.
        login_status, _, _ = _json(base, "/api/auth/login", "POST",
                                   {"email": "delete-me@example.com", "password": PASSWORD},
                                   {"Origin": base})
        assert login_status == 401
        with _connect(data / "invites.db") as db:
            # Sessions were shredded, so use the surviving tombstone row.
            user = db.execute("SELECT email,deleted_at FROM users WHERE email LIKE 'deleted-%@invalid'").fetchone()
            assert user is not None and user["deleted_at"]
            assert "delete-me@example.com" not in str(dict(user))
            private_row = db.execute("SELECT deleted_at,draft_json FROM invitations WHERE id=?", (private_invite,)).fetchone()
            public_row = db.execute("SELECT deleted_at FROM invitations WHERE id=?", (public_invite,)).fetchone()
            assert private_row["deleted_at"] is not None
            assert json.loads(private_row["draft_json"]).get("fields") == {}
            assert public_row["deleted_at"] is None  # public/past invitation is preserved
            guests = db.execute("SELECT name,email,phone FROM guests WHERE invitation_id=?", (public_invite,)).fetchall()
            assert guests and all(row["name"].startswith("Guest ") for row in guests)
            assert all(not row["email"] and not row["phone"] for row in guests)
            rsvp = db.execute("SELECT name,note,answers_json FROM rsvps WHERE invitation_id=?", (public_invite,)).fetchone()
            assert rsvp["name"].startswith("Guest ") and rsvp["note"] == "[REDACTED_PII]"
            assert rsvp["answers_json"] == "{}"
            assert db.execute("SELECT COUNT(*) FROM user_templates WHERE owner_id=(SELECT id FROM users WHERE email LIKE 'deleted-%@invalid')").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM outbound_retry_queue WHERE invitation_id=?", (public_invite,)).fetchone()[0] == 0


def test_retention_anonymizes_only_events_older_than_the_window():
    from core.privacy import run_pii_retention
    from v14_test_utils import app_server

    with app_server() as (_process, base, data):
        token, _, _ = _register(base, "retention@example.com")
        old_invite = _create_invitation(base, token, "retention-old", "2020-01-01")
        fresh_invite = _create_invitation(base, token, "retention-fresh", "2030-01-01")
        with _connect(data / "invites.db") as db:
            _seed_guest(db, old_invite, "Old Guest", "old@example.com", "+15550005555", "old comment")
            _seed_guest(db, fresh_invite, "Fresh Guest", "fresh@example.com", "+15550006666", "fresh comment")
        result = run_pii_retention(lambda: _connect(data / "invites.db"), retention_days=90)
        assert result["anonymizedInvitations"] >= 1
        with _connect(data / "invites.db") as db:
            old = db.execute("SELECT name,email,phone FROM guests WHERE invitation_id=?", (old_invite,)).fetchone()
            fresh = db.execute("SELECT name,email,phone FROM guests WHERE invitation_id=?", (fresh_invite,)).fetchone()
            old_rsvp = db.execute("SELECT note FROM rsvps WHERE invitation_id=?", (old_invite,)).fetchone()
            assert old["name"].startswith("Guest ") and old["email"] == "" and old["phone"] == ""
            assert old_rsvp["note"] == "[REDACTED_PII]"
            assert fresh["name"] == "Fresh Guest" and fresh["email"] == "fresh@example.com"


def test_structured_logs_redact_pii_marker():
    from v14_test_utils import app_server

    with app_server(extra_env={"EINVITE_JSON_LOGS": "1"}) as (_process, base, data):
        _register(base, "log-privacy@example.com")
        status, _, _ = _http(base, "/api/public/no-such-invite?email=alice%40example.com")
        assert status == 404
        time.sleep(0.2)
        log = (data / "server-test.log").read_text(encoding="utf-8")
        assert "alice@example.com" not in log
        assert "[REDACTED_PII]" in log


def test_async_export_completes_and_downloads():
    import io
    import zipfile
    from v14_test_utils import app_server

    with app_server(extra_env={"EINVITE_PRIVACY_EXPORT_ASYNC_BYTES": "1"}) as (_process, base, _data):
        token, _, _ = _register(base, "async-export@example.com")
        invite_id = _create_invitation(base, token, "async-export-invite")
        status, _, queued = _json(base, "/api/user/data-export",
                                  headers={"Authorization": f"Bearer {token}"})
        assert status == 202, queued
        assert queued["status"] == "queued" and queued["downloadUrl"]
        deadline = time.time() + 15
        completed = None
        while time.time() < deadline:
            state, _, completed = _json(base, queued["downloadUrl"],
                                        headers={"Authorization": f"Bearer {token}"})
            if state == 200 and completed.get("status") == "completed":
                break
            time.sleep(0.1)
        assert completed and completed.get("status") == "completed", completed
        status, headers, raw = _http(base, queued["downloadUrl"] + "/download",
                                     headers={"Authorization": f"Bearer {token}"})
        assert status == 200 and headers.get("Content-Type") == "application/zip"
        archive = zipfile.ZipFile(io.BytesIO(raw))
        payload = json.loads(archive.read("account.json"))
        assert any(item["id"] == invite_id for item in payload["invitations"])


def test_error_logging_scrubs_pii(capsys):
    import server

    handler = object.__new__(server.Handler)
    handler.request_id = "sprint9-log-test"
    handler.log_failure("privacy_probe", ValueError("contact alice@example.com or +15550007777"))
    output = capsys.readouterr().out
    assert "alice@example.com" not in output
    assert "+15550007777" not in output
    assert "[REDACTED_PII]" in output
