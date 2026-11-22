#!/usr/bin/env python3
"""S4 query parity: the same fixtures through core.db (SQLite) and the Node
service (PostgreSQL), compared field by field including value types.

Usage:
    python3 tools/db-parity.py --database-url postgres://postgres:...@127.0.0.1:55432/einvite
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src" / "python"))

from core.crypto import hash_for_lookup  # noqa: E402
from core.db import find_user_by_email  # noqa: E402

EMAILS = [
    "alice@example.com",
    "  ALICE@Example.com  ",
    "legacy@example.com",
    "other@example.com",
    "nobody@example.com",
    "",
    None,
]

USERS = [
    ("u-parity-alice", "Alice@Example.com", hash_for_lookup("alice@example.com"),
     1700000000123, 1, 2, 1234567890123),
    ("u-parity-legacy", "Legacy@Example.com", "", 1700000000000, 0, 0, 0),
    ("u-parity-other", "Other@Example.com", hash_for_lookup("other@example.com"),
     1700000000999, 1, 0, 7),
]

SCHEMA = """
CREATE TABLE users(
  id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, email_hash TEXT DEFAULT '',
  password_hash TEXT NOT NULL, salt TEXT NOT NULL, created_at BIGINT NOT NULL,
  email_verified INTEGER NOT NULL DEFAULT 0, failed_login_attempts INTEGER NOT NULL DEFAULT 0,
  storage_used_bytes BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE invitations(
  id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, draft_json TEXT NOT NULL,
  updated_at BIGINT NOT NULL, owner_id TEXT
);
CREATE TABLE guests(
  id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL,
  slug TEXT NOT NULL DEFAULT '', token TEXT NOT NULL, created_at BIGINT NOT NULL
);
"""


def project(row):
    if row is None:
        return None
    data = dict(row) if not isinstance(row, dict) else row
    return {
        "id": data["id"],
        "email": data["email"],
        "created_at": data["created_at"],
        "created_at_type": type(data["created_at"]).__name__.replace("int", "number"),
        "email_verified": data["email_verified"],
        "failed_login_attempts": data["failed_login_attempts"],
        "storage_used_bytes": data["storage_used_bytes"],
    }


def python_side() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        connection = sqlite3.connect(Path(tmp) / "invites.db")
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        for user in USERS:
            connection.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,"
                "email_verified,failed_login_attempts,storage_used_bytes) "
                "VALUES(?,?,?,'hash','salt',?,?,?,?)",
                user,
            )
        connection.execute(
            "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id) "
            "VALUES('inv-parity','inv-parity','{}',1,NULL)"
        )
        connection.execute(
            "INSERT INTO guests(id,invitation_id,name,slug,token,created_at) "
            "VALUES('g-parity','inv-parity','Guest One','g-one','tok-g-one',1700000000000)"
        )
        users = {str(email): project(find_user_by_email(connection, email)) for email in EMAILS}
        guest = connection.execute(
            "SELECT name FROM guests WHERE invitation_id=? AND slug=?", ("inv-parity", "g-one")
        ).fetchone()
        missing = connection.execute(
            "SELECT name FROM guests WHERE invitation_id=? AND slug=?", ("inv-parity", "nope")
        ).fetchone()
        return {
            "users": users,
            "guest": guest["name"] if guest else None,
            "missingGuest": missing["name"] if missing else None,
        }


def simulate_python_boot(database_url: str) -> None:
    """Apply the column Python adds at boot but the schema file omits.

    ``docs/postgres_schema.sql`` has no ``users.email_hash``; server.py:2018
    runs ``ALTER TABLE users ADD COLUMN email_hash TEXT`` when it boots. A
    fresh PostgreSQL instance is therefore *not* the schema the queries expect
    until the Python backend has started once. The harness reproduces that boot
    step so the fixture matches a deployed database — the Node service must
    never perform it itself.
    """
    import psycopg

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_hash TEXT")


def node_side(database_url: str) -> dict:
    output = subprocess.run(
        ["node", "bin/parity-check.mjs", database_url],
        cwd=REPO / "services" / "api-node",
        capture_output=True,
        text=True,
        check=False,
    )
    if output.returncode != 0:
        raise SystemExit(f"node parity check failed:\n{output.stderr}")
    return json.loads(output.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    simulate_python_boot(args.database_url)
    python_result = python_side()
    node_result = node_side(args.database_url)

    failures = 0
    for key in python_result["users"]:
        if python_result["users"][key] != node_result["users"].get(key):
            failures += 1
            print(f"FAIL user {key!r}")
            print(f"     python={python_result['users'][key]}")
            print(f"     node  ={node_result['users'].get(key)}")
    for key in ("guest", "missingGuest"):
        if python_result[key] != node_result[key]:
            failures += 1
            print(f"FAIL {key}: python={python_result[key]!r} node={node_result[key]!r}")

    cases = len(python_result["users"]) + 2
    print(f"\nDB PARITY {cases - failures}/{cases} identical, {failures} failing")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
