#!/usr/bin/env python3
"""Non-destructive live attack simulation for the final V0.52 hardening pass."""
from __future__ import annotations

import http.client
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v14_test_utils import app_server

ROOT = Path(__file__).resolve().parents[1]


def client():
    jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)), jar


def call(opener, base, path, method="GET", body=None, headers=None, expected=None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(base + path, data=payload, method=method, headers=request_headers)
    try:
        with opener.open(request, timeout=12) as response:
            status, response_headers, raw = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, response_headers, raw = error.code, error.headers, error.read()
    try:
        decoded = json.loads(raw or b"{}")
    except Exception:
        decoded = raw
    if expected is not None:
        assert status == expected, (method, path, status, decoded)
    return status, response_headers, decoded


def raw_call(opener, base, path, payload, mime, csrf, expected):
    request = urllib.request.Request(
        base + path,
        data=payload,
        method="POST",
        headers={
            "Content-Type": mime,
            "Content-Length": str(len(payload)),
            "X-File-Name": "attack.bin",
            "X-CSRF-Token": csrf,
        },
    )
    try:
        with opener.open(request, timeout=12) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    decoded = json.loads(raw or b"{}")
    assert status == expected, (path, status, decoded)
    return decoded


def malformed_host_status(base):
    parsed = urlparse(base)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=8)
    connection.request("GET", "/api/health", headers={"Host": "127.0.0.1:99999"})
    response = connection.getresponse()
    status = response.status
    response.read()
    connection.close()
    return status


