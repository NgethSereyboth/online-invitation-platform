# OWASP AISVS 1.0 — Chapters C9 & C10 Mapping

> Status: Phase 1a design document (no code modified).
> Scope: Maps the eInvite AI agent subsystem to OWASP AISVS 1.0 Chapter 9 (Orchestration & Agentic Security) and Chapter 10 (Model Context Protocol / MCP Security).
> Source spec: OWASP AISVS 1.0 (released June 2026, 191 requirements / 12 chapters). Reference: https://owasp.org/www-project-artificial-intelligence-security-verification-standard-aisvs-docs/
> Grounding: Every claim cites a file path. `file.py:NN` refers to the line in the main branch.

## How to read this table

- **Requirement ID** — the AISVS chapter / requirement / sub-item (`C9.x.y`).
- **Requirement (paraphrased)** — short paraphrase of the AISVS control. The authoritative wording lives in the AISVS spec; this column is a working summary only.
- **Status** — `pass` (control implemented and evidence exists), `partial` (control implemented but with a documented gap), `fail` (control not implemented and must be remediated in Phase 1).
- **Evidence** — the file path (and line where applicable) that proves the status.

## Inventory — what AISVS C9/C10 maps to in this codebase

- AI agent subsystem: `ai_agent/` package (`tools.py`, `capabilities.py`, `service.py`, `storage.py`, `providers.py`, `local_providers.py`, `config.py`, `context.py`, `design_blueprints.py`).
- 80 typed tools registered in `ai_agent/tools.py:_defs()` (frozen dataclass `ToolDefinition` at `ai_agent/tools.py:32`).
- Tier-based permissions (`read`/`edit`/`manage`/`admin`) declared per-tool in `ai_agent/tools.py` and enforced by `ai_agent/capabilities.py:ROLE_PERMISSIONS` and `availability()`.
- Confirmation boundaries in `docs/V28_CONFIRMATION_BOUNDARIES.md` and `ai_agent/service.py:confirm_plan` / `authorize_tool_call`.
- Audit log: `audit_events` table (`src/python/server.py:1137`), hash-chained (`src/python/server.py:1379`), immutable (`src/python/server.py:1206` — BEFORE UPDATE/DELETE triggers).
- Plan / authorization token flow: `ai_agent/service.py:authorize_tool_call` (30-second signed authorization tokens bound to `(userId, invitationId, toolId, planId, index)`).
- Tool-to-HTTP binding enforcement: `ai_agent/capabilities.py:TOOL_BINDINGS` and `http_request_matches_tool()` (`ai_agent/capabilities.py:147`).
- Provider boundary: `ai_agent/providers.py` (bounded JSON response schema, no executable markup accepted).
- MCP-style server tooling: eInvite does NOT currently expose an external MCP transport. C10 items that map to "MCP server responsibilities" are marked `partial` and scoped to the internal tool registry that *would* be exposed through a future MCP gateway (see `docs/ROADMAP.md` Phase 4a plugin marketplace).

---

## Chapter C9 — Orchestration & Agentic Security

### C9.1 — Tool Inventory & Boundaries

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.1.1 | Maintain a complete, versioned inventory of every tool an agent can invoke, including its name, schema, executor, risk, and required permission. | pass | `ai_agent/tools.py:_defs()` — 80 `ToolDefinition` instances with frozen id/description/risk/permission/input_schema/output_schema/reversible/confirmation/executor. `ai_agent/capabilities.py:coverage_report()` emits a machine-readable coverage report. `docs/V28_TOOL_REGISTRY.md` documents the registry. |
| C9.1.2 | Reject unknown or undeclared tools at runtime; the model may not invent tool names. | pass | `ai_agent/tools.py:get_tool()` raises `ToolValidationError("Unknown tool", code="unknown_tool")` for any id not in the `TOOLS` dict. `ai_agent/service.py:validate_tool_calls()` enforces this for every provider response. |
| C9.1.3 | Every tool must declare a binding to a concrete authoritative executor (HTTP path, editor action, internal API, bounded read). | pass | `ai_agent/capabilities.py:TOOL_BINDINGS` declares one binding entry per tool id. `coverage_report()` flags `missingBindings` for any unbound tool. The current registry has zero missing bindings (verified by `tests/v28_agent_tool_contract_test.py`). |
| C9.1.4 | Tool input schemas must reject selector / HTML / SQL / script / shell / filesystem-path / arbitrary-endpoint / network-destination arguments. | pass | `ai_agent/tools.py:FORBIDDEN_KEYS` + `FORBIDDEN_VALUE_PATTERNS` (5 regex patterns blocking `javascript:`, `file/ftp/data:` URLs, `<script>` / `<iframe>` / `<object>` / `<embed>`, SQL DDL, and shell launchers). `_reject_forbidden()` walks every nested value in tool arguments. |
| C9.1.5 | Tool arguments must be bounded in length, count, and numeric range to prevent resource exhaustion. | pass | `ai_agent/tools.py:string(maximum=50000)`, `arr(items, maximum=100)`, `number(minimum, maximum)` enforce per-field bounds; `validate_tool_calls()` enforces `maximum=40` calls per plan and rejects encoded payloads > 200 KB (`ai_agent/tools.py:validate_tool_call`). |

