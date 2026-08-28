"""Regression tests for V12 storage references, protected media, and derivative limits."""
from __future__ import annotations

from contextlib import closing

import base64
import json
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(base, path, method="GET", body=None, token=None, headers=None, expected=200, binary=False):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            payload = response.read()
            response_headers = dict(response.headers)
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = exc.read()
        response_headers = dict(exc.headers)
    if status != expected:
        try:
            shown = json.loads(payload or b"{}")
        except Exception:
            shown = payload[:200]
        raise AssertionError((method, path, status, expected, shown))
    if binary:
        return payload, response_headers
    return json.loads(payload or b"{}"), response_headers


def raw_upload(base, invite_id, token, payload, name="shared.png", expected=201):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/png",
        "Content-Length": str(len(payload)),
        "X-File-Name": urllib.parse.quote(name),
    }
    req = urllib.request.Request(base + f"/api/invitations/{invite_id}/assets/raw", data=payload, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.status
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = json.loads(exc.read() or b"{}")
    if status != expected:
        raise AssertionError((status, expected, body))
    return body


def wait(base):
    for _ in range(100):
        try:
            request(base, "/api/health")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def huge_png_header(width=50000, height=50000):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # The decompression-bomb guard is expected to reject the dimensions before full decode.
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b"")


def run():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="einvite-v12-storage-") as data_dir:
        env = {**os.environ, "EINVITE_DATA_DIR": data_dir, "EINVITE_DEV_AUTH_TOKENS": "1"}
        process = subprocess.Popen([sys.executable, "-u", str(ROOT / "server.py"), "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            wait(base)
            registered, _ = request(base, "/api/auth/register", "POST", {"email": "storage@example.com", "password": "correct-horse-123"}, expected=201)
            token = registered["token"]
            doc = {"schemaVersion": 10, "fields": {"names": "Protected Couple", "date": "2027-01-01", "venue": "Private Venue"}, "settings": {"rsvpEnabled": False, "openingEnabled": True}, "objects": {}, "designPages": [], "sectionOrder": []}
            a, _ = request(base, "/api/invitations", "POST", {"slug": "storage-a", "document": doc}, token=token, expected=201)
            b, _ = request(base, "/api/invitations", "POST", {"slug": "storage-b", "document": doc}, token=token, expected=201)
            first = raw_upload(base, a["id"], token, VALID_PNG, "same.png")
            second = raw_upload(base, b["id"], token, VALID_PNG, "same.png")
            assert second["duplicate"] is True
            assert first["url"] == second["url"], (first, second)
            path = Path(urllib.parse.urlparse(first["url"]).path).name
            physical = Path(data_dir) / "uploads" / path
            assert physical.is_file()
            with closing(sqlite3.connect(Path(data_dir) / "invites.db")) as db:
                object_rows = db.execute("SELECT path,ref_count FROM stored_objects WHERE path=?", (path,)).fetchall()
                assert len(object_rows) == 1 and object_rows[0][1] == 2, object_rows

            request(base, f"/api/invitations/{a['id']}", "DELETE", token=token, expected=200)
            assert physical.is_file(), "shared physical object was deleted with the first invitation"
            request(base, first["url"], token=token, expected=200, binary=True)
            with closing(sqlite3.connect(Path(data_dir) / "invites.db")) as db:
                assert db.execute("SELECT ref_count FROM stored_objects WHERE path=?", (path,)).fetchone()[0] == 1

            # Protect the second invitation and ensure direct media access is denied.
            private_doc = json.loads(json.dumps(doc))
            private_doc["objects"]["photo"] = {"type": "image", "src": second["url"], "responsiveBase": second["responsiveBase"], "intrinsicWidth": second["width"], "intrinsicHeight": second["height"]}
            request(base, f"/api/invitations/{b['id']}", "PUT", {"document": private_doc}, token=token)
            request(base, f"/api/invitations/{b['id']}/access", "PUT", {"mode": "password", "password": "private-pass-123"}, token=token)
            request(base, f"/api/invitations/{b['id']}/publish", "POST", {"document": private_doc}, token=token, expected=201)
            request(base, second["url"], expected=403)
            request(base, second["responsiveBase"] + "?w=480&format=webp", expected=403)
            unlocked, _ = request(base, f"/api/public/{b['slug']}/unlock", "POST", {"password": "private-pass-123"})
            access = unlocked["accessToken"]
            public, _ = request(base, f"/api/public/{b['slug']}", headers={"X-Invitation-Access": access})
            signed_src = public["document"]["objects"]["photo"]["src"]
            signed_responsive = public["document"]["objects"]["photo"]["responsiveBase"]
            assert signed_src.startswith("/api/media/") and "sig=" in signed_src
            request(base, signed_src, expected=200, binary=True)
            derivative, derivative_headers = request(base, signed_responsive + "&w=480&format=webp", expected=200, binary=True)
            assert derivative.startswith(b"RIFF") and "private" in derivative_headers.get("Cache-Control", "")

            # Strict derivative variants and file-signature validation.
            request(base, second["responsiveBase"] + "?w=400&format=webp", token=token, expected=400)
            request(base, second["responsiveBase"] + "?w=480&format=tiff", token=token, expected=400)
            raw_upload(base, b["id"], token, b"this is not a png", "fake.png", expected=400)
            oversized = huge_png_header()
            raw_upload(base, b["id"], token, oversized, "oversized.png", expected=400)

            # Final reference removal must delete the physical object and stored-object row.
            request(base, f"/api/invitations/{b['id']}", "DELETE", token=token)
            assert not physical.exists(), "final reference removal did not delete physical object"
            with closing(sqlite3.connect(Path(data_dir) / "invites.db")) as db:
                assert db.execute("SELECT 1 FROM stored_objects WHERE path=?", (path,)).fetchone() is None
            print("V12_STORAGE_PRIVACY_TEST_PASSED")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    run()
