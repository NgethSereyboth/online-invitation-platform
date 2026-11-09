"""core/db.py — Part 4 Task 4.1 (ROADMAP-v0.54-to-v1.0 §4.1).

The read/write layer that makes field-level encryption* invisible to the rest
of the backend.

Why a wrapper instead of call-site edits: this backend has no ORM. Sensitive
columns such as ``users.email`` are selected from ~20 statements and read in
dozens of handlers. Each row that leaves the database is therefore passed
through :func:`reveal` here, once, at the connection boundary — a handler
cannot forget to decrypt, and a new handler cannot silently ship ciphertext.

Write side is deliberately **not** intercepted: rewriting ``INSERT``/``UPDATE``
parameters would mean parsing SQL to map ``?`` positions to columns, and a
silent mis-map corrupts data. The handful of statements that write a protected
column are explicit and use :func:`protect` at the call site.

*Protected columns (``EINVITE_FIELD_ENCRYPTION=0`` disables all of this):*

    users.email                     guests.email            guests.phone
    delivery_attempts.recipient     audit_events.metadata_json
    invitation_edit_history.diff_json

Key storage and legacy behaviour live in :mod:`core.crypto`. Two properties
hold for every mixed-state database (partly migrated, or freshly deployed next
to old rows):

* :func:`reveal` returns a value unchanged unless it is a Fernet token, so
  plaintext rows keep working and nothing is double-decrypted;
* :func:`find_user_by_email` looks up ``email_hash`` first and **falls back**
  to the legacy plaintext column, so sign-in works before, during and after the
  migration script.

Standard library only. No import-time side effects.
"""
from __future__ import annotations

import sqlite3

from core import db_metrics
from core.crypto import CIPHERTEXT_PREFIX, decrypt_field, encrypt_field, hash_for_lookup

__all__ = [
    "PROTECTED_COLUMNS",
    "protect",
    "reveal",
    "reveal_row",
    "find_user_by_email",
    "protect_row_columns",
    "reveal_connection",
    "SensitiveRow",
]

#: Table → protected columns. Documentation and the migration script's driver;
#: the wrapper itself works on token shape (see :func:`reveal`) so that a
#: column added to this map cannot break reads whose table cannot be inferred.
PROTECTED_COLUMNS = {
    "users": ("email",),
    "guests": ("email", "phone"),
    "delivery_attempts": ("recipient",),
    "audit_events": ("metadata_json",),
    "invitation_edit_history": ("diff_json",),
}


def _is_token(value) -> bool:
    return isinstance(value, str) and value.startswith(CIPHERTEXT_PREFIX)


def protect(value):
    """Encrypt a value for storage. Non-strings, ``None`` and empty strings pass through."""
    if isinstance(value, str) and value and not _is_token(value):
        return encrypt_field(value)
    return value


def reveal(value):
    """Decrypt a stored value. Anything that is not a Fernet token is returned as-is."""
    if _is_token(value):
        return decrypt_field(value)
    return value


class SensitiveRow(dict):
    """A result row that supports the access patterns this codebase uses.

    ``sqlite3.Row`` offers key access, positional access, ``len()`` and
    ``dict(row)``; ``psycopg``'s ``dict_row`` offers key access. This class
    offers all of them, and iterates its **values** the way ``sqlite3.Row``
    does. It is a ``dict`` subclass, so ``dict(row)``, ``row.get(...)``,
    ``row["col"]`` and ``json.dumps(dict(row))`` keep working unchanged.
    """

    def __init__(self, mapping):
        super().__init__(mapping)
        self._order = tuple(mapping.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._order[key])
        return super().__getitem__(key)

    def __iter__(self):
        return iter(self._order)

    def keys(self):
        return list(self._order)

    def values(self):
        return [super().__getitem__(name) for name in self._order]

    def items(self):
        return [(name, super().__getitem__(name)) for name in self._order]


def reveal_row(row):
    """Return ``row`` as a :class:`SensitiveRow` with every protected value revealed.

    Applies to every string column rather than a fixed list: a Fernet token is
    self-describing, and :func:`reveal` leaves anything else untouched, so a
    column that gains encryption later needs no change here.
    """
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        row = dict(zip(row.keys(), tuple(row)))
    if isinstance(row, dict):
        return SensitiveRow({key: reveal(value) for key, value in row.items()})
    if isinstance(row, (list, tuple)):
        return [reveal(value) for value in row]
    return row


def protect_row_columns(columns, values):
    """Encrypt the values whose column name is protected (write-side helper).

    ``INSERT INTO guests(name,email,phone) VALUES(?,?,?)`` passes
    ``columns=("name","email","phone")`` with the matching parameter tuple and
    gets back the parameter tuple with the protected columns encrypted.
    """
    protected = set()
    for table_columns in PROTECTED_COLUMNS.values():
        protected.update(table_columns)
    return tuple(
        protect(value) if str(column).lower() in protected else value
        for column, value in zip(columns, values)
    )


class SensitiveCursor:
    """Cursor facade whose fetched rows are revealed. Everything else delegates."""

    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return reveal_row(self._cursor.fetchone())

    def fetchall(self):
        return [reveal_row(row) for row in self._cursor.fetchall()]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        return [reveal_row(row) for row in rows]

    def __iter__(self):
        for row in self._cursor:
            yield reveal_row(row)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class SensitiveConnection:
    """Connection facade that hands out :class:`SensitiveCursor` objects."""

    def __init__(self, connection):
        object.__setattr__(self, "_connection", connection)

    def execute(self, sql, params=()):
        db_metrics.record(sql)
        return SensitiveCursor(self._connection.execute(sql, params))

    def executemany(self, sql, seq_of_params):
        db_metrics.record(sql)
        return SensitiveCursor(self._connection.executemany(sql, seq_of_params))

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __setattr__(self, name, value):
        setattr(self._connection, name, value)


def reveal_connection(connection):
    """Wrap a sqlite3 or psycopg connection/adapter so reads come back revealed."""
    if isinstance(connection, SensitiveConnection):
        return connection
    return SensitiveConnection(connection)


def find_user_by_email(db, email):
    """Find one user by email, indexed-hash first with a legacy plaintext fallback.

    Returns a revealed row (or ``None``). ``email`` is matched case-insensitively
    through :func:`core.crypto.hash_for_lookup`; the fallback exists only for
    rows the migration has not converted yet and disappears on its own once it
    runs — no code change needed at that point.
    """
    if not email:
        return None
    normalized = str(email).strip().lower()
    row = db.execute("SELECT * FROM users WHERE email_hash=? LIMIT 1", (hash_for_lookup(normalized),)).fetchone()
    if row is not None:
        return row
    return db.execute(
        "SELECT * FROM users WHERE lower(email)=? AND (email_hash IS NULL OR email_hash='') LIMIT 1",
        (normalized,),
    ).fetchone()
