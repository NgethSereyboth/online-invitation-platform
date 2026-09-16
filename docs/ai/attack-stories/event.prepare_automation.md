# Attack Story: `event.prepare_automation`

| Field | Value |
|---|---|
| **Tool ID** | `event.prepare_automation` |
| **Group** | `event` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/events/automations` (platform-api) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `event.run_intelligence`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["event.prepare_automation"]` |
| **Feature gate** | `events` (`ai_agent/capabilities.py:FEATURE_TOOL_PREFIXES["events"] = ("event.",)`) — only available when the `event_tasks_v52` table exists. |

### 1. What it touches

- **Data**: `event_automations` (write — automation definition: name, trigger, conditions, actions), `event_automation_runs` (write — one row per execution), `event_tasks_v52` (write — automations create and update tasks), `event_incidents` (write — automation failures create incidents).
- **Services**: `POST /api/platform/v52/events/automations` registers the automation. A `event-automation-v52` background job (`future_platform_v52/service.py` registers the handler) executes the automation when the trigger fires.
- **Files**: automations may reference asset URLs (e.g. a notification template that includes an image).
- **Side effects**: depending on the `triggerType` and `actions`, the automation can: send external messages (email / SMS / WhatsApp / Telegram), create / update / delete event tasks, schedule follow-up automations, invoke external webhooks (Phase 4a), or trigger data-merge jobs. The action set is open-ended (the `actions` array accepts free-form objects — Phase 1b should add a schema).

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `event.prepare_automation` with attacker-controlled `triggerType`, `trigger`, `conditions`, and `actions`, the attacker could:

- **Create a triggerless automation** that fires immediately and on every event tick, sending 1000 SMS messages to a paid SMS gateway within minutes — exhausting the host's billing balance and the SMS provider's daily quota.
- **Create an automation that fires on `guest.rsvp_received`** and forwards the guest's PII (name, email, phone, RSVP response) to an attacker-controlled webhook URL embedded in the `actions` array.
- **Create a chain reaction**: automation A triggers automation B, which triggers automation C, which triggers automation A — an infinite loop that consumes CPU, database writes, and message-dispatch quota until the platform crashes.
- **Schedule an automation that fires at the event start time** and deletes all event tasks, replacing the host's prepared agenda with attacker-controlled content.
- **Embed an SSRF payload** in the `actions[].url` field: the platform fetches the URL as part of the action, allowing the attacker to scan the internal network (e.g. `http://169.254.169.254/latest/meta-data/` for cloud metadata, or `http://localhost:4175/api/account/audit` for the platform's own audit log).

Blast radius: **workspace-wide for automation state**, **potentially cross-workspace if the automation triggers a data-merge or marketplace operation**, **external-network for SSRF**. Data affected: **PII exfiltration + billing abuse + task destruction + SSRF + chain-reaction DoS**.

### 3. Containment

- **Schema validation**: `name` is `string(160)`. `triggerType` is `string(80)`. `trigger` is a free-form object (Phase 1b should constrain). `conditions` is a bounded array (max 100 entries). `actions` is a bounded array (max 40 entries). `FORBIDDEN_KEYS` blocks `url`, `endpoint`, `destination`, `network`, `command` argument keys **at the top level of each action** — but the action objects are nested and `FORBIDDEN_KEYS` walks the entire nested structure, so nested `url` keys are also rejected.
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=False, confirmation=True, risk="high"` → `destructiveAccepted=True` required.
- **Feature gate**: requires the `event_tasks_v52` table.
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/platform/v52/events/automations`.
- **Background job**: `event-automation-v52` runs in the bounded job queue with retry limits, idempotency keys, and cancellation.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"name": ..., "triggerType": ..., "actionCount": len(actions)}`.

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: the host can disable the automation via `PUT /api/platform/v52/events/automations/{id}` (set `enabled=false`). This stops future executions but does not undo any actions already performed (messages already sent, tasks already deleted, webhooks already invoked).
- **Time to undo**: seconds to disable; permanent for already-dispatched actions.
- **Side effects of undo**: if the automation triggered a chain reaction, the chain must be broken by disabling every automation in the cycle.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `workspace:{id}:event-automation:create`, `workspace:{id}:event-automation:enable`, `workspace:{id}:event-automation:disable`, `workspace:{id}:event-automation:delete`. The `enable` action deserves its own scope because it activates the trigger.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Out-of-band confirmation** for any automation whose `actions` array contains an external-message dispatch (`channel != "internal"`).
- **Action schema** (Phase 1b): constrain the `actions` array to a discriminated union: `{type: "send_message" | "create_task" | "update_task" | "delete_task" | "trigger_merge" | "invoke_webhook", ...}`. Forbid `invoke_webhook` unless the workspace has the `webhook-out` feature flag.
- **Chain-reaction guard**: track the depth of automation-triggered automations. If depth > 3, refuse the execution and emit an `event_automation_chain_too_deep` audit event. If the same automation fires more than 10 times in 60 seconds, auto-disable it and emit an alert.
- **SSRF guard**: any URL referenced in `actions` must be HTTPS, must not resolve to a private IP range (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, ::1), and must not be on the host allowlist (`EINVITE_ALLOWED_HOSTS`). Use a private-IP-aware HTTP client.
- **Webhook allowlist** (Phase 4a): if `invoke_webhook` is enabled, the destination URL must be pre-registered in a `webhook_allowlist` table; ad-hoc URLs are refused.
- **Anomaly detection**: dashboard detects when an automation fires more than 10 times in 60 seconds, when an automation chain exceeds depth 3, or when an automation triggers an external message dispatch.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the chain-reaction, SSRF, or bulk-message-dispatch attacks. Add tests in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.5` — non-reversible + confirmation.
- `C9.6.4` — anomaly detection on automation firing patterns.
- `C9.7.5` — workspace budget policy (automation executions consume budget).
- `C10.2.1` — HTTP binding match.
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.6.2` — no `url` / `endpoint` / `destination` keys in `actions` (top-level + nested).
- `C10.6.4` — bounded context (automation definitions are bounded in size).
