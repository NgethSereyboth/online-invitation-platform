"""Migrate E-invitation-website data from the local SQLite database to PostgreSQL.

Requires the optional production dependency:
    pip install -r requirements-production.txt

Example:
    python migrate_sqlite_to_postgres.py --database-url "$DATABASE_URL"

The application can run directly on PostgreSQL when EINVITE_DATABASE_URL is configured.
This utility transfers an existing SQLite dataset before switching the runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path



def platform_env(name, default=None):
    """Read the current EINVITE_* setting, with legacy SOVAN_* fallback."""
    legacy = name.replace("EINVITE_", "SOVAN_", 1)
    return os.environ.get(name, os.environ.get(legacy, default))

ROOT = Path(__file__).resolve().parent
DEFAULT_SQLITE = Path(platform_env("EINVITE_DATA_DIR", ROOT / "data")) / "invites.db"
TABLES = [
    "users", "sessions", "invitations", "publications", "rsvps", "assets", "guests",
    "user_templates", "template_versions", "user_page_templates", "view_events",
    "access_tokens", "user_components", "guest_messages", "auth_tokens", "invitation_collaborators",
]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default=str(DEFAULT_SQLITE))
    parser.add_argument("--database-url", default=platform_env("EINVITE_DATABASE_URL", os.environ.get("DATABASE_URL", "")))
    parser.add_argument("--replace", action="store_true", help="Delete destination rows before import")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("psycopg is required. Run: pip install -r requirements-production.txt") from exc

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")
    schema = (ROOT / "postgres_schema.sql").read_text(encoding="utf-8")
    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    with psycopg.connect(args.database_url) as target:
        with target.cursor() as cur:
            cur.execute(schema)
            if args.replace:
                cur.execute("TRUNCATE TABLE invitation_collaborators, auth_tokens, guest_messages, user_components, access_tokens, view_events, user_page_templates, template_versions, user_templates, guests, assets, rsvps, publications, invitations, sessions, users CASCADE")
            for table in TABLES:
                exists = source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                if not exists:
                    print(f"skip {table}: not present")
                    continue
                rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
                if not rows:
                    print(f"{table}: 0")
                    continue
                columns = list(rows[0].keys())
                placeholders = ",".join(["%s"] * len(columns))
                column_sql = ",".join(f'"{name}"' for name in columns)
                sql = f'INSERT INTO "{table}" ({column_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
                count = 0
                for row in rows:
                    values = []
                    for column in columns:
                        values.append(row[column])
                    cur.execute(sql, values)
                    count += 1
                print(f"{table}: {count}")
        target.commit()
    source.close()
    print("PostgreSQL migration completed.")


if __name__ == "__main__":
    main()
