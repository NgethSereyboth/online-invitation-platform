# eInvite Plugin SDK

**Version**: 1.0.0 (Phase 4a / V54.6)
**អត្ថបទភាសាខ្មែរ**: សូមមើល §ខ្មែរខាងក្រោម។

The eInvite Plugin SDK helps third-party developers build, sign, and validate plugins for the eInvite marketplace. The SDK is framework-free (no React, no Lodash, no transpilation step) — it runs as-is in any modern browser and the validation script is stdlib-only Python.

> **Design principle** (ROADMAP §7 4a): JetBrains plugins run with full IDE privileges — no sandbox, no fine-grained permissions. eInvite's users are non-technical event hosts; third-party plugins must be **sandboxed and scoped from day one**. The SDK reflects this: there is no escape hatch, no "trusted plugin" mode, no way to bypass the manifest's declared permissions.

---

## 1. What's in the box

```
plugins/sdk/
├── README.md                  ← this file
├── manifest.schema.json       ← JSON Schema for the plugin manifest (V54.6)
├── einvite-plugin.js          ← host bridge shim (imported by the plugin's entrypoint)
├── validate_manifest.py       ← stdlib-only Python manifest + signature validator
└── example-plugin/
    ├── manifest.json           ← minimal worked example (confetti animation)
    ├── index.html              ← UI entrypoint (loaded into the sandbox iframe)
    ├── index.js                ← plugin logic
    └── tests/
        └── test_example_plugin.py  ← stdlib-only Python test (validates manifest + simulates install)
```

---

## 2. Quickstart

### 2.1 Install

The SDK is shipped in-tree — no `npm install` step. To develop a plugin:

1. Copy `plugins/sdk/example-plugin/` to a new directory (e.g. `plugins/my-cool-plugin/`).
2. Edit `manifest.json` — change `name`, `name_kh`, `description`, `description_kh`, `permissions[]`, `extension_points[]`, `entrypoint`, `author`, `author_key_id`.
3. Edit `index.html` / `index.js` (or `index.wasm`) to implement your plugin's logic.
4. Validate the manifest:
   ```sh
   python3 plugins/sdk/validate_manifest.py plugins/my-cool-plugin/manifest.json
   ```
5. Generate an Ed25519 author keypair (see `PLUGIN-SIGNING.md` §3.1) and sign the manifest+bundle.
6. Submit the signed bundle to the marketplace via `POST /_marketplace/plugins/submit`.

### 2.2 The manifest

See `docs/plugins/PLUGIN-SPEC.md` for the canonical spec. The minimum required fields are:

```json
{
  "schema_version": 1,
  "name": "My plugin",
  "name_kh": "ប្លក់អ៊ីនរបស់ខ្ញុំ",
  "version": "1.0.0",
  "description": "...",
  "description_kh": "...",
  "author": { "name": "...", "email": "...", "vendor_id": "..." },
  "author_key_id": "<64-char hex SHA-256 of your Ed25519 public key>",
  "permissions": ["invitation:{current}:read"],
  "extension_points": [{ "id": "my-panel", "point": "editor.panel", "label": "My panel", "label_kh": "..." }],
  "entrypoint": "./index.html",
  "min_platform_version": "54.6",
  "content_security_policy": {
    "default_src": ["'self'"],
    "script_src": ["'self'"],
    "style_src": ["'self'"],
    "img_src": ["'self'", "data:"],
    "connect_src": ["'self'"],
    "frame_src": ["'none'"],
    "object_src": ["'none'"],
    "base_uri": ["'self'"],
    "form_action": ["'self'"]
  },
  "signature": { "algorithm": "ed25519", "public_key": "...", "sig": "...", "signed_payload": "manifest+bundle", "signed_at": 1789300000 },
  "marketplace_signature": { "algorithm": "ed25519", "public_key": "...", "sig": "...", "signed_payload": "manifest", "signed_at": 0, "expires_at": 0 }
}
```

### 2.3 Using the SDK shim

Your `index.html` (UI plugin) or worker entrypoint (logic plugin) imports `../einvite-plugin.js` (or a copy of it). The shim exposes `window.EInvitePlugin`:

