#!/usr/bin/env python3
"""S12c proof: the creator-analytics and jobs reads answer identically.

Covers, against one seeded database and both backends:
  GET /api/invitations/:id/analytics             owner 200 / collaborator 404 / anon 401
  GET /api/invitations/:id/analytics/live         flag off 403, stranger 404, then flag on 200
  GET /api/account/analytics/summary
  GET /api/account/analytics/creations            default, asc sort, status filter, paging
  GET /api/studio/bulk-jobs
  GET /api/invitations/:id/materials/import-jobs  readable 200, stranger 404

Python caches feature flags for 60 s per process, so the live-flag phase restarts
both servers cold rather than waiting for a cache to expire.

Usage:
  .venv/bin/python tools/analytics-read-parity.py --database-url postgres://...
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

OWNER = "parity-an-owner"
COLLAB = "parity-an-collab"
STRANGER = "parity-an-stranger"
TOKENS = {
    OWNER: "parity-an-owner-session",
    COLLAB: "parity-an-collab-session",
    STRANGER: "parity-an-stranger-session",
}


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


def request(base: str, path: str, cookie: str | None = None):
    headers = {"Cookie": cookie} if cookie else {}
    req = urllib.request.Request(f"{base}{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
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


def seed_base(database_url: str) -> None:
    import psycopg

    now = int(time.time() * 1000)
    with psycopg.connect(database_url) as connection:
        connection.execute("DELETE FROM analytics_events")
        connection.execute("DELETE FROM analytics_sessions")
        connection.execute("DELETE FROM material_import_jobs WHERE owner_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM studio_bulk_jobs WHERE owner_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM view_events WHERE invitation_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM rsvps WHERE invitation_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM guests WHERE invitation_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM invitation_collaborators WHERE invitation_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM invitations WHERE id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM sessions WHERE user_id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM users WHERE id LIKE %s", ("parity-an-%",))
        connection.execute("DELETE FROM feature_flags")

        for user_id in (OWNER, COLLAB, STRANGER):
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role,plan) "
                "VALUES(%s,%s,%s,'x','y',%s,'customer','free')",
                (user_id, f"{user_id}@example.test", sha256(f"{user_id}@example.test"), now),
            )
            connection.execute(
                "INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,csrf_hash,last_seen_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    sha256(TOKENS[user_id]),
                    f"{user_id}-session",
                    user_id,
                    now + 86_400_000,
                    now,
                    sha256(f"csrf-{user_id}"),
                    now,
                ),
            )

        invitations = [
            (
                "parity-an-inv1",
                "parity-an-inv1",
                json.dumps({"fields": {"names": "Sokha & Dara"}, "settings": {"rsvpEnabled": False}}),
                now - 3_600_000,
                OWNER,
                0,
                42,
                1,
            ),
            (
                "parity-an-inv2",
                "parity-an-inv2",
                "{not json",
                now - 7_200_000,
                OWNER,
                0,
                0,
                0,
            ),
            (
                "parity-an-inv3",
                "parity-an-inv3",
                json.dumps({"meta": {"title": "Archived one", "eventDate": "1760000000000"}}),
                now - 10_800_000,
                OWNER,
                1,
                0,
                1,
            ),
            (
                "parity-an-inv4",
                "parity-an-inv4",
                json.dumps({"fields": {"eventDate": 1761111111111}}),
                now - 14_400_000,
                COLLAB,
                0,
                5,
                0,
            ),
        ]
        for invite in invitations:
            connection.execute(
                "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,views,is_published) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                invite,
            )
        connection.execute(
            "INSERT INTO invitation_collaborators(invitation_id,user_id,role,created_at) VALUES(%s,%s,'content',%s)",
            ("parity-an-inv1", COLLAB, now),
        )

        for index in range(4):
            connection.execute(
                "INSERT INTO view_events(id,invitation_id,publication_id,viewed_at) VALUES(%s,%s,%s,%s)",
                (f"parity-an-view-{index}", "parity-an-inv1", "parity-an-pub", now - index * 86_400_000),
            )
        rsvps = [
            ("parity-an-rsvp-1", "yes", 2, now - 1000),
            ("parity-an-rsvp-2", "no", 1, now - 2000),
            ("parity-an-rsvp-3", "yes", 4, now - 3000),
        ]
        for rsvp_id, status, guest_count, created_at in rsvps:
            connection.execute(
                "INSERT INTO rsvps(id,invitation_id,publication_id,name,status,guest_count,created_at) "
                "VALUES(%s,%s,'parity-an-pub',%s,%s,%s,%s)",
                (rsvp_id, "parity-an-inv1", rsvp_id, status, guest_count, created_at),
            )
        for index, checked_in in enumerate((1, 0, 1)):
            connection.execute(
                "INSERT INTO guests(id,invitation_id,name,slug,token,created_at,checked_in) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    f"parity-an-guest-{index}",
                    "parity-an-inv1",
                    f"Guest {index}",
                    f"guest-{index}",
                    f"tok-{index}",
                    now,
                    checked_in,
                ),
            )

        for index, (kind, status, created_at) in enumerate(
            (("release-pin", "completed", now - 1000), ("bulk-archive", "running", now - 5000))
        ):
            connection.execute(
                "INSERT INTO studio_bulk_jobs(id,owner_id,kind,status,selection_json,result_json,created_by,created_at,completed_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    f"parity-an-bulk-{index}",
                    OWNER,
                    kind,
                    status,
                    json.dumps({"scope": "ids", "invitationIds": ["parity-an-inv1"]}),
                    json.dumps({"updated": 1}),
                    OWNER,
                    created_at,
                    created_at if status == "completed" else None,
                ),
            )

        for index, (source_type, status, failures) in enumerate(
            (("zip", "completed", '[]'), ("folder", "failed", '[{"path":"a.png","error":"too large"}]'))
        ):
            connection.execute(
                "INSERT INTO material_import_jobs(id,invitation_id,owner_id,source_type,root_name,status,"
                "total_files,processed_files,failed_files,total_bytes,processed_bytes,failures_json,created_at,updated_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    f"parity-an-job-{index}",
                    "parity-an-inv1",
                    OWNER,
                    source_type,
                    f"root-{index}",
                    status,
                    index + 2,
                    index + 2,
                    index,
                    index * 1024,
                    index * 512,
                    failures,
                    now - index * 60_000,
                    now - index * 30_000,
                ),
            )
        connection.commit()


def seed_analytics(database_url: str, live_enabled: bool) -> None:
    import psycopg

    now = int(time.time() * 1000)
    day = 24 * 60 * 60 * 1000
    sessions = [
        # id, recipient, started offset days, ended offset, duration, scroll, country, referrer, device
        ("s1", "r1", 1, 0, 40_000, 80, "KH", "facebook.com", "mobile"),
        ("s2", "r1", 2, 0, 60_000, 30, "KH", "facebook.com", "mobile"),
        ("s3", "r2", 3, 0, 20_000, 55, "TH", "facebook.com", "desktop"),
        ("s4", "r3", 5, 0, None, None, None, "twitter.com", "tablet"),
        ("s5", "r4", 10, 0, 10_000, 100, "US", "example.org", "desktop"),
        ("s6", None, 40, 0, 90_000, 90, "US", None, None),
    ]
    with psycopg.connect(database_url) as connection:
        connection.execute("DELETE FROM analytics_sessions")
        connection.execute("DELETE FROM analytics_events")
        for sid, recipient, start_days, end_days, duration, scroll, country, referrer, device in sessions:
            started = now - start_days * day
            ended = now - end_days * day
            connection.execute(
                "INSERT INTO analytics_sessions(id,invitation_id,recipient_id,started_at,ended_at,duration_ms,"
                "max_scroll_pct,country_code,referrer_domain,device_type,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    sid,
                    "parity-an-inv1",
                    recipient,
                    started,
                    ended,
                    duration,
                    scroll,
                    country,
                    referrer,
                    device,
                    started,
                ),
            )
        events = [
            ("s1", "invitation.view", now - 1 * day),
            ("s2", "invitation.view", now - 2 * day),
            ("s3", "invitation.view", now - 3 * day),
            ("s4", "invitation.rsvp.open", now - 5 * day),
            ("s5", "invitation.rsvp.submit", now - 10 * day),
            ("s5", "invitation.rsvp.submit", now - 10 * day + 1000),
            ("s6", "invitation.view", now - 40 * day),
        ]
        for sid, event_type, created_at in events:
            connection.execute(
                "INSERT INTO analytics_events(session_id,invitation_id,event_type,payload_json,created_at) "
                "VALUES(%s,%s,%s,'{}',%s)",
                (sid, "parity-an-inv1", event_type, created_at),
            )
        connection.execute(
            "INSERT INTO feature_flags(key,value,description,tier,updated_at,updated_by) "
            "VALUES('analytics_live_enabled',%s,'', 'creator',%s,'parity-admin') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (1 if live_enabled else 0, now),
        )
        connection.commit()


CASES = [
    ("owner analytics", "/api/invitations/parity-an-inv1/analytics", OWNER),
    ("malformed draft analytics", "/api/invitations/parity-an-inv2/analytics", OWNER),
    ("collaborator analytics (404)", "/api/invitations/parity-an-inv1/analytics", COLLAB),
    ("anonymous analytics (401)", "/api/invitations/parity-an-inv1/analytics", None),
    ("account summary", "/api/account/analytics/summary", OWNER),
    ("creations default", "/api/account/analytics/creations", OWNER),
    ("creations asc by views", "/api/account/analytics/creations?sort=views&order=asc", OWNER),
    ("creations published filter", "/api/account/analytics/creations?status=published", OWNER),
    ("creations archived filter", "/api/account/analytics/creations?status=archived", OWNER),
    ("creations paged", "/api/account/analytics/creations?limit=2&offset=1", OWNER),
    ("creations bad paging", "/api/account/analytics/creations?limit=abc&offset=-4", OWNER),
    ("studio bulk jobs", "/api/studio/bulk-jobs", OWNER),
    ("studio bulk jobs other user", "/api/studio/bulk-jobs", COLLAB),
    ("material import jobs", "/api/invitations/parity-an-inv1/materials/import-jobs", OWNER),
    ("material jobs collaborator", "/api/invitations/parity-an-inv1/materials/import-jobs", COLLAB),
    ("material jobs stranger (404)", "/api/invitations/parity-an-inv1/materials/import-jobs", STRANGER),
]
LIVE_CASES_OFF = [
    ("live flag off (403)", "/api/invitations/parity-an-inv1/analytics/live", OWNER),
    ("live stranger (404)", "/api/invitations/parity-an-inv1/analytics/live", STRANGER),
]
LIVE_CASES_ON = [
    ("live flag on", "/api/invitations/parity-an-inv1/analytics/live", OWNER),
    ("live flag on collaborator", "/api/invitations/parity-an-inv1/analytics/live", COLLAB),
]


def compare(services: dict[str, str], cases, failures: int) -> int:
    for name, path, user in cases:
        cookie = f"einvite_session={TOKENS[user]}" if user else None
        py_status, py_body = request(services["python"], path, cookie)
        node_status, node_body = request(services["node"], path, cookie)
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

    data_dir = tempfile.mkdtemp(prefix="einvite-analytics-")
    env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    processes: list[subprocess.Popen] = []
    failures = 0
    try:
        # Warm-up: base schema, then one analytics read so ensure_analytics_ready
        # creates the three analytics tables before the seed inserts into them.
        warm_port = free_port()
        warm_log = Path(data_dir) / "python-warm.log"
        warm = start(
            env,
            warm_port,
            warm_log,
            [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(warm_port)],
        )
        seed_base(args.database_url)
        request(
            f"http://127.0.0.1:{warm_port}",
            "/api/account/analytics/summary",
            f"einvite_session={TOKENS[OWNER]}",
        )
        stop([warm])

        python_log = Path(data_dir) / "python.log"
        node_log = Path(data_dir) / "node.log"

        # Phase A — live analytics flag off.
        seed_analytics(args.database_url, live_enabled=False)
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
        failures = compare(services, CASES, failures)
        failures = compare(services, LIVE_CASES_OFF, failures)
        stop(processes)

        # Phase B — flag on; both processes restart so neither flag cache is stale.
        seed_analytics(args.database_url, live_enabled=True)
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
        failures = compare(services, LIVE_CASES_ON, failures)

        total = len(CASES) + len(LIVE_CASES_OFF) + len(LIVE_CASES_ON)
        print(f"\nANALYTICS READ PARITY {total - failures}/{total} identical, {failures} failing")
        if failures:
            print(f"\npython log:\n{python_log.read_text()[-3000:]}")
            print(f"\nnode log:\n{node_log.read_text()[-3000:]}")
        return 0 if failures == 0 else 1
    finally:
        stop(processes)
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
