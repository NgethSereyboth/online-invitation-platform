# eInvite Plugin Manifest Specification (V54.6 / Phase 4a)

> **Status**: Phase 4a design document. Companion to `PLUGIN-SIGNING.md`, `PLUGIN-SANDBOX.md`, and `MODERATION-PIPELINE.md`.
> **Scope**: Defines the on-disk manifest format that every eInvite marketplace plugin must ship, the JSON Schema that validates it, the permission model that scopes it, and the 13 extension points it can declare.
> **AISVS driver**: C9.2.6 (permission tiers must reflect the underlying role model and not be hardcoded per agent), C10.3.1 (tool invocations must be scoped to a specific resource and reject cross-resource access).
> **Codebase ground truth**:
> - Existing V48 plugin runtime: `src/js/plugin-runtime-v48.js` (allow-lists 11 extension points + 13 permissions).
> - Existing V48 plugin platform UI: `src/js/plugin-platform-v48.js` (declares declarative manifests + grants).
> - Existing V48 changelog: `docs/V48_PLUGIN_PLATFORM_CHANGELOG.md` (manifests are declarative; executable HTML/JS/SQL/paths/network URLs are rejected).
> - Resource-scoped permission design: `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` §2.1 (grant syntax `{resource_type}:{resource_id}:{action}[:{sub_resource}[:{sub_id}]]`).

---

## 1. Why this exists

JetBrains plugins run with full IDE privileges — no sandbox, no fine-grained permissions, no manifest signing requirement for the long tail of third-party plugins. That model is inappropriate for eInvite, whose users are non-technical event hosts. A malicious JetBrains-style plugin in eInvite could exfiltrate guest PII, send spam to the host's address book, or quietly alter invitation content. The eInvite marketplace refuses that risk surface from day one.

Every plugin on the eInvite marketplace is:

1. **Declarative** — ships a signed manifest that enumerates its permissions, extension points, and version compatibility. Unknown or unauthorized fields are rejected (matching the existing V48 runtime behaviour in `src/js/plugin-runtime-v48.js:scan()` which throws on the `forbidden` set `script|javascript|code|eval|html|cssText|filesystemPath|networkUrl|sql|srcdoc|onload|onclick`).
2. **Double-signed** — author Ed25519 signature + eInvite marketplace CA Ed25519 signature. Both must verify on install.
3. **Sandboxed** — UI plugins run in a cross-origin iframe with `sandbox="allow-scripts"` (no `allow-same-origin`); logic plugins run as WASM in a dedicated Web Worker. Every capability is granted by the manifest's `permissions[]`.
4. **Resource-scoped** — permissions follow the Phase 1a grant syntax from `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` (e.g. `invitation:{id}:read`, `event:{id}:edit`, `template:install`). Wildcard grants (`*`) are rejected.

This document defines (1) and (4). `PLUGIN-SIGNING.md` defines (2). `PLUGIN-SANDBOX.md` defines (3).

---

## 2. Manifest file format

Every plugin ships a single `manifest.json` at the root of its bundle. The file is UTF-8 JSON, max 64 KiB (the manifest only — the bundle itself has its own size limit, see `MODERATION-PIPELINE.md` §3.4).