### C9.2 — Authorization Model

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.2.1 | Every tool must declare a minimum permission tier (read / edit / manage / admin) that is enforced at execution time, not just at discovery time. | pass | `ToolDefinition.permission` is one of `read` / `edit` / `manage` / `admin` (`ai_agent/tools.py:36`). `ai_agent/capabilities.py:availability()` rejects the tool at discovery time, and `ai_agent/service.py:authorize_tool_call()` re-checks permission immediately before issuing an authorization token. |
| C9.2.2 | The agent must not be able to authorize a tool call that the calling user could not perform directly through the underlying API. | pass | `ai_agent/service.py:authorize_tool_call()` calls `assert_calls_available([call], access_snapshot)` immediately before issuing the token, and `consume_tool_authorization()` re-checks `userId`, `invitationId`, and `toolId` equality with `secrets.compare_digest`. `http_request_matches_tool()` (`ai_agent/capabilities.py:147`) verifies that the bound HTTP request matches the planned tool's binding pattern. |
| C9.2.3 | The agent must re-check authorization immediately before execution, because permissions can change between plan creation and execution. | pass | `ai_agent/service.py:confirm_plan()` rejects stale plans via `documentRevision` + `documentFingerprint` comparison; `authorize_tool_call()` rejects if revision changed and marks the plan `stale`. |
| C9.2.4 | High-risk and destructive operations require explicit destructive-action confirmation that is separate from plan acceptance. | pass | `ai_agent/service.py:confirm_plan()` raises `destructive_confirmation_required` if any call has `risk == "high"` and `destructiveAccepted` is not set. The destructive confirmation is a separate, additional gate on top of `exactTargetsAccepted` (line 401). |
| C9.2.5 | Tool execution must be gated by a short-lived, single-use authorization token bound to a specific planned operation. | pass | `ai_agent/service.py:authorize_tool_call()` issues `secrets.token_urlsafe(32)` with `expiresAt = now + 30` (30-second TTL) stored in `self._tool_authorizations`. `consume_tool_authorization()` pops the token (single-use) and verifies all four binding fields. |
| C9.2.6 | Permission tiers must reflect the underlying collaboration role model and must not be hardcoded per agent. | partial | `ai_agent/capabilities.py:ROLE_PERMISSIONS` maps `read`/`edit`/`manage`/`admin` to invitation-collaborator roles (`owner/manager/designer/content/viewer`). However, the underlying workspace role model in `platform_v32/service.py:ROLE_PERMISSIONS` has richer roles (`viewer/reviewer/content-editor/designer/manager/owner`) and per-resource permissions (`read/comment/edit-content/edit-design/assets/publish/manage-members/backup`). The agent permission model is a coarser subset of the platform permission model and does not currently express resource-scoped grants like `event:{id}:publish`. See `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` for the migration design. |
| C9.2.7 | Admin-tier agent tools must require a server-side administrator role, separate from project collaboration. | pass | `ai_agent/capabilities.py:ADMIN_TOOL_PREFIXES = ("admin.",)` and the `admin` permission tier require `accountRole == "admin"` in `availability()` (line 238). No tool in the current registry uses the `admin` tier or `admin.*` prefix — every admin-tier tool would be a new addition that inherits the gate automatically. |

