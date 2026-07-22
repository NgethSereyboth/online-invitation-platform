"""Deterministic checks for collaboration SSE and graceful direct-upload fallback."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(base: str, path: str, method: str = "GET", body=None, token: str | None = None, cookie: str | None = None, expected: int = 200):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            data = json.loads(response.read() or b"{}")
            response_headers = dict(response.headers)
    except urllib.error.HTTPError as exc:
        status = exc.code
        data = json.loads(exc.read() or b"{}")
        response_headers = dict(exc.headers)
    if status != expected:
        raise AssertionError(f"{method} {path}: expected {expected}, got {status}: {data}")
    return status, data, response_headers


def wait(base: str) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            if request(base, "/api/health")[0] == 200:
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("server unavailable")


def read_sse_event(stream, timeout_seconds: float = 8) -> tuple[str, dict]:
    deadline = time.time() + timeout_seconds
    event = "message"
    data = None
    while time.time() < deadline:
        line = stream.readline().decode("utf-8", "replace").strip()
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = json.loads(line.split(":", 1)[1].strip())
        elif line == "" and data is not None:
            return event, data
    raise AssertionError("Timed out waiting for SSE event")


def run() -> None:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="einvite-realtime-storage-") as data_dir:
        env = {**os.environ, "EINVITE_DATA_DIR": data_dir}
        process = subprocess.Popen(
            [sys.executable, "-u", "server.py", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait(base)
            _, registered, headers = request(
                base,
                "/api/auth/register",
                "POST",
                {"email": "realtime@example.com", "password": "password123"},
                expected=201,
            )
            token = registered["token"]
            cookie = (headers.get("Set-Cookie") or headers.get("set-cookie") or "").split(";", 1)[0]
            document = {
                "eventType": "Wedding",
                "fields": {"names": "Realtime Test", "date": "2026-12-27", "venue": "Venue", "message": "Join us"},
                "objects": {},
                "designPages": [],
                "sectionOrder": ["schedule", "venue", "rsvp"],
                "settings": {"rsvpEnabled": True},
            }
            _, created, _ = request(base, "/api/invitations", "POST", {"slug": "realtime-test", "document": document}, token, expected=201)
            invitation_id = created["id"]

            # Local/default storage intentionally reports that browser-direct object upload
            # is unavailable so the shared client can fall back to the normal raw endpoint.
            _, presign, _ = request(
                base,
                f"/api/invitations/{invitation_id}/assets/presign",
                "POST",
                {"name": "photo.png", "mime": "image/png", "size": 100},
                token,
                expected=409,
            )
            assert presign.get("directUpload") is False

            # Cookie-authenticated SSE emits the current version and then a later update.
            sse_request = urllib.request.Request(
                base + f"/api/invitations/{invitation_id}/events",
                headers={"Cookie": cookie, "Accept": "text/event-stream"},
            )
            with urllib.request.urlopen(sse_request, timeout=10) as stream:
                event, first = read_sse_event(stream)
                assert event == "invitation-update" and int(first["updatedAt"]) > 0

                document["fields"]["message"] = "Updated from another editing session"
                _, saved, _ = request(
                    base,
                    f"/api/invitations/{invitation_id}",
                    "PUT",
                    {"document": document},
                    token,
                    expected=200,
                )
                event, second = read_sse_event(stream, timeout_seconds=10)
                assert event == "invitation-update"
                assert int(second["updatedAt"]) >= int(saved["updatedAt"]) > int(first["updatedAt"])

            print("REALTIME_STORAGE_TEST_PASSED")
        finally:
            process.terminate()
            try:
                process.wait(3)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    run()
