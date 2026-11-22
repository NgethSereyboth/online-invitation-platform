#!/usr/bin/env python3
"""S6 proof: one session row, two backends, identical answers.

Starts the Python backend and the Node service against the *same* PostgreSQL
database, then checks that a session created once authenticates on both, that a
bad CSRF token is rejected identically, and that state written by one side is
read by the other.

Usage:
    python3 tools/session-parity.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / ".venv" / "bin" / "python")
TOKEN = "parity-session-token-0123456789abcdef"
CSRF = "parity-csrf-token-0123456789abcdef"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def http(method: str, url: str, cookie: str = "", headers: dict[str, str] | None = None):
    request = urllib.request.Request(url, method=method, headers={**(headers or {})})
    if cookie:
        request.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def wait_for(url: str, label: str, attempts: int = 60) -> None:
    for _ in range(attempts):
        try:
            status, _, _ = http("GET", url)
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit(f"{label} did not become ready at {url}")


def apply_schema(database_url: str) -> None:
    import psycopg

    schema = (REPO / "docs" / "postgres_schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema)
            # Columns server.py adds at boot but the schema file omits
            # (defect #25): email_hash (server.py:2018) and suspended_at (1999).
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_hash TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_at INTEGER")


def seed(database_url: str) -> None:
    import psycopg

    now = int(time.time() * 1000)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sessions WHERE id LIKE 's6-%'")
            cursor.execute("DELETE FROM users WHERE id LIKE 'u-s6-%'")
            cursor.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role,email_verified) "
                "VALUES('u-s6','s6@example.com',%s,'hash','salt',%s,'customer',1)",
                (sha256("s6@example.com"), now),
            )
            cursor.execute(
                "INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,last_seen_at,csrf_hash) "
                "VALUES(%s,'s6-1','u-s6',%s,%s,%s,%s)",
                (sha256(TOKEN), now + 86_400_000, now, now, sha256(CSRF)),
            )


def node_hash(value: str) -> str:
    script = (
        "import {hashToken} from './lib/session.mjs';"
        "process.stdout.write(hashToken(process.argv[1]));"
    )
    return subprocess.run(
        ["node", "--input-type=module", "-e", script, value],
        cwd=REPO / "services" / "api-node",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--python-port", type=int, default=8911)
    parser.add_argument("--node-port", type=int, default=8912)
    args = parser.parse_args()

    apply_schema(args.database_url)
    seed(args.database_url)

    data_dir = tempfile.mkdtemp(prefix="einvite-s6-")
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": f"{REPO / 'src' / 'python'}:{REPO}",
            "EINVITE_DATA_DIR": data_dir,
            "EINVITE_DATABASE_URL": args.database_url,
        }
    )
    python_log = open(Path(data_dir) / "python.log", "w", encoding="utf-8")
    node_log = open(Path(data_dir) / "node.log", "w", encoding="utf-8")
    python_server = subprocess.Popen(
        [PY, "src/python/server.py", "--host", "127.0.0.1", "--port", str(args.python_port)],
        cwd=REPO,
        env=env,
        stdout=python_log,
        stderr=subprocess.STDOUT,
    )
    node_env = dict(os.environ)
    node_env.update(
        {
            "PORT": str(args.node_port),
            "HOST": "127.0.0.1",
            "EINVITE_DATABASE_URL": args.database_url,
            "EINVITE_DATA_DIR": data_dir,
            "LOG_LEVEL": "warn",
        }
    )
    node_server = subprocess.Popen(
        ["node", "server.mjs"],
        cwd=REPO / "services" / "api-node",
        env=node_env,
        stdout=node_log,
        stderr=subprocess.STDOUT,
    )

    checks = failures = 0

    def check(label, actual, expected):
        nonlocal checks, failures
        checks += 1
        if actual == expected:
            return
        failures += 1
        print(f"FAIL {label}\n     expected={expected!r}\n     actual  ={actual!r}")

    try:
        py_base = f"http://127.0.0.1:{args.python_port}"
        nd_base = f"http://127.0.0.1:{args.node_port}"
        wait_for(f"{py_base}/api/health", "python")
        wait_for(f"{nd_base}/healthz", "node")

        cookie = f"einvite_session={TOKEN}; einvite_csrf={CSRF}"

        # 1. One session row authenticates on both backends.
        py_status, _, py_body = http("GET", f"{py_base}/api/auth/me", cookie)
        nd_status, _, nd_body = http("GET", f"{nd_base}/api/auth/me", cookie)
        py_user = json.loads(py_body)["user"]
        nd_user = json.loads(nd_body)["user"]
        check("python accepts the session", (py_status, py_user and py_user["id"]), (200, "u-s6"))
        check("node accepts the same session", (nd_status, nd_user and nd_user["id"]), (200, "u-s6"))
        check("same keys", sorted(py_user), sorted(nd_user))
        for field in ("email", "role", "plan", "email_verified"):
            check(f"same {field}", nd_user.get(field), py_user.get(field))

        # 2. An unknown cookie is not a user on either side.
        check(
            "unknown cookie on python",
            json.loads(http("GET", f"{py_base}/api/auth/me", "einvite_session=nope")[2])["user"],
            None,
        )
        check(
            "unknown cookie on node",
            json.loads(http("GET", f"{nd_base}/api/auth/me", "einvite_session=nope")[2])["user"],
            None,
        )

        # 3. CSRF: a header that does not match the cookie is rejected identically.
        origin_py = {"Origin": py_base}
        origin_nd = {"Origin": nd_base}
        bad = {"X-CSRF-Token": "wrong-token", **origin_py}
        py_status, _, py_body = http("POST", f"{py_base}/api/auth/logout", cookie, bad)
        _, _, nd_body = http("POST", f"{nd_base}/api/auth/logout", cookie, {**bad, **origin_nd})
        check("csrf mismatch status", py_status, 403)
        check("csrf mismatch body", json.loads(nd_body), json.loads(py_body))

        # 4. A cookie-matching but unbound token is csrf_invalid on both.
        unbound = {"X-CSRF-Token": "not-the-session-token", **origin_py}
        unbound_cookie = "einvite_session=" + TOKEN + "; einvite_csrf=not-the-session-token"
        py_status, _, py_body = http("POST", f"{py_base}/api/auth/logout", unbound_cookie, unbound)
        _, _, nd_body = http("POST", f"{nd_base}/api/auth/logout", unbound_cookie, {**unbound, **origin_nd})
        check("unbound csrf status", py_status, 403)
        check("unbound csrf body", json.loads(nd_body), json.loads(py_body))

        # 5. The rejections did not destroy the session.
        check(
            "session survives csrf rejections",
            json.loads(http("GET", f"{nd_base}/api/auth/me", cookie)[2])["user"]["id"],
            "u-s6",
        )

        # 6. A correct token signs out on both.
        good = {"X-CSRF-Token": CSRF, **origin_py}
        py_status, _, py_body = http("POST", f"{py_base}/api/auth/logout", cookie, good)
        check("python logout", (py_status, json.loads(py_body)), (200, {"signedOut": True}))
        check("session gone after logout", json.loads(http("GET", f"{py_base}/api/auth/me", cookie)[2])["user"], None)

        # 7. State written with the Node implementation's hashing is read by Python.
        py_status, _, py_body = http("GET", f"{py_base}/api/auth/me", cookie)
        seed_token, seed_csrf = "node-written-token", "node-written-csrf"
        import psycopg

        now = int(time.time() * 1000)
        with psycopg.connect(args.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,last_seen_at,csrf_hash) "
                    "VALUES(%s,'s6-2','u-s6',%s,%s,%s,%s)",
                    (node_hash(seed_token), now + 3_600_000, now, now, node_hash(seed_csrf)),
                )
        written = f"einvite_session={seed_token}"
        check(
            "python reads a session hashed by the Node implementation",
            json.loads(http("GET", f"{py_base}/api/auth/me", written)[2])["user"]["id"],
            "u-s6",
        )
        check(
            "node reads it too",
            json.loads(http("GET", f"{nd_base}/api/auth/me", written)[2])["user"]["id"],
            "u-s6",
        )

        print(f"\nSESSION PARITY {checks - failures}/{checks} identical, {failures} failing")
        return 0 if failures == 0 else 1
    except Exception:
        print("--- python log ---")
        print(Path(data_dir, "python.log").read_text(encoding="utf-8")[-2500:])
        print("--- node log ---")
        print(Path(data_dir, "node.log").read_text(encoding="utf-8")[-2500:])
        raise
    finally:
        python_server.terminate()
        node_server.terminate()
        for process in (python_server, node_server):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