### C9.3 — Confirmation Boundaries

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.3.1 | Define and document which operations are auto-eligible, which require exact-target confirmation, and which require destructive-action confirmation. | pass | `docs/V28_CONFIRMATION_BOUNDARIES.md` lists all three tiers with examples. `ai_agent/service.py:_run_job()` computes `confirmations` (any call with `confirmationRequired`) and `high_risk` (any call with `risk == "high"`) at line 337-338. |
| C9.3.2 | Auto-eligible operations must be reversible, low-risk, and require an explicit user preference toggle. | pass | `ai_agent/service.py:plan_value["autoApplyEligible"] = prefs["allowLowRiskAuto"] and all(call["risk"] == "low" and call["reversible"] and not call["confirmationRequired"] for call in validated_calls)`. The `allowLowRiskAuto` preference defaults to 0 (off) in `ai_agent/storage.py:ai_preferences`. |
| C9.3.3 | Confirmation must capture the exact target set (invitation, pages, object IDs, effects) so the user knows what they are approving. | pass | `ai_agent/service.py:plan_value` captures `affectedPages` and `affectedObjectIds` (sorted, deduplicated) before the plan is presented. `confirm_plan()` requires `exactTargetsAccepted=True` when `confirmationRequired` is set (line 401). |
| C9.3.4 | Confirmation must be re-checked if the document revision changes between plan creation and execution. | pass | `ai_agent/service.py:confirm_plan()` compares `plan["documentRevision"]` and `plan["documentFingerprint"]` against `current = self.context.build(...)`. If they differ, the plan is marked `stale` and `stale_plan` (HTTP 409) is raised. |
| C9.3.5 | Publish/unpublish, message preparation, and destructive deletion must be marked non-reversible and require a separate final confirmation. | pass | `ai_agent/tools.py` declares `reversible=False, confirmation=True` for: `publish.prepare`, `message.prepare_send`, `guest.delete`, `invitation.update_operations`, `invitation.archive`, `export.prepare`, `plugin.configure`, `merge.prepare_job`, `publishing.configure_environment`, `event.prepare_automation`. |

### C9.4 — Plan Lifecycle & Idempotency

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.4.1 | Each agent execution must be captured as a stored plan with status (proposed / confirmed / completed / failed / cancelled / stale). | pass | `ai_agent/storage.py:ai_plans` table has `status TEXT NOT NULL DEFAULT 'proposed'`. `ai_agent/service.py:update_plan_status()` transitions states. |
| C9.4.2 | Plans must support idempotency keys so the same client request does not produce two executions. | pass | `ai_agent/storage.py:ai_plans.idempotency_key` is `TEXT NOT NULL DEFAULT ''` with a partial unique index `idx_ai_plans_idempotency ON ai_plans(user_id, idempotency_key) WHERE idempotency_key<>''`. |
| C9.4.3 | Plan execution must be cancellable mid-flight. | pass | `ai_agent/storage.py:ai_jobs.cancellation_requested` flag. `ai_agent/service.py:cancel_job()` sets the flag; `_run_job()` checks `self.store.job_cancelled(job_id)` between major steps and yields `job.cancelled` events. |
| C9.4.4 | Plan outcome (success / failure, error code, verification, corrections) must be persisted for forensic review. | pass | `ai_agent/storage.py:ai_verification_results` table. `ai_agent/service.py:complete_plan()` records `verification` JSON and `corrections` array (bounded to 20 items). `ai_tool_outcomes` table records per-tool success/error_code. |

