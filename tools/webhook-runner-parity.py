#!/usr/bin/env python3
"""S12c webhook.deliver runner parity: Python vs Node.

Run both implementations against one PostgreSQL and one scripted local
receiver. Each scenario seeds an identical endpoint and queued job, advances the
same injected clock, and compares the job state, backoff timestamp, endpoint
counters and received requests.

Usage:
  .venv/bin/python tools/webhook-runner-parity.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
NODE = os.environ.get("NODE_BIN", "node")
sys.path.insert(0, str(ROOT / "src" / "python"))
from core.webhooks import verify_signature  # noqa: E402

SECRET = "whsec_parity"
BODY = '{"event":"rsvp.created","eventId":"wh-parity"}'
T0 = int(time.time() * 1000)


class Receiver:
    """One receiver, per-path scripted statuses, and per-request records."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.scripts: dict[str, list[int]] = {}
        self.lock = threading.Lock()
        receiver = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                with receiver.lock:
                    receiver.requests.append(
                        {
                            "path": self.path,
                            "body": body,
                            "signature": self.headers.get("X-EInvite-Signature", ""),
                            "timestamp": self.headers.get("X-EInvite-Timestamp", ""),
                        }
                    )
                    script = receiver.scripts.get(self.path, [200])
                    status = script.pop(0) if len(script) > 1 else script[0]
                self.send_response(status)
                if 300 <= status < 400:
                    self.send_header("Location", "/ignored")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *_args):  # silence the receiver
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def script(self, path: str, statuses: list[int]) -> None:
        with self.lock:
            self.scripts[path] = list(statuses)

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def close(self) -> None:
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


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


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
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
    raise RuntimeError(f"no JSON output from {' '.join(command)}:\n{result.stdout[-4000:]}")


def db_execute(database_url: str, sql: str, params=()) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)


def reset(database_url: str) -> None:
    db_execute(database_url, "DELETE FROM background_jobs WHERE kind='webhook.deliver' OR id LIKE %s", ("wh-job-%",))
    db_execute(database_url, "DELETE FROM webhook_endpoints WHERE id LIKE %s", ("wh-parity-%",))


def seed_endpoint(database_url: str, endpoint_id: str, url: str, *, active: int = 1, failure_count: int = 0) -> None:
    db_execute(database_url, "DELETE FROM webhook_endpoints WHERE id=%s", (endpoint_id,))
    db_execute(
        database_url,
        "INSERT INTO webhook_endpoints(id,owner_id,url,events_json,secret,secret_hint,active,created_at,"
        "last_delivery_at,last_status,failure_count) VALUES(%s,'owner-1',%s,'[\"*\"]',%s,'test',%s,%s,NULL,NULL,%s)",
        (endpoint_id, url, SECRET, active, T0, failure_count),
    )


def seed_job(database_url: str, job_id: str, endpoint_id: str, *, attempts: int = 0) -> None:
    payload = json.dumps(
        {"endpointId": endpoint_id, "event": "rsvp.created", "body": BODY, "ownerId": "owner-1"},
        separators=(",", ":"),
    )
    db_execute(database_url, "DELETE FROM background_jobs WHERE id=%s", (job_id,))
    db_execute(
        database_url,
        "INSERT INTO background_jobs(id,kind,payload_json,state,attempts,available_at,locked_at,last_error,"
        "created_at,updated_at,lock_owner,lease_expires_at) "
        "VALUES(%s,'webhook.deliver',%s,'queued',%s,%s,NULL,'',%s,%s,'',NULL)",
        (job_id, payload, attempts, T0, T0, T0),
    )


def observe(database_url: str, job_id: str, endpoint_id: str) -> dict:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT state,attempts,available_at,locked_at,last_error,lock_owner "
                "FROM background_jobs WHERE id=%s",
                (job_id,),
            )
            job = cursor.fetchone()
            cursor.execute(
                "SELECT last_delivery_at,last_status,failure_count FROM webhook_endpoints WHERE id=%s",
                (endpoint_id,),
            )
            endpoint = cursor.fetchone()
    if not job:
        raise RuntimeError(f"missing job {job_id}")
    return {
        "job": {
            "state": job[0],
            "attempts": job[1],
            "available_at": job[2],
            "locked_at_is_null": job[3] is None,
            "last_error": job[4],
            "lock_owner": job[5],
        },
        "endpoint": None
        if endpoint is None
        else {"last_delivery_at": endpoint[0], "last_status": endpoint[1], "failure_count": endpoint[2]},
    }


def normalize_requests(requests: list[dict]) -> list[dict]:
    normalized = []
    for request in requests:
        normalized.append(
            {
                "body": request["body"].decode("utf-8"),
                "signature_valid": verify_signature(
                    request["body"], request["signature"], SECRET, now_ms=int(time.time() * 1000)
                ),
                "timestamp_matches_signature": request["signature"].startswith(f"t={request['timestamp']},"),
            }
        )
    return normalized


