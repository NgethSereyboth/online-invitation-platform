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
  * ``--reencrypt`` — rotation pass: rewrite rows the active key cannot read
    but ``EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS`` can (see
    ``docs/ops/SECRETS-ROTATION.md``). No plaintext ever touches disk; run it
    while both keys are set, then remove the previous one.

Usage:
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --rollback
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --dry-run
    PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --reencrypt

Environment:
    EINVITE_FIELD_ENCRYPTION_KEY — 32-byte urlsafe-base64 Fernet key. Auto-
    generated via ``features.secrets.ensure_secret`` if absent.

Exit codes:
    0 — migration completed (or rollback completed).
    1 — encryption key unavailable / DB error.
    2 — backup tables missing on rollback.
    3 — refused: the target is the repo's own data directory (ROADMAP §4.1:
        the migration is run and tested against copies, never against data/).
        Pass --allow-repo-data-dir only after making your own copy.
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
    encryption_available,
    ensure_encryption_key,
    encrypt_field,
    is_current_key_ciphertext,
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


def _email_hash_index_sql(db, table: str) -> str | None:
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (f"idx_{table}_email_hash",),
    ).fetchone()
    return row["sql"] if row else None


def _email_hash_nullable(db, table: str) -> bool:
    infos = {r["name"]: r for r in db.execute(f"PRAGMA table_info({table})").fetchall()}
    info = infos.get("email_hash")
    return True if info is None else not bool(info["notnull"])


def _ensure_email_hash_column(db, table: str):
    """Add ``email_hash`` mirroring server.py's own DDL (column, name, index).

    The users index must stay UNIQUE: after encryption the plaintext
    ``UNIQUE(email)`` constraint compares ciphertexts (different on every
    encryption), so the partial unique index on the hash is what keeps accounts
    unique. server.py creates ``idx_users_email_hash ... UNIQUE ... WHERE
    email_hash IS NOT NULL`` at startup — a same-named non-unique index here
    would make that statement a silent no-op and drop the guarantee.
    """
    if not _column_exists(db, table, "email_hash"):
        db.execute(f"ALTER TABLE {table} ADD COLUMN email_hash TEXT")
        db.commit()
    unique = "UNIQUE " if table == "users" else ""
    existing = _email_hash_index_sql(db, table)
    if existing and unique and "UNIQUE" not in existing.upper():
        db.execute(f"DROP INDEX idx_{table}_email_hash")  # upgrade an older non-unique index
        existing = None
    if not existing:
        try:
            db.execute(
                f"CREATE {unique}INDEX idx_{table}_email_hash "
                f"ON {table}(email_hash) WHERE email_hash IS NOT NULL"
            )
        except sqlite3.OperationalError as exc:
            print(f"  [warn] could not create idx_{table}_email_hash: {exc}")
        db.commit()


def _email_hash_clashes(db, table: str, column: str) -> list[tuple[str, str]]:
    """Plaintext values that collide once hashed (case/whitespace variants).

    The users hash index is UNIQUE, so two legacy addresses differing only by
    case would otherwise abort mid-migration with a bare IntegrityError. Report
    them up front so the operator can merge or normalise the rows first.
    """
    values = [
        r["val"]
        for r in db.execute(f"SELECT {column} AS val FROM {table}").fetchall()
        if isinstance(r["val"], str) and r["val"] and not r["val"].startswith(CIPHERTEXT_PREFIX)
    ]
    seen: dict[str, str] = {}
    clashes: list[tuple[str, str]] = []
    for value in values:
        digest = email_hash(value) or ""
        if digest in seen and seen[digest] != value:
            clashes.append((seen[digest], value))
        seen.setdefault(digest, value)
    return clashes