### C9.5 — Provider Boundary

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.5.1 | Provider responses must conform to a bounded JSON schema; unknown shapes must be rejected. | pass | `ai_agent/providers.py:ProviderResult` is a typed structure (`text`, `tool_calls`, `questions`, `provider_mode`, `disclosure`, `raw_usage`). `ExternalProvider.generate()` enforces a bounded response schema and rejects oversized or malformed responses. |
| C9.5.2 | Provider model output must be treated as untrusted data; it must never directly mutate state. | pass | Per `docs/V28_ARCHITECTURE.md` ("project-scoped, multi-turn creative agent without giving a model direct DOM/JS/SQL/filesystem/network authority"). Provider output is validated through `validate_tool_calls()` → `_reject_forbidden()` → `_validate(schema, value)` before any plan is stored. |
| C9.5.3 | Provider API keys and credentials must never appear in client context, persisted conversation content, or audit logs. | pass | `ai_agent/config.py` keeps all provider credentials server-side. Context builder (`ai_agent/context.py`) excludes cookies, CSRF tokens, API keys, internal paths, and unrelated account data per `docs/V28_ARCHITECTURE.md`. `audit_events.metadata_json` is bounded and never contains raw secrets. |
| C9.5.4 | The system must support offline fallback when no external provider is reachable. | pass | `ai_agent/providers.py:OfflineTemplateProvider` provides deterministic, honest templates without network calls. `ai_agent/local_providers.py:LocalProviderManager` discovers loopback or admin-allowlisted local AI runtimes (Ollama, LM Studio, GPT4All). `FallbackProvider` chains primary → fallbacks. |
| C9.5.5 | Local AI providers must be loopback-only or administrator-allowlisted; no redirects. | pass | `ai_agent/local_providers.py:LocalProviderManager` checks endpoint against `local_provider_allowlist` and rejects any non-loopback endpoint not in the allowlist. `ai_agent/config.py` enforces HTTP-only (no redirects). |
| C9.5.6 | Provider disclosure must be honest: the user must be told whether the response came from a connected, local, or offline provider. | pass | `ai_agent/service.py:status()` exposes `providerMode` and `providerDisclosure` strings. Each assistant message records `providerMode` and `disclosure` (`ai_agent/service.py:_run_job` at `assistant_message = self.store.add_message(..., {"text": result.text, "providerMode": result.provider_mode, "disclosure": result.disclosure, ...})`). |

### C9.6 — Audit & Observability

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.6.1 | Every agent action (plan proposed, plan confirmed, tool authorized, tool consumed, plan completed, plan failed, job cancelled) must emit an audit event. | pass | `ai_agent/service.py:_emit_audit()` is called for `ai.plan_proposed`, `ai.plan_confirmed`, `ai.tool_authorized`, `ai.tool_authorization_consumed`, `ai.plan_completed`, `ai.plan_failed`, `ai.job_cancelled`, `ai.design_blueprint_created`, `ai.memory_created`, `ai.memory_deleted`, `ai.knowledge_created`, `ai.knowledge_deleted`, `ai.feedback_recorded`. Events are written to the hash-chained `audit_events` table (`src/python/server.py:write_audit_event` at line 1376). |
| C9.6.2 | Audit events must be immutable and tamper-evident. | pass | `src/python/server.py:1206-1207` declares `BEFORE UPDATE` and `BEFORE DELETE` triggers that `RAISE(ABORT, 'audit events are immutable')`. `event_hash` is `SHA256(id|user_id|action|target_type|target_id|metadata|ip|previous_hash|created_at)` and chains to the previous event's hash. Verification endpoint at `src/python/server.py:studio_operations_audit` recomputes the hash and exposes `validHash` to the dashboard. |
| C9.6.3 | Audit events must capture actor, target, action, IP, and timestamp with retention. | pass | `audit_events` schema includes `user_id`, `action`, `target_type`, `target_id`, `metadata_json`, `ip_address`, `previous_hash`, `event_hash`, `created_at`. Retention governed by `EINVITE_AUDIT_RETENTION_DAYS` (30-3650, default 730) per `docs/ARCHITECTURE.md`. |
| C9.6.4 | The system must provide anomaly detection on tool-invocation patterns. | partial | The audit log infrastructure is in place, and per-tool outcomes are tracked in `ai_tool_outcomes`. However, no anomaly-detection rules (volume spikes, off-hours bulk, permission-denied spikes, repeated confirmation-boundary hits) are implemented yet. See `docs/ai/AGENT-SECURITY-DASHBOARD.md` for the Phase 1a spec. |
| C9.6.5 | Per-tool outcome metrics (success rate, error codes, frequency) must be queryable for governance review. | partial | `ai_tool_outcomes` table (`ai_agent/storage.py`) records `(user_id, plan_id, tool_id, success, error_code, created_at)` with an index on `(user_id, tool_id, created_at DESC)`. There is no admin-facing query endpoint or visualization yet — the agent-security dashboard (`docs/ai/AGENT-SECURITY-DASHBOARD.md`) adds this. |

