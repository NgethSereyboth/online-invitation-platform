"""Backend test for the signed browser-direct R2/S3 upload registration flow."""
from __future__ import annotations

import base64
import importlib
import io
import json
import os
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(base: str, path: str, method: str = "GET", body=None, token: str | None = None, expected: int = 200):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            status = response.status
            payload = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = json.loads(exc.read() or b"{}")
    if status != expected:
        raise AssertionError(f"{method} {path}: expected {expected}, got {status}: {payload}")
    return payload


class FakeBody(io.BytesIO):
    pass


class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def generate_presigned_url(self, operation, Params, ExpiresIn, HttpMethod):
        assert operation == "put_object"
        assert HttpMethod == "PUT"
        return f"https://storage.example.test/{Params['Key']}?signed=1"

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return {"ContentLength": len(self.objects[Key]), "ContentType": "image/png"}

    def get_object(self, Bucket, Key, Range=None):
        if Key not in self.objects:
            raise KeyError(Key)
        data = self.objects[Key]
        if Range and Range.startswith("bytes=0-"):
            end = int(Range.split("-", 1)[1])
            data = data[: end + 1]
        return {"Body": FakeBody(data), "ContentType": "image/png"}


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="einvite-signed-upload-") as data_dir:
        os.environ["EINVITE_DATA_DIR"] = data_dir
        os.environ["EINVITE_UPLOAD_SIGNING_SECRET"] = "test-signing-secret"
        server = importlib.import_module("server")

        fake = FakeS3()
        server.OBJECT_STORAGE_BUCKET = "test-bucket"
        server.OBJECT_STORAGE_PREFIX = "materials"
        server.OBJECT_STORAGE_PUBLIC_BASE_URL = "https://cdn.example.test"
        server.object_storage_enabled = lambda: True
        server.object_storage_client = lambda: fake

        port = free_port()
        httpd = server.ThreadingHTTPServer(("127.0.0.1", port), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"
        try:
            registered = request(base, "/api/auth/register", "POST", {"email": "upload@example.com", "password": "password123"}, expected=201)
            token = registered["token"]
            document = {
                "eventType": "Wedding",
                "fields": {"names": "Signed Upload", "date": "2026-12-27", "venue": "Venue", "message": "Join us"},
                "objects": {},
                "designPages": [],
                "sectionOrder": ["gallery", "rsvp"],
                "settings": {"rsvpEnabled": True, "galleryEnabled": True},
            }
            created = request(base, "/api/invitations", "POST", {"slug": "signed-upload", "document": document}, token, expected=201)
            invitation_id = created["id"]

            # A valid 1x1 PNG. The browser would PUT these bytes directly to the
            # signed URL; the fake object store lets this deterministic test focus
            # on the server-side signing, verification, and registration contract.
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
            signed = request(
                base,
                f"/api/invitations/{invitation_id}/assets/presign",
                "POST",
                {"name": "photo.png", "mime": "image/png", "size": len(png)},
                token,
                expected=200,
            )
            assert signed["directUpload"] is True
            assert signed["uploadUrl"].startswith("https://storage.example.test/")
            claim = signed["claim"]
            fake.objects[server.object_storage_key(claim["path"])] = png

            completed = request(
                base,
                f"/api/invitations/{invitation_id}/assets/complete",
                "POST",
                {"name": "photo.png", "claim": claim},
                token,
                expected=201,
            )
            assert completed["directUpload"] is True
            assert completed["url"].startswith("https://cdn.example.test/")

            assets = request(base, "/api/assets", token=token)
            assert len(assets) == 1
            assert assets[0]["name"] == "photo.png"
            assert assets[0]["url"] == completed["url"]
            print("SIGNED_UPLOAD_BACKEND_TEST_PASSED")
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    run()
