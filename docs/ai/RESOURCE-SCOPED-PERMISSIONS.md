# Resource-Scoped Permissions — Design & Migration Plan

> **Status**: Phase 1a design document.
> **Scope**: Replace the coarse tier-based `read`/`edit`/`manage`/`admin` permission model in `ai_agent/capabilities.py` with resource-scoped grants like `event:{id}:publish`, `guest:{id}:delete`, `template:{id}:edit`.
> **AISVS driver**: C9.2.6 (permission tiers must reflect the underlying role model and not be hardcoded per agent), C10.3.1 (tool invocations must be scoped to a specific resource and reject cross-resource access).
> **Codebase ground truth**:
> - Current permission model: `ai_agent/capabilities.py:ROLE_PERMISSIONS` (lines 18-23).
> - Current capability discovery: `ai_agent/capabilities.py:availability()` (lines 231-255).
> - Current authorization layer: `ai_agent/service.py:authorize_tool_call()` (lines 421-458) + `consume_tool_authorization()` (lines 460-487).
> - Platform role model: `platform_v32/service.py:ROLE_PERMISSIONS` (lines 16-18) — finer-grained (`read/comment/edit-content/edit-design/assets/publish/manage-members/backup`).
> - Workspace membership: `platform_v32/service.py:membership()` (line 42) and `authorize()` (line 44).

## 1. Current state (as of V53.1)

### 1.1 Permission tier declarations

Each `ToolDefinition` in `ai_agent/tools.py` declares a `permission` field with one of four values:

| Tier | Allowed collaboration roles | Allowed account roles |
|---|---|---|
| `read` | `owner`, `manager`, `designer`, `content`, `viewer` | any |
| `edit` | `owner`, `manager`, `designer`, `content` | any |
| `manage` | `owner`, `manager` | any |
| `admin` | (none via collaboration) | `admin` only (per `ai_agent/capabilities.py:availability()` line 238-239) |

### 1.2 Discovery-time enforcement

`ai_agent/capabilities.py:availability()` (lines 231-255) filters the tool catalog by:
1. Workspace AI policy (`workspacePolicyEnabled`).
2. Admin-tier check (`accountRole == "admin"`).
3. Collaboration role membership (`role in ROLE_PERMISSIONS[permission]`).
4. Upload gate (`upload_enabled` + storage quota) for `UPLOAD_TOOL_IDS`.
5. Archive gate (`archived` flag) for `edit`/`manage` tools (except `EDIT_WHILE_ARCHIVED = {"invitation.archive"}`).
6. Feature-table existence for `events`/`plugins`/`animation`/`publishingDomains`/`dataMerge`/`marketplace` feature groups.

### 1.3 Execution-time enforcement

`ai_agent/service.py:authorize_tool_call()` re-checks:
1. Plan status (`confirmed`).
2. Exact tool index within the plan.
3. `clientCallId` match.
4. `assert_calls_available([call], access_snapshot)` — re-runs `availability()` for the single call.
5. Document revision + fingerprint match (stale-plan rejection).

`consume_tool_authorization()` then verifies:
1. Token exists in `self._tool_authorizations`.
2. Token not expired (30-second TTL).
3. `userId`, `invitationId`, `toolId` match the planned values via `secrets.compare_digest`.
4. `http_request_matches_tool(tool_id, method, path, invitation_id)` — the HTTP request matches the declared binding.

### 1.4 Limitations of the current model

