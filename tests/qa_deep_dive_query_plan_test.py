#!/usr/bin/env python3
"""Query-plan regression for the dashboard pagination scope.

The RC pass found that the documented owner index was not used by the real
dashboard query: a correlated ``EXISTS`` in an ``OR`` forced ``SCAN i`` even at
50k rows. Replacing it with a set-membership ``IN`` is semantically identical
and lets SQLite take the multi-index OR path. This test pins the planner choice
and the production clause so a future edit cannot silently reintroduce the scan.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCOPE = (
    "(i.owner_id=? OR i.id IN "
    "(SELECT invitation_id FROM invitation_collaborators WHERE user_id=?))"
)
ARCHIVED_SQL = (
    "SELECT i.id FROM invitations i WHERE i.deleted_at IS NULL AND "
    + SCOPE
    + " AND i.archived=1 ORDER BY i.archived,i.updated_at DESC LIMIT ? OFFSET ?"
)
ALL_SQL = (
    "SELECT i.id FROM invitations i WHERE i.deleted_at IS NULL AND "
    + SCOPE
    + " ORDER BY i.archived,i.updated_at DESC LIMIT ? OFFSET ?"
)
COLLABORATOR_LIST_SQL = (
    "SELECT invitation_id FROM invitation_collaborators "
    "WHERE user_id=? ORDER BY created_at DESC"
)

ROWS = 20_000


def _database() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE invitations(
            id TEXT PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            draft_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            owner_id TEXT,
            archived INTEGER NOT NULL DEFAULT 0,
            deleted_at INTEGER,
            is_published INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX idx_invitations_owner_archived_updated
            ON invitations(owner_id,archived,updated_at DESC);
        CREATE INDEX idx_invitations_owner ON invitations(owner_id,updated_at DESC);
        CREATE TABLE invitation_collaborators(
            invitation_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at INTEGER NOT NULL,
            PRIMARY KEY(invitation_id,user_id)
        );
        CREATE INDEX idx_invitation_collaborators_user
            ON invitation_collaborators(user_id,created_at);
        CREATE INDEX idx_invitation_collaborators_user_invite
            ON invitation_collaborators(user_id,invitation_id);
        """
    )
    now = 1_800_000_000_000
    db.executemany(
        "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,archived,is_published) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            (
                f"inv-{i}",
                f"slug-{i}",
                "{}",
                now - i * 1000,
                "owner-a" if i % 10 else "owner-b",
                i % 2,
                i % 3 == 0,
            )
            for i in range(ROWS)
        ),
    )
    # A realistic distribution: the target collaborator holds a small share, so
    # the ordered-list plan can use the user index instead of scanning the table.
    collaborators = [
        (f"inv-{i}", "collab-a", "viewer", now) for i in range(0, ROWS, 100)
    ]
    collaborators.extend(
        (f"inv-{i}", f"collab-{i % 50}", "viewer", now) for i in range(ROWS)
    )
    db.executemany(
        "INSERT INTO invitation_collaborators(invitation_id,user_id,role,created_at) "
        "VALUES(?,?,?,?)",
        collaborators,
    )
    db.commit()
    db.execute("ANALYZE")
    db.commit()
    return db


def _plan(db: sqlite3.Connection, sql: str, params: tuple) -> list[str]:
    return [row["detail"] for row in db.execute("EXPLAIN QUERY PLAN " + sql, params)]


def _has_full_table_scan(plan: list[str]) -> bool:
    """True only for an unindexed scan; an index-range scan is acceptable."""
    return any(detail == "SCAN i" for detail in plan)


def test_dashboard_scope_uses_indexes_instead_of_a_scan():
    db = _database()
    try:
        indices = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name IN ('invitations','invitation_collaborators')"
            )
        }
        assert {
            "idx_invitations_owner_archived_updated",
            "idx_invitation_collaborators_user_invite",
        } <= indices, indices

        archived = _plan(db, ARCHIVED_SQL, ("owner-a", "collab-a", 20, 0))
        assert not _has_full_table_scan(archived), archived
        assert any("idx_invitations" in detail for detail in archived), archived
        assert any("idx_invitation_collaborators_user_invite" in detail for detail in archived), archived

        unfiltered = _plan(db, ALL_SQL, ("owner-a", "collab-a", 20, 0))
        assert not _has_full_table_scan(unfiltered), unfiltered
        assert any("idx_invitations_owner" in detail for detail in unfiltered), unfiltered

        collaborators = _plan(db, COLLABORATOR_LIST_SQL, ("collab-a",))
        assert any("idx_invitation_collaborators_user" in detail for detail in collaborators), collaborators
    finally:
        db.close()


def test_server_dashboard_query_uses_set_membership():
    source = (ROOT / "src/python/server.py").read_text(encoding="utf-8")
    start = source.index("    def list_invitations(self):")
    end = source.find("\n    def ", start + 1)
    dashboard = source[start : end if end != -1 else None]
    assert "i.id IN (SELECT invitation_id FROM invitation_collaborators WHERE user_id=?)" in dashboard
    assert (
        "EXISTS(SELECT 1 FROM invitation_collaborators c "
        "WHERE c.invitation_id=i.id AND c.user_id=?)"
    ) not in dashboard
