# eInvite Plugin Sandbox Specification (V54.6 / Phase 4a)

> **Status**: Phase 4a design document. Companion to `PLUGIN-SPEC.md` (manifest + permissions) and `PLUGIN-SIGNING.md` (signatures).
> **Scope**: Defines the runtime isolation model for eInvite plugins: how UI plugins are sandboxed in a cross-origin iframe, how logic plugins are isolated in a Web Worker running WASM, the message protocol between host and sandbox, and the per-plugin resource limits.
> **Design principle** (ROADMAP §7 4a): JetBrains plugins run with full IDE privileges — no sandbox, no fine-grained permissions. eInvite's users are non-technical event hosts; third-party plugins must be sandboxed and scoped from day one.

---

## 1. Why a sandbox

The manifest declares permissions; the signature proves identity and review; but at runtime, the plugin code executes. Without a sandbox, a malicious or compromised plugin can:

- Walk the host's DOM, read invitation data it was not granted access to, exfiltrate it via `fetch` to an attacker-controlled endpoint.
- Execute `eval()` or `new Function()` to dynamically load more code post-install (evading the manifest's CSP).
- Access `document.cookie` or `localStorage` to steal session tokens.
- Block the host's UI thread with infinite loops.
- Allocate unbounded memory and crash the host tab.

The sandbox enforces: (1) no direct DOM access, (2) no direct network access, (3) no direct cookie/localStorage access, (4) bounded CPU and memory, (5) every capability is gated by the manifest's `permissions[]` array.

---

## 2. Two execution modes

A plugin's `entrypoint` field (`PLUGIN-SPEC.md` §2.1) selects the execution mode:

| Entry extension | Execution mode | Use case |
|---|---|---|
| `.html` | **UI plugin** — cross-origin iframe | Plugins that render UI: `editor.panel`, `content.block`, `map.provider`. |
| `.wasm` | **Logic plugin** — WASM in a Web Worker | Plugins that compute without UI: `automation.provider` triggers, `ai.provider` model adapters, pure data transforms. |
| `.js` | **Logic plugin** — JS in a Web Worker | Plugins that don't ship WASM. Same isolation as WASM (no DOM, no fetch) but runs as JS. |

The host detects the entrypoint extension and selects the sandbox type accordingly. A single plugin cannot mix the two — a UI plugin that also wants to run background work must spawn a Worker from inside its own iframe (the iframe has `allow-scripts` which permits Worker construction; the Worker runs in the iframe's origin, not the host's).

---

## 3. UI plugins — cross-origin iframe

### 3.1 Iframe construction

The host creates the sandboxed iframe with:

```html
<iframe
  src="https://plugins.einvite.local/{vendor_id}/{plugin_id}/{version}/index.html"
  sandbox="allow-scripts"
  referrerpolicy="no-referrer"
  credentialless
  csp="default-src 'self'; script-src 'self' 'nonce-{nonce}'; ..."
></iframe>
```

Key properties:

- **`sandbox="allow-scripts"`** — the iframe can run scripts but is otherwise locked down. Critically, **`allow-same-origin` is NOT set**, which means the iframe's origin is the special "opaque origin" (`null`) and the iframe CANNOT access cookies, localStorage, or its own parent's DOM.
- **`credentialless`** (Chrome 96+, Firefox 110+, Safari 16+) — the iframe loads without credentials (no `Authorization` header, no cookies sent on the iframe's own subresource requests).
- **Cross-origin** — the iframe loads from a different origin (`plugins.einvite.local`) than the host (`einvite.local`). Even if `allow-same-origin` were accidentally set, the cross-origin boundary would still protect the host.
- **`referrerpolicy="no-referrer"`** — the iframe does not leak the host URL via the `Referer` header when it loads subresources.
- **`csp` attribute** — the host injects the manifest's `content_security_policy` (intersected with the host's base CSP — see `PLUGIN-SPEC.md` §5).

### 3.2 The sandbox origin

`plugins.einvite.local` is a dedicated subdomain served by a separate web server process (or a separate virtual host on the same server) with the following properties:

- **No cookies** — the subdomain never sets cookies. The host's auth cookies are scoped to `einvite.local`, not `.einvite.local` (verified at V54 hardening — `secrets_v54.py` sets `SESSION_COOKIE_DOMAIN="einvite.local"` without a leading dot, so the cookie is NOT shared with subdomains).
- **No session** — the subdomain does not authenticate requests. It serves static files only.
- **No CORS** — the subdomain does NOT add `Access-Control-Allow-Origin` headers. The host fetches plugin assets via its own backend (which proxies them), not directly from the browser.

### 3.3 Communication protocol

The host and the iframe communicate via `postMessage` over a dedicated `MessageChannel` (so messages from one plugin cannot be intercepted by another):

```js
// host-side (in src/js/plugin_sandbox_host.js — Phase 4a follow-up)
const channel = new MessageChannel();
const iframe = document.createElement('iframe');
iframe.src = 'https://plugins.einvite.local/.../index.html';
iframe.sandbox = 'allow-scripts';
document.body.appendChild(iframe);
iframe.addEventListener('load', () => {
  // Send the plugin its context + a port to talk back on.
  iframe.contentWindow.postMessage({
    type: 'einvite.plugin.init',
    plugin_id: pluginId,
    version: version,
    permissions: approvedPermissions,
    locale: getUserLocale(),  // 'en' | 'km'
    invitation_context: { invitationId, workspaceId },
    nonce: crypto.randomUUID(),
  }, 'https://plugins.einvite.local', [channel.port2]);
  channel.port1.onmessage = handlePluginMessage;
});
```

The protocol has three message types:

#### 3.3.1 Request (sandbox → host)

```json
{
  "type": "einvite.plugin.request",
  "id": "9c2f1e87-...",
  "method": "invitation.read",
  "args": { "fields": ["title", "event_date"] },
  "permission": "invitation:{current}:read"
}
```

#### 3.3.2 Response (host → sandbox)

```json
{
  "type": "einvite.plugin.response",
  "id": "9c2f1e87-...",
  "ok": true,
  "result": { "title": "...", "event_date": 1789300000 }
}
```

#### 3.3.3 Error (host → sandbox)

```json
{
  "type": "einvite.plugin.error",
  "id": "9c2f1e87-...",
  "error": {
    "code": "permission_denied" | "rate_limited" | "resource_not_found" | "invalid_args" | "internal",
    "message": "...",
    "required_permission": "invitation:{current}:read"
  }
}
```

The host:

1. Validates every incoming `request` against the manifest's `approved_permissions` (the intersection of declared + marketplace-approved).
2. Rate-limits each plugin: max 100 requests per second, max 1000 outstanding requests.
3. Sanitizes every `response.result` to strip PII that the plugin was not granted (e.g. `communication.provider` plugins never see `recipient_email` even if they have `invitation:{current}:message:send` — the host redacts it before forwarding).
4. Logs every request as a `plugin.api_call` audit event (subject to a 10% sampling rate to control volume — full logging is opt-in per plugin in the host's plugin manager UI).

### 3.4 Lifecycle hooks

The host sends the following notifications to the sandbox (sandbox cannot reply — these are fire-and-forget):

| Message type | When | Payload |
|---|---|---|
| `einvite.plugin.init` | Iframe first loaded | Plugin context + MessagePort (see §3.3) |
| `einvite.plugin.context_changed` | User switches invitation, navigates to another page, or selects another element | `{ "invitationId": ..., "pageId": ..., "selection": ... }` |
| `einvite.plugin.locale_changed` | User toggles EN/KM | `{ "locale": "en" | "km" }` |
| `einvite.plugin.suspend` | Host is about to background the iframe (e.g. user switched browser tabs and the host's idle timer fired) | `{}` — sandbox should release idle resources |
| `einvite.plugin.resume` | Host foregrounds the iframe | `{}` |
| `einvite.plugin.uninstall` | Host is uninstalling the plugin | `{}` — sandbox has 1 second to flush state before the iframe is removed |

The sandbox should listen for these and update its UI accordingly. The `einvite-plugin.js` SDK shim (`plugins/sdk/einvite-plugin.js`) provides convenience handlers.

---

## 4. Logic plugins — WASM / JS in a Web Worker

### 4.1 Worker construction

```js
// host-side (in src/js/plugin_sandbox_host.js — Phase 4a follow-up)
const worker = new Worker(
  `https://plugins.einvite.local/.../worker.js`,
  { type: 'module', name: `plugin:${pluginId}:${version}` }
);
worker.postMessage({ type: 'einvite.plugin.init', ... }, [channel.port2]);
```

For WASM plugins, the host's `worker.js` bootstraps the WASM module:

```js
// inside worker.js (sandbox origin, served by plugins.einvite.local)
import init from './index.wasm';
const wasm = await init();
const port = ...; // received in init message
port.onmessage = async (e) => {
  const { method, args, permission } = e.data;
  // dispatch into WASM
  const result = wasm.exports[method](...);
  port.postMessage({ type: 'einvite.plugin.response', id, ok: true, result });
};
```

### 4.2 WASM import restrictions

The WASM module is instantiated with a deliberately minimal import object:

```js
const imports = {
  env: {
    // No `memory` is shared — the WASM module gets its own linear memory.
    memory: new WebAssembly.Memory({ initial: 1, maximum: 50 }),  // 50 pages = ~3.3 MB; max 50 MB heap per plugin
    table: new WebAssembly.Table({ initial: 0, element: 'anyfunc' }),
    // The only host functions exposed to WASM are the request_channel:
    host_request: (method_ptr, method_len, args_ptr, args_len, permission_ptr, permission_len) => {
      // synchronously calls back into the host bridge; returns a response_id
    },
    host_response_read: (response_id, buf_ptr, buf_len) => {
      // copies the response payload into WASM memory
    },
    // Logging only — no I/O, no network, no DOM:
    console_log: (ptr, len) => console.log('[plugin]', readWasmString(wasm, ptr, len)),
  }
};
```

The WASM module has **no** access to:

- `fetch` / `XMLHttpRequest` — there is no HTTP import.
- `setTimeout` / `setInterval` — WASM runs synchronously inside the Worker's event loop.
- `crypto.subtle` — no direct crypto.
- DOM APIs — Workers have no DOM by definition; WASM running in a Worker inherits this.

The only way for WASM to communicate with the host is via the `host_request` import, which is subject to the same permission + rate-limit checks as the iframe's `postMessage` path.

### 4.3 JS Worker mode

For plugins that ship `.js` instead of `.wasm`, the same isolation applies — but the Worker has access to JS's full standard library. To mitigate, the host:

1. Loads the plugin JS inside a `ShadowRealm` (TC39 Stage 3 proposal; available in Chrome 119+ behind a flag; otherwise falls back to `Function`-constructor-based isolation in a separate realm).
2. Patches out the global `fetch`, `XMLHttpRequest`, `WebSocket`, `navigator.serviceWorker`, `caches`, `indexedDB`, and `crypto.subtle` properties on the Worker's global scope.
3. Provides a single `einvoke(method, args, permission)` global function (analogous to WASM's `host_request`).

`ShadowRealm` is preferred over `eval`-based isolation because it provides a clean global with no shared identity with the host realm. The fallback is documented in `plugins/sdk/einvite-plugin.js`.

---

## 5. Capability surface (the host bridge API)

Every plugin (UI or logic) interacts with the host via the same JSON-RPC-style protocol. The methods are:

| Method | Required permission | Description |
|---|---|---|
| `invitation.read` | `invitation:{current}:read` | Read invitation metadata + page list. Field allow-list enforced by the manifest's permissions. |
| `invitation.update` | `invitation:{current}:edit` | Update invitation state. Goes through the host's existing `save_draft` path with diff capture (V54.4 contract). |
| `invitation.publish` | `invitation:{current}:publish` | Trigger publish. Subject to host's publish gate (existing V32 publishing pipeline). |
| `guest.list` | `invitation:{current}:guest:read` | List guests. PII (email, phone) is redacted unless `invitation:{current}:message:send` is also granted. |
| `guest.update_rsvp` | `invitation:{current}:rsvp:update` | Update RSVP state. |
| `message.send` | `invitation:{current}:message:send` | Send a message via the V54.3 delivery_channels pipeline. |
| `asset.upload` | `asset:upload` | Upload a binary asset to ObjectStorage. Bytes flow through `security_scanner_v54.scan_bytes` BEFORE storage (V54 contract). |
| `asset.read` | `invitation:{current}:materials:read` | Read an asset's bytes (subject to V54 malware scan; MalwareDetected → 422). |
| `event.read` | `event:{current}:read` | Read event ecosystem data (V52). |
| `event.create_automation` | `event:{current}:automation:create` | Create an event automation (V52). |
| `template.install` | `template:install` | Install a marketplace template (V36). |
| `plugin.bridge` | `plugin:{other_plugin_key}:{action}` | Inter-plugin communication (rare; both plugins must explicitly declare the cross-permission). |
| `locale.get` | (implicit) | Get the current user locale (always available). |
| `quota.get` | (implicit) | Get the plugin's remaining quota (heap, cpu, storage). Always available. |
| `log.write` | (implicit) | Write a log line (rate-limited to 10/sec). Always available. |

Every method call is logged as a `plugin.api_call` audit event with `actor=plugin:{plugin_id}`, `target=resource_id`, `method`, `permission`, `ok`. This matches the existing `audit_events` table structure (see V32 / `docs/ARCHITECTURE.md`).

---

## 6. Resource limits

### 6.1 Defaults

| Resource | Default cap | Max (marketplace ceiling) |
|---|---|---|
| Heap (WASM linear memory + JS heap) | 50 MB | 256 MB |
| CPU per `host_request` call | 100 ms | 1000 ms |
| Wall-clock per `host_request` call | 500 ms (includes await on host) | 5000 ms |
| Local storage (sandbox origin) | 10 MB | 100 MB |
| Outstanding requests | 1000 | 1000 (hard cap) |
| Requests per second | 100 | 100 (hard cap) |
| Bundle size on disk | 5 MB | 5 MB (hard cap — see `MODERATION-PIPELINE.md` §3.4) |
| Iframe count per plugin | 1 | 1 (hard cap — a plugin cannot nest iframes) |
| Worker count per plugin | 1 (logic plugins only) | 1 (hard cap — a plugin cannot spawn multiple Workers) |

### 6.2 Enforcement

- **Heap**: WASM linear memory is allocated with `maximum: 50` (pages) — a `RuntimeError: out of memory` is raised if the plugin exceeds this. For JS Workers, the host polls `worker.memoryUsage()` (via the Worker's `performance.memory` API, fallback to a `SharedArrayBuffer`-based memory-pressure probe) every 1 second and terminates the Worker if usage exceeds 50 MB. The Worker is restarted (cold state) and the plugin surfaces a `quota_exceeded` error to the user.
- **CPU**: each `host_request` call is wrapped in a `setTimeout` watchdog. If the call does not return within `cpu_ms_per_call + 50ms` grace, the host terminates the Worker (for logic plugins) or surfaces a `cpu_timeout` error to the iframe (for UI plugins, the iframe cannot be terminated without losing the user's work — instead, subsequent requests are rate-limited to 1/sec for 30 seconds as a backoff penalty).
- **Storage**: the sandbox origin's `localStorage` and `IndexedDB` quotas are intercepted by the host via the `navigator.storage.estimate()` API. If usage exceeds `requested_quota.storage_mb`, new writes return a `quota_exceeded` error.
- **Requests per second**: a token-bucket limiter in the host bridge. Overflow returns a `rate_limited` error with a `retry_after_ms` field.

### 6.3 Per-plugin overrides

The manifest's `requested_quota` field (see `PLUGIN-SPEC.md` §2.2) allows a plugin to request a higher cap. The marketplace reviews the request during human review and may approve a higher cap up to the marketplace ceiling. The approved cap is stored in `plugin_installations_v48.approved_quota_json`.

---

## 7. Things the sandbox deliberately does NOT allow

These are common plugin asks that eInvite explicitly refuses:

| Ask | Why refused |
|---|---|
| `allow-same-origin` on the iframe | Would let the iframe read the host's DOM, cookies, and localStorage. Refused. |
| Direct `fetch` to the plugin's own server | Would let the plugin exfiltrate invitation data. All network access goes through `host_request` (subject to permission + audit). |
| `eval` or `new Function` in the sandbox | The CSP forbids `'unsafe-eval'`. The marketplace moderation pipeline rejects plugins containing these patterns (see `MODERATION-PIPELINE.md` §3.3). |
| `document.cookie` access | The iframe runs in an opaque origin (no `allow-same-origin`); `document.cookie` returns the empty string. |
| `localStorage` access on the host origin | Same — the iframe cannot reach the host origin's storage. The sandbox has its own `localStorage` on the sandbox origin, capped per §6.2. |
| Spawning `SharedWorker` or `ServiceWorker` | The CSP `worker-src` is restricted to `'self'` on the sandbox origin; a plugin cannot register a service worker that would outlive the iframe. |
| Filesystem access (`showOpenFilePicker`, `showSaveFilePicker`) | These APIs require user activation and `allow-popups` in the sandbox; we do not grant it. |
| Clipboard access (`navigator.clipboard.writeText`) | Requires `clipboard-write` permission and user activation; we do not grant it. |
| Camera / microphone / geolocation | Refused by default. A future `device:camera:read` permission could be added if a plugin class needs it (e.g. an event check-in plugin); for V54.6 this is out of scope. |

---

## 8. Interactions with the existing V48 runtime

The V48 plugin runtime (`src/js/plugin-runtime-v48.js`) is a declarative-only runtime: it accepts manifests with `permissions[]` and `extensions[]`, validates them against allow-lists, and stores the activation state. It does NOT load plugin code — there is no `eval`, no `iframe`, no `Worker` construction in the V48 runtime.

Phase 4a preserves this: the V48 runtime continues to handle manifest validation and the declarative registry. The Phase 4a sandbox (`src/js/plugin_sandbox_host.js` — to be added in the code follow-up) layers on top:

1. V48 runtime validates the manifest (existing `validate()` function).
2. Phase 4a sandbox validates the manifest against the V54.6 JSON Schema (additional fields: `signature`, `marketplace_signature`, `content_security_policy`, `min_platform_version`, etc.).
3. V48 runtime activates the plugin's declared extension points (existing `activate()` function).
4. Phase 4a sandbox constructs the iframe or Worker for each extension point and wires up the MessageChannel.
5. V48 runtime's existing `einvite:plugin-activated` / `einvite:plugin-deactivated` events are forwarded to the sandbox so it can clean up.

This layering preserves the existing V48 contract: a plugin manifest that does NOT declare `signature` / `marketplace_signature` (i.e. a V48-style development manifest) continues to work in dev-only mode (`EINVITE_ALLOW_UNSIGNED_PLUGINS=1`, refused by `production_preflight`). The V48 `registerManifest()` UI in `src/js/plugin-platform-v48.js` remains the dev entry point; the Phase 4a marketplace UI (a follow-up task) lists doubly-signed plugins from the marketplace.

---

## 9. Acceptance criteria

- A UI plugin's iframe loads from `plugins.einvite.local` with `sandbox="allow-scripts"` (no `allow-same-origin`); the iframe cannot read the host's DOM, cookies, or localStorage.
- A logic plugin's WASM module runs in a Web Worker with a minimal import object (no `fetch`, no DOM, no `setTimeout`); the only host communication is via the `host_request` import.
- Every capability is gated by the manifest's `approved_permissions` (intersection of declared + marketplace-approved).
- Resource limits (heap 50 MB, CPU 100 ms/call, requests 100/sec) are enforced and the sandbox surfaces `quota_exceeded` / `cpu_timeout` / `rate_limited` errors.
- The existing V48 runtime's declarative validation is preserved; the Phase 4a sandbox layers on top without modifying the V48 contract.
- The CSP forbids `'unsafe-inline'` and `'unsafe-eval'`; the host injects a per-load nonce into every script tag.

---

## 10. References

- `docs/plugins/PLUGIN-SPEC.md` — manifest fields (`entrypoint`, `content_security_policy`, `permissions`, `requested_quota`).
- `docs/plugins/PLUGIN-SIGNING.md` — manifest signatures (the sandbox does not load a plugin whose signatures fail verification).
- `docs/plugins/MODERATION-PIPELINE.md` — automated pre-upload checks that reject plugins containing `eval` / `Function` / `document.cookie` patterns.
- `src/js/plugin-runtime-v48.js` — existing V48 declarative runtime (Phase 4a sandbox layers on top).
- `src/js/plugin-platform-v48.js` — existing V48 manifest registration UI (preserved as dev-only entry point).
- `src/python/security_scanner_v54.py` — malware scanner applied to every `asset:upload` from a plugin sandbox.
- MDN: [Window.postMessage()](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage) — the cross-origin message API.
- MDN: [MessageChannel](https://developer.mozilla.org/en-US/docs/Web/API/MessageChannel) — dedicated bi-directional channel.
- MDN: [iframe sandbox attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox) — the allow-list token semantics.
- TC39 ShadowRealm proposal — the JS-isolation primitive used for `.js` logic plugins.

*Last updated: Phase 4a (V54.6).*
