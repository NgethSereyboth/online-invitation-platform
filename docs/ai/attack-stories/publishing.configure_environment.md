# Attack Story: `publishing.configure_environment`

| Field | Value |
|---|---|
| **Tool ID** | `publishing.configure_environment` |
| **Group** | `publishing` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/publishing/environments` (platform-api) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `animation.update_timeline`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["publishing.configure_environment"]` |
| **Feature gate** | `publishingDomains` (`ai_agent/capabilities.py:FEATURE_TOOL_PREFIXES["publishingDomains"] = ("publishing.",)`) — only available when the `custom_domains_v45` table exists. |

### 1. What it touches

- **Data**: `custom_domains_v45` (write — domain verification, TLS cert reference), `publications` (write — per-environment publication snapshot), `invitation_publishing_environments` (write — environment metadata, access policy, schedule).
- **Services**: `POST /api/platform/v52/publishing/environments` registers the environment. If `environmentType="production"`, the environment can serve traffic at a custom domain. Background jobs handle TLS certificate issuance (Let's Encrypt integration in Phase 4a), DNS verification, and scheduled promotion.
- **Files**: per-environment publication snapshots are stored as JSON blobs in `publications.document_json`. TLS certificates (when issued) are stored in the workspace's secret store (encrypted at rest).
- **Side effects**: a `production` environment is publicly reachable. A `staging` environment may be reachable by workspace members. An `archive` environment is read-only and removes the publication from active serving.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `publishing.configure_environment` with `environmentType="production"` on a `preview` snapshot the host had not approved, the attacker could:

- **Promote an unreviewed draft to production** at a custom domain, serving attacker-modified content to guests.
- **Demote a live production environment to `archive`**, taking the invitation offline during the event.
- **Configure an `access` policy** that exposes the production environment without authentication, where the host had intended password protection.
- **Schedule a destructive promotion** at a future timestamp that the host cannot easily detect (e.g. promote at 02:00 the night before the event, then archive at 09:00 — a 7-hour window of attacker-controlled content).
- **TLS certificate mis-issuance** (Phase 4a concern): if the platform issues Let's Encrypt certificates on environment creation, an attacker who repeatedly creates and destroys environments can exhaust the Let's Encrypt rate limit (50 certificates per registered domain per week) for the host's apex domain, denying TLS service to the host's other invitations.

Blast radius: **workspace-wide for environment state**, **invitation-scoped for the published content**, **potentially platform-wide for TLS rate-limit abuse**. Data affected: **publication integrity + guest PII + TLS posture**.

### 3. Containment

- **Schema validation**: `name` is `string(80)`. `environmentType` is constrained to the enum `["preview", "staging", "production", "archive"]`. `schedule` and `access` are free-form objects (Phase 1b should add schemas).
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=False, confirmation=True, risk="high"` → `destructiveAccepted=True` required.
- **Feature gate**: requires the `custom_domains_v45` table.
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/platform/v52/publishing/environments`.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"name": ..., "environmentType": ..., "schedule": ..., "access": ...}`.
- **Publication readiness validator** (`platform_v32/service.py::publication_readiness` at line 66): walks every asset reference in the document and rejects publication if any reference is broken. This gate runs at promotion time, not just at environment-creation time.

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: the host can configure a new environment with `environmentType="archive"` to take the production environment offline, but the existing production snapshot remains in the publications table (immutable). Guests who already accessed the production URL have already seen the attacker's content.
- **Time to undo**: seconds for the field update; up to 5 minutes for TLS / DNS to propagate the change.
- **Side effects of undo**: any guest PII captured through the production RSVP form during the attacker's window remains in the `rsvps` table.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `workspace:{id}:publishing:environment:create`, `workspace:{id}:publishing:environment:promote`, `workspace:{id}:publishing:environment:archive`. The `promote` action (preview → production) deserves its own scope and its own JIT grant.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Two-person rule** for `environmentType="production"`: the promotion requires confirmation from a second workspace `owner` or `manager`. (This is the AISVS-aligned control for high-blast-radius operations on shared infrastructure.)
- **Diff-aware confirmation**: the confirmation dialog must show a diff between the current production snapshot and the proposed snapshot (EN: "Production change: 3 pages modified, 2 assets added, 1 asset removed." / KH: "ការផ្លាស់ប្ដូរផលិតកម្ម: ទំព័រ 3 ត្រូវបានកែប្រែ, ទ្រព្យសម្បត្តិ 2 ត្រូវបានបន្ថែម, ទ្រព្យសម្បត្តិ 1 ត្រូវបានយកចេញ.").
- **Schedule window restrictions**: refuse any schedule that promotes to production outside the workspace's configured business hours (default 08:00-20:00 host-local). Off-hours promotions require the two-person rule.
- **TLS rate-limit guard** (Phase 4a): cache certificates per apex domain; refuse to issue a new certificate for the same apex domain within 24 hours of a previous issuance.
- **Anomaly detection**: dashboard detects environment-type changes (preview → production) and triggers an alert when the change is followed by a guest-facing content modification within 10 minutes.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the two-person rule for production promotion. Add a test in Phase 1b once the rule is implemented.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.3` — exact-target confirmation (the diff must be in the confirmation payload).
- `C9.3.4` — revision re-check.
- `C9.3.5` — non-reversible + confirmation.
- `C10.2.1` — HTTP binding match.
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.3.3` — admin-tier separation (production promotion is effectively admin-tier).
