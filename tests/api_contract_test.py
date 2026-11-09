"""Strict API contracts for the core eInvite endpoints.

The schemas below are the contract, not a snapshot helper: object schemas reject
unknown top-level keys unless the schema explicitly allows a versioned detail
object. The test starts the real server process and validates status, JSON
content type, request correlation, and response shape.

Run with:
    .venv/bin/python -m pytest tests/api_contract_test.py -q
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from v14_test_utils import app_server  # noqa: E402

REQUEST_ID = re.compile(r"[A-Za-z0-9._:-]{1,80}\Z")

# A documented production document has versioned extension objects. Those are
# validated by validate_document(), so the API contract pins the stable core
# while allowing those versioned extensions to evolve.
DOCUMENT = {
    "type": "object",
    "required": ["schemaVersion", "eventType", "fields", "objects", "designPages", "settings"],
    "properties": {
        "schemaVersion": {"type": "integer"},
        "eventType": {"type": "string"},
        "fields": {"type": "object"},
        "objects": {"type": "object"},
        "designPages": {"type": "array"},
        "settings": {"type": "object"},
    },
    "additionalProperties": True,
}

SESSION_USER = {
    "type": "object",
    "required": ["id", "email", "role", "emailVerified", "plan", "uploadEnabled", "mfaEnabled"],
    "properties": {
        "id": {"type": "string"},
        "email": {"type": "string"},
        "role": {"type": "string"},
        "emailVerified": {"type": "boolean"},
        "plan": {"type": "string"},
        "uploadEnabled": {"type": "boolean"},
        "mfaEnabled": {"type": "boolean"},
    },
    "additionalProperties": False,
}

SESSION = {
    "type": "object",
    "required": ["user", "expiresAt", "csrfToken"],
    "properties": {
        "user": SESSION_USER,
        "expiresAt": {"type": "integer"},
        "csrfToken": {"type": "string"},
        "token": {"type": "string"},
    },
    "additionalProperties": False,
}

ME_USER = {
    "type": "object",
    "required": ["id", "email", "role", "email_verified", "plan", "upload_enabled", "mfa_enabled",
                 "deleted_at", "session_never_expires", "session_created_at", "last_seen_at"],
    "properties": {
        "id": {"type": "string"},
        "email": {"type": "string"},
        "role": {"type": "string"},
        "email_verified": {"type": "integer"},
        "plan": {"type": "string"},
        "upload_enabled": {"type": "integer"},
        "mfa_enabled": {"type": "integer"},
        "deleted_at": {"type": ["string", "null"]},
        "session_never_expires": {"type": "integer"},
        "session_created_at": {"type": "integer"},
        "last_seen_at": {"type": "integer"},
    },
    "additionalProperties": False,
}

ME = {
    "type": "object",
    "required": ["user"],
    "properties": {"user": ME_USER},
    "additionalProperties": False,
}

ME_ANON = {
    "type": "object",
    "required": ["user"],
    "properties": {"user": {"type": "null"}},
    "additionalProperties": False,
}

HEALTH = {
    "type": "object",
    "required": ["ok", "status"],
    "properties": {"ok": {"type": "boolean"}, "status": {"type": "string", "const": "live"}},
    "additionalProperties": False,
}

LOGOUT = {
    "type": "object",
    "required": ["signedOut"],
    "properties": {"signedOut": {"type": "boolean"}},
    "additionalProperties": False,
}

INVITATION_CREATE = {
    "type": "object",
    "required": ["id", "slug", "updatedAt"],
    "properties": {
        "id": {"type": "string"},
        "slug": {"type": "string"},
        "updatedAt": {"type": "integer"},
    },
    "additionalProperties": False,
}

INVITATION_PREVIEW = {
    "type": "object",
    "required": ["eventType", "theme", "accent", "palette", "fields", "objects",
                 "designPages", "masterPageStyle"],
    "properties": {
        "eventType": {"type": "string"},
        "theme": {"type": "string"},
        "accent": {"type": "string"},
        "palette": {"type": "object"},
        "fields": {"type": "object"},
        "objects": {"type": "object"},
        "designPages": {"type": "array"},
        "masterPageStyle": {"type": "object"},
    },
    "additionalProperties": False,
}

INVITATION_SUMMARY = {
    "type": "object",
    "required": ["id", "slug", "title", "type", "status", "archived", "views", "rsvps",
                 "rsvpEnabled", "accessMode", "updatedAt", "shared", "collaborationRole",
                 "preview"],
    "properties": {
        "id": {"type": "string"},
        "slug": {"type": "string"},
        "title": {"type": "string"},
        "type": {"type": "string"},
        "status": {"type": "string"},
        "archived": {"type": "boolean"},
        "views": {"type": "integer"},
        "rsvps": {"type": "integer"},
        "rsvpEnabled": {"type": "boolean"},
        "accessMode": {"type": "string"},
        "updatedAt": {"type": "integer"},
        "shared": {"type": "boolean"},
        "collaborationRole": {"type": ["string", "null"]},
        "preview": INVITATION_PREVIEW,
    },
    "additionalProperties": False,
}

INVITATION_LIST = {"type": "array", "items": INVITATION_SUMMARY}

INVITATION = {
    "type": "object",
    "required": ["id", "slug", "document", "updatedAt", "archived", "accessMode",
                 "published", "collaborationRole", "owner", "lastClientId",
                 "lastMutationId", "customDomain", "publishAt", "unpublishAt",
                 "expiresAt", "galleryProtected"],
    "properties": {
        "id": {"type": "string"},
        "slug": {"type": "string"},
        "document": DOCUMENT,
        "updatedAt": {"type": "integer"},
        "archived": {"type": "boolean"},
        "accessMode": {"type": "string"},
        "published": {"type": "boolean"},
        "collaborationRole": {"type": ["string", "null"]},
        "owner": {"type": "boolean"},
        "lastClientId": {"type": ["string", "null"]},
        "lastMutationId": {"type": ["string", "null"]},
        "customDomain": {"type": "string"},
        "publishAt": {"type": ["integer", "null"]},
        "unpublishAt": {"type": ["integer", "null"]},
        "expiresAt": {"type": ["integer", "null"]},
        "galleryProtected": {"type": "boolean"},
    },
    "additionalProperties": False,
}

INVITATION_SAVE = {
    "type": "object",
    "required": ["saved", "updatedAt", "clientId", "mutationId", "editedAfterSend"],
    "properties": {
        "saved": {"type": "boolean"},
        "updatedAt": {"type": "integer"},
        "clientId": {"type": ["string", "null"]},
        "mutationId": {"type": ["string", "null"]},
        "editedAfterSend": {"type": "boolean"},
    },
    "additionalProperties": False,
}

INVITATION_PUBLISH = {
    "type": "object",
    "required": ["publicationId", "version", "updatedAt", "documentVersion", "clientId",
                 "mutationId", "slug", "url"],
    "properties": {
        "publicationId": {"type": "string"},
        "version": {"type": "integer"},
        "updatedAt": {"type": "integer"},
        "documentVersion": {"type": "integer"},
        "clientId": {"type": ["string", "null"]},
        "mutationId": {"type": ["string", "null"]},
        "slug": {"type": "string"},
        "url": {"type": "string"},
    },
    "additionalProperties": False,
}

INVITATION_DELETE = {
    "type": "object",
    "required": ["deleted"],
    "properties": {"deleted": {"type": "boolean", "const": True}},
    "additionalProperties": False,
}

GUEST_CREATE = {
    "type": "object",
    "required": ["id", "name", "slug", "token", "tokenExpiresAt"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "slug": {"type": "string"},
        "token": {"type": "string"},
        "tokenExpiresAt": {"type": ["integer", "null"]},
    },
    "additionalProperties": False,
}

GUEST = {
    "type": "object",
    "required": ["id", "name", "slug", "phone", "email", "group_name", "household_id",
                 "tags", "table_name", "seat_label", "delivery_status", "opened_at",
                 "token_salt", "token_version", "token_expires_at", "token_revoked_at",
                 "created_at", "checked_in", "checked_in_at", "rsvp_status", "token",
                 "personalLinkAvailable"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "slug": {"type": "string"},
        "phone": {"type": "string"},
        "email": {"type": "string"},
        "group_name": {"type": "string"},
        "household_id": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "table_name": {"type": "string"},
        "seat_label": {"type": "string"},
        "delivery_status": {"type": "string"},
        "opened_at": {"type": ["integer", "null"]},
        "token_salt": {"type": "string"},
        "token_version": {"type": "integer"},
        "token_expires_at": {"type": ["integer", "null"]},
        "token_revoked_at": {"type": ["integer", "null"]},
        "created_at": {"type": "integer"},
        "checked_in": {"type": "integer"},
        "checked_in_at": {"type": ["integer", "null"]},
        "rsvp_status": {"type": ["string", "null"]},
        "token": {"type": ["string", "null"]},
        "personalLinkAvailable": {"type": "boolean"},
    },
    "additionalProperties": False,
}

GUEST_LIST = {"type": "array", "items": GUEST}

CHECKIN = {
    "type": "object",
    "required": ["checkedIn", "checkedInAt", "alreadyCheckedIn"],
    "properties": {
        "checkedIn": {"type": "boolean"},
        "checkedInAt": {"type": ["integer", "null"]},
        "alreadyCheckedIn": {"type": "boolean"},
    },
    "additionalProperties": False,
}

ERROR = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {"type": "string"},
        "code": {"type": "string"},
        "requestId": {"type": "string"},
    },
    # Errors may include bounded detail fields such as readiness or retry data.
    "additionalProperties": True,
}


def validate(value, schema, path="$"):
    """Validate the small JSON-Schema subset used by the contract file."""
    expected = schema.get("type")
    if expected:
        kinds = expected if isinstance(expected, list) else [expected]
        if not any(_matches(value, kind) for kind in kinds):
            raise AssertionError(f"{path}: expected {kinds}, got {type(value).__name__}")
    if "const" in schema and value != schema["const"]:
        raise AssertionError(f"{path}: expected constant {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise AssertionError(f"{path}: expected one of {schema['enum']!r}, got {value!r}")
    if "pattern" in schema and isinstance(value, str):
        assert re.fullmatch(schema["pattern"], value), f"{path}: value does not match pattern"
    if isinstance(value, dict):
        for key in schema.get("required", []):
            assert key in value, f"{path}: missing required key {key!r}"
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value:
                validate(value[key], child, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(properties)
            assert not extra, f"{path}: unexpected keys {sorted(extra)}"
    if isinstance(value, list):
        if schema.get("minItems") is not None:
            assert len(value) >= schema["minItems"], f"{path}: too few items"
        if "items" in schema:
            for index, item in enumerate(value):
                validate(item, schema["items"], f"{path}[{index}]")


def _matches(value, kind):
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    if kind == "any":
        return True
    raise AssertionError(f"unsupported schema type {kind!r}")


def _request(base, method, path, body=None, token=None, raw=None):
    payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status, response_headers, response_body = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, response_headers, response_body = error.code, error.headers, error.read()
    request_id = response_headers.get("X-Request-ID", "")
    assert request_id and REQUEST_ID.fullmatch(request_id), (
        f"{method} {path} returned invalid X-Request-ID {request_id!r}"
    )
    return status, response_headers, response_body


def _json(base, method, path, body=None, token=None, raw=None):
    status, headers, payload = _request(base, method, path, body=body, token=token, raw=raw)
    assert headers.get("Content-Type", "").startswith("application/json"), (
        f"{method} {path} returned non-JSON content type {headers.get('Content-Type')!r}"
    )
    try:
        return status, json.loads(payload or b"{}")
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{method} {path} returned invalid JSON: {payload[:300]!r}") from exc


def _assert_error(base, method, path, status, body=None, token=None, raw=None):
    actual, payload = _json(base, method, path, body=body, token=token, raw=raw)
    assert actual == status, f"{method} {path}: expected {status}, got {actual}: {payload}"
    validate(payload, ERROR)
    assert payload["error"].strip(), f"{method} {path}: empty error message"
    return payload


def _register(base, email):
    status, payload = _json(base, "POST", "/api/auth/register",
                            {"email": email, "password": "Test1234!Pass"})
    assert status == 201, payload
    validate(payload, SESSION)
    return payload["token"]


def _document(names="Contract Couple"):
    return {
        "schemaVersion": 14,
        "eventType": "Wedding",
        "fields": {"names": names, "date": "2026-12-27", "venue": "Grand Hall"},
        "objects": {},
        "designPages": [],
        "settings": {"rsvpEnabled": True},
    }


def test_core_success_contracts():
    env = {"EINVITE_DEV_AUTH_TOKENS": "1", "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
           "EINVITE_ALLOW_NO_SCANNER": "1"}
    with app_server(env) as (_process, base, _data):
        status, health = _json(base, "GET", "/api/health/live")
        assert status == 200
        validate(health, HEALTH)

        token = _register(base, "contract-happy@example.test")
        status, login = _json(base, "POST", "/api/auth/login",
                              {"email": "contract-happy@example.test", "password": "Test1234!Pass"})
        assert status == 201
        validate(login, SESSION)
        token = login["token"]

        status, me = _json(base, "GET", "/api/auth/me", token=token)
        assert status == 200
        validate(me, ME)

        status, empty = _json(base, "GET", "/api/invitations", token=token)
        assert status == 200
        validate(empty, INVITATION_LIST)
        assert empty == []

        status, created = _json(base, "POST", "/api/invitations",
                                {"slug": "contract-happy", "document": _document()}, token=token)
        assert status == 201
        validate(created, INVITATION_CREATE)
        invite_id = created["id"]

        status, listing = _json(base, "GET", "/api/invitations", token=token)
        assert status == 200
        validate(listing, INVITATION_LIST)
        assert any(item["id"] == invite_id for item in listing)

        status, invitation = _json(base, "GET", f"/api/invitations/{invite_id}", token=token)
        assert status == 200
        validate(invitation, INVITATION)

        status, saved = _json(base, "PUT", f"/api/invitations/{invite_id}",
                              {"document": _document("Contract Couple Updated")}, token=token)
        assert status == 200
        validate(saved, INVITATION_SAVE)

        status, guest = _json(base, "POST", f"/api/invitations/{invite_id}/guests",
                              {"name": "Contract Guest"}, token=token)
        assert status == 201
        validate(guest, GUEST_CREATE)
        guest_id = guest["id"]

        status, guests = _json(base, "GET", f"/api/invitations/{invite_id}/guests", token=token)
        assert status == 200
        validate(guests, GUEST_LIST)
        assert any(item["id"] == guest_id for item in guests)

        status, checked = _json(base, "PUT", f"/api/invitations/{invite_id}/guests/{guest_id}/check-in",
                                {"checkedIn": True}, token=token)
        assert status == 200
        validate(checked, CHECKIN)
        assert checked["checkedIn"] is True

        status, published = _json(base, "POST", f"/api/invitations/{invite_id}/publish",
                                  {"document": _document("Contract Couple Updated")}, token=token)
        assert status == 201
        validate(published, INVITATION_PUBLISH)

        status, deleted = _json(base, "DELETE", f"/api/invitations/{invite_id}", token=token)
        assert status == 200
        validate(deleted, INVITATION_DELETE)

        status, after_delete = _json(base, "GET", f"/api/invitations/{invite_id}", token=token)
        assert status == 404
        validate(after_delete, ERROR)

        status, logged_out = _json(base, "POST", "/api/auth/logout", {}, token=token)
        assert status == 200
        validate(logged_out, LOGOUT)


def test_error_and_fuzz_contracts():
    env = {"EINVITE_DEV_AUTH_TOKENS": "1", "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
           "EINVITE_ALLOW_NO_SCANNER": "1"}
    with app_server(env) as (_process, base, _data):
        token = _register(base, "contract-errors@example.test")
        status, created = _json(base, "POST", "/api/invitations",
                                {"slug": "contract-errors", "document": _document()}, token=token)
        assert status == 201
        invite_id = created["id"]
        foreign = _register(base, "contract-foreign@example.test")
        missing = "00000000-0000-4000-8000-000000000000"

        _assert_error(base, "POST", "/api/auth/register", 400, {})
        _assert_error(base, "POST", "/api/auth/login", 401,
                      {"email": "contract-errors@example.test", "password": "Wrong1234!"})
        _assert_error(base, "GET", "/api/invitations", 401)
        _assert_error(base, "GET", f"/api/invitations/{missing}", 404, token=token)
        _assert_error(base, "GET", "/api/invitations?limit=not-an-integer", 400, token=token)
        _assert_error(base, "GET", "/api/invitations?status=unknown", 400, token=token)
        _assert_error(base, "POST", "/api/invitations", 400, {"document": "not-an-object"}, token=token)
        _assert_error(base, "POST", "/api/invitations", 400, raw=b"{", token=token)
        _assert_error(base, "PUT", f"/api/invitations/{invite_id}", 400,
                      {"expectedRevision": "not-an-integer"}, token=token)
        _assert_error(base, "POST", f"/api/invitations/{invite_id}/guests", 400, {}, token=token)
        _assert_error(base, "GET", f"/api/invitations/{invite_id}/guests", 403, token=foreign)
        _assert_error(base, "POST", f"/api/invitations/{invite_id}/guests", 403,
                      {"name": "Foreign Guest"}, token=foreign)
        _assert_error(base, "PUT", f"/api/invitations/{invite_id}/guests/{missing}/check-in",
                      404, {"checkedIn": True}, token=token)
        _assert_error(base, "DELETE", f"/api/invitations/{missing}", 404, token=token)


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