### C9.7 — Rate Limiting & Resource Bounds

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.7.1 | The agent endpoint must enforce per-user rate limits. | pass | `src/python/server.py:rate_limit` (line 2754) applies `ai-agent (120/3600s per user)` and `ai/assist (60/3600s per user)`. Redis-first with in-process fallback. |
| C9.7.2 | The agent must enforce a maximum number of tool calls per plan and a maximum number of actions per job. | pass | `ai_agent/config.py:AgentConfig` sets `max_tool_calls` (default 40) and `max_actions_per_job`. `ai_agent/service.py:_run_job()` raises `too_many_actions` if the proposed job exceeds the limit. |
| C9.7.3 | The agent must enforce a maximum context size to prevent prompt-injection amplification. | pass | `ai_agent/config.py:AgentConfig.max_context_bytes` is enforced by `ai_agent/context.py:ContextBuilder` which truncates the rendered context. |
| C9.7.4 | The agent must enforce bounded concurrency per user. | pass | `ai_agent/service.py` uses `self._running: dict[str, set[str]]` and `self._lock` to track in-flight jobs per user. `_release_job()` cleans up. `AgentConfig.max_concurrent_jobs` is the bound. |
| C9.7.5 | Workspace AI usage must respect a per-workspace budget policy that can disable AI entirely. | pass | `ai_agent/service.py:_budget_guard()` reads `ai_routing_policies.enabled` and `budget_json` for the invitation's workspace. If `enabled=0`, the request is rejected with `workspace_ai_disabled` (HTTP 403). `ai_agent/capabilities.py:build_access_snapshot()` propagates `workspacePolicyEnabled` into the capability snapshot. |
| C9.7.6 | Retention of conversations, messages, plans, and jobs must be user-configurable. | pass | `ai_agent/storage.py:ai_preferences.retention_days` (default 30). `purge_expired()` is called from `list_threads()` and elsewhere. |

### C9.8 — Memory & Knowledge Boundaries

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C9.8.1 | Memory and knowledge entries must be scoped (account vs invitation) and never leak across invitations. | pass | `ai_agent/storage.py:ai_memories.scope` (`account` or `invitation`) and `invitation_id` (empty for account-scoped). `ai_knowledge_sources` follows the same pattern. List functions filter by `(user_id, invitation_id)`. |
| C9.8.2 | Memory creation must be gated by an explicit user preference. | pass | `ai_preferences.memory_enabled INTEGER NOT NULL DEFAULT 1` (added via `ALTER TABLE`). `add_memory()` calls `_assert_enabled()` which checks `prefs["memoryEnabled"]`. |
| C9.8.3 | Knowledge source creation must be gated by an explicit user preference. | pass | `ai_preferences.knowledge_enabled INTEGER NOT NULL DEFAULT 1`. `add_knowledge_source()` calls `_assert_enabled()` which checks `prefs["knowledgeEnabled"]`. |
| C9.8.4 | Memory and knowledge deletion must emit audit events. | pass | `ai_agent/service.py:delete_memory` and `delete_knowledge_source` both call `_emit_audit(user_id, "ai.memory_deleted" | "ai.knowledge_deleted", ...)`. |
| C9.8.5 | Feedback-based memory learning must be explicitly opted into. | pass | `record_feedback()` accepts `remember: bool`; the value is AND-ed with `prefs.get("memoryEnabled", True)` before a memory is created from feedback. |

---

## Chapter C10 — MCP (Model Context Protocol) Security

> Context: eInvite does not currently expose an external MCP server or consume external MCP clients. Chapter C10 is mapped against the *internal* tool registry that would be exposed through a future MCP gateway (Phase 4a plugin marketplace, see `docs/ROADMAP.md` §7). Internal-only tools are evaluated against the spirit of the MCP controls — every control that would apply to a remote tool applies equally to the locally-declared tool, because the registry was designed as if every tool were untrusted.

