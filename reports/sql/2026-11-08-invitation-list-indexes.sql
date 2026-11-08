-- 2026-11-08 — indexes for GET /api/invitations (list_invitations).
--
-- The query filters deleted_at IS NULL, scopes to owner_id OR an
-- invitation_collaborators membership, optionally filters archived /
-- is_published, orders by (archived, updated_at DESC), and paginates with
-- LIMIT/OFFSET. The application also applies these statements idempotently at
-- boot; this file is for an out-of-band DBA migration and for review.
--
-- Deliberately NOT indexed: the free-text search. It uses
-- LOWER(json_extract(draft_json,'$.fields.names')) LIKE '%q%' and
-- LOWER(slug) LIKE '%q%'. A leading wildcard cannot use a b-tree index. The
-- candidate set is still bounded by owner/collaborator membership; add SQLite
-- FTS5 or PostgreSQL pg_trgm as a separate, backfilled change if search volume
-- makes the per-owner scan material.

-- ---------------------------------------------------------------------------
-- SQLite (src/python/server.py). is_published/deleted_at are added by the
-- startup ALTER block, so run this only against a schema that has them.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_invitations_owner_archived_updated
  ON invitations(owner_id, archived, updated_at DESC)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_invitations_owner_status_updated
  ON invitations(owner_id, archived, is_published, updated_at DESC)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_invitation_collaborators_user_invite
  ON invitation_collaborators(user_id, invitation_id);

ANALYZE invitations;

-- ---------------------------------------------------------------------------
-- PostgreSQL (docs/postgres_schema.sql). ADD COLUMN IF NOT EXISTS makes this
-- safe on databases created before is_published was in CREATE TABLE.
-- ---------------------------------------------------------------------------
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS is_published INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_invitations_owner_archived_updated
  ON invitations(owner_id, archived, updated_at DESC)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_invitations_owner_status_updated
  ON invitations(owner_id, archived, is_published, updated_at DESC)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_invitation_collaborators_user_invite
  ON invitation_collaborators(user_id, invitation_id);

ANALYZE invitations;