def production_constant_probe():
    env = {
        **os.environ,
        "EINVITE_PRODUCTION": "1",
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
        "EINVITE_STRICT_SESSION_CSRF": "0",
        "EINVITE_UPLOAD_SIGNING_SECRET": "upload-security-probe-abcdefghijklmnopqrstuvwxyz012345",
        "EINVITE_MEDIA_SIGNING_SECRET": "media-security-probe-abcdefghijklmnopqrstuvwxyz0123456",
        "EINVITE_GUEST_TOKEN_SECRET": "guest-security-probe-abcdefghijklmnopqrstuvwxyz0123456",
        "PYTHONPATH": str(ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    code = "import server;assert server.PRODUCTION_MODE and server.STRICT_SESSION_CSRF and not server.ALLOW_LOCAL_ADMIN_BOOTSTRAP"
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def main():
    production_constant_probe()
    with app_server({
        "EINVITE_ALLOWED_HOSTS": "127.0.0.1,localhost",
        "EINVITE_STRICT_SESSION_CSRF": "1",
        "EINVITE_DISCLOSE_HEALTH_DETAILS": "0",
        "EINVITE_REQUIRE_MALWARE_SCAN": "0",
    }) as (_process, base, data_dir):
        anonymous, _ = client()

        # Public file and operational-intelligence disclosure probes.
        for path in ("/BUILD_INFO.json", "/route-bundles-v15.json", "/server.py", "/.env.production"):
            call(anonymous, base, path, expected=404)
        _, _, health = call(anonymous, base, "/api/health", expected=200)
        assert health == {"ok": True}, health
        _, _, live = call(anonymous, base, "/api/health/live", expected=200)
        assert live == {"ok": True, "status": "live"}, live
        _, _, ready = call(anonymous, base, "/api/health/ready", expected=200)
        assert ready == {"ok": True, "status": "ready"}, ready

        # Host-header and correlation-header abuse probes.
        assert malformed_host_status(base) == 400
        _, headers, _ = call(anonymous, base, "/api/health", headers={"X-Request-ID": "<bad id>"}, expected=200)
        assert headers.get("X-Request-ID") == "badid", headers.get("X-Request-ID")
        call(anonymous, base, "/api/health", headers={"Host": "attacker.invalid"}, expected=421)

        # Cross-site bootstrap and password resource-exhaustion probes.
        call(anonymous, base, "/api/auth/register", "POST", {"email": "cross@example.test", "password": "password123"}, {"Origin": "https://attacker.invalid"}, 403)
        call(anonymous, base, "/api/auth/register", "POST", {"email": "long@example.test", "password": "x" * 201}, expected=400)

        owner, _ = client()
        _, _, registered = call(owner, base, "/api/auth/register", "POST", {"email": "owner@example.test", "password": "password123"}, expected=201)
        csrf = registered["csrfToken"]
        assert registered["user"]["role"] == "customer"

        # Unknown passkey accounts return a generic fake challenge, not a 404 oracle.
        _, _, fake = call(anonymous, base, "/api/auth/passkeys/login/options", "POST", {"email": "missing@example.test"}, expected=200)
        assert fake["challengeId"] and len(fake["publicKey"]["allowCredentials"]) == 1

        document = {
            "eventType": "Wedding",
            "fields": {"names": "Security Test", "date": "2026-12-27", "time": "16:00", "venue": "Test", "message": "Join us"},
            "objects": {}, "designPages": [], "sectionOrder": [], "settings": {},
        }
        # Strict session CSRF cannot be bypassed by omitting Origin/Sec-Fetch-Site.
        call(owner, base, "/api/invitations", "POST", {"slug": "csrf-bypass", "document": document}, expected=403)
        _, _, invitation = call(owner, base, "/api/invitations", "POST", {"slug": "security-test", "document": document}, {"X-CSRF-Token": csrf}, 201)
        invitation_id = invitation["id"]
        _, _, platform = call(owner, base, "/api/platform/v32/status", expected=200)
        workspace_id = platform["workspace"]["id"]
        call(owner, base, "/api/platform/v32/objects/sign", "POST", {"key": f"workspaces/{workspace_id}/assets/unregistered/v1/payload.html", "disposition": "inline"}, {"X-CSRF-Token": csrf}, 404)

        # IDOR: a second authenticated account cannot enumerate the invitation.
        outsider, _ = client()
        _, _, outsider_registered = call(outsider, base, "/api/auth/register", "POST", {"email": "outsider@example.test", "password": "password123"}, expected=201)
        call(outsider, base, f"/api/invitations/{invitation_id}", expected=404)
        call(outsider, base, f"/api/invitations/{invitation_id}", "DELETE", headers={"X-CSRF-Token": outsider_registered["csrfToken"]}, expected=404)

        # Signed-storage sessions reject active content and incomplete digests.
        call(owner, base, "/api/platform/v32/uploads", "POST", {"invitationId": invitation_id, "name": "payload.html", "mime": "text/html", "size": 20}, {"X-CSRF-Token": csrf}, 415)
        call(owner, base, "/api/platform/v32/uploads", "POST", {"invitationId": invitation_id, "name": "photo.png", "mime": "image/png", "size": 20, "checksum": "abcd"}, {"X-CSRF-Token": csrf}, 400)

        # Completion re-reads storage and runs magic-byte/malware validation;
        # it does not trust the signed session's declared MIME type.
        active_payload = b"<script>alert('stored')</script>"
        _, _, upload_session = call(owner, base, "/api/platform/v32/uploads", "POST", {"invitationId": invitation_id, "name": "photo.png", "mime": "image/png", "size": len(active_payload)}, {"X-CSRF-Token": csrf}, 201)
        stored_path = data_dir / "objects-v32" / upload_session["objectKey"]
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(active_payload)
        _, _, rejected = call(owner, base, f"/api/platform/v32/uploads/{upload_session['id']}/complete", "POST", {"name": "photo.png"}, {"X-CSRF-Token": csrf}, 422)
        assert rejected.get("code") == "upload_security_validation_failed", rejected
        assert not stored_path.exists(), "Rejected object was not removed from quarantine storage"

        # Magic-byte mismatch is rejected before material storage.
        mismatch = raw_call(owner, base, f"/api/invitations/{invitation_id}/assets/raw", b"<script>alert(1)</script>", "image/png", csrf, 400)
        assert "does not match" in mismatch.get("error", "").lower(), mismatch

        # A high-ratio ZIP bomb is rejected before decompression into memory.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("photo.png", b"0" * 2_000_000)
        bomb = raw_call(owner, base, f"/api/invitations/{invitation_id}/materials/import-zip", buffer.getvalue(), "application/zip", csrf, 400)
        assert "suspiciously compressed" in bomb.get("error", "").lower(), bomb

    print("V0_52_SECURITY_HARDENING_ATTACK_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