### 2.1 Required fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | integer | The manifest schema version this file targets. **Must be `1`** for Phase 4a. Future schema versions must be additive (gated by `min_platform_version`). |
| `name` | string | Human-readable plugin name, 1–80 chars. Bilingual display via `name_kh`. |
| `name_kh` | string | Khmer transliteration or translation of `name`. Required per ROADMAP ground rule 5. |
| `version` | string | Semver 2.0.0 version string (e.g. `1.4.2`). Pre-release tags (`-rc.1`) are allowed; build metadata (`+sha.abc123`) is allowed but ignored for ordering. |
| `description` | string | Short description, 1–280 chars. |
| `description_kh` | string | Khmer translation of `description`. Required. |
| `author` | object | `{ "name": "...", "email": "...", "vendor_id": "..." }`. `vendor_id` is the eInvite marketplace vendor identifier (see `MODERATION-PIPELINE.md` §5 Verified Vendor badge). |
| `author_key_id` | string | Fingerprint (hex SHA-256 of the author's Ed25519 public key) that signed this manifest. The matching public key must be retrievable from the marketplace's `/_marketplace/keys/{author_key_id}` endpoint. |
| `permissions` | array<string> | Resource-scoped permission grants required at runtime. Each entry MUST match the grammar in §3. The intersection of declared permissions and approved permissions (per the marketplace's CA signature) is enforced. |
| `extension_points` | array<object> | Each entry declares one extension point the plugin uses (see §4). Empty array is valid for headless plugins (e.g. a pure data-merge plugin). |
| `entrypoint` | string | Relative path within the bundle to the plugin entry. Either `./index.html` (UI plugin → loaded into the sandbox iframe) or `./index.wasm` (logic plugin → loaded as a WASM module in a Web Worker) or `./index.js` (logic plugin → legacy V48 declarative-only runtime; cannot access the DOM or network directly). |
| `min_platform_version` | string | Minimum eInvite platform version that can load this plugin (semver). Compared against the host's reported version (`EINVITE_PLATFORM_VERSION` env). |
| `max_platform_version` | string | Maximum eInvite platform version (exclusive upper bound, semver). Allows the marketplace to retire a plugin on a known-broken major. Optional — if absent, no upper bound. |
| `content_security_policy` | object | Per-plugin CSP that the host injects when loading the entrypoint. See §5. |
| `signature` | object | Author signature block. See `PLUGIN-SIGNING.md` §3. |
| `marketplace_signature` | object | Marketplace CA signature block. Populated by the eInvite marketplace at approval time. See `PLUGIN-SIGNING.md` §4. Empty `{}` on submission; the marketplace fills it. |

### 2.2 Optional fields

| Field | Type | Description |
|---|---|---|
| `homepage` | string | HTTPS URL for the plugin's homepage (display in marketplace UI only; the plugin sandbox cannot fetch it). |
| `repository` | string | HTTPS URL for the source repository (display only). |
| `license` | string | SPDX identifier (e.g. `MIT`, `OFL-1.1`, `Apache-2.0`). Required for marketplace listing. |
| `categories` | array<string> | Marketplace taxonomy tags. Values: `design`, `delivery`, `analytics`, `payment`, `ai`, `calendar`, `maps`, `automation`, `enterprise`, `accessibility`. |
| `icon_256` | string | Relative path to a 256×256 PNG icon, max 32 KiB. |
| `screenshots` | array<string> | Up to 4 relative paths to PNG screenshots (max 800×600, 256 KiB each) for marketplace display. |
| `requested_quota` | object | `{ "heap_mb": 50, "cpu_ms_per_call": 100, "storage_mb": 10 }`. If omitted, defaults from `PLUGIN-SANDBOX.md` §6 apply. Marketplace may cap. |
| `supported_locales` | array<string> | BCP-47 locale tags the plugin ships translations for (e.g. `["en", "km"]`). |
| `compatibility_notes` | string | Free-text notes shown to the host before install (e.g. "Requires eInvite Pro tier for AI tool access"). |

### 2.3 Forbidden fields

The manifest validator rejects the following field names anywhere in the document tree (recursive scan, matching the existing V48 runtime's `forbidden` set at `src/js/plugin-runtime-v48.js`):

```
script, javascript, code, eval, html, cssText,
filesystemPath, networkUrl, sql, srcdoc, onload, onclick,
innerHTML, outerHTML, document_cookie, window_location
```

This list is the union of the V48 runtime's forbidden set and the additional DOM-API surface that a sandboxed plugin might attempt to reach. The recursive scan also enforces a max nesting depth of 12 and a max array length of 500 (matching the V48 runtime).

---

## 3. Permission model

### 3.1 Grant grammar

Permissions are resource-scoped grants, following the syntax from `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` §2.1:

```
{resource_type}:{resource_id}:{action}[:{sub_resource}[:{sub_id}]]
```

Where:

- `resource_type` ∈ `{invitation, event, template, workspace, asset, plugin, guest, message, page, account}`.
- `resource_id` is either:
  - A literal resource identifier (e.g. an invitation UUID) — the plugin operates on that specific resource only.
  - The token `{current}` — the plugin operates on the resource currently active in the host (e.g. the invitation the host is editing). This is the most common case.
  - The token `*` — **rejected**. Wildcard resource grants are never permitted (defence in depth: even an approved plugin cannot ask for blanket access to every invitation).
- `action` is a verb scoped to the resource type (see §3.2).
- `sub_resource` / `sub_id` further narrow the scope (e.g. `invitation:{current}:guest:{guestId}:delete`).

### 3.2 Per-resource actions

| Resource type | Allowed actions |
|---|---|
| `invitation` | `read`, `edit`, `publish`, `archive`, `guest:create`, `guest:read`, `guest:update`, `guest:delete`, `message:prepare`, `message:send`, `rsvp:read`, `rsvp:update`, `materials:read`, `materials:import`, `materials:move`, `asset:insert`, `custom-domain:set` |
| `event` | `read`, `edit`, `manage`, `task:create`, `task:update`, `vendor:create`, `incident:log`, `automation:create`, `automation:enable` |
| `template` | `read`, `edit`, `install`, `instantiate`, `publish` |
| `workspace` | `read`, `marketplace:install`, `plugin:install`, `data-merge:prepare`, `data-merge:execute`, `event-automation:create`, `publishing:environment:create`, `publishing:environment:promote`, `enterprise:protocol:create:{classification}` (classification ∈ `public`, `internal`, `restricted`, `confidential`) |
| `asset` | `read`, `upload`, `delete-own` (deletion is restricted to assets the plugin itself uploaded) |
| `plugin` | `{pluginKey}:{action}` (a plugin can request scoped permission to interact with another plugin via the plugin bridge — see §4.12) |
| `guest` | `read`, `update` (only via `invitation:{current}:guest:{guestId}:update` form — bare `guest:*:*` is rejected) |
| `message` | `prepare`, `send` (only via `invitation:{current}:message:send`) |
| `page` | `read`, `create`, `update`, `delete` (only via `invitation:{current}:page:...`) |
| `account` | `read` (only the host's own account; never `guest` account access) |

### 3.3 Mapping to V48 permissions

The V48 runtime (`src/js/plugin-runtime-v48.js:allowedPermissions`) currently has 13 coarse permission tokens. Phase 4a deprecates them in favour of the resource-scoped grammar above. The marketplace validator accepts BOTH the new grammar and the legacy V48 tokens during a transition window (V54.6 → V55 inclusive); after V55, only resource-scoped grants are accepted. The mapping:

| V48 token (legacy) | Phase 4a resource-scoped grant |
|---|---|
| `project.read` | `invitation:{current}:read` |
| `project.write` | `invitation:{current}:edit` |
| `assets.read` | `invitation:{current}:materials:read` |
| `assets.insert` | `invitation:{current}:asset:insert` |
| `export.prepare` | `invitation:{current}:read` (export is a host-mediated action; the plugin reads the invitation state and submits a render request) |
| `publish.prepare` | `invitation:{current}:publish` |
| `analytics.write` | `workspace:{current}:analytics:write` (new action; not in §3.2 because analytics writes are mediated by the host) |
| `calendar.prepare` | `invitation:{current}:read` (calendar export reads invitation data) |
| `communications.prepare` | `invitation:{current}:message:prepare` |
| `payments.prepare` | `invitation:{current}:read` (payment integration reads invitation metadata; actual payment authorization is host-mediated) |
| `storage.metadata` | `workspace:{current}:storage:read` (new action) |
| `ui.panel` | implicit — declaring an `extension_points[]` entry with `point: "editor.panel"` conveys the panel permission; no separate grant required |
| `content.block` | implicit — declaring an `extension_points[]` entry with `point: "content.block"` conveys the block permission |

### 3.4 Permission evaluation

At install time, the host:

1. Validates the manifest against the JSON Schema (see §6).
2. Computes the set of approved permissions = `manifest.permissions ∩ marketplace_signature.approved_permissions`. The marketplace may approve a subset of the requested permissions (e.g. strip `invitation:{current}:message:send` from a plugin that has no legitimate need to dispatch emails).
3. Persists the approved permission set in the `plugin_installations_v48` table (existing V48 table; new column `approved_permissions_json TEXT NOT NULL DEFAULT '[]'` added by V54.6).
4. At runtime, every host API call from the plugin sandbox is checked against the approved permission set by the host bridge (see `PLUGIN-SANDBOX.md` §4). An unapproved permission request returns `{"error": "permission_denied", "required": "..."}`.

---

## 4. Extension points

eInvite exposes **13 extension points**. The first 11 are inherited from V48 (`src/js/plugin-runtime-v48.js:allowedPoints`); the last 2 are new in Phase 4a to support the marketplace itself.

### 4.1 `editor.panel`

A panel docked in the editor sidebar (right-hand side by default). Plugin renders its own UI inside the sandbox iframe. The host provides the panel container and forwards host events (selection changed, page changed, document dirty).

- Input contract: `{ "type": "editor.panel.mount", "invitationId": "...", "selection": {...}, "page": {...}, "locale": "en|km" }`.
- Output contract: panel uses the host bridge to read invitation state and propose mutations (which are subject to the manifest's permissions).
- Required permission: none implicit (the panel may be purely informational). Any data access requires the corresponding `invitation:{current}:read` or `:edit` grant.

### 4.2 `content.block`

A custom block type that hosts can drag onto an invitation page. Examples: a "Countdown timer" block, a "Khmer lunar calendar" block, a "QR-code RSVP" block.

- Input contract: `{ "type": "content.block.render", "blockId": "...", "props": {...}, "locale": "en|km" }`.
- Output contract: `{ "html": "...", "css": "...", "width": N, "height": N }`. The HTML is sanitized by the host before insertion into the page (DOMPurify-style allow-list; `script` tags and inline event handlers stripped).
- Required permission: implicit (render-only). If the block needs to write back to the invitation (e.g. a "guest can update RSVP in-place" block), declare `invitation:{current}:rsvp:update`.

### 4.3 `asset.provider`

Provides assets (images, icons, illustrations) to the host's asset library. Examples: an Unsplash plugin, a Khmer-pattern pack, a brand-kit plugin.

- Input contract: `{ "type": "asset.provider.search", "query": "...", "locale": "en|km" }`.
- Output contract: `{ "assets": [{ "id": "...", "name": "...", "name_kh": "...", "thumbnail_url": "...", "license": "..." }] }`. The `thumbnail_url` must be HTTPS; the host fetches it (not the plugin).
- Required permission: `asset:upload` (so the host can ingest the chosen asset into ObjectStorage). The plugin itself does not call `asset:upload` — it returns asset descriptors and the host uploads on the host's behalf.

### 4.4 `export.provider`

Provides a custom export target (PDF, PNG, MP4, .ics, calendar feed). The plugin receives the rendered invitation payload and returns a binary blob (or a hosted URL).

- Input contract: `{ "type": "export.provider.export", "invitationId": "...", "format": "pdf|png|mp4|ics|...", "locale": "en|km" }`.
- Output contract: `{ "url": "...", "expires_at": N, "mime": "..." }` OR `{ "blob_b64": "...", "mime": "..." }` (host stores via `asset:upload`).
- Required permission: `invitation:{current}:read` (rendered payload is sensitive — guest list, RSVPs).

### 4.5 `communication.provider`

Provides a delivery channel adapter. Examples: a Line plugin, a Viber plugin, a Slack-workspace-invite plugin.

- Input contract: `{ "type": "communication.provider.send", "invitationId": "...", "recipient": "...", "message": {...}, "locale": "en|km" }`.
- Output contract: `{ "status": "queued|sent|failed|skipped", "provider_message_id": "...", "error": "..." }`. Matches the V54.3 `SendResult` dataclass from `src/python/delivery_channels/base.py`.
- Required permission: `invitation:{current}:message:send`. The marketplace will reject `communication.provider` plugins that lack this permission.

### 4.6 `payment.provider`

Provides a payment integration for ticketed events. Examples: a Stripe plugin, a Khmer PGOS plugin, an ABA-Payway plugin.

- Input contract: `{ "type": "payment.provider.create_checkout", "invitationId": "...", "amount_cents": N, "currency": "USD|KHR", "guest_id": "...", "locale": "en|km" }`.
- Output contract: `{ "checkout_url": "...", "provider_session_id": "...", "expires_at": N }`.
- Required permission: `invitation:{current}:read` (the plugin needs invitation metadata; actual money movement is host-mediated — the plugin returns a checkout URL the host embeds in the invitation page).

### 4.7 `analytics.provider`

Provides an analytics sink. Examples: a Plausible plugin, a PostHog plugin, a Khmer-translation-of-Plausible plugin.

- Input contract: `{ "type": "analytics.provider.event", "invitationId": "...", "event": "...", "props": {...}, "locale": "en|km" }`.
- Output contract: `{ "status": "ok|dropped|error" }`.
- Required permission: `invitation:{current}:read`. Note that the plugin must NOT receive guest PII — the host strips `recipient_email`, `recipient_phone`, and `guest_name` from the payload before forwarding. This is enforced by the host bridge, not by the plugin.

### 4.8 `storage.provider`

Provides an alternative storage backend for plugin-private data. Examples: a plugin that stores user preferences in Dropbox, a plugin that backs up invitation snapshots to Google Drive.

- Input contract: `{ "type": "storage.provider.put|get|list", "key": "...", "value_b64": "..." }`.
- Output contract: `{ "status": "ok|error", "value_b64": "..." }`.
- Required permission: `workspace:{current}:storage:read` (new action; the host must approve the storage backend separately — the marketplace will refuse storage providers that target an unknown domain).

### 4.9 `ai.provider`

Provides an AI model adapter. Examples: a plugin that wraps a local Ollama instance, a plugin that proxies Anthropic models.

- Input contract: `{ "type": "ai.provider.complete", "model": "...", "messages": [...], "max_tokens": N, "temperature": F, "locale": "en|km" }`.
- Output contract: `{ "text": "...", "finish_reason": "...", "usage": {...} }`.
- Required permission: `invitation:{current}:read`. The host enforces that the prompt does NOT contain guest PII (the host bridge strips PII before forwarding to the plugin's model).

### 4.10 `calendar.provider`

Provides a calendar-feed adapter. Examples: a Google Calendar plugin, an Apple Calendar plugin, a Khmer-lunar-calendar plugin.

- Input contract: `{ "type": "calendar.provider.create_event", "invitationId": "...", "start_ts": N, "end_ts": N, "title": "...", "locale": "en|km" }`.
- Output contract: `{ "event_url": "...", "provider_event_id": "..." }`.
- Required permission: `invitation:{current}:read`.

### 4.11 `map.provider`

Provides a map-embed adapter. Examples: an OpenStreetMap plugin, a Google Maps plugin.

- Input contract: `{ "type": "map.provider.embed", "venue": "...", "lat": F, "lng": F, "locale": "en|km" }`.
- Output contract: `{ "embed_html": "...", "embed_url": "..." }`. The `embed_html` is sanitized by the host.
- Required permission: implicit (read-only). If the plugin needs to display the invitation venue, declare `invitation:{current}:read` so the plugin can read the venue address.

### 4.12 `template.provider` (NEW in Phase 4a)

Provides marketplace-listable templates. Examples: a wedding-template pack from a design studio, a Khmer-New-Year template pack from a local designer.

- Input contract: `{ "type": "template.provider.list", "locale": "en|km", "category": "..." }`.
- Output contract: `{ "templates": [{ "template_id": "...", "name": "...", "name_kh": "...", "thumbnail_url": "...", "preview_url": "...", "license": "..." }] }`.
- Required permission: `template:install` (so the host can install the chosen template into the workspace).
- Notes: the marketplace requires Verified Vendor status (see `MODERATION-PIPELINE.md` §5) for any plugin declaring this extension point.

### 4.13 `automation.provider` (NEW in Phase 4a)

Provides event-automation triggers or actions. Examples: a "send thank-you email 24h after event" automation, a "sync RSVPs to a Google Sheet" automation.

- Input contract: `{ "type": "automation.provider.register", "trigger_schema": {...}, "action_schema": {...}, "locale": "en|km" }`.
- Output contract: `{ "automation_id": "...", "version": "..." }`.
- Required permission: `event:{current}:automation:create` for trigger registration; `event:{current}:automation:enable` for trigger enablement.
- Notes: automation plugins run server-side (the trigger evaluation runs in the eInvite scheduler, not in the browser sandbox). The plugin's WASM module is invoked by the scheduler on trigger fire. The marketplace requires Verified Vendor status.

---

## 5. Per-plugin Content Security Policy

The manifest's `content_security_policy` field is an object with the following shape:

```json
{
  "default_src": ["'self'"],
  "script_src": ["'self'"],
  "style_src": ["'self'"],
  "img_src": ["'self'", "data:", "https:"],
  "font_src": ["'self'"],
  "connect_src": ["'self'"],
  "frame_src": ["'none'"],
  "object_src": ["'none'"],
  "base_uri": ["'self'"],
  "form_action": ["'self'"]
}
```

Rules:

1. `'unsafe-inline'` and `'unsafe-eval'` are forbidden. The host bridge injects a nonce into every script tag, so inline scripts are not needed.
2. `https:` is permitted only in `img_src` (so plugins can reference external thumbnail URLs served by their own CDN — the host fetches them, never the sandbox).
3. `connect_src` is restricted to `'self'` — the sandbox cannot make direct network calls. All network access is mediated by the host bridge (which enforces the manifest's permissions).
4. `frame_src` is `'none'` — the sandbox cannot itself embed iframes.
5. The host merges the plugin's CSP with its own base CSP (`default-src 'self'`) by intersecting the directives (the plugin cannot expand the host's CSP).

---

## 6. JSON Schema for the manifest

The canonical JSON Schema lives at `plugins/sdk/manifest.schema.json`. A reproduction follows for reference:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://einvite.local/schemas/plugin-manifest-v1.json",
  "title": "eInvite Plugin Manifest v1",
  "type": "object",
  "required": [
    "schema_version", "name", "name_kh", "version", "description",
    "description_kh", "author", "author_key_id", "permissions",
    "extension_points", "entrypoint", "min_platform_version",
    "content_security_policy", "signature", "marketplace_signature"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "const": 1 },
    "name": { "type": "string", "minLength": 1, "maxLength": 80 },
    "name_kh": { "type": "string", "minLength": 1, "maxLength": 120 },
    "version": { "type": "string", "pattern": "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$" },
    "description": { "type": "string", "minLength": 1, "maxLength": 280 },
    "description_kh": { "type": "string", "minLength": 1, "maxLength": 420 },
    "author": {
      "type": "object",
      "required": ["name", "email", "vendor_id"],
      "additionalProperties": false,
      "properties": {
        "name": { "type": "string", "minLength": 1, "maxLength": 80 },
        "email": { "type": "string", "format": "email" },
        "vendor_id": { "type": "string", "pattern": "^[a-z0-9-]{3,64}$" }
      }
    },
    "author_key_id": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
    "permissions": {
      "type": "array",
      "items": { "$ref": "#/$defs/permission" },
      "maxItems": 64,
      "uniqueItems": true
    },
    "extension_points": {
      "type": "array",
      "items": { "$ref": "#/$defs/extension_point" },
      "maxItems": 32
    },
    "entrypoint": { "type": "string", "pattern": "^\\./[a-zA-Z0-9_./-]+\\.(html|wasm|js)$" },
    "min_platform_version": { "$ref": "#/$defs/semver" },
    "max_platform_version": { "$ref": "#/$defs/semver" },
    "content_security_policy": { "$ref": "#/$defs/csp" },
    "signature": { "$ref": "#/$defs/signature" },
    "marketplace_signature": { "$ref": "#/$defs/signature" },
    "homepage": { "type": "string", "pattern": "^https://" },
    "repository": { "type": "string", "pattern": "^https://" },
    "license": { "type": "string", "pattern": "^[A-Za-z0-9.+-]+$" },
    "categories": {
      "type": "array",
      "items": { "enum": ["design", "delivery", "analytics", "payment", "ai", "calendar", "maps", "automation", "enterprise", "accessibility"] },
      "maxItems": 5,
      "uniqueItems": true
    },
    "icon_256": { "type": "string", "pattern": "^\\./[a-zA-Z0-9_./-]+\\.png$" },
    "screenshots": {
      "type": "array",
      "items": { "type": "string", "pattern": "^\\./[a-zA-Z0-9_./-]+\\.png$" },
      "maxItems": 4
    },
    "requested_quota": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "heap_mb": { "type": "integer", "minimum": 1, "maximum": 256 },
        "cpu_ms_per_call": { "type": "integer", "minimum": 1, "maximum": 1000 },
        "storage_mb": { "type": "integer", "minimum": 0, "maximum": 100 }
      }
    },
    "supported_locales": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z]{2}(-[A-Z]{2})?$" },
      "uniqueItems": true,
      "minItems": 1
    },
    "compatibility_notes": { "type": "string", "maxLength": 500 }
  },
  "$defs": {
    "semver": {
      "type": "string",
      "pattern": "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)"
    },
    "permission": {
      "type": "string",
      "pattern": "^(invitation|event|template|workspace|asset|plugin|guest|message|page|account):(\\{current\\}|\\{[a-f0-9-]+\\}|[a-f0-9-]+):[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*(?::[a-f0-9-]+)?)?$"
    },
    "extension_point": {
      "type": "object",
      "required": ["id", "point"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]{0,63}$" },
        "point": {
          "enum": [
            "editor.panel", "content.block", "asset.provider",
            "export.provider", "communication.provider", "payment.provider",
            "analytics.provider", "storage.provider", "ai.provider",
            "calendar.provider", "map.provider",
            "template.provider", "automation.provider"
          ]
        },
        "label": { "type": "string", "maxLength": 80 },
        "label_kh": { "type": "string", "maxLength": 120 },
        "schema": { "type": "object" }
      }
    },
    "csp": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "default_src": { "type": "array", "items": { "type": "string" } },
        "script_src": { "type": "array", "items": { "type": "string" } },
        "style_src": { "type": "array", "items": { "type": "string" } },
        "img_src": { "type": "array", "items": { "type": "string" } },
        "font_src": { "type": "array", "items": { "type": "string" } },
        "connect_src": { "type": "array", "items": { "type": "string" } },
        "frame_src": { "type": "array", "items": { "type": "string" } },
        "object_src": { "type": "array", "items": { "type": "string" } },
        "base_uri": { "type": "array", "items": { "type": "string" } },
        "form_action": { "type": "array", "items": { "type": "string" } }
      }
    },
    "signature": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "algorithm": { "const": "ed25519" },
        "public_key": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
        "sig": { "type": "string", "pattern": "^[a-f0-9]{128}$" },
        "signed_payload": { "type": "string", "enum": ["manifest", "manifest+bundle"] },
        "signed_at": { "type": "integer", "minimum": 0 },
        "expires_at": { "type": "integer", "minimum": 0 },
        "revoked_at": { "type": "integer", "minimum": 0 },
        "revocation_reason": { "type": "string" }
      }
    }
  }
}
```

---

## 7. Versioning

### 7.1 Semver

Plugin versions follow [SemVer 2.0.0](https://semver.org/). The marketplace enforces:

- **Major bump** required when: removing an extension point, removing a permission, narrowing a permission scope, changing an extension-point contract (input/output schema), removing `supported_locales` entries.
- **Minor bump** required when: adding an extension point, adding a permission (subject to re-approval), adding a new locale, adding an optional manifest field.
- **Patch bump** sufficient for: bug fixes, manifest description / icon / screenshot changes, CSP tightening (loosening the CSP is a minor bump).

### 7.2 Platform compatibility

`min_platform_version` and `max_platform_version` are checked at install time and at every host launch. If the host platform version is outside the declared range:

- At install: the marketplace refuses the install with `{"error": "incompatible_platform", "host_version": "...", "min": "...", "max": "..."}`.
- At launch: the host disables the plugin and surfaces a notice in the dashboard ("Plugin {name} {version} requires eInvite {min}–{max}; you are running {host_version}. Please upgrade the host or uninstall the plugin.").

The host platform version is the `BUILD_INFO.version` field from `docs/BUILD_INFO.json` (currently `54.6` for Phase 4a).

### 7.3 Schema version

The `schema_version` field is the manifest schema version. The marketplace accepts `schema_version: 1` for V54.6 and V55. A future `schema_version: 2` (planned for V56+) may add new fields; the host MUST accept unknown optional fields (forward compatibility — matches the V48 runtime's "safe unknown fields are retained" behaviour from `docs/V48_PLUGIN_PLATFORM_CHANGELOG.md` line 9). Required fields cannot be added in a minor schema bump — that would be a breaking change requiring `schema_version: 2`.

---

## 8. Worked example

A minimal "confetti animation" plugin manifest:

```json
{
  "schema_version": 1,
  "name": "Confetti animation",
  "name_kh": "អានីម៉េសិនផ្កាយរត់",
  "version": "1.0.0",
  "description": "Adds a celebratory confetti animation to the invitation page on RSVP confirm.",
  "description_kh": "បន្ថែមអានីម៉េសិនផ្កាយរត់នៅពេលភ្ញៀវឆ្លើយឆ្លង។",
  "author": {
    "name": "eInvite community",
    "email": "plugins@einvite.local",
    "vendor_id": "einvite-community"
  },
  "author_key_id": "7a8d8e3c5f109b7251643662d1fae18569a207599bba8660289a397248cbba2c",
  "permissions": [
    "invitation:{current}:rsvp:read"
  ],
  "extension_points": [
    {
      "id": "confetti-overlay",
      "point": "content.block",
      "label": "Confetti overlay",
      "label_kh": "ស្រទាប់ផ្កាយរត់",
      "schema": {
        "type": "object",
        "properties": {
          "intensity": { "type": "integer", "minimum": 1, "maximum": 100, "default": 50 }
        }
      }
    }
  ],
  "entrypoint": "./index.html",
  "min_platform_version": "54.6.0",
  "max_platform_version": "56.0.0",
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
  "signature": {
    "algorithm": "ed25519",
    "public_key": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
    "sig": "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c",
    "signed_payload": "manifest+bundle",
    "signed_at": 1789300000
  },
  "marketplace_signature": {
    "algorithm": "ed25519",
    "public_key": "ee1a0000000000000000000000000000000000000000000000000000000000e1",
    "sig": "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    "signed_payload": "manifest",
    "signed_at": 0,
    "expires_at": 0
  },
  "license": "MIT",
  "categories": ["design"],
  "supported_locales": ["en", "km"],
  "requested_quota": {
    "heap_mb": 16,
    "cpu_ms_per_call": 50,
    "storage_mb": 0
  }
}
```

The full working example plugin (manifest + entrypoint + tests) lives at `plugins/sdk/example-plugin/`.

---

## 9. Acceptance criteria for Phase 4a (per ROADMAP §7 4a)

- A third-party plugin can be signed (author + marketplace), sandboxed, and installed without full platform access.
- The manifest schema rejects unknown fields (forward compat: safe unknown fields retained only if `additionalProperties` is `true` for that sub-object — the top-level manifest has `additionalProperties: false`).
- All 13 extension points are enumerable from the manifest schema.
- The permission model is a strict subset of the Phase 1a resource-scoped model from `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` §2.1.
- Bilingual EN+KH is required for every user-facing string (`name`, `description`, every `extension_points[].label`).

---

## 10. References

- `docs/V48_PLUGIN_PLATFORM_CHANGELOG.md` — V48 plugin platform baseline.
- `src/js/plugin-runtime-v48.js` — existing runtime (allow-lists 11 extension points + 13 permissions; rejects executable HTML/JS/SQL/paths/network URLs).
- `src/js/plugin-platform-v48.js` — existing platform UI (declares declarative manifests + grants).
- `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` §2.1 — grant grammar reused by §3.
- `docs/plugins/PLUGIN-SIGNING.md` — Ed25519 double-signing.
- `docs/plugins/PLUGIN-SANDBOX.md` — sandboxed execution model.
- `docs/plugins/MODERATION-PIPELINE.md` — moderation pipeline + Verified Vendor badge.
- `plugins/sdk/manifest.schema.json` — canonical JSON Schema (machine-readable).
- `plugins/sdk/README.md` — getting started guide for plugin developers.
- `plugins/sdk/example-plugin/` — minimal working example.

*Last updated: Phase 4a (V54.6).*