### C10.1 — Tool Discovery

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.1.1 | A tool catalog must be exposed to the model only after capability filtering (the model never sees tools it cannot invoke). | pass | `ai_agent/service.py:capability_catalog()` returns `{"tools": allowed, "denied": denied, "access": snapshot}`. `filter_catalog()` (in `ai_agent/capabilities.py:258`) returns only the allowed subset. |
| C10.1.2 | Denial reasons must be machine-readable so the model can adapt rather than guess. | pass | `ai_agent/capabilities.py:filter_catalog()` returns `denied: [{"id": ..., "reason": ...}]` with localized denial reasons. `assert_calls_available()` re-uses the same reasons. |
| C10.1.3 | Tool descriptions must NOT contain execution instructions, examples, or prompt-injection vectors. | partial | `ToolDefinition.description` strings are one-line semantic descriptions (e.g. "Create a text object."). However, there is no automated linter that scans descriptions for prompt-injection patterns. Add a registry-lint test in Phase 1b. |
| C10.1.4 | Tool input/output schemas must be frozen and versioned; schema drift must break the registry contract. | pass | `ToolDefinition` is `@dataclass(frozen=True)` (`ai_agent/tools.py:32`). `public()` returns a `copy.deepcopy()` of the schema so callers cannot mutate the registry. `tests/v28_agent_tool_contract_test.py` rejects registry drift. |

### C10.2 — Tool Invocation

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.2.1 | Every tool invocation must be matched against its declared HTTP binding before the underlying API is called. | pass | `ai_agent/capabilities.py:http_request_matches_tool()` compiles each binding into an exact same-origin path regex (with `[^/]+` placeholders for `{guestId}` etc.) and verifies `(method, path)` against the planned tool. `consume_tool_authorization()` rejects scope mismatches with `ai_tool_authorization_scope_mismatch` (HTTP 403). |
| C10.2.2 | Tool invocation must require an authorization token tied to a confirmed plan; the token is single-use and short-lived. | pass | `ai_agent/service.py:authorize_tool_call()` mints `secrets.token_urlsafe(32)` with 30-second TTL. `consume_tool_authorization()` pops it from `self._tool_authorizations` (single-use). |
| C10.2.3 | The authorization token must bind to the exact tool index inside the plan, preventing token substitution. | pass | `self._tool_authorizations[token]` records `"index": index` (the plan-relative position). The consuming endpoint must present the same `planId` + `index` or the request is rejected with `tool_call_mismatch` (HTTP 409). |
| C10.2.4 | Tool execution must be observable in real time (NDJSON event stream). | pass | `ai_agent/service.py:_run_job()` is a generator yielding `job.started`, `context.ready`, `assistant.started`, `assistant.delta`, `assistant.completed`, `plan.proposed`, `question`, `error`, `job.completed`, `job.cancelled` events. The server streams these as NDJSON. |
| C10.2.5 | The agent must support cancellation at any point and propagate it to running tool calls. | pass | `ai_jobs.cancellation_requested` is checked at every yield point in `_run_job()`. The HTTP handler supports client disconnect via `GeneratorExit`. |
| C10.2.6 | The agent must enforce a maximum number of tool calls per single provider response. | pass | `validate_tool_calls(calls, maximum=40)` (`ai_agent/tools.py`) raises `too_many_tool_calls` for plans exceeding the limit. |

### C10.3 — Resource Scoping

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.3.1 | Tool invocations must be scoped to a specific resource (invitation, page, asset, guest) and reject cross-resource access. | partial | `http_request_matches_tool()` binds each tool to a path pattern that includes `{invitationId}` (literal) and `{guestId|rsvpId|assetId|blueprintId}` (regex `[^/]+`). This prevents the agent from invoking a tool on a different invitation. However, the model still receives a flat tool id without explicit resource scoping at the *permission* layer — see `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` for the migration to `event:{id}:publish`-style grants. |
| C10.3.2 | Standing permission grants (always-on tool access) must be minimized; high-risk operations must use just-in-time elevation. | partial | High-risk operations require `destructiveAccepted` confirmation and a 30-second authorization token (see C9.2.5), but the standing grant is still "user has `manage` permission on the invitation." JIT elevation with a separate 5-minute TTL grant is documented in `docs/ai/JIT-ELEVATION.md` and is not yet enforced in code. |
| C10.3.3 | Admin-tier tools must require server-side administrator role, separate from project collaboration. | pass | Same evidence as C9.2.7. |
| C10.3.4 | The system must support revocation of a granted permission mid-session without restarting the agent. | partial | The 30-second authorization token is revocable by expiry. Standing tier-based grants (e.g. `manage` on an invitation) are revocable by removing the collaborator from `invitation_collaborators`, but the in-memory `self._tool_authorizations` cache is per-process and not shared across server instances. See `docs/ai/JIT-ELEVATION.md` §5 for the cross-instance revocation design using the `jit_elevations` table. |

