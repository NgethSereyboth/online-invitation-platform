#!/usr/bin/env python3
"""Encrypt sensitive columns at rest (ROADMAP-v0.54-to-v1.0 §4.1).

Migrates ``users.email``, ``guests.email``, ``guests.phone``,
``delivery_attempts.recipient``, ``audit_events.metadata_json`` and
``invitation_edit_history.diff_json`` to Fernet-encrypted ciphertexts. For
``users.email`` and ``guests.email`` it also writes a SHA-256 ``email_hash``
column so login-by-email stays an indexed O(1) lookup.

Modes:
  * default — encrypt every plaintext row in place, after backing up the
    pre-migration table to ``<table>_plaintext_backup`` (kept 30 days).
  * ``--rollback`` — restore from ``<table>_plaintext_backup``, decrypting
    every ciphertext back to plaintext and clearing the backup tables.

Usage:
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --rollback
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --dry-run

Environment:
    EINVITE_FIELD_ENCRYPTION_KEY — 32-byte urlsafe-base64 Fernet key. Auto-
    generated via ``features.secrets.ensure_secret`` if absent.

Exit codes:
    0 — migration completed (or rollback completed).
    1 — encryption key unavailable / DB error.
    2 — backup tables missing on rollback.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

# Make the repo-root + src/python importable when invoked as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "python"))
sys.path.insert(0, str(ROOT))

from core.crypto import (  # noqa: E402
    CIPHERTEXT_PREFIX,
    decrypt_field,
    email_hash,
    ensure_encryption_key,
    encrypt_field,
    is_encryption_active,
)


# (table, column, needs_email_hash) tuples for every column we encrypt.
SENSITIVE_COLUMNS = [
    ("users", "email", True),
    ("guests", "email", True),
    ("guests", "phone", False),
    ("delivery_attempts", "recipient", False),
    ("audit_events", "metadata_json", False),
    ("invitation_edit_history", "diff_json", False),
]

BACKUP_SUFFIX = "_plaintext_backup"
BACKUP_RETENTION_DAYS = 30


def _connect(db_path: Path):
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    return db


def _backup_table(db, table: str):
    """Copy ``table`` to ``table + '_plaintext_backup'`` (drop old backup first)."""
    backup = table + BACKUP_SUFFIX
    db.execute(f"DROP TABLE IF EXISTS {backup}")
    db.execute(f"CREATE TABLE {backup} AS SELECT * FROM {table}")
    db.commit()


def _table_exists(db, table: str) -> bool:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchall()
    return bool(rows)


def _column_exists(db, table: str, column: str) -> bool:
    if not _table_exists(db, table):
        return False
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _ensure_email_hash_column(db, table: str):
    if not _column_exists(db, table, "email_hash"):
        db.execute(f"ALTER TABLE {table} ADD COLUMN email_hash TEXT NOT NULL DEFAULT ''")
        try:
            db.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_email_hash "
                f"ON {table}(email_hash) WHERE email_hash <> ''"
            )
        except sqlite3.OperationalError:
            pass  # index creation may fail on Postgres-backed dev paths
        db.commit()


def _encrypt_rows(db, table: str, column: str, with_email_hash: bool, dry_run: bool):
    if not _column_exists(db, table, column):
        print(f"  [skip] {table}.{column} does not exist")
        return 0
    if with_email_hash:
        _ensure_email_hash_column(db, table)
    rows = db.execute(f"SELECT rowid AS rid, {column} AS val FROM {table}").fetchall()
    changed = 0
    for r in rows:
        val = r["val"]
        if val is None:
            continue
        if isinstance(val, str) and val.startswith(CIPHERTEXT_PREFIX):
            continue  # already encrypted
        if dry_run:
            changed += 1
            continue
        enc = encrypt_field(val)
        db.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?", (enc, r["rid"]))
        if with_email_hash and column == "email":
            db.execute(
                f"UPDATE {table} SET email_hash=? WHERE rowid=?",
                (email_hash(val) or "", r["rid"]),
            )
        changed += 1
    db.commit()
    return changed


def _decrypt_rows(db, table: str, column: str, dry_run: bool):
    if not _column_exists(db, table, column):
        return 0
    rows = db.execute(f"SELECT rowid AS rid, {column} AS val FROM {table}").fetchall()
    changed = 0
    for r in rows:
        val = r["val"]
        if val is None:
            continue
        if not (isinstance(val, str) and val.startswith(CIPHERTEXT_PREFIX)):
            continue  # already plaintext
        if dry_run:
            changed += 1
            continue
        plain = decrypt_field(val)
        db.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?", (plain, r["rid"]))
        changed += 1
    db.commit()
    return changed


def _restore_from_backup(db, table: str, dry_run: bool):
    backup = table + BACKUP_SUFFIX
    if not _table_exists(db, backup):
        return False
    if dry_run:
        return True
    # Replace the live table with the backup (plaintext) contents.
    cols = [r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    backup_cols = [r["name"] for r in db.execute(f"PRAGMA table_info({backup})").fetchall()]
    common = [c for c in cols if c in backup_cols]
    col_list = ",".join(common)
    db.execute(f"DELETE FROM {table}")
    db.execute(f"INSERT INTO {table}({col_list}) SELECT {col_list} FROM {backup}")
    db.execute(f"DROP TABLE {backup}")
    db.commit()
    return True


def migrate(db_path: Path, dry_run: bool) -> int:
    ensure_encryption_key()
    if not is_encryption_active():
        print("ERROR: field encryption key unavailable.", file=sys.stderr)
        return 1
    db = _connect(db_path)
    try:
        for table, column, needs_hash in SENSITIVE_COLUMNS:
            if not _column_exists(db, table, column):
                print(f"  [skip] {table}.{column} does not exist")
                continue
            if not dry_run:
                _backup_table(db, table)
            n = _encrypt_rows(db, table, column, needs_hash, dry_run)
            print(f"  {table}.{column}: encrypted {n} row(s)")
    finally:
        db.close()
    return 0


def rollback(db_path: Path, dry_run: bool) -> int:
    db = _connect(db_path)
    try:
        missing = []
        restored = set()
        for table, column, _ in SENSITIVE_COLUMNS:
            if table in restored:
                continue  # multi-column tables already restored as a unit
            backup = table + BACKUP_SUFFIX
            if not _table_exists(db, backup):
                missing.append(backup)
                continue
            if not dry_run:
                ok = _restore_from_backup(db, table, dry_run)
                if not ok:
                    missing.append(backup)
                    continue
                # Also clear the email_hash we wrote so the schema is clean.
                if _column_exists(db, table, "email_hash") and column == "email":
                    db.execute(f"UPDATE {table} SET email_hash=''")
                    db.commit()
                restored.add(table)
            print(f"  {table}: restored from {backup}")
        if missing:
            print("WARNING: missing backups for: " + ", ".join(missing))
            if all(b in missing for b in [t + BACKUP_SUFFIX for t, _, _ in SENSITIVE_COLUMNS]):
                return 2
    finally:
        db.close()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollback", action="store_true", help="decrypt back to plaintext from backup tables")
    parser.add_argument("--dry-run", action="store_true", help="report what would change without writing")
    parser.add_argument("--data-dir", default=os.environ.get("EINVITE_DATA_DIR", str(ROOT / "src" / "python" / "data")))
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir).expanduser().resolve()
    db_path = data_dir / "invites.db"
    if not db_path.is_file():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        return 1

    print(f"EINVITE_FIELD_ENCRYPTION_KEY={'set' if os.environ.get('EINVITE_FIELD_ENCRYPTION_KEY') else 'auto-generate'}")
    print(f"DB: {db_path}")
    print(f"Mode: {'rollback' if args.rollback else 'encrypt'} {'(dry-run)' if args.dry_run else ''}")
    start = time.time()
    if args.rollback:
        rc = rollback(db_path, args.dry_run)
    else:
        rc = migrate(db_path, args.dry_run)
    print(f"Done in {time.time() - start:.2f}s (rc={rc})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
