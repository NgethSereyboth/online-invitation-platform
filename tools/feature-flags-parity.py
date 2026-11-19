#!/usr/bin/env python3
"""S12c proof: GET /api/feature-flags answers identically on both backends.

Seeds overrides and one unknown flag, then compares the public projection for an
anonymous caller and for free/creator/pro sessions. Python caches the snapshot
for 60 s per process, so the seed happens after a warm-up boot and both servers
start cold — otherwise the harness would compare Python's cache, not its logic.

Usage:
  .venv/bin/python tools/feature-flags-parity.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "bin" / "python")
NODE = shutil.which("node")

USERS = {
    "free": ("parity-flags-free", "free"),
    "creator": ("parity-flags-creator", "creator"),
    "pro": ("parity-flags-pro", "pro"),
}
TOKENS = {key: f"parity-flags-{key}-session" for key in USERS}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_health(base: str, process: subprocess.Popen, log_path: Path, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise SystemExit(f"server exited early ({base}); log:\n{log_path.read_text()[-3000:]}")
        try:
            with urllib.request.urlopen(f"{base}/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.4)
    raise SystemExit(f"server at {base} did not answer; log:\n{log_path.read_text()[-3000:]}")


def get(base: str, path: str, cookie: str | None = None):
    headers = {"Cookie": cookie} if cookie else {}
    request = urllib.request.Request(f"{base}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body)
        except json.JSONDecodeError:
            return error.code, {"_raw": body}


def seed(database_url: str) -> None:
    import psycopg

    now = int(time.time() * 1000)
    flags = [
        # key, value, description, tier
        ("plugin_marketplace_enabled", 0, "", "creator"),
        ("analytics_live_enabled", 1, "", "creator"),
        ("analytics_enabled", 0, "", "free"),
        ("custom_experiment", 1, "Ad-hoc experiment", None),
        ("maintenance_mode", 1, "", None),
        ("guest_polls_enabled", 0, "Polls paused", None),
    ]
    with psycopg.connect(database_url) as connection:
        connection.execute("DELETE FROM sessions WHERE user_id LIKE %s", ("parity-flags-%",))
        connection.execute("DELETE FROM users WHERE id LIKE %s", ("parity-flags-%",))
        connection.execute("DELETE FROM feature_flags")
        for key, value, description, tier in flags:
            connection.execute(
                "INSERT INTO feature_flags(key,value,description,tier,updated_at,updated_by) "
                "VALUES(%s,%s,%s,%s,%s,'parity-admin')",
                (key, value, description, tier, now),
            )
        for plan_key, (user_id, plan) in USERS.items():
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role,plan) "
                "VALUES(%s,%s,%s,'x','y',%s,'customer',%s)",
                (user_id, f"{user_id}@example.test", sha256(f"{user_id}@example.test"), now, plan),
            )
            connection.execute(
                "INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,csrf_hash,last_seen_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    sha256(TOKENS[plan_key]),
                    f"parity-flags-session-{plan_key}",
                    user_id,
                    now + 86_400_000,
                    now,
                    sha256(f"csrf-{plan_key}"),
                    now,
                ),
            )
        connection.commit()


CASES = [
    ("anonymous", None),
    ("free plan", "free"),
    ("creator plan", "creator"),
    ("pro plan", "pro"),
]


def start(env: dict[str, str], port: int, log_path: Path, command: list[str]) -> subprocess.Popen:
    with open(log_path, "wb") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    wait_health(f"http://127.0.0.1:{port}", process, log_path)
    return process


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    if not NODE:
        raise SystemExit("node is not on PATH")

    data_dir = tempfile.mkdtemp(prefix="einvite-flags-")
    env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    processes: list[subprocess.Popen] = []
    try:
        # Warm-up boot: Python creates its own tables, then exits so the seed is
        # visible to a cold process rather than to the 60-second flag cache.
        warm_port = free_port()
        warm_log = Path(data_dir) / "python-warm.log"
        warm = start(
            env,
            warm_port,
            warm_log,
            [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(warm_port)],
        )
        warm.terminate()
        warm.wait(timeout=15)

        seed(args.database_url)

        python_port, node_port = free_port(), free_port()
        python_log = Path(data_dir) / "python.log"
        node_log = Path(data_dir) / "node.log"
        processes.append(
            start(
                env,
                python_port,
                python_log,
                [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(python_port)],
            )
        )
        processes.append(
            start(
                {**env, "PORT": str(node_port), "HOST": "127.0.0.1", "LOG_LEVEL": "warn"},
                node_port,
                node_log,
                [NODE, str(ROOT / "services/api-node/server.mjs")],
            )
        )

        failures = 0
        for name, key in CASES:
            cookie = f"einvite_session={TOKENS[key]}" if key else None
            python_status, python_body = get(f"http://127.0.0.1:{python_port}", "/api/feature-flags", cookie)
            node_status, node_body = get(f"http://127.0.0.1:{node_port}", "/api/feature-flags", cookie)
            same = python_status == node_status and python_body == node_body
            print(f"{'ok  ' if same else 'DIFF'} {name}: python={python_status} node={node_status}")
            if not same:
                failures += 1
                print("  python:", json.dumps(python_body, sort_keys=True)[:900])
                print("  node:  ", json.dumps(node_body, sort_keys=True)[:900])
        print(f"\nFEATURE FLAG PARITY {len(CASES) - failures}/{len(CASES)} identical, {failures} failing")
        if failures:
            print(f"\npython log:\n{python_log.read_text()[-2000:]}")
            print(f"\nnode log:\n{node_log.read_text()[-2000:]}")
        return 0 if failures == 0 else 1
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
