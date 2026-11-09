"""Per-request SQL statement accounting for the embedded database.

Sprint 6 needed a measured number instead of an opinion: how many SQL
statements does one HTTP request actually run? Counting inside the connection
wrapper is the only place that sees every statement — handlers, auth lookups,
helpers that open their own ``connect()`` block, and audit writes all add up.

Why thread-local: ``ThreadingHTTPServer`` serves one request per thread at a
time and the handler resets the counter in ``parse_request()``. Nothing is
shared between requests, so the hot path needs no lock.

Cost: one function call and one integer increment per statement. The counter is
always maintained; only the ``X-DB-Query-Count`` response header is opt-in via
``EINVITE_DB_QUERY_COUNT=1`` (a diagnostics switch, not a production header).
"""
from __future__ import annotations

import os
import threading

__all__ = ["enabled", "reset", "record", "count", "statements"]

_MAX_STATEMENTS = 200
_MAX_SQL_CHARS = 200
_state = threading.local()


def enabled() -> bool:
    """True when the caller asked for the ``X-DB-Query-Count`` header."""
    return os.environ.get("EINVITE_DB_QUERY_COUNT", "") == "1"


def reset() -> None:
    """Start a fresh count for the current request thread."""
    _state.count = 0
    _state.statements = []


def record(sql) -> None:
    """Count one SQL statement and keep a bounded, whitespace-normalized text."""
    _state.count = getattr(_state, "count", 0) + 1
    log = getattr(_state, "statements", None)
    if log is None:
        log = _state.statements = []
    if len(log) < _MAX_STATEMENTS:
        log.append(" ".join(str(sql).split())[:_MAX_SQL_CHARS])


def count() -> int:
    return getattr(_state, "count", 0)


def statements():
    """The statements recorded for the current request (bounded)."""
    return list(getattr(_state, "statements", []))
