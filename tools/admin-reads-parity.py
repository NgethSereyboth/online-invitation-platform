#!/usr/bin/env python3
"""S12c proof: the admin console reads answer identically on both backends.

Covers access (anonymous 401, customer 403, admin and super_admin 200), the
overview counts, the legacy user array, users-v2 masking/search/cursor/paging,
the invitation list, the audit explorer (filters, clamps, CSV bytes) and one
background job. The admin IP allowlist is exercised in the denying and the
allowing direction, with both processes restarted so neither reads a stale
allowlist.

Usage:
  .venv/bin/python tools/admin-reads-parity.py --database-url postgres://...
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
    "admin": ("adm-admin", "admin"),
    "super": ("adm-super", "super_admin"),
    "user": ("adm-user", "customer"),
    "suspended": ("adm-susp", "customer"),
    "anon": (None, None),
}
TOKENS = {name: f"parity-admin-reads-{name}-session" for name in ACCOUNTS}


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
    request = urllib.request.Request(f"{base}{path}", headers={"Cookie": cookie} if cookie else {})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, (json.loads(body) if body else None), response.headers.get("Content-Type")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body), error.headers.get("Content-Type")
        except json.JSONDecodeError:
            return error.code, {"_raw": body}, error.headers.get("Content-Type")


def get_raw(base: str, path: str, cookie: str | None = None):
    request = urllib.request.Request(f"{base}{path}", headers={"Cookie": cookie} if cookie else {})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8"), response.headers.get("Content-Type")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8"), error.headers.get("Content-Type")


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


def seed(database_url: str) -> None:
    import psycopg

    now = int(time.time() * 1000)
    emails = {name: f"{user_id}@example.test" for name, (user_id, _) in ACCOUNTS.items() if user_id}
    with psycopg.connect(database_url) as connection:
        for statement in (
            "DELETE FROM rsvps WHERE id LIKE 'adm-%'",
            "DELETE FROM assets WHERE id LIKE 'adm-%'",
            "DELETE FROM publications WHERE id LIKE 'adm-%'",
            "DELETE FROM invitations WHERE id LIKE 'adm-%'",
            "DELETE FROM user_templates WHERE id LIKE 'adm-%'",
            "DELETE FROM background_jobs WHERE id LIKE 'adm-%'",
            "DELETE FROM audit_events WHERE id LIKE 'adm-%' OR action='admin.users_unmasked'",
            "DELETE FROM sessions WHERE user_id LIKE 'adm-%'",
            "DELETE FROM users WHERE id LIKE 'adm-%'",
        ):
            connection.execute(statement)
        for name, (user_id, role) in ACCOUNTS.items():
            if not user_id:
                continue
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role,plan,"
                "upload_enabled,suspended_at,force_mfa) VALUES(%s,%s,%s,'x','y',%s,%s,'free',%s,%s,%s)",
                (
                    user_id,
                    emails[name],
                    sha256(emails[name]),
                    now - (10 if name == "suspended" else 5) * 1000,
                    role,
                    0 if name == "user" else 1,
                    now - 500 if name == "suspended" else None,
                    1 if name == "super" else 0,
                ),
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
        connection.execute(
            "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,views,access_mode,is_published) "
            "VALUES('adm-inv1','adm-one',%s,%s,'adm-admin',0,3,'unlisted',1)",
            (json.dumps({"fields": {"names": "Ada & Bo"}}), now - 2000),
        )
        connection.execute(
            "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,views,access_mode,is_published) "
            "VALUES('adm-inv2','adm-two','not json',%s,'adm-user',1,0,'unlisted',0)",
            (now - 1000,),
        )
        connection.execute(
            "INSERT INTO publications(id,invitation_id,version,document_json,published_at) "
            "VALUES('adm-pub1','adm-inv1',1,'{}',%s)",
            (now - 2000,),
        )
        for template_id, owner, name, visibility, status in (
            ("adm-t1", "adm-admin", "Public", "public", "approved"),
            ("adm-t2", "adm-user", "Private", "private", "draft"),
        ):
            connection.execute(
                "INSERT INTO user_templates(id,owner_id,name,category,document_json,created_at,updated_at,"
                "visibility,marketplace_status) VALUES(%s,%s,%s,'wedding','{}',%s,%s,%s,%s)",
                (template_id, owner, name, now - 3000, now - 3000, visibility, status),
            )
        for rsvp_id, status in (("adm-r1", "yes"), ("adm-r2", "no")):
            connection.execute(
                "INSERT INTO rsvps(id,invitation_id,publication_id,name,normalized_name,status,guest_count,"
                "note,created_at,updated_at,answers_json) VALUES(%s,'adm-inv1','adm-pub1',%s,%s,%s,2,'',%s,%s,'{}')",
                (rsvp_id, rsvp_id, rsvp_id, status, now - 4000, now - 4000),
            )
        connection.execute(
            "INSERT INTO assets(id,invitation_id,name,mime,path,size,created_at) "
            "VALUES('adm-a1','adm-inv1','a.png','image/png','a.png',123,%s)",
            (now - 4000,),
        )
        audit_rows = [
            ("adm-e1", "adm-user", "user.login", "user", "adm-user", '{"x":1}', "", 0, now - 5000),
            ("adm-e2", "adm-admin", "admin.users_unmasked", "user", "", '{"admin":true}', "127.0.0.1", 1, now - 4000),
            ("adm-e3", "adm-user", "invitation.view", "invitation", "adm-inv1", '{"n":2}', "10.0.0.9", 0, now - 3000),
            ("adm-e4", None, "session.expired", "session", "", "{}", "10.1.0.9", 0, 1_700_000_000_000),
            ("adm-e5", "adm-user", "report.created", "report", "r1", "{}", "127.0.0.1", 0, now - 1000),
        ]
        for row in audit_rows:
            connection.execute(
                "INSERT INTO audit_events(id,user_id,action,target_type,target_id,metadata_json,ip_address,"
                "previous_hash,event_hash,created_at,admin_only) VALUES(%s,%s,%s,%s,%s,%s,%s,'',%s,%s,%s)",
                (*row[:7], sha256(row[0]), row[8], row[7]),
            )
        connection.execute(
            "INSERT INTO background_jobs(id,kind,payload_json,state,attempts,available_at,last_error,created_at,updated_at) "
            "VALUES('adm-job1','webhook.deliver',%s,'queued',2,%s,'',%s,%s)",
            (json.dumps({"endpointId": "e1"}), now, now - 6000, now - 6000),
        )
        connection.commit()


BASE_CASES = [
    ("overview admin", "/api/admin/overview", "admin"),
    ("overview super", "/api/admin/overview", "super"),
    ("overview customer 403", "/api/admin/overview", "user"),
    ("overview anonymous 401", "/api/admin/overview", "anon"),
    ("users legacy", "/api/admin/users", "admin"),
    ("users legacy super", "/api/admin/users", "super"),
    ("users legacy customer 403", "/api/admin/users", "user"),
    ("users-v2 default masked", "/api/admin/users-v2", "admin"),
    ("users-v2 unmask", "/api/admin/users-v2?unmask=1", "admin"),
    ("users-v2 limit 2", "/api/admin/users-v2?limit=2", "admin"),
    ("users-v2 limit 0 clamps", "/api/admin/users-v2?limit=0", "admin"),
    ("users-v2 limit 500 clamps", "/api/admin/users-v2?limit=500", "admin"),
    ("users-v2 exact search", "/api/admin/users-v2?q=ADM-SUSP%40Example.Test%20", "admin"),
    ("users-v2 substring search", "/api/admin/users-v2?q=example", "admin"),
    ("users-v2 no match", "/api/admin/users-v2?q=nobody", "admin"),
    ("users-v2 valid cursor", "/api/admin/users-v2?limit=2&cursor=1:zzz", "admin"),
    ("users-v2 invalid cursor 400", "/api/admin/users-v2?cursor=abc", "admin"),
    ("users-v2 invalid limit 400", "/api/admin/users-v2?limit=abc", "admin"),
    ("users-v2 customer 403", "/api/admin/users-v2", "user"),
    ("invitations admin", "/api/admin/invitations", "admin"),
    ("invitations super", "/api/admin/invitations", "super"),
    ("invitations customer 403", "/api/admin/invitations", "user"),
    ("audit default", "/api/admin/audit-events", "admin"),
    ("audit action filter", "/api/admin/audit-events?action=user.login", "admin"),
    ("audit user filter", "/api/admin/audit-events?user=adm-user", "admin"),
    ("audit target filter", "/api/admin/audit-events?targetType=invitation&targetId=adm-inv1", "admin"),
    ("audit ip filter", "/api/admin/audit-events?ip=10.0.0.9", "admin"),
    ("audit adminOnly", "/api/admin/audit-events?adminOnly=1", "admin"),
    ("audit from date", "/api/admin/audit-events?from=2000-01-01", "admin"),
    ("audit to date", "/api/admin/audit-events?to=2000-01-01", "admin"),
    ("audit limit 2", "/api/admin/audit-events?limit=2", "admin"),
    ("audit limit 500 clamps", "/api/admin/audit-events?limit=500", "admin"),
    ("audit invalid limit 400", "/api/admin/audit-events?limit=abc", "admin"),
    ("audit invalid date 400", "/api/admin/audit-events?from=yesterday", "admin"),
    ("audit customer 403", "/api/admin/audit-events", "user"),
    ("job found", "/api/admin/jobs/adm-job1", "admin"),
    ("job missing 404", "/api/admin/jobs/nope", "admin"),
    ("job customer 403", "/api/admin/jobs/adm-job1", "user"),
    ("job anonymous 401", "/api/admin/jobs/adm-job1", "anon"),
]
CSV_CASES = [
    ("audit csv", "/api/admin/audit-events?format=CSV", "admin"),
]
ALLOWLIST_DENY_CASES = [
    ("allowlist denies overview", "/api/admin/overview", "admin"),
]
ALLOWLIST_ALLOW_CASES = [
    ("allowlist allows overview", "/api/admin/overview", "admin"),
]


def compare(services: dict[str, str], cases, failures: int) -> int:
    for name, path, who in cases:
        cookie = f"einvite_session={TOKENS[who]}" if who != "anon" else None
        py_status, py_body, _ = get(services["python"], path, cookie)
        node_status, node_body, _ = get(services["node"], path, cookie)
        same = py_status == node_status and py_body == node_body
        print(f"{'ok  ' if same else 'DIFF'} {name}: python={py_status} node={node_status}")
        if not same:
            failures += 1
            print("  python:", json.dumps(py_body, sort_keys=True)[:1200])
            print("  node:  ", json.dumps(node_body, sort_keys=True)[:1200])
    return failures


def compare_csv(services: dict[str, str], cases, failures: int) -> int:
    for name, path, who in cases:
        cookie = f"einvite_session={TOKENS[who]}" if who != "anon" else None
        py_status, py_body, py_type = get_raw(services["python"], path, cookie)
        node_status, node_body, node_type = get_raw(services["node"], path, cookie)
        same = py_status == node_status and py_body == node_body and py_type == node_type
        print(f"{'ok  ' if same else 'DIFF'} {name}: python={py_status} node={node_status}")
        if not same:
            failures += 1
            print("  python:", py_type, py_body[:800])
            print("  node:  ", node_type, node_body[:800])
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    if not NODE:
        raise SystemExit("node is not on PATH")

    data_dir = tempfile.mkdtemp(prefix="einvite-admin-reads-")
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
        seed(args.database_url)
        stop([warm])

        python_log = Path(data_dir) / "python.log"
        node_log = Path(data_dir) / "node.log"

        def run_phase(cases, allowlist: str | None, csv_cases=()):
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
            result = compare_csv(services, csv_cases, result)
            stop(processes)
            return result

        failures = run_phase(BASE_CASES, None, CSV_CASES)
        failures = run_phase(ALLOWLIST_DENY_CASES, "10.0.0.0/8")
        failures = run_phase(ALLOWLIST_ALLOW_CASES, "127.0.0.1/32,::1")

        total = len(BASE_CASES) + len(CSV_CASES) + len(ALLOWLIST_DENY_CASES) + len(ALLOWLIST_ALLOW_CASES)
        print(f"\nADMIN READS PARITY {total - failures}/{total} identical, {failures} failing")
        if failures:
            print(f"\npython log:\n{python_log.read_text()[-3000:]}")
            print(f"\nnode log:\n{node_log.read_text()[-3000:]}")
        return 0 if failures == 0 else 1
    finally:
        stop(processes)
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
