"""Typed V34-V52 capability service built on the V32 workspace, authorization and job foundations."""
from __future__ import annotations
from typing import Any
import csv, hashlib, io, json, re, secrets, time, uuid


class FuturePlatformError(RuntimeError):
    def __init__(self, message: str, code: str = "future_platform_error", status: int = 400):
        super().__init__(message); self.code = code; self.status = status


def now_ms() -> int: return int(time.time() * 1000)
def uid() -> str: return str(uuid.uuid4())
def dumps(value: Any, limit: int = 1_000_000) -> str:
    encoded = json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > limit: raise FuturePlatformError("Payload exceeds the bounded storage size", "payload_too_large", 413)
    return encoded
def loads(value: Any, fallback: Any):
    try: return json.loads(value) if value else fallback
    except Exception: return fallback
def clean(value: Any, limit: int = 200) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value or "")).strip()[:limit]
def slug(value: Any, limit: int = 80) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", clean(value, 200).lower()).strip("-")[:limit]
    return result or "item"
def fingerprint(value: Any) -> str:
    return hashlib.sha256(dumps(value, 5_000_000).encode("utf-8")).hexdigest()
def boolean(value: Any) -> bool: return bool(value) and str(value).lower() not in {"0", "false", "no", "off"}
def bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try: number = int(value)
    except Exception: number = default
    return max(minimum, min(maximum, number))

_POLICY_SECRET_KEYS = {"apikey", "api_key", "secret", "token", "password", "authorization", "cookie", "credential", "endpoint", "url"}
def safe_policy_value(value: Any, depth: int = 0) -> Any:
    if depth > 8: return None
    if isinstance(value, dict):
        output = {}
        for key, item in list(value.items())[:200]:
            safe_key = clean(key, 100)
            if safe_key.lower().replace("-", "_") in _POLICY_SECRET_KEYS: continue
            output[safe_key] = safe_policy_value(item, depth + 1)
        return output
    if isinstance(value, list): return [safe_policy_value(item, depth + 1) for item in value[:200]]
    if isinstance(value, bool) or value is None: return value
    if isinstance(value, (int, float)): return value if abs(value) < 10**15 else 0
    return clean(value, 1000)


PLUGIN_PERMISSIONS = {
    "project.read", "project.write", "assets.read", "assets.insert", "export.prepare",
    "publish.prepare", "analytics.write", "calendar.prepare", "communications.prepare",
    "payments.prepare", "storage.metadata", "ui.panel", "content.block",
}
PLUGIN_EXTENSION_POINTS = {
    "editor.panel", "content.block", "asset.provider", "export.provider", "communication.provider",
    "payment.provider", "analytics.provider", "storage.provider", "ai.provider", "calendar.provider", "map.provider",
}


