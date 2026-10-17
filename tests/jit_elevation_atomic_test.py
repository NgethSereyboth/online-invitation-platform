from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from ai_agent.jit_elevation import JITElevationManager


class _ReadBarrierConnection:
    def __init__(self, connection: sqlite3.Connection, barrier: threading.Barrier):
        self.connection = connection
        self.barrier = barrier

    def execute(self, statement: str, parameters=()):
        cursor = self.connection.execute(statement, parameters)
        if (
            statement.lstrip().startswith("SELECT id, user_id, tool_id")
            and "WHERE user_id=? AND tool_id=?" in statement
        ):
            self.barrier.wait(timeout=5)
        return cursor



def test_concurrent_evaluations_consume_a_jit_grant_only_once(tmp_path: Path):
    database = tmp_path / "jit.sqlite3"
    select_barrier = threading.Barrier(2)

    @contextmanager
    def connect():
        connection = sqlite3.connect(database, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield _ReadBarrierConnection(connection, select_barrier)
        finally:
            connection.close()

    manager = JITElevationManager(connect)
    request = manager.request_elevation(
        "user-1",
        "message.prepare_send",
        "invite-1",
        "invitation",
        "manual approval for a single send",
        action="send",
        workspace_id="workspace-1",
        invitation_id="invite-1",
        role="owner",
    )
    manager.grant(request["id"], approver_id="approver-1")

    def evaluate_once() -> bool:
        return manager.evaluate(
            "user-1",
            "message.prepare_send",
            resource_id="invite-1",
            resource_type="invitation",
            action="send",
            workspace_id="workspace-1",
            invitation_id="invite-1",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: evaluate_once(), range(2)))

    assert sorted(results) == [False, True]
