# Attack Story: `enterprise.prepare_protocol`

| Field | Value |
|---|---|
| **Tool ID** | `enterprise.prepare_protocol` |
| **Group** | `enterprise` |
| **Risk tier** | `medium` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/enterprise/protocols` (platform-api) |
| **Reversible** | `True` (default) |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `marketplace.install_template`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["enterprise.prepare_protocol"]` |

### 1. What it touches

- **Data**: `enterprise_protocols` (write — protocol definition: name, classification, type, document), `enterprise_protocol_steps` (write — ordered approval steps), `enterprise_directory_entries` (write — official directory entries referenced by the protocol), `enterprise_delegations` (write — delegation chains).
- **Services**: `POST /api/platform/v52/enterprise/protocols` registers the protocol. The enterprise/government subsystem (`future_platform_v52/service.py`) enforces classification-level access control: `public` / `internal` / `restricted` / `confidential`.
- **Files**: protocol `document` may reference classified asset versions stored in the workspace's object storage. Access to these assets is gated by the workspace member's classification clearance.
- **Side effects**: a `confidential` protocol is visible only to workspace members with `confidential` clearance. A `public` protocol is visible to all workspace members and may be embedded in invitations. Approval steps notify designated approvers out-of-band (email / SMS).

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `enterprise.prepare_protocol` with attacker-controlled `classification` and `document`, the attacker could:

- **Downgrade a confidential protocol to public**: the agent sets `classification="public"` on a document that should be `confidential`, exposing classified content to all workspace members and (if published) to the public internet. This is a classic data-downgrade attack.
- **Embed attacker content in a `public` protocol** that is then included in invitations sent to government officials, foreign dignitaries, or other sensitive recipients — damaging the host's diplomatic or organizational reputation.
- **Insert malicious approval steps** that route protocol approval to attacker-controlled email addresses, allowing the attacker to approve (or block) protocol changes at will.
- **Forge delegation chains**: an attacker who controls the `enterprise_delegations` table can impersonate a senior official, signing protocols on their behalf.
- **Insert directory entries** that reference attacker-controlled external endpoints (e.g. a directory entry for a fake "IT Support" contact whose email forwards to an attacker-controlled inbox).
- **Bypass classification clearance** by manipulating the `document` object to include classified assets under a `public` protocol wrapper — the asset itself remains access-controlled, but the protocol metadata leak reveals the asset's existence and classification level.

Blast radius: **workspace-wide for protocol metadata**, **potentially cross-organizational if the protocol is published or shared**. Data affected: **classified PII + diplomatic / organizational reputation + approval-chain integrity**.

### 3. Containment

- **Schema validation**: `name` is `string(160)`. `classification` is constrained to the enum `["public", "internal", "restricted", "confidential"]`. `protocolType` is `string(80)`. `document` is a free-form object (Phase 1b should add a schema).
- **Permission tier**: `manage` — owner / manager only. The enterprise subsystem may further require `enterprise` workspace plan or a `government` workspace flag (Phase 4a).
- **Confirmation boundary**: `confirmation=True` (medium-risk → `exactTargetsAccepted=True`).
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/platform/v52/enterprise/protocols`.
- **Classification enforcement**: `future_platform_v52/service.py` enforces that the actor's classification clearance is >= the protocol's classification. A `confidential` protocol requires a `confidential`-cleared actor.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"name": ..., "classification": ..., "protocolType": ...}`. The audit event itself is classified at the same level as the protocol — unauthorized members cannot read the audit event metadata.

### 4. Reversible

- **Yes**: per `ToolDefinition.reversible = True` (default).
- **How**: `DELETE /api/platform/v52/enterprise/protocols/{id}` marks the protocol as `deleted_at`. Existing approval steps are cancelled. Any notification already dispatched to an approver cannot be un-sent.
- **Time to undo**: seconds for the database row; permanent for any notifications already dispatched.
- **Side effects of undo**: if the protocol was already included in a published invitation, the invitation continues to render the protocol's `public` fields until the invitation is re-published.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `workspace:{id}:enterprise:protocol:create:{classification}` — the classification is part of the grant. A host who has `create:public` does not automatically have `create:confidential`.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Two-person rule** for `classification="confidential"`: the protocol requires approval from a second `confidential`-cleared workspace owner before it is registered.
- **Downgrade prevention**: refuse any update that lowers a protocol's classification (e.g. `confidential` → `public`) without a separate `enterprise:protocol:downgrade` grant and a documented reason.
- **Document schema** (Phase 1b): constrain the `document` object to a typed schema with explicit asset references. Each referenced asset must be re-checked for classification clearance at protocol-creation time.
- **Approval-chain integrity**: approval steps must reference workspace members by `userId`, not by email address. Email-based approval is forbidden because email addresses are mutable.
- **Directory entry validation**: directory entries must reference existing workspace members or pre-registered external contacts. External contacts must be verified out-of-band before being added to the directory.
- **Anomaly detection**: dashboard detects classification downgrades, bulk protocol creation (more than 5 in 1 hour), and protocols created off-hours.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the classification-downgrade attack or the two-person rule. Add tests in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — confirmation (medium-risk → `exactTargetsAccepted`).
- `C9.2.7` — admin-tier separation (enterprise protocols are effectively admin-tier for `confidential` classification).
- `C9.3.3` — exact-target confirmation (`classification` is captured).
- `C9.3.4` — revision re-check.
- `C10.2.1` — HTTP binding match.
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.3.3` — admin-tier separation (two-person rule for `confidential`).
- `C10.6.1` — no exfiltration of classified content via the `document` object.
