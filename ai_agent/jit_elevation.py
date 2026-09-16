"""Phase 1a Stage 3: JIT elevation grant lifecycle + enforcement.

See docs/ai/JIT-ELEVATION.md for the design document. This module implements the
schema, grant lifecycle, audit-event emitter, and enforcement for just-in-time
permission elevation. Enforcement is wired into
ai_agent/service.py:authorize_tool_call() — high-risk tools (publish.prepare,
message.prepare_send, invitation.archive, etc. per JIT_ELIGIBLE_TOOLS) require
an active 5-minute JIT grant before the 30-second one-shot authorization token
is issued.

V54.13 (sec-5, §2.5) closes the Phase 1a stub: evaluate() no longer returns
True unconditionally. It looks up an active grant in the jit_elevations table,
marks it consumed (one-shot), and emits jit.consumed. If no grant is active it
returns False so authorize_tool_call() can call request_elevation() to start
the request/grant flow.

This module is safe to import on every boot: ensure_jit_schema() is idempotent
and request()/evaluate()/sweep_expired() are no-ops when the table is empty.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
import json
import time
import uuid

DEFAULT_TTL_SECONDS = 300  # 5 minutes
MAX_REASON_LENGTH = 1000

# The set of tools that require JIT elevation. These are the high-risk tools
# declared in ai_agent/tools.py with risk="high" + the destructive-delete tools
# + the bulk-operations tools. The list is frozen; adding a tool here is a
# security-relevant change that requires a regression test.
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
    """Create the jit_elevations table if it does not exist. Additive — safe to call on every boot.

    See docs/ai/JIT-ELEVATION.md §3.1 for the schema.
    """
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
    """A request for JIT elevation. The actor, the tool, the target resource, and the reason.

    Required fields: user_id, tool_id, resource_type, resource_id, action, reason.
    Optional fields: workspace_id, invitation_id, sub_resource, sub_id, plan_id, plan_index, role, metadata.

    The ``role`` field carries the invitation collaboration role ("owner",
    "manager", "designer", "content", "viewer") so the policy engine can apply
    the auto-approval rules from docs/ai/JIT-ELEVATION.md §4 without a separate
    database lookup at policy-decision time.
    """
    user_id: str
    tool_id: str
    resource_type: str
    resource_id: str
    action: str
    reason: str
    workspace_id: str = ""
    invitation_id: str = ""
    sub_resource: str = ""
    sub_id: str = ""
    plan_id: str = ""
    plan_index: int = -1
    role: str = ""
    metadata: dict[str, Any] | None = None


# Tool ids that are auto-approved when the requester is an owner or manager of
# the workspace (per ROADMAP-V2 §2.5 / JIT-ELEVATION.md §4). Destructive delete
# and bulk operations are NEVER auto-approved — they always require manual
# approval even from owners.
AUTO_APPROVED_TOOLS = frozenset({
    "publish.prepare",
})


def _is_auto_approved(tool_id: str, role: str) -> tuple[bool, str]:
    """Apply the §4.1 auto-approval rules.

    Returns (True, reason) if the request can be auto-approved,
    (False, reason) otherwise.
    """
    if role not in {"owner", "manager"}:
        return False, "manual approval required (requester is not owner/manager)"
    if tool_id not in AUTO_APPROVED_TOOLS:
        return False, f"manual approval required (tool {tool_id} is not in the auto-approval set)"
    if tool_id.startswith("delete.") or tool_id.startswith("bulk_"):
        return False, "manual approval required (destructive / bulk operations always require manual approval)"
    return True, f"auto-approved: {role} calling {tool_id}"


class JITElevationError(RuntimeError):
    """Raised when a JIT elevation request cannot be created, granted, or consumed."""

    def __init__(self, message: str, code: str = "jit_error", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


class JITElevationManager:
    """Manages the JIT elevation lifecycle.

    Singleton per AgentService instance. The schema is created on first
    instantiation via ensure_jit_schema(). All state transitions emit audit
    events through the provided audit callback (which writes to the hash-chained
    audit_events table per src/python/server.py:write_audit_event at line 1376).
    """

    def __init__(self, connect: Callable[[], Any], audit: Callable[..., Any] | None = None,
                 ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.connect = connect
        self.audit = audit
        self.ttl_seconds = ttl_seconds
        ensure_jit_schema(connect)

    def _emit_audit(self, user_id: str, action: str, target_type: str, target_id: str,
                    metadata: dict[str, Any]) -> None:
        if not self.audit:
            return
        try:
            self.audit(user_id, action, target_type, target_id, metadata)
        except Exception:
            # Audit emission must never break the elevation lifecycle.
            pass

    def _auto_eligible(self, request: ElevationRequest) -> tuple[bool, str]:
        """Apply the §4.1 auto-approval rules.

        Returns (True, reason) if the request can be auto-approved, (False, reason) otherwise.
        The rules are evaluated by ``_is_auto_approved(tool_id, role)`` so the
        same policy is applied whether the request is created via ``request()``
        (the ElevationRequest path) or ``request_elevation()`` (the
        keyword-argument path used by ai_agent/service.py:authorize_tool_call).
        """
        return _is_auto_approved(request.tool_id, request.role)

    def request(self, req: ElevationRequest) -> str:
        """Create a JIT elevation request. Returns the elevation id.

        Emits a `jit.requested` audit event. The request starts in status='requested'.
        If the auto-eligibility rules match, the request is immediately granted.
        Otherwise, the caller (or the policy engine) must call grant() or deny().
        """
        if not is_jit_eligible(req.tool_id):
            raise JITElevationError(
                f"Tool {req.tool_id} is not JIT-eligible",
                "jit_not_eligible", 400,
            )
        if not req.reason or len(req.reason) > MAX_REASON_LENGTH:
            raise JITElevationError(
                "A non-empty reason (max 1000 chars) is required",
                "jit_reason_required", 400,
            )
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
        auto, _reason = self._auto_eligible(req)
        if auto:
            return self.grant(elevation_id, approver_id="", approval_channel="auto")
        return elevation_id

    def grant(self, elevation_id: str, approver_id: str, approval_channel: str = "web") -> str:
        """Approve a pending JIT elevation request. Sets status='granted', granted_at=now, expires_at=now+TTL.

        Emits a `jit.granted` audit event. Returns the elevation id.
        Raises JITElevationError if the elevation is not found or is not in 'requested' status.
        """
        now_ms = int(time.time() * 1000)
        expires_at = now_ms + self.ttl_seconds * 1000
        with self.connect() as db:
            row = db.execute(
                "SELECT user_id, tool_id, resource_type, resource_id, action, status, reason "
                "FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "requested":
                raise JITElevationError(
                    f"Elevation request is in status={row['status']}",
                    "jit_not_requestable", 409,
                )
            db.execute(
                "UPDATE jit_elevations SET status='granted', granted_at=?, expires_at=?, "
                "approver_id=?, approval_channel=?, auto_eligible=? "
                "WHERE id=? AND status='requested'",
                (
                    now_ms, expires_at, approver_id, approval_channel,
                    1 if approval_channel == "auto" else 0, elevation_id,
                ),
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
                "SELECT user_id, tool_id, resource_type, resource_id, action, status "
                "FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "requested":
                raise JITElevationError(
                    f"Elevation request is in status={row['status']}",
                    "jit_not_requestable", 409,
                )
            db.execute(
                "UPDATE jit_elevations SET status='denied', revoked_at=?, revoked_by=?, revoke_reason=? "
                "WHERE id=?",
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
                "SELECT user_id, tool_id, resource_type, resource_id, action, status "
                "FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "granted":
                raise JITElevationError(
                    f"Only active grants can be revoked (current status={row['status']})",
                    "jit_not_revocable", 409,
                )
            db.execute(
                "UPDATE jit_elevations SET status='revoked', revoked_at=?, revoked_by=?, revoke_reason=? "
                "WHERE id=? AND status='granted'",
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

    def is_active(self, elevation_id: str, tool_id: str = "", resource_type: str = "",
                  resource_id: str = "", action: str = "") -> bool:
        """Return True if the elevation is currently active.

        If tool_id / resource_type / resource_id / action are provided, additionally
        verify that the elevation matches the requested operation (prevents token
        substitution across tools or resources).
        """
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT tool_id, resource_type, resource_id, action, status, expires_at "
                "FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
        if not row or row["status"] != "granted":
            return False
        if int(row["expires_at"] or 0) <= now_ms:
            return False
        if tool_id and row["tool_id"] != tool_id:
            return False
        if resource_type and row["resource_type"] != resource_type:
            return False
        if resource_id and row["resource_id"] != resource_id:
            return False
        if action and row["action"] != action:
            return False
        return True

    def evaluate(self, user_id: str, tool_id: str, resource_id: str | None = None,
                resource_type: str | None = None, action: str | None = None,
                workspace_id: str | None = None, invitation_id: str | None = None) -> bool:
        """Return True if the user holds an ACTIVE JIT grant for the operation.

        Looks up an unconsumed, unrevoked, non-expired grant in the
        ``jit_elevations`` table where ``user_id = ?`` AND ``tool_id = ?`` (and
        optionally ``resource_id``/``resource_type``/``action``/``invitation_id``
        for stricter matching). If a grant is found it is marked consumed
        (one-shot) and a ``jit.consumed`` audit event is emitted.

        Before the lookup, ``sweep_expired()`` is invoked lazily so that
        expired grants are transitioned to ``status='expired'`` (and emit
        ``jit.expired``) without requiring an external cron. This makes the
        enforcement path self-cleaning.

        Returns False when no active grant exists — the caller is then
        expected to invoke ``request_elevation()`` to start the grant flow.
        """
        # Lazy sweep — never trust a stale granted row whose TTL has elapsed.
        try:
            self.sweep_expired()
        except Exception:
            # Sweep must never block enforcement; if it fails, we fall back to
            # the expires_at > now() filter in the SELECT below.
            pass
        now_ms = int(time.time() * 1000)
        sql = (
            "SELECT id, user_id, tool_id, resource_type, resource_id, action, "
            "workspace_id, invitation_id, status, expires_at, granted_at "
            "FROM jit_elevations "
            "WHERE user_id=? AND tool_id=? AND status='granted' "
            "AND expires_at > ? AND revoked_at IS NULL AND consumed_at IS NULL"
        )
        params: list[Any] = [user_id, tool_id, now_ms]
        if resource_id is not None:
            sql += " AND resource_id=?"
            params.append(resource_id)
        if resource_type is not None:
            sql += " AND resource_type=?"
            params.append(resource_type)
        if action is not None and action != "":
            sql += " AND action=?"
            params.append(action)
        if invitation_id is not None and invitation_id != "":
            sql += " AND invitation_id=?"
            params.append(invitation_id)
        if workspace_id is not None and workspace_id != "":
            sql += " AND workspace_id=?"
            params.append(workspace_id)
        sql += " ORDER BY expires_at DESC LIMIT 1"
        with self.connect() as db:
            row = db.execute(sql, tuple(params)).fetchone()
            if not row:
                return False
            # Mark the grant consumed (one-shot). The consumed_at IS NULL filter
            # in the SELECT above + this UPDATE together implement the one-shot
            # contract: a grant authorises exactly one tool execution.
            db.execute(
                "UPDATE jit_elevations SET consumed_at=? WHERE id=? AND consumed_at IS NULL",
                (now_ms, row["id"]),
            )
        self._emit_audit(
            row["user_id"], "jit.consumed", row["resource_type"], row["resource_id"], {
                "elevationId": row["id"], "toolId": row["tool_id"], "action": row["action"],
                "consumedAt": now_ms, "consumedBy": "authorize_tool_call",
            },
        )
        return True

    def request_elevation(self, user_id: str, tool_id: str, resource_id: str,
                          resource_type: str, reason: str, *, action: str = "",
                          workspace_id: str = "", invitation_id: str = "",
                          role: str = "", plan_id: str = "", plan_index: int = -1,
                          metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a JIT elevation request. Returns the elevation row as a dict.

        Emits a ``jit.requested`` audit event. The request starts in
        ``status='requested'``. The §4.1 auto-approval rules are then
        evaluated: if the requester's ``role`` is owner/manager AND the tool is
        in ``AUTO_APPROVED_TOOLS`` (currently only ``publish.prepare``), the
        request is immediately granted (``status='granted'``, ``granted_at``,
        ``expires_at = now + ttl``) and a ``jit.granted`` audit event is
        emitted. Otherwise the row stays in ``status='requested'`` and requires
        manual approval via ``grant()`` (the ``/api/ai-agent/jit/approve``
        route) or denial via ``deny()`` (the ``/api/ai-agent/jit/deny`` route).

        The returned dict always contains ``id``, ``status``, ``toolId``,
        ``userId``, ``resourceType``, ``resourceId``, ``action``,
        ``autoEligible``, ``grantedAt``, ``expiresAt``. Callers should check
        ``status == 'granted'`` to know whether they can proceed immediately
        (auto-approved) or must surface a ``needsElevation`` response to the
        client (pending manual approval).
        """
        req = ElevationRequest(
            user_id=user_id, tool_id=tool_id,
            resource_type=resource_type, resource_id=resource_id,
            action=action or tool_id, reason=reason,
            workspace_id=workspace_id, invitation_id=invitation_id,
            plan_id=plan_id, plan_index=plan_index,
            role=role, metadata=metadata,
        )
        elevation_id = self.request(req)
        return self.get_elevation(elevation_id) or {
            "id": elevation_id, "status": "requested",
            "toolId": tool_id, "userId": user_id,
            "resourceType": resource_type, "resourceId": resource_id,
            "action": req.action, "autoEligible": False,
            "grantedAt": None, "expiresAt": None,
        }

    def get_elevation(self, elevation_id: str) -> dict[str, Any] | None:
        """Return the elevation row as a dict, or None if not found."""
        with self.connect() as db:
            row = db.execute(
                "SELECT id, user_id, workspace_id, invitation_id, tool_id, "
                "resource_type, resource_id, action, reason, auto_eligible, "
                "approver_id, approval_channel, status, granted_at, expires_at, "
                "revoked_at, revoked_by, revoke_reason, consumed_at, "
                "consumed_tool_authorization, plan_id, plan_index, created_at, "
                "metadata_json FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        # Camel-case aliases for the API surface.
        d["toolId"] = d["tool_id"]
        d["userId"] = d["user_id"]
        d["workspaceId"] = d["workspace_id"]
        d["invitationId"] = d["invitation_id"]
        d["resourceType"] = d["resource_type"]
        d["resourceId"] = d["resource_id"]
        d["autoEligible"] = bool(d["auto_eligible"])
        d["approverId"] = d["approver_id"]
        d["approvalChannel"] = d["approval_channel"]
        d["grantedAt"] = d["granted_at"]
        d["expiresAt"] = d["expires_at"]
        d["revokedAt"] = d["revoked_at"]
        d["revokedBy"] = d["revoked_by"]
        d["revokeReason"] = d["revoke_reason"]
        d["consumedAt"] = d["consumed_at"]
        d["planId"] = d["plan_id"]
        d["planIndex"] = d["plan_index"]
        d["createdAt"] = d["created_at"]
        return d

    def list_pending(self, workspace_id: str = "", invitation_id: str = "") -> list[dict[str, Any]]:
        """Return all elevation requests in ``status='requested'`` for the host's workspaces."""
        sql = (
            "SELECT id, user_id, workspace_id, invitation_id, tool_id, resource_type, "
            "resource_id, action, reason, status, created_at, plan_id, plan_index "
            "FROM jit_elevations WHERE status='requested' "
        )
        params: list[Any] = []
        if workspace_id:
            sql += " AND workspace_id=?"
            params.append(workspace_id)
        if invitation_id:
            sql += " AND invitation_id=?"
            params.append(invitation_id)
        sql += " ORDER BY created_at ASC LIMIT 200"
        with self.connect() as db:
            rows = db.execute(sql, tuple(params)).fetchall()
        return [
            {
                "id": r["id"], "userId": r["user_id"], "workspaceId": r["workspace_id"],
                "invitationId": r["invitation_id"], "toolId": r["tool_id"],
                "resourceType": r["resource_type"], "resourceId": r["resource_id"],
                "action": r["action"], "reason": r["reason"], "status": r["status"],
                "createdAt": int(r["created_at"]), "planId": r["plan_id"],
                "planIndex": int(r["plan_index"]),
            }
            for r in rows
        ]

    def consume(self, elevation_id: str, tool_authorization_token: str) -> None:
        """Mark the elevation as consumed by a tool execution. Records the 30-second one-shot token.

        Emits a `jit.consumed` audit event. This is informational; the authoritative
        audit events are `ai.tool_authorized` and `ai.tool_authorization_consumed`
        from ai_agent/service.py.
        """
        now_ms = int(time.time() * 1000)
        with self.connect() as db:
            row = db.execute(
                "SELECT user_id, tool_id, resource_type, resource_id, action, status "
                "FROM jit_elevations WHERE id=?",
                (elevation_id,),
            ).fetchone()
            if not row:
                raise JITElevationError("Elevation request not found", "jit_not_found", 404)
            if row["status"] != "granted":
                raise JITElevationError(
                    f"Elevation is not active (status={row['status']})",
                    "jit_not_active", 409,
                )
            db.execute(
                "UPDATE jit_elevations SET consumed_at=?, consumed_tool_authorization=? WHERE id=?",
                (now_ms, tool_authorization_token[:128], elevation_id),
            )
        self._emit_audit(row["user_id"], "jit.consumed", row["resource_type"], row["resource_id"], {
            "elevationId": elevation_id, "toolId": row["tool_id"], "action": row["action"],
            "consumedAt": now_ms, "toolAuthorization": tool_authorization_token[:32] + "...",
        })
