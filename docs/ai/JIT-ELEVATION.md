# JIT (Just-In-Time) Elevation — Design

> **Status**: Phase 1a design document + skeleton implementation in `ai_agent/jit_elevation.py`.
> **Scope**: Replace standing high-risk permissions with short-lived (5-minute TTL) grants for `publish`, `delete`, `bulk_*` operations.
> **AISVS driver**: C10.3.2 (standing permission grants must be minimized; high-risk operations must use just-in-time elevation), C10.3.4 (revocation of granted permissions mid-session).
> **Codebase ground truth**:
> - Existing authorization token: `ai_agent/service.py:authorize_tool_call()` (30-second single-use token).
> - Existing audit log: `audit_events` table (hash-chained, immutable — `src/python/server.py:1137`, triggers at `src/python/server.py:1206-1207`).
> - Existing permission tiers: `ai_agent/capabilities.py:ROLE_PERMISSIONS`.
> - High-risk tools (`risk="high"`): `object.delete`, `guest.delete`, `invitation.archive`, `invitation.update_operations`, `rsvp.update` (no — that's medium), `export.prepare`, `publish.prepare`, `message.prepare_send`, `publishing.configure_environment`, `merge.prepare_job`, `plugin.configure`, `event.prepare_automation`.

## 1. Goals

1. **No standing high-risk permission**: a user with `manage` on an invitation does NOT automatically have the right to publish / delete / bulk-operate. Each high-risk operation requires a separate, time-bounded grant.
2. **5-minute TTL**: JIT grants expire after 5 minutes. Re-elevation is required for the next operation.
3. **Audit trail**: every elevation request, grant, denial, expiry, and revocation is recorded as an immutable, hash-chained audit event.
4. **Cross-instance revocation**: a JIT grant can be revoked from any server instance, not just the one that issued it. The grant table is the source of truth; in-memory caches are bounded by the TTL.
5. **Auto-approval policy**: low-impact JIT requests (e.g. a single `guest.delete` on an invitation the user manages) can be auto-approved by policy. High-impact requests (e.g. `merge.prepare_job` with rowCount > 100) require manual approval.
6. **Out-of-band confirmation**: for the highest-impact operations, an out-of-band email confirmation is required before the JIT grant is issued. This is the AISVS-aligned two-person rule for high-blast-radius operations.

## 2. Grant lifecycle

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  requested  │ ──▶ │   approved   │ ──▶ │  granted │ ──▶ │  expired │ ──▶ │ logged  │
│             │     │   or denied  │     │  5min TTL│     │ or revok │     │         │
└─────────────┘     └──────────────┘     └──────────┘     └──────────┘     └─────────┘
       │                    │                                                  ▲
       │                    └──────────────── denied ─────────────────────────┘
       │
       └──── auto-approved by policy ──▶ granted
```

| State | Description | Audit event |
|---|---|---|
| `requested` | The agent (on behalf of the user) requests a JIT elevation. | `jit.requested` |
| `approved` (auto) | The policy engine auto-approves the request because it matches an auto-approval rule. | `jit.granted` |
| `approved` (manual) | A second workspace owner / manager approves the request out-of-band. | `jit.granted` |
| `denied` | The policy engine rejects the request, or the manual approver rejects it. | `jit.denied` |
| `granted` | The grant is active and can be consumed by `consume_tool_authorization()`. | (covered by `jit.granted`) |
| `expired` | The grant's TTL has elapsed. The grant is no longer consumable. | `jit.expired` |
| `revoked` | An administrator (or the original grantor) manually revokes the grant before its TTL. | `jit.revoked` |

## 3. Schema

### 3.1 New table: `jit_elevations`

```sql
CREATE TABLE IF NOT EXISTS jit_elevations(
    id TEXT PRIMARY KEY,                       -- the elevation id (also the audit correlation id)
    user_id TEXT NOT NULL,                     -- the actor (the user on whose behalf the agent is acting)
    workspace_id TEXT NOT NULL DEFAULT '',
    invitation_id TEXT NOT NULL DEFAULT '',    -- the resource context (invitation scope)
    tool_id TEXT NOT NULL,                     -- the tool that will be invoked under this grant
    resource_type TEXT NOT NULL,               -- 'invitation' | 'workspace' | 'template' | 'plugin' | 'event'
    resource_id TEXT NOT NULL,                 -- the {id} of the resource
    action TEXT NOT NULL,                      -- the action being elevated (e.g. 'publish', 'guest:delete')
    sub_resource TEXT NOT NULL DEFAULT '',
    sub_id TEXT NOT NULL DEFAULT '',
    plan_id TEXT NOT NULL DEFAULT '',          -- the plan that this elevation authorizes
    plan_index INTEGER NOT NULL DEFAULT -1,    -- the index within the plan
    reason TEXT NOT NULL,                      -- mandatory; surfaces in audit + dashboard
    auto_eligible INTEGER NOT NULL DEFAULT 0,  -- 1 if the policy engine auto-approved
    approver_id TEXT NOT NULL DEFAULT '',      -- the userId who approved (or '' if auto)
    approval_channel TEXT NOT NULL DEFAULT '', -- 'auto' | 'web' | 'email' | 'sms'
    status TEXT NOT NULL DEFAULT 'requested',  -- 'requested' | 'granted' | 'denied' | 'expired' | 'revoked'
    granted_at INTEGER,                        -- NULL until granted
    expires_at INTEGER,                        -- NULL until granted; then granted_at + 5min
    revoked_at INTEGER,                        -- NULL until revoked
    revoked_by TEXT NOT NULL DEFAULT '',
    revoke_reason TEXT NOT NULL DEFAULT '',
    consumed_at INTEGER,                       -- NULL until consumed by a tool execution
    consumed_tool_authorization TEXT NOT NULL DEFAULT '',  -- the 30-second one-shot token that consumed this JIT grant
    metadata_json TEXT NOT NULL DEFAULT '{}'   -- additional context (e.g. row_count for merge jobs)
);
CREATE INDEX IF NOT EXISTS idx_jit_elevations_user ON jit_elevations(user_id, status, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_jit_elevations_resource ON jit_elevations(resource_type, resource_id, status);
CREATE INDEX IF NOT EXISTS idx_jit_elevations_tool ON jit_elevations(tool_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jit_elevations_active ON jit_elevations(status, expires_at) WHERE status = 'granted';
```

### 3.2 Audit event types

Every state transition emits an audit event with `action` set to one of:

| Audit action | Emitted when |
|---|---|
| `jit.requested` | A JIT elevation request is created (status=`requested`). |
| `jit.granted` | The request is approved and the grant is active (status=`granted`). Includes `grantedAt`, `expiresAt`, `approverId`, `approvalChannel`. |
| `jit.denied` | The request is rejected by the policy engine or the manual approver (status=`denied`). Includes `deniedBy`, `denyReason`. |
| `jit.expired` | The grant's TTL has elapsed (status=`expired`). Emitted by a background sweep job (every 60 seconds). |
| `jit.revoked` | The grant is manually revoked before its TTL (status=`revoked`). Includes `revokedBy`, `revokeReason`. |
| `jit.consumed` | The grant is consumed by a tool execution. Includes `consumedAt`, `consumedToolAuthorization`. (Optional; can be inferred from `ai.tool_authorized`.) |

All audit events are written to the existing hash-chained, immutable `audit_events` table (`src/python/server.py:write_audit_event` at line 1376).

## 4. Auto-approval policy

The policy engine evaluates each JIT request against the rules below. If any rule matches, the request is auto-approved. Otherwise, the request is queued for manual approval.

### 4.1 Auto-approval rules (default; configurable per workspace)

| Rule | Tool IDs | Conditions |
|---|---|---|
| `single-publish` | `publish.prepare` | `action="publish"` AND no other active JIT grant for the same invitation in the last 5 minutes. |
| `single-unpublish` | `publish.prepare` | `action="unpublish"` (always auto-approved — taking a publication offline is safe). |
| `single-archive` | `invitation.archive` | (always auto-approved — reversible). |
| `single-guest-delete` | `guest.delete` | the plan has exactly one tool call. |
| `single-object-delete` | `object.delete` | the plan has exactly one tool call AND `objectIds.length <= 10`. |
| `single-export` | `export.prepare` | `format != "backup"`. |
| `merge-preview` | `merge.prepare_job` | `mode="preview"`. |

### 4.2 Manual-approval required (default)

Any JIT request that does not match an auto-approval rule requires manual approval. Manual approval can be granted by:

1. **Web**: a second workspace `owner` or `manager` visits the JIT queue UI and approves the request.
2. **Email**: the platform sends an email to all `owner` and `manager` workspace members with a one-time approval link. The link expires after 10 minutes.
3. **SMS**: (Phase 4a) a one-time code is sent to the user's registered phone; the user enters the code in the agent UI.

### 4.3 Out-of-band confirmation (highest-impact operations)

For the highest-impact operations, an additional out-of-band confirmation is required even after manual approval:

| Operation | Out-of-band confirmation |
|---|---|
| `merge.prepare_job` with `rowCount > 100` | Email confirmation link to the original actor's registered email. |
| `publishing.configure_environment` with `environmentType="production"` | Two-person rule: two distinct workspace `owner` or `manager` accounts must approve. |
| `plugin.configure` with `permissions` containing `*` | Email confirmation + workspace admin approval. |
| `enterprise.prepare_protocol` with `classification="confidential"` | Two-person rule. |
| `invitation.update_operations` with `customDomain != ""` | Email confirmation link (the new domain does not serve content until confirmed out-of-band). |
| `message.prepare_send` with `recipientIds.length > 50` | Email confirmation link. |

## 5. Skeleton implementation: `ai_agent/jit_elevation.py`

This is a skeleton with the schema, the grant lifecycle, and the audit-event emitter. Enforcement is stubbed — the `evaluate()` function returns `True` (always allow) for now. Wiring into `ai_agent/service.py:authorize_tool_call()` is deferred to Phase 1a Stage 3 (see `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` §3).

```python
# ai_agent/jit_elevation.py
"""Phase 1a skeleton: JIT elevation grant lifecycle.

This module implements the schema, grant lifecycle, and audit-event emitter for
just-in-time permission elevation. Enforcement is stubbed in this skeleton — the
evaluate() function returns True (always allow) — and will be wired into
ai_agent/service.py:authorize_tool_call() in Phase 1a Stage 3.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Optional
import json
import secrets
import time
import uuid

DEFAULT_TTL_SECONDS = 300  # 5 minutes
MAX_REASON_LENGTH = 1000

JIT_ELIGIBLE_TOOLS = frozenset({
    "publish.prepare", "message.prepare_send", "invitation.archive",
    "invitation.update_operations", "plugin.configure", "merge.prepare_job",
    "publishing.configure_environment", "guest.delete", "event.prepare_automation",
    "enterprise.prepare_protocol", "object.delete", "export.prepare",
    "marketplace.install_template",
})


def is_jit_eligible(tool_id: str) -> bool:
    """Return True if the tool requires JIT elevation."""
    return tool_id in JIT_ELIGIBLE_TOOLS


def ensure_jit_schema(connect: Callable[[], Any]) -> None:
    """Create the jit_elevations table if it does not exist. Additive — safe to call on every boot."""
    statements = [
        """CREATE TABLE IF NOT EXISTS jit_elevations(
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL DEFAULT '',
            invitation_id TEXT NOT NULL DEFAULT '',
            tool_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            action TEXT NOT NULL,
            sub_resource TEXT NOT NULL DEFAULT '',
            sub_id TEXT NOT NULL DEFAULT '',
            plan_id TEXT NOT NULL DEFAULT '',
            plan_index INTEGER NOT NULL DEFAULT -1,
            reason TEXT NOT NULL,
            auto_eligible INTEGER NOT NULL DEFAULT 0,
            approver_id TEXT NOT NULL DEFAULT '',
            approval_channel TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'requested',
            granted_at INTEGER,
            expires_at INTEGER,
            revoked_at INTEGER,
            revoked_by TEXT NOT NULL DEFAULT '',
            revoke_reason TEXT NOT NULL DEFAULT '',
            consumed_at INTEGER,
            consumed_tool_authorization TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_jit_elevations_user ON jit_elevations(user_id, status, expires_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_jit_elevations_resource ON jit_elevations(resource_type, resource_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_jit_elevations_tool ON jit_elevations(tool_id, status, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_jit_elevations_active ON jit_elevations(status, expires_at) WHERE status = 'granted'",
    ]
    with connect() as db:
        for statement in statements:
            db.execute(statement)


@dataclass(frozen=True)
class ElevationRequest:
    user_id: str
    workspace_id: str
    invitation_id: str
    tool_id: str
    resource_type: str
    resource_id: str
    action: str
    sub_resource: str = ""
    sub_id: str = ""
    plan_id: str = ""
    plan_index: int = -1
    reason: str = ""
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ElevationGrant:
    id: str
    user_id: str
    tool_id: str
    resource_type: str
    resource_id: str
    action: str
    status: str
    granted_at: int
    expires_at: int
    auto_eligible: bool
    approver_id: str
    approval_channel: str


class JITElevationError(RuntimeError):
    def __init__(self, message: str, code: str = "jit_error", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


class JITElevationManager:
    """Manages the JIT elevation lifecycle. Singleton per AgentService instance."""

    def __init__(self, connect: Callable[[], Any], audit: Callable[..., Any] | None = None,
                 ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.connect = connect
        self.audit = audit
        self.ttl_seconds = ttl_seconds
        ensure_jit_schema(connect)

    def _emit_audit(self, user_id: str, action: str, target_type: str, target_id: str, metadata: dict[str, Any]) -> None:
        if not self.audit:
            return
        try:
            self.audit(user_id, action, target_type, target_id, metadata)
        except Exception:
            pass

    def _auto_eligible(self, request: ElevationRequest) -> tuple[bool, str]:
        """Phase 1a stub: auto-approve nothing. Phase 1b will implement the rules from §4.1."""
        return False, "manual approval required (auto-approval disabled in Phase 1a skeleton)"

    def request(self, req: ElevationRequest) -> str:
        """Create a JIT elevation request. Returns the elevation id.

        Emits a `jit.requested` audit event. The request starts in status='requested'.
        The caller (or the policy engine, if auto-eligible) must call grant() or deny().
        """
        if not is_jit_eligible(req.tool_id):
            raise JITElevationError(f"Tool {req.tool_id} is not JIT-eligible", "jit_not_eligible", 400)
        if not req.reason or len(req.reason) > MAX_REASON_LENGTH:
            raise JITElevationError("A non-empty reason (max 1000 chars) is required", "jit_reason_required", 400)
        elevation_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            db.execute("""
                INSERT INTO jit_elevations(
                    id, user_id, workspace_id, invitation_id, tool_id,
                    resource_type, resource_id, action, sub_resource, sub_id,
                    plan_id, plan_index, reason, auto_eligible, status, created_at, metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'requested', ?, ?)
            """, (
                elevation_id, req.user_id, req.workspace_id, req.invitation_id, req.tool_id,
                req.resource_type, req.resource_id, req.action, req.sub_resource, req.sub_id,
                req.plan_id, req.plan_index, req.reason[:MAX_REASON_LENGTH], 0, now_ms,
                json.dumps(req.metadata or {}, ensure_ascii=False, separators=(",", ":")),
            ))
        self._emit_audit(req.user_id, "jit.requested", req.resource_type, req.resource_id, {
            "elevationId": elevation_id, "toolId": req.tool_id, "action": req.action,
            "resourceId": req.resource_id, "planId": req.plan_id, "reason": req.reason[:200],
        })
        # Phase 1a skeleton: try auto-approval
        auto, reason = self._auto_eligible(req)
        if auto:
            return self.grant(elevation_id, approver_id="", approval_channel="auto")
        return elevation_id

    def grant(self, elevation_id: str, approver_id: str, approval_channel: str = "web") -> str:
        """Approve a pending JIT elevation request. Sets status='granted', granted_at=now, expires_at=now+TTL.

        Emits a `jit.granted` audit event. Returns the elevation id.
        """
        now_ms = int(time.time() * 1000)
        expires_at = now_ms + self.ttl_seconds * 1000
        with self.connect() as db:
            row = db.execute(
                "SELECT user_id, tool_id, resource_type, resource_id, action, status, reason FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "requested":
                raise JITElevationError(f"Elevation request is in status={row['status']}", "jit_not_requestable", 409)
            db.execute(
                "UPDATE jit_elevations SET status='granted', granted_at=?, expires_at=?, "
                "approver_id=?, approval_channel=?, auto_eligible=? WHERE id=? AND status='requested'",
                (now_ms, expires_at, approver_id, approval_channel, 1 if approval_channel == "auto" else 0, elevation_id),
            )
        self._emit_audit(row["user_id"], "jit.granted", row["resource_type"], row["resource_id"], {
            "elevationId": elevation_id, "toolId": row["tool_id"], "action": row["action"],
            "grantedAt": now_ms, "expiresAt": expires_at, "approverId": approver_id,
            "approvalChannel": approval_channel, "ttlSeconds": self.ttl_seconds,
        })
        return elevation_id

    def deny(self, elevation_id: str, denied_by: str, deny_reason: str) -> str:
        """Deny a pending JIT elevation request. Sets status='denied'.

        Emits a `jit.denied` audit event.
        """
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT user_id, tool_id, resource_type, resource_id, action, status FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "requested":
                raise JITElevationError(f"Elevation request is in status={row['status']}", "jit_not_requestable", 409)
            db.execute(
                "UPDATE jit_elevations SET status='denied', revoked_at=?, revoked_by=?, revoke_reason=? WHERE id=?",
                (now_ms, denied_by, deny_reason[:MAX_REASON_LENGTH], elevation_id),
            )
        self._emit_audit(row["user_id"], "jit.denied", row["resource_type"], row["resource_id"], {
            "elevationId": elevation_id, "toolId": row["tool_id"], "action": row["action"],
            "deniedBy": denied_by, "denyReason": deny_reason[:200],
        })
        return elevation_id

    def revoke(self, elevation_id: str, revoked_by: str, revoke_reason: str) -> str:
        """Revoke an active JIT grant before its TTL. Sets status='revoked'.

        Emits a `jit.revoked` audit event.
        """
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT user_id, tool_id, resource_type, resource_id, action, status FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "granted":
                raise JITElevationError(f"Only active grants can be revoked (current status={row['status']})", "jit_not_revocable", 409)
            db.execute(
                "UPDATE jit_elevations SET status='revoked', revoked_at=?, revoked_by=?, revoke_reason=? WHERE id=? AND status='granted'",
                (now_ms, revoked_by, revoke_reason[:MAX_REASON_LENGTH], elevation_id),
            )
        self._emit_audit(row["user_id"], "jit.revoked", row["resource_type"], row["resource_id"], {
            "elevationId": elevation_id, "toolId": row["tool_id"], "action": row["action"],
            "revokedBy": revoked_by, "revokeReason": revoke_reason[:200],
        })
        return elevation_id

    def sweep_expired(self) -> int:
        """Mark all grants whose expires_at has elapsed as status='expired'. Returns the count.

        Should be called by a background scheduler every 60 seconds.
        Emits a `jit.expired` audit event for each.
        """
        now_ms = int(time.time() * 1000)
        expired_rows: list[dict[str, Any]] = []
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, user_id, tool_id, resource_type, resource_id, action FROM jit_elevations "
                "WHERE status='granted' AND expires_at <= ?",
                (now_ms,),
            ).fetchall()
            for row in rows:
                db.execute(
                    "UPDATE jit_elevations SET status='expired' WHERE id=? AND status='granted'",
                    (row["id"],),
                )
                expired_rows.append(dict(row))
        for row in expired_rows:
            self._emit_audit(row["user_id"], "jit.expired", row["resource_type"], row["resource_id"], {
                "elevationId": row["id"], "toolId": row["tool_id"], "action": row["action"],
                "expiredAt": now_ms,
            })
        return len(expired_rows)

    def is_active(self, elevation_id: str) -> bool:
        """Return True if the elevation is currently active (status='granted' and not yet expired)."""
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT status, expires_at FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
        return bool(row and row["status"] == "granted" and int(row["expires_at"] or 0) > now_ms)

    def evaluate(self, elevation_id: str, tool_id: str, resource_type: str, resource_id: str, action: str) -> bool:
        """Phase 1a STUB: always returns True. Phase 1a Stage 3 will replace with real enforcement.

        When wired in, this function is called by consume_tool_authorization() AFTER the existing
        30-second one-shot token check, to additionally verify that the caller holds an active
        JIT elevation for the specific (tool_id, resource_type, resource_id, action) tuple.
        """
        # Phase 1a Stage 1-2: stub — return True (no enforcement yet)
        # Phase 1a Stage 3: replace with:
        #   if is_jit_eligible(tool_id) and not self.is_active(elevation_id):
        #       return False
        #   return True
        return True

    def consume(self, elevation_id: str, tool_authorization_token: str) -> None:
        """Mark the elevation as consumed by a tool execution. Records the 30-second one-shot token.

        Emits a `jit.consumed` audit event. This is informational; the authoritative audit events
        are `ai.tool_authorized` and `ai.tool_authorization_consumed` from ai_agent/service.py.
        """
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT user_id, tool_id, resource_type, resource_id, action, status FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "granted":
                raise JITElevationError(f"Elevation is not active (status={row['status']})", "jit_not_active", 409)
            db.execute(
                "UPDATE jit_elevations SET consumed_at=?, consumed_tool_authorization=? WHERE id=?",
                (now_ms, tool_authorization_token[:128], elevation_id),
            )
        self._emit_audit(row["user_id"], "jit.consumed", row["resource_type"], row["resource_id"], {
            "elevationId": elevation_id, "toolId": row["tool_id"], "action": row["action"],
            "consumedAt": now_ms, "toolAuthorization": tool_authorization_token[:32] + "...",
        })
```

## 6. Wiring into the existing authorization flow

The current flow in `ai_agent/service.py:authorize_tool_call()` (lines 421-458) and `consume_tool_authorization()` (lines 460-487):

```
confirm_plan() → authorize_tool_call() → [30-second one-shot token] → consume_tool_authorization()
```

The Phase 1a Stage 3 flow becomes:

```
confirm_plan() → request_jit_elevation() → [grant or deny] → authorize_tool_call()
   → [30-second one-shot token + JIT elevation id] → consume_tool_authorization()
   → consume_jit_elevation() [records consumption]
```

The 30-second one-shot token in `self._tool_authorizations` is preserved as the single-use layer. The JIT elevation is the longer-lived (5-minute) layer that *authorizes* the issuance of the one-shot token.

### 6.1 Changes to `ai_agent/service.py:authorize_tool_call()` (Phase 1a Stage 3)

```python
# Pseudocode — actual edit deferred to Stage 3
def authorize_tool_call(self, invitation_id, user_id, role, plan_id, data):
    # ... existing plan / index / revision checks ...
    if is_jit_eligible(call["id"]):
        elevation_id = data.get("elevationId")
        if not elevation_id:
            raise AgentServiceError("JIT elevation is required for this tool",
                                    "jit_elevation_required", 403)
        if not self.jit.is_active(elevation_id, call["id"], resource_type, resource_id, action):
            raise AgentServiceError("JIT elevation is not active or does not match",
                                    "jit_elevation_invalid", 403)
    # ... existing 30-second token issuance ...
    self._tool_authorizations[token] = {
        "userId": user_id, "invitationId": invitation_id, "planId": plan_id,
        "index": index, "toolId": call["id"], "expiresAt": now + 30,
        "elevationId": elevation_id,  # NEW: bind the token to the JIT elevation
    }
    return {"authorized": True, "authorizationToken": token, "elevationId": elevation_id, ...}
```

### 6.2 Changes to `ai_agent/service.py:consume_tool_authorization()` (Phase 1a Stage 3)

```python
def consume_tool_authorization(self, token, invitation_id, user_id, tool_id, method="", path=""):
    # ... existing token / userId / invitationId / toolId / http_request_matches_tool checks ...
    elevation_id = record.get("elevationId", "")
    if is_jit_eligible(tool_id):
        if not elevation_id or not self.jit.is_active(elevation_id, tool_id, resource_type, resource_id, action):
            raise AgentServiceError("JIT elevation is not active", "jit_elevation_invalid", 403)
        self.jit.consume(elevation_id, token)
    # ... existing audit emission ...
```

## 7. Background sweep

A background job (run by `platform_v32/jobs.py::JobQueue` every 60 seconds) calls `JITElevationManager.sweep_expired()`. This transitions expired grants to `status='expired'` and emits the `jit.expired` audit events.

The sweep is idempotent — running it twice in the same second produces the same result.

## 8. Frontend changes (Phase 1a Stage 3)

The agent UI in `src/js/ai-creative-agent-v28.js` must:

1. Detect when a plan contains a JIT-eligible tool call.
2. Show a JIT elevation request dialog before `authorize_tool_call()` is invoked:
   - EN: "This action requires just-in-time elevation. Reason: [input]." / KH: "សកម្មភាពនេះទាមទារការលើកសិទ្ធិគ្រានោះ។ ហេតុផល៖ [បញ្ចូល]។"
   - The user must enter a reason (minimum 10 characters).
3. After the request is created, poll `GET /api/agent/jit/{elevationId}` every 2 seconds until `status` is `granted` or `denied`.
4. If auto-approved, proceed immediately to `authorize_tool_call()` with the `elevationId`.
5. If manual approval is required, show a waiting screen with the elevation id and the list of approvers (workspace `owner` / `manager` accounts). Provide a "Cancel request" button.
6. If denied, show the denial reason and abort the plan.

## 9. Test plan

### 9.1 New tests (Phase 1a Stage 1)

- `tests/jit_elevation_schema_test.py` — table exists, indexes exist, migration runs cleanly on SQLite + PostgreSQL.
- `tests/jit_elevation_lifecycle_test.py` — request → grant → consume → expire; request → deny; grant → revoke.
- `tests/jit_elevation_audit_test.py` — every state transition emits the correct audit event with the correct metadata; events are hash-chained and immutable.
- `tests/jit_elevation_sweep_test.py` — `sweep_expired()` correctly transitions grants whose TTL has elapsed.

### 9.2 Updated tests (Phase 1a Stage 3)

- `tests/v28_agent_server_contract_test.py` — assert that JIT-eligible tools require an `elevationId` in the authorize request; assert that the elevation is consumed when the token is consumed.

### 9.3 AISVS acceptance tests

- `tests/aisvs_c10_3_2_test.py` — verify that high-risk operations require a JIT grant; verify that the grant is not transferable to a different tool or resource.
- `tests/aisvs_c10_3_4_test.py` — verify that a JIT grant can be revoked mid-session and that the revocation takes effect within 5 seconds across server instances (simulated by clearing the in-memory cache).

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| User experience friction (every publish requires JIT). | Auto-approval rules (§4.1) reduce friction for low-impact operations. Out-of-band confirmation (§4.3) is reserved for the highest-impact operations. |
| JIT request flood (an attacker triggers thousands of requests). | Rate-limit `POST /api/agent/jit` to 10 requests per user per hour. The `jit_elevations` table is indexed by `(user_id, status, expires_at DESC)` for efficient lookup. |
| Manual approval latency (a human must approve). | Email approval link with 10-minute expiry; SMS one-time code (Phase 4a). If no approver responds within 10 minutes, the request auto-expires. |
| Cross-instance cache drift. | The `jit_elevations` table is the source of truth. The in-memory `_tool_authorizations` cache in `ai_agent/service.py` is bounded by the 30-second TTL of the one-shot token; revocation takes effect within 30 seconds. |
| Grant table grows unbounded. | Daily cron deletes grants older than `EINVITE_JIT_RETENTION_DAYS` (default 90) where `status` is `expired`, `consumed`, or `revoked`. |

## 11. Acceptance criteria

- [ ] `jit_elevations` table exists on SQLite + PostgreSQL.
- [ ] `JITElevationManager.request()` / `grant()` / `deny()` / `revoke()` / `sweep_expired()` / `is_active()` / `consume()` pass the unit tests.
- [ ] Audit events `jit.requested`, `jit.granted`, `jit.denied`, `jit.expired`, `jit.revoked`, `jit.consumed` are emitted to the hash-chained `audit_events` table.
- [ ] `ai_agent/service.py:authorize_tool_call()` rejects JIT-eligible tools without a valid `elevationId` (Stage 3).
- [ ] Background sweep job runs every 60 seconds and transitions expired grants.
- [ ] AISVS C10.3.2 status upgraded from `partial` to `pass` in `docs/ai/AISVS-C9-C10-MAPPING.md`.
- [ ] AISVS C10.3.4 status upgraded from `partial` to `pass` in `docs/ai/AISVS-C9-C10-MAPPING.md`.
