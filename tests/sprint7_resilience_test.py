#!/usr/bin/env python3
"""Sprint 7 — resilience: outbound timeouts, circuit breaker, slow DB, limits.

Fault injection is deliberately local and test-only:

* ``_FaultServer`` is an HTTP server whose delay and status are scripted by the
  test. The product code has no chaos switch.
* The slow-database test wraps ``SensitiveConnection.execute`` in-process and
  sleeps before the real statement. No production "delay" environment variable
  exists.
* The worker-recovery test runs the real WSGI app under Waitress with two
  threads and asserts every slow request ends with 504 instead of hanging.

Run with::

    .venv/bin/python -m pytest tests/sprint7_resilience_test.py -q -s
"""
from __future__ import annotations

import base64
import collections
import errno
import http.client
import sqlite3
import http.server
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# ``src/python/server.py`` must win over the repo-root launcher (which parses
# argv and exits); conftest.py uses the same order.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "python"))

from core import resilience  # noqa: E402
from core import db as db_layer  # noqa: E402
import server as app_server  # noqa: E402

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
DOCUMENT = {
    "schemaVersion": 13,
    "eventType": "Wedding",
    "fields": {"names": "S7 Test", "date": "2029-01-01", "time": "16:00", "venue": "Phnom Penh"},
    "objects": {},
    "designPages": [],
    "sectionOrder": ["rsvp"],
    "settings": {"rsvpEnabled": True},
}


class _FaultServer:
    """Local HTTP fixture with scripted delay/status and a request counter."""

    def __init__(self):
        self.delay = 0.0
        self.status = 200
        self.hits = 0
        self._lock = threading.Lock()
        fixture = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                with fixture._lock:
                    fixture.hits += 1
                    delay, status = fixture.delay, fixture.status
                if delay:
                    time.sleep(delay)
                body = json.dumps({"ok": status == 200, "status": status}).encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/hook"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _http(
    url: str,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict | None = None,
    timeout: float = 8.0,
):
    """Return ``(status, headers, parsed JSON)`` and never raise on 4xx/5xx."""
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, response.headers, json.loads(raw or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw or b"{}")
        except ValueError:
            payload = {"raw": raw.decode("utf-8", "replace")[:200]}
        return exc.code, exc.headers, payload


