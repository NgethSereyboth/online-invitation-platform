"""V28 agent orchestration, plans, confirmation policy and NDJSON events."""
from __future__ import annotations
from typing import Any, Callable, Iterable
import json
import secrets
import threading
import time

from .config import AgentConfig
from .context import ContextBuilder, ContextError
from .providers import ProviderError, create_provider
from .storage import AgentStore
from .tools import ToolValidationError, get_tool, tool_catalog, validate_tool_calls
from .capabilities import build_access_snapshot, filter_catalog, assert_calls_available, coverage_report, http_request_matches_tool
from .design_blueprints import DesignBlueprintAnalyzer, DesignBlueprintError


class AgentServiceError(RuntimeError):
    def __init__(self, message: str, code: str = "agent_error", status: int = 400, detail: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.detail = detail or {}

    def payload(self) -> dict[str, Any]:
        return {"error": str(self), "code": self.code, **self.detail}


class AgentService:
    PERMISSION_ROLES = {
        "read": {"owner", "manager", "designer", "content", "viewer"},
        "edit": {"owner", "manager", "designer", "content"},
        "manage": {"owner", "manager"},
    }
    def __init__(self, connect: Callable[[], Any], config: AgentConfig, audit: Callable[..., Any] | None = None, asset_reader: Callable[[str, str, str], dict[str, Any]] | None = None):
        self.connect = connect
        self.config = config
        self.store = AgentStore(connect, config.retention_days_default)
        self.context = ContextBuilder(connect, config.max_context_bytes)
        self.provider = create_provider(config)
        self.blueprints = DesignBlueprintAnalyzer(connect, config, asset_reader)
        self.audit = audit
        self._running: dict[str, set[str]] = {}
        self._tool_authorizations: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _emit_audit(self, user_id: str, action: str, invitation_id: str, metadata: dict[str, Any]) -> None:
        if not self.audit:
            return
        try:
            self.audit(user_id, action, "invitation", invitation_id, metadata)
        except Exception:
            pass

    def status(self, user_id: str, invitation_id: str | None = None) -> dict[str, Any]:
        prefs = self.store.preferences(user_id, self.config.enabled_default)
        provider_mode = "fake" if self.config.fake_provider_enabled else ("local" if self.config.provider == "local" and self.config.local_enabled else ("connected" if self.config.connected else ("local-fallback" if self.config.local_enabled else "offline")))
        local = {"enabled": bool(self.config.local_enabled), "providers": [], "modelRoles": dict(self.config.local_model_roles or {}), "modelDirectoryConfigured": bool(self.config.local_model_dir)}
        if self.config.local_enabled:
            try:
                from .local_providers import LocalProviderManager
                discovered = LocalProviderManager(self.config.local_provider_specs, self.config.local_provider_allowlist, self.config.local_provider_timeout_seconds, self.config.local_provider_concurrency, self.config.local_model_roles or {}).catalog()
                self.store.record_local_catalog(self.config.local_provider_specs, discovered)
                local["providers"] = [{"id":item.get("id"),"label":item.get("label"),"kind":item.get("kind"),"healthy":bool(item.get("healthy")),"availableModelCount":len(item.get("models") or []),"checkedAt":item.get("checkedAt"),"lastSuccessfulCheck":item.get("lastSuccessfulCheck")} for item in discovered]
            except Exception:
                local["providers"] = [{"id": str(item.get("id") or "local"), "label": str(item.get("label") or item.get("id") or "Local provider"), "healthy": False, "availableModelCount": 0} for item in self.config.local_provider_specs]
        return {
            "version": "53.1",
            "enabled": prefs["enabled"],
            "providerMode": provider_mode,
            "providerDisclosure": self.config.disclosure if prefs["providerDisclosure"] else "Provider disclosure hidden by account preference",
            "conversationPersistence": "project-scoped" if invitation_id else "available after a project is selected",
            "offlineMode": "session-only",
            "preferences": prefs,
            "learning": self.store.learning_summary(user_id, invitation_id or ""),
            "localAI": local,
            "limits": {"maxToolCalls": self.config.max_tool_calls, "maxActionsPerJob": self.config.max_actions_per_job, "maxConcurrentJobs": self.config.max_concurrent_jobs, "maxContextBytes": self.config.max_context_bytes},
        }

    def admin_local_provider_status(self, public_roots: tuple[str, ...] = ()) -> dict[str, Any]:
        from .local_providers import LocalProviderManager, discover_model_directory
        manager = LocalProviderManager(self.config.local_provider_specs, self.config.local_provider_allowlist, self.config.local_provider_timeout_seconds, self.config.local_provider_concurrency, self.config.local_model_roles or {})
        providers = manager.catalog(force=True) if self.config.local_enabled else []
        if providers:
            self.store.record_local_catalog(self.config.local_provider_specs, providers)
        return {
            "version":"53.1",
            "enabled":bool(self.config.local_enabled),
            "providers":providers,
            "modelRoles":manager.role_status() if self.config.local_enabled else {},
            "modelDirectory":discover_model_directory(self.config.local_model_dir, public_roots),
            "timeoutSeconds":self.config.local_provider_timeout_seconds,
            "concurrency":self.config.local_provider_concurrency,
        }

    def capability_catalog(self, user_id: str, invitation_id: str = "", role: str = "") -> dict[str, Any]:
        snapshot = build_access_snapshot(self.connect, user_id, invitation_id, role)
        allowed, denied = filter_catalog(tool_catalog(), snapshot)
        return {"version":"53.1", "tools":allowed, "denied":denied, "access":snapshot, "coverage":coverage_report(tool_catalog())}

    def analyze_reference(self, invitation_id: str, user_id: str, role: str, data: dict[str, Any]) -> dict[str, Any]:
        if role not in self.PERMISSION_ROLES["edit"]:
            raise AgentServiceError("Your collaboration role cannot analyze and apply reference designs", "tool_permission_denied", 403)
        asset_ids=data.get("assetIds") if isinstance(data.get("assetIds"),list) else []
        mode=str(data.get("mode") or "style")[:30]
        if mode not in {"create","style","palette","typography"}:raise AgentServiceError("Unsupported blueprint mode","invalid_blueprint_mode",400)
        try:blueprint,provider_mode=self.blueprints.analyze(invitation_id,user_id,asset_ids)
        except DesignBlueprintError as exc:raise AgentServiceError(str(exc),exc.code,400) from exc
        record=self.store.save_design_blueprint(invitation_id,user_id,[str(x) for x in asset_ids],mode,provider_mode,blueprint)
        self._emit_audit(user_id,"ai.design_blueprint_created",invitation_id,{"blueprintId":record["id"],"mode":mode,"providerMode":provider_mode,"assetCount":len(asset_ids)})
        return record

    def list_blueprints(self, invitation_id: str, user_id: str) -> list[dict[str, Any]]:
        return self.store.list_design_blueprints(invitation_id,user_id)

    def get_blueprint(self, invitation_id: str, user_id: str, blueprint_id: str) -> dict[str, Any]:
        value=self.store.get_design_blueprint(invitation_id,user_id,blueprint_id)
        if not value:raise AgentServiceError("Design blueprint not found","blueprint_not_found",404)
        return value

    def update_preferences(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.store.update_preferences(user_id, data, self.config.enabled_default)

    def list_memories(self, user_id: str, invitation_id: str = "") -> list[dict[str, Any]]:
        self._assert_enabled(user_id)
        return self.store.list_memories(user_id, invitation_id)

    def add_memory(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._assert_enabled(user_id)
        memory = self.store.create_memory(user_id, str(data.get("content") or ""), str(data.get("scope") or "account"), str(data.get("invitationId") or ""), str(data.get("kind") or "preference"))
        self._emit_audit(user_id, "ai.memory_created", str(data.get("invitationId") or ""), {"memoryId": memory["id"], "scope": memory["scope"], "kind": memory["kind"]})
        return memory

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        deleted = self.store.delete_memory(user_id, memory_id)
        if deleted:
            self._emit_audit(user_id, "ai.memory_deleted", "", {"memoryId": memory_id})
        return deleted

    def list_knowledge_sources(self, user_id: str, invitation_id: str = "") -> list[dict[str, Any]]:
        self._assert_enabled(user_id)
        return self.store.list_knowledge_sources(user_id, invitation_id)

    def add_knowledge_source(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._assert_enabled(user_id)
        source = self.store.create_knowledge_source(
            user_id,
            str(data.get("title") or ""),
            str(data.get("content") or ""),
            str(data.get("scope") or "invitation"),
            str(data.get("invitationId") or ""),
            str(data.get("sourceType") or "text"),
        )
        self._emit_audit(user_id, "ai.knowledge_created", str(data.get("invitationId") or ""), {"sourceId": source["id"], "scope": source["scope"], "sourceType": source["sourceType"]})
        return source

    def delete_knowledge_source(self, user_id: str, source_id: str) -> bool:
        deleted = self.store.delete_knowledge_source(user_id, source_id)
        if deleted:
            self._emit_audit(user_id, "ai.knowledge_deleted", "", {"sourceId": source_id})
        return deleted

    def record_feedback(self, invitation_id: str, user_id: str, message_id: str, data: dict[str, Any]) -> dict[str, Any]:
        prefs = self._assert_enabled(user_id)
        rating = int(data.get("rating") or 0)
        if rating not in {-1, 1}:
            raise AgentServiceError("Feedback rating must be positive or negative", "invalid_feedback")
        remember = bool(data.get("remember")) and bool(prefs.get("memoryEnabled", True))
        result = self.store.record_feedback(invitation_id, user_id, message_id, rating, data.get("tags") if isinstance(data.get("tags"), list) else [], str(data.get("comment") or ""), remember)
        self._emit_audit(user_id, "ai.feedback_recorded", invitation_id, {"messageId": message_id, "rating": rating, "remember": remember})
        return result

    def _assert_enabled(self, user_id: str) -> dict[str, Any]:
        prefs = self.store.preferences(user_id, self.config.enabled_default)
        if not prefs["enabled"]:
            raise AgentServiceError("AI is disabled for this account", "ai_disabled", 403)
        return prefs

    def create_thread(self, invitation_id: str, user_id: str, title: str = "New agent chat") -> dict[str, Any]:
        self._assert_enabled(user_id)
        return self.store.create_conversation(invitation_id, user_id, title, "connected" if self.config.connected else "offline")

    def list_threads(self, invitation_id: str, user_id: str) -> list[dict[str, Any]]:
        self.store.purge_expired(user_id)
        return self.store.list_conversations(invitation_id, user_id)

    def get_thread(self, invitation_id: str, user_id: str, conversation_id: str) -> dict[str, Any]:
        thread = self.store.get_conversation(conversation_id, invitation_id, user_id, include_messages=True)
        if not thread:
            raise AgentServiceError("Conversation not found", "conversation_not_found", 404)
        return thread

    def archive_thread(self, invitation_id: str, user_id: str, conversation_id: str) -> bool:
        return self.store.archive_conversation(conversation_id, invitation_id, user_id)

    @staticmethod
    def _history(thread: dict[str, Any]) -> list[dict[str, Any]]:
        history = []
        for message in thread.get("messages", [])[-40:]:
            if message.get("type") not in {"user", "assistant", "question", "result", "error"}:
                continue
            content = message.get("content") or {}
            history.append({"role": message.get("role"), "type": message.get("type"), "text": str(content.get("text") or "")[:10000]})
        return history

    def _budget_guard(self, invitation_id: str, user_id: str) -> dict[str, Any]:
        """Enforce optional workspace AI request/cost budgets without persisting provider secrets."""
        try:
            period = time.strftime("%Y-%m")
            with self.connect() as db:
                invite = db.execute("SELECT workspace_id FROM invitations WHERE id=?", (invitation_id,)).fetchone()
                workspace_id = invite["workspace_id"] if invite and invite["workspace_id"] else ""
                if not workspace_id:
                    return {"workspaceId": "", "period": period}
                policy = db.execute("SELECT enabled,budget_json FROM ai_routing_policies WHERE workspace_id=? ORDER BY updated_at DESC LIMIT 1", (workspace_id,)).fetchone()
                if not policy:
                    return {"workspaceId": workspace_id, "period": period}
                if not bool(policy["enabled"]):
                    raise AgentServiceError("Connected AI routing is disabled for this workspace", "workspace_ai_disabled", 403)
                budget = json.loads(policy["budget_json"] or "{}")
                usage = db.execute("SELECT COALESCE(SUM(request_count),0) requests,COALESCE(SUM(cost_micros),0) cost FROM ai_budget_ledger_v35 WHERE workspace_id=? AND period_key=?", (workspace_id, period)).fetchone()
                max_requests = max(0, int(budget.get("monthlyRequests") or 0)); max_cost = max(0, int(budget.get("monthlyCostMicros") or 0)); hard_stop = budget.get("hardStop") is not False
                if hard_stop and max_requests and int(usage["requests"] or 0) >= max_requests:
                    raise AgentServiceError("Workspace AI request budget has been reached", "ai_request_budget_reached", 429)
                if hard_stop and max_cost and int(usage["cost"] or 0) >= max_cost:
                    raise AgentServiceError("Workspace AI cost budget has been reached", "ai_cost_budget_reached", 429)
                return {"workspaceId": workspace_id, "period": period}
        except AgentServiceError:
            raise
        except Exception:
            return {"workspaceId": "", "period": time.strftime("%Y-%m")}

    def _record_workspace_usage(self, budget_context: dict[str, Any], user_id: str, result: Any) -> None:
        workspace_id = str(budget_context.get("workspaceId") or "")
        if not workspace_id:
            return
        usage = result.raw_usage if isinstance(result.raw_usage, dict) else {}
        try:
            with self.connect() as db:
                db.execute("INSERT INTO ai_budget_ledger_v35(id,workspace_id,user_id,provider,model,input_units,output_units,cost_micros,request_count,period_key,created_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)", (
                    secrets.token_hex(16), workspace_id, user_id, str(usage.get("routeId") or result.provider_mode)[:80], str(usage.get("model") or self.config.model or "")[:120],
                    max(0, int(usage.get("inputTokens") or usage.get("inputBytes") or 0)), max(0, int(usage.get("outputTokens") or usage.get("outputBytes") or 0)),
                    max(0, int(usage.get("costMicros") or 0)), str(budget_context.get("period") or time.strftime("%Y-%m")), int(time.time()*1000),
                ))
        except Exception:
            pass

    def _reserve_job(self, user_id: str, job_id: str) -> None:
        with self._lock:
            jobs = self._running.setdefault(user_id, set())
            if len(jobs) >= self.config.max_concurrent_jobs:
                raise AgentServiceError("Too many AI jobs are already running", "ai_concurrency_limit", 429)
            jobs.add(job_id)

    def _release_job(self, user_id: str, job_id: str) -> None:
        with self._lock:
            self._running.get(user_id, set()).discard(job_id)

    @staticmethod
    def event(event_type: str, **payload: Any) -> bytes:
        return (json.dumps({"type": event_type, "timestamp": int(time.time() * 1000), **payload}, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

    def stream_message(self, invitation_id: str, user_id: str, role: str, conversation_id: str, data: dict[str, Any]) -> Iterable[bytes]:
        prefs = self._assert_enabled(user_id)
        thread = self.get_thread(invitation_id, user_id, conversation_id)
        prompt = str(data.get("message") or "").strip()
        if not prompt or len(prompt) > 50_000:
            raise AgentServiceError("Message must contain 1 to 50,000 characters", "invalid_message")
        client_context = data.get("context") if isinstance(data.get("context"), dict) else {}
        idempotency_key = str(data.get("idempotencyKey") or secrets.token_urlsafe(18))[:160]
        budget_context = self._budget_guard(invitation_id, user_id)
        user_message = self.store.add_message(conversation_id, "user", "user", {"text": prompt, "context": {"pageId": client_context.get("pageId"), "objectIds": client_context.get("objectIds") or []}})
        try:
            context = self.context.build(invitation_id, user_id, role, client_context)
            context["learning"] = self.store.learning_context(user_id, invitation_id, prompt)
            reference_ids = client_context.get("referenceAssetIds") if isinstance(client_context.get("referenceAssetIds"), list) else []
            if reference_ids and role in self.PERMISSION_ROLES["edit"]:
                try:
                    blueprint, blueprint_mode = self.blueprints.analyze(invitation_id, user_id, reference_ids[:6])
                    stored_blueprint = self.store.save_design_blueprint(invitation_id,user_id,[str(x) for x in reference_ids[:6]],str(client_context.get("referenceMode") or "style")[:30],blueprint_mode,blueprint)
                    context["designBlueprint"] = {"id":stored_blueprint["id"], **blueprint}
                except Exception:
                    context["designBlueprint"] = {"available":False,"warning":"Reference-image analysis could not run; continue without claiming visual inspection."}
        except ContextError as exc:
            raise AgentServiceError(str(exc), "invalid_context", 409) from exc
        job = self.store.create_job(conversation_id, invitation_id, user_id)
        job_id = job["id"]
        try:
            self._reserve_job(user_id, job_id)
        except AgentServiceError:
            self.store.finish_job(job_id, "failed", {"code": "ai_concurrency_limit"})
            raise
        job_finished = False
        def finish(status: str, summary: dict[str, Any]) -> None:
            nonlocal job_finished
            if job_finished:
                return
            job_finished = True
            self.store.finish_job(job_id, status, summary)
        try:
            yield self.event("job.started", job=job, message=user_message)
            if self.store.job_cancelled(job_id):
                finish("cancelled", {"code": "cancelled"})
                yield self.event("job.cancelled", jobId=job_id)
                return
            access_snapshot = build_access_snapshot(self.connect, user_id, invitation_id, role)
            allowed_catalog, denied_catalog = filter_catalog(tool_catalog(), access_snapshot)
            context["authorization"] = {"access": access_snapshot, "availableToolIds": [item["id"] for item in allowed_catalog], "permissionBlockers": denied_catalog[:120]}
            yield self.event("context.ready", jobId=job_id, context={"invitation": context["invitation"], "activePageId": context["document"]["activePageId"], "selection": context["document"]["selection"], "pageSummaries": context["document"]["pageSummaries"], "permissionBlockers": denied_catalog[:120]})
            result = self.provider.generate(prompt, context, allowed_catalog, self._history(thread))
            validated_calls = validate_tool_calls(result.tool_calls, self.config.max_tool_calls)
            try:
                assert_calls_available(validated_calls, access_snapshot)
            except PermissionError as exc:
                raise AgentServiceError("The requested AI capability is not available for the current account or invitation state", "tool_permission_denied", 403, {"denied": getattr(exc, "denied", [])}) from exc
            if len(validated_calls) > self.config.max_actions_per_job:
                raise AgentServiceError("The proposed job exceeds the action limit", "too_many_actions", 400)
            if self.store.job_cancelled(job_id):
                finish("cancelled", {"code": "cancelled"})
                yield self.event("job.cancelled", jobId=job_id)
                return
            assistant_message = self.store.add_message(conversation_id, "assistant", "assistant", {"text": result.text, "providerMode": result.provider_mode, "disclosure": result.disclosure, "memoryCount": len((context.get("learning") or {}).get("memories") or [])})
            yield self.event("assistant.started", jobId=job_id, messageId=assistant_message["id"], providerMode=result.provider_mode, disclosure=result.disclosure)
            for chunk in self.provider.stream_text(result.text):
                if self.store.job_cancelled(job_id):
                    finish("cancelled", {"code": "cancelled"})
                    yield self.event("job.cancelled", jobId=job_id)
                    return
                yield self.event("assistant.delta", jobId=job_id, messageId=assistant_message["id"], delta=chunk)
            yield self.event("assistant.completed", jobId=job_id, message=assistant_message)
            if result.questions and not validated_calls:
                question_message = self.store.add_message(conversation_id, "assistant", "question", {"questions": result.questions, "text": result.questions[0]})
                yield self.event("question", jobId=job_id, message=question_message)
                finish("completed", {"questions": len(result.questions)})
                return
            if validated_calls:
                confirmations = [call for call in validated_calls if call["confirmationRequired"]]
                high_risk = [call for call in validated_calls if call["risk"] == "high"]
                plan_value = {
                    "summary": result.text[:2000],
                    "toolCalls": validated_calls,
                    "affectedPages": sorted({str(call["arguments"].get("pageId")) for call in validated_calls if call["arguments"].get("pageId")}),
                    "affectedObjectIds": sorted({str(value) for call in validated_calls for value in (call["arguments"].get("objectIds") or call["arguments"].get("targets") or [])}),
                    "estimatedActionCount": len(validated_calls),
                    "confirmationRequired": bool(confirmations or high_risk),
                    "confirmationReasons": [call["reason"] or call["id"] for call in confirmations or high_risk],
                    "autoApplyEligible": bool(prefs["allowLowRiskAuto"] and all(call["risk"] == "low" and call["reversible"] and not call["confirmationRequired"] for call in validated_calls)),
                    "providerMode": result.provider_mode,
                }
                plan = self.store.create_plan(conversation_id, invitation_id, user_id, context["invitation"]["revision"], context["invitation"]["fingerprint"], plan_value, idempotency_key)
                self.store.add_message(conversation_id, "assistant", "plan", {"planId": plan["id"], **plan_value})
                yield self.event("plan.proposed", jobId=job_id, plan=plan)
            self.store.record_usage(user_id, invitation_id, result.provider_mode, int(result.raw_usage.get("inputBytes", len(prompt.encode("utf-8")))), int(result.raw_usage.get("outputBytes", len(result.text.encode("utf-8")))), len(validated_calls))
            self._record_workspace_usage(budget_context, user_id, result)
            finish("completed", {"toolCalls": len(validated_calls)})
            self._emit_audit(user_id, "ai.plan_proposed", invitation_id, {"conversationId": conversation_id, "jobId": job_id, "toolIds": [call["id"] for call in validated_calls], "providerMode": result.provider_mode})
            yield self.event("job.completed", jobId=job_id, toolCallCount=len(validated_calls))
        except GeneratorExit:
            finish("cancelled", {"code": "client_disconnected"})
            raise
        except ToolValidationError as exc:
            finish("failed", {"code": exc.code})
            error_message = self.store.add_message(conversation_id, "assistant", "error", {"text": "The provider proposed an unsupported or unsafe tool action.", "code": exc.code})
            yield self.event("error", jobId=job_id, code=exc.code, message=str(exc), storedMessage=error_message)
        except ProviderError as exc:
            finish("failed", {"code": exc.code})
            error_message = self.store.add_message(conversation_id, "assistant", "error", {"text": "The provider could not complete the request. No project change was applied.", "code": exc.code})
            yield self.event("error", jobId=job_id, code=exc.code, message=str(exc), storedMessage=error_message)
        except AgentServiceError as exc:
            finish("failed", {"code": exc.code})
            error_message = self.store.add_message(conversation_id, "assistant", "error", {"text": "The proposed agent job was rejected before any project change was applied.", "code": exc.code})
            yield self.event("error", jobId=job_id, code=exc.code, message=str(exc), storedMessage=error_message)
        except Exception:
            finish("failed", {"code": "agent_internal_error"})
            error_message = self.store.add_message(conversation_id, "assistant", "error", {"text": "The agent job failed safely. No plan was authorized for execution.", "code": "agent_internal_error"})
            yield self.event("error", jobId=job_id, code="agent_internal_error", message="The agent job failed safely.", storedMessage=error_message)
        finally:
            self._release_job(user_id, job_id)

    def confirm_plan(self, invitation_id: str, user_id: str, role: str, plan_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._assert_enabled(user_id)
        plan = self.store.get_plan(plan_id, invitation_id, user_id)
        if not plan:
            raise AgentServiceError("Plan not found", "plan_not_found", 404)
        if plan["status"] not in {"proposed", "confirmed"}:
            raise AgentServiceError("Plan is no longer available", "plan_not_available", 409)
        unauthorized = [call.get("id") for call in plan.get("toolCalls", []) if role not in self.PERMISSION_ROLES.get(str(call.get("permission") or "manage"), set())]
        if unauthorized:
            raise AgentServiceError("Your invitation role cannot authorize one or more proposed actions", "tool_permission_denied", 403, {"toolIds": unauthorized})
        access_snapshot = build_access_snapshot(self.connect, user_id, invitation_id, role)
        try:
            assert_calls_available(plan.get("toolCalls", []), access_snapshot)
        except PermissionError as exc:
            self.store.update_plan_status(plan_id, invitation_id, user_id, "stale", {"reason":"capability_changed"})
            raise AgentServiceError("Permissions or account capability changed after this plan was prepared", "stale_capability", 409, {"denied": getattr(exc, "denied", [])}) from exc
        current = self.context.build(invitation_id, user_id, role, data.get("context") if isinstance(data.get("context"), dict) else {})
        if int(plan["documentRevision"] or 0) != int(current["invitation"]["revision"] or 0) or plan["documentFingerprint"] != current["invitation"]["fingerprint"]:
            self.store.update_plan_status(plan_id, invitation_id, user_id, "stale", {"reason": "revision_changed"})
            raise AgentServiceError("The invitation changed after this plan was prepared", "stale_plan", 409, {"currentRevision": current["invitation"]["revision"], "currentFingerprint": current["invitation"]["fingerprint"]})
        confirmation = {"confirmedAt": int(time.time() * 1000), "confirmedBy": user_id, "exactTargetsAccepted": bool(data.get("exactTargetsAccepted")), "destructiveAccepted": bool(data.get("destructiveAccepted"))}
        if plan.get("confirmationRequired") and not confirmation["exactTargetsAccepted"]:
            raise AgentServiceError("Confirm the exact targets and effects before execution", "confirmation_required", 409)
        if any(call.get("risk") == "high" for call in plan.get("toolCalls", [])) and not confirmation["destructiveAccepted"]:
            raise AgentServiceError("High-risk actions require explicit destructive-action confirmation", "destructive_confirmation_required", 409)
        updated = self.store.update_plan_status(plan_id, invitation_id, user_id, "confirmed", confirmation)
        self._emit_audit(user_id, "ai.plan_confirmed", invitation_id, {"planId": plan_id, "toolIds": [call["id"] for call in plan.get("toolCalls", [])]})
        return updated or plan

    def authorize_tool_call(self, invitation_id: str, user_id: str, role: str, plan_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Re-authorize one exact planned operation immediately before execution."""
        plan = self.store.get_plan(plan_id, invitation_id, user_id)
        if not plan or plan.get("status") != "confirmed":
            raise AgentServiceError("Only a confirmed plan can execute tools", "plan_not_confirmed", 409)
        index = int(data.get("index") if data.get("index") is not None else -1)
        calls = plan.get("toolCalls") or []
        if index < 0 or index >= len(calls):
            raise AgentServiceError("The requested tool operation is not part of this plan", "tool_call_not_planned", 409)
        call = calls[index]
        client_call_id = str(data.get("clientCallId") or "")[:120]
        if client_call_id and str(call.get("clientCallId") or "") and client_call_id != str(call.get("clientCallId") or ""):
            raise AgentServiceError("The planned tool operation does not match the client request", "tool_call_mismatch", 409)
        access_snapshot = build_access_snapshot(self.connect, user_id, invitation_id, role)
        try:
            assert_calls_available([call], access_snapshot)
        except PermissionError as exc:
            raise AgentServiceError("This operation is no longer authorized", "tool_permission_denied", 403, {"denied": getattr(exc, "denied", [])}) from exc
        current = self.context.build(invitation_id, user_id, role, data.get("context") if isinstance(data.get("context"), dict) else {})
        if int(plan["documentRevision"] or 0) != int(current["invitation"]["revision"] or 0) or plan["documentFingerprint"] != current["invitation"]["fingerprint"]:
            self.store.update_plan_status(plan_id, invitation_id, user_id, "stale", {"reason":"revision_changed_before_operation"})
            raise AgentServiceError("The invitation changed before this operation could run", "stale_plan", 409)
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            for expired_token, record in list(self._tool_authorizations.items()):
                if float(record.get("expiresAt") or 0) <= now:
                    self._tool_authorizations.pop(expired_token, None)
            self._tool_authorizations[token] = {
                "userId": user_id,
                "invitationId": invitation_id,
                "planId": plan_id,
                "index": index,
                "toolId": str(call.get("id") or ""),
                "expiresAt": now + 30,
            }
        self._emit_audit(user_id, "ai.tool_authorized", invitation_id, {"planId":plan_id,"index":index,"toolId":call.get("id")})
        return {"authorized":True,"authorizationToken":token,"planId":plan_id,"index":index,"toolId":call.get("id"),"expiresInSeconds":30}

    def consume_tool_authorization(self, token: str, invitation_id: str, user_id: str, tool_id: str, method: str = "", path: str = "") -> dict[str, Any]:
        """Consume one short-lived authorization issued for an exact planned tool."""
        token = str(token or "")
        if not token:
            raise AgentServiceError("AI tool authorization is required", "ai_tool_authorization_required", 403)
        with self._lock:
            record = self._tool_authorizations.pop(token, None)
        if not record or float(record.get("expiresAt") or 0) <= time.time():
            raise AgentServiceError("AI tool authorization expired or was already used", "ai_tool_authorization_invalid", 403)
        if not secrets.compare_digest(str(record.get("userId") or ""), str(user_id or "")):
            raise AgentServiceError("AI tool authorization belongs to another account", "ai_tool_authorization_invalid", 403)
        if not secrets.compare_digest(str(record.get("invitationId") or ""), str(invitation_id or "")):
            raise AgentServiceError("AI tool authorization belongs to another invitation", "ai_tool_authorization_invalid", 403)
        if not secrets.compare_digest(str(record.get("toolId") or ""), str(tool_id or "")):
            raise AgentServiceError("AI tool authorization does not match this operation", "ai_tool_authorization_invalid", 403)
        if not http_request_matches_tool(tool_id, method, path, invitation_id):
            raise AgentServiceError("AI tool authorization is not valid for this endpoint", "ai_tool_authorization_scope_mismatch", 403)
        self._emit_audit(user_id, "ai.tool_authorization_consumed", invitation_id, {"planId":record.get("planId"),"index":record.get("index"),"toolId":tool_id})
        return record

    def cancel_plan(self, invitation_id: str, user_id: str, plan_id: str) -> dict[str, Any]:
        plan = self.store.update_plan_status(plan_id, invitation_id, user_id, "cancelled", {"cancelledAt": int(time.time() * 1000)})
        if not plan:
            raise AgentServiceError("Plan not found", "plan_not_found", 404)
        return plan

    def complete_plan(self, invitation_id: str, user_id: str, plan_id: str, data: dict[str, Any]) -> dict[str, Any]:
        plan = self.store.get_plan(plan_id, invitation_id, user_id)
        if not plan:
            raise AgentServiceError("Plan not found", "plan_not_found", 404)
        if plan["status"] != "confirmed":
            raise AgentServiceError("Only a confirmed plan can report completion", "plan_not_confirmed", 409)
        status = "completed" if bool(data.get("ok")) else "failed"
        verification = data.get("verification") if isinstance(data.get("verification"), dict) else {}
        corrections = data.get("corrections") if isinstance(data.get("corrections"), list) else []
        try:
            verification_json = json.dumps(verification, ensure_ascii=False, separators=(",", ":"))
            if len(verification_json) > 30_000:
                verification = {"truncated": True, "ok": bool(verification.get("ok")), "summary": str(verification.get("summary") or "")[:4_000], "diagnosticCount": int(verification.get("diagnosticCount") or len(verification.get("diagnostics") or []))}
        except Exception:
            verification = {"truncated": True, "ok": False, "summary": "Verification payload could not be serialized."}
        safe_corrections = []
        for item in corrections[:20]:
            if isinstance(item, dict):
                safe_corrections.append({str(k)[:80]: v for k, v in list(item.items())[:20]})
            else:
                safe_corrections.append(str(item)[:500])
        result = {"completedAt": int(time.time() * 1000), "clientJobId": str(data.get("clientJobId") or "")[:160], "actionCount": max(0, min(200, int(data.get("actionCount") or 0))), "errorCode": str(data.get("errorCode") or "")[:120], "verification": verification, "corrections": safe_corrections}
        updated = self.store.update_plan_status(plan_id, invitation_id, user_id, status, {**(plan.get("confirmation") or {}), **result})
        self.store.record_verification(plan_id,invitation_id,user_id,status == "completed",verification,corrections)
        self.store.record_plan_outcomes(user_id, invitation_id, plan_id, [str(call.get("id") or "") for call in plan.get("toolCalls", [])], status == "completed", result["errorCode"])
        self._emit_audit(user_id, f"ai.plan_{status}", invitation_id, {"planId": plan_id, **result})
        return updated or plan

    def cancel_job(self, invitation_id: str, user_id: str, job_id: str) -> bool:
        cancelled = self.store.cancel_job(job_id, invitation_id, user_id)
        if cancelled:
            self._emit_audit(user_id, "ai.job_cancelled", invitation_id, {"jobId": job_id})
        return cancelled
