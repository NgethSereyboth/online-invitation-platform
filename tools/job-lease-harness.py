#!/usr/bin/env python3
"""S12b job lease harness.

One disposable PostgreSQL serves the real Python claim
(server.claim_background_job) and the new Node claim (lib/jobs.mjs). The
harness proves:

  * concurrent Python and Node workers claim every queued job exactly once;
  * a live Node lease cannot be claimed or released by another worker;
  * an expired Node lease is recovered with attempts incremented;
  * a heartbeat extends the lease past its original expiry;
  * a Python-owned running row is not stolen before Python's 30-minute sweep;
  * queued rows with a stale owner are still claimable, and kind filters hold.

Usage:
  .venv/bin/python tools/job-lease-harness.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
NODE = os.environ.get("NODE_BIN", "node")
KIND = "harness.lease"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_health(port: int, process: subprocess.Popen, log: Path, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early:\n{log.read_text()[-4000:]}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError(f"server did not become healthy:\n{log.read_text()[-4000:]}")


def stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def run_json(command: list[str], env: dict[str, str], timeout: float = 120.0) -> dict:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed:\n{result.stderr[-4000:]}\n{result.stdout[-2000:]}")
    for line in reversed(result.stdout.splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"no JSON output from {' '.join(command)}:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}")


def db_execute(database_url: str, sql: str, params=()) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)


def db_row(database_url: str, job_id: str) -> dict:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,state,lock_owner,attempts,available_at,locked_at,lease_expires_at,last_error "
                "FROM background_jobs WHERE id=%s",
                (job_id,),
            )
            row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"missing job {job_id}")
    keys = ("id", "state", "lock_owner", "attempts", "available_at", "locked_at", "lease_expires_at", "last_error")
    return dict(zip(keys, row))


def seed_job(database_url: str, job_id: str, *, kind: str = KIND, payload: str = '{"probe":1}', state: str = "queued",
             attempts: int = 0, available_at: int | None = None, locked_at: int | None = None,
             lock_owner: str = "", lease_expires_at: int | None = None) -> None:
    now = int(time.time() * 1000)
    db_execute(database_url, "DELETE FROM background_jobs WHERE id=%s", (job_id,))
    db_execute(
        database_url,
        "INSERT INTO background_jobs(id,kind,payload_json,state,attempts,available_at,locked_at,last_error,"
        "created_at,updated_at,lock_owner,lease_expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,'',%s,%s,%s,%s)",
        (
            job_id,
            kind,
            payload,
            state,
            attempts,
            available_at if available_at is not None else now - 1000,
            locked_at,
            now,
            now,
            lock_owner,
            lease_expires_at,
        ),
    )


def seed_platform_job(database_url: str, job_id: str, *, kind: str = KIND, state: str = "queued",
                      retry_count: int = 0, updated_at: int | None = None, lock_owner: str = "",
                      lease_expires_at: int | None = None, cancellation: int = 0) -> None:
    now = int(time.time() * 1000)
    db_execute(database_url, "DELETE FROM platform_jobs WHERE id=%s", (job_id,))
    db_execute(
        database_url,
        "INSERT INTO platform_jobs(id,workspace_id,invitation_id,owner_id,kind,status,progress,payload_json,"
        "result_json,idempotency_key,retry_count,max_retries,cancellation_requested,error_text,created_at,"
        "updated_at,started_at,completed_at,lock_owner,lease_expires_at) "
        "VALUES(%s,%s,'',%s,%s,%s,0,%s,'{}','',%s,3,%s,'',%s,%s,NULL,NULL,%s,%s)",
        (
            job_id,
            "harness-ws",
            "harness-owner",
            kind,
            state,
            '{"probe":1}',
            retry_count,
            cancellation,
            now,
            updated_at if updated_at is not None else now,
            lock_owner,
            lease_expires_at,
        ),
    )


def platform_row(database_url: str, job_id: str) -> dict:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,status,lock_owner,retry_count,updated_at,lease_expires_at,result_json "
                "FROM platform_jobs WHERE id=%s",
                (job_id,),
            )
            row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"missing platform job {job_id}")
    keys = ("id", "status", "lock_owner", "retry_count", "updated_at", "lease_expires_at", "result_json")
    return dict(zip(keys, row))


def reset(database_url: str) -> None:
    db_execute(
        database_url,
        "DELETE FROM background_jobs WHERE kind LIKE %s OR id LIKE %s",
        ("harness.%", "lease-%"),
    )


class Harness:
    def __init__(self, database_url: str, base_env: dict[str, str], data_dir: str) -> None:
        self.database_url = database_url
        self.env = base_env
        self.data_dir = data_dir
        self.total = 0
        self.failures = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}{'' if ok else ' — ' + detail}")
        if not ok:
            self.failures += 1

    def node(self, mode: str, worker: str, **options) -> dict:
        command = [NODE, str(ROOT / "tools/job-lease-agent.mjs"), "--database-url", self.database_url,
                   "--worker", worker, "--mode", mode, "--kind", KIND]
        for key, value in options.items():
            command.extend([f"--{key.replace('_', '-')}", str(value)])
        return run_json(command, self.env)

    def python_claim(self, worker: str) -> dict:
        return run_json(
            [PY, str(ROOT / "tools/job-lease-python-agent.py"), "--database-url", self.database_url,
             "--data-dir", self.data_dir, "--worker", worker, "--mode", "claim", "--kind", KIND],
            self.env,
        )

    def python_platform_claim(self, worker: str) -> dict:
        return run_json(
            [PY, str(ROOT / "tools/job-lease-python-agent.py"), "--database-url", self.database_url,
             "--data-dir", self.data_dir, "--worker", worker, "--mode", "platform-claim", "--kind", KIND],
            self.env,
        )

    def drain_race(self) -> None:
        reset(self.database_url)
        expected = [f"lease-race-{index}" for index in range(18)]
        for job_id in expected:
            seed_job(self.database_url, job_id)

        start_at = time.time() + 4.0
        commands = []
        for index in range(2):
            commands.append(
                [PY, str(ROOT / "tools/job-lease-python-agent.py"), "--database-url", self.database_url,
                 "--data-dir", self.data_dir, "--worker", f"python-{index}", "--mode", "drain", "--kind", KIND,
                 "--start-at", str(start_at)]
            )
        for index in range(2):
            commands.append(
                [NODE, str(ROOT / "tools/job-lease-agent.mjs"), "--database-url", self.database_url,
                 "--worker", f"node-{index}", "--mode", "drain", "--kind", KIND, "--start-at", str(int(start_at * 1000))]
            )
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                     for command in commands]
        results = []
        for process, command in zip(processes, commands):
            stdout, stderr = process.communicate(timeout=120)
            if process.returncode != 0:
                raise RuntimeError(f"agent failed: {' '.join(command)}\n{stderr[-3000:]}\n{stdout[-1000:]}")
            lines = [line for line in stdout.splitlines() if line.strip()]
            results.append(json.loads(lines[-1]))

        claims = [claim for result in results for claim in result["claims"]]
        claimed_ids = [claim["id"] for claim in claims]
        self.check("4 concurrent Python/Node workers claim all 18 jobs",
                   len(claims) == len(expected), f"claimed {len(claims)}")
        self.check("every job claimed exactly once", sorted(claimed_ids) == sorted(expected),
                   f"duplicates={len(claimed_ids) - len(set(claimed_ids))}")
        self.check("no duplicate claim", len(claimed_ids) == len(set(claimed_ids)), str(claimed_ids))
        # Python returns the pre-update SELECT row, so read attempts from the table.
        attempts = {claim["id"]: db_row(self.database_url, claim["id"])["attempts"] for claim in claims}
        self.check("every claim is a first attempt", all(count == 1 for count in attempts.values()), str(attempts))
        self.check("the first job is done after the drain", db_row(self.database_url, expected[0])["state"] == "done")
        remaining = 0
        with psycopg.connect(self.database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM background_jobs WHERE kind=%s AND state IN ('queued','running')", (KIND,))
                remaining = cursor.fetchone()[0]
        self.check("no queued or running harness job remains", remaining == 0, f"{remaining} remain")

    def live_lease(self) -> None:
        job_id = "lease-live"
        seed_job(self.database_url, job_id)
        held = self.node("claim", "node-a", lease_ms=60000)
        self.check("node-a claims the live-lease job", (held.get("job") or {}).get("id") == job_id, str(held))
        self.check("the claimed payload is parsed", (held.get("job") or {}).get("payload") == {"probe": 1}, str(held))
        rival = self.node("claim", "node-b", lease_ms=60000)
        self.check("node-b cannot claim a live lease", rival.get("job") is None, str(rival))
        self.check("another worker cannot renew the lease", self.node("renew", "node-b", job_id=job_id, lease_ms=5000)["ok"] is False)
        self.check("another worker cannot release the job", self.node("release", "node-b", job_id=job_id)["ok"] is False)
        row = db_row(self.database_url, job_id)
        self.check("the live lease still belongs to node-a", row["state"] == "running" and row["lock_owner"] == "node-a", str(row))
        self.check("the owner releases the job", self.node("release", "node-a", job_id=job_id)["ok"] is True)
        row = db_row(self.database_url, job_id)
        self.check("release clears owner and lease", row["state"] == "done" and row["lock_owner"] == "" and row["lease_expires_at"] is None, str(row))

    def expired_lease(self) -> None:
        job_id = "lease-expired"
        seed_job(self.database_url, job_id)
        first = self.node("claim", "node-a", lease_ms=300)
        self.check("node-a claims the short lease", (first.get("job") or {}).get("id") == job_id, str(first))
        time.sleep(0.7)
        second = self.node("claim", "node-b", lease_ms=60000)
        job = second.get("job") or {}
        self.check("an expired lease is recovered by node-b", job.get("id") == job_id, str(second))
        self.check("recovery increments attempts", job.get("attempts") == 2, str(job))
        row = db_row(self.database_url, job_id)
        self.check("the recovered lease is owned by node-b", row["lock_owner"] == "node-b" and row["state"] == "running", str(row))
        self.check("the new owner releases the recovered job", self.node("release", "node-b", job_id=job_id)["ok"] is True)

    def heartbeat(self) -> None:
        job_id = "lease-heartbeat"
        seed_job(self.database_url, job_id)
        held = self.node("hold", "node-a", lease_ms=400, hold_ms=600, renew_ms=4000, job_id=job_id)
        self.check("node-a claims and renews before expiry", held.get("renew") is True, str(held))
        time.sleep(0.7)
        rival = self.node("claim", "node-b", lease_ms=60000)
        self.check("a renewed lease is not stolen after the original expiry", rival.get("job") is None, str(rival))
        self.check("the heartbeat owner still holds the row",
                   db_row(self.database_url, job_id)["lock_owner"] == "node-a", str(db_row(self.database_url, job_id)))
        self.check("the heartbeat owner releases the row", self.node("release", "node-a", job_id=job_id)["ok"] is True)

    def python_owned(self) -> None:
        job_id = "lease-python-owned"
        now = int(time.time() * 1000)
        seed_job(self.database_url, job_id, state="running", attempts=1, locked_at=now, lock_owner="")
        rival = self.node("claim", "node-a", lease_ms=60000)
        self.check("Node will not steal a fresh Python-owned running row", rival.get("job") is None, str(rival))
        db_execute(self.database_url, "UPDATE background_jobs SET locked_at=%s WHERE id=%s", (now - 31 * 60 * 1000, job_id))
        recovered = self.node("claim", "node-a", lease_ms=60000)
        self.check("Node recovers a Python row after its 30-minute sweep", (recovered.get("job") or {}).get("id") == job_id, str(recovered))
        self.check("legacy recovery increments attempts", (recovered.get("job") or {}).get("attempts") == 2, str(recovered))
        self.node("release", "node-a", job_id=job_id)

    def stale_owner_and_kind(self) -> None:
        job_id = "lease-stale-owner"
        now = int(time.time() * 1000)
        seed_job(self.database_url, job_id, lock_owner="dead-worker", lease_expires_at=now - 1000)
        claimed = self.node("claim", "node-a", lease_ms=60000)
        self.check("a queued row with a stale owner is claimable", (claimed.get("job") or {}).get("id") == job_id, str(claimed))
        self.node("release", "node-a", job_id=job_id)

        seed_job(self.database_url, "lease-other-kind", kind="harness.other")
        ignored = self.node("claim", "node-a", lease_ms=60000)
        self.check("the kind filter keeps other jobs untouched", ignored.get("job") is None, str(ignored))

    def platform_race(self) -> None:
        expected = [f"platform-race-{index}" for index in range(18)]
        for job_id in expected:
            seed_platform_job(self.database_url, job_id)

        start_at = time.time() + 4.0
        commands = []
        for index in range(2):
            commands.append(
                [PY, str(ROOT / "tools/job-lease-python-agent.py"), "--database-url", self.database_url,
                 "--data-dir", self.data_dir, "--worker", f"python-{index}", "--mode", "platform-drain",
                 "--kind", KIND, "--start-at", str(start_at)]
            )
        for index in range(2):
            commands.append(
                [NODE, str(ROOT / "tools/job-lease-agent.mjs"), "--database-url", self.database_url,
                 "--worker", f"node-{index}", "--mode", "platform-drain", "--kind", KIND,
                 "--start-at", str(int(start_at * 1000))]
            )
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                     for command in commands]
        results = []
        for process, command in zip(processes, commands):
            stdout, stderr = process.communicate(timeout=120)
            if process.returncode != 0:
                raise RuntimeError(f"agent failed: {' '.join(command)}\n{stderr[-3000:]}\n{stdout[-1000:]}")
            lines = [line for line in stdout.splitlines() if line.strip()]
            results.append(json.loads(lines[-1]))

        claimed_ids = [claim["id"] for result in results for claim in result["claims"]]
        self.check("2 Python + 2 Node workers claim all 18 platform jobs",
                   len(claimed_ids) == len(expected), f"claimed {len(claimed_ids)}")
        self.check("every platform job claimed exactly once", sorted(claimed_ids) == sorted(expected),
                   f"duplicates={len(claimed_ids) - len(set(claimed_ids))}")
        self.check("no duplicate platform claim", len(claimed_ids) == len(set(claimed_ids)), str(claimed_ids))
        with psycopg.connect(self.database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM platform_jobs WHERE id LIKE 'platform-race-%%' AND status='completed'")
                completed = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM platform_jobs WHERE id LIKE 'platform-race-%%' AND retry_count=0")
                untouched = cursor.fetchone()[0]
        self.check("every platform job completed once", completed == 18, f"{completed} completed")
        self.check("a claim does not count as a retry", untouched == 18, f"{untouched} with retry_count 0")

    def platform_live_lease(self) -> None:
        job_id = "platform-lease-live"
        seed_platform_job(self.database_url, job_id)
        held = self.node("platform-claim", "node-a", lease_ms=60000)
        self.check("node-a claims the platform job", (held.get("job") or {}).get("id") == job_id, str(held))
        rival = self.node("platform-claim", "node-b", lease_ms=60000)
        self.check("a live platform lease is not claimable", rival.get("job") is None, str(rival))
        self.check("another worker cannot renew a platform lease",
                   self.node("platform-renew", "node-b", job_id=job_id, lease_ms=5000)["ok"] is False)
        self.check("another worker cannot release a platform job",
                   self.node("platform-release", "node-b", job_id=job_id, state="completed")["ok"] is False)
        row = platform_row(self.database_url, job_id)
        self.check("the platform lease still belongs to node-a",
                   row["status"] == "running" and row["lock_owner"] == "node-a", str(row))
        self.check("the owner completes the platform job",
                   self.node("platform-release", "node-a", job_id=job_id, state="completed")["ok"] is True)
        row = platform_row(self.database_url, job_id)
        self.check("platform completion clears the lease",
                   row["status"] == "completed" and row["lock_owner"] == "" and row["lease_expires_at"] is None, str(row))

    def platform_expired_lease(self) -> None:
        job_id = "platform-lease-expired"
        seed_platform_job(self.database_url, job_id)
        self.check("node-a claims the short platform lease",
                   (self.node("platform-claim", "node-a", lease_ms=300).get("job") or {}).get("id") == job_id)
        time.sleep(0.7)
        second = self.node("platform-claim", "node-b", lease_ms=60000)
        self.check("an expired platform lease is recovered", (second.get("job") or {}).get("id") == job_id, str(second))
        row = platform_row(self.database_url, job_id)
        self.check("the recovered platform lease is owned by node-b",
                   row["lock_owner"] == "node-b" and row["status"] == "running", str(row))
        self.node("platform-release", "node-b", job_id=job_id, state="completed")

    def platform_python_owned(self) -> None:
        job_id = "platform-lease-python"
        now = int(time.time() * 1000)
        seed_platform_job(self.database_url, job_id, state="running", updated_at=now, lock_owner="")
        rival = self.node("platform-claim", "node-a", lease_ms=60000)
        self.check("Node will not steal a fresh Python platform row", rival.get("job") is None, str(rival))
        db_execute(self.database_url, "UPDATE platform_jobs SET updated_at=%s WHERE id=%s",
                   (now - 31 * 60 * 1000, job_id))
        recovered = self.node("platform-claim", "node-a", lease_ms=60000)
        self.check("Node recovers a Python platform row after 31 minutes",
                   (recovered.get("job") or {}).get("id") == job_id, str(recovered))
        self.node("platform-release", "node-a", job_id=job_id, state="completed")

    def platform_python_cannot_steal(self) -> None:
        job_id = "platform-lease-node-held"
        seed_platform_job(self.database_url, job_id)
        held = self.node("platform-claim", "node-a", lease_ms=60000)
        self.check("node-a holds the platform job for the Python probe",
                   (held.get("job") or {}).get("id") == job_id, str(held))
        rival = self.python_platform_claim("python-rival")
        self.check("Python's queued-only platform claim does not take a running Node job",
                   rival.get("job") is None, str(rival))
        self.node("platform-release", "node-a", job_id=job_id, state="completed")

    def python_cannot_steal(self) -> None:
        job_id = "lease-node-held"
        seed_job(self.database_url, job_id)
        held = self.node("claim", "node-a", lease_ms=60000)
        self.check("node-a holds a job for the Python probe", (held.get("job") or {}).get("id") == job_id, str(held))
        rival = self.python_claim("python-rival")
        self.check("Python's queued-only claim does not take a running Node job", rival.get("job") is None, str(rival))
        self.node("release", "node-a", job_id=job_id)

    def run(self) -> int:
        # Apply Node's lease-column migration on an empty queue, before any
        # claimer can hold a row lock that its ALTER would wait for.
        self.node("claim", "preflight")
        self.node("platform-claim", "preflight")
        self.drain_race()
        self.platform_race()
        self.platform_live_lease()
        self.platform_expired_lease()
        self.platform_python_owned()
        self.platform_python_cannot_steal()
        self.live_lease()
        self.expired_lease()
        self.heartbeat()
        self.python_owned()
        self.stale_owner_and_kind()
        self.python_cannot_steal()
        print(f"\nJOB LEASE HARNESS {self.total - self.failures}/{self.total} passed")
        return 0 if self.failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    data_dir = tempfile.mkdtemp(prefix="einvite-lease-")
    base_env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    port = free_port()
    log_path = Path(data_dir) / "python-warm.log"
    warm = subprocess.Popen(
        [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(port)],
        env=base_env,
        stdout=log_path.open("w"),
        stderr=subprocess.STDOUT,
    )
    try:
        wait_health(port, warm, log_path)
    finally:
        stop([warm])

    reset(args.database_url)
    return Harness(args.database_url, base_env, data_dir).run()


if __name__ == "__main__":
    raise SystemExit(main())
