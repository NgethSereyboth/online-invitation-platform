# Attack Story: `invitation.archive`

| Field | Value |
|---|---|
| **Tool ID** | `invitation.archive` |
| **Group** | `invitation` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `server` |
| **Binding** | `PUT /api/invitations/{invitationId}/archive` (internal-api) |
| **Reversible** | `True` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `materials.insert_into_page`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["invitation.archive"]` |
| **Special: editable while archived** | `ai_agent/capabilities.py:EDIT_WHILE_ARCHIVED = {"invitation.archive"}` — this is the only `manage`-tier tool that remains available on an archived invitation (so it can be un-archived). |

### 1. What it touches

- **Data**: `invitations.archived` (write), `invitations.archived_at`, `invitations.updated_at`. Archiving does NOT delete the invitation, but it removes it from active dashboard lists and blocks all `edit` / `manage` tools except `invitation.archive` itself.
- **Services**: `PUT /api/invitations/{invitationId}/archive` flips the archived flag. The endpoint is enforced by `src/python/server.py` (invitation routes) which performs the same ownership / collaboration check.
- **Files**: no file-system side effects. Stored assets are retained.
- **Side effects**: archiving an *published* invitation does not un-publish it — the public page remains reachable at its custom domain until the host explicitly unpublishes. **This is a documented pitfall** the host must be warned about.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `invitation.archive` with `archived=true` on a *published* invitation `inv_X`, the attacker could:

- **Hide the invitation from the host's dashboard** while the publication remains live at its public URL. The host may not notice the discrepancy for days, during which the public page continues to collect guest RSVPs and PII.
- **Lock out collaborators**: a designer or content-editor who was actively editing the invitation loses access to all `edit` and `manage` tools (except `invitation.archive` itself), blocking work in progress.
- **Trigger a denial-of-service** on the host's event preparation workflow by archiving all of the host's invitations in a single plan (up to 40 tool calls per plan, per `validate_tool_calls(maximum=40)`).

Blast radius: **invitation-scoped for visibility, but the host's entire event preparation workflow is affected if multiple invitations are archived in one plan**. Data affected: **workflow availability + visibility**.

### 3. Containment

- **Schema validation**: `archived` is a `boolean` (constrained). No free-form arguments.
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=True` but `confirmation=True` and `risk="high"` → `destructiveAccepted=True` required.
- **Authorization token**: 30-second single-use, bound to `(userId, invitationId, toolId="invitation.archive", planId, index)`.
- **HTTP-binding match**: `http_request_matches_tool` verifies the request is `PUT /api/invitations/{invitationId}/archive` with the matching `invitationId` from the plan.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` / `ai.tool_authorization_consumed` with `target_type="invitation"`, `target_id=inv_X`, `metadata={"archived": true}`.
- **Edit-while-archived exception**: `EDIT_WHILE_ARCHIVED = {"invitation.archive"}` ensures the un-archive path always works.

### 4. Reversible

- **Yes**: per `ToolDefinition.reversible = True`.
- **How**: invoke `invitation.archive` with `archived=false` on the same invitation. The tool is the only `manage`-tier tool available while archived, so the host can always recover.
- **Time to undo**: seconds.
- **Side effects of undo**: none — the archived flag is flipped back; the dashboard re-lists the invitation.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `invitation:{id}:archive` and `invitation:{id}:unarchive` (separate grants).
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`.
- **Anomaly detection**: dashboard detects when more than 3 invitations are archived in a 5-minute window (potential bulk abuse).
- **Warning on archive-while-published**: the confirmation dialog must surface the warning "This invitation is currently published at `{public_url}`. Archiving does NOT unpublish it. Guests will continue to see the invitation. Unpublish first if you want to take it offline." (EN) / "ការផ្តល់ការអបអរនេះត្រូវបានបោះពុម្ពផ្សាយ។ ការទុកក្នុងប័ណ្ណសំគាល់មិនមែនជាការលុបចោលទេ។ ភ្ញៀវនឹងបន្តឃើញការអបអរ។ សូមលុបផ្សាយជាមុនប្រសិនបើអ្នកចង់យកវាចេញ។" (KH).

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_storage_test.py` — plan lifecycle.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.
- `tests/v53_1_ai_project_operator_contract_test.py` — operator contract.

Gap: no test covers the "archive-while-published" pitfall. Add a UI-level test in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation (even though reversible, the high risk tier triggers destructive confirmation).
- `C9.3.3` — exact-target confirmation (invitationId is captured in `affectedPages` / target set).
- `C9.3.5` — non-reversible + confirmation (this tool is reversible, but confirmation is still required).
- `C10.2.1` — HTTP binding match.
- `C10.3.2` — JIT elevation (Phase 1a).
