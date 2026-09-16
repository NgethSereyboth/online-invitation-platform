# Attack Story: `marketplace.install_template`

| Field | Value |
|---|---|
| **Tool ID** | `marketplace.install_template` |
| **Group** | `marketplace` |
| **Risk tier** | `medium` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/marketplace/install` (platform-api) |
| **Reversible** | `True` (default) |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `editor.apply_workspace`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["marketplace.install_template"]` |
| **Feature gate** | `marketplace` (`ai_agent/capabilities.py:FEATURE_TOOL_PREFIXES["marketplace"] = ("marketplace.",)`) — only available when the `marketplace_templates_v36` table exists. |

### 1. What it touches

- **Data**: `marketplace_templates_v36` (read — template metadata, signature, version, author), `user_templates` / `user_page_templates` (write — installed template becomes available to the host), `studio_resources` (write — template assets are copied into the workspace's studio library).
- **Services**: `POST /api/platform/v52/marketplace/install` registers the installation. A `marketplace-package-v36` background job (per `future_platform_v52/service.py`) unpackages the template, verifies its manifest, copies assets, and registers a version-pinned template record.
- **Files**: template packages are ZIP archives stored under the workspace's object storage area. Asset versions reference stored-object versions (`platform_v32/storage.py::ObjectStorage`).
- **Side effects**: installed templates appear in the host's template picker and can be used as the basis for new invitations. Each new invitation based on the template inherits its design tokens, fonts, and asset references.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `marketplace.install_template` with an attacker-supplied `templateId`, the attacker could:

- **Install a malicious template** that:
  - Contains a malicious SVG or font asset with embedded `<script>` payload (XSS in the editor at template-insert time).
  - References asset URLs that resolve to attacker-controlled endpoints (SSRF / exfiltration via the asset loader).
  - Carries a benign-looking manifest but a tampered asset body (signature mismatch is currently a Phase 4a control, not yet enforced).
  - Embeds a template-bound plugin manifest that auto-installs a malicious plugin when the host uses the template.
- **Supply-chain attack at scale**: a single compromised template may be used by hundreds of hosts who install it through the marketplace, giving the attacker a foothold in every workspace that adopts the template.
- **License / pricing fraud**: install a paid template with a faked `externalLicenseReference` to bypass the marketplace billing check.
- **Resource exhaustion**: install a 5000-asset template that exhausts the workspace's storage quota and blocks legitimate invitations from being created.

Blast radius: **workspace-wide on install, potentially platform-wide if the malicious template propagates through shared invitations** (a host who shares an invitation based on a malicious template with another workspace can infect the recipient). Data affected: **supply-chain + PII via XSS + storage abuse**.

### 3. Containment

- **Schema validation**: `templateId` is a stable-id (120 chars). `externalLicenseReference` is `string(200)`.
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `confirmation=True` (medium-risk triggers `exactTargetsAccepted=True`). `reversible=True` so `destructiveAccepted` is not required.
- **Feature gate**: requires the `marketplace_templates_v36` table.
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/platform/v52/marketplace/install`.
- **Background job**: `marketplace-package-v36` runs in the bounded job queue (`platform_v32/jobs.py::JobQueue`) with retry limits, idempotency keys, and cancellation.
- **Malware scanning**: the uploaded package is scanned by `src/python/security_scanner_v54.py` before unpacking.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"templateId": ..., "externalLicenseReference": ...}`.

### 4. Reversible

- **Yes**: per `ToolDefinition.reversible = True`.
- **How**: `DELETE /api/platform/v52/marketplace/installations/{id}` uninstalls the template. This removes the template from the host's picker and decrements the installation count.
- **Time to undo**: seconds.
- **Side effects of undo**: invitations that were *already created* from the template retain their content (the template is copied at create-time, not referenced). Asset versions remain in storage; they can be garbage-collected when no invitation references them.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `workspace:{id}:marketplace:install`, `workspace:{id}:marketplace:uninstall`. Template-scoped permissions become `template:{templateId}:instantiate` (a separate grant for using the template to create a new invitation).
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Out-of-band confirmation** when installing a template whose author is not a Verified Vendor (per `docs/ROADMAP.md` §7 Phase 4a Verified Vendor badge).
- **Signature enforcement** (Phase 4a): refuse any template whose signature does not verify against the eInvite marketplace CA. The signed manifest must include a SHA256 of every asset body; mismatches are rejected at unpack-time.
- **Asset URL allowlist**: any URL referenced in a template asset must resolve to the platform's own object-storage origin (`{originBase}/api/platform/v32/objects/{key}`) or a verified CDN. External URLs are refused.
- **SVG / font sanitization**: strip `<script>` tags, `onload` handlers, and external references from SVG and font assets before storing. Use `defusedxml` or equivalent for parsing.
- **Anomaly detection**: dashboard detects when a single template is installed by an unusual number of distinct workspaces within a 24-hour window (potential viral spread of a malicious template).

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the SVG-script / font-payload attack. Add a sanitization test in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — confirmation (medium-risk → `exactTargetsAccepted`).
- `C9.3.3` — exact-target confirmation (`templateId` is captured).
- `C10.4.4` — signed and verified on install (Phase 4a).
- `C10.5.1` — template content treated as untrusted data.
- `C10.6.3` — no executable markup in template assets (sanitization).
