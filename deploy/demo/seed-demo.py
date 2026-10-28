#!/usr/bin/env python3
"""Seed the hosted demo with one account and three invitations (A-4, D-16).

The demo host may have an ephemeral disk, so this script runs on every boot;
it is **idempotent** and does nothing once its rows exist. It is deliberately
small and self-contained:

* it uses the application's own schema, password hashing, document validators
  and personal-workspace helper (imported from ``src/python``), so the seeded
  rows are exactly the rows the server writes;
* it reads the three designs from the tracked template pack
  (``assets/template-pack/built/<id>.js``) and changes one thing: the pack ships
  RSVP off, and the demo needs to accept one RSVP, so the seeded copy enables it;
* it reads nothing from ``artifacts/`` — a clean checkout does not have it;
* it never touches ``data/`` unless that is the directory it is pointed at.

Usage (from the repository root):

    EINVITE_DATA_DIR=/path/to/demo-data \\
    EINVITE_DEMO_PASSWORD='...' \\
    python deploy/demo/seed-demo.py

``EINVITE_DEMO_EMAIL`` overrides the account address (default
``demo@einvite.test``). The password is read from the environment only and is
never printed, logged or written to the database in clear text.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_SRC = REPO_ROOT / "src" / "python"
# ``src/python`` must win: the repository root has its own ``server.py`` launcher,
# and importing that one would start the application instead of exposing helpers.
sys.path.insert(0, str(PYTHON_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

DEMO_EMAIL = os.environ.get("EINVITE_DEMO_EMAIL", "demo@einvite.test").strip().lower()
DEMO_TEMPLATES = ("wd-royal-maroon-gold", "bd-first-pastel", "biz-corporate-gala")


def built_document(template_id: str) -> dict:
    """Return a template pack document with RSVP enabled for the demo."""
    path = REPO_ROOT / "assets" / "template-pack" / "built" / f"{template_id}.js"
    raw = path.read_text(encoding="utf-8")
    prefix = "export default "
    if not raw.startswith(prefix):
        raise SystemExit(f"unexpected template module shape: {path}")
    payload = json.loads(raw[len(prefix):].rstrip().rstrip(";"))
    document = payload.get("document")
    if not isinstance(document, dict):
        raise SystemExit(f"template module has no document: {path}")
    settings = document.get("settings")
    if not isinstance(settings, dict):
        settings = document["settings"] = {}
    settings["rsvpEnabled"] = True
    return document


def main() -> int:
    password = os.environ.get("EINVITE_DEMO_PASSWORD", "")
    if len(password) < 8:
        sys.exit("EINVITE_DEMO_PASSWORD (8+ characters) is required; it is never printed.")

    # Imported here so the script's --help-style failures happen before the app's
    # heavier module graph loads, and so a missing data dir is reported by the app.
    import server
    from core.auth import hash_password
    from core.crypto import hash_for_lookup
    from core.db import find_user_by_email, protect
    from platform_v32 import ensure_personal_workspace

    with server.connect():
        pass  # one schema pass, exactly what the first request does
    with server.connect() as db:
        existing = find_user_by_email(db, DEMO_EMAIL)
        if existing:
            user_id = existing["id"]
            db.execute("UPDATE users SET email_verified=1 WHERE id=?", (user_id,))
            print(f"demo user: {DEMO_EMAIL} (present)")
        else:
            user_id = str(uuid.uuid4())
            hashed, salt, algo = hash_password(password)
            db.execute(
                "INSERT INTO users(id,email,email_hash,password_hash,salt,password_algo,created_at,role,email_verified,plan) "
                "VALUES(?,?,?,?,?,?,?,'customer',1,'free')",
                (user_id, protect(DEMO_EMAIL), hash_for_lookup(DEMO_EMAIL), hashed, salt, algo, int(time.time() * 1000)),
            )
            print(f"demo user: {DEMO_EMAIL} (created)")
    ensure_personal_workspace(server.connect, user_id)

    with server.connect() as db:
        workspace_id = db.execute(
            "SELECT workspace_id FROM workspace_memberships WHERE user_id=? AND status='active' LIMIT 1", (user_id,)
        ).fetchone()["workspace_id"]

    created = 0
    for template_id in DEMO_TEMPLATES:
        slug = f"demo-{template_id}"[:120]
        document = server.validate_document(built_document(template_id))
        now = int(time.time() * 1000)
        with server.connect() as db:
            if db.execute("SELECT 1 FROM invitations WHERE slug=?", (slug,)).fetchone():
                print(f"invitation: {slug} (present)")
                continue
            invite_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,workspace_id,access_mode,is_published,document_epoch,document_version) "
                "VALUES(?,?,?,?,?,?,'unlisted',1,1,1)",
                (invite_id, slug, json.dumps(document, ensure_ascii=False), now, user_id, workspace_id),
            )
            db.execute(
                "INSERT INTO publications(id,invitation_id,version,document_json,published_at) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), invite_id, now, json.dumps(document, ensure_ascii=False), now),
            )
        created += 1
        print(f"invitation: {slug} (created)")

    print(f"SEED_OK invitations_created={created} templates={len(DEMO_TEMPLATES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
