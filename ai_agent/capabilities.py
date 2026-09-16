"""Permission-aware AI capability discovery.

Discovery is intentionally conservative: a tool is shown only when the current
account/invitation state can legitimately reach its registered executor. Server
APIs remain the final authority at execution time.

V54.15 (sec-6 — §2.6) Stage 3 introduces resource-scoped grants
(``event:{id}:publish``, ``template:install``, ...) evaluated alongside the
legacy coarse tier check.  Per ROADMAP-V2 §2.6 the semantics are:

* If a grant EXISTS for the tool's resource_type + action (for the current
  user): the new grant check is authoritative — the grant must match.
* If NO grant exists for that resource_type + action: fall back to the
  legacy tier check (unchanged behavior).

When both paths run AND disagree, a structured ``shadow_eval_divergence``
log line is emitted so the Stage 4 migration can audit the divergence
without failing the operation.  When the legacy path was authoritative
because no grant existed for the user on that (resource_type, action)
pair, a ``no_grant_legacy_authoritative`` log line is emitted instead.
"""
from __future__ import annotations
from typing import Any, Callable
import json
import os
import re
import time

from .scopes import Grant, GrantParseError

PLAN_LIMITS = {
    "free": {"storageBytes": 250_000_000},
    "creator": {"storageBytes": 5_000_000_000},
    "studio": {"storageBytes": 50_000_000_000},
}
ROLE_PERMISSIONS = {
    "read": {"owner", "manager", "designer", "content", "viewer"},
    "edit": {"owner", "manager", "designer", "content"},
    "manage": {"owner", "manager"},
    "admin": set(),
}
UPLOAD_TOOL_IDS = {
    "materials.create_folder", "materials.import_folder", "materials.import_zip",
}
ADMIN_TOOL_PREFIXES = ("admin.",)
EDIT_WHILE_ARCHIVED = {"invitation.archive"}
FEATURE_TOOL_PREFIXES = {
    "events": ("event.",),
    "plugins": ("plugin.",),
    "animation": ("animation.",),
    "publishingDomains": ("publishing.",),
    "dataMerge": ("merge.",),
    "marketplace": ("marketplace.",),
}

# V54.15 (sec-6 — §2.6) Stage 3 — resource-scoped grant mapping.
#
# Maps a tool id to the (resource_type, action) tuple that the tool
# requires.  The ``resource_id`` for the required grant is always the
# current invitation_id (i.e. the invitation the plan is being authored
# against — see ``build_access_snapshot``).  Tools absent from this map
# are evaluated by the legacy tier check ONLY (no shadow evaluation),
# which preserves Stage 3 backward compatibility for the long tail of
# tools that have not yet declared ``required_grants``.
#
# The resource_type for ``publish.prepare`` is ``event`` (the design doc
# §5 also lists ``invitation:{id}:publish`` — for Stage 3 we use
# ``event`` as the resource_type to match the §2.6 test matrix).
TOOL_REQUIRED_GRANTS: dict[str, tuple[str, str]] = {
    "publish.prepare": ("event", "publish"),
    "invitation.archive": ("event", "archive"),
    "invitation.update_operations": ("event", "update-operations"),
    "message.prepare_send": ("event", "message-send"),
    "guest.delete": ("event", "guest-delete"),
    "guest.create": ("event", "guest-create"),
    "guest.update": ("event", "guest-update"),
    "rsvp.update": ("event", "rsvp-update"),
    "invitation.configure_rsvp": ("event", "rsvp-configure"),
}


# V54.15 (sec-6) — in-memory log buffer for shadow evaluation events.
# The runtime writes structured entries here; tests inspect them via
# :func:`recent_shadow_eval_logs` / :func:`reset_shadow_eval_logs`.
# Production code can also tail this via JSON-serialised stdout prints
# (one line per entry) for SIEM ingestion.
_SHADOW_EVAL_LOGS: list[dict[str, Any]] = []
_SHADOW_EVAL_MAX = 1024


def reset_shadow_eval_logs() -> None:
    """Clear the in-memory shadow-eval log buffer.  Test helper."""
    _SHADOW_EVAL_LOGS.clear()


