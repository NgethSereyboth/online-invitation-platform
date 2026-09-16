# Attack Story: `message.prepare_send`

| Field | Value |
|---|---|
| **Tool ID** | `message.prepare_send` |
| **Group** | `message` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `server` |
| **Binding** | `prepare message in session and open Guests review; no automatic external send` (review-workflow) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `publish.prepare`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["message.prepare_send"]` |

### 1. What it touches

- **Data**: `guests` table (read — name, phone, email, household composition), `messages` / `delivery_log` tables (write — message content + dispatch attempt), and `rsvps` table (read — to determine recipient set).
- **Services**: outbound SMTP (`src/python/server.py:send_platform_email` at line 220) when channel is `email`; SMS / WhatsApp / Telegram gateway adapters when those channels are configured.
- **Files**: no file-system side effects in this tool itself, but message templates may reference asset URLs (`platform_v32/storage.py::ObjectStorage` presigned URLs).
- **Side effects**: external message dispatch to guest contacts. Each recipient may receive an email / SMS / WhatsApp / Telegram message. Send rate is bounded by the channel adapter.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `message.prepare_send` with attacker-controlled `message`, `channel`, and `recipientIds`, the attacker could:

- Send **phishing or scam content** to all invitation guests under the host's verified sender identity. Guests are highly likely to trust a message from the host's invitation platform.
- Exfiltrate guest PII by encoding it into the message body and instructing guests to reply with additional personal data (e.g. "Reply with your full address for seating").
- **Spam-flood** the channel adapter (e.g. SMS gateway) and trigger rate-limit lockouts or billing charges.
- Send **misleading event information** (wrong date, wrong venue, wrong RSVP link) that causes mass guest confusion and reputational damage.
- Send messages with **malicious links** disguised as the invitation URL, harvesting guest credentials on a look-alike domain.

Blast radius: **invitation-scoped for recipients, but cross-channel for sender reputation** (the host's SMTP / SMS sending domain may be flagged as spam by Gmail / Twilio, affecting all future invitations). Data affected: **PII disclosure + external communication + billing abuse**.

### 3. Containment

- **Schema validation**: `channel` is constrained to the enum `["email", "sms", "telegram", "whatsapp"]`. `recipientIds` is a bounded array (max 100 per call). `message` is bounded to 50 000 characters. `FORBIDDEN_KEYS` blocks `url`, `endpoint`, `destination`, `network`, `command` argument keys.
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=False, confirmation=True`. `confirm_plan()` requires `destructiveAccepted=True` (high-risk).
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **Review workflow**: per the binding declaration, this tool "prepares message in session and opens Guests review; **no automatic external send**." The actual send requires the host to confirm via the Guests review UI, which is a second, out-of-band confirmation step.
- **Audit event**: `ai.plan_confirmed`, `ai.tool_authorized`, `ai.tool_authorization_consumed` are all recorded with `toolId="message.prepare_send"` and the recipient count in `metadata_json`.
- **Rate limit**: `ai-agent (120/3600s per user)`.
- **Malware scanning**: if the message contains an attachment URL, the underlying asset is malware-scanned via `src/python/security_scanner_v54.py` before the URL was generated.

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: messages already dispatched cannot be unsent. The host can:
  - Recall messages in the message-batch UI (only effective for queued-but-not-yet-dispatched messages).
  - Send a follow-up correction message.
  - Issue a privacy request (`platform_v32/schema.py:privacy_requests`) to purge delivery logs.
- **Time to undo**: cannot be undone once the channel adapter has accepted the message.
- **Side effects of undo**: the platform's sender reputation may already be damaged.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `invitation:{id}:message:prepare` + `invitation:{id}:message:send` (separate grants — the prepare step does not authorize the send step).
- **JIT elevation**: require a 5-minute TTL grant for `message.prepare_send`. Reason field is mandatory and surfaced in the audit event.
- **Anomaly detection**: dashboard detects when message volume exceeds the host's historical baseline (e.g. > 3 standard deviations from the 30-day rolling average) or when the recipient list expands beyond the guest count by > 20%.
- **Out-of-band confirmation for high-volume sends**: if `recipientIds.length > 50`, require a separate email confirmation step to the host's registered address before the review workflow unlocks.
- **Content scanning**: scan the message body for URL patterns and flag any non-`{originBase}` URLs in the review UI.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.
- `tests/v53_1_ai_project_operator_backend_test.py` — operator backend flow.

Gap: no test specifically covers the "message body contains an external URL" path. Add a forbidden-pattern test for message content in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.5` — non-reversible + confirmation.
- `C9.5.1` — bounded JSON schema for provider output.
- `C10.6.2` — no `url` / `endpoint` / `destination` argument keys.
- `C10.6.3` — no executable markup in message body.
