#!/usr/bin/env python3
"""LT-7.2 step 6b — webhook destination rules and the durable delivery queue.

Part 1 — the D-6 SSRF contract, in-process:

* https only; `http` is refused unless the explicit private-receiver opt-out is on;
* loopback, RFC1918, link-local (the cloud metadata address), IPv6 loopback and
  userinfo URLs are refused;
* a `3xx` answer is final and its `Location` is never fetched;
* the reply body is read with the 64 KiB cap.

Part 2 — the queue, against a real DB in a child process:

* `dispatch_webhook_event` writes one `webhook.deliver` job per subscribed
  endpoint instead of spawning an untracked thread;
* a 5xx attempt is retried on the 1 s / 2 s / 4 s / 8 s schedule (injected clock,
  no sleeping), the fifth failure ends the job as `failed`;
* a 400 ends the job after exactly one attempt;
* every attempt is freshly signed and verifies with `verify_signature`.

Prints ``LT_7_2_WEBHOOK_DELIVERY_PASSED`` on success.
"""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src" / "python"))
sys.path.insert(0, str(REPO / "tests"))

from core.webhooks import (  # noqa: E402
    MAX_RESPONSE_BYTES,
    SIGNATURE_HEADER,
    _read_capped,
    deliver,
    validate_destination,
    verify_signature,
)


class _Receiver:
    """Local receiver with a scripted status list and per-request records."""

    def __init__(self, statuses=(200,), path="/hook"):
        self.requests = []
        self.statuses = list(statuses)
        self.path = path
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
                        "location": self.headers.get("Location", ""),
                    })
                    index = len(receiver.requests) - 1
                    status = receiver.statuses[min(index, len(receiver.statuses) - 1)]
                self.send_response(status)
                if 300 <= status < 400:
                    self.send_header("Location", receiver.redirect_to)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')

            def log_message(self, *args):  # silence stderr
                pass

        self.redirect_to = ""
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}{path}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def test_destination_rules():
    destination = validate_destination("https://93.184.216.34/hook?x=1")
    assert destination["scheme"] == "https"
    assert destination["port"] == 443
    assert destination["ips"] == ["93.184.216.34"]
    assert destination["query"] == "x=1"

    for url in (
        "http://93.184.216.34/hook",          # plain http
        "https://127.0.0.1/hook",             # loopback
        "https://10.1.2.3/hook",              # RFC1918
        "https://172.16.0.9/hook",            # RFC1918
        "https://169.254.169.254/latest/meta-data/",  # link-local metadata
        "https://[::1]/hook",                 # IPv6 loopback
        "https://user:pw@93.184.216.34/h",    # embedded credentials
        "ftp://93.184.216.34/hook",           # not http(s)
        "not-a-url",
        "",
    ):
        with pytest.raises(ValueError):
            validate_destination(url)

    local = validate_destination("http://127.0.0.1:1234/hook", allow_private=True)
    assert local["port"] == 1234 and local["ips"] == ["127.0.0.1"]

    # deliver() refuses at delivery time too, not only at registration.
    refused = deliver("http://127.0.0.1:9/hook", b"{}", "whsec_x", attempts=1)
    assert refused["ok"] is False and refused["status"] is None
    assert "invalid destination" in (refused["error"] or "")
    print("[OK] destination rules: https, public address, no userinfo", flush=True)


def test_read_cap():
    calls = []

    class _Body:
        def read(self, size=-1):
            calls.append(size)
            return b"x" * min(size if size and size > 0 else MAX_RESPONSE_BYTES, 200_000)

    data = _read_capped(_Body())
    assert calls == [MAX_RESPONSE_BYTES], calls
    assert len(data) == MAX_RESPONSE_BYTES
    print("[OK] response body capped at 64 KiB", flush=True)


def test_redirect_is_not_followed():
    target = _Receiver()
    source = _Receiver(statuses=(302,))
    source.redirect_to = target.url
    try:
        result = deliver(source.url, b'{"event":"x"}', "whsec_test", attempts=1, allow_private=True)
        assert result == {"ok": False, "status": 302, "attempts": 1, "error": "HTTP 302"}, result
        time.sleep(0.4)
        assert len(source.requests) == 1
        assert target.requests == [], target.requests
    finally:
        source.close()
        target.close()
    print("[OK] a 3xx is final and its Location is never fetched", flush=True)


def test_local_delivery_verifies_each_attempt():
    receiver = _Receiver(statuses=(500, 200))
    body = b'{"event":"rsvp.created","eventId":"q1"}'
    secret = "whsec_delivery_rules"
    try:
        result = deliver(receiver.url, body, secret, attempts=2, backoff_base=0.01,
                         allow_private=True)
        assert result == {"ok": True, "status": 200, "attempts": 2, "error": None}, result
        assert len(receiver.requests) == 2
        for request in receiver.requests:
            assert request["body"] == body
            assert verify_signature(request["body"], request["signature"], secret,
                                    now_ms=int(time.time() * 1000)) is True
    finally:
        receiver.close()
    print("[OK] each attempt is freshly signed and verifies", flush=True)


