"""Behavior pins for the bounded Sprint 3 refactors.

These tests exercise the existing public seams before and after the helper
extractions: the PUT dispatcher, studio publish policy composition, and the
production preflight report. They intentionally use fakes instead of a live
HTTP server so a refactor cannot change route targets or blocker payloads
without failing here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

import server  # noqa: E402
from core import preflight  # noqa: E402


class _One:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _StudioDB:
    def __init__(self, *, policy=None, resources=None, pin=None, release=None):
        self.policy = policy
        self.resources = resources or {}
        self.pin = pin
        self.release = release

    def execute(self, sql, params=()):
        if "FROM studio_governance" in sql:
            return _One(None if self.policy is None else {"policy_json": json.dumps(self.policy)})
        if "FROM studio_resources" in sql:
            resource_id = params[0] if params else ""
            return _One(self.resources.get(resource_id))
        if "FROM invitation_studio_release_pins" in sql:
            return _One(self.pin)
        if "FROM studio_releases" in sql:
            return _One(self.release)
        raise AssertionError(f"unexpected studio SQL: {sql}")


def _handler(path):
    handler = object.__new__(server.Handler)
    handler.path = path
    handler.guard_request_boundary = lambda: True
    handler.guard_cookie_origin = lambda: True
    return handler


def _put_calls(path, routes):
    handler = _handler(path)
    calls = []
    responses = []
    for name, target in routes.items():
        setattr(handler, name, lambda *args, _name=name, _target=target: calls.append((_name, args)))
    handler.json = lambda status, payload: responses.append((status, payload))
    handler.do_PUT()
    return calls, responses


def test_put_dispatches_admin_user_role():
    calls, responses = _put_calls(
        "/api/admin/users/user-1/role",
        {"admin_update_user_role": ("admin_update_user_role",)},
    )
    assert calls == [("admin_update_user_role", ("user-1",))]
    assert responses == []


def test_put_dispatches_guest_check_in():
    calls, responses = _put_calls(
        "/api/invitations/inv-1/guests/guest-1/check-in",
        {"check_in_guest": ("check_in_guest",)},
    )
    assert calls == [("check_in_guest", ("inv-1", "guest-1"))]
    assert responses == []


def test_put_falls_through_to_save_draft():
    calls, responses = _put_calls(
        "/api/invitations/inv-1",
        {"save_draft": ("save_draft",)},
    )
    assert calls == [("save_draft", ("inv-1",))]
    assert responses == []


def test_put_unknown_path_returns_not_found():
    calls, responses = _put_calls("/api/not-a-route", {})
    assert calls == []
    assert responses == [(404, {"error": "Not found"})]


def test_studio_publish_readiness_without_policy_is_ready():
    report = server.studio_publish_readiness(_StudioDB(policy=None), "owner", {})
    assert report == {"ready": True, "policy": {}, "blockers": []}


def test_studio_publish_readiness_requires_print_preflight():
    document = {}
    db = _StudioDB(policy={"requirePrintPreflight": True})
    report = server.studio_publish_readiness(db, "owner", document)
    assert report["ready"] is False
    assert report["blockers"] == [{
        "code": "print_preflight_required",
        "message": "Run and mark the print preflight current before publishing.",
    }]


def test_studio_publish_readiness_requires_approved_resource():
    document = {}
    db = _StudioDB(policy={"approvedOnly": True})
    report = server.studio_publish_readiness(db, "owner", document)
    assert report["ready"] is False
    assert report["blockers"] == [{
        "code": "approved_resource_required",
        "message": "Studio policy requires at least one approved governed resource.",
    }]


def test_studio_publish_readiness_requires_release_pin():
    document = {
        "templateFamily": {"resourceId": "tpl-1", "resourceVersion": 1},
        "studioGovernance": {"brandResourceId": "brand-1", "brandResourceVersion": 1},
    }
    resources = {
        "tpl-1": {"id": "tpl-1", "kind": "template-family", "status": "approved",
                   "version": 1, "payload_json": "{}", "governance_json": "{}"},
        "brand-1": {"id": "brand-1", "kind": "brand", "status": "approved",
                    "version": 1, "payload_json": "{}", "governance_json": "{}"},
    }
    db = _StudioDB(policy={"approvedOnly": True, "requireStudioRelease": True}, resources=resources)
    report = server.studio_publish_readiness(db, "owner", document, invitation_id="inv-1")
    assert report["ready"] is False
    assert any(blocker["code"] == "studio_release_required" for blocker in report["blockers"])


def _valid_audit_environment():
    return {
        "EINVITE_PRODUCTION": "1",
        "EINVITE_REQUIRE_DURABLE_SERVICES": "1",
        "EINVITE_REQUIRE_VERIFIED_EMAIL": "1",
        "EINVITE_PUBLIC_BASE_URL": "https://invite.example.test",
        "EINVITE_ALLOWED_HOSTS": "invite.example.test",
        "EINVITE_COOKIE_SECURE": "1",
        "EINVITE_REQUIRE_MALWARE_SCAN": "1",
        "EINVITE_UPLOAD_SIGNING_SECRET": "Up9!kL2@rT7#vX4$mN8%qW3&yH6*zC1+",
        "EINVITE_MEDIA_SIGNING_SECRET": "Me8!jK3@pS6#uV2$nB9%rQ5&xG7*wD4+",
        "EINVITE_GUEST_TOKEN_SECRET": "Gu7!hJ4@nR5#tU3$mC8%pP6&zF9*vE2+",
        "EINVITE_DATABASE_URL": "postgresql://einvite:Db9!kL2@postgres:5432/einvite",
        "EINVITE_REDIS_URL": "redis://:Rd8!mN3@redis:6379/0",
        "EINVITE_OBJECT_STORAGE_PROVIDER": "minio",
        "EINVITE_OBJECT_STORAGE_BUCKET": "einvite-private",
        "EINVITE_OBJECT_STORAGE_ENDPOINT": "http://minio:9000",
        "EINVITE_OBJECT_STORAGE_ACCESS_KEY": "minio-access-9K2m",
        "EINVITE_OBJECT_STORAGE_SECRET_KEY": "minio-secret-7R4p-2L8x",
        "EINVITE_ALLOW_INSECURE_OBJECT_STORAGE": "1",
        "EINVITE_BACKUP_PROVIDER": "object",
        "EINVITE_TRUSTED_PROXY_IPS": "172.20.0.10",
        "EINVITE_ADMIN_IP_ALLOWLIST": "10.0.0.0/8,192.168.1.5",
    }


def test_audit_environment_accepts_complete_production_config():
    report = preflight.audit_environment(_valid_audit_environment())
    assert report["ok"], report
    assert report["summary"]["database"] == "postgresql"
    assert report["summary"]["allowedHostCount"] == 1


def test_audit_environment_reports_invalid_public_and_secret_groups():
    values = _valid_audit_environment()
    values.update({
        "EINVITE_PUBLIC_BASE_URL": "http://invite.example.test/path",
        "EINVITE_COOKIE_SECURE": "0",
        "EINVITE_DATABASE_URL": "sqlite:///data.db",
        "EINVITE_REDIS_URL": "redis://redis:6379/0",
        "EINVITE_OBJECT_STORAGE_PROVIDER": "local",
        "EINVITE_BACKUP_PROVIDER": "local",
        "EINVITE_TRUSTED_PROXY_IPS": "0.0.0.0/0",
    })
    report = preflight.audit_environment(values)
    assert report["ok"] is False
    assert any("EINVITE_PUBLIC_BASE_URL" in error for error in report["errors"])
    assert any("EINVITE_COOKIE_SECURE" in error for error in report["errors"])
    assert any("EINVITE_DATABASE_URL" in error for error in report["errors"])
    assert any("EINVITE_REDIS_URL" in error for error in report["errors"])
    assert any("EINVITE_TRUSTED_PROXY_IPS" in error for error in report["errors"])


def test_audit_environment_rejects_wildcard_admin_allowlist():
    values = _valid_audit_environment()
    values["EINVITE_ADMIN_IP_ALLOWLIST"] = "0.0.0.0/0"
    report = preflight.audit_environment(values)
    assert report["ok"] is False
    assert any("contains a /0 network" in error for error in report["errors"])


def test_audit_environment_ignores_storage_endpoint_when_provider_is_local():
    values = _valid_audit_environment()
    values.update({
        "EINVITE_REQUIRE_DURABLE_SERVICES": "0",
        "EINVITE_OBJECT_STORAGE_PROVIDER": "local",
        "EINVITE_OBJECT_STORAGE_ENDPOINT": "not-a-url",
        "EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL": "also-not-a-url",
        "EINVITE_BACKUP_PROVIDER": "local",
    })
    report = preflight.audit_environment(values)
    assert report["ok"], report
    assert report["summary"]["objectStorageProvider"] == "local"
