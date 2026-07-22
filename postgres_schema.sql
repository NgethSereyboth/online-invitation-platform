-- PostgreSQL target schema for the E-invitation-website production migration.
-- This schema mirrors the current SQLite data model using TEXT JSON payloads for runtime compatibility with the shared SQLite/PostgreSQL application code.

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  role TEXT NOT NULL DEFAULT 'customer',
  email_verified INTEGER NOT NULL DEFAULT 0,
  plan TEXT NOT NULL DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS invitations (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  draft_json TEXT NOT NULL,
  updated_at BIGINT NOT NULL,
  owner_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  archived INTEGER NOT NULL DEFAULT 0,
  views BIGINT NOT NULL DEFAULT 0,
  access_mode TEXT NOT NULL DEFAULT 'unlisted',
  access_password_hash TEXT,
  access_password_salt TEXT,
  is_published INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_invitations_owner ON invitations(owner_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS publications (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  version BIGINT NOT NULL,
  document_json TEXT NOT NULL,
  published_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_publications_invitation ON publications(invitation_id, published_at DESC);

CREATE TABLE IF NOT EXISTS rsvps (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  publication_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  guest_count INTEGER NOT NULL,
  note TEXT,
  created_at BIGINT NOT NULL,
  answers_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_rsvps_invitation ON rsvps(invitation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  mime TEXT NOT NULL,
  path TEXT NOT NULL,
  size BIGINT NOT NULL,
  created_at BIGINT NOT NULL,
  folder TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  favorite INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_assets_invitation ON assets(invitation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS guests (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  phone TEXT,
  token TEXT UNIQUE NOT NULL,
  created_at BIGINT NOT NULL,
  checked_in INTEGER NOT NULL DEFAULT 0,
  checked_in_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_guests_invitation ON guests(invitation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS user_templates (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  document_json TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  favorite INTEGER NOT NULL DEFAULT 0,
  current_version INTEGER NOT NULL DEFAULT 1,
  thumbnail_json TEXT NOT NULL DEFAULT '{}',
  visibility TEXT NOT NULL DEFAULT 'private',
  published_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_templates_owner ON user_templates(owner_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_templates_marketplace ON user_templates(visibility, published_at DESC);

CREATE TABLE IF NOT EXISTS template_versions (
  id TEXT PRIMARY KEY,
  template_id TEXT NOT NULL REFERENCES user_templates(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  document_json TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  UNIQUE(template_id, version)
);

CREATE TABLE IF NOT EXISTS user_page_templates (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'General',
  page_json TEXT NOT NULL,
  favorite INTEGER NOT NULL DEFAULT 0,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS view_events (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  publication_id TEXT NOT NULL,
  viewed_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_view_events_invitation ON view_events(invitation_id, viewed_at);

CREATE TABLE IF NOT EXISTS access_tokens (
  token_hash TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_components (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'General',
  payload_json TEXT NOT NULL,
  favorite INTEGER NOT NULL DEFAULT 0,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_components_owner_kind ON user_components(owner_id, kind, updated_at DESC);

CREATE TABLE IF NOT EXISTS guest_messages (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  publication_id TEXT NOT NULL,
  name TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_kind ON auth_tokens(user_id, kind, expires_at);


CREATE TABLE IF NOT EXISTS invitation_collaborators (
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'viewer',
  created_at BIGINT NOT NULL,
  PRIMARY KEY(invitation_id,user_id)
);
CREATE INDEX IF NOT EXISTS idx_invitation_collaborators_user ON invitation_collaborators(user_id,created_at DESC);
