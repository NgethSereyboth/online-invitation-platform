#!/usr/bin/env python3
"""HTTP regression coverage for canonical and legacy uploaded-asset identities."""
from __future__ import annotations

import base64
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(base: str, path: str, method: str = "GET", body=None, token: str = "", expected: int = 200):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.status
            payload = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = json.loads(exc.read() or b"{}")
    assert status == expected, (method, path, status, expected, payload)
    return payload


def upload(base: str, invitation_id: str, token: str, name: str):
    req = urllib.request.Request(
        base + f"/api/invitations/{invitation_id}/assets/raw",
        data=PNG,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "image/png",
            "Content-Length": str(len(PNG)),
            "X-File-Name": urllib.parse.quote(name),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        assert response.status == 201
        return json.loads(response.read())


def wait(base: str) -> None:
    for _ in range(120):
        try:
            request(base, "/api/health")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def document(asset_id: str = "", *, server_id: str = "", url: str = ""):
    photo = {"type": "image", "src": url, "width": "80%", "height": "240px", "alt": "Uploaded photo"}
    if asset_id:
        photo["assetId"] = asset_id
    if server_id:
        photo["serverId"] = server_id
    return {
        "schemaVersion": 13,
        "fields": {"names": "Dara & Sophea", "namesKm": "ដារ៉ា និង សុភា", "date": "2027-01-03", "venue": "Phnom Penh", "venueKm": "ភ្នំពេញ"},
        "objects": {"photo": photo},
        "designPages": [],
        "sectionOrder": ["gallery", "wishes"],
        "settings": {"rsvpEnabled": False, "wishesEnabled": True},
        "palette": {"background": "#fff8e7", "text": "#342c26"},
        "accent": "#8a5b16",
    }


def create_invite(base: str, token: str, slug: str):
    return request(base, "/api/invitations", "POST", {"slug": slug, "document": document()}, token, 201)


def main() -> int:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="einvite-v052-assets-") as data_dir:
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
            owner = request(base, "/api/auth/register", "POST", {"email": "asset-owner@example.com", "password": "password123"}, expected=201)
            other = request(base, "/api/auth/register", "POST", {"email": "asset-other@example.com", "password": "password123"}, expected=201)
            owner_token, other_token = owner["token"], other["token"]

            canonical_invite = create_invite(base, owner_token, "asset-canonical")
            canonical_asset = upload(base, canonical_invite["id"], owner_token, "canonical.png")
            canonical_doc = document(canonical_asset["id"], server_id=canonical_asset["id"], url=canonical_asset["url"])
            request(base, f"/api/invitations/{canonical_invite['id']}/publish", "POST", {"document": canonical_doc}, owner_token, 201)

            legacy_invite = create_invite(base, owner_token, "asset-legacy")
            legacy_asset = upload(base, legacy_invite["id"], owner_token, "legacy.png")
            legacy_doc = document("image-local-1700000000000", server_id=legacy_asset["id"], url=legacy_asset["url"])
            request(base, f"/api/invitations/{legacy_invite['id']}/publish", "POST", {"document": legacy_doc}, owner_token, 201)
            with closing(sqlite3.connect(Path(data_dir) / "invites.db")) as db:
                snapshot = json.loads(db.execute("SELECT document_json FROM publications WHERE invitation_id=? ORDER BY published_at DESC LIMIT 1", (legacy_invite["id"],)).fetchone()[0])
            migrated = snapshot["objects"]["photo"]
            assert migrated["assetId"] == legacy_asset["id"], migrated
            assert migrated["serverId"] == legacy_asset["id"], migrated
            assert migrated["localAssetId"] == "image-local-1700000000000", migrated

            same_workspace_invite = create_invite(base, owner_token, "asset-wrong-invitation")
            wrong_invitation_doc = document("image-local-wrong-invitation", server_id=canonical_asset["id"], url=canonical_asset["url"])
            blocked = request(base, f"/api/invitations/{same_workspace_invite['id']}/publish", "POST", {"document": wrong_invitation_doc}, owner_token, 409)
            codes = {item["code"] for item in blocked["readiness"]["blockers"]}
            assert "asset_wrong_invitation" in codes, blocked

            other_invite = create_invite(base, other_token, "asset-other-workspace")
            other_asset = upload(base, other_invite["id"], other_token, "other.png")
            wrong_workspace_invite = create_invite(base, owner_token, "asset-wrong-workspace")
            wrong_workspace_doc = document("image-local-wrong-workspace", server_id=other_asset["id"], url=other_asset["url"])
            blocked = request(base, f"/api/invitations/{wrong_workspace_invite['id']}/publish", "POST", {"document": wrong_workspace_doc}, owner_token, 409)
            codes = {item["code"] for item in blocked["readiness"]["blockers"]}
            assert "asset_wrong_workspace" in codes, blocked

            missing_invite = create_invite(base, owner_token, "asset-missing")
            blocked = request(base, f"/api/invitations/{missing_invite['id']}/publish", "POST", {"document": document("image-local-missing")}, owner_token, 409)
            assert {item["code"] for item in blocked["readiness"]["blockers"]} == {"asset_missing"}, blocked
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    print("V0_52_ASSET_IDENTITY_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