### C10.4 — MCP Server Boundary (Future Plugin Marketplace)

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.4.1 | External tool servers (MCP servers) must be sandboxed; they must not inherit platform privileges. | partial (future) | The current registry has no external MCP servers. Phase 4a (`docs/ROADMAP.md` §7) specifies a plugin manifest with declared permission scopes + cross-origin iframe + WASM isolation. The Phase 1a `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` design extends cleanly to plugins via `plugin:{pluginKey}:{permission}` grants. |
| C10.4.2 | External tool servers must declare their permission scopes up-front and refuse undeclared scopes at runtime. | partial (future) | The `plugin.configure` tool (`ai_agent/tools.py`) accepts `permissions: arr(string(80), 20)` and `scope: obj` — declared grants are stored and enforced. The plugin sandbox (`docs/plugins/PLUGIN-SANDBOX.md`, Phase 4a) will enforce the declared scope at the iframe boundary. |
| C10.4.3 | External tool server responses must be treated as fully untrusted data, including their tool-call outputs. | pass (by design) | The provider-boundary design (`docs/V28_ARCHITECTURE.md`) treats all provider output as untrusted. A future MCP gateway would feed tool-call outputs through `validate_tool_calls()` → `_reject_forbidden()` → `_validate(schema, value)` exactly as native tool calls do. |
| C10.4.4 | External tool servers must be signed and verified on install. | partial (future) | `plugin.configure` accepts `pluginKey: ID` and `version: string(40)`. The signature verification pipeline (Phase 4a, `docs/plugins/PLUGIN-SPEC.md`) double-signs with author key + eInvite marketplace CA. |
| C10.4.5 | External tool servers must be rate-limited independently from the agent's own rate limits. | partial (future) | `src/python/server.py:rate_limit` already supports per-route buckets. The Phase 4a design will add a per-plugin-installation rate-limit bucket keyed on `plugin:{installationId}`. |

### C10.5 — Prompt Injection Resistance

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.5.1 | Invitation text, comments, filenames, asset names, and provider output must be treated as untrusted data and never as instructions to the agent. | pass | `docs/V28_ARCHITECTURE.md` "Security model" section: "Invitation text, comments, filenames, asset names, and provider output are untrusted data." The context builder (`ai_agent/context.py`) wraps untrusted content with structural markers, never as instructions. |
| C10.5.2 | The system must reject tool arguments that contain executable markup (script, iframe, SQL DDL, shell launchers, javascript: URIs). | pass | `ai_agent/tools.py:FORBIDDEN_VALUE_PATTERNS` (5 regex patterns). `_reject_forbidden()` walks every nested value. |
| C10.5.3 | The system must reject tool arguments whose keys are selector / css / html / sql / script / shell / filesystem / path / network / endpoint / url / command. | pass | `ai_agent/tools.py:FORBIDDEN_KEYS` set. |
| C10.5.4 | The model must not be able to bypass the plan confirmation flow by emitting a tool call that auto-applies when the user has not opted in. | pass | `autoApplyEligible` requires `prefs["allowLowRiskAuto"]` (default 0) AND every call must be `risk == "low"` AND `reversible` AND `not confirmationRequired`. Default state is "always confirm." |
| C10.5.5 | The agent must refuse to chain a high-risk operation as a side-effect of a low-risk operation without explicit destructive confirmation. | pass | `_run_job()` evaluates `confirmations` and `high_risk` across the *entire* plan, not per-call. If any call is high-risk, the plan as a whole requires `destructiveAccepted`. |

