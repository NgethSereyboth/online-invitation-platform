# Attack Story Template — Per-Tool Threat Model

> Use this template for every AI tool that the V28/V53.1 agent can invoke.
> Scope: One file per tool, named after the tool id (e.g. `publish.prepare.md`).
> The 80 registered tools are listed in `ai_agent/tools.py:_defs()`. See `README.md` for the index.

## Tool: `<tool_id>`

| Field | Value |
|---|---|
| **Tool ID** | `<tool_id>` (as registered in `ai_agent/tools.py:TOOLS`) |
| **Group** | `<group>` (the prefix before the dot, e.g. `publish`, `guest`, `merge`) |
| **Risk tier** | `low` \| `medium` \| `high` (per `ToolDefinition.risk`) |
| **Permission tier** | `read` \| `edit` \| `manage` \| `admin` (per `ToolDefinition.permission`) |
| **Executor** | `server` \| `client` \| `editor-action` \| `platform-api` \| `internal-api` \| `ui-command` \| `bounded-read` \| `diagnostic` \| `governed-workflow` \| `existing-workflow` \| `editor-transaction` \| `editor-command` \| `upload-workflow` \| `review-workflow` (per `ai_agent/capabilities.py:TOOL_BINDINGS[id].type`) |
| **Binding** | `<the declared HTTP path or editor action>` |
| **Reversible** | `True` \| `False` (per `ToolDefinition.reversible`) |
| **Confirmation required** | `True` \| `False` (per `ToolDefinition.confirmation`) |
| **Source file** | `ai_agent/tools.py:<line of the ToolDefinition>` |
| **Binding file** | `ai_agent/capabilities.py:<line of the TOOL_BINDINGS entry>` |

### 1. What it touches

- **Data**: which tables / columns / documents / assets the tool reads or writes (cite `ai_agent/storage.py` schema or `src/python/server.py` schema).
- **Services**: which HTTP routes / editor functions / external systems the tool invokes (cite `ai_agent/capabilities.py:TOOL_BINDINGS`).
- **Files**: which user-uploaded or generated files the tool creates, reads, or deletes (cite `platform_v32/storage.py` for object storage paths).
- **Side effects**: which other systems the tool triggers (e.g. email dispatch, billing webhook, scheduled job). If none, state "no external side effects."

### 2. Worst case if malicious

A concrete, scoped scenario. NOT a vague "the model could do bad things." Write the scenario as:

> If a prompt-injected or compromised agent successfully invoked `<tool_id>` with attacker-chosen arguments on resource `<resource_id>`, the attacker could `<specific harm>`. The blast radius is bounded to `<scope: this invitation / this workspace / cross-workspace / account-wide / system-wide>`. The data affected is `<PII / financial / authentication / publication / collaboration>`.

Concrete examples of worst-case categories:

- **PII disclosure**: exfiltration of guest names, emails, phone numbers, RSVPs, household composition.
- **Publication tampering**: publishing an invitation that was meant to stay draft; changing the public URL or custom domain; scheduling an early publish.
- **Destructive deletion**: deleting guests, pages, assets, or invitations in a way that bypasses recovery.
- **Supply-chain attack**: installing a malicious plugin or marketplace template that escalates to platform-wide code execution.
- **Billing fraud**: triggering a billing webhook or upgrade without authorization.
- **External-message dispatch**: sending emails / SMS / WhatsApp / Telegram to guests on behalf of the host with attacker-controlled content.
- **Bulk abuse**: running a 5000-row data merge that drains workspace budget or floods downstream services.

### 3. Containment

What prevents the worst case TODAY. Cite the specific gate:

- **Schema validation**: `ai_agent/tools.py:_validate()` rejects out-of-range / forbidden-pattern arguments.
- **Permission tier**: `ai_agent/capabilities.py:availability()` rejects if the user lacks the required collaboration role.
- **Confirmation boundary**: `ai_agent/service.py:confirm_plan()` requires `exactTargetsAccepted` (medium-risk) or `destructiveAccepted` (high-risk).
- **Authorization token**: `ai_agent/service.py:authorize_tool_call()` issues a 30-second single-use token bound to `(userId, invitationId, toolId, planId, index)`.
- **HTTP-binding match**: `ai_agent/capabilities.py:http_request_matches_tool()` verifies the bound HTTP request matches the planned tool.
- **Revision + fingerprint check**: `ai_agent/service.py:authorize_tool_call()` rejects stale plans when the document revision changes.
- **Workspace AI policy**: `ai_agent/service.py:_budget_guard()` rejects when the workspace policy is disabled.
- **Rate limit**: `src/python/server.py:rate_limit` (line 2754) bounds per-user request volume.
- **Audit immutability**: `src/python/server.py:1206` BEFORE UPDATE/DELETE triggers on `audit_events`.
- **Malware scanning**: `src/python/security_scanner_v54.py` scans uploaded content (for tools that touch uploaded materials).

### 4. Reversible

- **Yes / No**: per `ToolDefinition.reversible`.
- **How**: if yes, the specific undo path. If no, the recovery path (e.g. "restore from backup per `docs/ops/RESTORE-RUNBOOK.md`").
- **Time to undo**: estimated wall-clock time if applicable.
- **Side effects of undo**: any data lost during the undo window.

### 5. Mitigation (Phase 1a + future)

What Phase 1a adds or strengthens. Cite the design doc:

- **Resource-scoped permission**: replace the standing `manage` tier with `event:{id}:publish` (see `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md`).
- **JIT elevation**: require a 5-minute TTL grant for high-risk operations (see `docs/ai/JIT-ELEVATION.md`).
- **Anomaly detection**: dashboard detects unusual invocation patterns for this tool (see `docs/ai/AGENT-SECURITY-DASHBOARD.md`).
- **Audit alert**: emit `jit.requested` / `jit.granted` / `jit.denied` / `jit.expired` / `jit.revoked` events for high-risk operations.
- **Plugin marketplace gating** (future, Phase 4a): if this tool is exposed via MCP, the plugin sandbox must declare and enforce the permission scope.

### 6. Test coverage

Cite the test file(s) that exercise this tool's permission / validation / confirmation / authorization boundary:

- `tests/v28_agent_tool_contract_test.py` — registry contract (all 80 tools).
- `tests/v28_agent_storage_test.py` — plan lifecycle.
- `tests/v28_agent_server_contract_test.py` — server-side plan + authorize + consume flow.
- `tests/v28_agent_provider_test.py` — provider boundary.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.
- `tests/v28_agent_performance_contract_test.py` — bounded context, max tool calls.
- `tests/v28_agent_registry_browser_test.py` — capability filtering.
- `tests/v28_agent_mobile_browser_test.py` — confirmation boundary on mobile.
- `tests/v53_1_ai_project_operator_backend_test.py` — V53.1 operator repair flow.
- `tests/v53_1_ai_project_operator_contract_test.py` — V53.1 operator contract.
- `tests/v53_1_operator_repair_contract_test.py` — V53.1 operator repair contract.

If no test exercises this specific tool's high-risk path, note it as a gap.

### 7. AISVS cross-reference

Which AISVS C9 / C10 requirements this tool's threat model maps to. Cite the row in `docs/ai/AISVS-C9-C10-MAPPING.md`. Example: `C9.2.4` (destructive confirmation), `C9.3.5` (non-reversible + confirmation), `C10.2.1` (HTTP binding match), `C10.3.2` (JIT elevation).
