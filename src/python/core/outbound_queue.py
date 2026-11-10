"""Durable retry queue for outbound messages (Sprint 8).

The queue is deliberately small and SQLite-first: a failed Twilio/WhatsApp/
Telegram/channel send is written to ``outbound_retry_queue`` with an
exponential ``next_attempt_at``, then one background thread polls and retries
it.  There is no external broker and no in-memory-only state.

Rows are claimed by a single worker, so the ``pending -> processing``
transition is safe without a distributed lock.  A row that fails three times
becomes ``FAILED`` (the dead-letter state) and is exposed by the admin API.
The queue table is created idempotently on first use; WAL is requested only for
SQLite and a PostgreSQL deployment simply ignores the PRAGMA.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any, Callable, Optional


def _env_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def _env_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


SCHEMA_STATEMENTS = (
    "CREATE TABLE IF NOT EXISTS outbound_retry_queue("
    "id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL DEFAULT '', "
    "channel TEXT NOT NULL, route TEXT NOT NULL DEFAULT 'channel', "
    "recipient TEXT NOT NULL, message_text TEXT NOT NULL DEFAULT '', "
    "metadata_json TEXT NOT NULL DEFAULT '{}', request_id TEXT NOT NULL DEFAULT '', "
    "status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, "
    "max_attempts INTEGER NOT NULL DEFAULT 3, next_attempt_at BIGINT NOT NULL, "
    "last_error TEXT NOT NULL DEFAULT '', error_kind TEXT NOT NULL DEFAULT '', "
    "created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL, "
    "completed_at BIGINT, dead_lettered_at BIGINT)",
    "CREATE INDEX IF NOT EXISTS idx_outbound_retry_due "
    "ON outbound_retry_queue(status,next_attempt_at,created_at)",
    "CREATE INDEX IF NOT EXISTS idx_outbound_retry_failed "
    "ON outbound_retry_queue(status,dead_lettered_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_outbound_retry_invitation "
    "ON outbound_retry_queue(invitation_id,created_at DESC)",
)


def ensure_schema(connect: Callable[[], Any]) -> None:
    """Create the queue table and indexes; enable WAL when the engine supports it."""
    with connect() as db:
        for statement in SCHEMA_STATEMENTS:
            db.execute(statement)
        try:
            # SQLite-only. A PostgreSQL adapter raises on PRAGMA; that is fine.
            db.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass


class OutboundRetryQueue:
    """A bounded, DB-backed retry queue with one polling worker."""

    def __init__(
        self,
        connect: Callable[[], Any],
        sender: Callable[[dict], dict],
        *,
        poll_interval: float = 0.5,
        backoff_seconds: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ):
        self.connect = connect
        self.sender = sender
        self.poll_interval = max(0.05, min(10.0, float(poll_interval)))
        self.backoff_seconds = max(
            0.0,
            min(
                3600.0,
                float(
                    _env_float("EINVITE_OUTBOUND_RETRY_BACKOFF_SECONDS", 5.0, 0.0, 3600.0)
                    if backoff_seconds is None
                    else backoff_seconds
                ),
            ),
        )
        self.max_attempts = max(
            1,
            min(
                10,
                int(
                    _env_int("EINVITE_OUTBOUND_RETRY_MAX_ATTEMPTS", 3, 1, 10)
                    if max_attempts is None
                    else max_attempts
                ),
            ),
        )
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.last_error = ""
        ensure_schema(connect)

    @property
    def running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def start(self) -> "OutboundRetryQueue":
        """Start the polling thread once; repeated calls are harmless."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._worker, name="outbound-retry-1", daemon=True
            )
            self._thread.start()
        return self

    def shutdown(self, timeout: float = 10.0) -> bool:
        """Stop the worker and join it; safe to call more than once."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(max(0.0, float(timeout)))
        return not self.running

    stop = shutdown

    def _backoff(self, attempts: int) -> float:
        """Delay after ``attempts`` failed attempts: base, 2x, 4x, capped."""
        exponent = max(0, min(8, int(attempts) - 1))
        return self.backoff_seconds * (2 ** exponent)

    @staticmethod
    def _now(now_ms: Optional[int]) -> int:
        return int(time.time() * 1000) if now_ms is None else int(now_ms)

    @staticmethod
    def _text(value, limit: int) -> str:
        return str(value or "")[:limit]

    @staticmethod
    def _metadata(metadata: Optional[dict]) -> str:
        return json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":"))

    def _limit(self, max_attempts: Optional[int]) -> int:
        value = self.max_attempts if max_attempts is None else max_attempts
        return max(1, min(10, int(value)))

    def enqueue(
        self,
        channel: str,
        recipient: str,
        message: str,
        *,
        invitation_id: str = "",
        route: str = "channel",
        metadata: Optional[dict] = None,
        request_id: str = "",
        error: str = "",
        error_kind: str = "",
        max_attempts: Optional[int] = None,
        now_ms: Optional[int] = None,
    ) -> str:
        """Persist one retry row and return its id. Starts the worker lazily."""
        now = self._now(now_ms)
        item_id = str(uuid.uuid4())
        limit = self._limit(max_attempts)
        payload = self._metadata(metadata)
        with self.connect() as db:
            db.execute(
                "INSERT INTO outbound_retry_queue("
                "id,invitation_id,channel,route,recipient,message_text,metadata_json,"
                "request_id,status,attempts,max_attempts,next_attempt_at,last_error,"
                "error_kind,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,'pending',0,?,?,?,?,?,?)",
                (
                    item_id,
                    self._text(invitation_id, 160),
                    self._text(channel, 40).lower(),
                    self._text(route, 40) or "channel",
                    self._text(recipient, 500),
                    self._text(message, 5000),
                    payload[:100_000],
                    self._text(request_id, 200),
                    limit,
                    now + int(self._backoff(1) * 1000),
                    self._text(error, 2000),
                    self._text(error_kind, 80),
                    now,
                    now,
                ),
            )
        self.start()
        return item_id

    def claim_due(self, now_ms: Optional[int] = None) -> Optional[dict]:
        """Claim the oldest due row (single worker) or return ``None``."""
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM outbound_retry_queue WHERE status='pending' "
                "AND next_attempt_at<=? ORDER BY next_attempt_at,created_at LIMIT 1",
                (now,),
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            changed = db.execute(
                "UPDATE outbound_retry_queue SET status='processing',"
                "attempts=attempts+1,updated_at=? WHERE id=? AND status='pending'",
                (now, item["id"]),
            ).rowcount
            if not changed:
                return None
            item["attempts"] = int(item.get("attempts") or 0) + 1
            item["status"] = "processing"
            return item

    def mark_sent(self, item_id: str, now_ms: Optional[int] = None) -> None:
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        with self.connect() as db:
            db.execute(
                "UPDATE outbound_retry_queue SET status='sent',completed_at=?,"
                "updated_at=?,last_error='' WHERE id=?",
                (now, now, item_id),
            )

    def _dead_letter(self, db, item_id: str, error: str, error_kind: str, now: int) -> None:
        db.execute(
            "UPDATE outbound_retry_queue SET status='FAILED',last_error=?,"
            "error_kind=?,dead_lettered_at=?,updated_at=? WHERE id=?",
            (error[:2000], error_kind[:80], now, now, item_id),
        )

    def _reschedule(self, db, item_id: str, attempts: int, error: str, error_kind: str, now: int) -> None:
        db.execute(
            "UPDATE outbound_retry_queue SET status='pending',last_error=?,"
            "error_kind=?,next_attempt_at=?,updated_at=? WHERE id=?",
            (error[:2000], error_kind[:80],
             now + int(self._backoff(attempts) * 1000), now, item_id),
        )

    def mark_failed(
        self,
        item_id: str,
        error: str,
        *,
        error_kind: str = "",
        now_ms: Optional[int] = None,
    ) -> None:
        """Schedule another attempt, or dead-letter the row at the limit."""
        now = self._now(now_ms)
        message = str(error or "")[:2000]
        kind = str(error_kind or "")[:80]
        with self.connect() as db:
            row = db.execute(
                "SELECT attempts,max_attempts,status FROM outbound_retry_queue WHERE id=?",
                (item_id,),
            ).fetchone()
            if not row or row["status"] == "sent":
                return
            attempts = int(row["attempts"] or 0)
            maximum = int(row["max_attempts"] or self.max_attempts)
            if attempts >= maximum:
                self._dead_letter(db, item_id, message, kind, now)
            else:
                self._reschedule(db, item_id, attempts, message, kind, now)

    def release(self, item_id: str, now_ms: Optional[int] = None) -> None:
        """Return an in-flight row to pending after a shutdown."""
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        with self.connect() as db:
            db.execute(
                "UPDATE outbound_retry_queue SET status='pending',"
                "attempts=CASE WHEN attempts>0 THEN attempts-1 ELSE 0 END,"
                "updated_at=? WHERE id=? AND status='processing'",
                (now, item_id),
            )

    def list_failed(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return dead-letter rows for the admin endpoint, parsed for JSON."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM outbound_retry_queue WHERE status='FAILED' "
                "ORDER BY dead_lettered_at DESC,created_at DESC LIMIT ? OFFSET ?",
                (max(1, min(200, int(limit))), max(0, int(offset))),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item.get("metadata_json") or "{}")
            except (TypeError, ValueError):
                item["metadata"] = {}
            item.pop("metadata_json", None)
            item.pop("message_text", None)  # do not echo message bodies to the admin list
            items.append(item)
        return items

    def count_failed(self) -> int:
        with self.connect() as db:
            row = db.execute(
                "SELECT COUNT(*) c FROM outbound_retry_queue WHERE status='FAILED'"
            ).fetchone()
        return int(row["c"] if row else 0)

    def _process_item(self, item: dict) -> bool:
        """Send one claimed row; return False when shutdown won the race."""
        if self._stop.is_set():
            self.release(item["id"])
            return False
        result = self.sender(item) or {}
        status = str(result.get("status") or "failed").lower()
        if status in {"sent", "queued", "preview"}:
            self.mark_sent(item["id"])
        else:
            self.mark_failed(
                item["id"],
                str(result.get("error") or "Retry send failed"),
                error_kind=str(result.get("kind") or result.get("errorKind") or ""),
            )
        return True

    def _handle_worker_error(self, exc: Exception, item: Optional[dict]) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        if item:
            try:
                self.release(item["id"])
            except Exception:
                pass
        print(
            json.dumps(
                {"level": "warning", "event": "outbound_retry_worker_failed",
                 "message": self.last_error[:300]},
                ensure_ascii=False,
            ),
            flush=True,
        )
        self._stop.wait(self.poll_interval)

    def _worker(self) -> None:
        while not self._stop.is_set():
            item = None
            try:
                item = self.claim_due()
                if not item:
                    self._stop.wait(self.poll_interval)
                    continue
                if not self._process_item(item):
                    break
            except Exception as exc:  # never let the worker die silently
                self._handle_worker_error(exc, item)
