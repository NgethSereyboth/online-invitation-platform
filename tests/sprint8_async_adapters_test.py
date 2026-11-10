#!/usr/bin/env python3
"""Sprint 8 — worker lifecycle, consolidated adapters and durable retries.

The tests use a temporary SQLite file and a scripted sender. No external
broker, provider, or network call is involved except the local HTTP fixture in
the circuit-open test, which is never reached because the breaker is already
open.

Run with::

    .venv/bin/python -m pytest tests/sprint8_async_adapters_test.py -q -s
"""
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# src/python must win over the repo-root launcher (which parses argv).
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "python"))

from core.outbound_queue import OutboundRetryQueue  # noqa: E402
from platform_v32.jobs import JobQueue  # noqa: E402


def _sqlite_connect(path: Path):
    @contextlib.contextmanager
    def connect():
        connection = sqlite3.connect(str(path), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    return connect


def _make_job_db(path: Path):
    with _sqlite_connect(path)() as db:
        db.execute(
            "CREATE TABLE platform_jobs("
            "id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL DEFAULT '',"
            "owner_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',"
            "progress REAL NOT NULL DEFAULT 0,payload_json TEXT NOT NULL DEFAULT '{}',"
            "result_json TEXT NOT NULL DEFAULT '{}',idempotency_key TEXT NOT NULL DEFAULT '',"
            "retry_count INTEGER NOT NULL DEFAULT 0,max_retries INTEGER NOT NULL DEFAULT 3,"
            "cancellation_requested INTEGER NOT NULL DEFAULT 0,error_text TEXT NOT NULL DEFAULT '',"
            "created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,started_at INTEGER,completed_at INTEGER)"
        )


def test_job_queue_shutdown_joins_workers_before_db_removal(tmp_path):
    db_path = tmp_path / "jobs.sqlite"
    _make_job_db(db_path)
    done = threading.Event()
    excepthook_errors = []
    old_hook = threading.excepthook
    threading.excepthook = lambda args: excepthook_errors.append(args)

    queue = JobQueue(_sqlite_connect(db_path), workers=2, poll_interval=0.05)
    queue.register("probe", lambda payload, progress, cancelled: done.set() or {"ok": True})
    try:
        queue.submit("workspace-1", "owner-1", "probe", {"value": 1})
        assert done.wait(3), "job did not run"
        assert queue.shutdown(timeout=3) is True
        names = [thread.name for thread in threading.enumerate()]
        assert not any(name.startswith("einvite-worker-") for name in names), names
        # The old bug appeared here: a worker was still polling when the
        # temporary directory disappeared.
        db_path.unlink()
        time.sleep(0.25)
        assert excepthook_errors == [], excepthook_errors
    finally:
        threading.excepthook = old_hook
        queue.shutdown(timeout=3)


def _wait_for(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_retry_queue_uses_backoff_and_dead_letters_after_three_failures(tmp_path):
    calls = []

    def sender(row):
        calls.append(int(row["attempts"]))
        return {"status": "failed", "error": "HTTP 503", "kind": "server"}

    queue = OutboundRetryQueue(
        _sqlite_connect(tmp_path / "retry.sqlite"),
        sender,
        poll_interval=0.02,
        backoff_seconds=0,
        max_attempts=3,
    )
    try:
        queue.enqueue("sms", "+15551234567", "hello", invitation_id="inv-1",
                      request_id="req-1", error="HTTP 503", error_kind="server")
        assert _wait_for(lambda: queue.count_failed() == 1), queue.list_failed()
        assert calls == [1, 2, 3], calls
        failed = queue.list_failed()
        assert failed and failed[0]["status"] == "FAILED"
        assert failed[0]["attempts"] == 3 and failed[0]["max_attempts"] == 3
        assert failed[0]["request_id"] == "req-1"
        assert failed[0]["metadata"] == {}
    finally:
        assert queue.shutdown(timeout=3) is True


def test_retry_queue_succeeds_on_second_attempt(tmp_path):
    calls = []

    def sender(row):
        calls.append(int(row["attempts"]))
        if len(calls) == 1:
            return {"status": "failed", "error": "timeout", "kind": "timeout"}
        return {"status": "sent", "providerId": "retry-ok"}

    queue = OutboundRetryQueue(
        _sqlite_connect(tmp_path / "retry-ok.sqlite"),
        sender,
        poll_interval=0.02,
        backoff_seconds=0,
        max_attempts=3,
    )
    try:
        queue.enqueue("telegram", "12345", "hello", metadata={"invitationId": "inv-2"})
        assert _wait_for(lambda: calls == [1, 2]), calls
        time.sleep(0.05)
        assert queue.count_failed() == 0
    finally:
        assert queue.shutdown(timeout=3) is True


def test_circuit_open_queues_without_network(monkeypatch):
    import server
    from core import resilience

    class FakeQueue:
        def __init__(self):
            self.items = []

        def enqueue(self, *args, **kwargs):
            self.items.append((args, kwargs))
            return "retry-test-id"

    fake = FakeQueue()
    monkeypatch.setattr(server, "get_outbound_queue", lambda start=True: fake)
    monkeypatch.setattr(server, "MESSAGING_WEBHOOK_ENDPOINT", "http://127.0.0.1:9/hook")
    monkeypatch.setattr(server, "MESSAGING_WEBHOOK_SECRET", "")
    breaker = resilience.breaker()
    breaker.reset()
    for _ in range(breaker.failures):
        breaker.record_failure("127.0.0.1:9")
    try:
        result = server.send_message_provider(
            "sms", "+15551234567", "hello", {"invitationId": "inv-3"},
            request_id="request-circuit-open",
        )
        assert result["status"] == "queued", result
        assert result["queuedForRetry"] is True
        assert fake.items and fake.items[0][1]["route"] == "messaging"
        assert fake.items[0][1]["request_id"] == "request-circuit-open"
    finally:
        breaker.reset()


def test_admin_failed_outbound_route_dispatches(monkeypatch):
    import server

    calls = []

    class FakeQueue:
        def list_failed(self, limit, offset):
            return [{"id": "retry-1", "status": "FAILED"}]

        def count_failed(self):
            return 1

    handler = object.__new__(server.Handler)
    handler.path = "/api/admin/failed-outbound?limit=1&offset=0"
    handler._admin_gate = lambda *args: {"id": "admin-1"}
    handler.json = lambda status, payload: calls.append((status, payload))
    monkeypatch.setattr(server, "get_outbound_queue", lambda start=True: FakeQueue())

    assert handler._admin_get_dispatch("/api/admin/failed-outbound") is True
    assert calls == [(200, {"items": [{"id": "retry-1", "status": "FAILED"}],
                            "count": 1, "limit": 1, "offset": 0})]


def test_admin_failed_outbound_exposes_dead_letters(tmp_path):
    queue = OutboundRetryQueue(
        _sqlite_connect(tmp_path / "admin-failed.sqlite"),
        lambda row: {"status": "failed", "error": "HTTP 503", "kind": "server"},
        poll_interval=0.02,
        backoff_seconds=0,
        max_attempts=1,
    )
    try:
        queue.enqueue("whatsapp", "+15550001111", "hello", invitation_id="inv-4")
        assert _wait_for(lambda: queue.count_failed() == 1)
        items = queue.list_failed()
        assert len(items) == 1
        assert "message_text" not in items[0]
        assert items[0]["channel"] == "whatsapp"
        assert items[0]["status"] == "FAILED"
        assert json.dumps(items[0])  # JSON-serializable for the admin API
    finally:
        assert queue.shutdown(timeout=3) is True
