#!/usr/bin/env python3
"""S7 proof: the public invitation read path answers identically on both backends.

One PostgreSQL database, seeded once, is served by Python and by the Node
service; each request is sent to both and the parsed JSON is compared after
normalising the short-lived media signatures (their expiry is wall-clock, so a
byte compare would be flaky — the signatures themselves are verified against the
shared signing secret instead).

Usage:
  .venv/bin/python tools/public-parity.py --database-url postgres://...
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "bin" / "python")
NODE = shutil.which("node")
SECRET = "s7-parity-media-secret-0123456789"
SLUG = "parity-s7"
MEDIA = re.compile(r"/api/media/([^?\"'\s]+)\?i=([^&]+)&exp=(\d+)&sig=([0-9a-f]{64})")


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


def get(base: str, path: str, headers: dict[str, str] | None = None):
    request = urllib.request.Request(f"{base}{path}", headers=headers or {})
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
    document = {
        "privacy": {"analyticsConsentRequired": False, "externalMediaConsentRequired": True},
        "galleryProtection": {"enabled": True},
        "objects": {
            "hero": {"type": "image", "src": "/uploads/hero.png", "showInGallery": True, "showInHero": True},
            "gallery": {
                "type": "image",
                "src": "/uploads/gallery-only.png",
                "showInGallery": True,
                "showInHero": False,
            },
            "greeting": {
                "type": "text",
                "html": "Hello {{ name }}",
                "contentBinding": "guest.name",
            },
        },
        "designPages": [{"objects": {"seating": {"type": "text", "text": "Table {{ table_name }}", "contentBinding": "guest.table_name"}}}],
    }
    consent_document = {
        "privacy": {"analyticsConsentRequired": True},
        "objects": {},
    }
    # No gallery protection at all: apply_gallery_access must early-return rather
    # than add a `locked` field, which is a separate branch from "locked".
    plain_document = {
        "privacy": {"externalMediaConsentRequired": True},
        "objects": {"hero": {"type": "image", "src": "/uploads/hero.png", "showInGallery": True, "showInHero": True}},
    }
    with psycopg.connect(database_url) as connection:
        # Tokens and view events are not cascade children of invitations, so a
        # second run must clear them explicitly or their primary keys collide.
        for table in ("access_tokens", "gallery_access_tokens", "view_events"):
            connection.execute(f"DELETE FROM {table} WHERE invitation_id LIKE %s", ("parity-s7-inv-%",))
        connection.execute("DELETE FROM invitations WHERE slug LIKE %s", (f"{SLUG}%",))
        connection.execute("DELETE FROM users WHERE id LIKE %s", ("parity-s7-%",))
        connection.execute(
            "INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,role,studio_name,white_label_json) "
            "VALUES(%s,%s,%s,%s,%s,%s,'customer',%s,%s)",
            (
                "parity-s7-user",
                "parity-s7@example.test",
                sha256("parity-s7@example.test"),
                "x",
                "y",
                now,
                "Studio Parity",
                json.dumps({"logo": "/uploads/logo.png", "primaryColor": "#123456", "hidePlatformBrand": True}),
            ),
        )
        fixtures = [
            (f"{SLUG}-plain", "unlisted", plain_document),
            (f"{SLUG}-gallery", "unlisted", document),
            (f"{SLUG}-consent", "unlisted", consent_document),
            (f"{SLUG}-password", "password", document),
        ]
        for index, (slug, access_mode, doc) in enumerate(fixtures):
            invitation_id = f"parity-s7-inv-{index}"
            connection.execute(
                "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,views,access_mode,"
                "access_password_hash,access_password_salt,is_published,sent_at,edited_after_send_at,"
                "gallery_access_password_hash,gallery_access_password_salt,deleted_at) "
                "VALUES(%s,%s,'{}',%s,'parity-s7-user',0,0,%s,'x','y',1,%s,%s,%s,'y',NULL)",
                (
                    invitation_id,
                    slug,
                    now,
                    access_mode,
                    now - 60_000,
                    now - 30_000,
                    "hash" if access_mode == "password" else None,
                ),
            )
            connection.execute(
                "INSERT INTO publications(id,invitation_id,version,document_json,published_at) "
                "VALUES(%s,%s,1,%s,%s)",
                (f"parity-s7-pub-{index}", invitation_id, json.dumps(doc), now),
            )
            for guest_index, (name, table) in enumerate((("Ada Lovelace", "Table 1"), ("Grace Hopper", "Table 2"))):
                token = f"parity-s7-guest-{index}-{guest_index}"
                code = f"parity-s7-code-{index}-{guest_index}"
                connection.execute(
                    "INSERT INTO guests(id,invitation_id,name,phone,token,token_hash,token_salt,token_version,"
                    "created_at,checked_in,slug,table_name,token_revoked_at) "
                    "VALUES(%s,%s,%s,NULL,%s,%s,'',1,%s,0,%s,%s,NULL)",
                    (
                        f"parity-s7-guest-row-{index}-{guest_index}",
                        invitation_id,
                        name,
                        code,
                        sha256(token),
                        now,
                        f"guest-{guest_index}",
                        table,
                    ),
                )
        connection.execute(
            "INSERT INTO access_tokens(token_hash,invitation_id,expires_at,created_at) VALUES(%s,%s,%s,%s)",
            (sha256("parity-s7-access"), "parity-s7-inv-3", now + 3_600_000, now),
        )
        connection.execute(
            "INSERT INTO gallery_access_tokens(token_hash,invitation_id,expires_at,created_at) VALUES(%s,%s,%s,%s)",
            (sha256("parity-s7-gallery"), "parity-s7-inv-1", now + 3_600_000, now),
        )
        connection.commit()


def normalize(value):
    """Replace expiry/signature with a verified marker so clocks do not matter."""
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if not isinstance(value, str):
        return value
    def replace(match):
        name, invitation_id, expires, signature = match.groups()
        payload = f"{urllib.parse.unquote(name)}|{urllib.parse.unquote(invitation_id)}|{int(expires)}"
        expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return match.group(0) + "!BADSIG"
        return f"/api/media/{name}?i={invitation_id}&exp=<exp>&sig=<valid>"
    return MEDIA.sub(replace, value)


CASES = [
    ("missing", "/api/public/does-not-exist", {}),
    ("empty slug", "/api/public/", {}),
    ("plain", f"/api/public/{SLUG}-plain", {}),
    ("gallery locked", f"/api/public/{SLUG}-gallery", {}),
    ("gallery unlocked", f"/api/public/{SLUG}-gallery", {"X-Gallery-Access": "parity-s7-gallery"}),
    (
        "guest binding",
        f"/api/public/{SLUG}-gallery",
        {"X-Invitation-Guest": "parity-s7-guest-1-0", "X-Gallery-Access": "parity-s7-gallery"},
    ),
    ("consent flags", f"/api/public/{SLUG}-consent", {}),
    ("password required", f"/api/public/{SLUG}-password", {}),
    ("password accepted", f"/api/public/{SLUG}-password?access=parity-s7-access", {}),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    if not NODE:
        raise SystemExit("node is not on PATH")

    data_dir = tempfile.mkdtemp(prefix="einvite-s7-")
    env = {
        **os.environ,
        "EINVITE_DATABASE_URL": args.database_url,
        "EINVITE_DATA_DIR": data_dir,
        "EINVITE_MEDIA_SIGNING_SECRET": SECRET,
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
        for name, path, headers in CASES:
            python_status, python_body = get(f"http://127.0.0.1:{python_port}", path, headers)
            node_status, node_body = get(f"http://127.0.0.1:{node_port}", path, headers)
            same = python_status == node_status and normalize(python_body) == normalize(node_body)
            print(f"{'ok  ' if same else 'DIFF'} {name}: python={python_status} node={node_status}")
            if not same:
                failures += 1
                print("  python:", json.dumps(python_body, sort_keys=True)[:600])
                print("  node:  ", json.dumps(node_body, sort_keys=True)[:600])
        print(f"\nPUBLIC PARITY {len(CASES) - failures}/{len(CASES)} identical, {failures} failing")
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
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    raise SystemExit(main())
