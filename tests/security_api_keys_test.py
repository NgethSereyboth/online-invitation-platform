#!/usr/bin/env python3
"""LT-7.2 step 5 — API keys: generate, scope, revoke (ROADMAP §4.5).

Against a real server on a pinned temp data directory (field encryption off so
the audit metadata is directly assertable):

* create returns the plaintext key exactly once, `einv_` prefixed, with the
  stored row holding only a hash (Argon2id or the PBKDF2 fallback) and the last
  4 characters;
* list never returns the secret;
* an `rsvps:read` key can read RSVPs and is refused (403
  ``api_key_scope_denied``) on any route outside the API-key allowlist;
* an `invitations:write` key can create an invitation but not read RSVPs;
* a tampered key fails authentication;
* every accepted API request writes an ``api.request`` audit row whose metadata
  carries ``auth=api_key``;
* revoke makes the key stop working immediately.

The per-key rate limit (1000 requests/hour, `rate_limit(f"api-key:{id}",1000,3600)`)
is wired in the auth path; this test does not flood 1000 requests to prove it.

Prints ``LT_7_2_API_KEYS_PASSED`` on success.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from v14_test_utils import app_server, temporary_data  # noqa: E402


def _request(base, method, path, body=None, token=None, api_key=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        payload = error.read() or b"{}"
        try:
            return error.code, json.loads(payload)
        except json.JSONDecodeError:
            return error.code, {"_raw": payload.decode("utf-8", "replace")}


def _db_rows(db_file, sql, params=()):
    connection = sqlite3.connect(str(db_file))
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]
    finally:
        connection.close()


def test_api_keys_generate_scope_revoke():
    with temporary_data("einvite-lt-7-2-keys-") as data_dir:
        env = {
            "EINVITE_DATA_DIR": str(data_dir),
            "EINVITE_DEV_AUTH_TOKENS": "1",
            "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
            "EINVITE_ALLOW_NO_SCANNER": "1",
            "EINVITE_FIELD_ENCRYPTION": "0",
        }
        with app_server(extra_env=env) as (_process, base, _data):
            status, auth = _request(base, "POST", "/api/auth/register",
                                    {"email": "keys-owner@einvite.test", "password": "Test1234!Pass"})
            assert status in (200, 201) and auth.get("token"), (status, auth)
            token = auth["token"]

            document = {"schemaVersion": 14, "eventType": "Wedding",
                        "fields": {"names": "Keys Couple"}, "objects": {}, "designPages": [],
                        "settings": {"rsvpEnabled": True}}
            status, created = _request(base, "POST", "/api/invitations",
                                       {"slug": "keys-rsvp", "document": document}, token=token)
            assert status in (200, 201), (status, created)
            invitation_id = created["id"]

            # Scope validation is enforced at creation time.
            status, invalid = _request(base, "POST", "/api/account/api-keys",
                                       {"name": "bad", "scopes": ["everything:write"]}, token=token)
            assert status == 400 and invalid.get("code") == "api_key_scope_invalid", (status, invalid)

            status, first = _request(base, "POST", "/api/account/api-keys",
                                     {"name": "rsvp reader", "scopes": ["rsvps:read"]}, token=token)
            assert status == 201, (status, first)
            read_key, read_id = first["key"], first["id"]
            assert read_key.startswith("einv_") and len(read_key) >= 40, first
            assert first["hint"] == read_key[-4:], first

            rows = _db_rows(data_dir / "invites.db",
                            "SELECT key_hash, hint, scopes_json, revoked_at FROM api_keys WHERE id=?", (read_id,))
            assert len(rows) == 1, rows
            stored = rows[0]
            assert stored["key_hash"] != read_key and read_key not in stored["key_hash"], stored
            assert stored["key_hash"].startswith("$argon2") or stored["key_hash"].startswith("pbkdf2_sha256$"), stored
            assert stored["hint"] == read_key[-4:] and stored["revoked_at"] is None, stored
            assert json.loads(stored["scopes_json"]) == ["rsvps:read"], stored

            status, listing = _request(base, "GET", "/api/account/api-keys", token=token)
            assert status == 200, (status, listing)
            item = next(row for row in listing["items"] if row["id"] == read_id)
            assert "key" not in item and "key_hash" not in item, item
            assert item["hint"] == read_key[-4:], item

            # Allowed route: read RSVPs through the key.
            status, rsvps = _request(base, "GET", f"/api/invitations/{invitation_id}/rsvps", api_key=read_key)
            assert status == 200 and isinstance(rsvps, list), (status, rsvps)

            # A route outside the allowlist is refused for key auth.
            status, denied = _request(base, "POST", "/api/account/privacy",
                                      {"analyticsOptOut": True}, api_key=read_key)
            assert status == 403 and denied.get("code") == "api_key_scope_denied", (status, denied)

            # A write key may create an invitation but not read RSVPs.
            status, write = _request(base, "POST", "/api/account/api-keys",
                                     {"name": "invitation writer", "scopes": ["invitations:write"]}, token=token)
            assert status == 201, (status, write)
            write_key = write["key"]
            status, made = _request(base, "POST", "/api/invitations",
                                    {"slug": "keys-made-by-key", "document": document}, api_key=write_key)
            assert status in (200, 201), (status, made)
            status, refused = _request(base, "GET", f"/api/invitations/{invitation_id}/rsvps", api_key=write_key)
            assert status == 403 and refused.get("code") == "api_key_scope_denied", (status, refused)

            # A tampered key does not authenticate.
            status, bad = _request(base, "GET", f"/api/invitations/{invitation_id}/rsvps",
                                   api_key=read_key[:-1] + ("A" if read_key[-1] != "A" else "B"))
            assert status == 401, (status, bad)

            # Accepted API requests are audited with auth=api_key.
            events = _db_rows(data_dir / "invites.db",
                              "SELECT action, target_id, metadata_json FROM audit_events "
                              "WHERE action='api.request' AND target_id=? ORDER BY created_at DESC", (read_id,))
            assert events, "no api.request audit event for the key"
            metadata = json.loads(events[0]["metadata_json"])
            assert metadata.get("auth") == "api_key" and metadata.get("path", "").endswith("/rsvps"), metadata

            # Revoke: the key stops working immediately.
            status, revoked = _request(base, "DELETE", f"/api/account/api-keys/{read_id}", token=token)
            assert status == 200 and revoked.get("revoked") is True, (status, revoked)
            status, after = _request(base, "GET", f"/api/invitations/{invitation_id}/rsvps", api_key=read_key)
            assert status == 401, (status, after)
            print("[OK] api key created once, scoped, audited and revoked", flush=True)
        print("LT_7_2_API_KEYS_PASSED", flush=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))
