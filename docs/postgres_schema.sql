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
  plan TEXT NOT NULL DEFAULT 'free',
  upload_enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS billing_orders (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  provider TEXT NOT NULL DEFAULT '',
  provider_session_id TEXT NOT NULL DEFAULT '',
  amount_minor BIGINT NOT NULL,
  currency TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL,
  paid_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_billing_orders_user_time ON billing_orders(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS billing_events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  received_at BIGINT NOT NULL,
  processed_at BIGINT
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);

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
  is_published INTEGER NOT NULL DEFAULT 0,
  last_client_id TEXT,
  last_mutation_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_invitations_owner ON invitations(owner_id, updated_at DESC);
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS last_client_id TEXT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS last_mutation_id TEXT;

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
  guest_id TEXT,
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  guest_count INTEGER NOT NULL,
  note TEXT,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL DEFAULT 0,
  answers_json TEXT NOT NULL DEFAULT '{}'
);
ALTER TABLE rsvps ADD COLUMN IF NOT EXISTS guest_id TEXT;
ALTER TABLE rsvps ADD COLUMN IF NOT EXISTS normalized_name TEXT NOT NULL DEFAULT '';
ALTER TABLE rsvps ADD COLUMN IF NOT EXISTS updated_at BIGINT NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_rsvps_invitation ON rsvps(invitation_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rsvps_guest_unique ON rsvps(invitation_id,guest_id) WHERE guest_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rsvps_name_lookup ON rsvps(invitation_id,normalized_name,created_at DESC);

CREATE TABLE IF NOT EXISTS stored_objects (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  path TEXT UNIQUE NOT NULL,
  sha256 TEXT NOT NULL DEFAULT '',
  mime TEXT NOT NULL,
  size BIGINT NOT NULL,
  width INTEGER NOT NULL DEFAULT 0,
  height INTEGER NOT NULL DEFAULT 0,
  dominant_color TEXT NOT NULL DEFAULT '',
  processing_state TEXT NOT NULL DEFAULT 'ready',
  quarantine_state TEXT NOT NULL DEFAULT 'released',
  scan_status TEXT NOT NULL DEFAULT 'not-configured',
  ref_count INTEGER NOT NULL DEFAULT 0,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stored_objects_owner_hash ON stored_objects(owner_id,sha256,size,mime);
CREATE INDEX IF NOT EXISTS idx_stored_objects_path ON stored_objects(path);

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
  sha256 TEXT NOT NULL DEFAULT '',
  width INTEGER NOT NULL DEFAULT 0,
  height INTEGER NOT NULL DEFAULT 0,
  dominant_color TEXT NOT NULL DEFAULT '',
  object_id TEXT REFERENCES stored_objects(id),
  processing_state TEXT NOT NULL DEFAULT 'ready'
);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS width INTEGER NOT NULL DEFAULT 0;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS height INTEGER NOT NULL DEFAULT 0;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS dominant_color TEXT NOT NULL DEFAULT '';
ALTER TABLE assets ADD COLUMN IF NOT EXISTS object_id TEXT;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS processing_state TEXT NOT NULL DEFAULT 'ready';
CREATE INDEX IF NOT EXISTS idx_assets_invitation ON assets(invitation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS upload_sessions (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  mime TEXT NOT NULL,
  expected_size BIGINT NOT NULL,
  received_size BIGINT NOT NULL DEFAULT 0,
  temp_path TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  expires_at BIGINT NOT NULL
);
ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS folder TEXT NOT NULL DEFAULT '';
ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS import_job_id TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_upload_sessions_expiry ON upload_sessions(expires_at);

CREATE TABLE IF NOT EXISTS material_folders (
  id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, parent_id TEXT,
  name TEXT NOT NULL, relative_key TEXT NOT NULL, created_by TEXT NOT NULL, created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL,
  UNIQUE(invitation_id, relative_key)
);
CREATE INDEX IF NOT EXISTS idx_material_folders_invitation ON material_folders(invitation_id,relative_key);
CREATE TABLE IF NOT EXISTS material_import_jobs (
  id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL, root_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'queued', total_files INTEGER NOT NULL DEFAULT 0, processed_files INTEGER NOT NULL DEFAULT 0, failed_files INTEGER NOT NULL DEFAULT 0,
  total_bytes BIGINT NOT NULL DEFAULT 0, processed_bytes BIGINT NOT NULL DEFAULT 0, failures_json TEXT NOT NULL DEFAULT '[]', created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL, cancelled_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_material_import_jobs_invitation ON material_import_jobs(invitation_id,created_at DESC);

CREATE TABLE IF NOT EXISTS guests (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  phone TEXT,
  token TEXT UNIQUE NOT NULL,
  token_hash TEXT,
  token_salt TEXT NOT NULL DEFAULT '',
  token_version INTEGER NOT NULL DEFAULT 1,
  token_expires_at BIGINT,
  token_revoked_at BIGINT,
  created_at BIGINT NOT NULL,
  checked_in INTEGER NOT NULL DEFAULT 0,
  checked_in_at BIGINT
);
ALTER TABLE guests ADD COLUMN IF NOT EXISTS token_hash TEXT;
ALTER TABLE guests ADD COLUMN IF NOT EXISTS token_salt TEXT NOT NULL DEFAULT '';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE guests ADD COLUMN IF NOT EXISTS token_expires_at BIGINT;
ALTER TABLE guests ADD COLUMN IF NOT EXISTS token_revoked_at BIGINT;
CREATE INDEX IF NOT EXISTS idx_guests_invitation ON guests(invitation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_guests_token_hash ON guests(token_hash);

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

CREATE INDEX IF NOT EXISTS idx_page_templates_owner ON user_page_templates(owner_id, updated_at DESC);

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

CREATE INDEX IF NOT EXISTS idx_access_tokens_invitation ON access_tokens(invitation_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_access_tokens_expiry ON access_tokens(expires_at);

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

CREATE TABLE IF NOT EXISTS studio_resources (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'General',
  payload_json TEXT NOT NULL,
  governance_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'draft',
  version INTEGER NOT NULL DEFAULT 1,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_studio_resources_owner_kind ON studio_resources(owner_id,kind,status,updated_at DESC);

CREATE TABLE IF NOT EXISTS studio_governance (
  owner_id TEXT PRIMARY KEY,
  policy_json TEXT NOT NULL DEFAULT '{}',
  updated_at BIGINT NOT NULL DEFAULT 0
);


CREATE TABLE IF NOT EXISTS studio_releases (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft',
  manifest_json TEXT NOT NULL DEFAULT '[]',
  version INTEGER NOT NULL DEFAULT 1,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL,
  activated_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_studio_releases_owner_status ON studio_releases(owner_id,status,updated_at DESC);

CREATE TABLE IF NOT EXISTS invitation_studio_release_pins (
  invitation_id TEXT PRIMARY KEY REFERENCES invitations(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  release_id TEXT NOT NULL REFERENCES studio_releases(id) ON DELETE RESTRICT,
  release_version INTEGER NOT NULL DEFAULT 1,
  pinned_by TEXT NOT NULL DEFAULT '',
  pinned_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_studio_release_pins_owner ON invitation_studio_release_pins(owner_id,release_id,updated_at DESC);

CREATE TABLE IF NOT EXISTS studio_backup_policies (
  owner_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  enabled INTEGER NOT NULL DEFAULT 0,
  interval_hours INTEGER NOT NULL DEFAULT 24,
  retention_count INTEGER NOT NULL DEFAULT 7,
  include_media INTEGER NOT NULL DEFAULT 1,
  updated_by TEXT NOT NULL DEFAULT '',
  updated_at BIGINT NOT NULL DEFAULT 0,
  last_run_at BIGINT,
  next_run_at BIGINT
);

CREATE TABLE IF NOT EXISTS studio_bulk_jobs (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'completed',
  selection_json TEXT NOT NULL DEFAULT '{}',
  result_json TEXT NOT NULL DEFAULT '{}',
  created_by TEXT NOT NULL DEFAULT '',
  created_at BIGINT NOT NULL,
  completed_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_studio_bulk_jobs_owner_time ON studio_bulk_jobs(owner_id,created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_components_owner_kind ON user_components(owner_id, kind, updated_at DESC);

CREATE TABLE IF NOT EXISTS guest_messages (
  id TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  publication_id TEXT NOT NULL,
  name TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_guest_messages_invitation ON guest_messages(invitation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS auth_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_kind ON auth_tokens(user_id, kind, expires_at);


CREATE INDEX IF NOT EXISTS idx_auth_tokens_expiry ON auth_tokens(expires_at);

CREATE TABLE IF NOT EXISTS invitation_collaborators (
  invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'viewer',
  created_at BIGINT NOT NULL,
  PRIMARY KEY(invitation_id,user_id)
);
CREATE INDEX IF NOT EXISTS idx_invitation_collaborators_user ON invitation_collaborators(user_id,created_at DESC);

-- V13 future-development security foundation
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_algo TEXT NOT NULL DEFAULT 'pbkdf2-sha256-v1';
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_scheduled_at BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS id TEXT NOT NULL DEFAULT '';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_agent TEXT NOT NULL DEFAULT '';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ip_address TEXT NOT NULL DEFAULT '';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_seen_at BIGINT NOT NULL DEFAULT 0;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS device_name TEXT NOT NULL DEFAULT '';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS csrf_hash TEXT NOT NULL DEFAULT '';
UPDATE sessions SET id=token_hash WHERE id IS NULL OR id='';
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_public_id ON sessions(id);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  action TEXT NOT NULL,
  target_type TEXT NOT NULL DEFAULT '',
  target_id TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  ip_address TEXT NOT NULL DEFAULT '',
  previous_hash TEXT NOT NULL DEFAULT '',
  event_hash TEXT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS auth_challenges (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  kind TEXT NOT NULL,
  challenge TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  expires_at BIGINT NOT NULL,
  used_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_auth_challenges_expiry ON auth_challenges(expires_at);

CREATE TABLE IF NOT EXISTS passkeys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  credential_id TEXT UNIQUE NOT NULL,
  public_key TEXT NOT NULL,
  sign_count BIGINT NOT NULL DEFAULT 0,
  transports_json TEXT NOT NULL DEFAULT '[]',
  name TEXT NOT NULL DEFAULT 'Passkey',
  created_at BIGINT NOT NULL,
  last_used_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_passkeys_user ON passkeys(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS deleted_items (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  item_id TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  deleted_at BIGINT NOT NULL,
  purge_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deleted_items_owner ON deleted_items(owner_id,deleted_at DESC);

-- V13 recovery lifecycle
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS deleted_at BIGINT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS purge_at BIGINT;
CREATE INDEX IF NOT EXISTS idx_invitations_trash ON invitations(owner_id, deleted_at, purge_at);

-- V13 production storage, worker queue, bandwidth and backup tracking
ALTER TABLE stored_objects ADD COLUMN IF NOT EXISTS storage_key TEXT NOT NULL DEFAULT '';
ALTER TABLE stored_objects ADD COLUMN IF NOT EXISTS deleted_at BIGINT;
UPDATE stored_objects SET storage_key=path WHERE storage_key='';
CREATE TABLE IF NOT EXISTS background_jobs(
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'queued',
  attempts INTEGER NOT NULL DEFAULT 0, available_at BIGINT NOT NULL, locked_at BIGINT, last_error TEXT NOT NULL DEFAULT '', created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_background_jobs_queue ON background_jobs(state, available_at, created_at);
CREATE TABLE IF NOT EXISTS bandwidth_events(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, bytes BIGINT NOT NULL, created_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_bandwidth_events_owner_time ON bandwidth_events(owner_id, created_at);
CREATE TABLE IF NOT EXISTS backup_runs(id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL, detail_json TEXT NOT NULL DEFAULT '{}', created_at BIGINT NOT NULL, completed_at BIGINT, owner_id TEXT NOT NULL DEFAULT '', initiated_by TEXT NOT NULL DEFAULT '', archive_name TEXT NOT NULL DEFAULT '', size_bytes BIGINT NOT NULL DEFAULT 0, error_text TEXT NOT NULL DEFAULT '');
ALTER TABLE backup_runs ADD COLUMN IF NOT EXISTS owner_id TEXT NOT NULL DEFAULT '';
ALTER TABLE backup_runs ADD COLUMN IF NOT EXISTS initiated_by TEXT NOT NULL DEFAULT '';
ALTER TABLE backup_runs ADD COLUMN IF NOT EXISTS archive_name TEXT NOT NULL DEFAULT '';
ALTER TABLE backup_runs ADD COLUMN IF NOT EXISTS size_bytes BIGINT NOT NULL DEFAULT 0;
ALTER TABLE backup_runs ADD COLUMN IF NOT EXISTS error_text TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_backup_runs_owner_time ON backup_runs(owner_id,created_at DESC);

-- V13 studio operations and invitation-product features
ALTER TABLE users ADD COLUMN IF NOT EXISTS studio_name TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS white_label_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS upload_enabled INTEGER NOT NULL DEFAULT 1;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS custom_domain TEXT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS publish_at BIGINT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS unpublish_at BIGINT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS expires_at BIGINT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_invitations_custom_domain ON invitations(custom_domain) WHERE custom_domain IS NOT NULL AND custom_domain<>'';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT '';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS group_name TEXT NOT NULL DEFAULT '';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS household_id TEXT NOT NULL DEFAULT '';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS tags_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS table_name TEXT NOT NULL DEFAULT '';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS seat_label TEXT NOT NULL DEFAULT '';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS delivery_status TEXT NOT NULL DEFAULT 'not-sent';
ALTER TABLE guests ADD COLUMN IF NOT EXISTS opened_at BIGINT;
CREATE TABLE IF NOT EXISTS message_campaigns(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, name TEXT NOT NULL, channel TEXT NOT NULL, message TEXT NOT NULL, segment_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'draft', scheduled_at BIGINT, created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS message_deliveries(id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES message_campaigns(id) ON DELETE CASCADE, guest_id TEXT NOT NULL REFERENCES guests(id) ON DELETE CASCADE, channel TEXT NOT NULL, status TEXT NOT NULL, provider_id TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_campaign ON message_deliveries(campaign_id,status);
CREATE TABLE IF NOT EXISTS invitation_comments(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, object_id TEXT NOT NULL DEFAULT '', page_id TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', anchor_x DOUBLE PRECISION NOT NULL DEFAULT -1, anchor_y DOUBLE PRECISION NOT NULL DEFAULT -1, body TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0, created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_invitation_comments_invite ON invitation_comments(invitation_id,resolved,created_at);
CREATE INDEX IF NOT EXISTS idx_invitation_comments_parent ON invitation_comments(invitation_id,parent_id,created_at);
CREATE TABLE IF NOT EXISTS approval_requests(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, requested_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, requested_from TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', note TEXT NOT NULL DEFAULT '', document_revision BIGINT NOT NULL DEFAULT 0, document_fingerprint TEXT NOT NULL DEFAULT '', summary_json TEXT NOT NULL DEFAULT '{}', decided_by TEXT NOT NULL DEFAULT '', decided_at BIGINT, created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS invitation_review_policies(invitation_id TEXT PRIMARY KEY REFERENCES invitations(id) ON DELETE CASCADE, approval_gate INTEGER NOT NULL DEFAULT 0, unresolved_comments_gate INTEGER NOT NULL DEFAULT 0, min_approvals INTEGER NOT NULL DEFAULT 1, updated_by TEXT NOT NULL DEFAULT '', updated_at BIGINT NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS review_notifications(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, actor_id TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, target_id TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '', read_at BIGINT, created_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_review_notifications_user ON review_notifications(user_id,read_at,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_notifications_invite ON review_notifications(invitation_id,user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS review_tasks(comment_id TEXT PRIMARY KEY REFERENCES invitation_comments(id) ON DELETE CASCADE, invitation_id TEXT NOT NULL REFERENCES invitations(id) ON DELETE CASCADE, assignee_id TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'normal', status TEXT NOT NULL DEFAULT 'open', updated_by TEXT NOT NULL DEFAULT '', updated_at BIGINT NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_review_tasks_invite ON review_tasks(invitation_id,status,due_date);
CREATE INDEX IF NOT EXISTS idx_review_tasks_assignee ON review_tasks(assignee_id,status,due_date);
ALTER TABLE invitation_comments ADD COLUMN IF NOT EXISTS page_id TEXT NOT NULL DEFAULT '';
ALTER TABLE invitation_comments ADD COLUMN IF NOT EXISTS parent_id TEXT NOT NULL DEFAULT '';
ALTER TABLE invitation_comments ADD COLUMN IF NOT EXISTS anchor_x DOUBLE PRECISION NOT NULL DEFAULT -1;
ALTER TABLE invitation_comments ADD COLUMN IF NOT EXISTS anchor_y DOUBLE PRECISION NOT NULL DEFAULT -1;
ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS document_revision BIGINT NOT NULL DEFAULT 0;
ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS document_fingerprint TEXT NOT NULL DEFAULT '';
ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS summary_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS decided_by TEXT NOT NULL DEFAULT '';
ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS decided_at BIGINT;

-- V13 protected gallery access.
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS gallery_access_password_hash TEXT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS gallery_access_password_salt TEXT;
CREATE TABLE IF NOT EXISTS gallery_access_tokens (
  token_hash TEXT PRIMARY KEY,
  invitation_id TEXT NOT NULL,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gallery_access_tokens_invite ON gallery_access_tokens(invitation_id, expires_at);

-- V13 marketplace moderation and licensing.
ALTER TABLE user_templates ADD COLUMN IF NOT EXISTS marketplace_status TEXT NOT NULL DEFAULT 'draft';
ALTER TABLE user_templates ADD COLUMN IF NOT EXISTS license_type TEXT NOT NULL DEFAULT 'personal';
CREATE INDEX IF NOT EXISTS idx_marketplace_templates ON user_templates(marketplace_status, visibility, published_at DESC);

-- V29-V32 cumulative professional editor, collaboration, raster, and platform schema.
-- Applied transactionally by platform_v32/schema.py in application deployments.
CREATE TABLE IF NOT EXISTS platform_schema_migrations(
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at BIGINT NOT NULL,
  detail_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS workspaces(
  id TEXT PRIMARY KEY,name TEXT NOT NULL,slug TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL DEFAULT 'personal',owner_id TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'free',settings_json TEXT NOT NULL DEFAULT '{}',
  created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL,deleted_at BIGINT
);
CREATE TABLE IF NOT EXISTS workspace_memberships(
  workspace_id TEXT NOT NULL,user_id TEXT NOT NULL,role TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',permissions_json TEXT NOT NULL DEFAULT '{}',
  created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL,
  PRIMARY KEY(workspace_id,user_id)
);
CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_memberships(user_id,status,updated_at DESC);
CREATE TABLE IF NOT EXISTS collaboration_updates(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL,
  document_epoch INTEGER NOT NULL,actor_id TEXT NOT NULL,logical_clock BIGINT NOT NULL,
  update_type TEXT NOT NULL,path_json TEXT NOT NULL DEFAULT '[]',payload_json TEXT NOT NULL DEFAULT '{}',
  update_bytes INTEGER NOT NULL DEFAULT 0,created_at BIGINT NOT NULL,revision BIGINT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_collab_update_identity ON collaboration_updates(invitation_id,document_epoch,actor_id,logical_clock);
CREATE INDEX IF NOT EXISTS idx_collab_replay ON collaboration_updates(invitation_id,document_epoch,revision);
CREATE TABLE IF NOT EXISTS collaboration_checkpoints(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL,
  document_epoch INTEGER NOT NULL,name TEXT NOT NULL,document_json TEXT NOT NULL,
  fingerprint TEXT NOT NULL,state_vector_json TEXT NOT NULL DEFAULT '{}',
  created_by TEXT NOT NULL,created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_collab_checkpoint ON collaboration_checkpoints(invitation_id,document_epoch,created_at DESC);
CREATE TABLE IF NOT EXISTS raster_edit_documents(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL,
  owner_id TEXT NOT NULL,source_asset_id TEXT NOT NULL,source_asset_version INTEGER NOT NULL DEFAULT 1,
  edit_version INTEGER NOT NULL DEFAULT 1,document_json TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',
  fingerprint TEXT NOT NULL DEFAULT '',preview_asset_id TEXT NOT NULL DEFAULT '',result_asset_id TEXT NOT NULL DEFAULT '',
  created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS platform_jobs(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL DEFAULT '',owner_id TEXT NOT NULL,
  kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',progress DOUBLE PRECISION NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL DEFAULT '{}',result_json TEXT NOT NULL DEFAULT '{}',idempotency_key TEXT NOT NULL DEFAULT '',
  retry_count INTEGER NOT NULL DEFAULT 0,max_retries INTEGER NOT NULL DEFAULT 3,cancellation_requested INTEGER NOT NULL DEFAULT 0,
  error_text TEXT NOT NULL DEFAULT '',created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL,started_at BIGINT,completed_at BIGINT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_job_idempotency ON platform_jobs(workspace_id,idempotency_key) WHERE idempotency_key<>'';
CREATE INDEX IF NOT EXISTS idx_platform_jobs_status ON platform_jobs(status,created_at);
CREATE TABLE IF NOT EXISTS object_versions(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,asset_id TEXT NOT NULL,version INTEGER NOT NULL,
  provider TEXT NOT NULL,object_key TEXT NOT NULL,sha256 TEXT NOT NULL,mime TEXT NOT NULL,size_bytes BIGINT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',visibility TEXT NOT NULL DEFAULT 'private',created_at BIGINT NOT NULL,deleted_at BIGINT,
  UNIQUE(asset_id,version)
);
CREATE TABLE IF NOT EXISTS upload_sessions_v32(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,owner_id TEXT NOT NULL,invitation_id TEXT NOT NULL DEFAULT '',
  object_key TEXT NOT NULL,mime TEXT NOT NULL,size_bytes BIGINT NOT NULL,checksum TEXT NOT NULL DEFAULT '',
  multipart_id TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',parts_json TEXT NOT NULL DEFAULT '[]',
  expires_at BIGINT NOT NULL,created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_records(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,user_id TEXT NOT NULL,operation TEXT NOT NULL,key_value TEXT NOT NULL,
  response_json TEXT NOT NULL DEFAULT '{}',created_at BIGINT NOT NULL,expires_at BIGINT NOT NULL,
  UNIQUE(workspace_id,user_id,operation,key_value)
);
CREATE TABLE IF NOT EXISTS platform_backups(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,owner_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',
  provider TEXT NOT NULL DEFAULT 'local',object_key TEXT NOT NULL DEFAULT '',checksum TEXT NOT NULL DEFAULT '',size_bytes BIGINT NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}',recovery_epoch INTEGER NOT NULL DEFAULT 0,created_at BIGINT NOT NULL,completed_at BIGINT,deleted_at BIGINT
);
CREATE TABLE IF NOT EXISTS privacy_requests(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,user_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',
  scope_json TEXT NOT NULL DEFAULT '{}',result_json TEXT NOT NULL DEFAULT '{}',created_at BIGINT NOT NULL,completed_at BIGINT
);
CREATE TABLE IF NOT EXISTS operational_metrics(
  id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL DEFAULT '',name TEXT NOT NULL,value DOUBLE PRECISION NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '{}',created_at BIGINT NOT NULL
);
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS document_epoch INTEGER NOT NULL DEFAULT 1;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS document_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE user_templates ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE user_page_templates ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE user_components ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE studio_resources ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE studio_releases ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE backup_runs ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE publications ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE publications ADD COLUMN IF NOT EXISTS snapshot_fingerprint TEXT NOT NULL DEFAULT '';
ALTER TABLE publications ADD COLUMN IF NOT EXISTS document_epoch INTEGER NOT NULL DEFAULT 1;
ALTER TABLE publications ADD COLUMN IF NOT EXISTS document_version INTEGER NOT NULL DEFAULT 0;

-- V53 governed AI learning: explicit preferences, feedback, approved knowledge,
-- conversations, plans, jobs, usage, and auditable tool outcomes. Runtime startup
-- also applies these idempotently for existing SQLite and PostgreSQL deployments.
CREATE TABLE IF NOT EXISTS ai_preferences(
  user_id TEXT PRIMARY KEY,enabled INTEGER NOT NULL DEFAULT 1,retention_days INTEGER NOT NULL DEFAULT 30,
  allow_low_risk_auto INTEGER NOT NULL DEFAULT 0,provider_disclosure INTEGER NOT NULL DEFAULT 1,
  feedback_learning INTEGER NOT NULL DEFAULT 1,memory_enabled INTEGER NOT NULL DEFAULT 1,
  knowledge_enabled INTEGER NOT NULL DEFAULT 1,updated_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_conversations(
  id TEXT PRIMARY KEY,invitation_id TEXT NOT NULL,user_id TEXT NOT NULL,title TEXT NOT NULL DEFAULT 'New agent chat',
  status TEXT NOT NULL DEFAULT 'active',provider_mode TEXT NOT NULL DEFAULT 'offline',created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_project ON ai_conversations(invitation_id,user_id,updated_at DESC);
CREATE TABLE IF NOT EXISTS ai_messages(
  id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,sequence INTEGER NOT NULL,role TEXT NOT NULL,
  message_type TEXT NOT NULL,content_json TEXT NOT NULL DEFAULT '{}',created_at BIGINT NOT NULL,
  UNIQUE(conversation_id,sequence)
);
CREATE TABLE IF NOT EXISTS ai_plans(
  id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,invitation_id TEXT NOT NULL,user_id TEXT NOT NULL,
  document_revision BIGINT NOT NULL DEFAULT 0,document_fingerprint TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'proposed',
  plan_json TEXT NOT NULL DEFAULT '{}',confirmation_json TEXT NOT NULL DEFAULT '{}',idempotency_key TEXT NOT NULL DEFAULT '',
  created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_plans_idempotency ON ai_plans(user_id,idempotency_key) WHERE idempotency_key<>'';
CREATE TABLE IF NOT EXISTS ai_jobs(
  id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,plan_id TEXT,invitation_id TEXT NOT NULL,user_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',cancellation_requested INTEGER NOT NULL DEFAULT 0,
  progress_json TEXT NOT NULL DEFAULT '{}',created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_usage_events(
  id TEXT PRIMARY KEY,user_id TEXT NOT NULL,invitation_id TEXT NOT NULL,provider_mode TEXT NOT NULL,
  input_bytes BIGINT NOT NULL DEFAULT 0,output_bytes BIGINT NOT NULL DEFAULT 0,tool_calls INTEGER NOT NULL DEFAULT 0,created_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_feedback(
  id TEXT PRIMARY KEY,message_id TEXT NOT NULL,conversation_id TEXT NOT NULL,invitation_id TEXT NOT NULL,user_id TEXT NOT NULL,
  rating INTEGER NOT NULL,tags_json TEXT NOT NULL DEFAULT '[]',comment TEXT NOT NULL DEFAULT '',remember INTEGER NOT NULL DEFAULT 0,
  created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL,UNIQUE(message_id,user_id)
);
CREATE TABLE IF NOT EXISTS ai_memories(
  id TEXT PRIMARY KEY,user_id TEXT NOT NULL,scope TEXT NOT NULL DEFAULT 'account',invitation_id TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL DEFAULT 'preference',content TEXT NOT NULL,keywords_json TEXT NOT NULL DEFAULT '[]',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 1,source_feedback_id TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'active',
  created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_knowledge_sources(
  id TEXT PRIMARY KEY,user_id TEXT NOT NULL,scope TEXT NOT NULL DEFAULT 'invitation',invitation_id TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,source_type TEXT NOT NULL DEFAULT 'text',content TEXT NOT NULL,keywords_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'active',created_at BIGINT NOT NULL,updated_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_tool_outcomes(
  id TEXT PRIMARY KEY,user_id TEXT NOT NULL,invitation_id TEXT NOT NULL,plan_id TEXT NOT NULL,tool_id TEXT NOT NULL,
  success INTEGER NOT NULL,error_code TEXT NOT NULL DEFAULT '',created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_user ON ai_feedback(user_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_memories_lookup ON ai_memories(user_id,status,invitation_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_lookup ON ai_knowledge_sources(user_id,status,invitation_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_tool_outcomes_user ON ai_tool_outcomes(user_id,tool_id,created_at DESC);

-- V53.1 AI Project Operator persistence additions. These remain idempotent for
-- existing PostgreSQL databases and mirror ai_agent/storage.py runtime schema.
ALTER TABLE ai_preferences ADD COLUMN IF NOT EXISTS feedback_learning INTEGER NOT NULL DEFAULT 1;
ALTER TABLE ai_preferences ADD COLUMN IF NOT EXISTS memory_enabled INTEGER NOT NULL DEFAULT 1;
ALTER TABLE ai_preferences ADD COLUMN IF NOT EXISTS knowledge_enabled INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS ai_design_blueprints(
  id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL,
  reference_asset_ids_json TEXT NOT NULL DEFAULT '[]', mode TEXT NOT NULL DEFAULT 'style',
  provider_mode TEXT NOT NULL DEFAULT 'offline', blueprint_json TEXT NOT NULL DEFAULT '{}',
  created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_blueprints_project
  ON ai_design_blueprints(invitation_id,user_id,updated_at DESC);

CREATE TABLE IF NOT EXISTS ai_verification_results(
  id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL,
  success INTEGER NOT NULL DEFAULT 0, result_json TEXT NOT NULL DEFAULT '{}',
  corrections_json TEXT NOT NULL DEFAULT '[]', created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_verification_plan
  ON ai_verification_results(plan_id,created_at DESC);

CREATE TABLE IF NOT EXISTS ai_local_provider_configs(
  provider_id TEXT PRIMARY KEY, label TEXT NOT NULL, kind TEXT NOT NULL,
  endpoint_label TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, updated_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_model_capabilities(
  provider_id TEXT NOT NULL, model_id TEXT NOT NULL, capability_json TEXT NOT NULL DEFAULT '{}',
  health TEXT NOT NULL DEFAULT 'unknown', last_successful_check BIGINT NOT NULL DEFAULT 0,
  updated_at BIGINT NOT NULL, PRIMARY KEY(provider_id,model_id)
);
