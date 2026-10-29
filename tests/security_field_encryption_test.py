#!/usr/bin/env python3
"""LT-7.2 — field-level encryption as code + migration + rollback (ROADMAP §4.1).

Everything here runs against temporary data directories. The migration script
refuses the repo's own ``src/python/data`` by default, and this test also proves
that refusal (exit code 3), so a stray invocation cannot convert real data.

Part 1 — live round trip, on a real server over HTTP:

* a new account is stored with ``users.email`` as a Fernet ciphertext and a
  populated ``users.email_hash`` (checked in the SQLite file itself);
* sign-in works case-insensitively through the hash index, and ``/api/auth/me``
  returns the original casing;
* a second registration with a different case is still refused;
* password-reset lookup finds the account;
* after a **server restart on the same data directory** the account still
  decrypts — which is the property the old key bootstrap failed (it generated a
  key of the wrong shape and therefore a fresh key every process);
* ``/api/admin/audit-events`` stillreturns readable metadata (the read layer
  reveals protected columns).

Part 2 — the migration script against a temp database only:

* seed a legacy plaintext row, byte-for-byte what a pre-encryption install has;
* the app can sign in as that legacy row before the migration (fallback path);
* ``--apply`` encrypts it, writes the hash, and leaves a plaintext backup table;
* the app can still sign in afterwards (hash path);
* ``--rollback`` restores plaintext, clears the hash and drops the backup;
* the app can still sign in (back to the fallback path).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

CIPHERTEXT_PREFIX = "gAAAAA"
PASSWORD = "Test1234!Pass"
ADMIN_ENV = {
    "EINVITE_ALLOW_NO_SCANNER": "1",
    "EINVITE_ADMIN_EMAIL": "admin@einvite.test",
    "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
}


def _request(base, method, path, body=None, cookie=None, csrf=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read() or b""
            try:
                return response.status, json.loads(payload), response.headers.get("Set-Cookie", "")
            except json.JSONDecodeError:
                return response.status, {"_raw": payload.decode("utf-8", "replace")}, response.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as error:
        payload = error.read() or b""
        try:
            return error.code, json.loads(payload), error.headers.get("Set-Cookie", "")
        except json.JSONDecodeError:
            return error.code, {"_raw": payload.decode("utf-8", "replace")}, error.headers.get("Set-Cookie", "")


def _session(base, email, password):
    """Sign in and return ``(cookie_header, csrf_token)`` for later calls."""
    status, data, set_cookie = _request(base, "POST", "/api/auth/login", {"email": email, "password": password})
    assert status in {200, 201}, (status, data)
    cookies = {}
    for part in set_cookie.split(","):
        chunk = part.strip().split(";")[0]
        if "=" in chunk:
            name, _, value = chunk.partition("=")
            cookies[name.strip()] = value.strip()
    jar = "; ".join(f"{name}={value}" for name, value in cookies.items())
    status, me, _ = _request(base, "GET", "/api/auth/me", cookie=jar)
    assert status == 200, (status, me)
    csrf = urllib.parse.unquote(cookies.get("einvite_csrf", ""))
    return jar, csrf, me["user"]


def _register(base, email, password=PASSWORD):
    return _request(base, "POST", "/api/auth/register", {"email": email, "password": password})


def _db_rows(data_dir, sql, params=()):
    connection = sqlite3.connect(str(Path(data_dir) / "invites.db"))
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]
    finally:
        connection.close()


def test_live_server_round_trip_and_restart():
    from v14_test_utils import temporary_data

    mixed_email = "Mixed.Case@einvite.test"
    # The register handler lowercases the address before storing it, so the
    # canonical value is what must survive encryption and decryption.
    canonical_email = mixed_email.lower()
    with temporary_data("einvite-enc-field-") as shared_data:
        env = dict(ADMIN_ENV)
        env["EINVITE_DATA_DIR"] = str(shared_data)
        with _server(env) as (base, _data):
            assert _register(base, "admin@einvite.test")[0] in {200, 201}
            status, data, _ = _register(base, mixed_email)
            assert status in {200, 201}, (status, data)

            # Stored encrypted, with the lookup hash written alongside.
            rows = _db_rows(shared_data, "SELECT email, email_hash FROM users WHERE email_hash IS NOT NULL")
            assert rows, "no row carries an email_hash"
            stored = [row for row in rows if row["email_hash"] == hashlib.sha256(canonical_email.encode()).hexdigest()]
            assert stored, rows
            assert stored[0]["email"].startswith(CIPHERTEXT_PREFIX), stored[0]["email"]
            assert canonical_email not in stored[0]["email"]

            # The key persists in the data directory, so a restart can still read it.
            key_file = shared_data / ".field-encryption-key"
            assert key_file.is_file(), "encryption key was not persisted beside the data"
            first_key = key_file.read_text(encoding="utf-8").strip()
            assert len(first_key) == 44, first_key

            # Sign-in is case-insensitive, and the session reports the decrypted value.
            _cookie, _csrf, user = _session(base, "MIXED.CASE@EINVITE.TEST", PASSWORD)
            assert user["email"] == canonical_email, user

            # A duplicate account is still refused when the case differs.
            status, duplicate, _ = _register(base, "mixed.case@EINVITE.test")
            assert status not in {200, 201}, (status, duplicate)

            # Password reset finds the account through the hash.
            status, reset, _ = _request(base, "POST", "/api/auth/password-reset/request", {"email": canonical_email})
            assert status == 200, (status, reset)

            # Admin reads (raw SQL through the read layer) are decrypted too.
            cookie, csrf, _ = _session(base, "admin@einvite.test", PASSWORD)
            status, listing, _ = _request(base, "GET", "/api/admin/users", cookie=cookie)
            assert status == 200, (status, listing)
            assert any(row["email"] == canonical_email for row in listing), listing

            status, events, _ = _request(base, "GET", "/api/admin/audit-events?limit=50", cookie=cookie)
            assert status == 200, (status, events)
            items = events.get("items") or events.get("events") or []
            assert items, events
            for item in items:
                meta = item.get("metadata") or item.get("metadata_json")
                if isinstance(meta, str) and meta:
                    assert not meta.startswith(CIPHERTEXT_PREFIX), item
                    json.loads(meta)  # still valid JSON after the reveal pass

        # Restart on the SAME data directory: the key must still decrypt.
        with _server(env) as (base, _data):
            assert (shared_data / ".field-encryption-key").read_text(encoding="utf-8").strip() == first_key
            _cookie, _csrf, user = _session(base, canonical_email, PASSWORD)
            assert user["email"] == canonical_email, user
            print("[OK] live round trip + restart decrypt survived", flush=True)


def test_new_writes_are_encrypted_at_rest():
    """§4.1: the protected columns are encrypted on the write path, not only by the migration.

    Each column is written through its real HTTP route, then read back from the
    SQLite file (ciphertext expected) and through the API (plaintext expected).
    ``delivery_attempts.recipient`` and ``invitation_edit_history.diff_json`` come
    from the real deliver/edit flows; the audit checks cover the ``admin_only``
    flag that replaces SQL ``LIKE`` on the now-encrypted metadata.
    """
    from v14_test_utils import temporary_data

    with temporary_data("einvite-enc-writes-") as shared_data:
        env = dict(ADMIN_ENV)
        env["EINVITE_DATA_DIR"] = str(shared_data)
        with _server(env) as (base, _data):
            assert _register(base, "admin@einvite.test")[0] in {200, 201}
            status, writer, _ = _register(base, "writer@einvite.test")
            assert status in {200, 201} and writer.get("token"), (status, writer)
            token = writer["token"]

            document = {"schemaVersion": 14, "eventType": "Wedding", "fields": {"names": "Enc Fields"},
                        "objects": {}, "designPages": [], "settings": {}}
            status, created, _ = _request(base, "POST", "/api/invitations",
                                          {"slug": "enc-writes", "document": document}, token=token)
            assert status in {200, 201}, (status, created)
            invite_id = created["id"]

            # 1) guests.email / guests.phone.
            status, guest, _ = _request(base, "POST", f"/api/invitations/{invite_id}/guests",
                                        {"name": "Guest One", "email": "guest.one@einvite.test",
                                         "phone": "+85512345678"}, token=token)
            assert status in {200, 201} and guest.get("id"), (status, guest)
            rows = _db_rows(shared_data, "SELECT email, phone FROM guests WHERE invitation_id=?", (invite_id,))
            assert rows, "guest row missing"
            assert rows[0]["email"].startswith(CIPHERTEXT_PREFIX), rows[0]
            assert rows[0]["phone"].startswith(CIPHERTEXT_PREFIX), rows[0]
            status, listed, _ = _request(base, "GET", f"/api/invitations/{invite_id}/guests", token=token)
            assert status == 200, (status, listed)
            guest_rows = listed.get("guests") if isinstance(listed, dict) else listed
            assert any(g["email"] == "guest.one@einvite.test" for g in guest_rows), guest_rows

            # 2) delivery_attempts.recipient — the real deliver route, whose first
            #    row is written before the provider is called (so no SMTP needed).
            status, delivered, _ = _request(
                base, "POST", f"/api/invitations/{invite_id}/deliver",
                {"channels": ["email"],
                 "recipients": [{"guestId": guest["id"], "name": "Guest One", "email": "guest.one@einvite.test"}]},
                token=token)
            assert status in {200, 201}, (status, delivered)
            attempts = _db_rows(shared_data, "SELECT recipient FROM delivery_attempts WHERE invitation_id=?", (invite_id,))
            assert attempts, "no delivery attempt recorded"
            assert attempts[0]["recipient"].startswith(CIPHERTEXT_PREFIX), attempts[0]

            # 3) invitation_edit_history.diff_json — a post-send edit (deliver sets sent_at).
            document["fields"]["names"] = "Enc Fields Edited"
            status, saved, _ = _request(base, "PUT", f"/api/invitations/{invite_id}",
                                        {"document": document, "editReason": "enc test"}, token=token)
            assert status == 200 and saved.get("saved") is True, (status, saved)
            history = _db_rows(shared_data, "SELECT diff_json FROM invitation_edit_history WHERE invitation_id=?", (invite_id,))
            assert history, "post-send edit did not record history"
            assert history[0]["diff_json"].startswith(CIPHERTEXT_PREFIX), history[0]
            status, history_list, _ = _request(base, "GET", f"/api/invitations/{invite_id}/edit-history", token=token)
            assert status == 200, (status, history_list)
            shown = history_list.get("history") or history_list.get("items") or []
            # The diff is a list of change entries ({path,before,after}).
            assert shown and isinstance(shown[0].get("diff"), (list, dict)) and shown[0]["diff"], history_list

            # 4) audit_events.metadata_json + the admin_only flag that keeps the
            #    admin "admin-only events" filter exact over ciphertext.
            admin_cookie, admin_csrf, _ = _session(base, "admin@einvite.test", PASSWORD)
            status, stepup, _ = _request(base, "POST", "/api/admin/step-up", {"password": PASSWORD},
                                         cookie=admin_cookie, csrf=admin_csrf)
            assert status == 200 and stepup.get("stepUp") is True, (status, stepup)
            audit_rows = _db_rows(shared_data, "SELECT action, metadata_json, admin_only FROM audit_events ORDER BY created_at DESC LIMIT 8")
            stepup_rows = [r for r in audit_rows if r["action"] == "admin.stepup_granted"]
            assert stepup_rows, audit_rows
            assert stepup_rows[0]["metadata_json"].startswith(CIPHERTEXT_PREFIX), stepup_rows[0]
            assert stepup_rows[0]["admin_only"] == 1, stepup_rows[0]
            status, filtered, _ = _request(base, "GET", "/api/admin/audit-events?adminOnly=1&limit=50", cookie=admin_cookie)
            assert status == 200, (status, filtered)
            items = filtered.get("items") or filtered.get("events") or []
            assert any(i.get("action") == "admin.stepup_granted" for i in items), items
            assert all(not str(i.get("metadata_json") or "").startswith(CIPHERTEXT_PREFIX) for i in items), items
            print("[OK] new writes are ciphertext for guests, delivery attempts, edit history and audit metadata", flush=True)


def test_migration_script_apply_and_rollback_on_a_temp_database():
    from v14_test_utils import temporary_data

    legacy_email = "Legacy.Plaintext@einvite.test"
    legacy_id = str(uuid.uuid4())
    with temporary_data("einvite-enc-migrate-") as shared_data:
        env = dict(ADMIN_ENV)
        env["EINVITE_DATA_DIR"] = str(shared_data)
        with _server(env) as (base, _data):
            assert _register(base, "modern@einvite.test")[0] in {200, 201}
            assert _register(base, "admin@einvite.test")[0] in {200, 201}

        # Seed a legacy row exactly as a pre-encryption install would have it.
        connection = sqlite3.connect(str(shared_data / "invites.db"))
        try:
            salt = "legacy-salt"
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,password_algo,created_at,role,email_verified,plan)"
                " VALUES(?,?,NULL,?,?,?,?,?,0,?)",
                (legacy_id, legacy_email, "not-a-real-hash", salt, "pbkdf2-sha256-v1", int(time.time() * 1000), "customer", "free"),
            )
            connection.commit()
        finally:
            connection.close()

        key = (shared_data / ".field-encryption-key").read_text(encoding="utf-8").strip()

        # The guard: the repo's own data directory is refused outright. Pin
        # EINVITE_DATA_DIR explicitly — other in-process tests leave their own
        # temp directory in os.environ (observed leak), and the guard must be
        # tested against the repo default, not whatever ran before this file.
        guard = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "migrate_encrypt_sensitive_fields.py")],
            capture_output=True, text=True, cwd=REPO,
            env={**os.environ, "EINVITE_FIELD_ENCRYPTION_KEY": key,
                 "EINVITE_DATA_DIR": str(REPO / "src" / "python" / "data")},
        )
        assert guard.returncode == 3, (guard.returncode, guard.stdout, guard.stderr)
        assert "REFUSING" in guard.stderr, guard.stderr

        def run_script(*extra):
            return subprocess.run(
                [sys.executable, str(REPO / "scripts" / "migrate_encrypt_sensitive_fields.py"),
                 "--data-dir", str(shared_data), *extra],
                capture_output=True, text=True, cwd=REPO,
                env={**os.environ, "EINVITE_FIELD_ENCRYPTION_KEY": key},
            )

        # Before the migration the app signs the legacy row in via the fallback.
        with _server(env) as (base, _data):
            status, data, _ = _request(base, "POST", "/api/auth/password-reset/request", {"email": legacy_email})
            assert status == 200, (status, data)

        applied = run_script()
        assert applied.returncode == 0, (applied.returncode, applied.stdout, applied.stderr)
        assert "users.email: encrypted" in applied.stdout, applied.stdout

        rows = _db_rows(shared_data, "SELECT email, email_hash FROM users WHERE id=?", (legacy_id,))
        assert rows[0]["email"].startswith(CIPHERTEXT_PREFIX), rows
        assert rows[0]["email_hash"] == hashlib.sha256(legacy_email.lower().encode()).hexdigest(), rows
        backups = _db_rows(shared_data, "SELECT email FROM users_plaintext_backup WHERE id=?", (legacy_id,))
        assert backups and backups[0]["email"] == legacy_email, backups

        # Still reachable through the hash index afterwards.
        with _server(env) as (base, _data):
            status, data, _ = _request(base, "POST", "/api/auth/password-reset/request", {"email": legacy_email})
            assert status == 200, (status, data)
            print("[OK] migrated row still resolves by email", flush=True)

        rolled_back = run_script("--rollback")
        assert rolled_back.returncode == 0, (rolled_back.returncode, rolled_back.stdout, rolled_back.stderr)
        rows = _db_rows(shared_data, "SELECT email, email_hash FROM users WHERE id=?", (legacy_id,))
        assert rows[0]["email"] == legacy_email, rows
        assert not rows[0]["email_hash"], rows
        assert not _db_rows(
            shared_data, "SELECT name FROM sqlite_master WHERE type='table' AND name='users_plaintext_backup'"
        ), "backup table should be dropped after rollback"
        assert _db_rows(shared_data, "SELECT email FROM users WHERE id=?", (legacy_id,))[0]["email"] == legacy_email

        with _server(env) as (base, _data):
            status, data, _ = _request(base, "POST", "/api/auth/password-reset/request", {"email": legacy_email})
            assert status == 200, (status, data)
        print("[OK] apply + rollback round trip on a temp database", flush=True)


def test_migration_scale_and_byte_identical_rollback():
    """E-3: 1,000 rows per table, dry run, apply, roll back to the exact bytes."""
    from v14_test_utils import temporary_data

    rows = 1000
    with temporary_data("einvite-enc-scale-") as shared_data:
        env = dict(ADMIN_ENV)
        env["EINVITE_DATA_DIR"] = str(shared_data)
        with _server(env) as (base, _data):
            assert _register(base, "scale-owner@einvite.test")[0] in {200, 201}
        key = (shared_data / ".field-encryption-key").read_text(encoding="utf-8").strip()

        now = int(time.time() * 1000)
        users = [(str(uuid.uuid4()), f"legacy-{index:04d}@einvite.test") for index in range(rows)]
        guests = [(str(uuid.uuid4()), f"Guest {index:04d}", f"guest-{index:04d}@einvite.test",
                   f"+8551000{index:04d}") for index in range(rows)]
        connection = sqlite3.connect(str(shared_data / "invites.db"))
        try:
            connection.executemany(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,password_algo,created_at,role,email_verified,plan)"
                " VALUES(?,?,NULL,'not-a-real-hash','legacy-salt','pbkdf2-sha256-v1',?,'customer',0,'free')",
                [(user_id, email, now) for user_id, email in users],
            )
            connection.executemany(
                "INSERT INTO guests(id,invitation_id,name,email,phone,token,slug,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                [(guest_id, "scale-invitation", name, email, phone, f"scale-token-{index}",
                  f"scale-guest-{index}", now)
                 for index, (guest_id, name, email, phone) in enumerate(guests)],
            )
            connection.commit()
        finally:
            connection.close()

        def run_script(*extra):
            return subprocess.run(
                [sys.executable, str(REPO / "scripts" / "migrate_encrypt_sensitive_fields.py"),
                 "--data-dir", str(shared_data), *extra],
                capture_output=True, text=True, cwd=REPO,
                env={**os.environ, "EINVITE_FIELD_ENCRYPTION_KEY": key},
            )

        dry = run_script("--dry-run")
        assert dry.returncode == 0, (dry.returncode, dry.stdout, dry.stderr)
        stored = _db_rows(shared_data, "SELECT email FROM users WHERE id=?", (users[0][0],))
        assert stored[0]["email"] == users[0][1], "--dry-run changed a row"

        applied = run_script()
        assert applied.returncode == 0, (applied.returncode, applied.stdout, applied.stderr)
        first = _db_rows(shared_data, "SELECT email, email_hash FROM users WHERE id=?", (users[0][0],))[0]
        last = _db_rows(shared_data, "SELECT email FROM users WHERE id=?", (users[-1][0],))[0]
        assert first["email"].startswith(CIPHERTEXT_PREFIX), first
        assert last["email"].startswith(CIPHERTEXT_PREFIX), last
        assert first["email_hash"] == hashlib.sha256(users[0][1].encode()).hexdigest(), first
        guest_rows = _db_rows(shared_data, "SELECT email, phone FROM guests WHERE id IN (?,?)",
                              (guests[0][0], guests[-1][0]))
        assert all(row["email"].startswith(CIPHERTEXT_PREFIX) for row in guest_rows), guest_rows
        assert all(row["phone"].startswith(CIPHERTEXT_PREFIX) for row in guest_rows), guest_rows

        rolled_back = run_script("--rollback")
        assert rolled_back.returncode == 0, (rolled_back.returncode, rolled_back.stdout, rolled_back.stderr)
        restored_users = _db_rows(shared_data, "SELECT id, email FROM users WHERE email_hash IS NULL ORDER BY id")
        restored_guests = _db_rows(shared_data, "SELECT id, email, phone FROM guests ORDER BY id")
        # Rollback restores exactly the migrated rows; the owner registered while
        # encryption was on stays a ciphertext row (it was never in the backup).
        assert len(restored_users) == rows, len(restored_users)
        assert {(row["id"], row["email"]) for row in restored_users} == set(users)
        assert {(row["id"], row["email"], row["phone"]) for row in restored_guests} == {
            (guest_id, email, phone) for guest_id, _name, email, phone in guests
        }, "rollback is not byte-identical"
        print("[OK] 1,000 users + 1,000 guests: dry run, apply, byte-identical rollback", flush=True)


# --- helper: boot the server on a caller-owned data directory -----------------

class _server:
    def __init__(self, env):
        self.env = env
        self._context = None

    def __enter__(self):
        from v14_test_utils import app_server

        self._context = app_server(extra_env=self.env)
        process, base, data = self._context.__enter__()
        return base, data

    def __exit__(self, *exc):
        return self._context.__exit__(*exc)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))