```js
window.EInvitePlugin
  .onReady(function (info) {
    console.log('plugin ready', info.locale, info.context.invitationId);
  })
  .onLocaleChanged(function (locale) {
    // re-render your UI with the new locale
  })
  .onContextChanged(function (ctx) {
    // the user switched invitation / page / selection
  });

// Host bridge call (subject to manifest's permissions):
window.EInvitePlugin.invitationRead(['title', 'event_date']).then(function (invitation) {
  console.log(invitation.title, invitation.event_date);
}).catch(function (err) {
  console.error('invitationRead failed:', err.message);
});
```

### 2.4 Available host bridge methods

| Method | Required permission | Notes |
|---|---|---|
| `invitationRead(fields)` | `invitation:{current}:read` | Returns invitation metadata. `fields` is an allow-list array. |
| `invitationUpdate(patch)` | `invitation:{current}:edit` | Subject to host's existing `save_draft` path + diff capture (V54.4 contract). |
| `invitationPublish()` | `invitation:{current}:publish` | Triggers publish. |
| `guestList(opts)` | `invitation:{current}:guest:read` | PII (email, phone) is redacted unless `message:send` is also granted. |
| `guestUpdateRsvp(guestId, status)` | `invitation:{current}:rsvp:update` | |
| `messageSend(guestId, message)` | `invitation:{current}:message:send` | Dispatches via the V54.3 `delivery_channels` pipeline. |
| `assetUpload(bytes, name, mime)` | `asset:upload` | `bytes` is a `Uint8Array`. Bytes flow through `security_scanner_v54.scan_bytes` BEFORE storage. |
| `assetRead(assetId)` | `invitation:{current}:materials:read` | Subject to malware scan; MalwareDetected → 422. |
| `eventRead()` | `event:{current}:read` | Reads V52 event ecosystem data. |
| `eventCreateAutomation(trigger, action)` | `event:{current}:automation:create` | Requires Verified Vendor status (see `MODERATION-PIPELINE.md` §5). |
| `templateInstall(templateId)` | `template:install` | Installs a marketplace template (V36). |
| `getQuota()` | (implicit) | Returns `{ heap_used_mb, heap_cap_mb, storage_used_mb, storage_cap_mb, cpu_ms_per_call }`. |
| `log(level, message, fields)` | (implicit) | Rate-limited to 10/sec by the host. |

### 2.5 Lifecycle hooks

| Hook | When called |
|---|---|
| `onReady(info)` | SDK initialised. `info = { pluginId, version, locale, context }`. |
| `onContextChanged(ctx)` | User switched invitation / page / selection. |
| `onLocaleChanged(locale)` | User toggled EN/KM. |
| `onSuspend()` | Host is about to background the iframe (release idle resources). |
| `onResume()` | Host foregrounds the iframe. |
| `onUninstall()` | Host is uninstalling the plugin (1-second cleanup window). |

---

## 3. Validation

```sh
python3 plugins/sdk/validate_manifest.py <path/to/manifest.json>
```

By default, this validates the manifest against the JSON Schema and prints a report. With `--check-signatures`, it also verifies the author + marketplace Ed25519 signatures (requires the bundle path so the bundle hash can be recomputed).

See `validate_manifest.py --help` for full flags.

---

## 4. Sandbox constraints (read this before you start)

The sandbox is described in detail in `docs/plugins/PLUGIN-SANDBOX.md`. Key constraints:

- Your plugin runs in a cross-origin iframe (`plugins.einvite.local`) with `sandbox="allow-scripts"` — no `allow-same-origin`. You cannot read the host's DOM, cookies, or localStorage.
- Your plugin cannot call `fetch`, `XMLHttpRequest`, `WebSocket`, `navigator.serviceWorker`, `crypto.subtle`, or `new Worker()` directly. All network access goes through the host bridge (subject to permissions).
- Your plugin's heap is capped at 50 MB by default (request more via `requested_quota.heap_mb` — the marketplace may approve up to 256 MB).
- Your plugin's per-call CPU is capped at 100 ms by default (up to 1000 ms with `requested_quota.cpu_ms_per_call`).
- Your plugin's bundle is capped at 5 MB (gzipped).
- The CSP forbids `'unsafe-inline'` and `'unsafe-eval'`. The host injects a per-load nonce into every `<script>` tag — inline scripts are not needed.

