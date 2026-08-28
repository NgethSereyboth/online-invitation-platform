#!/usr/bin/env python3
"""Per-account upload permission must be immediate, exhaustive, and admin-controlled."""
from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = b"\x00\x00\x00\x18ftypmp42" + b"upload-permission-test"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def call(base: str, path: str, method: str = "GET", body=None, token: str = "", headers=None, raw: bool = False):
    payload = body if raw else (None if body is None else json.dumps(body).encode("utf-8"))
    request_headers = {} if raw else {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=payload, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def register(base: str, email: str):
    status, result = call(base, "/api/auth/register", "POST", {"email": email, "password": "password123"})
    assert status == 201 and result["user"]["uploadEnabled"] is True, result
    return result["user"], result["token"]


def raw_upload(base: str, invitation_id: str, token: str):
    return call(
        base,
        f"/api/invitations/{invitation_id}/assets/raw",
        "POST",
        MEDIA,
        token,
        {"Content-Type": "video/mp4", "Content-Length": str(len(MEDIA)), "X-File-Name": urllib.parse.quote("permission.mp4")},
        raw=True,
    )


def expect_disabled(result) -> None:
    status, body = result
    assert status == 403 and body == {"error": "Uploads are disabled for this account", "code": "upload_disabled"}, (status, body)


def run() -> int:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="einvite-upload-permission-") as data:
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": data,
            "EINVITE_ADMIN_EMAIL": "upload-admin@example.com",
            "EINVITE_DEV_AUTH_TOKENS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        process = subprocess.Popen(
            [sys.executable, "-u", "server.py", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(100):
                try:
                    if call(base, "/api/health")[0] == 200:
                        break
                except Exception:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("server did not start")

            _, admin_token = register(base, "upload-admin@example.com")
            user, user_token = register(base, "upload-user@example.com")
            status, invitation = call(base, "/api/invitations", "POST", {"slug": "upload-permission", "document": {"fields": {"names": "Upload permission"}, "objects": {}, "designPages": [], "sectionOrder": [], "settings": {}}}, user_token)
            assert status == 201, invitation
            invitation_id = invitation["id"]

            # Existing uploads and a pending resumable session establish the
            # behavior before an administrator changes the account capability.
            status, first_asset = raw_upload(base, invitation_id, user_token)
            assert status == 201, first_asset
            status, pending = call(base, f"/api/invitations/{invitation_id}/uploads/start", "POST", {"name": "pending.mp4", "mime": "video/mp4", "size": len(MEDIA)}, user_token)
            assert status == 201 and pending.get("uploadId"), pending

            # A normal user cannot change account capabilities.
            status, denied = call(base, f"/api/admin/users/{user['id']}/uploads", "PUT", {"enabled": False}, user_token)
            assert status == 403 and "permission" in denied.get("error", "").lower(), denied
            status, invalid = call(base, f"/api/admin/users/{user['id']}/uploads", "PUT", {"enabled": "false"}, admin_token)
            assert status == 400, invalid

            status, changed = call(base, f"/api/admin/users/{user['id']}/uploads", "PUT", {"enabled": False}, admin_token)
            assert status == 200 and changed == {"updated": True, "uploadEnabled": False}, changed
            status, users = call(base, "/api/admin/users", token=admin_token)
            row = next(item for item in users if item["id"] == user["id"])
            assert status == 200 and row["uploadEnabled"] is False, row
            status, me = call(base, "/api/auth/me", token=user_token)
            assert status == 200 and me["user"]["upload_enabled"] == 0, me

            # Every material-ingress family is blocked immediately, including
            # a resumable session that was created before the permission change.
            expect_disabled(raw_upload(base, invitation_id, user_token))
            expect_disabled(call(base, f"/api/invitations/{invitation_id}/uploads/start", "POST", {"name": "blocked.mp4", "mime": "video/mp4", "size": len(MEDIA)}, user_token))
            expect_disabled(call(base, f"/api/uploads/{pending['uploadId']}", "PUT", MEDIA, user_token, {"Content-Type": "application/octet-stream", "Content-Length": str(len(MEDIA)), "X-Upload-Offset": "0"}, raw=True))
            expect_disabled(call(base, f"/api/uploads/{pending['uploadId']}/complete", "POST", {}, user_token))
            expect_disabled(call(base, f"/api/invitations/{invitation_id}/assets/presign", "POST", {"name": "blocked.mp4", "mime": "video/mp4", "size": len(MEDIA)}, user_token))
            expect_disabled(call(base, f"/api/invitations/{invitation_id}/assets/complete", "POST", {}, user_token))
            expect_disabled(call(base, f"/api/invitations/{invitation_id}/fonts", "POST", b"", user_token, {"Content-Type": "font/ttf", "Content-Length": "0"}, raw=True))
            expect_disabled(call(base, f"/api/invitations/{invitation_id}/assets", "POST", {"name": "legacy.mp4", "mime": "video/mp4", "base64": base64.b64encode(MEDIA).decode("ascii")}, user_token))
            expect_disabled(call(base, "/api/platform/v32/uploads", "POST", {"invitationId": invitation_id, "name": "platform.mp4", "mime": "video/mp4", "size": len(MEDIA)}, user_token))

            # Read/delete cleanup remains available; disabling uploads does not
            # hide existing customer material or trap abandoned sessions.
            status, assets = call(base, f"/api/invitations/{invitation_id}/assets", token=user_token)
            assert status == 200 and any(item["id"] == first_asset["id"] for item in assets), assets
            status, cancelled = call(base, f"/api/uploads/{pending['uploadId']}", "DELETE", token=user_token)
            assert status == 200 and cancelled["cancelled"] is True, cancelled

            status, changed = call(base, f"/api/admin/users/{user['id']}/uploads", "PUT", {"enabled": True}, admin_token)
            assert status == 200 and changed["uploadEnabled"] is True, changed
            status, second_asset = raw_upload(base, invitation_id, user_token)
            assert status == 201, second_asset

            status, audit = call(base, "/api/account/audit", token=admin_token)
            assert status == 200 and any(item.get("action") == "account.upload_permission_changed" for item in audit), audit
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    admin_source = (ROOT / "admin.js").read_text(encoding="utf-8")
    account_source = (ROOT / "account.js").read_text(encoding="utf-8")
    admin_bundle = (ROOT / "bundle-admin-v15.js").read_text(encoding="utf-8")
    account_bundle = (ROOT / "bundle-account-v15.js").read_text(encoding="utf-8")
    schema = (ROOT / "postgres_schema.sql").read_text(encoding="utf-8")
    assert all(marker in admin_source for marker in ("data-upload-enabled", "data-save-uploads", "/uploads", "Allow uploads"))
    assert "Disabled by administrator" in account_source
    assert all(marker in admin_bundle for marker in ("data-upload-enabled", "data-save-uploads", "Allow uploads"))
    assert "Disabled by administrator" in account_bundle
    assert "upload_enabled INTEGER NOT NULL DEFAULT 1" in schema
    print("V0_52_UPLOAD_PERMISSION_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