def recent_shadow_eval_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Return up to ``limit`` most recent shadow-eval log entries."""
    if limit <= 0:
        return []
    return list(_SHADOW_EVAL_LOGS[-limit:])


def _log_shadow_eval(entry: dict[str, Any]) -> None:
    """Append a shadow-eval log entry.  Idempotent on failure."""
    try:
        _SHADOW_EVAL_LOGS.append(entry)
        if len(_SHADOW_EVAL_LOGS) > _SHADOW_EVAL_MAX:
            del _SHADOW_EVAL_LOGS[: len(_SHADOW_EVAL_LOGS) - _SHADOW_EVAL_MAX]
        # Also emit a single JSON line to stdout for production SIEM ingestion.
        print(json.dumps({"level": "info", **entry}, ensure_ascii=False), flush=True)
    except Exception:
        pass


def _format_grant_str(resource_type: str, resource_id: str, action: str) -> str:
    """Render a (type, id, action) tuple as the canonical grant string."""
    if resource_id == "*":
        return f"{resource_type}:{action}"
    return f"{resource_type}:{resource_id}:{action}"


# Machine-readable executor bindings. Every registered AI tool must appear here;
# tests reject registry entries without a concrete binding. These are descriptive
# bindings only: authorization remains enforced by the authoritative server APIs
# and the editor action service at execution time.
TOOL_BINDINGS: dict[str, dict[str, str]] = {
    "account.read_usage": {"type":"internal-api", "binding":"GET /api/account/usage"},
    "analytics.read_summary": {"type":"internal-api", "binding":"GET /api/invitations/{invitationId}/analytics"},
    "animation.update_timeline": {"type":"platform-api", "binding":"POST /api/platform/v52/animation/projects"},
    "asset.insert": {"type":"editor-action", "binding":"insertAsset (authorized invitation asset lookup)"},
    "asset.search": {"type":"bounded-read", "binding":"authorized invitation asset search"},
    "check.accessibility": {"type":"diagnostic", "binding":"EInviteAIActionService diagnostics: accessibility"},
    "check.design": {"type":"diagnostic", "binding":"EInviteAIActionService diagnostics: design"},
    "check.layout": {"type":"diagnostic", "binding":"EInviteAIActionService diagnostics: responsive layout"},
    "check.print": {"type":"diagnostic", "binding":"EInviteAIActionService diagnostics: print"},
    "design.analyze_reference": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/ai/design-blueprints"},
    "design.apply_blueprint": {"type":"governed-workflow", "binding":"style/palette/typography: GET blueprint + preview/commit typed editor actions; create: POST /api/invitations/{invitationId}/ai/design-blueprints/{blueprintId}/create-invitation"},
    "editor.apply_workspace": {"type":"editor-transaction", "binding":"EInviteEditorBridge.transact editorExperienceV34"},
    "enterprise.prepare_protocol": {"type":"platform-api", "binding":"POST /api/platform/v52/enterprise/protocols"},
    "event.configure_details": {"type":"editor-action", "binding":"updateEventDetails"},
    "event.create_task": {"type":"platform-api", "binding":"POST /api/platform/v52/events/tasks"},
    "event.prepare_automation": {"type":"platform-api", "binding":"POST /api/platform/v52/events/automations"},
    "event.run_intelligence": {"type":"platform-api", "binding":"GET /api/platform/v52/events/intelligence"},
    "event.update_fields": {"type":"editor-action", "binding":"updateFields"},
    "event.update_schedule": {"type":"editor-action", "binding":"applySchedule"},
    "export.prepare": {"type":"ui-command", "binding":"EInviteQualityExport.open"},
    "fix.apply": {"type":"governed-workflow", "binding":"bounded repair preview + EInviteAIActionService.commit"},
    "gallery.arrange": {"type":"editor-action", "binding":"tidyObjects"},
    "guest.check_in": {"type":"internal-api", "binding":"PUT /api/invitations/{invitationId}/guests/{guestId}/check-in"},
    "guest.create": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/guests"},
    "guest.delete": {"type":"internal-api", "binding":"DELETE /api/invitations/{invitationId}/guests/{guestId}"},
    "guest.read_delivery_status": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/ai/guest-delivery-status"},
    "guest.update": {"type":"internal-api", "binding":"PUT /api/invitations/{invitationId}/guests/{guestId}"},
    "image.configure_frame": {"type":"editor-action", "binding":"updateImageFrame"},
    "invitation.archive": {"type":"internal-api", "binding":"PUT /api/invitations/{invitationId}/archive"},
    "invitation.configure_opening": {"type":"editor-action", "binding":"updateOpeningScene"},
    "invitation.configure_rsvp": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/rsvp-config"},
    "invitation.update_operations": {"type":"internal-api", "binding":"PUT /api/invitations/{invitationId}/operations"},
    "marketplace.install_template": {"type":"platform-api", "binding":"POST /api/platform/v52/marketplace/install"},
    "materials.classify": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/materials/classify"},
    "materials.create_folder": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/materials/folders"},
    "materials.find_duplicates": {"type":"internal-api", "binding":"GET /api/invitations/{invitationId}/materials/duplicates"},
    "materials.import_folder": {"type":"upload-workflow", "binding":"POST material import job + resumable/raw asset upload preserving webkitRelativePath"},
    "materials.import_zip": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/materials/import-zip"},
    "materials.insert_into_page": {"type":"editor-action", "binding":"insertAsset (authorized invitation asset lookup)"},
    "materials.list_folders": {"type":"internal-api", "binding":"GET /api/invitations/{invitationId}/materials/folders"},
    "materials.move": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/materials/move"},
    "materials.rename": {"type":"internal-api", "binding":"POST /api/invitations/{invitationId}/materials/rename"},
    "materials.update_metadata": {"type":"internal-api", "binding":"PUT /api/assets/{assetId}"},
    "merge.prepare_job": {"type":"platform-api", "binding":"POST /api/platform/v52/data-merge/jobs"},
    "message.prepare_send": {"type":"review-workflow", "binding":"prepare message in session and open Guests review; no automatic external send"},
    "object.create_image": {"type":"editor-action", "binding":"insertAsset (authorized invitation asset lookup)"},
    "object.create_shape": {"type":"editor-action", "binding":"createObject shape"},
    "object.create_text": {"type":"editor-action", "binding":"addText"},
    "object.delete": {"type":"editor-action", "binding":"deleteObjects"},
    "object.duplicate": {"type":"editor-action", "binding":"duplicateObjects"},
    "object.update": {"type":"editor-action", "binding":"updateObject"},
    "page.configure_style": {"type":"editor-action", "binding":"updatePageStyle"},
    "page.create": {"type":"editor-action", "binding":"createPage"},
    "page.duplicate": {"type":"editor-action", "binding":"duplicatePage"},
    "page.rename": {"type":"editor-action", "binding":"renamePage"},
    "page.reorder": {"type":"editor-action", "binding":"reorderPages"},
    "photo.remove_background": {"type":"existing-workflow", "binding":"registered #aiBgCut local background-removal workflow + document fingerprint verification"},
    "plugin.configure": {"type":"platform-api", "binding":"POST /api/platform/v52/plugins/install"},
    "preview.prepare": {"type":"ui-command", "binding":"existing invitation preview command"},
    "publish.prepare": {"type":"ui-command", "binding":"existing publish/unpublish command after governed confirmation"},
    "publishing.configure_environment": {"type":"platform-api", "binding":"POST /api/platform/v52/publishing/environments"},
    "read.page_summary": {"type":"bounded-read", "binding":"captured authorized document page summary"},
    "read.project_summary": {"type":"bounded-read", "binding":"captured authorized invitation summary"},
    "read.selection_summary": {"type":"bounded-read", "binding":"captured authorized selection summary"},
    "rich_text.replace": {"type":"editor-action", "binding":"replaceText"},
    "rsvp.update": {"type":"internal-api", "binding":"PUT /api/invitations/{invitationId}/rsvps/{rsvpId}"},
    "selection.select_layers": {"type":"editor-command", "binding":"EInviteEditorBridge.select"},
    "style.apply_brand_kit": {"type":"editor-action", "binding":"applyBrandKit"},
    "style.apply_palette": {"type":"editor-action", "binding":"applyPalette"},
    "style.apply_photo": {"type":"editor-action", "binding":"photoPreset"},
    "style.apply_text_style": {"type":"editor-action", "binding":"applyTextStyle"},
    "transform.align": {"type":"editor-action", "binding":"alignObjects"},
    "transform.arrange": {"type":"editor-action", "binding":"arrange"},
    "transform.distribute": {"type":"editor-action", "binding":"distributeObjects"},
    "transform.group": {"type":"editor-action", "binding":"groupObjects"},
    "transform.move": {"type":"editor-action", "binding":"resize position patch"},
    "transform.resize": {"type":"editor-action", "binding":"resize dimension patch"},
    "transform.rotate": {"type":"editor-action", "binding":"resize rotation patch"},
    "transform.tidy": {"type":"editor-action", "binding":"tidyObjects"},
    "transform.ungroup": {"type":"editor-action", "binding":"ungroupObjects"},
}


_SPECIAL_HTTP_BINDINGS: dict[str, tuple[tuple[str, str], ...]] = {
    "design.apply_blueprint": (
        ("GET", "/api/invitations/{invitationId}/ai/design-blueprints/{blueprintId}"),
        ("POST", "/api/invitations/{invitationId}/ai/design-blueprints/{blueprintId}/create-invitation"),
    ),
    "materials.import_folder": (
        ("POST", "/api/invitations/{invitationId}/materials/import-jobs"),
    ),
}


def _binding_pattern(template: str, invitation_id: str) -> re.Pattern[str]:
    """Compile one declarative tool binding into an exact same-origin path scope."""
    escaped = re.escape(template)
    escaped = escaped.replace(re.escape("{invitationId}"), re.escape(str(invitation_id)))
    for placeholder in ("guestId", "rsvpId", "assetId", "blueprintId"):
        escaped = escaped.replace(re.escape("{" + placeholder + "}"), r"[^/]+")
    return re.compile(r"^" + escaped + r"/?$")


def http_request_matches_tool(tool_id: str, method: str, path: str, invitation_id: str) -> bool:
    """Return whether a governed browser request matches its planned tool binding."""
    method = str(method or "").upper()
    candidates = list(_SPECIAL_HTTP_BINDINGS.get(str(tool_id or ""), ()))
    binding = TOOL_BINDINGS.get(str(tool_id or ""), {}).get("binding", "")
    direct = re.match(r"^(GET|POST|PUT|DELETE|PATCH)\s+(\/api\/\S+)$", binding)
    if direct:
        candidates.append((direct.group(1), direct.group(2)))
    return any(method == expected_method and _binding_pattern(template, invitation_id).fullmatch(path or "") for expected_method, template in candidates)


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)


def _table_exists(db: Any, table: str) -> bool:
    if table not in {
        "agent_grants", "ai_routing_policies", "editor_workspace_profiles",
        "ai_saved_workflows_v35", "marketplace_templates_v36",
        "enterprise_protocols_v42", "animation_projects_v44",
        "custom_domains_v45", "data_merge_sources_v47",
        "data_merge_jobs_v47", "plugin_installations_v48",
        "event_tasks_v52", "event_programs_v52",
    }:
        return False
    try:
        db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()  # nosec B608 - table is checked against the fixed allowlist above
        return True
    except Exception:
        return False


def build_access_snapshot(connect: Callable[[], Any], user_id: str, invitation_id: str = "", invitation_role: str = "") -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "userId": user_id, "invitationId": invitation_id, "invitationRole": invitation_role or "",
        "accountRole": "customer", "plan": "free", "uploadEnabled": False, "storageUsedBytes": 0,
        "storageLimitBytes": PLAN_LIMITS["free"]["storageBytes"], "storageRemainingBytes": 0,
        "archived": False, "published": False, "workspacePolicyEnabled": True,
        "features": {"events": False, "plugins": False, "animation": False, "publishingDomains": False, "dataMerge": False, "marketplace": False},
        "blockers": [],
        # V54.15 (sec-6) — active resource-scoped grants for this user.
        # Populated below by querying the ``agent_grants`` table.  Absent
        # (or empty) means "no grants defined for this user"; the
        # availability() legacy tier check is then authoritative for
        # every tool (Stage 3 fallback).
        "grants": [],
    }
    with connect() as db:
        user = db.execute("SELECT id,role,plan,upload_enabled FROM users WHERE id=? AND deleted_at IS NULL", (user_id,)).fetchone()
        if user:
            snapshot["accountRole"] = str(_row_value(user, "role", "customer") or "customer")
            snapshot["plan"] = str(_row_value(user, "plan", "free") or "free")
            snapshot["uploadEnabled"] = bool(_row_value(user, "upload_enabled", 1))
            try:
                usage = db.execute("SELECT COALESCE(SUM(size),0) total FROM stored_objects WHERE owner_id=? AND processing_state='ready' AND ref_count>0", (user_id,)).fetchone()
                snapshot["storageUsedBytes"] = int(_row_value(usage, "total", 0) or 0)
            except Exception:
                snapshot["storageUsedBytes"] = 0
        snapshot["storageLimitBytes"] = int(PLAN_LIMITS.get(snapshot["plan"], PLAN_LIMITS["free"])["storageBytes"])
        snapshot["storageRemainingBytes"] = max(0, snapshot["storageLimitBytes"] - snapshot["storageUsedBytes"])
        if invitation_id:
            invite = db.execute("SELECT archived,is_published,workspace_id FROM invitations WHERE id=? AND deleted_at IS NULL", (invitation_id,)).fetchone()
            if invite:
                snapshot["archived"] = bool(_row_value(invite, "archived", 0))
                snapshot["published"] = bool(_row_value(invite, "is_published", 0))
                workspace_id = str(_row_value(invite, "workspace_id", "") or "")
                if workspace_id and _table_exists(db, "ai_routing_policies"):
                    policy = db.execute("SELECT enabled FROM ai_routing_policies WHERE workspace_id=? ORDER BY updated_at DESC LIMIT 1", (workspace_id,)).fetchone()
                    if policy is not None:
                        snapshot["workspacePolicyEnabled"] = bool(_row_value(policy, "enabled", 1))
        tables = {
            "events": "event_tasks_v52", "plugins": "plugin_installations_v48", "animation": "animation_projects_v44",
            "publishingDomains": "custom_domains_v45", "dataMerge": "data_merge_jobs_v47", "marketplace": "marketplace_templates_v36",
        }
        for key, table in tables.items():
            snapshot["features"][key] = _table_exists(db, table)
        # V54.15 (sec-6 — §2.6) Stage 3 — load this user's active
        # resource-scoped grants (unrevoked, unexpired) so availability()
        # can run the new grant check alongside the legacy tier check.
        # The table is created by the SQLite / PostgreSQL schema helpers
        # (see ``_ensure_p2a_schema_sqlite`` / ``docs/postgres_schema.sql``);
        # if it does not exist yet (e.g. a legacy in-memory test DB), we
        # silently fall back to an empty grant set — the legacy tier
        # check then remains authoritative for every tool.
        #
        # Grants are stored as plain dicts (NOT ``Grant`` instances) so
        # the snapshot remains JSON-serialisable for the
        # ``/api/ai-agent/tools`` response (which returns ``access`` as
        # part of the payload).  ``availability`` constructs ``Grant``
        # objects on the fly when matching.
        if _table_exists(db, "agent_grants"):
            try:
                now_ms = int(time.time() * 1000)
                grant_rows = db.execute(
                    "SELECT resource_type, resource_id, action FROM agent_grants "
                    "WHERE user_id=? AND revoked_at IS NULL "
                    "AND (expires_at IS NULL OR expires_at>?)",
                    (user_id, now_ms),
                ).fetchall()
                snapshot["grants"] = [
                    {
                        "resource_type": str(_row_value(r, "resource_type", "") or ""),
                        "resource_id": str(_row_value(r, "resource_id", "") or ""),
                        "action": str(_row_value(r, "action", "") or ""),
                    }
                    for r in grant_rows
                    if _row_value(r, "resource_type", "") and _row_value(r, "action", "")
                ]
            except Exception:
                snapshot["grants"] = []
        else:
            snapshot["grants"] = []
    if not snapshot["uploadEnabled"]:
        snapshot["blockers"].append({"code":"upload_disabled","message":"Uploads are disabled for this account. An administrator must enable uploads before folder import can run."})
    if snapshot["storageRemainingBytes"] <= 0:
        snapshot["blockers"].append({"code":"storage_limit_reached","message":"The account storage limit has been reached. Free space or increase the plan before importing materials."})
    if snapshot["archived"]:
        snapshot["blockers"].append({"code":"invitation_archived","message":"This invitation is archived. Editing tools stay unavailable until it is restored."})
    if not snapshot["workspacePolicyEnabled"]:
        snapshot["blockers"].append({"code":"workspace_ai_disabled","message":"Connected AI routing is disabled by the workspace policy."})
    return snapshot


def _feature_for_tool(tool_id: str) -> str:
    for feature, prefixes in FEATURE_TOOL_PREFIXES.items():
        if any(tool_id.startswith(prefix) for prefix in prefixes):
            return feature
    return ""


def _legacy_availability(tool: dict[str, Any], snapshot: dict[str, Any]) -> tuple[bool, str]:
    """Legacy coarse-tier check (V28 — read/edit/manage/admin).  Stage 3
    retains this as the fallback when no resource-scoped grant is defined
    for the current user on the tool's (resource_type, action) pair.
    """
    tool_id = str(tool.get("id") or "")
    permission = str(tool.get("permission") or "manage")
    role = str(snapshot.get("invitationRole") or "")
    account_role = str(snapshot.get("accountRole") or "customer")
    if not snapshot.get("workspacePolicyEnabled", True):
        return False, "AI tools are disabled by the workspace policy"
    if permission == "admin" or any(tool_id.startswith(prefix) for prefix in ADMIN_TOOL_PREFIXES):
        if account_role != "admin":
            return False, "administrator permission is required"
    elif role and role not in ROLE_PERMISSIONS.get(permission, set()):
        return False, f"the {role} collaboration role does not include {permission} permission"
    elif not role and permission in {"edit", "manage"}:
        return False, "an invitation with edit permission must be selected"
    if tool_id in UPLOAD_TOOL_IDS:
        if not snapshot.get("uploadEnabled"):
            return False, "uploads are disabled for this account"
        if int(snapshot.get("storageRemainingBytes") or 0) <= 0:
            return False, "the account storage limit has been reached"
    if snapshot.get("archived") and permission in {"edit", "manage"} and tool_id not in EDIT_WHILE_ARCHIVED:
        return False, "the invitation is archived"
    feature = _feature_for_tool(tool_id)
    if feature and not bool((snapshot.get("features") or {}).get(feature)):
        return False, f"the {feature} platform capability is unavailable"
    return True, ""


def availability(tool: dict[str, Any], snapshot: dict[str, Any]) -> tuple[bool, str]:
    """V54.15 (sec-6 — §2.6) Stage 3 availability check.

    Runs the legacy coarse-tier check first.  If the tool declares a
    resource-scoped ``required_grants`` tuple in :data:`TOOL_REQUIRED_GRANTS`
    AND the snapshot carries an ``agent_grants``-derived ``grants`` list,
    the new grant check is also evaluated:

    * If ANY grant for the tool's (resource_type, action) exists for the
      current user → new check is authoritative (grant must match).
    * If NO grant exists for that (resource_type, action) → fall back to
      the legacy result.

    When both paths run AND disagree, a ``shadow_eval_divergence`` log
    entry is emitted.  When the legacy path was authoritative because no
    grant existed, a ``no_grant_legacy_authoritative`` log entry is
    emitted.  Neither log changes the operation's outcome — they are
    telemetry for the Stage 4 migration.

    Tools absent from :data:`TOOL_REQUIRED_GRANTS` use the legacy result
    only (no shadow evaluation) to preserve Stage 3 backward
    compatibility for the long tail of tools that have not yet declared
    ``required_grants``.
    """
    legacy_ok, legacy_reason = _legacy_availability(tool, snapshot)
    tool_id = str(tool.get("id") or "")
    required = TOOL_REQUIRED_GRANTS.get(tool_id)
    # Tools without a declared required_grant → legacy-only.  No shadow
    # log: there is nothing to compare against.  This is the long tail of
    # editor/transform/style/etc. tools that Stage 4 will migrate.
    if required is None:
        return legacy_ok, legacy_reason

    resource_type, action = required
    invitation_id = str(snapshot.get("invitationId") or "") or "*"
    user_id = str(snapshot.get("userId") or "") or ""
    raw_grants = list(snapshot.get("grants") or [])
    # Normalise snapshot grants (which may be dicts or Grant instances)
    # into Grant objects for matching.  Malformed entries are skipped —
    # they should not exist (the loader filters them) but defensive
    # parsing keeps a bad DB row from breaking the entire availability
    # check.
    grants: list[Grant] = []
    for raw in raw_grants:
        try:
            if isinstance(raw, Grant):
                grants.append(raw)
            elif isinstance(raw, dict):
                grants.append(Grant(
                    str(raw.get("resource_type") or ""),
                    str(raw.get("resource_id") or ""),
                    str(raw.get("action") or ""),
                ))
            elif isinstance(raw, str):
                grants.append(Grant.parse(raw))
        except (GrantParseError, ValueError):
            continue

    # Filter the user's grants to those matching (resource_type, action).
    # Per §2.6: "If a grant EXISTS for the tool's resource type + action"
    # → new check is authoritative.  Otherwise fall back to legacy.
    type_action_grants = [
        g for g in grants
        if g.resource_type == resource_type and (g.action == "*" or g.action == action)
    ]
    required_str = _format_grant_str(resource_type, invitation_id, action)
    if not type_action_grants:
        # No grant for this (resource_type, action) for this user →
        # legacy tier check is authoritative.  Emit the no-grant log so
        # Stage 4 can audit which tool calls were still on the legacy
        # path (i.e. whose operators have not yet been migrated to
        # standing resource-scoped grants).
        _log_shadow_eval({
            "event": "no_grant_legacy_authoritative",
            "user_id": user_id,
            "tool_id": tool_id,
            "resource": required_str,
            "legacy_check": "allow" if legacy_ok else "deny",
        })
        return legacy_ok, legacy_reason

    # New check is authoritative.  The required grant is
    # (resource_type, invitation_id, action).  ``invitation_id`` defaults
    # to ``"*"`` when the snapshot is unscoped (e.g. account-level tool
    # listing); wildcard grants (``event:*:publish``) match either way.
    try:
        required_grant = Grant(resource_type, invitation_id, action)
    except (GrantParseError, ValueError):
        # If the invitation_id contains characters the Grant grammar
        # rejects, fail closed — the runtime should never produce a
        # malformed required grant, but defensive programming wins.
        new_ok = False
    else:
        new_ok = any(g.matches(required_grant) for g in type_action_grants)

    # Shadow evaluation: log a divergence when both paths disagree.
    if new_ok != legacy_ok:
        _log_shadow_eval({
            "event": "shadow_eval_divergence",
            "user_id": user_id,
            "tool_id": tool_id,
            "resource": required_str,
            "new_check": "allow" if new_ok else "deny",
            "legacy_check": "allow" if legacy_ok else "deny",
        })

    if new_ok:
        return True, ""
    return False, "no resource-scoped grant authorises this tool call"


def filter_catalog(catalog: list[dict[str, Any]], snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed: list[dict[str, Any]] = []
    denied: list[dict[str, Any]] = []
    for tool in catalog:
        ok, reason = availability(tool, snapshot)
        if ok:
            allowed.append(tool)
        else:
            denied.append({"id": tool.get("id"), "reason": reason})
    return allowed, denied


def assert_calls_available(calls: list[dict[str, Any]], snapshot: dict[str, Any]) -> None:
    denied = []
    for call in calls:
        ok, reason = availability(call, snapshot)
        if not ok:
            denied.append({"id": call.get("id"), "reason": reason})
    if denied:
        error = PermissionError("One or more AI capabilities are no longer available")
        setattr(error, "denied", denied)
        raise error


def coverage_report(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, int] = {}
    executors: dict[str, int] = {}
    rows = []
    for tool in catalog:
        tool_id = str(tool.get("id") or "")
        group = tool_id.split(".", 1)[0] if "." in tool_id else tool_id
        groups[group] = groups.get(group, 0) + 1
        executor = str(tool.get("executor") or "client")
        executors[executor] = executors.get(executor, 0) + 1
        binding = TOOL_BINDINGS.get(tool_id)
        rows.append({
            "toolId": tool_id, "permission": tool.get("permission"), "risk": tool.get("risk"),
            "executor": executor, "bindingType": (binding or {}).get("type", ""),
            "binding": (binding or {}).get("binding", ""),
            "confirmationRequired": bool(tool.get("confirmationRequired")),
            "reversible": bool(tool.get("reversible")), "connected": bool(binding),
        })
    missing = sorted(row["toolId"] for row in rows if not row["connected"])
    return {"schema":"einvite-ai-capability-coverage-v1", "toolCount":len(rows), "connectedToolCount":len(rows)-len(missing), "missingBindings":missing, "groups":groups, "executors":executors, "tools":rows}
