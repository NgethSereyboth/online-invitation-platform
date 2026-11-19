#!/usr/bin/env python3
"""S10 proof: the invitation read cluster answers identically on both backends.

Seeds one PostgreSQL database with an owner, a content collaborator, a manager,
a stranger, invitations in several states, guests (including revoked and expired
personal links) and RSVPs. Both backends serve the same rows; responses are
compared as parsed JSON, and personal-link tokens are part of the comparison
because they are HMACs over a shared secret.

Usage:
  .venv/bin/python tools/invitation-read-parity.py --database-url postgres://...
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
GUEST_SECRET = secrets.token_urlsafe(32)  # per run; both backends receive it via env

USERS = {
    "owner": "parity-r-owner",
    "content": "parity-r-content",
    "manager": "parity-r-manager",
    "stranger": "parity-r-stranger",
}
TOKENS = {
    "owner": "parity-r-owner-session",
    "content": "parity-r-content-session",
    "manager": "parity-r-manager-session",
    "stranger": "parity-r-stranger-session",
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
    draft = {
        "version": 1,
        "objects": {"title": {"type": "text", "html": "Parity draft"}},
        "privacy": {},
    }
    with psycopg.connect(database_url) as connection:
        connection.execute("DELETE FROM invitation_versions WHERE invitation_id LIKE %s", ("parity-r-inv-%",))
        connection.execute("DELETE FROM sessions WHERE user_id LIKE %s", ("parity-r-%",))
        connection.execute("DELETE FROM invitations WHERE slug LIKE %s", ("parity-r-%",))
        connection.execute("DELETE FROM users WHERE id LIKE %s", ("parity-r-%",))
        for key, user_id in USERS.items():
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role) "
                "VALUES(%s,%s,%s,'x','y',%s,'customer')",
                (user_id, f"{user_id}@example.test", sha256(f"{user_id}@example.test"), now),
            )
            connection.execute(
                "INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,csrf_hash,last_seen_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    sha256(TOKENS[key]),
                    f"parity-r-session-{key}",
                    user_id,
                    now + 86_400_000,
                    now,
                    sha256(f"csrf-{key}"),
                    now,
                ),
            )

        fixtures = [
            # id, slug, owner key, deleted_at
            ("parity-r-inv-owned", "parity-r-owned", "owner", None),
            ("parity-r-inv-shared", "parity-r-shared", "owner", None),
            ("parity-r-inv-empty", "parity-r-empty", "owner", None),
            ("parity-r-inv-foreign", "parity-r-foreign", "stranger", None),
            ("parity-r-inv-deleted", "parity-r-deleted", "owner", now - 1_000),
            ("parity-r-inv-deleted-titled", "parity-r-deleted-titled", "owner", now - 2_000),
        ]
        for invitation_id, slug, owner_key, deleted_at in fixtures:
            body = dict(draft)
            if invitation_id == "parity-r-inv-deleted-titled":
                body = {**draft, "fields": {"names": "A titled trashed invitation"}}
            connection.execute(
                "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,views,access_mode,"
                "is_published,deleted_at,custom_domain,gallery_access_password_hash,purge_at) "
                "VALUES(%s,%s,%s,%s,%s,0,0,'unlisted',1,%s,%s,NULL,%s)",
                (
                    invitation_id,
                    slug,
                    json.dumps(body, sort_keys=True),
                    now - 5_000,
                    USERS[owner_key],
                    deleted_at,
                    "owned.example.test" if invitation_id == "parity-r-inv-owned" else None,
                    now + 86_400_000 if deleted_at else None,
                ),
            )
        for invitation_id in ("parity-r-inv-shared", "parity-r-inv-owned"):
            for role, key in (("content", "content"), ("manager", "manager")):
                connection.execute(
                    "INSERT INTO invitation_collaborators(invitation_id,user_id,role,created_at) VALUES(%s,%s,%s,%s)",
                    (invitation_id, USERS[key], role, now),
                )

        guests = [
            # id, name, slug, salt, revoked, expires offset, tags
            ("parity-r-guest-1", "Ada Lovelace", "ada", "salt-ada", None, None, ["vip"]),
            ("parity-r-guest-2", "Grace Hopper", "grace", "salt-grace", now - 1_000, None, []),
            ("parity-r-guest-3", "Alan Turing", "alan", "", None, now - 1_000, ["speaker"]),
            ("parity-r-guest-4", "Katherine Johnson", "katherine", "salt-kj", None, now + 86_400_000, []),
        ]
        for guest_id, name, slug, salt, revoked, expires, tags in guests:
            connection.execute(
                "INSERT INTO guests(id,invitation_id,name,phone,email,group_name,household_id,tags_json,"
                "table_name,seat_label,token,token_hash,token_salt,token_version,token_expires_at,"
                "token_revoked_at,created_at,slug,delivery_status,checked_in) "
                "VALUES(%s,'parity-r-inv-owned',%s,%s,%s,'Family','hh-1',%s,'Table 4','4A',%s,NULL,%s,1,%s,%s,%s,%s,'sent',0)",
                (
                    guest_id,
                    name,
                    "+8551000000",
                    f"{slug}@example.test",
                    json.dumps(tags),
                    f"hashed-{guest_id}",
                    salt,
                    expires,
                    revoked,
                    now - 10_000,
                    slug,
                ),
            )
        connection.execute(
            "INSERT INTO publications(id,invitation_id,version,document_json,published_at) "
            "VALUES(%s,'parity-r-inv-owned',3,%s,%s)",
            ("parity-r-pub-3", json.dumps({**draft, "version": 3}, sort_keys=True), now - 60_000),
        )
        connection.execute(
            "INSERT INTO publications(id,invitation_id,version,document_json,published_at) "
            "VALUES(%s,'parity-r-inv-owned',2,%s,%s)",
            ("parity-r-pub-2", json.dumps({**draft, "version": 2}, sort_keys=True), now - 120_000),
        )
        for index, (snapshot_id, summary, created) in enumerate(
            (
                ("parity-r-auto-1", "Auto snapshot", now - 30_000),
                ("parity-r-auto-2", "Second auto snapshot", now - 90_000),
            )
        ):
            connection.execute(
                "INSERT INTO invitation_versions(id,invitation_id,document_json,author_id,author_name,"
                "summary,is_auto,created_at) VALUES(%s,'parity-r-inv-owned',%s,'parity-r-owner','Owner',%s,1,%s)",
                (snapshot_id, json.dumps({**draft, "auto": index + 1}, sort_keys=True), summary, created),
            )
        for index, (name, status, count, answers) in enumerate(
            (
                ("Ada Lovelace", "Yes, joyfully", 2, {"meal": "vegetarian"}),
                ("Grace Hopper", "Unable to attend", 1, {}),
            )
        ):
            connection.execute(
                "INSERT INTO rsvps(id,invitation_id,publication_id,guest_id,name,normalized_name,status,"
                "guest_count,note,created_at,updated_at,answers_json) "
                "VALUES(%s,'parity-r-inv-owned','pub-1',NULL,%s,%s,%s,%s,NULL,%s,%s,%s)",
                (
                    f"parity-r-rsvp-{index}",
                    name,
                    name.lower(),
                    status,
                    count,
                    now - index * 1_000,
                    now,
                    json.dumps(answers),
                ),
            )
        connection.commit()


CASES = [
    ("unauth invitation", "/api/invitations/parity-r-inv-owned", None),
    ("owner invitation", "/api/invitations/parity-r-inv-owned", "owner"),
    ("collaborator invitation", "/api/invitations/parity-r-inv-shared", "content"),
    ("stranger invitation", "/api/invitations/parity-r-inv-owned", "stranger"),
    ("deleted invitation", "/api/invitations/parity-r-inv-deleted", "owner"),
    ("missing invitation", "/api/invitations/parity-r-does-not-exist", "owner"),
    ("owner guests", "/api/invitations/parity-r-inv-owned/guests", "owner"),
    ("manager guests", "/api/invitations/parity-r-inv-owned/guests", "manager"),
    ("content guests", "/api/invitations/parity-r-inv-owned/guests", "content"),
    ("empty guests", "/api/invitations/parity-r-inv-empty/guests", "owner"),
    ("missing guests", "/api/invitations/parity-r-does-not-exist/guests", "owner"),
    ("unauth guests", "/api/invitations/parity-r-inv-owned/guests", None),
    ("owner rsvps", "/api/invitations/parity-r-inv-owned/rsvps", "owner"),
    ("manager rsvps", "/api/invitations/parity-r-inv-owned/rsvps", "manager"),
    ("content rsvps", "/api/invitations/parity-r-inv-owned/rsvps", "content"),
    ("stranger rsvps", "/api/invitations/parity-r-inv-owned/rsvps", "stranger"),
    ("owner versions", "/api/invitations/parity-r-inv-owned/versions", "owner"),
    ("collaborator versions", "/api/invitations/parity-r-inv-shared/versions", "content"),
    ("stranger versions", "/api/invitations/parity-r-inv-owned/versions", "stranger"),
    ("unauth versions", "/api/invitations/parity-r-inv-owned/versions", None),
    ("version by number", "/api/invitations/parity-r-inv-owned/versions/2", "owner"),
    ("version by publication id", "/api/invitations/parity-r-inv-owned/versions/parity-r-pub-3", "owner"),
    ("auto snapshot by id", "/api/invitations/parity-r-inv-owned/versions/parity-r-auto-1", "owner"),
    ("missing version", "/api/invitations/parity-r-inv-owned/versions/999", "owner"),
    ("unauth trash", "/api/trash", None),
    ("owner trash", "/api/trash", "owner"),
    ("stranger trash", "/api/trash", "stranger"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    if not NODE:
        raise SystemExit("node is not on PATH")

    data_dir = tempfile.mkdtemp(prefix="einvite-s10-")
    env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "EINVITE_GUEST_TOKEN_SECRET": GUEST_SECRET,
        "EINVITE_MEDIA_SIGNING_SECRET": secrets.token_urlsafe(32),
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}",
    }
    python_port, node_port = free_port(), free_port()
    python_log = Path(data_dir) / "python.log"
    node_log = Path(data_dir) / "node.log"
    processes = []
    try:
        with open(python_log, "wb") as log:
            python_process = subprocess.Popen(
                [PY, str(ROOT / "src/python/server.py"), "--host", "127.0.0.1", "--port", str(python_port)],
                env=env, stdout=log, stderr=subprocess.STDOUT,
            )
        processes.append(python_process)
        wait_health(f"http://127.0.0.1:{python_port}", python_process, python_log)

        seed(args.database_url)

        with open(node_log, "wb") as log:
            node_process = subprocess.Popen(
                [NODE, str(ROOT / "services/api-node/server.mjs")],
                env={**env, "PORT": str(node_port), "HOST": "127.0.0.1", "LOG_LEVEL": "warn"},
                stdout=log, stderr=subprocess.STDOUT,
            )
        processes.append(node_process)
        wait_health(f"http://127.0.0.1:{node_port}", node_process, node_log)

        failures = 0
        for name, path, key in CASES:
            cookie = f"einvite_session={TOKENS[key]}" if key else None
            python_status, python_body = get(f"http://127.0.0.1:{python_port}", path, cookie)
            node_status, node_body = get(f"http://127.0.0.1:{node_port}", path, cookie)
            same = python_status == node_status and python_body == node_body
            print(f"{'ok  ' if same else 'DIFF'} {name}: python={python_status} node={node_status}")
            if not same:
                failures += 1
                print("  python:", json.dumps(python_body, sort_keys=True)[:900])
                print("  node:  ", json.dumps(node_body, sort_keys=True)[:900])
        print(f"\nINVITATION READ PARITY {len(CASES) - failures}/{len(CASES)} identical, {failures} failing")
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
