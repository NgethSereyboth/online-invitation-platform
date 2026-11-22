#!/usr/bin/env python3
"""Compare the SQLite runtime schema with a PostgreSQL database and emit the gap.

`docs/postgres_schema.sql` is what a PostgreSQL boot applies, but the SQLite
path also creates tables and adds columns at runtime. Nothing kept the two in
sync, so a fresh PostgreSQL database (defect #27) was missing `email_hash`,
`suspended_at`, `session_never_expires` and more — reads failed at request time
while every SQLite test passed.

This tool builds a throwaway SQLite database from the same code the server
uses, reads both schemas, and prints the missing tables/columns. `--emit-sql`
prints idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements for the
tail of `docs/postgres_schema.sql`.

Exit status: 0 when PostgreSQL has everything SQLite has, 1 when it does not.

Usage:
  .venv/bin/python tools/pg-schema-parity.py --database-url postgres://...
  .venv/bin/python tools/pg-schema-parity.py --database-url ... --emit-sql
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

# SQLite type affinity -> PostgreSQL type. Anything not listed stays TEXT,
# which is what the SQLite value already behaves like for our readers.
_TYPE_MAP = {
    "INTEGER": "BIGINT",
    "INT": "BIGINT",
    "BIGINT": "BIGINT",
    "REAL": "DOUBLE PRECISION",
    "DOUBLE": "DOUBLE PRECISION",
    "FLOAT": "DOUBLE PRECISION",
    "NUMERIC": "NUMERIC",
    "BLOB": "BYTEA",
    "TEXT": "TEXT",
}


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_for_health(port, process, log_path, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise SystemExit(f"SQLite server exited early; log:\n{pathlib.Path(log_path).read_text()[-1500:]}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.5)
    raise SystemExit(f"SQLite server did not answer in {timeout}s; log:\n{pathlib.Path(log_path).read_text()[-1500:]}")


def sqlite_schema():
    """Create a temporary SQLite database through the server's own boot path.

    The server module parses argv at import, so it is booted as a subprocess and
    the resulting database is read with sqlite3 — importing it would either run
    the CLI or need global state we do not want to fake.
    """
    tmp = tempfile.mkdtemp(prefix="einvite-schema-")
    log_path = pathlib.Path(tmp) / "server.log"
    port = _free_port()
    env = {key: value for key, value in os.environ.items() if key not in {"EINVITE_DATABASE_URL", "EINVITE_DATA_DIR"}}
    env["EINVITE_DATA_DIR"] = tmp
    env["PYTHONPATH"] = f"{ROOT / 'src' / 'python'}{os.pathsep}{ROOT}"
    try:
        with open(log_path, "wb") as log:
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "src" / "python" / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        try:
            _wait_for_health(port, process, log_path)
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
        database = pathlib.Path(tmp) / "invites.db"
        if not database.is_file():
            raise SystemExit(f"no invites.db in {tmp}")
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            tables = [
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            schema = {}
            for table in tables:
                columns = {}
                for row in connection.execute(f'PRAGMA table_info("{table}")'):
                    columns[row["name"]] = {
                        "type": row["type"] or "",
                        "notnull": bool(row["notnull"]),
                        "default": row["dflt_value"],
                        "pk": bool(row["pk"]),
                    }
                schema[table] = columns
            return schema
        finally:
            connection.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def postgres_schema(database_url):
    import psycopg
    from psycopg.rows import dict_row

    rows = {}
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        for row in connection.execute(
            "SELECT table_name, column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name, ordinal_position"
        ):
            rows.setdefault(row["table_name"], {})[row["column_name"]] = {
                "type": row["data_type"],
                "notnull": row["is_nullable"] == "NO",
                "default": row["column_default"],
            }
    return rows


def literal_default(server_type, default):
    """Translate a SQLite column default into something PostgreSQL can inline."""
    if default is None:
        return None
    text = str(default).strip()
    # SQLite keeps the parentheses around defaults, PostgreSQL does not need them.
    while text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    lowered = text.lower()
    if lowered in {"null", "true", "false"}:
        return text.upper() if lowered != "null" else None
    # Any function call (strftime, datetime, json_object...) is evaluated by the
    # application or by a trigger; a PostgreSQL ADD COLUMN cannot carry it.
    if "(" in text:
        return None
    return text


def create_table_sql(table, columns):
    parts = []
    for name, meta in columns.items():
        pg_type = _TYPE_MAP.get(meta["type"].upper().split("(")[0].strip(), "TEXT")
        piece = f"{name} {pg_type}"
        if meta["default"] is not None:
            piece += f" DEFAULT {literal_default(meta['type'], meta['default'])}"
        # A NOT NULL column with no constant default cannot be added to a table
        # that may already hold rows; keep those nullable and let the app enforce it.
        if meta["notnull"] and meta["default"] is not None:
            piece += " NOT NULL"
        parts.append(piece)
    return f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(parts)})"


def add_column_sql(table, name, meta):
    pg_type = _TYPE_MAP.get(meta["type"].upper().split("(")[0].strip(), "TEXT")
    piece = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {pg_type}"
    if meta["default"] is not None:
        piece += f" DEFAULT {literal_default(meta['type'], meta['default'])}"
    if meta["notnull"] and meta["default"] is not None:
        piece += " NOT NULL"
    return piece


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--emit-sql", action="store_true", help="print the additive DDL")
    args = parser.parse_args(argv)

    sqlite = sqlite_schema()
    postgres = postgres_schema(args.database_url)

    missing_tables = [t for t in sqlite if t not in postgres]
    missing_columns = {
        t: [c for c in columns if c not in postgres.get(t, {})]
        for t, columns in sqlite.items()
        if t in postgres and any(c not in postgres[t] for c in columns)
    }
    missing_columns = {t: cols for t, cols in missing_columns.items() if cols}

    total_missing = sum(len(columns) for columns in missing_columns.values()) + len(missing_tables)
    print(f"sqlite_tables={len(sqlite)} postgres_tables={len(postgres)} missing_tables={len(missing_tables)} "
          f"missing_columns={sum(len(c) for c in missing_columns.values())}")

    for table in missing_tables:
        print(f"MISSING TABLE {table} ({len(sqlite[table])} columns)")
    for table, columns in sorted(missing_columns.items()):
        print(f"MISSING COLUMNS {table}: {', '.join(columns)}")

    extra = {
        t: [c for c in columns if c not in sqlite.get(t, {})]
        for t, columns in postgres.items()
        if any(c not in sqlite.get(t, {}) for c in columns)
    }
    extra = {t: cols for t, cols in extra.items() if cols}
    if extra:
        print("note — PostgreSQL-only columns (kept, not part of this check):")
        for table, columns in sorted(extra.items()):
            print(f"  {table}: {', '.join(columns)}")

    if args.emit_sql:
        print("\n--- additive DDL ---")
        for table in missing_tables:
            print(create_table_sql(table, sqlite[table]) + ";")
        for table, columns in sorted(missing_columns.items()):
            for column in columns:
                print(add_column_sql(table, column, sqlite[table][column]) + ";")

    return 0 if total_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
