# Attack Story: `enterprise.prepare_protocol`

| Field | Value |
|---|---|
| **Tool ID** | `enterprise.prepare_protocol` |
| **Group** | `enterprise` |
| **Risk tier** | `medium` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/enterprise/protocols` (platform-api) |
| **Reversible** | `True` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` — `TOOLS['enterprise.prepare_protocol']` |
| **Binding file** | `ai_agent/capabilities.py` — `TOOL_BINDINGS['enterprise.prepare_protocol']` |

### 1. What it touches

- **Operation:** Prepare an enterprise or government ceremony protocol.
- **Data and inputs:** one new enterprise or government ceremony protocol with a bounded classification, protocol type, and structured document. The schema accepts: `name`, `classification`, `protocolType`, `document`; values are validated against the registered bounded schema.
- **Execution boundary:** `platform-api` — `POST /api/platform/v52/enterprise/protocols`. This story does not assume any unlisted external destination or side effect.

### 2. Worst case if malicious

If a prompt-injected or compromised agent persuaded an authorized user to approve `enterprise.prepare_protocol` with attacker-chosen but schema-valid arguments, it could label a restricted ceremony plan as public or replace trusted protocol details with misleading instructions, exposing sensitive attendees or causing an unsafe event sequence. The immediate scope is the authorized invitation/page/resource described above; repeated calls can multiply the effect only within the same underlying permissions and rate limits. Treat model-provided content and target IDs as untrusted until verified against the host's intent.

### 3. Containment

- **Input validation:** `ai_agent/tools.py::validate_tool_call()` applies this tool's registered required fields, types, enums, and declared bounds; the shared validator rejects unknown top-level arguments and recursively blocks several executable-markup, shell/SQL, and destination-key patterns. Nested objects declared with `additionalProperties: true` are permissive, so this shared validation is not a substitute for executor-specific validation.
- **Permission check:** `manage` is the declared minimum permission. Capability discovery filters tools, then `ai_agent/service.py::confirm_plan()` and `authorize_tool_call()` re-check the user's current access immediately before authorization.
- **Plan/revision gate:** approval is bound to this plan's exact tool index, user, invitation, and document revision/fingerprint; stale plans are rejected. This tool has no high-risk destructive confirmation boundary; review its exact arguments and targets before accepting the plan.
- **One-shot authorization:** `authorize_tool_call()` issues a 30-second token bound to `(userId, invitationId, toolId, planId, index)`; it is consumed once (`ai_agent/service.py::consume_tool_authorization()`).
- **Endpoint binding:** the invocation must match the declared HTTP method/path through `http_request_matches_tool()`; invitation/resource IDs are constrained to the approved binding pattern.
- **JIT elevation:** this tool is listed in `ai_agent/jit_elevation.py::JIT_ELIGIBLE_TOOLS`; it requires an active five-minute database grant before a one-shot authorization token is issued. Evaluation binds the grant to user/tool/resource and consumes it once (`ai_agent/jit_elevation.py::JITElevationManager.evaluate`). This tool requires manual approval; it is not in `AUTO_APPROVED_TOOLS`.
- **Audit trail:** when the production audit callback is configured, plan confirmation, tool authorization, token consumption, and JIT state transitions are recorded through `src/python/server.py::write_audit_event` in the hash-chained audit log. Rate limits and workspace AI policy apply to the agent request path.

### 4. Reversible

- **Registry declaration:** `True`.
- **Recovery:** The tool registry marks this operation reversible. Capture the pre-operation values and target IDs; restore them with the corresponding inverse/editor action or invitation history where available, then verify the resulting page and guest-visible preview.

### 5. Mitigation and residual risk

- Before confirmation, show the exact target IDs and meaningful argument summary; reject a stale target, changed document fingerprint, or caller whose invitation permission has changed.
- Keep the host-facing action limited to the declared `platform-api` executor and validate every referenced page, asset, guest, or external-effect target against the current invitation/workspace ownership.
- **Residual test gap:** the general registry/plan tests verify the shared agent contract, not necessarily this specific executor's complete downstream behavior. A tool-specific executor test should cover the malicious outcome described above before treating that behavior as independently certified.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry completeness, schema bounds, and executor bindings.
- `tests/v28_agent_server_contract_test.py` — plan, confirmation, and authorization flow.
- `tests/ai_resource_scopes_test.py` — resource-grant behavior (where mapped).
- `tests/ai_jit_enforcement_test.py` — JIT lifecycle (only applies to JIT-eligible tools).
- **Tool-specific test:** no dedicated end-to-end executor test is asserted by this document; add/identify one for `enterprise.prepare_protocol` in the relevant route/editor subsystem.

### 7. AISVS cross-reference

`C9.1.1` (complete tool inventory), `C9.2.1` (permission enforcement), `C9.2.3` (authorization re-check), `C9.3.3` (exact-target confirmation), `C10.3.2` (JIT elevation), `C10.2.1` (tool-to-endpoint binding), `C10.5.1` (untrusted provider/input data). See `docs/ai/AISVS-C9-C10-MAPPING.md`. These are control mappings, not a claim that this individual tool has a dedicated test or an external MCP transport.
