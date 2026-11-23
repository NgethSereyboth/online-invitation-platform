#!/usr/bin/env python3
"""S12b platform-runner parity: Python's JobQueue._run vs the Node runner.

One PostgreSQL serves both backends. Each scenario seeds one `platform_jobs`
row, runs the Python side through `JobQueue._run()` in a fresh process (real
production code at a real clock), then seeds the same row again and runs the
Node runner at a fixed clock, and compares the resulting row: status, progress,
result JSON, error text, retry counters, cancellation flag and whether the
start/finish timestamps were set.

Two behaviours are intentional differences rather than parity, and are asserted
as such: an expired lease is recovered only by Node (Python's queue has no
recovery path), and Node never claims the kind it does not implement.

Usage:
  .venv/bin/python tools/platform-runner-parity.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
NODE = os.environ.get("NODE_BIN", "node")
T0 = int(time.time() * 1000)


def run_json(command: list[str], env: dict[str, str], timeout: float = 120.0) -> dict:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed:\n{result.stderr[-4000:]}\n{result.stdout[-2000:]}")
    for line in reversed(result.stdout.splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"no JSON output from {' '.join(command)}:\n{result.stdout[-4000:]}")


def db_execute(database_url: str, sql: str, params=()) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)


def reset(database_url: str) -> None:
    db_execute(database_url, "DELETE FROM platform_jobs WHERE id LIKE %s", ("pj-%",))


def seed_job(
    database_url: str,
    job_id: str,
    payload: dict,
    *,
    kind: str = "media-ingest",
    status: str = "queued",
    retry_count: int = 0,
    max_retries: int = 3,
    cancellation_requested: int = 0,
    lock_owner: str = "",
    lease_expires_at: int | None = None,
    progress: float = 0.0,
    created_at: int = T0,
    started_at: int | None = None,
    completed_at: int | None = None,
) -> None:
    db_execute(database_url, "DELETE FROM platform_jobs WHERE id=%s", (job_id,))
    db_execute(
        database_url,
        "INSERT INTO platform_jobs(id,workspace_id,invitation_id,owner_id,kind,status,progress,"
        "payload_json,result_json,idempotency_key,retry_count,max_retries,cancellation_requested,"
        "error_text,created_at,updated_at,started_at,completed_at,lock_owner,lease_expires_at) "
        "VALUES(%s,'workspace-1','','owner-1',%s,%s,%s,%s,'{}','',%s,%s,%s,'',%s,%s,%s,%s,%s,%s)",
        (
            job_id,
            kind,
            status,
            progress,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            retry_count,
            max_retries,
            cancellation_requested,
            created_at,
            created_at,
            started_at,
            completed_at,
            lock_owner,
            lease_expires_at,
        ),
    )


def observe(database_url: str, job_id: str) -> dict:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status,progress,retry_count,max_retries,cancellation_requested,result_json,"
                "error_text,lock_owner,lease_expires_at,started_at,completed_at "
                "FROM platform_jobs WHERE id=%s",
                (job_id,),
            )
            row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"missing platform job {job_id}")
    try:
        result = json.loads(row[5] or "{}")
    except json.JSONDecodeError:
        result = {"unparsable": row[5]}
    return {
        "status": row[0],
        "progress": float(row[1] or 0),
        "retry_count": row[2],
        "max_retries": row[3],
        "cancellation_requested": int(row[4] or 0),
        "result": result,
        "result_json": row[5],
        "error_text": row[6],
        "lock_owner": row[7],
        "lease_expires_at_is_null": row[8] is None,
        "started_at_set": row[9] is not None,
        "completed_at_set": row[10] is not None,
    }


class Harness:
    def __init__(self, database_url: str, data_dir: str, env: dict[str, str]) -> None:
        self.database_url = database_url
        self.data_dir = data_dir
        self.env = env
        self.total = 0
        self.failures = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}{'' if ok else ' — ' + detail}")
        if not ok:
            self.failures += 1

    def prepare_schema(self) -> None:
        run_json(
            [
                PY,
                str(ROOT / "tools/platform-runner-python-agent.py"),
                "--database-url",
                self.database_url,
                "--data-dir",
                self.data_dir,
            ],
            self.env,
        )

    def run_python(self, job_id: str) -> dict:
        return run_json(
            [
                PY,
                str(ROOT / "tools/platform-runner-python-agent.py"),
                "--database-url",
                self.database_url,
                "--data-dir",
                self.data_dir,
                "--job-id",
                job_id,
            ],
            self.env,
        )

    def run_node(self, now_ms: int) -> dict:
        return run_json(
            [
                NODE,
                str(ROOT / "tools/platform-runner-agent.mjs"),
                "--database-url",
                self.database_url,
                "--now-ms",
                str(now_ms),
                "--limit",
                "1",
            ],
            self.env,
        )

    def scenario(self, name: str, payload: dict, **options) -> tuple[dict, dict]:
        python_id = f"pj-{name}-python"
        node_id = f"pj-{name}-node"
        reset(self.database_url)
        seed_job(self.database_url, python_id, payload, **options)
        self.run_python(python_id)
        python_state = observe(self.database_url, python_id)

        reset(self.database_url)
        seed_job(self.database_url, node_id, payload, **options)
        self.run_node(T0)
        node_state = observe(self.database_url, node_id)

        self.check(
            f"{name} is identical",
            python_state == node_state,
            json.dumps({"python": python_state, "node": node_state}, sort_keys=True)[:1800],
        )
        return python_state, node_state

    def run(self) -> int:
        self.scenario("media-ingest-success", {"assetId": "asset-1"})
        self.scenario("media-ingest-empty-payload", {})
        self.scenario("media-ingest-null-asset", {"assetId": None})
        self.scenario("media-ingest-unicode-asset", {"assetId": "asset-café-1"})
        self.scenario(
            "media-ingest-live-lease",
            {"assetId": "asset-1"},
            status="running",
            lock_owner="other-worker",
            lease_expires_at=T0 + 600_000,
            started_at=T0 - 1_000,
        )
        self.scenario(
            "media-ingest-cancelled",
            {"assetId": "asset-1"},
            status="cancelled",
            cancellation_requested=1,
        )

        # Python's platform queue has no recovery sweep, so a row left running by
        # a dead owner stays there; Node's lease is the recovery path (P7 row 8).
        reset(self.database_url)
        seed_job(
            self.database_url,
            "pj-expired-python",
            {"assetId": "asset-1"},
            status="running",
            lock_owner="dead-worker",
            lease_expires_at=T0 - 1_000,
            started_at=T0 - 5_000,
        )
        self.run_python("pj-expired-python")
        python_state = observe(self.database_url, "pj-expired-python")
        self.check(
            "python leaves an expired lease running",
            python_state["status"] == "running" and not python_state["completed_at_set"],
            json.dumps(python_state, sort_keys=True)[:1200],
        )
        reset(self.database_url)
        seed_job(
            self.database_url,
            "pj-expired-node",
            {"assetId": "asset-1"},
            status="running",
            lock_owner="dead-worker",
            lease_expires_at=T0 - 1_000,
            started_at=T0 - 5_000,
        )
        self.run_node(T0)
        node_state = observe(self.database_url, "pj-expired-node")
        self.check(
            "node recovers an expired lease and completes it",
            node_state["status"] == "completed"
            and node_state["result"] == {"status": "provider-hook-ready", "assetId": "asset-1"}
            and node_state["lock_owner"] == "",
            json.dumps(node_state, sort_keys=True)[:1200],
        )

        # The kinds Node does not implement must stay queued for Python.
        reset(self.database_url)
        seed_job(self.database_url, "pj-python-kind", {}, kind="workspace-backup")
        result = self.run_node(T0)
        python_kind = observe(self.database_url, "pj-python-kind")
        self.check(
            "node claims none of python's platform kinds",
            result["processed"] == 0 and python_kind["status"] == "queued",
            json.dumps({"processed": result["processed"], "row": python_kind}, sort_keys=True)[:1200],
        )
        print(f"\nPLATFORM RUNNER PARITY {self.total - self.failures}/{self.total} identical")
        return 0 if self.failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    data_dir = tempfile.mkdtemp(prefix="einvite-platform-parity-")
    env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "EINVITE_FIELD_ENCRYPTION": "0",
        "EINVITE_OBJECT_STORAGE_BUCKET": "",
        "EINVITE_WORKER_CONCURRENCY": "0",
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    try:
        harness = Harness(args.database_url, data_dir, env)
        harness.prepare_schema()
        reset(args.database_url)
        return harness.run()
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