_QUEUE_CHILD = r'''
import json, os, sys, time
sys.path.insert(0, os.environ["EINVITE_SRC"])
import server

server.ensure_platform_schema(server.connect)

ENDPOINTS = json.loads(os.environ["WEBHOOK_ENDPOINTS"])
T0 = int(time.time() * 1000)

with server.connect() as db:
    server._ensure_webhook_schema(db)
    for endpoint in ENDPOINTS:
        db.execute(
            "INSERT INTO webhook_endpoints(id,owner_id,url,events_json,secret,secret_hint,active,created_at,failure_count) "
            "VALUES(?,?,?,'[\"*\"]',?,'test',1,?,0)",
            (endpoint["id"], "owner-1", endpoint["url"], endpoint["secret"], T0))

count = server.dispatch_webhook_event("rsvp.created", {"invitationId": "inv-1"}, "owner-1", process=False)
# Pin the queue's clock to T0 so the injected steps are the only clock.
with server.connect() as db:
    db.execute("UPDATE background_jobs SET available_at=?,created_at=? WHERE kind='webhook.deliver'", (T0, T0))

def state():
    with server.connect() as db:
        rows = db.execute("SELECT id,state,attempts,available_at,last_error FROM background_jobs WHERE kind='webhook.deliver' ORDER BY created_at").fetchall()
        return [dict(row) for row in rows]

report = {"dispatched": count, "steps": []}
for step in json.loads(os.environ["WEBHOOK_STEPS"]):
    processed = server.process_webhook_jobs(now_ms=T0 + step["offsetMs"])
    report["steps"].append({"offsetMs": step["offsetMs"], "processed": processed, "jobs": state()})
print("QUEUE_REPORT " + json.dumps(report, sort_keys=True))
'''


def _run_queue_child(endpoints, steps):
    env = {
        **os.environ,
        "EINVITE_SRC": str(REPO / "src" / "python"),
        "EINVITE_DATA_DIR": os.environ["WEBHOOK_TEST_DATA_DIR"],
        "EINVITE_ALLOW_PRIVATE_WEBHOOKS": "1",
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_BACKGROUND_MEDIA": "0",
        "WEBHOOK_ENDPOINTS": json.dumps(endpoints),
        "WEBHOOK_STEPS": json.dumps(steps),
    }
    completed = subprocess.run([sys.executable, "-c", _QUEUE_CHILD], cwd=str(REPO), env=env,
                               capture_output=True, text=True, timeout=90)
    assert completed.returncode == 0, completed.stderr[-3000:]
    line = [row for row in completed.stdout.splitlines() if row.startswith("QUEUE_REPORT ")]
    assert line, completed.stdout[-3000:]
    return json.loads(line[-1][len("QUEUE_REPORT "):])


@pytest.fixture()
def queue_data(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBHOOK_TEST_DATA_DIR", str(tmp_path))
    return tmp_path


def test_queue_retries_backoff_and_4xx(queue_data, monkeypatch):
    flaky = _Receiver(statuses=(500, 500, 200), path="/flaky")
    rejecting = _Receiver(statuses=(400,), path="/reject")
    always = _Receiver(statuses=(500,), path="/always")
    try:
        endpoints = [
            {"id": "ep-flaky", "url": flaky.url, "secret": "whsec_flaky"},
            {"id": "ep-reject", "url": rejecting.url, "secret": "whsec_reject"},
            {"id": "ep-always", "url": always.url, "secret": "whsec_always"},
        ]
        steps = [
            {"offsetMs": 0},        # flaky #1 (500), reject #1 (400 -> failed), always #1 (500)
            {"offsetMs": 999},      # nothing due yet
            {"offsetMs": 1000},     # flaky #2 (500), always #2 (500)
            {"offsetMs": 2999},     # nothing
            {"offsetMs": 3000},     # flaky #3 (200 -> done), always #3 (500)
            {"offsetMs": 7000},     # always #4 (500)
            {"offsetMs": 15000},    # always #5 (500 -> failed, the last allowed attempt)
            {"offsetMs": 31000},    # nothing left
            {"offsetMs": 63000},
            {"offsetMs": 127000},
        ]
        report = _run_queue_child(endpoints, steps)
        assert report["dispatched"] == 3, report
        assert [step["processed"] for step in report["steps"]] == [3, 0, 2, 0, 2, 1, 1, 0, 0, 0], report

        last = report["steps"][-1]["jobs"]
        assert sorted(job["state"] for job in last) == ["done", "failed", "failed"], last
        assert sorted(job["attempts"] for job in last) == [1, 3, 5], last

        assert len(flaky.requests) == 3, len(flaky.requests)
        assert len(rejecting.requests) == 1, len(rejecting.requests)
        assert len(always.requests) == 5, len(always.requests)
        for request in flaky.requests + rejecting.requests + always.requests:
            assert verify_signature(request["body"], request["signature"],
                                    _secret_for(request, endpoints),
                                    now_ms=int(time.time() * 1000)) is True
    finally:
        flaky.close()
        rejecting.close()
        always.close()
    print("[OK] queue: 1/2/4/8 s retries, 4xx final, 5 attempts max, signed each time", flush=True)


def _secret_for(request, endpoints):
    for endpoint in endpoints:
        if request["path"] == "/flaky" and endpoint["id"] == "ep-flaky":
            return endpoint["secret"]
        if request["path"] == "/reject" and endpoint["id"] == "ep-reject":
            return endpoint["secret"]
        if request["path"] == "/always" and endpoint["id"] == "ep-always":
            return endpoint["secret"]
    raise AssertionError(f"unknown receiver path {request['path']}")
