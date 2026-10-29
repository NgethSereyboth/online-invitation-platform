"""invitation_versions.py — v0.58.0 (ROADMAP-v0.54-to-v1.0 §3.5.3)

Version-history timeline — data-access layer.

Tables
------
``invitation_versions``
    id              TEXT PRIMARY KEY
    invitation_id   TEXT NOT NULL
    document_json   TEXT NOT NULL
    author_id       TEXT NOT NULL
    author_name     TEXT NOT NULL DEFAULT ''
    summary         TEXT NOT NULL DEFAULT ''
    is_auto         INTEGER NOT NULL DEFAULT 0
    created_at      INTEGER NOT NULL

Capped at MAX_SNAPSHOTS_PER_INVITATION (50) per invitation; oldest pruned.

Public API
----------
``ensure_schema(db)``
    Idempotent CREATE TABLE / CREATE INDEX.

``list_versions(db, invitation_id, limit=50)``
    Return ``[{"id","invitationId","authorId","authorName","summary",
              "isAuto","createdAt","documentJson"}]`` newest first.
    The ``documentJson`` field is omitted when ``include_document=False``
    (the default for list views — clients fetch it separately when restoring).

``create_snapshot(db, invitation_id, document_json, author_id, author_name, summary, is_auto)``
    Insert a snapshot row. Prune oldest if over the cap. Returns the new id.

``restore_version(db, invitation_id, version_id, by_user_id, by_user_name)``
    Auto-snapshot the current state first (so restore is reversible), then
    return the stored document JSON. Caller is responsible for applying it
    to the editor state.

``get_version_document(db, invitation_id, version_id)``
    Return only the document JSON for one version (used by preview).

``capture_auto_snapshot(db, invitation_id, document_json, *, author_id,
                        author_name, now_ms)``
    The draft-save hook. Stores an automatic snapshot only when the content
    hash changed and ``AUTO_SNAPSHOT_MIN_INTERVAL_MS`` has elapsed since the
    last auto snapshot; a document above ``AUTO_SNAPSHOT_MAX_DOCUMENT_BYTES``
    is skipped with a log line. Returns ``{"created", "reason", "id"}`` where
    reason is one of ``created`` / ``unchanged`` / ``too_soon`` / ``size``.
    ``now_ms`` is passed in so the five-minute rule is testable with an
    injected clock instead of sleeping.
"""
from __future__ import annotations
import hashlib
import json
import time
import uuid
from typing import Optional

MAX_SNAPSHOTS_PER_INVITATION = 50

# Automatic snapshots are a safety net, not a save log: one per five minutes
# of real editing, at most 50 kept, and nothing that would double a document
# of embedded images into version history.
AUTO_SNAPSHOT_MIN_INTERVAL_MS = 5 * 60 * 1000
AUTO_SNAPSHOT_MAX_DOCUMENT_BYTES = 2 * 1024 * 1024

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS invitation_versions(
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL,
  document_json TEXT NOT NULL,
  author_id TEXT NOT NULL,
  author_name TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  is_auto INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
)""",
    "CREATE INDEX IF NOT EXISTS idx_invitation_versions_invitation ON invitation_versions(invitation_id,created_at DESC)",
]


def ensure_schema(db) -> None:
    """Create the invitation_versions table + indices if missing."""
    for statement in SCHEMA_STATEMENTS:
        db.execute(statement)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _row(row, include_document: bool = True) -> dict:
    out = {
        "id": row["id"],
        "invitationId": row["invitation_id"],
        "authorId": row["author_id"],
        "authorName": row["author_name"] or "",
        "summary": row["summary"] or "",
        "isAuto": bool(row["is_auto"]),
        "createdAt": row["created_at"],
    }
    if include_document:
        out["documentJson"] = row["document_json"]
    return out


def list_versions(db, invitation_id: str, limit: int = 50, include_document: bool = False) -> list[dict]:
    """Return snapshots for an invitation, newest first."""
    ensure_schema(db)
    rows = db.execute(
        "SELECT * FROM invitation_versions WHERE invitation_id=? "
        "ORDER BY created_at DESC LIMIT ?",
        (invitation_id, int(max(1, min(limit, MAX_SNAPSHOTS_PER_INVITATION))))
    ).fetchall()
    return [_row(r, include_document) for r in rows]


def create_snapshot(db, invitation_id: str, *, document_json: str,
                    author_id: str, author_name: str = "",
                    summary: str = "", is_auto: bool = False,
                    now_ms: Optional[int] = None) -> str:
    """Insert a snapshot row. Prune oldest over the cap. Returns the new id."""
    ensure_schema(db)
    snapshot_id = str(uuid.uuid4())
    # Validate JSON before persisting — refuse to store corrupt documents.
    try:
        json.loads(document_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid document JSON: {exc}")
    db.execute(
        "INSERT INTO invitation_versions"
        "(id, invitation_id, document_json, author_id, author_name, summary, is_auto, created_at) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (snapshot_id, invitation_id, document_json,
         author_id, author_name[:200], str(summary or "")[:240],
         1 if is_auto else 0, _now_ms() if now_ms is None else int(now_ms))
    )
    _prune(db, invitation_id)
    return snapshot_id


def _document_hash(document_json: str) -> str:
    """Hash the *content*, not the serialisation.

    Two saves of the same document can differ in key order; comparing raw
    strings would then store a snapshot whose content is unchanged, which is
    exactly what the five-minute rule exists to prevent.
    """
    try:
        canonical = json.dumps(json.loads(document_json), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid document JSON: {exc}")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def latest_auto_snapshot(db, invitation_id: str) -> Optional[dict]:
    """Return the newest auto snapshot's ``{id, created_at, document_json}``."""
    ensure_schema(db)
    row = db.execute(
        "SELECT id,created_at,document_json FROM invitation_versions "
        "WHERE invitation_id=? AND is_auto=1 ORDER BY created_at DESC LIMIT 1",
        (invitation_id,)
    ).fetchone()
    return dict(row) if row else None


