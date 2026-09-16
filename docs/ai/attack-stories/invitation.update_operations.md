# Attack Story: `invitation.update_operations`

| Field | Value |
|---|---|
| **Tool ID** | `invitation.update_operations` |
| **Group** | `invitation` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `client` (default executor — but the binding is an internal API) |
| **Binding** | `PUT /api/invitations/{invitationId}/operations` (internal-api) |
| **Reversible** | `True` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `invitation.archive`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["invitation.update_operations"]` |

### 1. What it touches

- **Data**: `invitations.custom_domain`, `invitations.publish_at`, `invitations.unpublish_at`, `invitations.expires_at`, and the `custom_domains_v45` table (when a custom domain is configured, the platform writes a verification record).
- **Services**: `PUT /api/invitations/{invitationId}/operations` updates the operation fields. If `customDomain` is set, the platform issues a DNS verification challenge via `future_platform_v52/service.py` (custom domain management).
- **Files**: no file-system side effects.
- **Side effects**: changing `customDomain` triggers DNS verification; changing `publishAt` schedules a background job to flip `is_published` at the scheduled time; changing `expiresAt` schedules a background job to flip it back off.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `invitation.update_operations` with attacker-controlled arguments on invitation `inv_X`, the attacker could:

- **Point the invitation at an attacker-controlled custom domain**: the host's verified custom domain (`events.host.com`) is replaced with an attacker-controlled domain (`evil.attacker.com`). Once DNS verification succeeds (or if the attacker can use a domain they already control), the host's previously-trusted URL redirects guests to attacker-controlled content. Guests who bookmarked `events.host.com/i/inv_X` continue to type that URL but receive attacker content.
- **Pre-schedule an early publish**: set `publishAt` to a timestamp in the past, immediately publishing the invitation before the host has reviewed the final design.
- **Schedule a silent un-publish** during the event: set `unpublishAt` to the event start time, taking the invitation offline exactly when guests need it most.
- **Set a short expiry** that takes the invitation offline mid-RSVP window, blocking late RSVPs.
- **Domain hijack via DNS verification challenge**: if the host has not yet verified `events.host.com`, the attacker can substitute an attacker-controlled domain that has the same TXT record pattern, claiming verification before the host notices.

Blast radius: **cross-workspace (DNS verification affects the host's broader DNS posture)**, **invitation-scoped for the publication lifecycle**. Data affected: **brand integrity + DNS posture + publication timing + guest trust**.

### 3. Containment

- **Schema validation**: `customDomain` is a `string(253)` (max RFC-1035 length). `publishAt`, `unpublishAt`, `expiresAt` are `number(0, 9e15)` (epoch millis, bounded). No enum constraints on the domain (the platform performs DNS verification at runtime).
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=True, confirmation=True, risk="high"` → `destructiveAccepted=True` required.
- **Authorization token**: 30-second single-use, bound to `(userId, invitationId, toolId="invitation.update_operations", planId, index)`.
- **HTTP-binding match**: `http_request_matches_tool` verifies `PUT /api/invitations/{invitationId}/operations`.
- **Audit event**: full audit trail including the previous and new `customDomain` / `publishAt` / `unpublishAt` / `expiresAt` values.
- **DNS verification**: a custom domain cannot actually serve content until DNS verification succeeds — `future_platform_v52/service.py` enforces this. However, the *field* is written immediately, which is itself a state change.

### 4. Reversible

- **Yes**: per `ToolDefinition.reversible = True`.
- **How**: invoke `invitation.update_operations` again with the original values. For a custom domain removal, set `customDomain` to an empty string.
- **Time to undo**: seconds for the field update; minutes-to-hours for DNS propagation if the attacker already proved verification on their own domain.
- **Side effects of undo**: if the attacker's domain was already verified and serving, guest traffic may have already been redirected.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: separate grants for `invitation:{id}:custom-domain:set`, `invitation:{id}:custom-domain:clear`, `invitation:{id}:schedule:publish`, `invitation:{id}:schedule:unpublish`. The custom-domain grant is the most sensitive — it deserves its own scope.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason` for any `customDomain` change. **Out-of-band confirmation**: when the `customDomain` value changes, send an email to the host's registered address with a 24-hour confirmation link. The new domain does not serve content until confirmed out-of-band.
- **Diff-aware confirmation**: the confirmation dialog must show the previous value alongside the new value (EN: "Custom domain change: `events.host.com` → `evil.attacker.com`" / KH: "ការផ្លាស់ប្ដូរឈ្មោះដែន: `events.host.com` → `evil.attacker.com`").
- **Anomaly detection**: dashboard detects when a custom-domain change is followed by a `publish.prepare` within 5 minutes (potential attack pattern: switch domain then publish).

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the DNS verification race (attacker proves their own domain before the host notices the substitution). Add a custom-domain verification test in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.3` — exact-target confirmation (must include the previous + new domain values).
- `C9.3.4` — revision re-check (the custom-domain field is part of the document revision).
- `C10.2.1` — HTTP binding match.
- `C10.3.1` — resource scoping (custom-domain is a high-sensitivity sub-resource).
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.6.1` — no exfiltration of cookies / CSRF tokens (custom domain does not transmit secrets).
