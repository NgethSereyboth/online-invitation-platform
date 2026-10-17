# Attack Story: `page.configure_style`

| Field | Value |
|---|---|
| **Tool ID** | `page.configure_style` |
| **Group** | `page` |
| **Risk tier** | `medium` |
| **Permission tier** | `edit` |
| **Executor** | `client` |
| **Binding** | `updatePageStyle` (editor-action) |
| **Reversible** | `True` |
| **Confirmation required** | `False` |
| **Source file** | `ai_agent/tools.py` — `TOOLS['page.configure_style']` |
| **Binding file** | `ai_agent/capabilities.py` — `TOOL_BINDINGS['page.configure_style']` |

### 1. What it touches

- **Operation:** Configure page background, entrance animation, and transition using bounded page properties.
- **Data and inputs:** page-level background, animation, transition, and authorized background-asset references. The schema accepts: `pageId`, `background`, `backgroundAssetId`, `clearBackgroundImage`, `backgroundSize`, `backgroundOverlay`, `useMasterBackground`, `animationPreset`, `animationDuration`, `transitionPreset`, `transitionDuration`; values are validated against the registered bounded schema.
- **Execution boundary:** `editor-action` — `updatePageStyle`. This story does not assume any unlisted external destination or side effect.

### 2. Worst case if malicious

If a prompt-injected or compromised agent persuaded an authorized user to approve `page.configure_style` with attacker-chosen but schema-valid arguments, it could configure a distracting transition or inaccessible background that conceals text or causes motion discomfort for guests. The immediate scope is the authorized invitation/page/resource described above; repeated calls can multiply the effect only within the same underlying permissions and rate limits. Treat model-provided content and target IDs as untrusted until verified against the host's intent.

### 3. Containment

- **Input validation:** `ai_agent/tools.py::validate_tool_call()` applies this tool's registered required fields, types, enums, and declared bounds; the shared validator rejects unknown top-level arguments and recursively blocks several executable-markup, shell/SQL, and destination-key patterns. Nested objects declared with `additionalProperties: true` are permissive, so this shared validation is not a substitute for executor-specific validation.
- **Permission check:** `edit` is the declared minimum permission. Capability discovery filters tools, then `ai_agent/service.py::confirm_plan()` and `authorize_tool_call()` re-check the user's current access immediately before authorization.
- **Plan/revision gate:** approval is bound to this plan's exact tool index, user, invitation, and document revision/fingerprint; stale plans are rejected. This tool does not declare a separate confirmation boundary; normal plan and authorization gates still apply.
- **One-shot authorization:** `authorize_tool_call()` issues a 30-second token bound to `(userId, invitationId, toolId, planId, index)`; it is consumed once (`ai_agent/service.py::consume_tool_authorization()`).
- **Executor boundary:** the registry binds this call to the declared executor/function below; authorization remains enforced by the server API or editor action service. The binding is not an arbitrary endpoint or script supplied by the model.
- **JIT scope:** this tool is not in `JIT_ELIGIBLE_TOOLS`; do not describe a JIT grant as an existing control for it. Its current gates are the role/capability checks, plan rules, and one-shot tool authorization.
- **Audit trail:** when the production audit callback is configured, plan confirmation, tool authorization, token consumption, and JIT state transitions are recorded through `src/python/server.py::write_audit_event` in the hash-chained audit log. Rate limits and workspace AI policy apply to the agent request path.

### 4. Reversible

- **Registry declaration:** `True`.
- **Recovery:** The tool registry marks this operation reversible. Capture the pre-operation values and target IDs; restore them with the corresponding inverse/editor action or invitation history where available, then verify the resulting page and guest-visible preview.

### 5. Mitigation and residual risk

- Before confirmation, show the exact target IDs and meaningful argument summary; reject a stale target, changed document fingerprint, or caller whose invitation permission has changed.
- Keep the host-facing action limited to the declared `editor-action` executor and validate every referenced page, asset, guest, or external-effect target against the current invitation/workspace ownership.
- **Residual test gap:** the general registry/plan tests verify the shared agent contract, not necessarily this specific executor's complete downstream behavior. A tool-specific executor test should cover the malicious outcome described above before treating that behavior as independently certified.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry completeness, schema bounds, and executor bindings.
- `tests/v28_agent_server_contract_test.py` — plan, confirmation, and authorization flow.
- `tests/ai_resource_scopes_test.py` — resource-grant behavior (where mapped).
- `tests/ai_jit_enforcement_test.py` — JIT lifecycle (only applies to JIT-eligible tools).
- **Tool-specific test:** no dedicated end-to-end executor test is asserted by this document; add/identify one for `page.configure_style` in the relevant route/editor subsystem.

### 7. AISVS cross-reference

`C9.1.1` (complete tool inventory), `C9.2.1` (permission enforcement), `C9.2.3` (authorization re-check), `C10.5.1` (untrusted provider/input data). See `docs/ai/AISVS-C9-C10-MAPPING.md`. These are control mappings, not a claim that this individual tool has a dedicated test or an external MCP transport.