def capture_auto_snapshot(db, invitation_id: str, document_json: str, *,
                          author_id: str, author_name: str = "",
                          now_ms: Optional[int] = None) -> dict:
    """Snapshot a saved draft when the content changed and the gap allows it.

    Returns ``{"created": bool, "reason": str, "id": str|None}``. A document
    that cannot be parsed is reported as ``invalid`` instead of raised; a
    database failure still raises, so the caller can log it and keep the save
    it already wrote.
    """
    now = _now_ms() if now_ms is None else int(now_ms)
    try:
        size = len(document_json.encode("utf-8"))
    except (AttributeError, UnicodeError):
        return {"created": False, "reason": "invalid", "id": None}
    if size > AUTO_SNAPSHOT_MAX_DOCUMENT_BYTES:
        print(
            f"[invitation_versions] auto snapshot skipped: document {size} B "
            f"exceeds {AUTO_SNAPSHOT_MAX_DOCUMENT_BYTES} B (invitation {invitation_id})",
            flush=True,
        )
        return {"created": False, "reason": "size", "id": None}
    try:
        digest = _document_hash(document_json)
    except ValueError:
        return {"created": False, "reason": "invalid", "id": None}
    latest = latest_auto_snapshot(db, invitation_id)
    if latest is not None:
        if _document_hash(latest["document_json"]) == digest:
            return {"created": False, "reason": "unchanged", "id": None}
        if now - int(latest["created_at"] or 0) < AUTO_SNAPSHOT_MIN_INTERVAL_MS:
            return {"created": False, "reason": "too_soon", "id": None}
    snapshot_id = create_snapshot(
        db, invitation_id,
        document_json=document_json,
        author_id=author_id,
        author_name=author_name,
        summary="Auto",
        is_auto=True,
        now_ms=now,
    )
    return {"created": True, "reason": "created", "id": snapshot_id}


def _prune(db, invitation_id: str) -> int:
    """Delete oldest snapshots over the cap. Returns count pruned."""
    count_row = db.execute(
        "SELECT COUNT(*) AS n FROM invitation_versions WHERE invitation_id=?",
        (invitation_id,)
    ).fetchone()
    total = int(count_row["n"] if count_row else 0)
    if total <= MAX_SNAPSHOTS_PER_INVITATION:
        return 0
    excess = total - MAX_SNAPSHOTS_PER_INVITATION
    # Find the ids of the oldest `excess` rows.
    stale = db.execute(
        "SELECT id FROM invitation_versions WHERE invitation_id=? "
        "ORDER BY created_at ASC LIMIT ?",
        (invitation_id, excess)
    ).fetchall()
    for row in stale:
        db.execute(
            "DELETE FROM invitation_versions WHERE id=? AND invitation_id=?",
            (row["id"], invitation_id)
        )
    return len(stale)


def get_version(db, invitation_id: str, version_id: str) -> Optional[dict]:
    """Return one snapshot row (document included), or None if not found."""
    ensure_schema(db)
    row = db.execute(
        "SELECT * FROM invitation_versions WHERE id=? AND invitation_id=?",
        (version_id, invitation_id)
    ).fetchone()
    return _row(row, include_document=True) if row else None


def get_version_document(db, invitation_id: str, version_id: str) -> Optional[str]:
    """Return the raw document JSON for a version, or None if not found."""
    ensure_schema(db)
    row = db.execute(
        "SELECT document_json FROM invitation_versions "
        "WHERE id=? AND invitation_id=?",
        (version_id, invitation_id)
    ).fetchone()
    return row["document_json"] if row else None


def restore_version(db, invitation_id: str, version_id: str, *,
                    current_document_json: Optional[str] = None,
                    by_user_id: str = "", by_user_name: str = "") -> dict:
    """Restore a prior version.

    The current state (if provided) is auto-snapshotted first so the restore
    is reversible. Returns ``{"document": <parsed JSON>, "versionId": ...,
    "autoSnapshotId": ...}`` — the caller applies the document to the editor.
    """
    ensure_schema(db)
    doc_json = get_version_document(db, invitation_id, version_id)
    if doc_json is None:
        raise ValueError("Version not found")
    auto_snapshot_id = None
    if current_document_json:
        try:
            auto_snapshot_id = create_snapshot(
                db, invitation_id,
                document_json=current_document_json,
                author_id=by_user_id,
                author_name=by_user_name,
                summary=f"Auto-snapshot before restore of {version_id}",
                is_auto=True
            )
        except Exception:
            auto_snapshot_id = None
    try:
        document = json.loads(doc_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Stored document JSON is corrupt: {exc}")
    return {"document": document, "versionId": version_id, "autoSnapshotId": auto_snapshot_id}