class FuturePlatformService:
    def __init__(self, connect, platform, ai_service=None, audit=None):
        self.connect = connect; self.platform = platform; self.ai_service = ai_service; self.audit = audit
        platform.jobs.register("animation-export-v44", self._animation_export_job)
        platform.jobs.register("bulk-generation-v47", self._bulk_generation_job)
        platform.jobs.register("event-automation-v52", self._event_automation_job)
        platform.jobs.register("marketplace-package-v36", self._marketplace_package_job)

    def _audit(self, user_id: str, action: str, target_type: str, target_id: str, metadata: dict[str, Any] | None = None):
        if not self.audit: return
        try: self.audit(user_id, action, target_type, target_id, metadata or {})
        except Exception: pass

    def _workspace(self, user_id: str) -> dict[str, Any]:
        row = self.platform.workspace_for_user(user_id)
        if not row: raise FuturePlatformError("Workspace not found", "workspace_not_found", 404)
        return row

    def _scope(self, invitation_id: str, user_id: str, permission: str = "read") -> dict[str, Any]:
        invitation_id = clean(invitation_id, 160)
        if not invitation_id: raise FuturePlatformError("Invitation ID is required", "invitation_required")
        try:
            scoped = self.platform.invitation_scope(invitation_id, user_id, permission)
            if isinstance(scoped, tuple) and len(scoped) == 3:
                invitation, workspace_id, membership = scoped
                return {"invitation": dict(invitation), "workspace_id": workspace_id, "membership": dict(membership)}
            if isinstance(scoped, dict):
                return scoped
            raise FuturePlatformError("Invitation scope returned an unsupported shape", "invalid_scope", 500)
        except Exception as exc:
            status = getattr(exc, "status", 403); code = getattr(exc, "code", "invitation_forbidden")
            raise FuturePlatformError(str(exc), code, status) from exc

    @staticmethod
    def _rows(rows): return [dict(row) for row in rows]

    @staticmethod
    def _query_one(query: dict[str, list[str]], name: str, default: str = "") -> str:
        value = query.get(name, [default]); return clean(value[0] if value else default, 200)

    def status(self, user_id: str) -> dict[str, Any]:
        workspace = self._workspace(user_id)
        with self.connect() as db:
            counts = {}
            for name, table in {
                "editorProfiles": "editor_workspace_profiles", "aiWorkflows": "ai_saved_workflows_v35",
                "marketplaceTemplates": "marketplace_templates_v36", "enterpriseProtocols": "enterprise_protocols_v42",
                "animationProjects": "animation_projects_v44", "customDomains": "custom_domains_v45",
                "mergeSources": "data_merge_sources_v47", "plugins": "plugin_installations_v48",
                "eventPrograms": "event_programs_v52",
            }.items():
                row = db.execute(f"SELECT COUNT(*) value FROM {table} WHERE workspace_id=?", (workspace["id"],)).fetchone()
                counts[name] = int(row["value"] or 0)
        return {
            "version": "0.52", "schemaVersion": 27, "workspaceId": workspace["id"], "counts": counts,
            "capabilities": {
                "unifiedEditor": True, "productionAgent": True, "templateMarketplace": True,
                "enterpriseGovernment": True, "advancedAnimationExport": True, "publishingDomains": True,
                "dataMergeBulk": True, "pluginPlatform": True, "intelligentEventEcosystem": True,
            },
            "certification": "pending independent Codex testing",
        }

    # ---------- Unified editor V34 ----------
    def list_editor_profiles(self, user_id: str):
        workspace = self._workspace(user_id)
        with self.connect() as db:
            rows = db.execute("SELECT * FROM editor_workspace_profiles WHERE workspace_id=? AND user_id=? ORDER BY is_default DESC,updated_at DESC", (workspace["id"], user_id)).fetchall()
        return [{**dict(row), "layout": loads(row["layout_json"], {}), "shortcuts": loads(row["shortcuts_json"], {})} for row in rows]

    def save_editor_profile(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); profile_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        name = clean(data.get("name") or "My workspace", 100); mode = clean(data.get("mode") or "quick", 30)
        if mode not in {"quick", "studio", "vector", "photo", "animation", "review", "operations"}: raise FuturePlatformError("Unsupported editor mode", "invalid_editor_mode")
        layout = data.get("layout") if isinstance(data.get("layout"), dict) else {}; shortcuts = data.get("shortcuts") if isinstance(data.get("shortcuts"), dict) else {}
        is_default = 1 if data.get("isDefault") else 0
        with self.connect() as db:
            if is_default: db.execute("UPDATE editor_workspace_profiles SET is_default=0 WHERE workspace_id=? AND user_id=?", (workspace["id"], user_id))
            row = db.execute("SELECT id FROM editor_workspace_profiles WHERE id=? AND workspace_id=? AND user_id=?", (profile_id, workspace["id"], user_id)).fetchone()
            if row: db.execute("UPDATE editor_workspace_profiles SET name=?,mode=?,layout_json=?,shortcuts_json=?,is_default=?,updated_at=? WHERE id=?", (name, mode, dumps(layout), dumps(shortcuts), is_default, timestamp, profile_id))
            else: db.execute("INSERT INTO editor_workspace_profiles(id,workspace_id,user_id,name,mode,layout_json,shortcuts_json,is_default,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (profile_id, workspace["id"], user_id, name, mode, dumps(layout), dumps(shortcuts), is_default, timestamp, timestamp))
        self._audit(user_id, "editor.workspace_profile_saved", "editor_profile", profile_id, {"mode": mode})
        return {"id": profile_id, "name": name, "mode": mode, "layout": layout, "shortcuts": shortcuts, "isDefault": bool(is_default)}

    # ---------- Production AI agent V35 ----------
    def ai_policy(self, user_id: str):
        workspace = self._workspace(user_id)
        with self.connect() as db:
            row = db.execute("SELECT * FROM ai_routing_policies WHERE workspace_id=? ORDER BY updated_at DESC LIMIT 1", (workspace["id"],)).fetchone()
            usage = db.execute("SELECT COALESCE(SUM(input_units),0) input_units,COALESCE(SUM(output_units),0) output_units,COALESCE(SUM(cost_micros),0) cost_micros,COALESCE(SUM(request_count),0) request_count FROM ai_budget_ledger_v35 WHERE workspace_id=? AND period_key=?", (workspace["id"], time.strftime("%Y-%m"))).fetchone()
        value = {"id": "", "name": "Workspace AI policy", "enabled": True, "providers": [], "modelProfiles": {}, "fallback": [], "budget": {"monthlyCostMicros": 0, "monthlyRequests": 0}, "evaluation": {"required": True}}
        if row: value.update({"id": row["id"], "name": row["name"], "enabled": bool(row["enabled"]), "providers": loads(row["providers_json"], []), "modelProfiles": loads(row["model_profiles_json"], {}), "fallback": loads(row["fallback_json"], []), "budget": loads(row["budget_json"], {}), "evaluation": loads(row["evaluation_json"], {})})
        value["usage"] = dict(usage) if usage else {}; value["period"] = time.strftime("%Y-%m")
        if self.ai_service: value["agentStatus"] = self.ai_service.status(user_id)
        return value

    def save_ai_policy(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); policy_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        providers = data.get("providers") if isinstance(data.get("providers"), list) else []
        safe_providers = []
        configured_ids = {clean(item.get("id"), 80) for item in (getattr(getattr(self.ai_service, "config", None), "provider_routes", ()) or ()) if isinstance(item, dict)}
        for item in providers[:12]:
            if not isinstance(item, dict): continue
            provider_id = clean(item.get("id"), 80)
            safe_providers.append({"id": provider_id, "label": clean(item.get("label"), 100), "mode": clean(item.get("mode") or "external", 30), "modelAliases": [clean(x, 100) for x in (item.get("modelAliases") or [])[:24]], "configuredServerSide": provider_id in configured_ids})
        budget = data.get("budget") if isinstance(data.get("budget"), dict) else {}
        budget = {"monthlyCostMicros": bounded_int(budget.get("monthlyCostMicros"), 0, 0, 10_000_000_000), "monthlyRequests": bounded_int(budget.get("monthlyRequests"), 0, 0, 10_000_000), "hardStop": budget.get("hardStop") is not False}
        model_profiles = safe_policy_value(data.get("modelProfiles") if isinstance(data.get("modelProfiles"), dict) else {})
        fallback = [clean(item, 100) for item in (data.get("fallback") or [])[:24] if isinstance(item, (str, int))]
        evaluation = safe_policy_value(data.get("evaluation") if isinstance(data.get("evaluation"), dict) else {"required": True})
        values = (clean(data.get("name") or "Workspace AI policy", 100), 1 if data.get("enabled", True) else 0, dumps(safe_providers), dumps(model_profiles), dumps(fallback), dumps(budget), dumps(evaluation))
        with self.connect() as db:
            row = db.execute("SELECT id FROM ai_routing_policies WHERE id=? AND workspace_id=?", (policy_id, workspace["id"])).fetchone()
            if row: db.execute("UPDATE ai_routing_policies SET name=?,enabled=?,providers_json=?,model_profiles_json=?,fallback_json=?,budget_json=?,evaluation_json=?,updated_at=? WHERE id=?", (*values, timestamp, policy_id))
            else: db.execute("INSERT INTO ai_routing_policies(id,workspace_id,name,enabled,providers_json,model_profiles_json,fallback_json,budget_json,evaluation_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (policy_id, workspace["id"], *values, user_id, timestamp, timestamp))
        self._audit(user_id, "ai.routing_policy_saved", "ai_policy", policy_id, {"providerCount": len(safe_providers)})
        return self.ai_policy(user_id)

    def list_ai_workflows(self, user_id: str):
        workspace = self._workspace(user_id)
        with self.connect() as db: rows = db.execute("SELECT * FROM ai_saved_workflows_v35 WHERE workspace_id=? ORDER BY updated_at DESC", (workspace["id"],)).fetchall()
        return [{**dict(row), "toolPolicy": loads(row["tool_policy_json"], {}), "contextPolicy": loads(row["context_policy_json"], {}), "confirmationPolicy": loads(row["confirmation_policy_json"], {})} for row in rows]

    def save_ai_workflow(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        name = clean(data.get("name") or "Agent workflow", 120); prompt = clean(data.get("promptTemplate"), 50_000)
        tool_policy = data.get("toolPolicy") if isinstance(data.get("toolPolicy"), dict) else {}
        # Never allow a saved workflow to expand beyond registered tool IDs supplied by the product.
        tool_policy["allowedToolIds"] = [clean(x, 120) for x in (tool_policy.get("allowedToolIds") or [])[:200]]
        with self.connect() as db:
            row = db.execute("SELECT id,version FROM ai_saved_workflows_v35 WHERE id=? AND workspace_id=?", (item_id, workspace["id"])).fetchone(); version = int(row["version"] or 1) + 1 if row else 1
            values = (name, clean(data.get("description"), 1000), prompt, dumps(tool_policy), dumps(data.get("contextPolicy") if isinstance(data.get("contextPolicy"), dict) else {}), dumps(data.get("confirmationPolicy") if isinstance(data.get("confirmationPolicy"), dict) else {}), clean(data.get("visibility") or "private", 30), version, timestamp)
            if row: db.execute("UPDATE ai_saved_workflows_v35 SET name=?,description=?,prompt_template=?,tool_policy_json=?,context_policy_json=?,confirmation_policy_json=?,visibility=?,version=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO ai_saved_workflows_v35(id,workspace_id,owner_id,name,description,prompt_template,tool_policy_json,context_policy_json,confirmation_policy_json,visibility,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, workspace["id"], user_id, *values[:-1], timestamp, timestamp))
        return {"id": item_id, "name": name, "version": version}

    # ---------- Template marketplace V36 ----------
    def list_marketplace(self, user_id: str, query: dict[str, list[str]]):
        workspace = self._workspace(user_id); search = self._query_one(query, "q").lower(); category = self._query_one(query, "category")
        sql = "SELECT * FROM marketplace_templates_v36 WHERE ((visibility='public' AND status='approved') OR workspace_id=?)"; args: list[Any] = [workspace["id"]]
        if category: sql += " AND category=?"; args.append(category)
        sql += " ORDER BY CASE WHEN workspace_id=? THEN 0 ELSE 1 END,updated_at DESC LIMIT 200"; args.append(workspace["id"])
        with self.connect() as db: rows = db.execute(sql, tuple(args)).fetchall()
        result = []
        for row in rows:
            item = {**dict(row), "compatibility": loads(row["compatibility_json"], {}), "preview": loads(row["preview_json"], {}), "moderation": loads(row["moderation_json"], {})}
            if search and search not in (item["title"] + " " + item["description"] + " " + item["category"]).lower(): continue
            result.append(item)
        return result

    def save_marketplace_template(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms(); title = clean(data.get("title") or "Untitled template", 160); item_slug = slug(data.get("slug") or title)
        requested_status = clean(data.get("status") or "draft", 30); visibility = clean(data.get("visibility") or "private", 30)
        if requested_status not in {"draft", "submitted"}: raise FuturePlatformError("Marketplace moderation states cannot be set through the author endpoint", "marketplace_moderation_required", 403)
        if visibility not in {"private", "workspace", "public"}: raise FuturePlatformError("Invalid template visibility")
        status = "submitted" if visibility == "public" else requested_status
        with self.connect() as db:
            row = db.execute("SELECT id,current_version,status FROM marketplace_templates_v36 WHERE id=? AND workspace_id=?", (item_id, workspace["id"])).fetchone(); version = int(row["current_version"] or 1) if row else 1
            if row and row["status"] in {"approved", "rejected", "suspended"}: raise FuturePlatformError("Create a new draft version instead of overwriting a moderated template", "marketplace_version_required", 409)
            compatibility = data.get("compatibility") if isinstance(data.get("compatibility"), dict) else {"minBuild": "0.52", "schema": 27}
            values = (title, item_slug, clean(data.get("category") or "invitation", 80), clean(data.get("description"), 4000), status, visibility, clean(data.get("licenseType") or "free", 40), bounded_int(data.get("priceMinor"), 0, 0, 1_000_000_000), clean(data.get("currency") or "USD", 8), version, dumps(compatibility), dumps(data.get("preview") if isinstance(data.get("preview"), dict) else {}), dumps({}), timestamp)
            if row: db.execute("UPDATE marketplace_templates_v36 SET title=?,slug=?,category=?,description=?,status=?,visibility=?,license_type=?,price_minor=?,currency=?,current_version=?,compatibility_json=?,preview_json=?,moderation_json=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO marketplace_templates_v36(id,workspace_id,owner_id,title,slug,category,description,status,visibility,license_type,price_minor,currency,current_version,compatibility_json,preview_json,moderation_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, workspace["id"], user_id, *values[:-1], timestamp, timestamp))
        return {"id": item_id, "title": title, "slug": item_slug, "status": status, "visibility": visibility, "version": version}

    def publish_marketplace_version(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); template_id = clean(data.get("templateId"), 160)
        package = data.get("package") if isinstance(data.get("package"), dict) else {}; manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else {}
        with self.connect() as db:
            row = db.execute("SELECT current_version FROM marketplace_templates_v36 WHERE id=? AND workspace_id=?", (template_id, workspace["id"])).fetchone()
            if not row: raise FuturePlatformError("Template not found", "template_not_found", 404)
            version = int(row["current_version"] or 0) + 1; item_id = uid(); fp = fingerprint({"package": package, "manifest": manifest})
            db.execute("INSERT INTO marketplace_template_versions_v36(id,template_id,version,package_json,manifest_json,fingerprint,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)", (item_id, template_id, version, dumps(package, 5_000_000), dumps(manifest), fp, user_id, now_ms()))
            db.execute("UPDATE marketplace_templates_v36 SET current_version=?,updated_at=? WHERE id=?", (version, now_ms(), template_id))
        return {"id": item_id, "templateId": template_id, "version": version, "fingerprint": fp}

    def install_marketplace_template(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); template_id = clean(data.get("templateId"), 160); timestamp = now_ms()
        with self.connect() as db:
            template = db.execute("SELECT id,current_version,status,visibility,license_type,price_minor,currency FROM marketplace_templates_v36 WHERE id=? AND ((visibility='public' AND status='approved') OR workspace_id=?)", (template_id, workspace["id"])).fetchone()
            if not template: raise FuturePlatformError("Template is unavailable", "template_unavailable", 404)
            installation = db.execute("SELECT id FROM marketplace_installations_v36 WHERE workspace_id=? AND template_id=?", (workspace["id"], template_id)).fetchone(); install_id = installation["id"] if installation else uid()
            license_data = {"type": template["license_type"], "priceMinor": template["price_minor"], "currency": template["currency"], "paymentStatus": "not-required" if int(template["price_minor"] or 0) == 0 else "external-checkout-required"}
            if int(template["price_minor"] or 0) > 0 and not data.get("externalLicenseReference"): raise FuturePlatformError("A paid template requires an external license reference", "license_required", 409)
            license_data["externalReference"] = clean(data.get("externalLicenseReference"), 200)
            if installation: db.execute("UPDATE marketplace_installations_v36 SET template_version=?,status='active',license_json=?,settings_json=?,updated_at=? WHERE id=?", (int(template["current_version"]), dumps(license_data), dumps(data.get("settings") if isinstance(data.get("settings"), dict) else {}), timestamp, install_id))
            else: db.execute("INSERT INTO marketplace_installations_v36(id,workspace_id,template_id,template_version,installed_by,status,license_json,settings_json,created_at,updated_at) VALUES(?,?,?,?,?,'active',?,?,?,?)", (install_id, workspace["id"], template_id, int(template["current_version"]), user_id, dumps(license_data), dumps(data.get("settings") if isinstance(data.get("settings"), dict) else {}), timestamp, timestamp))
        return {"id": install_id, "templateId": template_id, "version": int(template["current_version"]), "license": license_data}

    # ---------- Enterprise/government V42 ----------
    def list_protocols(self, user_id: str, invitation_id: str):
        scope = self._scope(invitation_id, user_id, "read")
        with self.connect() as db:
            rows = db.execute("SELECT * FROM enterprise_protocols_v42 WHERE invitation_id=? AND workspace_id=? ORDER BY updated_at DESC", (invitation_id, scope["workspace_id"])).fetchall()
            steps = db.execute("SELECT * FROM enterprise_approval_steps_v42 WHERE invitation_id=? AND workspace_id=? ORDER BY step_order", (invitation_id, scope["workspace_id"])).fetchall()
        return {"protocols": [{**dict(row), "document": loads(row["document_json"], {})} for row in rows], "approvalSteps": [{**dict(row), "decision": loads(row["decision_json"], {})} for row in steps]}

    def save_protocol(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        classification = clean(data.get("classification") or "internal", 40)
        if classification not in {"public", "internal", "restricted", "confidential"}: raise FuturePlatformError("Invalid classification")
        document = data.get("document") if isinstance(data.get("document"), dict) else {}
        with self.connect() as db:
            row = db.execute("SELECT id FROM enterprise_protocols_v42 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
            values = (clean(data.get("name") or "Government ceremony protocol", 160), clean(data.get("protocolType") or "government-ceremony", 80), classification, dumps(document), clean(data.get("status") or "draft", 30), timestamp)
            if row: db.execute("UPDATE enterprise_protocols_v42 SET name=?,protocol_type=?,classification=?,document_json=?,status=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO enterprise_protocols_v42(id,workspace_id,invitation_id,name,protocol_type,classification,document_json,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
        return {"id": item_id, "classification": classification, "document": document}

    def configure_approval_chain(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); steps = data.get("steps") if isinstance(data.get("steps"), list) else []
        if len(steps) > 32: raise FuturePlatformError("Approval chain exceeds 32 steps")
        protocol_id = clean(data.get("protocolId"), 160); timestamp = now_ms(); result = []
        with self.connect() as db:
            db.execute("DELETE FROM enterprise_approval_steps_v42 WHERE invitation_id=? AND workspace_id=? AND protocol_id=?", (invitation_id, scope["workspace_id"], protocol_id))
            for index, raw in enumerate(steps):
                if not isinstance(raw, dict): continue
                item_id = uid(); step_type = clean(raw.get("type") or "approval", 50); role = clean(raw.get("requiredRole") or "manager", 50)
                db.execute("INSERT INTO enterprise_approval_steps_v42(id,workspace_id,invitation_id,protocol_id,step_order,step_type,required_role,assignee_id,status,decision_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,'{}',?,?)", (item_id, scope["workspace_id"], invitation_id, protocol_id, index + 1, step_type, role, clean(raw.get("assigneeId"), 160), "pending", timestamp, timestamp))
                result.append({"id": item_id, "order": index + 1, "type": step_type, "requiredRole": role})
        return {"invitationId": invitation_id, "protocolId": protocol_id, "steps": result}

    # ---------- Advanced animation/export V44 ----------
    def list_animation_projects(self, user_id: str, invitation_id: str):
        scope = self._scope(invitation_id, user_id, "read")
        with self.connect() as db:
            projects = db.execute("SELECT * FROM animation_projects_v44 WHERE invitation_id=? AND workspace_id=? ORDER BY updated_at DESC", (invitation_id, scope["workspace_id"])).fetchall()
            exports = db.execute("SELECT * FROM animation_exports_v44 WHERE invitation_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT 100", (invitation_id, scope["workspace_id"])).fetchall()
        return {"projects": [{**dict(row), "timeline": loads(row["timeline_json"], {}), "audio": loads(row["audio_json"], {}), "reducedMotion": loads(row["reduced_motion_json"], {})} for row in projects], "exports": [{**dict(row), "settings": loads(row["settings_json"], {})} for row in exports]}

    def save_animation_project(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "edit"); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        timeline = self._normalize_timeline(data.get("timeline") if isinstance(data.get("timeline"), dict) else {})
        audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}; reduced = data.get("reducedMotion") if isinstance(data.get("reducedMotion"), dict) else {"mode": "simplify"}; fp = fingerprint({"timeline": timeline, "audio": audio, "reduced": reduced})
        with self.connect() as db:
            row = db.execute("SELECT id,version FROM animation_projects_v44 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone(); version = int(row["version"] or 1) + 1 if row else 1
            values = (clean(data.get("pageId") or "hero", 160), clean(data.get("name") or "Invitation animation", 160), version, dumps(timeline, 5_000_000), dumps(audio), dumps(reduced), fp, timestamp)
            if row: db.execute("UPDATE animation_projects_v44 SET page_id=?,name=?,version=?,timeline_json=?,audio_json=?,reduced_motion_json=?,fingerprint=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO animation_projects_v44(id,workspace_id,invitation_id,page_id,name,version,timeline_json,audio_json,reduced_motion_json,fingerprint,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
        return {"id": item_id, "version": version, "fingerprint": fp, "timeline": timeline}

    def submit_animation_export(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); project_id = clean(data.get("projectId"), 160); fmt = clean(data.get("format") or "webm", 20).lower()
        if fmt not in {"mp4", "webm", "gif", "png-sequence", "social-story"}: raise FuturePlatformError("Unsupported animation export format")
        settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}; export_id = uid(); timestamp = now_ms()
        job = self.platform.jobs.submit(scope["workspace_id"], user_id, "animation-export-v44", {"exportId": export_id, "projectId": project_id, "format": fmt, "settings": settings}, invitation_id, clean(data.get("idempotencyKey"), 160), 2)
        with self.connect() as db: db.execute("INSERT INTO animation_exports_v44(id,workspace_id,invitation_id,project_id,job_id,format,settings_json,status,result_asset_id,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (export_id, scope["workspace_id"], invitation_id, project_id, job["id"], fmt, dumps(settings), job["status"], "", user_id, timestamp, timestamp))
        return {"id": export_id, "jobId": job["id"], "format": fmt, "status": job["status"]}

    # ---------- Publishing/custom domains V45 ----------
    def list_publishing(self, user_id: str, invitation_id: str):
        scope = self._scope(invitation_id, user_id, "read")
        with self.connect() as db:
            domains = db.execute("SELECT * FROM custom_domains_v45 WHERE invitation_id=? AND workspace_id=? ORDER BY updated_at DESC", (invitation_id, scope["workspace_id"])).fetchall()
            environments = db.execute("SELECT * FROM publication_environments_v45 WHERE invitation_id=? AND workspace_id=? ORDER BY created_at", (invitation_id, scope["workspace_id"])).fetchall()
        return {"domains": [{**dict(row), "verification": loads(row["verification_json"], {}), "redirect": loads(row["redirect_json"], {})} for row in domains], "environments": [{**dict(row), "access": loads(row["access_json"], {}), "schedule": loads(row["schedule_json"], {})} for row in environments]}

    def save_domain(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); hostname = clean(data.get("hostname"), 253).lower().rstrip(".")
        if not re.fullmatch(r"(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", hostname): raise FuturePlatformError("Enter a valid domain name", "invalid_domain")
        item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms(); token = secrets.token_urlsafe(24)
        with self.connect() as db:
            existing = db.execute("SELECT id,verification_token FROM custom_domains_v45 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
            if existing: token = existing["verification_token"]; db.execute("UPDATE custom_domains_v45 SET hostname=?,environment=?,redirect_json=?,updated_at=? WHERE id=?", (hostname, clean(data.get("environment") or "production", 30), dumps(data.get("redirect") if isinstance(data.get("redirect"), dict) else {}), timestamp, item_id))
            else: db.execute("INSERT INTO custom_domains_v45(id,workspace_id,invitation_id,hostname,environment,status,verification_token,verification_json,certificate_status,redirect_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,'pending',?,'{}','pending',?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, hostname, clean(data.get("environment") or "production", 30), token, dumps(data.get("redirect") if isinstance(data.get("redirect"), dict) else {}), user_id, timestamp, timestamp))
        return {"id": item_id, "hostname": hostname, "status": "pending", "verification": {"type": "TXT", "name": f"_einvite.{hostname}", "value": token}}

    def verify_domain(self, user_id: str, data: dict[str, Any]):
        item_id = clean(data.get("domainId"), 160); workspace = self._workspace(user_id); evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
        # Explicit development evidence is accepted only when the server is not in production mode.
        production = bool(getattr(getattr(self.platform, "config", None), "production", False))
        if production and evidence.get("developmentVerified"):
            raise FuturePlatformError("Production domain verification requires a configured DNS verification provider", "domain_provider_required", 503)
        verified = bool(evidence.get("developmentVerified")) and not production
        with self.connect() as db:
            row = db.execute("SELECT invitation_id,hostname FROM custom_domains_v45 WHERE id=? AND workspace_id=?", (item_id, workspace["id"])).fetchone()
            if not row: raise FuturePlatformError("Domain not found", "domain_not_found", 404)
            db.execute("UPDATE custom_domains_v45 SET status=?,verification_json=?,certificate_status=?,updated_at=? WHERE id=?", ("verified" if verified else "pending", dumps({"checkedAt": now_ms(), **evidence}), "provider-pending" if verified else "pending", now_ms(), item_id))
        return {"id": item_id, "hostname": row["hostname"], "verified": verified, "certificateStatus": "provider-pending" if verified else "pending"}

    def save_publication_environment(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms(); name = clean(data.get("name") or "production", 80)
        env_type = clean(data.get("environmentType") or name, 30)
        if env_type not in {"preview", "staging", "production", "archive"}: raise FuturePlatformError("Invalid publication environment")
        schedule = data.get("schedule") if isinstance(data.get("schedule"), dict) else {}
        with self.connect() as db:
            row = db.execute("SELECT id FROM publication_environments_v45 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
            values = (name, env_type, slug(data.get("slug") or name), clean(data.get("domainId"), 160), dumps(data.get("access") if isinstance(data.get("access"), dict) else {}), dumps(schedule), clean(data.get("snapshotId"), 160), clean(data.get("status") or "draft", 30), timestamp)
            if row: db.execute("UPDATE publication_environments_v45 SET name=?,environment_type=?,slug=?,domain_id=?,access_json=?,schedule_json=?,snapshot_id=?,status=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO publication_environments_v45(id,workspace_id,invitation_id,name,environment_type,slug,domain_id,access_json,schedule_json,snapshot_id,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
        return {"id": item_id, "name": name, "environmentType": env_type, "schedule": schedule}

    def activate_domain(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); domain_id = clean(data.get("domainId"), 160)
        with self.connect() as db:
            row = db.execute("SELECT invitation_id,hostname,status FROM custom_domains_v45 WHERE id=? AND workspace_id=?", (domain_id, workspace["id"])).fetchone()
            if not row: raise FuturePlatformError("Domain not found", "domain_not_found", 404)
            self._scope(row["invitation_id"], user_id, "manage")
            if row["status"] != "verified": raise FuturePlatformError("Verify the domain before activation", "domain_not_verified", 409)
            db.execute("UPDATE invitations SET custom_domain=?,updated_at=? WHERE id=?", (row["hostname"], now_ms(), row["invitation_id"]))
            db.execute("UPDATE custom_domains_v45 SET status='active',updated_at=? WHERE id=?", (now_ms(), domain_id))
        self._audit(user_id, "publishing.custom_domain_activated", "invitation", row["invitation_id"], {"domainId": domain_id, "hostname": row["hostname"]})
        return {"id": domain_id, "hostname": row["hostname"], "status": "active"}

    # ---------- Data merge/bulk V47 ----------
    def list_merge(self, user_id: str, invitation_id: str):
        scope = self._scope(invitation_id, user_id, "read")
        with self.connect() as db:
            sources = db.execute("SELECT * FROM data_merge_sources_v47 WHERE invitation_id=? AND workspace_id=? ORDER BY updated_at DESC", (invitation_id, scope["workspace_id"])).fetchall()
            jobs = db.execute("SELECT * FROM data_merge_jobs_v47 WHERE invitation_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT 100", (invitation_id, scope["workspace_id"])).fetchall()
        return {"sources": [{**dict(row), "columns": loads(row["columns_json"], []), "mapping": loads(row["mapping_json"], {}), "validation": loads(row["validation_json"], {})} for row in sources], "jobs": [{**dict(row), "configuration": loads(row["configuration_json"], {}), "progress": loads(row["progress_json"], {}), "result": loads(row["result_json"], {})} for row in jobs]}

    def save_merge_source(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "edit"); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        source_type = clean(data.get("sourceType") or "csv", 30)
        if source_type not in {"csv", "xlsx", "json", "manual"}: raise FuturePlatformError("Unsupported merge source")
        columns = data.get("columns") if isinstance(data.get("columns"), list) else []
        safe_columns = [{"key": clean(x.get("key"), 100), "label": clean(x.get("label") or x.get("key"), 160), "type": clean(x.get("type") or "text", 30), "required": bool(x.get("required"))} for x in columns[:200] if isinstance(x, dict)]
        checksum = clean(data.get("checksum"), 128) or fingerprint({"columns": safe_columns, "mapping": data.get("mapping") or {}, "rowCount": data.get("rowCount") or 0})
        with self.connect() as db:
            row = db.execute("SELECT id FROM data_merge_sources_v47 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
            values = (clean(data.get("name") or "Guest data", 160), source_type, dumps(safe_columns), dumps(data.get("mapping") if isinstance(data.get("mapping"), dict) else {}), dumps(data.get("validation") if isinstance(data.get("validation"), dict) else {}), bounded_int(data.get("rowCount"), 0, 0, 1_000_000), checksum, clean(data.get("status") or "draft", 30), timestamp)
            if row: db.execute("UPDATE data_merge_sources_v47 SET name=?,source_type=?,columns_json=?,mapping_json=?,validation_json=?,row_count=?,checksum=?,status=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO data_merge_sources_v47(id,workspace_id,invitation_id,name,source_type,columns_json,mapping_json,validation_json,row_count,checksum,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
        return {"id": item_id, "checksum": checksum, "columns": safe_columns}

    def submit_merge_job(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); source_id = clean(data.get("sourceId"), 160); mode = clean(data.get("mode") or "preview", 30)
        if mode not in {"preview", "generate-drafts", "prepare-publications", "prepare-delivery"}: raise FuturePlatformError("Unsupported merge mode")
        configuration = data.get("configuration") if isinstance(data.get("configuration"), dict) else {}; rows = data.get("rows") if isinstance(data.get("rows"), list) else []
        if len(rows) > 5000: raise FuturePlatformError("One bulk job is limited to 5,000 rows", "bulk_limit")
        merge_id = uid(); timestamp = now_ms(); payload = {"mergeJobId": merge_id, "sourceId": source_id, "mode": mode, "configuration": configuration, "rows": rows[:5000]}
        job = self.platform.jobs.submit(scope["workspace_id"], user_id, "bulk-generation-v47", payload, invitation_id, clean(data.get("idempotencyKey"), 160), 2)
        with self.connect() as db: db.execute("INSERT INTO data_merge_jobs_v47(id,workspace_id,invitation_id,source_id,platform_job_id,mode,status,configuration_json,progress_json,result_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,? ,?,'{}','{}',?,?,?)", (merge_id, scope["workspace_id"], invitation_id, source_id, job["id"], mode, job["status"], dumps(configuration), user_id, timestamp, timestamp))
        return {"id": merge_id, "jobId": job["id"], "mode": mode, "status": job["status"], "rowCount": len(rows)}

    # ---------- Plugin platform V48 ----------
    def list_plugins(self, user_id: str):
        workspace = self._workspace(user_id)
        with self.connect() as db:
            catalog = db.execute("SELECT * FROM plugin_manifests_v48 WHERE status IN ('approved','development') ORDER BY updated_at DESC LIMIT 200").fetchall()
            installed = db.execute("SELECT * FROM plugin_installations_v48 WHERE workspace_id=? ORDER BY updated_at DESC", (workspace["id"],)).fetchall()
            grants = db.execute("SELECT * FROM plugin_grants_v48 WHERE workspace_id=? AND revoked_at IS NULL", (workspace["id"],)).fetchall()
        return {"catalog": [{**dict(row), "manifest": loads(row["manifest_json"], {})} for row in catalog], "installed": [{**dict(row), "configuration": loads(row["configuration_json"], {})} for row in installed], "grants": [{**dict(row), "scope": loads(row["scope_json"], {})} for row in grants]}

    def register_plugin_manifest(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else {}; normalized = self._validate_plugin_manifest(manifest)
        key = normalized["key"]; version = normalized["version"]; fp = fingerprint(normalized); item_id = uid(); timestamp = now_ms(); signature = clean(data.get("signature"), 1000)
        # Development manifests may be unsigned; public approval must be performed by an external reviewer/signing process.
        status = "development" if not signature else "submitted"
        with self.connect() as db:
            existing = db.execute("SELECT id FROM plugin_manifests_v48 WHERE plugin_key=? AND version=?", (key, version)).fetchone()
            if existing: item_id = existing["id"]; db.execute("UPDATE plugin_manifests_v48 SET name=?,description=?,publisher=?,manifest_json=?,signature=?,fingerprint=?,status=?,updated_at=? WHERE id=?", (normalized["name"], normalized.get("description", ""), normalized.get("publisher", ""), dumps(normalized), signature, fp, status, timestamp, item_id))
            else: db.execute("INSERT INTO plugin_manifests_v48(id,plugin_key,version,name,description,publisher,manifest_json,signature,fingerprint,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, key, version, normalized["name"], normalized.get("description", ""), normalized.get("publisher", ""), dumps(normalized), signature, fp, status, timestamp, timestamp))
        self._audit(user_id, "plugin.manifest_registered", "plugin", key, {"version": version, "workspaceId": workspace["id"], "status": status})
        return {"id": item_id, "key": key, "version": version, "fingerprint": fp, "status": status}

    def install_plugin(self, user_id: str, data: dict[str, Any]):
        workspace = self._workspace(user_id); key = clean(data.get("pluginKey"), 100); version = clean(data.get("version"), 40); requested = [clean(x, 80) for x in (data.get("permissions") or [])]
        if any(permission not in PLUGIN_PERMISSIONS for permission in requested): raise FuturePlatformError("Plugin requested an unsupported permission", "unsafe_plugin_permission")
        with self.connect() as db:
            row = db.execute("SELECT manifest_json,status FROM plugin_manifests_v48 WHERE plugin_key=? AND version=?", (key, version)).fetchone()
            if not row or row["status"] not in {"approved", "development"}: raise FuturePlatformError("Plugin version is unavailable", "plugin_unavailable", 404)
            manifest = loads(row["manifest_json"], {}); declared = set(manifest.get("permissions") or [])
            if not set(requested).issubset(declared): raise FuturePlatformError("Requested grants exceed the plugin manifest", "plugin_grant_exceeds_manifest")
            existing = db.execute("SELECT id FROM plugin_installations_v48 WHERE workspace_id=? AND plugin_key=?", (workspace["id"], key)).fetchone(); item_id = existing["id"] if existing else uid(); timestamp = now_ms()
            if existing: db.execute("UPDATE plugin_installations_v48 SET plugin_version=?,status='enabled',configuration_json=?,updated_at=? WHERE id=?", (version, dumps(data.get("configuration") if isinstance(data.get("configuration"), dict) else {}), timestamp, item_id))
            else: db.execute("INSERT INTO plugin_installations_v48(id,workspace_id,plugin_key,plugin_version,status,configuration_json,installed_by,created_at,updated_at) VALUES(?,?,?,?, 'enabled',?,?,?,?)", (item_id, workspace["id"], key, version, dumps(data.get("configuration") if isinstance(data.get("configuration"), dict) else {}), user_id, timestamp, timestamp))
            db.execute("UPDATE plugin_grants_v48 SET revoked_at=? WHERE workspace_id=? AND plugin_key=? AND revoked_at IS NULL", (timestamp, workspace["id"], key))
            for permission in requested:
                db.execute("INSERT INTO plugin_grants_v48(id,workspace_id,plugin_key,permission,scope_json,granted_by,created_at,revoked_at) VALUES(?,?,?,?,?,?,?,NULL) ON CONFLICT(workspace_id,plugin_key,permission) DO UPDATE SET scope_json=excluded.scope_json,granted_by=excluded.granted_by,created_at=excluded.created_at,revoked_at=NULL", (uid(), workspace["id"], key, permission, dumps(data.get("scope") if isinstance(data.get("scope"), dict) else {}), user_id, timestamp))
        return {"id": item_id, "pluginKey": key, "version": version, "status": "enabled", "permissions": requested}

    # ---------- Intelligent automation and event ecosystem V52 ----------
    def event_dashboard(self, user_id: str, invitation_id: str):
        scope = self._scope(invitation_id, user_id, "read")
        with self.connect() as db:
            programs = db.execute("SELECT * FROM event_programs_v52 WHERE invitation_id=? AND workspace_id=? ORDER BY start_at,created_at", (invitation_id, scope["workspace_id"])).fetchall()
            tasks = db.execute("SELECT * FROM event_tasks_v52 WHERE invitation_id=? AND workspace_id=? ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,due_at", (invitation_id, scope["workspace_id"])).fetchall()
            vendors = db.execute("SELECT * FROM event_vendors_v52 WHERE invitation_id=? AND workspace_id=? ORDER BY category,name", (invitation_id, scope["workspace_id"])).fetchall()
            incidents = db.execute("SELECT * FROM event_incidents_v52 WHERE invitation_id=? AND workspace_id=? ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,created_at DESC", (invitation_id, scope["workspace_id"])).fetchall()
            automations = db.execute("SELECT * FROM event_automations_v52 WHERE invitation_id=? AND workspace_id=? ORDER BY updated_at DESC", (invitation_id, scope["workspace_id"])).fetchall()
        return {
            "programs": [{**dict(row), "program": loads(row["program_json"], {}), "operations": loads(row["operations_json"], {})} for row in programs],
            "tasks": [{**dict(row), "dependencies": loads(row["dependencies_json"], []), "details": loads(row["details_json"], {})} for row in tasks],
            "vendors": [{**dict(row), "contact": loads(row["contact_json"], {}), "contract": loads(row["contract_json"], {})} for row in vendors],
            "incidents": [{**dict(row), "location": loads(row["location_json"], {})} for row in incidents],
            "automations": [{**dict(row), "trigger": loads(row["trigger_json"], {}), "conditions": loads(row["conditions_json"], []), "actions": loads(row["actions_json"], [])} for row in automations],
        }

    def save_event_entity(self, user_id: str, kind: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "edit"); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        with self.connect() as db:
            if kind == "program":
                values = (clean(data.get("name") or "Event program", 160), clean(data.get("eventType") or "ceremony", 80), clean(data.get("timezone") or "Asia/Phnom_Penh", 80), data.get("startAt"), data.get("endAt"), clean(data.get("status") or "planning", 30), dumps(data.get("program") if isinstance(data.get("program"), dict) else {}), dumps(data.get("operations") if isinstance(data.get("operations"), dict) else {}), timestamp)
                row = db.execute("SELECT id FROM event_programs_v52 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
                if row: db.execute("UPDATE event_programs_v52 SET name=?,event_type=?,timezone=?,start_at=?,end_at=?,status=?,program_json=?,operations_json=?,updated_at=? WHERE id=?", (*values, item_id))
                else: db.execute("INSERT INTO event_programs_v52(id,workspace_id,invitation_id,name,event_type,timezone,start_at,end_at,status,program_json,operations_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
            elif kind == "task":
                values = (clean(data.get("programId"), 160), clean(data.get("title") or "Event task", 240), clean(data.get("category") or "general", 80), clean(data.get("assigneeId"), 160), clean(data.get("status") or "todo", 30), clean(data.get("priority") or "normal", 30), data.get("dueAt"), dumps(data.get("dependencies") if isinstance(data.get("dependencies"), list) else []), dumps(data.get("details") if isinstance(data.get("details"), dict) else {}), timestamp)
                row = db.execute("SELECT id FROM event_tasks_v52 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
                if row: db.execute("UPDATE event_tasks_v52 SET program_id=?,title=?,category=?,assignee_id=?,status=?,priority=?,due_at=?,dependencies_json=?,details_json=?,updated_at=? WHERE id=?", (*values, item_id))
                else: db.execute("INSERT INTO event_tasks_v52(id,workspace_id,invitation_id,program_id,title,category,assignee_id,status,priority,due_at,dependencies_json,details_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
            elif kind == "vendor":
                values = (clean(data.get("name") or "Vendor", 160), clean(data.get("category") or "general", 80), dumps(data.get("contact") if isinstance(data.get("contact"), dict) else {}), dumps(data.get("contract") if isinstance(data.get("contract"), dict) else {}), clean(data.get("status") or "active", 30), timestamp)
                row = db.execute("SELECT id FROM event_vendors_v52 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
                if row: db.execute("UPDATE event_vendors_v52 SET name=?,category=?,contact_json=?,contract_json=?,status=?,updated_at=? WHERE id=?", (*values, item_id))
                else: db.execute("INSERT INTO event_vendors_v52(id,workspace_id,invitation_id,name,category,contact_json,contract_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], timestamp, timestamp))
            elif kind == "incident":
                values = (clean(data.get("programId"), 160), clean(data.get("severity") or "low", 30), clean(data.get("title") or "Incident", 240), clean(data.get("description"), 8000), clean(data.get("status") or "open", 30), dumps(data.get("location") if isinstance(data.get("location"), dict) else {}), timestamp, data.get("resolvedAt"))
                row = db.execute("SELECT id FROM event_incidents_v52 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
                if row: db.execute("UPDATE event_incidents_v52 SET program_id=?,severity=?,title=?,description=?,status=?,location_json=?,updated_at=?,resolved_at=? WHERE id=?", (*values, item_id))
                else: db.execute("INSERT INTO event_incidents_v52(id,workspace_id,invitation_id,program_id,severity,title,description,status,location_json,reported_by,created_at,updated_at,resolved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:6], user_id, timestamp, timestamp, values[-1]))
            else: raise FuturePlatformError("Unsupported event entity")
        return {"id": item_id, "kind": kind, "invitationId": invitation_id}

    def save_event_automation(self, user_id: str, data: dict[str, Any]):
        invitation_id = clean(data.get("invitationId"), 160); scope = self._scope(invitation_id, user_id, "manage"); item_id = clean(data.get("id"), 160) or uid(); timestamp = now_ms()
        trigger_type = clean(data.get("triggerType") or "manual", 80); actions = data.get("actions") if isinstance(data.get("actions"), list) else []
        safe_actions = [self._normalize_automation_action(item) for item in actions[:40] if isinstance(item, dict)]
        enabled = 1 if data.get("enabled") else 0
        with self.connect() as db:
            row = db.execute("SELECT id FROM event_automations_v52 WHERE id=? AND workspace_id=?", (item_id, scope["workspace_id"])).fetchone()
            values = (clean(data.get("name") or "Event automation", 160), trigger_type, dumps(data.get("trigger") if isinstance(data.get("trigger"), dict) else {}), dumps(data.get("conditions") if isinstance(data.get("conditions"), list) else []), dumps(safe_actions), enabled, data.get("nextRunAt"), timestamp)
            if row: db.execute("UPDATE event_automations_v52 SET name=?,trigger_type=?,trigger_json=?,conditions_json=?,actions_json=?,enabled=?,next_run_at=?,updated_at=? WHERE id=?", (*values, item_id))
            else: db.execute("INSERT INTO event_automations_v52(id,workspace_id,invitation_id,name,trigger_type,trigger_json,conditions_json,actions_json,enabled,next_run_at,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, scope["workspace_id"], invitation_id, *values[:-1], user_id, timestamp, timestamp))
        return {"id": item_id, "triggerType": trigger_type, "actions": safe_actions, "enabled": bool(enabled)}

    def run_event_automation(self, user_id: str, data: dict[str, Any]):
        automation_id = clean(data.get("automationId"), 160); workspace = self._workspace(user_id)
        with self.connect() as db:
            row = db.execute("SELECT * FROM event_automations_v52 WHERE id=? AND workspace_id=?", (automation_id, workspace["id"])).fetchone()
            if not row: raise FuturePlatformError("Automation not found", "automation_not_found", 404)
        self._scope(row["invitation_id"], user_id, "manage")
        job = self.platform.jobs.submit(workspace["id"], user_id, "event-automation-v52", {"automationId": automation_id, "trigger": data.get("trigger") if isinstance(data.get("trigger"), dict) else {}}, row["invitation_id"], clean(data.get("idempotencyKey"), 160), 1)
        return {"automationId": automation_id, "jobId": job["id"], "status": job["status"]}

    def event_intelligence(self, user_id: str, invitation_id: str):
        scope = self._scope(invitation_id, user_id, "read"); timestamp = now_ms(); findings = []
        with self.connect() as db:
            programs = self._rows(db.execute("SELECT id,name,start_at,end_at,status FROM event_programs_v52 WHERE invitation_id=? AND workspace_id=? ORDER BY start_at", (invitation_id, scope["workspace_id"])).fetchall())
            tasks = self._rows(db.execute("SELECT id,title,status,priority,due_at,assignee_id FROM event_tasks_v52 WHERE invitation_id=? AND workspace_id=?", (invitation_id, scope["workspace_id"])).fetchall())
            incidents = self._rows(db.execute("SELECT id,title,severity,status FROM event_incidents_v52 WHERE invitation_id=? AND workspace_id=?", (invitation_id, scope["workspace_id"])).fetchall())
            vendors = self._rows(db.execute("SELECT id,name,category,contact_json,status FROM event_vendors_v52 WHERE invitation_id=? AND workspace_id=?", (invitation_id, scope["workspace_id"])).fetchall())
            approvals = self._rows(db.execute("SELECT id,step_order,required_role,status FROM enterprise_approval_steps_v42 WHERE invitation_id=? AND workspace_id=? ORDER BY step_order", (invitation_id, scope["workspace_id"])).fetchall())
        for index, program in enumerate(programs):
            if program.get("start_at") and program.get("end_at") and int(program["end_at"]) < int(program["start_at"]): findings.append({"severity":"high","type":"program.invalid_range","targets":[program["id"]],"message":f"{program['name']} ends before it starts.","suggestion":"Correct the program date range."})
            for other in programs[index+1:]:
                if program.get("start_at") and program.get("end_at") and other.get("start_at") and other.get("end_at") and int(program["start_at"]) < int(other["end_at"]) and int(other["start_at"]) < int(program["end_at"]): findings.append({"severity":"medium","type":"program.overlap","targets":[program["id"],other["id"]],"message":f"{program['name']} overlaps {other['name']}.","suggestion":"Confirm venues, staff and guest routing for the overlap."})
        for task in tasks:
            if task.get("due_at") and int(task["due_at"]) < timestamp and task.get("status") not in {"done","cancelled"}: findings.append({"severity":"high" if task.get("priority") in {"high","critical"} else "medium","type":"task.overdue","targets":[task["id"]],"message":f"Overdue task: {task['title']}","suggestion":"Assign an owner or revise the due date."})
            if not task.get("assignee_id") and task.get("status") not in {"done","cancelled"}: findings.append({"severity":"low","type":"task.unassigned","targets":[task["id"]],"message":f"Unassigned task: {task['title']}","suggestion":"Assign an operational owner."})
        for incident in incidents:
            if incident.get("status") != "resolved" and incident.get("severity") in {"high","critical"}: findings.append({"severity":"critical" if incident["severity"]=="critical" else "high","type":"incident.open","targets":[incident["id"]],"message":f"Open {incident['severity']} incident: {incident['title']}","suggestion":"Escalate to the event command lead."})
        for vendor in vendors:
            contact = loads(vendor.get("contact_json"), {})
            if vendor.get("status") == "active" and not any(contact.get(key) for key in ("phone","email","telegram","whatsapp")): findings.append({"severity":"low","type":"vendor.missing_contact","targets":[vendor["id"]],"message":f"{vendor['name']} has no operational contact.","suggestion":"Add at least one contact method."})
        pending = [step for step in approvals if step.get("status") == "pending"]
        if pending: findings.append({"severity":"medium","type":"approval.pending","targets":[step["id"] for step in pending],"message":f"{len(pending)} enterprise approval steps remain pending.","suggestion":"Complete the approval chain before production publication."})
        score = max(0, 100 - sum({"critical":25,"high":15,"medium":8,"low":3}.get(item["severity"],5) for item in findings))
        return {"version":1,"invitationId":invitation_id,"readinessScore":score,"findings":findings[:500],"generatedAt":timestamp,"mode":"deterministic-operational-intelligence"}

    # ---------- Dispatch ----------
    def dispatch_get(self, path: str, user_id: str, query: dict[str, list[str]]):
        if path == "/api/platform/v52/status": return 200, self.status(user_id)
        if path == "/api/platform/v52/editor/profiles": return 200, {"profiles": self.list_editor_profiles(user_id)}
        if path == "/api/platform/v52/ai/policy": return 200, self.ai_policy(user_id)
        if path == "/api/platform/v52/ai/workflows": return 200, {"workflows": self.list_ai_workflows(user_id)}
        if path == "/api/platform/v52/marketplace/templates": return 200, {"templates": self.list_marketplace(user_id, query)}
        if path == "/api/platform/v52/plugins": return 200, self.list_plugins(user_id)
        invitation_id = self._query_one(query, "invitationId")
        if path == "/api/platform/v52/enterprise": return 200, self.list_protocols(user_id, invitation_id)
        if path == "/api/platform/v52/animation": return 200, self.list_animation_projects(user_id, invitation_id)
        if path == "/api/platform/v52/publishing": return 200, self.list_publishing(user_id, invitation_id)
        if path == "/api/platform/v52/data-merge": return 200, self.list_merge(user_id, invitation_id)
        if path == "/api/platform/v52/events": return 200, self.event_dashboard(user_id, invitation_id)
        if path == "/api/platform/v52/events/intelligence": return 200, self.event_intelligence(user_id, invitation_id)
        return None

    def dispatch_post(self, path: str, user_id: str, data: dict[str, Any]):
        handlers = {
            "/api/platform/v52/editor/profiles": self.save_editor_profile,
            "/api/platform/v52/ai/policy": self.save_ai_policy,
            "/api/platform/v52/ai/workflows": self.save_ai_workflow,
            "/api/platform/v52/marketplace/templates": self.save_marketplace_template,
            "/api/platform/v52/marketplace/versions": self.publish_marketplace_version,
            "/api/platform/v52/marketplace/install": self.install_marketplace_template,
            "/api/platform/v52/enterprise/protocols": self.save_protocol,
            "/api/platform/v52/enterprise/approval-chain": self.configure_approval_chain,
            "/api/platform/v52/animation/projects": self.save_animation_project,
            "/api/platform/v52/animation/exports": self.submit_animation_export,
            "/api/platform/v52/publishing/domains": self.save_domain,
            "/api/platform/v52/publishing/domains/verify": self.verify_domain,
            "/api/platform/v52/publishing/domains/activate": self.activate_domain,
            "/api/platform/v52/publishing/environments": self.save_publication_environment,
            "/api/platform/v52/data-merge/sources": self.save_merge_source,
            "/api/platform/v52/data-merge/jobs": self.submit_merge_job,
            "/api/platform/v52/plugins/manifests": self.register_plugin_manifest,
            "/api/platform/v52/plugins/install": self.install_plugin,
            "/api/platform/v52/events/automations": self.save_event_automation,
            "/api/platform/v52/events/automations/run": self.run_event_automation,
        }
        if path in handlers: return 200, handlers[path](user_id, data)
        match = re.fullmatch(r"/api/platform/v52/events/(program|task|vendor|incident)s", path)
        if match: return 200, self.save_event_entity(user_id, match.group(1), data)
        return None

    # ---------- Validation and job executors ----------
    @staticmethod
    def _normalize_timeline(raw: dict[str, Any]) -> dict[str, Any]:
        duration = max(0, min(3_600_000, int(raw.get("duration") or 0))); tracks = []
        for track in (raw.get("tracks") or [])[:1000]:
            if not isinstance(track, dict): continue
            keyframes = []
            for frame in (track.get("keyframes") or [])[:5000]:
                if not isinstance(frame, dict): continue
                offset = max(0, min(duration or 3_600_000, int(frame.get("offset") or 0)))
                keyframes.append({"id": clean(frame.get("id"), 160) or uid(), "offset": offset, "value": frame.get("value"), "easing": clean(frame.get("easing") or "linear", 100)})
            keyframes.sort(key=lambda item: item["offset"])
            tracks.append({"id": clean(track.get("id"), 160) or uid(), "objectId": clean(track.get("objectId"), 160), "property": clean(track.get("property"), 80), "enabled": track.get("enabled") is not False, "keyframes": keyframes})
        return {"version": 1, "duration": duration, "fps": max(1, min(120, int(raw.get("fps") or 30))), "tracks": tracks, "markers": (raw.get("markers") or [])[:500], "loop": bool(raw.get("loop"))}

    @staticmethod
    def _validate_plugin_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"script", "javascript", "code", "eval", "html", "cssText", "filesystemPath", "networkUrl", "sql"}
        if any(key in manifest for key in forbidden): raise FuturePlatformError("Plugin manifests cannot contain executable content", "plugin_executable_content")
        key = slug(manifest.get("key"), 100); version = clean(manifest.get("version") or "0.1.0", 40); name = clean(manifest.get("name") or key, 160)
        permissions = [clean(x, 80) for x in (manifest.get("permissions") or [])]
        if any(item not in PLUGIN_PERMISSIONS for item in permissions): raise FuturePlatformError("Plugin manifest contains an unsupported permission", "unsafe_plugin_permission")
        extensions = []
        for item in (manifest.get("extensions") or [])[:40]:
            if not isinstance(item, dict): continue
            point = clean(item.get("point"), 80)
            if point not in PLUGIN_EXTENSION_POINTS: raise FuturePlatformError("Unsupported plugin extension point", "unsafe_extension_point")
            extensions.append({"id": clean(item.get("id"), 100), "point": point, "label": clean(item.get("label"), 160), "schema": item.get("schema") if isinstance(item.get("schema"), dict) else {}})
        return {"version": version, "key": key, "name": name, "description": clean(manifest.get("description"), 2000), "publisher": clean(manifest.get("publisher"), 160), "permissions": permissions, "extensions": extensions, "compatibility": manifest.get("compatibility") if isinstance(manifest.get("compatibility"), dict) else {"minBuild": "32.0", "schema": 27}}

    @staticmethod
    def _normalize_automation_action(item: dict[str, Any]) -> dict[str, Any]:
        action_type = clean(item.get("type"), 80)
        allowed = {"task.create", "task.update", "notification.prepare", "message.prepare", "publish.prepare", "check.run", "export.prepare", "guest.tag", "incident.create"}
        if action_type not in allowed: raise FuturePlatformError("Automation requested an unsupported action", "unsafe_automation_action")
        return {"type": action_type, "arguments": item.get("arguments") if isinstance(item.get("arguments"), dict) else {}, "confirmationRequired": action_type in {"message.prepare", "publish.prepare", "export.prepare"}}

    def _animation_export_job(self, payload, progress, cancelled):
        export_id = clean(payload.get("exportId"), 160); progress(.15)
        if cancelled(): return {"cancelled": True}
        with self.connect() as db:
            row = db.execute("SELECT workspace_id,invitation_id,format,settings_json,project_id FROM animation_exports_v44 WHERE id=?", (export_id,)).fetchone()
            if not row: raise FuturePlatformError("Animation export record is missing")
            project = db.execute("SELECT timeline_json,audio_json,reduced_motion_json,fingerprint FROM animation_projects_v44 WHERE id=? AND workspace_id=?", (row["project_id"], row["workspace_id"])).fetchone()
        manifest = {"version":1,"exportId":export_id,"invitationId":row["invitation_id"],"format":row["format"],"settings":loads(row["settings_json"],{}),"timeline":loads(project["timeline_json"],{}) if project else {},"audio":loads(project["audio_json"],{}) if project else {},"reducedMotion":loads(project["reduced_motion_json"],{}) if project else {},"projectFingerprint":project["fingerprint"] if project else "","renderer":"provider-neutral-manifest"}
        encoded = dumps(manifest, 5_000_000).encode("utf-8"); asset_id = f"animation-export-{export_id}"; key = self.platform.storage.safe_key(row["workspace_id"], asset_id, 1, f"animation-{row['format']}.json"); stored = self.platform.storage.put(key, encoded, "application/json", {"kind":"animation-export","invitation":row["invitation_id"]}); progress(.8)
        with self.connect() as db:
            db.execute("INSERT INTO object_versions(id,workspace_id,asset_id,version,provider,object_key,sha256,mime,size_bytes,metadata_json,visibility,created_at,deleted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?, ?,NULL) ON CONFLICT(asset_id,version) DO UPDATE SET provider=excluded.provider,object_key=excluded.object_key,sha256=excluded.sha256,mime=excluded.mime,size_bytes=excluded.size_bytes,metadata_json=excluded.metadata_json", (uid(), row["workspace_id"], asset_id, 1, stored["provider"], key, stored["sha256"], "application/json", len(encoded), dumps({"kind":"animation-export","format":row["format"]}), "private", now_ms()))
            db.execute("UPDATE animation_exports_v44 SET status='prepared',result_asset_id=?,updated_at=? WHERE id=?", (asset_id, now_ms(), export_id))
        progress(1); return {"exportId":export_id,"format":row["format"],"provider":"provider-neutral-manifest","resultAssetId":asset_id,"objectKey":key,"sha256":stored["sha256"]}

    def _bulk_generation_job(self, payload, progress, cancelled):
        merge_id = clean(payload.get("mergeJobId"), 160); rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []; mode = clean(payload.get("mode"), 30); created = 0; errors = []
        with self.connect() as db:
            job = db.execute("SELECT workspace_id,invitation_id,source_id FROM data_merge_jobs_v47 WHERE id=?", (merge_id,)).fetchone()
            if not job: raise FuturePlatformError("Merge job record is missing")
            source = db.execute("SELECT columns_json,mapping_json FROM data_merge_sources_v47 WHERE id=? AND workspace_id=? AND invitation_id=?", (job["source_id"], job["workspace_id"], job["invitation_id"])).fetchone()
            if not source: raise FuturePlatformError("Merge source is missing", "merge_source_missing", 409)
            columns = loads(source["columns_json"], []); mapping = loads(source["mapping_json"], {})
            allowed = {clean(item.get("key"), 160) for item in columns if isinstance(item, dict) and item.get("key")}
            required = {clean(item.get("key"), 160) for item in columns if isinstance(item, dict) and item.get("key") and item.get("required")}
            for index, row in enumerate(rows[:5000]):
                if cancelled(): break
                if not isinstance(row, dict): errors.append({"row": index + 1, "error": "Row must be an object"}); continue
                missing = [key for key in required if row.get(key) in (None, "")]
                if missing: errors.append({"row": index + 1, "error": "Missing required fields", "fields": sorted(missing)}); continue
                filtered = {key: row.get(key) for key in allowed if key in row}
                projected = {clean(target, 200): filtered.get(source_key) for source_key, target in mapping.items() if source_key in filtered and isinstance(target, str)}
                row_key = clean(row.get("id") or row.get("guestId") or str(index + 1), 160)
                token_hash = ""
                if mode != "preview": token_hash = hashlib.sha256(secrets.token_urlsafe(32).encode("utf-8")).hexdigest()
                variant = {"version": 2, "values": projected, "sourceKeys": sorted(filtered), "mode": mode, "invitationId": job["invitation_id"]}
                db.execute("INSERT INTO generated_invitation_variants_v47(id,workspace_id,invitation_id,merge_job_id,row_key,guest_id,variant_json,public_token_hash,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(merge_job_id,row_key) DO UPDATE SET variant_json=excluded.variant_json,public_token_hash=excluded.public_token_hash,status=excluded.status,updated_at=excluded.updated_at", (uid(), job["workspace_id"], job["invitation_id"], merge_id, row_key, clean(row.get("guestId"), 160), dumps(variant), token_hash, "preview" if mode == "preview" else "draft", now_ms(), now_ms()))
                created += 1; progress((index + 1) / max(1, min(len(rows), 5000)))
            result = {"created": created, "errors": errors[:1000], "mode": mode, "cancelled": cancelled(), "rawRowsPersisted": False, "personalizedTokensStoredAsHashes": mode != "preview"}
            db.execute("UPDATE data_merge_jobs_v47 SET status=?,progress_json=?,result_json=?,updated_at=? WHERE id=?", ("cancelled" if result["cancelled"] else "completed", dumps({"completed": created, "total": min(len(rows), 5000)}), dumps(result), now_ms(), merge_id))
        return result

    def _event_automation_job(self, payload, progress, cancelled):
        automation_id = clean(payload.get("automationId"), 160); run_id = uid(); timestamp = now_ms(); progress(.1)
        with self.connect() as db:
            row = db.execute("SELECT * FROM event_automations_v52 WHERE id=?", (automation_id,)).fetchone()
            if not row: raise FuturePlatformError("Automation not found")
            actions = loads(row["actions_json"], []); results = []
            db.execute("INSERT INTO event_automation_runs_v52(id,automation_id,workspace_id,invitation_id,status,trigger_json,result_json,started_at,completed_at) VALUES(?,?,?,?,? ,?,'{}',?,NULL)", (run_id, automation_id, row["workspace_id"], row["invitation_id"], "running", dumps(payload.get("trigger") or {}), timestamp))
            for index, action in enumerate(actions):
                if cancelled(): break
                results.append({"type": action.get("type"), "status": "confirmation-pending" if action.get("confirmationRequired") else "prepared", "arguments": action.get("arguments") or {}})
                progress(.1 + .8 * ((index + 1) / max(1, len(actions))))
            status = "cancelled" if cancelled() else "completed"; completed = now_ms()
            db.execute("UPDATE event_automation_runs_v52 SET status=?,result_json=?,completed_at=? WHERE id=?", (status, dumps({"actions": results}), completed, run_id))
            db.execute("UPDATE event_automations_v52 SET last_run_at=?,updated_at=? WHERE id=?", (completed, completed, automation_id))
        progress(1); return {"runId": run_id, "status": status, "actions": results}

    def _marketplace_package_job(self, payload, progress, cancelled):
        progress(.25)
        if cancelled(): return {"cancelled": True}
        result = {"templateId": clean(payload.get("templateId"), 160), "status": "package-prepared", "fingerprint": fingerprint(payload)}
        progress(1); return result