1. **Coarse tiers**: a `manager` has blanket `manage` permission on every invitation they collaborate on. There is no way to grant `manage` on invitation A without also granting it on invitation B.
2. **No resource-scoped grants**: there is no `invitation:{id}:publish` grant that survives a single plan. A user who can `publish` once can `publish` again on any invitation they manage.
3. **No JIT elevation**: high-risk operations rely on `destructiveAccepted` confirmation and the 30-second authorization token, but the standing grant remains "user has `manage` on the invitation." (See `docs/ai/JIT-ELEVATION.md` for the separate JIT design.)
4. **Misalignment with platform role model**: the platform's `ROLE_PERMISSIONS` (in `platform_v32/service.py`) is finer-grained (`read/comment/edit-content/edit-design/assets/publish/manage-members/backup`) and supports per-resource custom permissions via `permissions_json`. The agent model is a coarse subset.
5. **No plugin scope**: when the Phase 4a plugin marketplace lands, plugins will need their own permission scopes (`plugin:{pluginKey}:{permission}`). The current model cannot express this.
6. **Cross-instance revocation gap**: the in-memory `self._tool_authorizations` dict (line 44) is per-process. In a multi-instance deployment, an authorization token issued by instance A cannot be revoked from instance B. (The `jit_elevations` table in `docs/ai/JIT-ELEVATION.md` addresses this.)

## 2. Target state

### 2.1 Grant syntax

```
{resource_type}:{resource_id}:{action}[:{sub_resource}[:{sub_id}]]
```

Examples:

| Grant | Meaning |
|---|---|
| `invitation:{invitationId}:read` | Read access to a specific invitation (read-only). |
| `invitation:{invitationId}:edit` | Edit access to a specific invitation (editor mutations). |
| `invitation:{invitationId}:publish` | Publish / unpublish a specific invitation. |
| `invitation:{invitationId}:archive` | Archive / unarchive a specific invitation. |
| `invitation:{invitationId}:custom-domain:set` | Set a custom domain on a specific invitation. |
| `invitation:{invitationId}:guest:create` | Create guests under a specific invitation. |
| `invitation:{invitationId}:guest:{guestId}:delete` | Delete a specific guest under a specific invitation. |
| `invitation:{invitationId}:guest:{guestId}:update` | Update a specific guest. |
| `invitation:{invitationId}:message:prepare` | Prepare a guest message (does not authorize send). |
| `invitation:{invitationId}:message:send` | Dispatch a guest message (separate grant). |
| `invitation:{invitationId}:rsvp:update` | Update RSVP state. |
| `invitation:{invitationId}:materials:import` | Import a materials archive. |
| `invitation:{invitationId}:materials:{assetId}:move` | Move a specific material. |
| `invitation:{invitationId}:asset:{assetId}:insert` | Insert a specific asset into a page. |
| `workspace:{workspaceId}:publishing:environment:create` | Create a publishing environment. |
| `workspace:{workspaceId}:publishing:environment:promote` | Promote an environment to production (most sensitive). |
| `workspace:{workspaceId}:enterprise:protocol:create:{classification}` | Create an enterprise protocol at a specific classification. |
| `workspace:{workspaceId}:marketplace:install` | Install a marketplace template. |
| `workspace:{workspaceId}:plugin:install` | Install a plugin (Phase 4a). |
| `workspace:{workspaceId}:data-merge:prepare` | Prepare a data-merge job. |
| `workspace:{workspaceId}:data-merge:execute` | Execute a data-merge job (separate grant). |
| `workspace:{workspaceId}:event-automation:create` | Create an event automation. |
| `workspace:{workspaceId}:event-automation:enable` | Enable a trigger (most sensitive). |
| `template:{templateId}:edit` | Edit a template (Phase 4a). |
| `template:{templateId}:instantiate` | Use a template as the basis for a new invitation. |
| `plugin:{pluginKey}:{permission}` | Plugin-specific permission scope (Phase 4a). |
| `event:{eventId}:manage` | Manage an event (Phase 4a event ecosystem). |

### 2.2 Grant lifecycle

Every grant is one of:

| Lifecycle | Description |
|---|---|
| **Standing** | Long-lived, persisted in the database. Survives session expiry. Examples: `invitation:{id}:edit` for a `manager`. |
| **Session** | Tied to an active user session. Expires when the session expires. |
| **JIT** | Short-lived (5-minute TTL). Requires explicit request + reason + audit event. See `docs/ai/JIT-ELEVATION.md`. |
| **One-shot** | Single-use. The 30-second authorization token in `consume_tool_authorization()` is one-shot. |