def _json_body(value) -> bytes:
    return json.dumps(value).encode("utf-8")


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    """A real in-process app server with an isolated data directory."""
    monkeypatch.setenv("EINVITE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EINVITE_DEV_AUTH_TOKENS", "1")
    monkeypatch.setenv("EINVITE_REQUIRE_EMAIL_VERIFICATION", "0")
    httpd = app_server.ThreadingHTTPServer(("127.0.0.1", 0), app_server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        yield base
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _bootstrap(base: str):
    """Register a user and create one invitation; return session cookie, CSRF, id."""
    status, headers, payload = _http(
        base + "/api/auth/register", "POST",
        _json_body({"email": "sprint7@example.com", "password": "Sprint7-Passw0rd-2026"}),
        {"Content-Type": "application/json", "Origin": base},
    )
    assert status == 201, (status, payload)
    # Send both the session cookie and the double-submit CSRF cookie.
    cookie = "; ".join(
        value.split(";", 1)[0]
        for value in headers.get_all("Set-Cookie") or []
        if "=" in value and "Max-Age=0" not in value
    )
    assert cookie, headers.get_all("Set-Cookie")
    csrf = payload["csrfToken"]
    status, _, created = _http(
        base + "/api/invitations", "POST",
        _json_body({"slug": "sprint7", "document": DOCUMENT}),
        {"Content-Type": "application/json", "Origin": base,
         "X-CSRF-Token": csrf, "Cookie": cookie},
    )
    assert status == 201, (status, created)
    return cookie, csrf, created["id"]


def test_outbound_timeout_configuration(monkeypatch):
    monkeypatch.setenv("EINVITE_OUTBOUND_CONNECT_TIMEOUT", "1.25")
    monkeypatch.setenv("EINVITE_OUTBOUND_READ_TIMEOUT", "0.75")
    assert resilience.connect_timeout() == 1.25
    assert resilience.read_timeout() == 0.75
    monkeypatch.setenv("EINVITE_OUTBOUND_CONNECT_TIMEOUT", "999")
    monkeypatch.setenv("EINVITE_OUTBOUND_READ_TIMEOUT", "0.01")
    assert resilience.connect_timeout() == 10.0
    assert resilience.read_timeout() == 0.5
    monkeypatch.setenv("EINVITE_OUTBOUND_CONNECT_TIMEOUT", "not-a-number")
    monkeypatch.setenv("EINVITE_OUTBOUND_READ_TIMEOUT", "not-a-number")
    assert resilience.connect_timeout() == 2.0
    assert resilience.read_timeout() == 5.0


def test_read_timeout_aborts_a_silent_peer():
    with _FaultServer() as peer:
        peer.delay = 1.5
        started = time.monotonic()
        with pytest.raises(resilience.OutboundError) as info:
            resilience.post_json(peer.url, {"ping": True}, read_timeout_s=0.25, connect_timeout_s=1.0)
        elapsed = time.monotonic() - started
        assert info.value.kind == "timeout", info.value
        assert elapsed < 1.0, elapsed
        assert peer.hits == 1


def test_circuit_breaker_opens_fails_fast_and_recovers():
    with _FaultServer() as peer:
        breaker = resilience.CircuitBreaker(failures=2, cooldown=0.3)
        peer.status = 503
        for _ in range(2):
            with pytest.raises(resilience.OutboundError):
                resilience.post_json(peer.url, {"x": 1}, breaker_instance=breaker, breaker_key="sprint7")
        hits = peer.hits
        with pytest.raises(resilience.CircuitOpenError) as info:
            resilience.post_json(peer.url, {"x": 1}, breaker_instance=breaker, breaker_key="sprint7")
        assert info.value.kind == "circuit_open"
        assert peer.hits == hits, "the open breaker must not touch the network"
        peer.status = 200
        time.sleep(0.4)
        assert resilience.post_json(peer.url, {"x": 1}, breaker_instance=breaker, breaker_key="sprint7")["ok"] is True
        assert breaker.state("sprint7") == "closed"
        assert peer.hits == hits + 1


def test_cursor_interrupt_maps_to_query_deadline():
    class InterruptedCursor:
        def fetchall(self):
            raise sqlite3.OperationalError("interrupted")

    with pytest.raises(db_layer.QueryDeadlineExceeded):
        db_layer.SensitiveCursor(InterruptedCursor()).fetchall()


def test_outbound_4xx_is_a_failure(monkeypatch):
    with _FaultServer() as peer:
        peer.status = 400
        with pytest.raises(resilience.OutboundError) as info:
            resilience.post_json(peer.url, {"x": 1})
        assert info.value.kind == "client"
        assert info.value.status == 400


def test_messaging_provider_timeout_degrades_to_failed(monkeypatch):
    with _FaultServer() as peer:
        peer.delay = 1.5
        monkeypatch.setattr(app_server, "MESSAGING_WEBHOOK_ENDPOINT", peer.url)
        monkeypatch.setenv("EINVITE_OUTBOUND_READ_TIMEOUT", "0.25")
        started = time.monotonic()
        result = app_server.send_message_provider(
            "sms", "+15550000000", "hello", {"guestName": "S7"}, request_id="req-sprint7"
        )
        elapsed = time.monotonic() - started
        assert result["status"] == "failed", result
        assert "temporarily unavailable" in result["error"]
        assert elapsed < 1.5, elapsed
        assert peer.hits == 1


def test_server_has_no_unbounded_urlopen():
    source = Path(app_server.__file__).read_text(encoding="utf-8")
    assert "urllib.request.urlopen" not in source
    assert source.count("resilience.post_json") >= 4


def test_slow_database_returns_504_and_releases_the_request(live_server, monkeypatch):
    original = db_layer.SensitiveConnection.execute

    def slow_execute(self, sql, params=()):
        time.sleep(0.6)
        return original(self, sql, params)

    with monkeypatch.context() as scoped:
        scoped.setattr(app_server, "DB_QUERY_BUDGET_SECONDS", 0.2)
        scoped.setattr(db_layer.SensitiveConnection, "execute", slow_execute)
        started = time.monotonic()
        status, headers, payload = _http(live_server + "/")
        elapsed = time.monotonic() - started
    assert status == 504, (status, payload)
    assert payload["code"] == "database_timeout", payload
    assert headers.get("X-Request-ID")
    assert elapsed < 3.0, elapsed
    # The next request is not poisoned by the previous deadline.
    status, _, payload = _http(live_server + "/api/health")
    assert status == 200 and payload["ok"] is True


def test_waitress_workers_recover_from_slow_database(live_server, monkeypatch):
    waitress_server = pytest.importorskip("waitress.server")

    app = app_server.create_app()
    wsgi = waitress_server.create_server(
        app, host="127.0.0.1", port=0, threads=2,
        max_request_body_size=app_server.MAX_REQUEST_BODY_BYTES,
        max_request_header_size=16_386,
    )
    def run_waitress():
        # close() shuts the listener down while run() is still in select().
        # The resulting EBADF is teardown noise, not a request failure.
        try:
            wsgi.run()
        except OSError:
            pass

    thread = threading.Thread(target=run_waitress, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{wsgi.effective_port}"
    original = db_layer.SensitiveConnection.execute

    def slow_execute(self, sql, params=()):
        time.sleep(0.7)
        return original(self, sql, params)

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(app_server, "DB_QUERY_BUDGET_SECONDS", 0.25)
            scoped.setattr(db_layer.SensitiveConnection, "execute", slow_execute)
            started = time.monotonic()
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(lambda _: _http(base + "/", timeout=12), range(6)))
            elapsed = time.monotonic() - started
        assert [status for status, _, _ in results] == [504] * 6, results
        assert all(body.get("code") == "database_timeout" for _, _, body in results)
        assert elapsed < 8.0, elapsed
        # Both worker threads were released; health is served again.
        status, _, payload = _http(base + "/api/health")
        assert status == 200 and payload["ok"] is True
    finally:
        wsgi.close()
        thread.join(timeout=8)


def test_transport_body_ceiling_returns_413_before_buffering(live_server):
    parsed = urllib.parse.urlsplit(live_server)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    try:
        connection.putrequest("POST", "/api/invitations/unknown/assets/raw")
        connection.putheader("Content-Length", str(app_server.MAX_REQUEST_BODY_BYTES + 1))
        connection.putheader("Content-Type", "image/png")
        connection.endheaders()
        response = connection.getresponse()
        raw = response.read()
        assert response.status == 413, (response.status, raw[:200])
        payload = json.loads(raw or b"{}")
        assert payload["code"] == "payload_too_large"
        assert payload["limit"] == app_server.MAX_REQUEST_BODY_BYTES
        assert response.getheader("X-Request-ID")
    finally:
        connection.close()


def test_disk_reserve_returns_507_for_a_real_upload(live_server, monkeypatch):
    cookie, csrf, invite_id = _bootstrap(live_server)
    monkeypatch.setattr(app_server, "MIN_FREE_DISK_BYTES", 10**12)
    status, headers, payload = _http(
        live_server + f"/api/invitations/{invite_id}/assets/raw", "POST", PNG_1PX,
        {"Content-Type": "image/png", "X-File-Name": "tiny.png", "Origin": live_server,
         "X-CSRF-Token": csrf, "Cookie": cookie},
    )
    assert status == 507, (status, payload)
    assert payload["code"] == "insufficient_storage", payload
    assert headers.get("X-Request-ID")


def test_disk_helpers_reserve_and_map_enospc(monkeypatch):
    usage = collections.namedtuple("usage", "total used free")
    monkeypatch.setattr(app_server, "MIN_FREE_DISK_BYTES", 1024)
    monkeypatch.setattr(app_server.shutil, "disk_usage", lambda path: usage(4096, 4000, 96))
    with pytest.raises(app_server.InsufficientStorage):
        app_server.ensure_disk_space("/tmp", 0)

    monkeypatch.setattr(app_server.shutil, "disk_usage", lambda path: usage(4096, 0, 4096))
    monkeypatch.setattr(app_server, "UPLOADS", Path("/tmp"))
    original_write = Path.write_bytes

    def full_disk(self, data):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(Path, "write_bytes", full_disk)
    try:
        with pytest.raises(app_server.InsufficientStorage):
            app_server.store_asset_bytes("tiny.png", PNG_1PX, "image/png")
    finally:
        monkeypatch.setattr(Path, "write_bytes", original_write)
