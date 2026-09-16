"""editor_comments.py — v0.58.0 (ROADMAP-v0.54-to-v1.0 §3.5.2)

Editor canvas comment threads — data-access layer.

This module provides the pure data-access functions used by the HTTP
handlers in `src/python/server.py`. The handlers own request parsing,
authentication, rate-limiting, and audit logging; this module owns
SQL queries, validation, and the @-mention notification side-effect.

Tables
------
``editor_comments``
    id              TEXT PRIMARY KEY
    invitation_id   TEXT NOT NULL
    page_id         TEXT NOT NULL DEFAULT 'hero'
    element_id      TEXT NOT NULL DEFAULT ''
    x               REAL NOT NULL DEFAULT 0
    y               REAL NOT NULL DEFAULT 0
    author_id       TEXT NOT NULL
    author_name     TEXT NOT NULL DEFAULT ''
    body            TEXT NOT NULL
    parent_id       TEXT NOT NULL DEFAULT ''
    resolved_at     INTEGER  -- NULL = open, millis = resolved timestamp
    created_at      INTEGER NOT NULL

Schema is created idempotently on first use (see ``ensure_schema``).

Public API
----------
``list_comments(db, invitation_id)``
    Return ``[{"id","pageId","elementId","x","y","authorId","authorName",
              "body","parentId","resolvedAt","createdAt","replies":[...]}]``
    grouped into root + replies (replies attached to their root).

``create_comment(db, invitation_id, author, body, x, y, page_id, element_id, parent_id)``
    Insert a comment row. Returns the new id. Triggers @-mention email
    notifications via ``send_platform_email`` when ``@name`` appears in body.

``resolve_comment(db, invitation_id, comment_id, resolved)``
    Toggle the resolved flag on the root (and by extension all replies —
    resolution is a thread-level state stored on the root row).

``delete_comment(db, invitation_id, comment_id, by_user_id, by_manager)``
    Delete a comment + (if root) all its replies.

``ensure_schema(db)``
    Idempotent CREATE TABLE / CREATE INDEX.
"""
from __future__ import annotations
import json
import re
import time
import uuid
from typing import Any, Iterable

# Schema statements — run on every connect() (cheap; IF NOT EXISTS).
SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS editor_comments(
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL,
  page_id TEXT NOT NULL DEFAULT 'hero',
  element_id TEXT NOT NULL DEFAULT '',
  x REAL NOT NULL DEFAULT 0,
  y REAL NOT NULL DEFAULT 0,
  author_id TEXT NOT NULL,
  author_name TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  parent_id TEXT NOT NULL DEFAULT '',
  resolved_at INTEGER,
  created_at INTEGER NOT NULL
)""",
    "CREATE INDEX IF NOT EXISTS idx_editor_comments_invitation ON editor_comments(invitation_id,created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_editor_comments_parent ON editor_comments(parent_id,created_at ASC)",
]


def ensure_schema(db) -> None:
    """Create the editor_comments table + indices if missing."""
    for statement in SCHEMA_STATEMENTS:
        db.execute(statement)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _row(row) -> dict:
    """Convert a sqlite3.Row / dict to a JSON-serializable dict."""
    return {
        "id": row["id"],
        "invitationId": row["invitation_id"],
        "pageId": row["page_id"],
        "elementId": row["element_id"] or "",
        "x": float(row["x"] or 0),
        "y": float(row["y"] or 0),
        "authorId": row["author_id"],
        "authorName": row["author_name"] or "",
        "body": row["body"],
        "parentId": row["parent_id"] or "",
        "resolvedAt": row["resolved_at"],
        "createdAt": row["created_at"],
    }


def list_comments(db, invitation_id: str) -> list[dict]:
    """Return all comments for an invitation, grouped into root + replies."""
    ensure_schema(db)
    rows = db.execute(
        "SELECT * FROM editor_comments WHERE invitation_id=? ORDER BY created_at ASC",
        (invitation_id,)
    ).fetchall()
    flat = [_row(r) for r in rows]
    roots = [c for c in flat if not c["parentId"]]
    replies = [c for c in flat if c["parentId"]]
    for root in roots:
        root["replies"] = [r for r in replies if r["parentId"] == root["id"]]
    return roots


_MENTION_RE = re.compile(r"@([A-Za-z0-9._-]+)")


def _extract_mentions(body: str) -> list[str]:
    """Extract @-mention tokens from a comment body."""
    return list({m.group(1) for m in _MENTION_RE.finditer(body or "")})


def _send_mention_emails(invitation_id: str, author_name: str, body: str, mentions: list[str]) -> None:
    """Best-effort: notify each @-mentioned user by email.

    Look up the mentioned user by email or username in the ``users`` table;
    if found and SMTP is configured, send a notification. Silently no-op on
    any error so a missing SMTP config doesn't break comment creation.
    """
    if not mentions:
        return
    try:
        # Late import — avoid circulars at module load.
        from server import send_platform_email  # type: ignore
        import sqlite3
    except Exception:
        return
    for handle in mentions[:20]:  # cap mentions per comment
        try:
            data_dir = _data_dir()
            conn = sqlite3.connect(data_dir / "einvite.db", timeout=5)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "SELECT email FROM users WHERE email=? OR username=? OR id=? LIMIT 1",
                    (handle, handle, handle)
                ).fetchone()
                if not row:
                    continue
                email = row["email"]
                subject = f"[EInvite] {author_name or 'Someone'} mentioned you in a comment"
                text = (
                    f"{author_name or 'Someone'} mentioned you in a comment thread:\n\n"
                    f"{body}\n\n"
                    f"Invitation: {invitation_id}\n"
                )
                try:
                    send_platform_email(email, subject, text)
                except Exception:
                    pass
            finally:
                conn.close()
        except Exception:
            continue


def _data_dir():
    """Resolve the data directory path. Mirrors server.py's DB() resolution."""
    import os
    from pathlib import Path
    return Path(os.environ.get("EINVITE_DATA_DIR", "data"))


