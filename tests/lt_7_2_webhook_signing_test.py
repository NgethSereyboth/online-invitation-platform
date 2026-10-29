#!/usr/bin/env python3
"""LT-7.2 step 6 — outbound webhook signing, delivery and retries (ROADMAP §4.6).

Part 1 — the signing module and the delivery retry policy, in-process:

* sign/verify round trip; tampering with the body fails; a replay older than
  the 5-minute window fails; a future timestamp fails;
* `deliver` retries a 500 up to success with the configured attempt budget and
  does NOT retry a 400.

Part 2 — end-to-end over HTTP with a real server:

* register an account, create + publish an invitation;
* register a webhook destination (a local receiver) through
  `POST /api/account/webhooks` — the secret is returned once;
* submit a public RSVP and assert the receiver got exactly one signed request
  whose `X-EInvite-Signature` verifies with that secret and whose body is the
  `rsvp.created` envelope;
* rotate the secret and prove the next delivery verifies with the new one;
* the list endpoint exposes only the hint, and delete stops deliveries.

`EINVITE_ALLOW_PRIVATE_WEBHOOKS=1` is set for the test server, and every local
`deliver` call passes `allow_private=True`, so the D-6 guard accepts this
loopback receiver. The guard itself — https only, private ranges refused,
redirects not followed, the 64 KiB read cap — is asserted in
`tests/lt_7_2_webhook_delivery_test.py`.

Prints ``LT_7_2_WEBHOOK_SIGNING_PASSED`` on success.
"""
from __future__ import annotations

import http.server
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src" / "python"))
sys.path.insert(0, str(REPO / "tests"))

from core.webhooks import (  # noqa: E402
    DEFAULT_TOLERANCE_MS,
    SIGNATURE_HEADER,
    deliver,
    sign_webhook,
    verify_signature,
)
from v14_test_utils import app_server  # noqa: E402