Patterns the moderation pipeline **rejects automatically** (see `MODERATION-PIPELINE.md` §3.3):

- `eval(`, `new Function(`, `Function(` constructor
- `document.cookie`, `document.write(`, `window.location =`, `.innerHTML =`, `.outerHTML =`
- `setTimeout("string")`, `setInterval("string")`
- `fetch("https://...")` with a hardcoded external URL (only allow-listed CDN URLs are permitted)
- `new XMLHttpRequest`, `new WebSocket`, `new Worker`, `new SharedWorker`
- `navigator.serviceWorker`, `importScripts(`, `import(` (dynamic), `WebAssembly.compileStreaming(`
- `crypto.subtle` (the host bridge provides signing)
- Base64 strings > 4 KB (suspected obfuscated payload)

---

## 5. Signing your plugin

See `docs/plugins/PLUGIN-SIGNING.md` for the full procedure. Briefly:

1. Generate an Ed25519 keypair locally (keep the private key secret — filesystem mode 0600, never commit to your plugin repo).
2. Compute the canonical payload per `PLUGIN-SIGNING.md` §2.2 (JCS-canonicalised manifest with `signature` + `marketplace_signature` set to `{}` + bundle sha256 + bundle size).
3. Sign the canonical payload with your private key → fills the `signature` block.
4. Register your public key with the marketplace (counter-signed by the marketplace CA).
5. Submit. The marketplace runs moderation; on approval, fills the `marketplace_signature` block.

---

## 6. Reference docs

| File | Purpose |
|---|---|
| `docs/plugins/PLUGIN-SPEC.md` | Manifest format + JSON Schema + 13 extension points + permission grammar |
| `docs/plugins/PLUGIN-SIGNING.md` | Ed25519 double-signing (author + marketplace CA) + CRL |
| `docs/plugins/PLUGIN-SANDBOX.md` | Sandboxed execution model (iframe + WASM Worker + limits) |
| `docs/plugins/MODERATION-PIPELINE.md` | Automated + human review + takedown + Verified Vendor badge |
| `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` | Phase 1a permission grammar reused by the manifest |

---

## ខ្មែរ (Khmer)

**កម្មវិធី SDK សម្រាប់ Plugin របស់ eInvite**

SDK នេះជួយឲ្យអ្នកអភិវឌ្ឍន៍ភាគីទីបីអាចសាងសង់ ចុះហត្ថលេខា និងផ្ទៀងផ្ទាត់ plugin សម្រាប់ marketplace របស់ eInvite។

**គោលការណ៍សំខាន់**: plugin របស់ eInvite ដំណើរការក្នុង sandbox ដាច់ដោយឡែកពី host (cross-origin iframe) ហើយសិទ្ធិគ្រប់គ្រាន់ត្រូវបានប្រកាសនៅក្នុង manifest ដោយច្បាស់លាស់។ គ្មានផ្លូវឡានម៉ាស៊ីនសម្រាប់ "trusted plugin" ទេ។

**ជំហានដំបូង**:

1. ចម្លង `plugins/sdk/example-plugin/` ទៅថតថ្មី។
2. កែ `manifest.json` (ឈ្មោះ ការពិពណ៌នា សិទ្ធិ ចំណុចបន្ថែម)។
3. ផ្ទៀងផ្ទាត់: `python3 plugins/sdk/validate_manifest.py plugins/my-plugin/manifest.json`
4. ចុះហត្ថលេខា Ed25519 (សូមមើល `docs/plugins/PLUGIN-SIGNING.md`)។
5. ដាក់ស្នើទៅ marketplace។

**ឯកសារយោង**: សូមមើល `docs/plugins/PLUGIN-SPEC.md`, `docs/plugins/PLUGIN-SANDBOX.md`, `docs/plugins/PLUGIN-SIGNING.md`, `docs/plugins/MODERATION-PIPELINE.md`។

---

*Last updated: Phase 4a (V54.6).*