The current 30-second authorization token remains as a **one-shot** layer on top of any standing / session / JIT grant. This preserves the existing two-layer enforcement (standing tier + one-shot token).

### 2.3 Tool → required grant mapping

Each `ToolDefinition` declares its required grant(s) — replacing the `permission` field. The grant can be:

- **Static** (the same grant for every invocation): e.g. `read.project_summary` requires `invitation:{invitationId}:read`.
- **Dynamic** (the grant depends on the tool's arguments): e.g. `guest.delete` requires `invitation:{invitationId}:guest:{guestId}:delete` — the `guestId` comes from the tool arguments.
- **Multiple** (the tool requires more than one grant): e.g. `invitation.update_operations` with `customDomain != ""` requires both `invitation:{invitationId}:update-operations` AND `invitation:{invitationId}:custom-domain:set`.

See §5 for the per-tool grant table.

## 3. Migration plan

The migration must not break existing sessions. The plan is staged over three deployments.

### 3.1 Stage 1 — Schema + grant table (additive, no behavior change)

**Deployment**: Phase 1a patch release.
**Risk**: zero (additive only).

- Add the `agent_grants` table (see §4.1).
- Add the `grant_evaluations` table (see §4.2) for caching.
- Add the new `ResourceScope` parser (`ai_agent/scopes.py` — see §6).
- Add the new `evaluate_grant()` function in `ai_agent/capabilities.py` — but do NOT call it from the existing `availability()` yet. It runs alongside as a no-op shadow evaluation that logs any disagreement with the legacy `ROLE_PERMISSIONS` check.

**Acceptance**: schema migration runs cleanly on SQLite + PostgreSQL; shadow evaluation logs zero disagreements on the test suite.

### 3.2 Stage 2 — Dual evaluation (warning mode)

**Deployment**: Phase 1a minor release.
**Risk**: low (warnings only; no denials).

- `availability()` calls both the legacy `ROLE_PERMISSIONS` check AND the new `evaluate_grant()` check.
- If they disagree, log a `grant_evaluation_disagreement` audit event with both results.
- The legacy check remains authoritative; the new check is informational.
- Add an admin dashboard widget showing disagreement counts over the last 7 days.
- Run for 2 weeks in production to collect data.

**Acceptance**: zero disagreements on production traffic for 14 consecutive days.

### 3.3 Stage 3 — New check authoritative, legacy as fallback

**Deployment**: Phase 1a major release.
**Risk**: medium (behavior change).

- `evaluate_grant()` becomes authoritative.
- The legacy `ROLE_PERMISSIONS` check is retained as a fallback: if `evaluate_grant()` returns `False` BUT the legacy check returns `True`, the call is allowed (logged as `legacy_grant_overrode_new`).
- Standing grants are populated for every existing collaborator: `invitation_collaborators.role` is converted to the equivalent grant set (see §4.3 migration script).
- The `permission` field on `ToolDefinition` is deprecated (still present for backward compatibility with serialized plans) but no longer consulted.

**Acceptance**: zero `legacy_grant_overrode_new` audit events for 30 consecutive days. After this, Stage 4 can proceed.

### 3.4 Stage 4 — Legacy fallback removed

**Deployment**: Phase 1b.
**Risk**: low (legacy check is already not firing).

- Remove the `ROLE_PERMISSIONS` fallback from `availability()`.
- Remove the `permission` field from `ToolDefinition.public()` (keep it on the internal dataclass for backward compat with serialized plans).
- Update `tests/v28_agent_tool_contract_test.py` to assert that every tool declares a `required_grants` field.

**Acceptance**: legacy code paths removed; all tests pass.

## 4. Schema changes

### 4.1 New table: `agent_grants`

Stores standing + session + JIT grants. JIT grants have a non-null `expires_at`.

```sql
CREATE TABLE IF NOT EXISTS agent_grants(
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL DEFAULT '',
    resource_type TEXT NOT NULL,        -- 'invitation' | 'workspace' | 'template' | 'plugin' | 'event'
    resource_id TEXT NOT NULL,          -- the {id} in the grant
    action TEXT NOT NULL,               -- 'read' | 'edit' | 'publish' | 'archive' | 'guest:delete' | ...
    sub_resource TEXT NOT NULL DEFAULT '', -- 'guest' | 'asset' | 'environment' | '' (top-level)
    sub_id TEXT NOT NULL DEFAULT '',    -- the {subId} or '' for wildcard
    lifecycle TEXT NOT NULL DEFAULT 'standing',  -- 'standing' | 'session' | 'jit' | 'one-shot'
    source TEXT NOT NULL DEFAULT 'role',  -- 'role' (derived from collaboration role) | 'explicit' (manually granted) | 'jit' (JIT elevation)
    reason TEXT NOT NULL DEFAULT '',     -- required when lifecycle='jit'
    granted_by TEXT NOT NULL DEFAULT '', -- userId who granted (or '' for system-derived)
    granted_at INTEGER NOT NULL,
    expires_at INTEGER,                 -- NULL for 'standing'; non-NULL for 'session' / 'jit'
    revoked_at INTEGER,                  -- NULL if not revoked
    revoked_by TEXT NOT NULL DEFAULT '',
    revoke_reason TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_agent_grants_lookup ON agent_grants(user_id, resource_type, resource_id, action, sub_resource, sub_id, revoked_at);
CREATE INDEX IF NOT EXISTS idx_agent_grants_expiry ON agent_grants(expires_at) WHERE expires_at IS NOT NULL AND revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_agent_grants_workspace ON agent_grants(workspace_id, resource_type, revoked_at);
```

### 4.2 New table: `grant_evaluations` (cache, optional)

Caches the result of `evaluate_grant()` for a short TTL (default 60s) to avoid re-querying on every tool call.

```sql
CREATE TABLE IF NOT EXISTS grant_evaluations(
    cache_key TEXT PRIMARY KEY,         -- sha256(user_id|resource_type|resource_id|action|sub_resource|sub_id|plan_revision)
    user_id TEXT NOT NULL,
    result INTEGER NOT NULL,            -- 1 = allowed, 0 = denied
    reason TEXT NOT NULL DEFAULT '',
    evaluated_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grant_evaluations_expiry ON grant_evaluations(expires_at);
```

### 4.3 Migration script: existing collaborators → standing grants

Run once at Stage 3 deployment. Converts existing collaboration roles into standing grants.

```python
# scripts/migrate_grants_from_roles.py (illustrative; not committed in Phase 1a)
ROLE_GRANT_MAP = {
    "owner": ["invitation:{id}:read", "invitation:{id}:edit", "invitation:{id}:publish",
              "invitation:{id}:archive", "invitation:{id}:custom-domain:set",
              "invitation:{id}:guest:create", "invitation:{id}:guest:delete",
              "invitation:{id}:message:prepare", "invitation:{id}:message:send",
              "invitation:{id}:rsvp:update", "invitation:{id}:materials:import",
              "invitation:{id}:materials:move", "invitation:{id}:asset:insert"],
    "manager": ["invitation:{id}:read", "invitation:{id}:edit", "invitation:{id}:publish",
                "invitation:{id}:archive", "invitation:{id}:guest:create",
                "invitation:{id}:guest:delete", "invitation:{id}:message:prepare",
                "invitation:{id}:message:send", "invitation:{id}:rsvp:update",
                "invitation:{id}:materials:import"],
    "designer": ["invitation:{id}:read", "invitation:{id}:edit", "invitation:{id}:materials:move",
                 "invitation:{id}:asset:insert"],
    "content": ["invitation:{id}:read", "invitation:{id}:edit"],
    "viewer": ["invitation:{id}:read"],
}
```

Workspace roles map similarly via `platform_v32/service.py:ROLE_PERMISSIONS`:

```python
WORKSPACE_ROLE_GRANT_MAP = {
    "owner": ["workspace:{id}:*"],  # wildcard — owner has every workspace grant
    "manager": ["workspace:{id}:publishing:environment:create",
                "workspace:{id}:marketplace:install", "workspace:{id}:plugin:install",
                "workspace:{id}:data-merge:prepare", "workspace:{id}:data-merge:execute",
                "workspace:{id}:event-automation:create", "workspace:{id}:event-automation:enable",
                "workspace:{id}:enterprise:protocol:create:public",
                "workspace:{id}:enterprise:protocol:create:internal",
                "workspace:{id}:enterprise:protocol:create:restricted"],
    # confidential protocol creation requires explicit grant (not derived from role)
    "designer": ["workspace:{id}:marketplace:install"],
    "content-editor": [],
    "reviewer": [],
    "viewer": [],
}
```

### 4.4 New table: `agent_grant_requests` (audit trail for manual grants)

When an administrator manually grants a permission to a user (outside the role-derived flow), the request is logged.

```sql
CREATE TABLE IF NOT EXISTS agent_grant_requests(
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,             -- the recipient
    requested_by TEXT NOT NULL,        -- the requestor (often same as user_id)
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,
    sub_resource TEXT NOT NULL DEFAULT '',
    sub_id TEXT NOT NULL DEFAULT '',
    lifecycle TEXT NOT NULL,           -- 'standing' | 'session'
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'approved' | 'denied' | 'expired'
    reviewed_by TEXT NOT NULL DEFAULT '',
    reviewed_at INTEGER,
    reviewed_reason TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_grant_requests_status ON agent_grant_requests(status, created_at DESC);
```

## 5. Per-tool required grants

Each tool's `required_grants` field is a function of the tool's arguments. The grant resolver returns a list of grant tuples; **all** must evaluate `True` for the tool to be authorized.

| Tool ID | Required grant(s) | Notes |
|---|---|---|
| `read.project_summary` | `invitation:{invitationId}:read` | |
| `read.page_summary` | `invitation:{invitationId}:read` | |
| `read.selection_summary` | `invitation:{invitationId}:read` | |
| `selection.select_layers` | `invitation:{invitationId}:edit` | |
| `object.create_text` | `invitation:{invitationId}:edit` | |
| `object.create_image` | `invitation:{invitationId}:edit` + `invitation:{invitationId}:asset:{assetId}:read` | the assetId comes from the arguments |
| `object.create_shape` | `invitation:{invitationId}:edit` | |
| `object.update` | `invitation:{invitationId}:edit` | |
| `object.duplicate` | `invitation:{invitationId}:edit` | |
| `object.delete` | `invitation:{invitationId}:edit` + `invitation:{invitationId}:object:delete` | the second grant is a more specific destructive-delete grant |
| `rich_text.replace` | `invitation:{invitationId}:edit` | |
| `transform.*` (9 tools) | `invitation:{invitationId}:edit` | |
| `style.apply_text_style` | `invitation:{invitationId}:edit` | |
| `style.apply_palette` | `invitation:{invitationId}:edit` | |
| `style.apply_brand_kit` | `invitation:{invitationId}:edit` + `workspace:{workspaceId}:brand-kit:{brandKitId}:read` | the brandKitId comes from the arguments |
| `style.apply_photo` | `invitation:{invitationId}:edit` | |
| `photo.remove_background` | `invitation:{invitationId}:edit` + `invitation:{invitationId}:materials:create` | the second grant authorizes the derivative asset |
| `image.configure_frame` | `invitation:{invitationId}:edit` | |
| `gallery.arrange` | `invitation:{invitationId}:edit` | |
| `page.create` | `invitation:{invitationId}:edit` | |
| `page.duplicate` | `invitation:{invitationId}:edit` | |
| `page.rename` | `invitation:{invitationId}:edit` | |
| `page.reorder` | `invitation:{invitationId}:edit` | |
| `page.configure_style` | `invitation:{invitationId}:edit` | |
| `invitation.configure_opening` | `invitation:{invitationId}:edit` | |
| `invitation.archive` | `invitation:{invitationId}:archive` | separate grant — high-risk |
| `invitation.update_operations` | `invitation:{invitationId}:operations:update` + (if `customDomain != ""`) `invitation:{invitationId}:custom-domain:set` | conditional grant |
| `invitation.configure_rsvp` | `invitation:{invitationId}:rsvp:configure` | |
| `event.update_fields` | `invitation:{invitationId}:edit` | |
| `event.configure_details` | `invitation:{invitationId}:edit` | |
| `event.update_schedule` | `invitation:{invitationId}:edit` | |
| `event.create_task` | `invitation:{invitationId}:edit` | creates an event task — currently edit-tier |
| `event.run_intelligence` | `invitation:{invitationId}:read` | read-only analysis |
| `event.prepare_automation` | `workspace:{workspaceId}:event-automation:create` + JIT `workspace:{workspaceId}:event-automation:enable` | JIT required because of chain-reaction risk |
| `guest.create` | `invitation:{invitationId}:guest:create` + JIT `invitation:{invitationId}:guest:create` (if `risk=high` per row count > 50) | |
| `guest.update` | `invitation:{invitationId}:guest:{guestId}:update` | per-guest scoped |
| `guest.delete` | `invitation:{invitationId}:guest:{guestId}:delete` + JIT `invitation:{invitationId}:guest:delete` | per-guest scoped + JIT |
| `guest.check_in` | `invitation:{invitationId}:guest:{guestId}:update` | check-in is a sub-action of update |
| `guest.read_delivery_status` | `invitation:{invitationId}:guest:read` | |
| `rsvp.update` | `invitation:{invitationId}:rsvp:{rsvpId}:update` | per-RSVP scoped |
| `analytics.read_summary` | `invitation:{invitationId}:read` | |
| `account.read_usage` | `account:{userId}:read` | self-scope; only the user can read their own usage |
| `materials.list_folders` | `invitation:{invitationId}:materials:read` | |
| `materials.create_folder` | `invitation:{invitationId}:materials:create` | |
| `materials.import_folder` | `invitation:{invitationId}:materials:import` + JIT (if total bytes > 50 MB) | |
| `materials.import_zip` | `invitation:{invitationId}:materials:import` + JIT (if file count > 100) | |
| `materials.move` | `invitation:{invitationId}:materials:{assetId}:move` | per-asset scoped |
| `materials.rename` | `invitation:{invitationId}:materials:{assetId}:update` | per-asset scoped |
| `materials.update_metadata` | `invitation:{invitationId}:materials:{assetId}:update` | per-asset scoped |
| `materials.classify` | `invitation:{invitationId}:materials:update` | bulk — applies to multiple assets |
| `materials.find_duplicates` | `invitation:{invitationId}:materials:read` | read-only |
| `materials.insert_into_page` | `invitation:{invitationId}:asset:{assetId}:insert` + `invitation:{invitationId}:edit` | |
| `design.analyze_reference` | `invitation:{invitationId}:edit` | |
| `design.apply_blueprint` | `invitation:{invitationId}:edit` (mode=`style`/`palette`/`typography`) OR `workspace:{workspaceId}:invitation:create` (mode=`create`) | conditional on mode |
| `asset.search` | `workspace:{workspaceId}:asset:search` | workspace-scoped |
| `asset.insert` | `invitation:{invitationId}:asset:{assetId}:insert` + `invitation:{invitationId}:edit` | |
| `check.*` (4 tools) | `invitation:{invitationId}:read` | read-only diagnostics |
| `fix.apply` | `invitation:{invitationId}:edit` + `invitation:{invitationId}:fix:apply` | second grant is fix-specific |
| `preview.prepare` | `invitation:{invitationId}:read` | |
| `export.prepare` | `invitation:{invitationId}:export:prepare` + JIT (if format=`backup`) | backup-format export discloses the full document |
| `publish.prepare` | `invitation:{invitationId}:publish` + JIT `invitation:{invitationId}:publish` | standing + JIT |
| `message.prepare_send` | `invitation:{invitationId}:message:prepare` + JIT `invitation:{invitationId}:message:send` (separate grant) | the prepare grant does NOT authorize the send grant |
| `editor.apply_workspace` | `invitation:{invitationId}:edit` | |
| `marketplace.install_template` | `workspace:{workspaceId}:marketplace:install` + JIT | |
| `enterprise.prepare_protocol` | `workspace:{workspaceId}:enterprise:protocol:create:{classification}` + JIT (if classification=`confidential`) | classification is part of the grant |
| `animation.update_timeline` | `invitation:{invitationId}:edit` | |
| `publishing.configure_environment` | `workspace:{workspaceId}:publishing:environment:create` + JIT `workspace:{workspaceId}:publishing:environment:promote` (if environmentType=`production`) | conditional grant |
| `merge.prepare_job` | `workspace:{workspaceId}:data-merge:prepare` + JIT `workspace:{workspaceId}:data-merge:execute` (separate grant) + JIT (if rowCount > 100) | row-count threshold |
| `plugin.configure` | `workspace:{workspaceId}:plugin:install` + JIT + plugin scope `plugin:{pluginKey}:{permission}` for each declared permission | |

## 6. Authorization layer changes

### 6.1 New module: `ai_agent/scopes.py`

Parses and matches grant strings. Pure functions, no I/O.

```python
# ai_agent/scopes.py (illustrative skeleton — not committed in Phase 1a)
from __future__ import annotations
import re
from dataclasses import dataclass

GRANT_RE = re.compile(
    r"^(?P<resource_type>[a-z][a-z0-9-]*):"
    r"(?P<resource_id>[^:]+):"
    r"(?P<action>[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)*)$"
)

@dataclass(frozen=True)
class Grant:
    resource_type: str   # 'invitation' | 'workspace' | 'template' | 'plugin' | 'event' | 'account'
    resource_id: str     # the {id} or '*'
    action: str           # 'read' | 'edit' | 'publish' | 'guest:delete' | ...
    sub_resource: str = ""
    sub_id: str = ""

    @classmethod
    def parse(cls, grant_str: str) -> "Grant":
        m = GRANT_RE.fullmatch(grant_str)
        if not m:
            raise ValueError(f"Invalid grant syntax: {grant_str!r}")
        action = m.group("action")
        parts = action.split(":", 1)
        if len(parts) == 2:
            return cls(m.group("resource_type"), m.group("resource_id"), parts[0], parts[1], "")  # sub_resource only
        return cls(m.group("resource_type"), m.group("resource_id"), action)

    def matches(self, other: "Grant") -> bool:
        """Return True if `self` (a granted permission) satisfies `other` (a required permission)."""
        if self.resource_type != other.resource_type:
            return False
        if self.resource_id != "*" and self.resource_id != other.resource_id:
            return False
        if self.action != "*" and self.action != other.action:
            return False
        if other.sub_resource and self.sub_resource != "*" and self.sub_resource != other.sub_resource:
            return False
        if other.sub_id and self.sub_id != "*" and self.sub_id != other.sub_id:
            return False
        return True
```

### 6.2 New function: `evaluate_grant()` in `ai_agent/capabilities.py`

```python
# ai_agent/capabilities.py (additions — not yet wired in Phase 1a)
def evaluate_grant(connect, user_id, required_grant, plan_revision=0):
    """Return (allowed: bool, reason: str) for a single required grant.

    Standing + session + JIT grants are all evaluated. Revoked grants are excluded.
    JIT grants that have expired are excluded.
    """
    from .scopes import Grant
    grant = Grant.parse(required_grant) if isinstance(required_grant, str) else required_grant
    now_ms = int(time.time() * 1000)
    with connect() as db:
        rows = db.execute("""
            SELECT id, action, sub_resource, sub_id, lifecycle, expires_at, revoked_at
              FROM agent_grants
             WHERE user_id = ?
               AND resource_type = ?
               AND (resource_id = ? OR resource_id = '*')
               AND revoked_at IS NULL
               AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, grant.resource_type, grant.resource_id, now_ms)).fetchall()
    for row in rows:
        granted = Grant(grant.resource_type, grant.resource_id, row["action"], row["sub_resource"], row["sub_id"])
        if granted.matches(grant):
            return True, ""
    return False, f"no grant satisfies {required_grant}"
```

### 6.3 Wiring into `availability()` and `authorize_tool_call()`

The migration is staged (§3). At Stage 3, `availability()` calls `evaluate_grant()` for each `required_grants` entry. The legacy `ROLE_PERMISSIONS` check is retained as a fallback.

At Stage 4, `permission` field on `ToolDefinition` is removed from `public()` and from the `availability()` decision path.

### 6.4 Cross-instance revocation

In a multi-instance deployment, the in-memory `self._tool_authorizations` dict in `ai_agent/service.py:44` is per-process. To revoke an authorization token from another instance:

1. Write a `revoked_at` timestamp to the `agent_grants` row corresponding to the JIT grant (or to a new `agent_authorization_revocations` table).
2. Each instance polls for revocations every 5 seconds (or subscribes to a Redis pub/sub channel) and clears matching entries from its in-memory cache.
3. The 30-second TTL on the authorization token bounds the maximum delay before a revocation takes effect.

## 7. Test plan

### 7.1 New tests (Phase 1a Stage 1)

- `tests/agent_grants_contract_test.py` — table exists, indexes exist, migration runs cleanly on SQLite + PostgreSQL.
- `tests/agent_scopes_test.py` — `Grant.parse()` + `Grant.matches()` for every syntax variant in §2.1.
- `tests/agent_evaluate_grant_test.py` — standing / session / JIT / revoked / expired cases.

### 7.2 Updated tests (Phase 1a Stage 3)

- `tests/v28_agent_tool_contract_test.py` — assert every tool declares `required_grants`.
- `tests/v28_agent_server_contract_test.py` — assert `evaluate_grant()` is consulted during `authorize_tool_call()`.
- `tests/v28_agent_storage_test.py` — assert JIT grants are written to `agent_grants` with `lifecycle='jit'`.

### 7.3 Shadow-evaluation tests (Phase 1a Stage 2)

- `tests/agent_grant_shadow_test.py` — run the test suite with shadow evaluation enabled; assert zero disagreements.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Migration breaks an active session. | Stage 1 is additive only (no behavior change). Stage 3 keeps the legacy check as a fallback for 30 days. |
| Performance regression from per-call grant lookup. | 60-second cache in `grant_evaluations` table. Index on `(user_id, resource_type, resource_id, action)`. |
| Grant table grows unbounded. | Add a daily cron to delete grants older than `EINVITE_AGENT_GRANT_RETENTION_DAYS` (default 365) where `lifecycle='standing'` and the corresponding collaboration role has been removed. |
| JIT grants leak across instances. | `agent_grants` is the source of truth; in-memory cache is a performance optimization only. |
| Plugin scope (`plugin:{pluginKey}:{permission}`) is not yet defined. | Phase 4a (`docs/ROADMAP.md` §7) defines the plugin manifest format. The `Grant` parser already supports the `plugin:...` syntax. |

## 9. Acceptance criteria

- [ ] `agent_grants` table exists on SQLite + PostgreSQL.
- [ ] `Grant.parse()` + `Grant.matches()` pass the unit test for every syntax variant in §2.1.
- [ ] `evaluate_grant()` returns the correct result for standing / session / JIT / revoked / expired cases.
- [ ] Shadow evaluation runs for 14 consecutive days with zero disagreements on production traffic.
- [ ] Per-tool `required_grants` field is declared for all 80 tools.
- [ ] `legacy_grant_overrode_new` audit events are zero for 30 consecutive days.
- [ ] Legacy `ROLE_PERMISSIONS` fallback removed (Stage 4).
- [ ] AISVS C9.2.6 + C10.3.1 status upgraded from `partial` to `pass` in `docs/ai/AISVS-C9-C10-MAPPING.md`.