def create_comment(db, invitation_id: str, *, author_id: str, author_name: str = "",
                   body: str, x: float = 0, y: float = 0,
                   page_id: str = "hero", element_id: str = "",
                   parent_id: str = "") -> str:
    """Insert a comment row. Returns the new id."""
    ensure_schema(db)
    comment_id = str(uuid.uuid4())
    body_clean = str(body or "").strip()[:4000]
    if not body_clean:
        raise ValueError("Comment body is required")
    # If parent_id is set, validate it exists + belongs to the same invitation,
    # and inherit its x/y/page_id (replies don't have their own pin).
    if parent_id:
        parent = db.execute(
            "SELECT id, x, y, page_id, element_id, resolved_at FROM editor_comments "
            "WHERE id=? AND invitation_id=?",
            (parent_id, invitation_id)
        ).fetchone()
        if not parent:
            raise ValueError("Parent comment not found")
        if parent["resolved_at"]:
            raise ValueError("Cannot reply to a resolved comment")
        x = float(parent["x"]); y = float(parent["y"])
        page_id = parent["page_id"]; element_id = parent["element_id"] or ""
    db.execute(
        "INSERT INTO editor_comments"
        "(id, invitation_id, page_id, element_id, x, y, author_id, author_name, "
        " body, parent_id, resolved_at, created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (comment_id, invitation_id, page_id, element_id, float(x), float(y),
         author_id, author_name[:200], body_clean, parent_id, None, _now_ms())
    )
    # Best-effort @-mention emails.
    try:
        _send_mention_emails(invitation_id, author_name, body_clean, _extract_mentions(body_clean))
    except Exception:
        pass
    return comment_id


def resolve_comment(db, invitation_id: str, comment_id: str, resolved: bool) -> bool:
    """Toggle the resolved flag on a root comment. Returns True if changed."""
    ensure_schema(db)
    row = db.execute(
        "SELECT id, parent_id, resolved_at FROM editor_comments "
        "WHERE id=? AND invitation_id=?",
        (comment_id, invitation_id)
    ).fetchone()
    if not row:
        return False
    root_id = row["parent_id"] or row["id"]
    new_value = _now_ms() if resolved else None
    changed = db.execute(
        "UPDATE editor_comments SET resolved_at=? WHERE id=? AND invitation_id=?",
        (new_value, root_id, invitation_id)
    ).rowcount
    return bool(changed)


def delete_comment(db, invitation_id: str, comment_id: str, *, by_user_id: str, by_manager: bool = False) -> bool:
    """Delete a comment. If root, also deletes all replies.

    Authorization:
      • The author can delete their own comment.
      • A manager can delete any comment (host or co-host with manager role).
    """
    ensure_schema(db)
    row = db.execute(
        "SELECT id, parent_id, author_id FROM editor_comments "
        "WHERE id=? AND invitation_id=?",
        (comment_id, invitation_id)
    ).fetchone()
    if not row:
        return False
    if row["author_id"] != by_user_id and not by_manager:
        raise PermissionError("Only the author or a manager can delete this comment")
    if row["parent_id"]:
        # Reply: just delete this row.
        db.execute(
            "DELETE FROM editor_comments WHERE id=? AND invitation_id=?",
            (comment_id, invitation_id)
        )
    else:
        # Root: delete root + all replies.
        db.execute(
            "DELETE FROM editor_comments WHERE invitation_id=? AND (id=? OR parent_id=?)",
            (invitation_id, comment_id, comment_id)
        )
    return True


def count_threads(db, invitation_id: str) -> int:
    """Return the count of unresolved root comment threads for the invitation."""
    ensure_schema(db)
    row = db.execute(
        "SELECT COUNT(*) AS n FROM editor_comments "
        "WHERE invitation_id=? AND parent_id='' AND resolved_at IS NULL",
        (invitation_id,)
    ).fetchone()
    return int(row["n"] if row else 0)