def _encrypt_rows(db, table: str, column: str, with_email_hash: bool, dry_run: bool):
    if not _column_exists(db, table, column):
        print(f"  [skip] {table}.{column} does not exist")
        return 0
    if with_email_hash:
        clashes = _email_hash_clashes(db, table, column)
        if clashes:
            sample = ", ".join(f"{a!r} vs {b!r}" for a, b in clashes[:3])
            if dry_run:
                print(f"  [warn] {table}.{column}: {len(clashes)} hash collision(s) would abort a real run: {sample}")
            else:
                print(
                    f"ERROR: {table}.{column} has {len(clashes)} case/whitespace variant(s) that "
                    f"collide on the lookup hash; merge or normalise them first: {sample}",
                    file=sys.stderr,
                )
                return -1
    hash_nullable = _email_hash_nullable(db, table) if with_email_hash else False
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
        if table == "audit_events" and column == "metadata_json" and _column_exists(db, table, "admin_only"):
            # §4.1: the admin filter reads this flag instead of the encrypted JSON.
            db.execute(
                "UPDATE audit_events SET admin_only=? WHERE rowid=?",
                (1 if '"admin":true' in val else 0, r["rid"]),
            )
        if with_email_hash and column == "email":
            digest = email_hash(val) or None
            if digest is None and not hash_nullable:
                digest = ""
            db.execute(
                f"UPDATE {table} SET email_hash=? WHERE rowid=?",
                (digest, r["rid"]),
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


def _restore_from_backup(db, table: str, dry_run: bool) -> list[str] | None:
    """Replace ``table`` with its backup; return the restored column names."""
    backup = table + BACKUP_SUFFIX
    if not _table_exists(db, backup):
        return None
    cols = [r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    backup_cols = [r["name"] for r in db.execute(f"PRAGMA table_info({backup})").fetchall()]
    common = [c for c in cols if c in backup_cols]
    if dry_run:
        return common
    # Replace the live table with the backup (plaintext) contents.
    col_list = ",".join(common)
    db.execute(f"DELETE FROM {table}")
    db.execute(f"INSERT INTO {table}({col_list}) SELECT {col_list} FROM {backup}")
    db.execute(f"DROP TABLE {backup}")
    db.commit()
    return common


def migrate(db_path: Path, dry_run: bool) -> int:
    ensure_encryption_key()
    if not encryption_available():
        print("ERROR: field encryption key unavailable.", file=sys.stderr)
        return 1
    db = _connect(db_path)
    backed_up: set[str] = set()
    failed = False
    try:
        for table, column, needs_hash in SENSITIVE_COLUMNS:
            if not _column_exists(db, table, column):
                print(f"  [skip] {table}.{column} does not exist")
                continue
            # Ensure the lookup column BEFORE the backup so the backup carries
            # it too — that is what lets --rollback restore each row's real
            # pre-migration hash (NULL for legacy rows, the server's hash for
            # rows created after encryption landed) instead of clearing it.
            if needs_hash and not dry_run:
                _ensure_email_hash_column(db, table)
            # Back up each table ONCE per run: a second backup of a table that
            # already holds one encrypted column would capture ciphertext and
            # make the plaintext backup unusable for --rollback.
            if not dry_run and table not in backed_up:
                _backup_table(db, table)
                backed_up.add(table)
            n = _encrypt_rows(db, table, column, needs_hash, dry_run)
            if n < 0:
                failed = True
                print(f"  {table}.{column}: ABORTED (see error above)")
                continue
            print(f"  {table}.{column}: encrypted {n} row(s)")
    finally:
        db.close()
    return 1 if failed else 0


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
            restored.add(table)
            if not dry_run:
                common = _restore_from_backup(db, table, dry_run)
                if common is None:
                    missing.append(backup)
                    continue
                # A backup that carried email_hash already restored each row's
                # real pre-migration value. Only a backup from an older script
                # run — taken before the column existed — needs the hashes we
                # wrote cleared (NULL, matching an un-migrated row; '' would
                # collide on the users partial unique index from the second row
                # onward).
                if column == "email" and "email_hash" not in common and _column_exists(db, table, "email_hash"):
                    db.execute(
                        f"UPDATE {table} SET email_hash=?",
                        (None if _email_hash_nullable(db, table) else "",),
                    )
                    db.commit()
            print(f"  {table}: restored from {backup}")
        if missing:
            print("WARNING: missing backups for: " + ", ".join(missing))
            if all(b in missing for b in [t + BACKUP_SUFFIX for t, _, _ in SENSITIVE_COLUMNS]):
                return 2
    finally:
        db.close()
    return 0


def _reencrypt_rows(db, table: str, column: str, dry_run: bool) -> tuple[int, int]:
    """Re-encrypt rows readable only with the previous key. Returns (changed, unreadable)."""
    if not _column_exists(db, table, column):
        print(f"  [skip] {table}.{column} does not exist")
        return 0, 0
    rows = db.execute(f"SELECT rowid AS rid, {column} AS val FROM {table}").fetchall()
    changed = 0
    unreadable = 0
    for r in rows:
        val = r["val"]
        if not isinstance(val, str) or not val.startswith(CIPHERTEXT_PREFIX):
            continue
        if is_current_key_ciphertext(val):
            continue  # already under the active key
        if dry_run:
            changed += 1
            continue
        plain = decrypt_field(val)
        if plain == val:
            # Neither the active nor the previous key could read it. Leave the
            # ciphertext untouched and report it — rewriting would destroy data.
            unreadable += 1
            continue
        db.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?", (encrypt_field(plain), r["rid"]))
        if table == "audit_events" and column == "metadata_json" and _column_exists(db, table, "admin_only"):
            db.execute(
                "UPDATE audit_events SET admin_only=? WHERE rowid=?",
                (1 if '"admin":true' in plain else 0, r["rid"]),
            )
        changed += 1
    db.commit()
    return changed, unreadable


def reencrypt(db_path: Path, dry_run: bool) -> int:
    """Rotation pass: bring every ciphertext under the active key."""
    ensure_encryption_key()
    if not encryption_available():
        print("ERROR: field encryption key unavailable.", file=sys.stderr)
        return 1
    db = _connect(db_path)
    total = 0
    unreadable = 0
    try:
        for table, column, _ in SENSITIVE_COLUMNS:
            n, u = _reencrypt_rows(db, table, column, dry_run)
            total += n
            unreadable += u
            suffix = f", {u} unreadable" if u else ""
            print(f"  {table}.{column}: re-encrypted {n} row(s){suffix}")
    finally:
        db.close()
    if unreadable:
        print(
            f"ERROR: {unreadable} ciphertext(s) could not be decrypted with the active or previous key.",
            file=sys.stderr,
        )
        return 1
    print(f"  total: {total} row(s) now under the active key" + (" (dry-run)" if dry_run else ""))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollback", action="store_true", help="decrypt back to plaintext from backup tables")
    parser.add_argument("--reencrypt", action="store_true", help="rotation pass: rewrite rows still readable only with EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS")
    parser.add_argument("--dry-run", action="store_true", help="report what would change without writing")
    parser.add_argument("--data-dir", default=os.environ.get("EINVITE_DATA_DIR", str(ROOT / "src" / "python" / "data")))
    parser.add_argument(
        "--allow-repo-data-dir",
        action="store_true",
        help="permit the repo's own src/python/data directory (make a copy first)",
    )
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir).expanduser().resolve()
    if data_dir == (ROOT / "src" / "python" / "data").resolve() and not args.allow_repo_data_dir:
        print(
            "REFUSING to migrate the repo's own data directory. Copy it elsewhere and "
            "pass --data-dir, or pass --allow-repo-data-dir deliberately (ROADMAP §4.1).",
            file=sys.stderr,
        )
        return 3
    db_path = data_dir / "invites.db"
    if not db_path.is_file():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        return 1

    print(f"EINVITE_FIELD_ENCRYPTION_KEY={'set' if os.environ.get('EINVITE_FIELD_ENCRYPTION_KEY') else 'auto-generate'}")
    print(f"DB: {db_path}")
    if args.rollback and args.reencrypt:
        print("ERROR: choose one of --rollback / --reencrypt.", file=sys.stderr)
        return 1
    mode = "rollback" if args.rollback else ("reencrypt" if args.reencrypt else "encrypt")
    print(f"Mode: {mode} {'(dry-run)' if args.dry_run else ''}")
    start = time.time()
    if args.rollback:
        rc = rollback(db_path, args.dry_run)
    elif args.reencrypt:
        rc = reencrypt(db_path, args.dry_run)
    else:
        rc = migrate(db_path, args.dry_run)
    print(f"Done in {time.time() - start:.2f}s (rc={rc})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