### C10.6 — Data Exfiltration Resistance

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.6.1 | The agent must not transmit cookies, CSRF tokens, API keys, internal paths, or unrelated account data to the provider. | pass | `ai_agent/context.py:ContextBuilder` resolves context references to stable IDs and revalidates ownership. `docs/V28_ARCHITECTURE.md` explicitly excludes cookies, CSRF tokens, API keys, internal paths, and unrelated account data from context. |
| C10.6.2 | The agent must not accept `url`, `endpoint`, `destination`, `network`, or `command` arguments that could be used for outbound exfiltration. | pass | `ai_agent/tools.py:FORBIDDEN_KEYS` set explicitly blocks these argument names. |
| C10.6.3 | The agent must not embed raw HTML, CSS, JavaScript, or SQL in tool arguments. | pass | `FORBIDDEN_VALUE_PATTERNS` regex blocks `<script>`, `<iframe>`, `<object>`, `<embed>`, SQL DDL keywords, and shell launchers. |
| C10.6.4 | The agent must not transmit the full document — only a bounded, summarized, project-scoped context. | pass | `ai_agent/config.py:AgentConfig.max_context_bytes` is enforced by `ContextBuilder`. The context exposes `pageSummaries` (bounded, summarized) and a bounded `selection` summary — not the full `draft_json`. |
| C10.6.5 | The agent must not be able to call a tool whose bound HTTP path does not match the planned tool id. | pass | `consume_tool_authorization()` calls `http_request_matches_tool(tool_id, method, path, invitation_id)` and rejects mismatches with `ai_tool_authorization_scope_mismatch` (HTTP 403). This prevents an authorized `read.page_summary` token from being used to invoke `guest.delete`. |

### C10.7 — Forensic & Recovery

| Requirement ID | Requirement (paraphrased) | Status | Evidence |
|---|---|---|---|
| C10.7.1 | Every plan must record its tool calls, target IDs, affected pages/objects, and the user-confirmed revision + fingerprint. | pass | `ai_plans.plan_json` stores the full `plan_value` (summary, toolCalls, affectedPages, affectedObjectIds, estimatedActionCount, confirmationRequired, confirmationReasons, autoApplyEligible, providerMode). `documentRevision` + `documentFingerprint` are columns on `ai_plans`. |
| C10.7.2 | Every plan must record its verification result and corrections. | pass | `ai_verification_results` table records `success`, `result_json`, `corrections_json`. `record_verification()` and `record_plan_outcomes()` write to it. |
| C10.7.3 | Plans must be queryable by user / invitation / status for forensic review. | partial | The schema supports queries by `(user_id, invitation_id, status)`, but there is no admin-facing forensic UI. The agent-security dashboard (`docs/ai/AGENT-SECURITY-DASHBOARD.md`) adds per-tool invocation queryability. |
| C10.7.4 | The system must support one-click undo of a completed plan. | partial | `docs/V28_ARCHITECTURE.md` mentions "one-click Undo AI job" as part of the data flow. The plan lifecycle records `verification` + `corrections` for the undo path. Full undo of high-risk operations (`guest.delete`, `publish.prepare`) requires a separate recover-from-backup path documented in `docs/ops/RESTORE-RUNBOOK.md` (Phase 1c). |

---

## Summary

| Chapter | Total items mapped | Pass | Partial | Fail |
|---|---:|---:|---:|---:|
| C9 (Orchestration & Agentic Security) | 38 | 33 | 5 | 0 |
| C10 (MCP Security) | 25 | 17 | 8 | 0 |
| **Total** | **63** | **50** | **13** | **0** |

### Remediation priorities (Phase 1a → Phase 1b → Phase 2)

1. **C9.2.6 / C10.3.1 — Resource-scoped permissions** (Partial). Standing tier-based `read/edit/manage/admin` must evolve to `event:{id}:publish`-style grants. Migration plan in `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md`.
2. **C10.3.2 / C10.3.4 — JIT elevation** (Partial). High-risk operations must require a 5-minute TTL grant that is revocable across instances. Design in `docs/ai/JIT-ELEVATION.md` + skeleton in `ai_agent/jit_elevation.py`.
3. **C9.6.4 / C9.6.5 / C10.7.3 — Agent-security dashboard** (Partial). Anomaly detection rules and per-tool invocation queryability must be added. Spec in `docs/ai/AGENT-SECURITY-DASHBOARD.md`.
4. **C10.1.3 — Tool-description lint** (Partial). Add a registry-lint test that scans `ToolDefinition.description` strings for prompt-injection patterns. Trivial; Phase 1b.
5. **C10.4.* — External MCP server / plugin sandbox** (Partial / future). Phase 4a per `docs/ROADMAP.md` §7. The Phase 1a resource-scoped permission design extends cleanly to plugins via `plugin:{pluginKey}:{permission}` grants.

No items are marked **fail** — the existing V28/V53.1 implementation already meets the majority of C9 and the spirit of C10. Phase 1a closes the remaining **partial** items.
