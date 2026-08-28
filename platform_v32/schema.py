from __future__ import annotations
import json,time,uuid
from typing import Any,Callable

SCHEMA_VERSION=18

def now_ms():return int(time.time()*1000)
def uid():return str(uuid.uuid4())

def _try(db,statement,params=()):
    try:db.execute(statement,params);return True
    except Exception:return False


def ensure_personal_workspace(connect: Callable[[],Any], user_id: str) -> str:
    """Provision the personal workspace for a newly created account.

    Schema migration handles users that already exist. Registration must also
    call this helper because readiness probes can initialize the schema before
    the first (or any later) account is created.
    """
    # Some lightweight/legacy startup paths create the core account schema
    # without constructing PlatformService first.  Initialize the additive
    # V32 schema on demand so registration is not dependent on a readiness
    # probe or on which API endpoint happened to be called first.
    schema_ready=True
    try:
        with connect() as db:db.execute("SELECT 1 FROM workspaces LIMIT 1")
    except Exception as exc:
        message=str(exc).lower()
        if "no such table" in message or "does not exist" in message or "undefined table" in message:schema_ready=False
        else:raise
    if not schema_ready:ensure_platform_schema(connect)
    with connect() as db:
        user=db.execute("SELECT id,email,COALESCE(studio_name,'') studio_name,COALESCE(plan,'free') plan FROM users WHERE id=? AND deleted_at IS NULL",(user_id,)).fetchone()
        if not user:raise ValueError("Account not found while provisioning workspace")
        row=db.execute("SELECT id FROM workspaces WHERE owner_id=? AND kind='personal' AND deleted_at IS NULL ORDER BY created_at LIMIT 1",(user_id,)).fetchone()
        if row:workspace_id=row['id']
        else:
            workspace_id=uid();base=(user['studio_name'] or str(user['email']).split('@')[0] or 'Personal workspace')[:100];slug='personal-'+str(user_id).replace('-','')[:20]
            db.execute("INSERT INTO workspaces(id,name,slug,kind,owner_id,plan,settings_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(workspace_id,base,slug,'personal',user_id,user['plan'],'{}',now_ms(),now_ms()))
        db.execute("INSERT INTO workspace_memberships(workspace_id,user_id,role,status,permissions_json,created_at,updated_at) VALUES(?,?,?,'active','{}',?,?) ON CONFLICT(workspace_id,user_id) DO UPDATE SET role=excluded.role,status='active',updated_at=excluded.updated_at",(workspace_id,user_id,'owner',now_ms(),now_ms()))
        return workspace_id

def ensure_platform_schema(connect: Callable[[],Any]) -> None:
    statements=[
    """CREATE TABLE IF NOT EXISTS platform_schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at INTEGER NOT NULL,detail_json TEXT NOT NULL DEFAULT '{}')""",
    """CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,name TEXT NOT NULL,slug TEXT NOT NULL UNIQUE,kind TEXT NOT NULL DEFAULT 'personal',owner_id TEXT NOT NULL,plan TEXT NOT NULL DEFAULT 'free',settings_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,deleted_at INTEGER)""",
    "CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id,deleted_at,updated_at DESC)",
    """CREATE TABLE IF NOT EXISTS workspace_memberships(workspace_id TEXT NOT NULL,user_id TEXT NOT NULL,role TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'active',permissions_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(workspace_id,user_id))""",
    "CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_memberships(user_id,status,updated_at DESC)",
    """CREATE TABLE IF NOT EXISTS collaboration_updates(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL,document_epoch INTEGER NOT NULL,actor_id TEXT NOT NULL,logical_clock INTEGER NOT NULL,update_type TEXT NOT NULL,path_json TEXT NOT NULL DEFAULT '[]',payload_json TEXT NOT NULL DEFAULT '{}',update_bytes INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,revision INTEGER NOT NULL)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_collab_update_identity ON collaboration_updates(invitation_id,document_epoch,actor_id,logical_clock)",
    "CREATE INDEX IF NOT EXISTS idx_collab_replay ON collaboration_updates(invitation_id,document_epoch,revision)",
    """CREATE TABLE IF NOT EXISTS collaboration_checkpoints(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL,document_epoch INTEGER NOT NULL,name TEXT NOT NULL,document_json TEXT NOT NULL,fingerprint TEXT NOT NULL,state_vector_json TEXT NOT NULL DEFAULT '{}',created_by TEXT NOT NULL,created_at INTEGER NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_collab_checkpoint ON collaboration_checkpoints(invitation_id,document_epoch,created_at DESC)",
    """CREATE TABLE IF NOT EXISTS raster_edit_documents(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL,owner_id TEXT NOT NULL,source_asset_id TEXT NOT NULL,source_asset_version INTEGER NOT NULL DEFAULT 1,edit_version INTEGER NOT NULL DEFAULT 1,document_json TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',fingerprint TEXT NOT NULL DEFAULT '',preview_asset_id TEXT NOT NULL DEFAULT '',result_asset_id TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_raster_edit_invitation ON raster_edit_documents(invitation_id,updated_at DESC)",
    """CREATE TABLE IF NOT EXISTS platform_jobs(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,invitation_id TEXT NOT NULL DEFAULT '',owner_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',progress DOUBLE PRECISION NOT NULL DEFAULT 0,payload_json TEXT NOT NULL DEFAULT '{}',result_json TEXT NOT NULL DEFAULT '{}',idempotency_key TEXT NOT NULL DEFAULT '',retry_count INTEGER NOT NULL DEFAULT 0,max_retries INTEGER NOT NULL DEFAULT 3,cancellation_requested INTEGER NOT NULL DEFAULT 0,error_text TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,started_at INTEGER,completed_at INTEGER)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_job_idempotency ON platform_jobs(workspace_id,idempotency_key) WHERE idempotency_key<>''",
    "CREATE INDEX IF NOT EXISTS idx_platform_jobs_status ON platform_jobs(status,created_at)",
    """CREATE TABLE IF NOT EXISTS object_versions(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,asset_id TEXT NOT NULL,version INTEGER NOT NULL,provider TEXT NOT NULL,object_key TEXT NOT NULL,sha256 TEXT NOT NULL,mime TEXT NOT NULL,size_bytes INTEGER NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',visibility TEXT NOT NULL DEFAULT 'private',created_at INTEGER NOT NULL,deleted_at INTEGER,UNIQUE(asset_id,version))""",
    "CREATE INDEX IF NOT EXISTS idx_object_versions_workspace ON object_versions(workspace_id,asset_id,version DESC)",
    """CREATE TABLE IF NOT EXISTS upload_sessions_v32(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,owner_id TEXT NOT NULL,invitation_id TEXT NOT NULL DEFAULT '',object_key TEXT NOT NULL,mime TEXT NOT NULL,size_bytes INTEGER NOT NULL,checksum TEXT NOT NULL DEFAULT '',multipart_id TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',parts_json TEXT NOT NULL DEFAULT '[]',expires_at INTEGER NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS idempotency_records(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,user_id TEXT NOT NULL,operation TEXT NOT NULL,key_value TEXT NOT NULL,response_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,UNIQUE(workspace_id,user_id,operation,key_value))""",
    """CREATE TABLE IF NOT EXISTS platform_backups(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,owner_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',provider TEXT NOT NULL DEFAULT 'local',object_key TEXT NOT NULL DEFAULT '',checksum TEXT NOT NULL DEFAULT '',size_bytes INTEGER NOT NULL DEFAULT 0,metadata_json TEXT NOT NULL DEFAULT '{}',recovery_epoch INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,completed_at INTEGER,deleted_at INTEGER)""",
    "CREATE INDEX IF NOT EXISTS idx_platform_backups_workspace ON platform_backups(workspace_id,created_at DESC)",
    """CREATE TABLE IF NOT EXISTS privacy_requests(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,user_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',scope_json TEXT NOT NULL DEFAULT '{}',result_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL,completed_at INTEGER)""",
    """CREATE TABLE IF NOT EXISTS operational_metrics(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL DEFAULT '',name TEXT NOT NULL,value DOUBLE PRECISION NOT NULL,tags_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_operational_metrics_name ON operational_metrics(name,created_at DESC)",
    ]
    with connect() as db:
        for statement in statements:db.execute(statement)
        _try(db,"ALTER TABLE invitations ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE invitations ADD COLUMN document_epoch INTEGER NOT NULL DEFAULT 1")
        _try(db,"ALTER TABLE invitations ADD COLUMN document_version INTEGER NOT NULL DEFAULT 0")
        _try(db,"ALTER TABLE assets ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE publications ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE publications ADD COLUMN snapshot_fingerprint TEXT NOT NULL DEFAULT ''")
        _try(db,"ALTER TABLE publications ADD COLUMN document_epoch INTEGER NOT NULL DEFAULT 1")
        _try(db,"ALTER TABLE publications ADD COLUMN document_version INTEGER NOT NULL DEFAULT 0")
        _try(db,"CREATE INDEX IF NOT EXISTS idx_publications_workspace ON publications(workspace_id,published_at DESC)")
        _try(db,"ALTER TABLE studio_resources ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE studio_releases ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE user_templates ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE user_page_templates ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE user_components ADD COLUMN workspace_id TEXT")
        _try(db,"ALTER TABLE backup_runs ADD COLUMN workspace_id TEXT")
        for table in ('user_templates','user_page_templates','user_components','studio_resources','studio_releases','backup_runs'):
            _try(db,f"CREATE INDEX IF NOT EXISTS idx_{table}_workspace_v32 ON {table}(workspace_id)")
        users=db.execute("SELECT id,email,COALESCE(studio_name,'') studio_name,COALESCE(plan,'free') plan FROM users WHERE deleted_at IS NULL").fetchall()
        for user in users:
            row=db.execute("SELECT id FROM workspaces WHERE owner_id=? AND kind='personal' AND deleted_at IS NULL ORDER BY created_at LIMIT 1",(user['id'],)).fetchone()
            if row:workspace_id=row['id']
            else:
                workspace_id=uid();base=(user['studio_name'] or str(user['email']).split('@')[0] or 'Personal workspace')[:100];slug='personal-'+str(user['id']).replace('-','')[:20]
                db.execute("INSERT INTO workspaces(id,name,slug,kind,owner_id,plan,settings_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(workspace_id,base,slug,'personal',user['id'],user['plan'],'{}',now_ms(),now_ms()))
            db.execute("INSERT INTO workspace_memberships(workspace_id,user_id,role,status,permissions_json,created_at,updated_at) VALUES(?,?,?,'active','{}',?,?) ON CONFLICT(workspace_id,user_id) DO UPDATE SET role=excluded.role,status='active',updated_at=excluded.updated_at",(workspace_id,user['id'],'owner',now_ms(),now_ms()))
            db.execute("UPDATE invitations SET workspace_id=? WHERE owner_id=? AND (workspace_id IS NULL OR workspace_id='')",(workspace_id,user['id']))
            db.execute("UPDATE assets SET workspace_id=? WHERE invitation_id IN (SELECT id FROM invitations WHERE owner_id=?) AND (workspace_id IS NULL OR workspace_id='')",(workspace_id,user['id']))
            for table in ('user_templates','user_page_templates','user_components','studio_resources','studio_releases'):
                db.execute(f"UPDATE {table} SET workspace_id=? WHERE owner_id=? AND (workspace_id IS NULL OR workspace_id='')",(workspace_id,user['id']))
            db.execute("UPDATE backup_runs SET workspace_id=? WHERE owner_id=? AND (workspace_id IS NULL OR workspace_id='')",(workspace_id,user['id']))
        db.execute("INSERT INTO platform_schema_migrations(version,name,applied_at,detail_json) VALUES(?,?,?,?) ON CONFLICT(version) DO UPDATE SET name=excluded.name,detail_json=excluded.detail_json",(SCHEMA_VERSION,'V29-V32 cumulative platform schema',now_ms(),json.dumps({'documentSchema':18,'milestones':['V29','V30','V31','V32']},separators=(',',':'))))