def _request(base, method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        payload = error.read() or b"{}"
        try:
            return error.code, json.loads(payload)
        except json.JSONDecodeError:
            return error.code, {"_raw": payload.decode("utf-8", "replace")}


class _Receiver:
    """Local HTTP receiver that records signed deliveries and can fail first."""

    def __init__(self, fail_first=0):
        self.requests = []
        self.fail_first = fail_first
        self._lock = threading.Lock()
        receiver = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                with receiver._lock:
                    receiver.requests.append({
                        "path": self.path,
                        "body": body,
                        "signature": self.headers.get(SIGNATURE_HEADER, ""),
                        "content_type": self.headers.get("Content-Type", ""),
                    })
                    fail = len(receiver.requests) <= receiver.fail_first
                self.send_response(500 if fail else 200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')

            def log_message(self, *args):  # silence stderr
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/hook"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def wait_for(self, count=1, timeout=20.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if len(self.requests) >= count:
                    return list(self.requests)
            time.sleep(0.1)
        with self._lock:
            return list(self.requests)

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def test_signature_and_retry_policy():
    body = b'{"event":"rsvp.created","eventId":"abc"}'
    secret = "whsec_unit_test"
    now = 1_700_000_000_000
    signature = sign_webhook(body, secret, timestamp_ms=now)
    assert verify_signature(body, signature, secret, now_ms=now) is True
    assert verify_signature(body + b" ", signature, secret, now_ms=now) is False
    assert verify_signature(body, signature, "other-secret", now_ms=now) is False
    assert verify_signature(body, signature, secret, now_ms=now + 30_000) is True
    assert verify_signature(body, signature, secret, now_ms=now + DEFAULT_TOLERANCE_MS + 1) is False
    assert verify_signature(body, signature, secret, now_ms=now - 31_000) is False

    flaky = _Receiver(fail_first=2)
    try:
        result = deliver(flaky.url, body, secret, attempts=4, backoff_base=0.01, timeout=5,
                         allow_private=True)
        assert result == {"ok": True, "status": 200, "attempts": 3, "error": None}, result
        assert len(flaky.requests) == 3
    finally:
        flaky.close()

    rejecting = _Receiver(fail_first=99)  # every request is a 500
    try:
        result = deliver(rejecting.url, body, secret, attempts=2, backoff_base=0.01, timeout=5,
                         allow_private=True)
        assert result["ok"] is False and result["attempts"] == 2 and result["status"] == 500, result
    finally:
        rejecting.close()

    # A 400 must not be retried (the receiver rejected the request itself).
    class _Reject400(http.server.BaseHTTPRequestHandler):
        calls = 0
        def do_POST(self):  # noqa: N802
            type(self).calls += 1
            self.send_response(400)
            self.end_headers()
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Reject400)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = deliver(f"http://127.0.0.1:{server.server_address[1]}/hook", body, secret,
                         attempts=4, backoff_base=0.01, timeout=5, allow_private=True)
        assert result == {"ok": False, "status": 400, "attempts": 1, "error": "HTTP 400"}, result
        assert _Reject400.calls == 1
    finally:
        server.shutdown(); server.server_close()
    print("[OK] signature round trip, tamper/replay rejection, retry policy", flush=True)


def test_webhook_delivery_end_to_end():
    receiver = _Receiver()
    env = {
        "EINVITE_ALLOW_PRIVATE_WEBHOOKS": "1",
        "EINVITE_DEV_AUTH_TOKENS": "1",
        "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
        "EINVITE_ALLOW_NO_SCANNER": "1",
    }
    try:
        with app_server(extra_env=env) as (_process, base, _data):
            status, auth = _request(base, "POST", "/api/auth/register",
                                    {"email": "wh-owner@einvite.test", "password": "Test1234!Pass"})
            assert status in (200, 201) and auth.get("token"), (status, auth)
            token = auth["token"]

            document = {"schemaVersion": 14, "eventType": "Wedding",
                        "fields": {"names": "Webhook Couple"}, "objects": {}, "designPages": [],
                        "settings": {"rsvpEnabled": True}}
            status, created = _request(base, "POST", "/api/invitations",
                                       {"slug": "wh-rsvp", "document": document}, token=token)
            assert status in (200, 201), (status, created)
            invitation_id = created["id"]

            status, hook = _request(base, "POST", "/api/account/webhooks",
                                    {"url": receiver.url, "events": ["rsvp.created"]}, token=token)
            assert status == 201, (status, hook)
            endpoint_id, secret = hook["id"], hook["secret"]
            assert secret and hook["secretHint"] == secret[-4:], hook

            status, listing = _request(base, "GET", "/api/account/webhooks", token=token)
            assert status == 200 and any(row["id"] == endpoint_id for row in listing["items"]), (status, listing)
            assert all("secret" not in row for row in listing["items"]), listing

            status, published = _request(base, "POST", f"/api/invitations/{invitation_id}/publish", {}, token=token)
            assert status == 201, (status, published)

            status, rsvp = _request(base, "POST", "/api/public/wh-rsvp/rsvps",
                                    {"name": "Webhook Guest", "status": "Yes, joyfully", "count": 2})
            assert status in (200, 201), (status, rsvp)

            captured = receiver.wait_for(1)
            assert captured, "no webhook delivery arrived"
            first = captured[0]
            assert verify_signature(first["body"], first["signature"], secret) is True, first
            envelope = json.loads(first["body"])
            assert envelope["event"] == "rsvp.created", envelope
            assert envelope["data"]["invitationId"] == invitation_id, envelope
            assert envelope["data"]["name"] == "Webhook Guest", envelope
            assert envelope["eventId"] and envelope["timestamp"], envelope

            # Rotate: the new secret signs the next delivery; the old one no longer verifies it.
            status, rotated = _request(base, "POST", f"/api/account/webhooks/{endpoint_id}/rotate", {}, token=token)
            assert status == 200 and rotated["secret"] != secret, (status, rotated)
            new_secret = rotated["secret"]

            status, second = _request(base, "POST", "/api/public/wh-rsvp/rsvps",
                                      {"name": "Webhook Guest Two", "status": "Maybe", "count": 1})
            assert status in (200, 201), (status, second)
            captured = receiver.wait_for(2)
            assert len(captured) >= 2, captured
            latest = captured[-1]
            assert verify_signature(latest["body"], latest["signature"], new_secret) is True, latest
            assert verify_signature(latest["body"], latest["signature"], secret) is False, latest

            # Delete stops deliveries; the endpoint disappears from the list.
            status, _ = _request(base, "DELETE", f"/api/account/webhooks/{endpoint_id}", token=token)
            assert status == 200, status
            status, listing = _request(base, "GET", "/api/account/webhooks", token=token)
            assert status == 200 and all(row["id"] != endpoint_id for row in listing["items"]), listing
            before = len(receiver.requests)
            status, third = _request(base, "POST", "/api/public/wh-rsvp/rsvps",
                                     {"name": "Webhook Guest Three", "status": "Unable to attend", "count": 1})
            assert status in (200, 201), (status, third)
            time.sleep(3)
            assert len(receiver.requests) == before, "deleted endpoint still received a delivery"
            print("[OK] signed rsvp.created delivery, rotation, hint-only listing, delete", flush=True)
    finally:
        receiver.close()
    print("LT_7_2_WEBHOOK_SIGNING_PASSED", flush=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))
