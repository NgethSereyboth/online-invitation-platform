"""End-to-end standard-library smoke test for the local E-invitation-website backend."""
from __future__ import annotations

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


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(base: str, path: str, method: str = "GET", body=None, token: str | None = None, expected: int | None = None):
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=encoded, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            payload = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = json.loads(exc.read() or b"{}")
    if expected is not None and status != expected:
        raise AssertionError(f"{method} {path}: expected {expected}, got {status}: {payload}")
    return status, payload


def raw_request(base: str, path: str, payload: bytes, mime: str, filename: str, token: str, expected: int = 201):
    headers = {
        "Content-Type": mime,
        "Content-Length": str(len(payload)),
        "X-File-Name": urllib.parse.quote(filename),
        "Authorization": f"Bearer {token}",
    }
    req = urllib.request.Request(base + path, data=payload, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = json.loads(exc.read() or b"{}")
    if status != expected:
        raise AssertionError(f"RAW POST {path}: expected {expected}, got {status}: {body}")
    return body


def wait_for_server(base: str, timeout: float = 12) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = request(base, "/api/health")
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(0.15)
    raise RuntimeError("Development server did not become ready")


def run() -> None:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    document = {
        "eventType": "Wedding",
        "fields": {"names": "Smoke Test", "date": "2026-12-27", "time": "16:00", "venue": "Test Venue", "message": "Join us"},
        "objects": {},
        "designPages": [],
        "sectionOrder": ["video", "rsvp", "wishes"],
        "settings": {"videoEnabled": True, "rsvpEnabled": True, "wishesEnabled": True},
        "video": None,
        "rsvpFields": [{"id": "meal", "type": "select", "label": "Meal", "required": True, "options": ["Standard", "Vegetarian"]}],
    }
    with tempfile.TemporaryDirectory(prefix="e-invitation-website-smoke-") as data_dir:
        admin_email = "admin-smoke@example.com"
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": data_dir,
            "EINVITE_ADMIN_EMAIL": admin_email,
            "EINVITE_DEV_AUTH_TOKENS": "1",
        }
        process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_for_server(base)

            # Admin registration, role/plan defaults, and usage endpoint.
            _, registered = request(base, "/api/auth/register", "POST", {"email": admin_email, "password": "oldpassword123"}, expected=201)
            token = registered["token"]
            assert registered["user"]["role"] == "admin"
            assert registered["user"]["plan"] == "studio"
            _, usage = request(base, "/api/account/usage", token=token, expected=200)
            assert usage["plan"] == "studio" and usage["enforced"] is False
            _, overview = request(base, "/api/admin/overview", token=token, expected=200)
            assert overview["users"] == 1

            # Email verification flow using development token exposure.
            _, verification = request(base, "/api/auth/verification/request", "POST", {}, token, 200)
            assert verification.get("devToken")
            request(base, "/api/auth/verification/confirm", "POST", {"token": verification["devToken"]}, expected=200)
            _, me = request(base, "/api/auth/me", token=token, expected=200)
            assert bool(me["user"]["email_verified"]) is True

            # Template marketplace lifecycle.
            _, template = request(base, "/api/templates", "POST", {"name": "Smoke Template", "category": "Wedding", "document": document}, token, 201)
            request(base, f"/api/templates/{template['id']}", "PUT", {"visibility": "public"}, token, 200)
            _, marketplace = request(base, "/api/template-marketplace", expected=200)
            assert any(item["id"] == template["id"] for item in marketplace)

            # Invitation creation and raw material uploads.
            _, invitation = request(base, "/api/invitations", "POST", {"slug": "Smoke Invitation", "document": document}, token, 201)
            invite_id, slug = invitation["id"], invitation["slug"]
            png = b"\x89PNG\r\n\x1a\n" + b"smoke-image"
            image_asset = raw_request(base, f"/api/invitations/{invite_id}/assets/raw", png, "image/png", "smoke image.png", token)
            mp4 = b"\x00\x00\x00\x18ftypmp42" + b"smoke-video"
            video_asset = raw_request(base, f"/api/invitations/{invite_id}/assets/raw", mp4, "video/mp4", "feature.mp4", token)
            request(base, f"/api/assets/{image_asset['id']}", "PUT", {"name": "Hero Image", "folder": "Wedding", "tags": ["hero", "favorite"], "favorite": True}, token, 200)
            _, assets = request(base, "/api/assets", token=token, expected=200)
            image_row = next(a for a in assets if a["id"] == image_asset["id"])
            assert image_row["favorite"] is True and image_row["folder"] == "Wedding" and "hero" in image_row["tags"]
            assert any(a["id"] == video_asset["id"] and a["mime"] == "video/mp4" for a in assets)

            # Save the featured video and a styled image object in the invitation document.
            document["video"] = {"url": video_asset["url"], "mime": "video/mp4", "name": "Feature Video"}
            document["objects"]["hero-photo"] = {
                "type": "image", "src": image_asset["url"], "left": "12%", "top": "30%", "width": "76%", "height": "320px",
                "imageBrightness": 104, "imageContrast": 110, "imageSaturation": 120, "imageGrayscale": 0, "imageSepia": 12, "imageBlur": 0,
            }
            request(base, f"/api/invitations/{invite_id}", "PUT", {"document": document}, token, 200)
            invalid_filter = json.loads(json.dumps(document))
            invalid_filter["objects"]["hero-photo"]["imageBrightness"] = 500
            request(base, f"/api/invitations/{invite_id}", "PUT", {"document": invalid_filter}, token, 400)

            # Privacy, publishing, custom RSVP, and guest wishes.
            request(base, f"/api/invitations/{invite_id}/access", "PUT", {"mode": "password", "password": "secret12"}, token, 200)
            request(base, f"/api/invitations/{invite_id}/publish", "POST", {"document": document}, token, 201)
            request(base, f"/api/public/{slug}", expected=403)
            _, unlocked = request(base, f"/api/public/{slug}/unlock", "POST", {"password": "secret12"}, expected=200)
            access = unlocked["accessToken"]
            request(base, f"/api/public/{slug}/rsvps", "POST", {"name": "Guest", "status": "Yes, joyfully", "count": 2, "accessToken": access}, expected=400)
            _, rsvp = request(base, f"/api/public/{slug}/rsvps", "POST", {"name": "Guest", "status": "Yes, joyfully", "count": 2, "custom_meal": "Vegetarian", "accessToken": access}, expected=201)
            _, wish = request(base, f"/api/public/{slug}/wishes", "POST", {"name": "Guest", "message": "Congratulations!", "accessToken": access}, expected=201)
            _, public_doc = request(base, f"/api/public/{slug}?access={access}", expected=200)
            assert public_doc["document"]["video"]["mime"] == "video/mp4"
            assert public_doc["document"]["objects"]["hero-photo"]["imageSepia"] == 12

            # Owner response operations.
            request(base, f"/api/invitations/{invite_id}/rsvps/{rsvp['id']}", "PUT", {"status": "Maybe", "guestCount": 3}, token, 200)
            _, responses = request(base, f"/api/invitations/{invite_id}/rsvps", token=token, expected=200)
            assert responses[0]["answers"]["custom_meal"] == "Vegetarian"
            request(base, f"/api/invitations/{invite_id}/wishes/{wish['id']}", "DELETE", token=token, expected=200)

            # Normal user, admin manual plan assignment, and password reset.
            user_email = "creator-smoke@example.com"
            _, user_registered = request(base, "/api/auth/register", "POST", {"email": user_email, "password": "creatorpass123"}, expected=201)
            user_token, user_id = user_registered["token"], user_registered["user"]["id"]
            assert user_registered["user"]["plan"] == "free"
            request(base, f"/api/admin/users/{user_id}/plan", "PUT", {"plan": "creator"}, token, 200)
            _, user_usage = request(base, "/api/account/usage", token=user_token, expected=200)
            assert user_usage["plan"] == "creator"
            _, admin_users = request(base, "/api/admin/users", token=token, expected=200)
            assert next(u for u in admin_users if u["id"] == user_id)["plan"] == "creator"
            _, reset = request(base, "/api/auth/password-reset/request", "POST", {"email": user_email}, expected=200)
            assert reset.get("devToken")
            request(base, "/api/auth/password-reset/confirm", "POST", {"token": reset["devToken"], "newPassword": "creatornew123"}, expected=200)
            request(base, "/api/auth/login", "POST", {"email": user_email, "password": "creatornew123"}, expected=201)

            # Data export and admin password change.
            _, exported = request(base, "/api/account/export", token=token, expected=200)
            assert exported["account"]["email"] == admin_email
            assert exported["account"]["plan"] == "studio"
            request(base, "/api/auth/password", "PUT", {"currentPassword": "oldpassword123", "newPassword": "newpassword123"}, token, 200)
            request(base, "/api/auth/login", "POST", {"email": admin_email, "password": "newpassword123"}, expected=201)

            # Unpublish must close the public endpoint and public write endpoints.
            request(base, f"/api/invitations/{invite_id}/unpublish", "POST", {}, token, 200)
            request(base, f"/api/public/{slug}?access={access}", expected=404)
            request(base, f"/api/public/{slug}/wishes", "POST", {"name": "Guest", "message": "Late", "accessToken": access}, expected=404)
            print("SMOKE_TEST_PASSED")
        finally:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    run()
