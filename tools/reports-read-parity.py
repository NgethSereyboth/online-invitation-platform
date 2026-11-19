#!/usr/bin/env python3
"""S12c proof: the admin reports queue answers identically on both backends.

Covers access (anonymous 401, customer 403, admin and super_admin 200), filters,
limit clamping, cursor paging, ignored cursors, invalid input (400), and the
admin IP allowlist in both the denying and the allowing direction — each phase
restarts both processes so neither reads a stale allowlist.

Usage:
  .venv/bin/python tools/reports-read-parity.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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

ACCOUNTS = {
    "admin": ("rep-admin", "admin"),
    "super": ("rep-super", "super_admin"),
    "user": ("rep-user", "customer"),
    "anon": (None, None),
}
TOKENS = {name: f"parity-reports-{name}-session" for name in ACCOUNTS}


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
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body)
        except json.JSONDecodeError:
            return error.code, {"_raw": body}


def start(env: dict[str, str], port: int, log_path: Path, command: list[str]) -> subprocess.Popen:
    with open(log_path, "wb") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    wait_health(f"http://127.0.0.1:{port}", process, log_path)
    return process


def stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        process.terminate()
    for process in processes:
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
    processes.clear()


def seed_accounts(database_url: str) -> None:
    import psycopg

    now = int(time.time() * 1000)
    with psycopg.connect(database_url) as connection:
        connection.execute("DELETE FROM sessions WHERE user_id LIKE 'rep-%'")
        connection.execute("DELETE FROM users WHERE id LIKE 'rep-%'")
        for name, (user_id, role) in ACCOUNTS.items():
            if not user_id:
                continue
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role,plan) "
                "VALUES(%s,%s,%s,'x','y',%s,%s,'free')",
                (user_id, f"{user_id}@example.test", sha256(f"{user_id}@example.test"), now, role),
            )
            connection.execute(
                "INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,csrf_hash,last_seen_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    sha256(TOKENS[name]),
                    f"{user_id}-session",
                    user_id,
                    now + 86_400_000,
                    now,
                    sha256(f"csrf-{name}"),
                    now,
                ),
            )
        connection.commit()


def seed_reports(database_url: str) -> None:
    import psycopg

    # Real epoch-ms values: PostgreSQL INTEGER would overflow here, which is
    # exactly the defect the BIGINT repair in features/reports.py fixes.
    base = int(time.time() * 1000) - 60_000
    rows = [
        # id, reporter, target_type, target_id, reason, body, status, resolved_by, resolved_at, note, created_at
        ("rep-r1", "user-a", "invitation", "inv-1", "spam", "looks like spam", "open", None, None, "", base + 9000),
        ("rep-r2", "user-b", "user", "user-c", "harassment", "", "investigating", None, None, "", base + 8000),
        ("rep-r3", "user-a", "invitation", "inv-2", "other", "body", "resolved_no_action", "rep-admin", base + 7000, "not actionable", base + 7000),
        ("rep-r4", "user-c", "user", "user-a", "impersonation", "", "duplicate", "rep-admin", base + 6000, "dup", base + 6000),
        ("rep-r5", "user-d", "invitation", "inv-3", "illegal_content", "x", "open", None, None, "", base + 5000),
    ]
    with psycopg.connect(database_url) as connection:
        connection.execute("DELETE FROM reports WHERE id LIKE 'rep-r%'")
        for row in rows:
            connection.execute(
                "INSERT INTO reports(id,reporter_id,target_type,target_id,reason,body,status,resolved_by,"
                "resolved_at,resolution_note,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                row,
            )
        connection.commit()


BASE_CASES = [
    ("admin default", "/api/admin/reports", "admin"),
    ("status open", "/api/admin/reports?status=open", "admin"),
    ("status uppercase normalises", "/api/admin/reports?status=OPEN", "admin"),
    ("status empty result", "/api/admin/reports?status=investigating&targetType=invitation", "admin"),
    ("targetType user", "/api/admin/reports?targetType=user", "admin"),
    ("combined filters", "/api/admin/reports?status=duplicate&targetType=user", "admin"),
    ("limit 2 paging", "/api/admin/reports?limit=2", "admin"),
    ("limit 0 clamps to 1", "/api/admin/reports?limit=0", "admin"),
    ("limit 500 clamps to 200", "/api/admin/reports?limit=500", "admin"),
    ("limit whitespace", "/api/admin/reports?limit=%202%20", "admin"),
    ("cursor numeric", "/api/admin/reports?limit=2&cursor=1760000007000", "admin"),
    ("cursor ignored when not digits", "/api/admin/reports?cursor=abc", "admin"),
    ("invalid status 400", "/api/admin/reports?status=bogus", "admin"),
    ("invalid limit 400", "/api/admin/reports?limit=abc", "admin"),
    ("decimal limit 400", "/api/admin/reports?limit=2.5", "admin"),
    ("super admin", "/api/admin/reports", "super"),
    ("customer 403", "/api/admin/reports", "user"),
    ("anonymous 401", "/api/admin/reports", "anon"),
]
ALLOWLIST_DENY_CASES = [
    ("allowlist denies admin", "/api/admin/reports", "admin"),
]
ALLOWLIST_ALLOW_CASES = [
    ("allowlist allows admin", "/api/admin/reports", "admin"),
]


def compare(services: dict[str, str], cases, failures: int) -> int:
    for name, path, who in cases:
        cookie = f"einvite_session={TOKENS[who]}" if who != "anon" else None
        py_status, py_body = get(services["python"], path, cookie)
        node_status, node_body = get(services["node"], path, cookie)
        same = py_status == node_status and py_body == node_body
        print(f"{'ok  ' if same else 'DIFF'} {name}: python={py_status} node={node_status}")
        if not same:
            failures += 1
            print("  python:", json.dumps(py_body, sort_keys=True)[:1200])
            print("  node:  ", json.dumps(node_body, sort_keys=True)[:1200])
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    if not NODE:
        raise SystemExit("node is not on PATH")

    data_dir = tempfile.mkdtemp(prefix="einvite-reports-")
    base_env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    processes: list[subprocess.Popen] = []
    failures = 0
    try:
        warm_port = free_port()
        warm_log = Path(data_dir) / "python-warm.log"
        warm = start(
            base_env,
            warm_port,
            warm_log,
            [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(warm_port)],
        )
        seed_accounts(args.database_url)
        # One authenticated read creates the reports table the way Python does.
        get(
            f"http://127.0.0.1:{warm_port}",
            "/api/admin/reports",
            f"einvite_session={TOKENS['admin']}",
        )
        stop([warm])
        seed_reports(args.database_url)

        python_log = Path(data_dir) / "python.log"
        node_log = Path(data_dir) / "node.log"

        def run_phase(cases, allowlist: str | None):
            env = dict(base_env)
            if allowlist is not None:
                env["EINVITE_ADMIN_IP_ALLOWLIST"] = allowlist
            else:
                env.pop("EINVITE_ADMIN_IP_ALLOWLIST", None)
            python_port, node_port = free_port(), free_port()
            services = {
                "python": f"http://127.0.0.1:{python_port}",
                "node": f"http://127.0.0.1:{node_port}",
            }
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
            result = compare(services, cases, failures)
            stop(processes)
            return result

        failures = run_phase(BASE_CASES, None)
        failures = run_phase(ALLOWLIST_DENY_CASES, "10.0.0.0/8")
        failures = run_phase(ALLOWLIST_ALLOW_CASES, "127.0.0.1/32,::1")

        total = len(BASE_CASES) + len(ALLOWLIST_DENY_CASES) + len(ALLOWLIST_ALLOW_CASES)
        print(f"\nREPORTS READ PARITY {total - failures}/{total} identical, {failures} failing")
        if failures:
            print(f"\npython log:\n{python_log.read_text()[-3000:]}")
            print(f"\nnode log:\n{node_log.read_text()[-3000:]}")
        return 0 if failures == 0 else 1
    finally:
        stop(processes)
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
