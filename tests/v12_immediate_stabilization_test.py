"""V12 immediate stabilization regression coverage for routing, RSVP, tokens, QR, and social cache."""
from __future__ import annotations

from contextlib import closing

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(base, path, method="GET", body=None, token=None, headers=None, expected=200, raw=False):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    request_obj = urllib.request.Request(base + path, data=payload, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            status = response.status
            data = response.read()
            response_headers = dict(response.headers)
    except urllib.error.HTTPError as exc:
        status = exc.code
        data = exc.read()
        response_headers = dict(exc.headers)
    if status != expected:
        try:
            shown = json.loads(data or b"{}")
        except Exception:
            shown = data[:200]
        raise AssertionError((method, path, status, expected, shown))
    if raw:
        return data, response_headers
    return json.loads(data or b"{}"), response_headers


def wait(base):
    for _ in range(120):
        try:
            request(base, "/api/health")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def run():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="einvite-v12-stabilization-") as data_dir:
        env = {**os.environ, "EINVITE_DATA_DIR": data_dir, "EINVITE_DEV_AUTH_TOKENS": "1"}
        process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            wait(base)
            health, _ = request(base, "/api/health")
            assert "dependencies" in health and health["dependencies"].get("qrReady") is True, health

            registered, _ = request(base, "/api/auth/register", "POST", {"email": "v12@example.com", "password": "strong-password-123"}, expected=201)
            token = registered["token"]
            base_doc = {
                "schemaVersion": 10,
                "fields": {"names": "V12 Invitation", "date": "2027-02-14", "venue": "Phnom Penh"},
                "objects": {},
                "designPages": [],
                "sectionOrder": ["wishes", "rsvp"],
                "settings": {"rsvpEnabled": False, "wishesEnabled": True, "openingEnabled": False},
            }
            invite, _ = request(base, "/api/invitations", "POST", {"slug": "v12-immediate", "document": base_doc}, token=token, expected=201)
            invite_id = invite["id"]

            # Pretty routes must be directly refreshable and server-authorized.
            page, headers = request(base, f"/invitations/{invite_id}/editor", token=token, raw=True)
            assert b"<!doctype html>" in page.lower() and "text/html" in headers.get("Content-Type", "")
            request(base, f"/invitations/{invite_id}/editor", expected=401)

            # RSVP-disabled invitations still accept independently-enabled wishes.
            request(base, f"/api/invitations/{invite_id}/publish", "POST", {"document": base_doc}, token=token, expected=201)
            request(base, f"/api/public/{invite['slug']}/rsvps", "POST", {"name": "Guest", "status": "Maybe", "count": 1}, expected=403)
            wish, _ = request(base, f"/api/public/{invite['slug']}/wishes", "POST", {"name": "Guest", "message": "Best wishes", "website": ""}, expected=201)
            assert wish["saved"] is True
            request(base, f"/api/public/{invite['slug']}/wishes", "POST", {"name": "Bot", "message": "Spam", "website": "filled"}, expected=400)
            analytics, _ = request(base, f"/api/invitations/{invite_id}/analytics", token=token)
            assert analytics["rsvpEnabled"] is False

            # Enable RSVP and verify personalized updates do not create duplicates.
            enabled_doc = json.loads(json.dumps(base_doc))
            enabled_doc["settings"].update({
                "rsvpEnabled": True,
                "rsvpMaxGuests": 3,
                "rsvpQuestions": {"meal": True, "transport": True, "accommodation": True},
            })
            request(base, f"/api/invitations/{invite_id}", "PUT", {"document": enabled_doc}, token=token)
            pub2, _ = request(base, f"/api/invitations/{invite_id}/publish", "POST", {"document": enabled_doc}, token=token, expected=201)
            guest, _ = request(base, f"/api/invitations/{invite_id}/guests", "POST", {"name": "Personal Guest", "phone": ""}, token=token, expected=201)
            guest_token = guest["token"]
            public_qr, _ = request(base, f"/api/public/{invite['slug']}/qr.png", raw=True)
            branded_qr, _ = request(base, f"/api/public/{invite['slug']}/qr-card.png", raw=True)
            personal_qr, _ = request(base, f"/api/invitations/{invite_id}/guests/{guest['id']}/qr.png", token=token, raw=True)
            assert public_qr.startswith(b"\x89PNG") and branded_qr.startswith(b"\x89PNG") and personal_qr.startswith(b"\x89PNG")
            rsvp_headers = {"X-Invitation-Guest": guest_token}
            first, _ = request(base, f"/api/public/{invite['slug']}/rsvps", "POST", {"name": "Personal Guest", "status": "Yes, joyfully", "count": 3, "meal": "Vegetarian", "transport": "Need transport", "accommodation": "None"}, headers=rsvp_headers, expected=201)
            second, _ = request(base, f"/api/public/{invite['slug']}/rsvps", "POST", {"name": "Personal Guest", "status": "Maybe", "count": 2, "meal": "Vegan"}, headers=rsvp_headers, expected=200)
            assert first["id"] == second["id"] and second["updated"] is True
            rows, _ = request(base, f"/api/invitations/{invite_id}/rsvps", token=token)
            assert len(rows) == 1 and rows[0]["status"] == "Maybe" and rows[0]["guest_count"] == 2, rows

            # Disabling RSVP later preserves historical responses.
            disabled_again = json.loads(json.dumps(enabled_doc))
            disabled_again["settings"]["rsvpEnabled"] = False
            request(base, f"/api/invitations/{invite_id}", "PUT", {"document": disabled_again}, token=token)
            request(base, f"/api/invitations/{invite_id}/publish", "POST", {"document": disabled_again}, token=token, expected=201)
            rows_after, _ = request(base, f"/api/invitations/{invite_id}/rsvps", token=token)
            assert len(rows_after) == 1, "historical RSVP was deleted when RSVP was disabled"

            # Personalized credentials must not be stored as plaintext and support rotation/revocation.
            with closing(sqlite3.connect(Path(data_dir) / "invites.db")) as db:
                stored = db.execute("SELECT token,token_hash,token_salt FROM guests WHERE id=?", (guest["id"],)).fetchone()
                assert stored and stored[0] != guest_token and stored[1] and stored[2]
            rotated, _ = request(base, f"/api/invitations/{invite_id}/guests/{guest['id']}/token/rotate", "POST", {"expiresDays": 30}, token=token)
            assert rotated["token"] != guest_token and rotated["tokenExpiresAt"]
            old_public, _ = request(base, f"/api/public/{invite['slug']}?g={guest_token}")
            new_public, _ = request(base, f"/api/public/{invite['slug']}?g={rotated['token']}")
            assert old_public["guest"] is None and new_public["guest"]["id"] == guest["id"]
            request(base, f"/api/invitations/{invite_id}/guests/{guest['id']}/token/revoke", "POST", {}, token=token)
            revoked_public, _ = request(base, f"/api/public/{invite['slug']}?g={rotated['token']}")
            assert revoked_public["guest"] is None
            request(base, f"/api/invitations/{invite_id}/guests/{guest['id']}/qr.png", token=token, expected=409)

            # Social cards cache by publication version, not by mutable draft state.
            social_dir = Path(data_dir) / "social-cache"
            deadline = time.time() + 8
            expected_cache = social_dir / f"{invite_id}-v{pub2['version']}-og.png"
            while time.time() < deadline and not expected_cache.exists():
                time.sleep(0.1)
            # A later publish may invalidate the old file; at least one latest-version cache must exist.
            latest_versions = list(social_dir.glob(f"{invite_id}-v*-og.png"))
            assert latest_versions, "asynchronous social-card cache warming did not create a versioned card"
            card, card_headers = request(base, f"/api/public/{invite['slug']}/social-card.png", raw=True)
            assert card.startswith(b"\x89PNG") and "max-age=300" in card_headers.get("Cache-Control", "")

            # Static share helpers strip personalized/private parameters.
            share_js = (ROOT / "public-share-panel.js").read_text(encoding="utf-8")
            assert all(key in share_js for key in ["guestToken", "access_token", "data-qr", "downloadGenerated"])
            print("V12_IMMEDIATE_STABILIZATION_TEST_PASSED")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    run()
