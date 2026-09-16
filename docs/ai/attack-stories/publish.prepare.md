# Attack Story: `publish.prepare`

| Field | Value |
|---|---|
| **Tool ID** | `publish.prepare` |
| **Group** | `publish` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `server` |
| **Binding** | `existing publish/unpublish command after governed confirmation` (ui-command) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, registered after `export.prepare`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["publish.prepare"]` |

### 1. What it touches

- **Data**: `invitations.is_published`, `invitations.published_at`, `invitations.publication_fingerprint`, and the `publications` table (`docs/postgres_schema.sql`). A publish action also materializes a snapshot of `draft_json` into a public, immutable `publication` row.
- **Services**: the publish command writes through `src/python/server.py` publication endpoints; if a custom domain is configured, the publication is exposed at `https://{custom_domain}/i/{slug}` (see `invitation.update_operations` attack story for the custom-domain surface).
- **Files**: publication snapshots reference stored asset versions (`platform_v32/storage.py::ObjectStorage`), so a publish makes the asset versions publicly readable through signed URLs.
- **Side effects**: guest-facing public page becomes reachable. Email / SMS notifications may be triggered downstream if the invitation has a scheduled send. SEO crawlers can index the publication if `accessMode = public`.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `publish.prepare` with `action="publish"` on an invitation `inv_X`, the attacker could **publish an unfinished, misconfigured, or attacker-modified invitation** to the public internet, including:

- A draft containing placeholder content, broken layout, or sensitive internal notes the host had not removed.
- A publication with a misleading RSVP URL that captures guest PII (name, email, phone, household composition, RSVP responses).
- A publication at a custom domain that overrides the host's previously published invitation (combined with `invitation.update_operations`).
- A pre-scheduled early publish that goes live before the host has reviewed the final design.

Blast radius: **cross-workspace if a custom domain is configured** (an attacker who controls the publication can serve content on the host's verified domain), **invitation-scoped otherwise**. Data affected: **publication + PII disclosure + brand integrity**.

### 3. Containment

- **Schema validation**: `ai_agent/tools.py` constrains `action` to the enum `["publish", "unpublish"]`. No free-form arguments.
- **Permission tier**: `manage` is required, restricted to `owner` and `manager` collaboration roles per `ai_agent/capabilities.py:ROLE_PERMISSIONS["manage"]`.
- **Confirmation boundary**: `publish.prepare` declares `reversible=False, confirmation=True`. `ai_agent/service.py:confirm_plan()` requires `destructiveAccepted=True` (line 403) because `risk == "high"`.
- **Authorization token**: `authorize_tool_call()` issues a 30-second single-use token. `consume_tool_authorization()` re-checks `userId`, `invitationId`, `toolId`, and `http_request_matches_tool`.
- **Revision + fingerprint check**: the plan is marked `stale` and rejected if the document revision changes between plan creation and execution.
- **Audit event**: `ai.plan_confirmed` and `ai.tool_authorized` are emitted to the hash-chained, immutable `audit_events` table.
- **Rate limit**: `ai-agent (120/3600s per user)` per `src/python/server.py:rate_limit`.

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: the host (or a compromised host) can call `publish.prepare` again with `action="unpublish"` to take the publication offline. However, once indexed by search engines or shared via social media, the URL may continue to be discovered. Guest PII already collected through the public RSVP form remains in the `rsvps` table and must be purged via a `privacy_requests` workflow (`platform_v32/schema.py:privacy_requests` table).
- **Time to undo**: seconds for the unpublish action; weeks for search-engine de-indexing.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: replace the standing `manage` tier with `invitation:{id}:publish` and `invitation:{id}:unpublish` grants. See `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` §3.
- **JIT elevation**: require a 5-minute TTL grant for `publish.prepare`. The grant is logged with actor, tool, resource, granted_at, expires_at, reason. See `docs/ai/JIT-ELEVATION.md`.
- **Anomaly detection**: dashboard detects when a publish operation occurs off-hours (e.g. 02:00 host-local time) or by an account that has not published in the last 30 days. See `docs/ai/AGENT-SECURITY-DASHBOARD.md`.
- **Pre-publish fingerprint diff**: surface the diff between the current draft and the last-published snapshot in the confirmation dialog so the user can see exactly what changed. (Already partially implemented via `documentFingerprint` in the plan; expose the diff in the UI.)

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_storage_test.py` — plan lifecycle states.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.
- `tests/v53_1_ai_project_operator_contract_test.py` — V53.1 operator contract.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.5` — non-reversible + confirmation.
- `C10.2.1` — HTTP binding match.
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.7.4` — one-click undo (partial — unpublish exists but is not a full undo).
