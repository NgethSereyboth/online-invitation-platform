"""V13 future-foundation regression coverage for security, studio, marketplace, privacy, and protected galleries."""
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
sys.path.insert(0, str(ROOT))
from security_v13 import totp_code  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(base, path, method="GET", body=None, token=None, headers=None, expected=200, raw=False):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=payload, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status, data, response_headers = response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        status, data, response_headers = exc.code, exc.read(), dict(exc.headers)
    if status != expected:
        try:
            shown = json.loads(data or b"{}")
        except Exception:
            shown = data[:240]
        raise AssertionError((method, path, status, expected, shown))
    if raw:
        return data, response_headers
    return json.loads(data or b"{}"), response_headers


def raw_upload(base, invite_id, token, payload, mime="image/png", filename="gallery.png"):
    req = urllib.request.Request(
        base + f"/api/invitations/{invite_id}/assets/raw",
        data=payload,
        method="POST",
        headers={
            "Content-Type": mime,
            "Content-Length": str(len(payload)),
            "X-File-Name": urllib.parse.quote(filename),
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def wait(base):
    for _ in range(300):
        try:
            request(base, "/api/health")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def run():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="einvite-v13-future-") as data_dir:
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": data_dir,
            "EINVITE_DEV_AUTH_TOKENS": "1",
            "EINVITE_ADMIN_EMAIL": "admin-v13@example.com",
            "EINVITE_MARKETPLACE_REQUIRES_MODERATION": "1",
        }
        proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            wait(base)
            admin, _ = request(base, "/api/auth/register", "POST", {"email": "admin-v13@example.com", "password": "strong-admin-password"}, expected=201)
            admin_token = admin["token"]
            owner, _ = request(base, "/api/auth/register", "POST", {"email": "owner-v13@example.com", "password": "strong-owner-password"}, expected=201)
            token = owner["token"]

            security, _ = request(base, "/api/account/security", token=token)
            assert security["passwordAlgorithm"] in {"argon2id-v1", "pbkdf2-sha256-v2"}

            studio, _ = request(base, "/api/account/studio", "PUT", {
                "studioName": "Khmer Celebration Studio",
                "whiteLabel": {"primaryColor": "#663319", "accentColor": "#c89b4a", "supportEmail": "hello@example.com", "hidePlatformBrand": True},
            }, token=token)
            assert studio["studioName"] == "Khmer Celebration Studio"
            profile, _ = request(base, "/api/account/studio", token=token)
            assert profile["studioName"] == "Khmer Celebration Studio"

            setup, _ = request(base, "/api/account/mfa/setup", "POST", {}, token=token)
            code = totp_code(setup["secret"], int(time.time()) // 30)
            enabled, _ = request(base, "/api/account/mfa/enable", "POST", {"code": code}, token=token)
            assert enabled["enabled"] is True
            login, _ = request(base, "/api/auth/login", "POST", {"email": "owner-v13@example.com", "password": "strong-owner-password"}, expected=202)
            assert login["mfaRequired"] is True
            code = totp_code(setup["secret"], int(time.time()) // 30)
            completed, _ = request(base, "/api/auth/mfa/complete", "POST", {"mfaToken": login["mfaToken"], "code": code}, expected=201)
            assert completed.get("token")
            sessions, _ = request(base, "/api/account/sessions", token=token)
            assert len(sessions) >= 2

            # Marketplace moderation and license metadata.
            template_doc = {"schemaVersion": 13, "fields": {"names": "Licensed Template"}, "objects": {}, "designPages": [], "sectionOrder": []}
            template, _ = request(base, "/api/templates", "POST", {"name": "Licensed Template", "category": "Wedding", "licenseType": "commercial", "visibility": "public", "document": template_doc}, token=token, expected=201)
            assert template["marketplaceStatus"] == "pending" and template["visibility"] == "private"
            market, _ = request(base, "/api/template-marketplace")
            assert all(item["id"] != template["id"] for item in market)
            request(base, f"/api/admin/templates/{template['id']}/visibility", "PUT", {"visibility": "public"}, token=admin_token)
            market, _ = request(base, "/api/template-marketplace")
            approved = next(item for item in market if item["id"] == template["id"])
            assert approved["licenseType"] == "commercial" and approved["marketplaceStatus"] == "approved"

            # Protected gallery + privacy consent + studio brand.
            doc = {
                "schemaVersion": 13,
                "fields": {"names": "Private Gallery Event", "date": "2027-04-12", "venue": "Phnom Penh"},
                "objects": {},
                "designPages": [],
                "sectionOrder": ["gallery", "events", "guest-info"],
                "settings": {"galleryEnabled": True, "openingEnabled": False, "rsvpEnabled": False},
                "galleryProtection": {"enabled": True},
                "privacy": {"analyticsConsentRequired": True, "externalMediaConsentRequired": True},
                "events": [{"id": "ceremony", "name": "Main Ceremony", "date": "2027-04-12", "time": "10:00", "venue": "Phnom Penh"}],
            }
            invite, _ = request(base, "/api/invitations", "POST", {"slug": "v13-private-gallery", "document": doc}, token=token, expected=201)
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
            asset = raw_upload(base, invite["id"], token, png)
            doc["objects"]["gallery-only"] = {"type": "image", "src": asset["url"], "showInGallery": True, "showInHero": False, "alt": "Private celebration"}
            request(base, f"/api/invitations/{invite['id']}", "PUT", {"document": doc}, token=token)
            request(base, f"/api/invitations/{invite['id']}/gallery-access", "PUT", {"enabled": True, "password": "gallery-secret-123"}, token=token)
            request(base, f"/api/invitations/{invite['id']}/publish", "POST", {"document": doc}, token=token, expected=201)

            # Direct public media is blocked for exclusive protected-gallery media.
            request(base, asset["url"], expected=403, raw=True)
            public, _ = request(base, f"/api/public/{invite['slug']}")
            assert public["galleryProtected"] is True and public["galleryAuthorized"] is False
            assert public["analyticsConsentRequired"] is True and public["externalMediaConsentRequired"] is True
            assert public["studioBrand"]["name"] == "Khmer Celebration Studio" and public["studioBrand"]["hidePlatformBrand"] is True
            locked_object = public["document"]["objects"]["gallery-only"]
            assert not locked_object.get("src") and locked_object.get("showInGallery") is False

            unlocked, _ = request(base, f"/api/public/{invite['slug']}/gallery/unlock", "POST", {"password": "gallery-secret-123"})
            public2, _ = request(base, f"/api/public/{invite['slug']}", headers={"X-Gallery-Access": unlocked["galleryAccessToken"]})
            signed_src = public2["document"]["objects"]["gallery-only"]["src"]
            assert signed_src.startswith("/api/media/") and "sig=" in signed_src
            image, _ = request(base, signed_src, raw=True)
            assert image.startswith(b"\x89PNG")

            # Explicit privacy consent view endpoint records only after consent.
            before, _ = request(base, f"/api/invitations/{invite['id']}/analytics", token=token)
            request(base, f"/api/public/{invite['slug']}")
            middle, _ = request(base, f"/api/invitations/{invite['id']}/analytics", token=token)
            assert middle["totalViews"] == before["totalViews"]
            request(base, f"/api/public/{invite['slug']}/view", "POST", {})
            after, _ = request(base, f"/api/invitations/{invite['id']}/analytics", token=token)
            assert after["totalViews"] == before["totalViews"] + 1

            # Studio operations APIs stay attached to the same invitation.
            comment, _ = request(base, f"/api/invitations/{invite['id']}/comments", "POST", {"body": "Please review the gallery", "objectId": "gallery-only"}, token=token, expected=201)
            request(base, f"/api/invitations/{invite['id']}/comments/{comment['id']}", "PUT", {"resolved": True}, token=token)
            approval, _ = request(base, f"/api/invitations/{invite['id']}/approvals", "POST", {"note": "Ready for review"}, token=token, expected=201)
            assert approval["status"] == "pending"
            request(base, f"/invitations/{invite['id']}/checkin", token=token, raw=True)

            print("V13_FUTURE_FOUNDATION_TEST_PASSED")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)
            if proc.stderr:
                err = proc.stderr.read().decode("utf-8", "replace")
                if proc.returncode not in (0, -15) and err:
                    print(err, file=sys.stderr)


if __name__ == "__main__":
    run()
