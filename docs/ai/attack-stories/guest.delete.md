# Attack Story: `guest.delete`

| Field | Value |
|---|---|
| **Tool ID** | `guest.delete` |
| **Group** | `guest` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `DELETE /api/invitations/{invitationId}/guests/{guestId}` (internal-api) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `guest.update`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["guest.delete"]` |

### 1. What it touches

- **Data**: `guests` table (delete — row is removed), `rsvps` table (cascade — associated RSVPs are deleted or orphaned depending on the platform policy), `delivery_log` (cascade — delivery records referencing the deleted guest are anonymized or orphaned), `invitation_collaborators` (if the guest was also a collaborator, their collaborator row is removed).
- **Services**: `DELETE /api/invitations/{invitationId}/guests/{guestId}` performs the deletion. The endpoint enforces ownership / collaboration checks.
- **Files**: no direct file-system side effects. The guest's avatar (if any) is a stored asset that may be garbage-collected when its ref-count drops to zero.
- **Side effects**: any in-flight email / SMS to the deleted guest will fail. Any household-composition changes (the guest was in a household with other guests) may break the household's grouping.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `guest.delete` for one or more `guestId` values on invitation `inv_X`, the attacker could:

- **Bulk-delete the entire guest list** (up to 40 `guestId` values per plan, per `validate_tool_calls(maximum=40)`, and the agent can issue multiple plans) — wiping out the host's complete guest roster. The host loses the ability to send invitations, track RSVPs, or check in guests.
- **Delete specific high-value guests** (e.g. the host's parents, the wedding officiant) to disrupt the event.
- **Delete guests who have already RSVP'd "Yes"**, causing them to be turned away at the door because their name is not on the list.
- **Cascade-delete RSVP data**: the platform may delete the guest's RSVP record, destroying audit evidence of who was invited and who responded.
- **Cover tracks**: by deleting a guest, an attacker who had been using that guest record for exfiltration (e.g. via a crafted email address that forwards to an attacker-controlled inbox) can erase the evidence.

Blast radius: **invitation-scoped for the guest data**, but **event-disruption impact is high**. Data affected: **PII destruction + audit evidence destruction + event continuity**.

### 3. Containment

- **Schema validation**: `guestId` is a stable-id (120 chars). No free-form arguments.
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=False, confirmation=True, risk="high"` → `destructiveAccepted=True` required.
- **Authorization token**: 30-second single-use, bound to `(userId, invitationId, toolId="guest.delete", planId, index)`.
- **HTTP-binding match**: `http_request_matches_tool` verifies `DELETE /api/invitations/{invitationId}/guests/{guestId}` with the matching `invitationId` and the literal `guestId` from the plan.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` / `ai.tool_authorization_consumed` with `metadata={"guestId": ..., "householdId": ...}`. The audit event is hash-chained and immutable, so even though the guest row is deleted, the audit record proves the deletion occurred.
- **Soft-delete consideration**: the current implementation hard-deletes the guest row. Phase 1b should consider a soft-delete (set `deleted_at` timestamp) so the row can be recovered within a grace window. The audit log preserves evidence of the deletion either way.

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: re-create the guest via `guest.create` with the same `name`, `phone`, `email`, `householdId`, etc. — but the historical RSVP record (if cascade-deleted) cannot be recovered except from a backup. The platform's restore path is documented in `docs/ops/RESTORE-RUNBOOK.md` (Phase 1c).
- **Time to undo**: minutes for re-creating one guest; hours for re-creating 40+ guests from a backup.
- **Side effects of undo**: the re-created guest record has a new `guestId`, which breaks any external references (e.g. calendar invites sent to the guest that contain the old `guestId` in the URL).

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `invitation:{id}:guest:create`, `invitation:{id}:guest:{guestId}:delete`, `invitation:{id}:guest:{guestId}:update`. The per-guest scope is critical — a bulk-delete grant must be explicit, not implicit in the `manage` tier.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Row-count threshold**: any plan that deletes more than 5 guests in a single confirmation flow requires an additional out-of-band email confirmation.
- **Soft-delete** (Phase 1b): change `guests` to use `deleted_at` timestamp; the deleted row is recoverable for 30 days (configurable). The hard-delete becomes a separate admin-tier operation.
- **Bulk-delete rate limit**: refuse more than 100 guest deletes per workspace per hour, even from authorized users.
- **Anomaly detection**: dashboard detects when guest deletions exceed 5 in 5 minutes, or when a delete is followed by a `guest.create` for the same `email` within 10 minutes (potential PII manipulation).
- **Cascade guard**: when deleting a guest, surface a warning in the confirmation dialog: "This will also delete 1 RSVP and 3 delivery log entries. Reversing this requires a backup restore." (EN) / "នេះនឹងលុប RSVP 1 និងកំណត់ហេតុដឹកជញ្ជូន 3 ផងដែរ។ ការបញ្ច្រាស់វាទាមទារការស្ដារពីការបម្រុងទុក។" (KH).

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_storage_test.py` — plan lifecycle.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the cascade-deletion warning. Add a UI-level test in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.3` — exact-target confirmation (`guestId` is captured).
- `C9.3.5` — non-reversible + confirmation.
- `C9.6.1` — audit event for the deletion (immutable evidence).
- `C10.2.1` — HTTP binding match (guest-id literal in path).
- `C10.3.1` — resource scoping (per-guest scope).
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.7.4` — one-click undo (partial — backup restore is the only path).
