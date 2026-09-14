"""Permission-aware AI capability discovery.

Discovery is intentionally conservative: a tool is shown only when the current
account/invitation state can legitimately reach its registered executor. Server
APIs remain the final authority at execution time.
"""
from __future__ import annotations
from typing import Any, Callable
import json
import os
import re

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
    try:
        db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
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


def availability(tool: dict[str, Any], snapshot: dict[str, Any]) -> tuple[bool, str]:
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