class Harness:
    def __init__(self, database_url: str, data_dir: str, env: dict[str, str], receiver: Receiver) -> None:
        self.database_url = database_url
        self.data_dir = data_dir
        self.env = env
        self.receiver = receiver
        self.total = 0
        self.failures = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}{'' if ok else ' — ' + detail}")
        if not ok:
            self.failures += 1

    def run_backend(self, backend: str, now_ms: int, allow_private: bool) -> dict:
        if backend == "python":
            return run_json(
                [
                    PY,
                    str(ROOT / "tools/webhook-runner-python-agent.py"),
                    "--database-url",
                    self.database_url,
                    "--data-dir",
                    self.data_dir,
                    "--now-ms",
                    str(now_ms),
                    "--limit",
                    "1",
                    "--allow-private",
                    "true" if allow_private else "false",
                ],
                self.env,
            )
        return run_json(
            [
                NODE,
                str(ROOT / "tools/webhook-runner-agent.mjs"),
                "--database-url",
                self.database_url,
                "--now-ms",
                str(now_ms),
                "--limit",
                "1",
                "--allow-private",
                "true" if allow_private else "false",
            ],
            self.env,
        )

    def execute(
        self,
        backend: str,
        name: str,
        statuses: list[int],
        steps: list[int],
        *,
        endpoint_exists: bool = True,
        active: int = 1,
        failure_count: int = 0,
        url_override: str | None = None,
        allow_private: bool = True,
    ) -> list[dict]:
        reset(self.database_url)
        path = f"/{name}-{backend}"
        endpoint_id = f"wh-parity-{name}-{backend}"
        job_id = f"wh-job-{name}-{backend}"
        if endpoint_exists:
            self.receiver.script(path, statuses)
            url = url_override if url_override is not None else self.receiver.url(path)
            seed_endpoint(self.database_url, endpoint_id, url, active=active, failure_count=failure_count)
        seed_job(self.database_url, job_id, endpoint_id)

        observations = []
        for offset in steps:
            start = len(self.receiver.requests)
            result = self.run_backend(backend, T0 + offset, allow_private)
            observations.append(
                {
                    "processed": result["processed"],
                    "job": observe(self.database_url, job_id, endpoint_id)["job"],
                    "endpoint": observe(self.database_url, job_id, endpoint_id)["endpoint"],
                    "requests": normalize_requests(self.receiver.requests[start:]),
                }
            )
        return observations

    def scenario(
        self,
        name: str,
        statuses: list[int],
        steps: list[int],
        **options,
    ) -> None:
        python_steps = self.execute("python", name, statuses, steps, **options)
        node_steps = self.execute("node", name, statuses, steps, **options)
        for index, (python_step, node_step) in enumerate(zip(python_steps, node_steps)):
            self.check(
                f"{name} step {index} (T+{steps[index]}ms) is identical",
                python_step == node_step,
                json.dumps({"python": python_step, "node": node_step}, sort_keys=True)[:1800],
            )
        requests = [request for step in python_steps for request in step["requests"]]
        self.check(
            f"{name} signatures verify for every Python attempt",
            all(request["signature_valid"] and request["timestamp_matches_signature"] for request in requests)
            if requests
            else True,
            json.dumps(requests)[:1200],
        )
        requests = [request for step in node_steps for request in step["requests"]]
        self.check(
            f"{name} signatures verify for every Node attempt",
            all(request["signature_valid"] and request["timestamp_matches_signature"] for request in requests)
            if requests
            else True,
            json.dumps(requests)[:1200],
        )

    def run(self) -> int:
        self.scenario("success", [200], [0], failure_count=3)
        self.scenario("retry-then-success", [500, 503, 200], [0, 1000, 3000])
        self.scenario("exhausted", [500], [0, 1000, 3000, 7000, 15000])
        self.scenario("terminal-400", [400], [0])
        self.scenario("redirect-302", [302], [0])
        self.scenario("missing-endpoint", [200], [0], endpoint_exists=False)
        self.scenario("inactive-endpoint", [200], [0], active=0, failure_count=2)
        self.scenario(
            "invalid-url",
            [200],
            [0],
            url_override="http://127.0.0.1:9/hook",
            allow_private=False,
        )
        print(f"\nWEBHOOK RUNNER PARITY {self.total - self.failures}/{self.total} identical")
        return 0 if self.failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    data_dir = tempfile.mkdtemp(prefix="einvite-webhook-parity-")
    env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "EINVITE_ALLOW_PRIVATE_WEBHOOKS": "1",
        "EINVITE_BACKGROUND_MEDIA": "0",
        "EINVITE_FIELD_ENCRYPTION": "0",
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    port = free_port()
    log = Path(data_dir) / "warm.log"
    warm = subprocess.Popen(
        [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=log.open("w"),
        stderr=subprocess.STDOUT,
    )
    receiver = Receiver()
    try:
        wait_health(port, warm, log)
        stop(warm)
        reset(args.database_url)
        return Harness(args.database_url, data_dir, env, receiver).run()
    finally:
        stop(warm)
        receiver.close()


if __name__ == "__main__":
    raise SystemExit(main())
