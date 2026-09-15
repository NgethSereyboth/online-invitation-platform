# Attack Story: `plugin.configure`

| Field | Value |
|---|---|
| **Tool ID** | `plugin.configure` |
| **Group** | `plugin` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/plugins/install` (platform-api) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `merge.prepare_job`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["plugin.configure"]` |
| **Feature gate** | `plugins` (`ai_agent/capabilities.py:FEATURE_TOOL_PREFIXES["plugins"] = ("plugin.",)`) — only available when the `plugin_installations_v48` table exists. |

### 1. What it touches

- **Data**: `plugin_installations_v48` (write — installation record), `studio_resources` (write — plugin manifests and assets), workspace settings (`workspaces.settings_json` — plugin-specific configuration).
- **Services**: `POST /api/platform/v52/plugins/install` registers the plugin; the plugin runtime (`src/js/plugin-runtime-v48.js`) is then loaded into the editor sandbox on the next page render.
- **Files**: plugin packages are extracted from the uploaded ZIP into a sandboxed storage area. Plugin manifests, entrypoints, signatures, and declared permissions are stored.
- **Side effects**: plugin code runs in the editor context. UI plugins render in a cross-origin iframe; logic plugins run in a WASM sandbox. Per `docs/ROADMAP.md` §7 Phase 4a, plugins must NOT inherit full platform privileges.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `plugin.configure` with an attacker-supplied `pluginKey`, `version`, and `permissions` array, the attacker could:

- **Install a malicious plugin** under the host's workspace that:
  - Exfiltrates the host's invitation PII to an attacker-controlled endpoint (if the `permissions` array includes `network.fetch` or `asset.read`).
  - Hijacks the editor DOM to display phishing content during the design phase.
  - Subscribes to editor transaction events and exfiltrates every keystroke.
  - Modifies the published invitation snapshot at publish-time to inject malicious scripts (if `permissions` includes `document.write`).
- **Privilege escalation via overbroad `permissions`**: the agent accepts `permissions: arr(string(80), 20)` and the platform enforces the declared scope. If the host accepts the agent-proposed `permissions=["*"]`, the plugin inherits platform-wide access — exactly the JetBrains anti-pattern called out in `docs/ROADMAP.md` §7 ("JetBrains plugins run with full IDE privileges — no sandbox, no fine-grained permissions. That is the model to **avoid**.").
- **Replay attack with an old plugin version**: install `pluginKey=evil, version=1.0` even when `1.2` is the current version, bypassing a security patch in `1.1`.

Blast radius: **workspace-wide** (a plugin installed under a workspace can affect every invitation owned by that workspace). Data affected: **PII + editor DOM + published content + supply-chain**.

### 3. Containment

- **Schema validation**: `pluginKey` is a stable-id (120 chars). `version` is `string(40)`. `permissions` is bounded to 20 string entries of max 80 chars each. `scope` is a free-form object (additional properties allowed — this is itself a soft spot; Phase 1b should add a schema for `scope`).
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=False, confirmation=True, risk="high"` → `destructiveAccepted=True` required.
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **Feature gate**: requires the `plugins` feature table (`plugin_installations_v48`) to exist. If the table is absent, the tool is filtered out by `availability()`.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/platform/v52/plugins/install`.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"pluginKey": ..., "version": ..., "permissions": [...]}`.
- **Malware scanning**: plugin packages uploaded through the materials pipeline are scanned by `src/python/security_scanner_v54.py` (ClamAV / Defender).
- **Signature verification** (Phase 4a): per `docs/ROADMAP.md` §7, plugins will be double-signed (author key + eInvite marketplace CA). Signature is verified on install; unsigned or tampered plugins are refused. (Not yet implemented — Phase 4a.)

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: the host can uninstall the plugin via the plugin management UI (`DELETE /api/platform/v52/plugins/installations/{id}`). This removes the plugin's manifest and entrypoint but cannot undo any data the plugin already exfiltrated or any side effects it caused during its execution.
- **Time to undo**: seconds for the uninstall; permanent for any exfiltrated data.
- **Side effects of undo**: previously-rendered invitation snapshots may have been tampered with by the plugin during its active window. Each published snapshot must be re-fingerprinted and verified.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `workspace:{id}:plugin:install`, `workspace:{id}:plugin:configure`, `workspace:{id}:plugin:uninstall`. Plugin permissions are themselves resource-scoped via `plugin:{pluginKey}:{permission}` (e.g. `plugin:com.evil.analytics:network.fetch`).
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Out-of-band confirmation** for any plugin whose `permissions` array contains `network.fetch`, `document.write`, `asset.read`, or `*` — the host receives an email confirmation link before the install completes.
- **Permissions denylist**: refuse any `permissions` entry containing `*` or matching `network.fetch` / `document.write` for unsigned plugins. Signed marketplace plugins may declare these scopes after moderation.
- **Version pinning**: refuse to install a plugin version older than the most recent installed version of the same `pluginKey`. Force a "downgrade" confirmation if the host explicitly wants to roll back.
- **Anomaly detection**: dashboard detects plugin installs followed by outbound network traffic from the editor iframe within 60 seconds (potential exfiltration indicator).
- **Sandbox enforcement** (Phase 4a): per `docs/ROADMAP.md` §7, UI plugins run in a cross-origin iframe with `sandbox="allow-scripts"` (no `allow-same-origin`); logic plugins run in a WASM module with declared imports. Never full platform privileges.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.

Gap: no test covers the overbroad-permissions attack. Add a test in Phase 1b that refuses `permissions=["*"]` for unsigned plugins.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.5` — non-reversible + confirmation.
- `C9.6.4` — anomaly detection on plugin-install patterns (Phase 1a dashboard).
- `C10.4.1` — external tool servers (MCP / plugin) sandboxed.
- `C10.4.2` — declared permission scopes, refused if undeclared.
- `C10.4.4` — signed and verified on install.
- `C10.4.5` — independent rate limits per plugin.
