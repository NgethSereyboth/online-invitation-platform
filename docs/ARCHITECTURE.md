# eInvite Platform — Architecture

> **Phase 0.2 deliverable of `docs/ROADMAP.md`.** This rewrite replaces the pre-V29 era draft with an accurate picture of the current codebase (V53.1 + V54 hardening). Every claim below is grounded in a specific file path.
>
> **Re-verified 2026-10-28 (LT-8.2)** against the Phase 8 tree for the three systems the plan names:
> the editor script split and generated bundle (§3.11), the inspector shell (§7.4) and the bilingual
> pipeline (§7.5). The builder file paths in §3.11 were stale (they are under `src/python/build/`,
> with deprecated root shims) and are corrected here.

---

## 1. Component Diagram

```mermaid
flowchart TD
    subgraph Browser["Browser (build-tool-free)"]
        Editor["Editor Chrome<br/>unified-editor-v34, editor-pro"]
        Renderer["renderer-core.js<br/>shared safe object renderer"]
        CRDT["crdt-adapter.js<br/>pure-JS CRDT engine"]
        CollabUI["collaboration-studio.js<br/>short-poll + presence"]
        Public["public-page.js<br/>advanced-public-renderer-v32"]
        AIUI["ai-creative-agent.js<br/>plan preview/confirm"]
        Assets["asset-workflow.js<br/>upload-client.js"]
    end

    subgraph Server["Python stdlib server (server.py monolith)"]
        Router["ThreadingHTTPServer<br/>~150 routes"]
        Auth["security_v13.py<br/>Argon2id · MFA · Passkeys"]
        Audit["audit_events<br/>hash-chained, immutable"]
        RateLimit["rate_limit<br/>Redis or in-process"]
        Guard["guard_request_boundary<br/>host allowlist · HTTPS · framing"]
        Malware["security_scanner_v54.py<br/>ClamAV / Defender fail-closed"]
        Secrets["secrets_v54.py<br/>auto-gen .env"]
    end

    subgraph V32["platform_v32 (production hardening)"]
        V32Svc["service.py<br/>workspaces, roles, authz"]
        V32Store["storage.py<br/>ObjectStorage: local|s3|r2|minio"]
        V32Jobs["jobs.py<br/>durable JobQueue + idempotency"]
        V32Obs["observability.py<br/>secret-redacting logger"]
    end

    subgraph V52["future_platform_v52 (V34–V52 layer)"]
        V52Svc["service.py<br/>event ecosystem, automation"]
        V52Schema["schema.py<br/>schema 27 additive"]
    end

    subgraph AI["ai_agent (V28, V35, V53.1)"]
        AISvc["service.py"]
        Tools["tools.py · capabilities.py<br/>80 typed tools"]
        Providers["providers.py · local_providers.py<br/>6 provider classes"]
        Context["context.py · storage.py<br/>conversation persistence"]
    end

    subgraph Stores["External stores"]
        DB[("SQLite / PostgreSQL")]
        Cache[("Redis (optional)")]
        Object[("S3 / R2 / MinIO<br/>or local disk")]
        SMTP["SMTP (optional)"]
        External["External AI endpoint (optional)"]
    end

    Editor --> Renderer
    Editor --> CRDT
    Editor --> AIUI
    Editor --> Assets
    Editor --> CollabUI
    CollabUI --> CRDT
    Public --> Renderer
    AIUI --> Assets

    Editor -- "fetch credentials:'same-origin'" --> Router
    Public --> Router
    CollabUI -- "GET /collaboration/v31/updates?since=N<br/>(poll 800 ms)" --> Router
    AIUI --> Router

    Router --> Guard
    Router --> Auth
    Router --> Audit
    Router --> RateLimit
    Router --> Malware
    Router --> Secrets
    Router --> V32Svc
    Router --> V52Svc
    Router --> AISvc

    Auth --> DB
    Audit --> DB
    RateLimit --> Cache
    V32Svc --> DB
    V32Store --> Object
    V32Jobs --> DB
    V52Svc --> DB
    AISvc --> DB
    AISvc --> Providers
    Providers --> External
    Providers --> Cache
    V32Svc --> SMTP
```

---

## 2. Product Model

Every invitation is a versioned structured document. The same document drives the editor, template workflow, preview, immutable publication snapshot, and public guest experience.

```text
Template + event content + visual objects + page/section settings
                              |
                              v
                     Invitation document
                    /          |          \
              Editor      Preview       Publish snapshot
                                           |
                                           v
                                  Public invitation + RSVP
```

The document model is normalized through `src/python/document_schema_v32.py` (cumulative schema 18) and `future_platform_v52/schema.py` (schema 27 additive). Snapshot publishing (V32) makes the published state immutable; CRDT collaboration (V31) handles *live* editing without overwriting published state.

---

## 3. Subsystems

### 3.1 HTTP Server & Route Handler (stdlib `http.server` monolith)

- **Files**: `src/python/server.py` (~6,600 lines, 437 functions, ~150 routes); `Handler` class at line 2397; `connect()` at line 1370; `guard_request_boundary()` at line 2506; `end_headers()` at line 2410.
- **What it does**: A `ThreadingHTTPServer` monolith dispatching `do_GET` / `do_PUT` / `do_POST` / `do_DELETE` across:
  - `/api/auth/*` — register, login, logout, MFA, passkey flows
  - `/api/account/*` — user account, security settings, audit log
  - `/api/invitations/*` — invitation CRUD, including `collaboration/v31/{snapshot,updates,presence,checkpoints}`, `events` (SSE awareness), `raster/v30/documents`
  - `/api/admin/*` — admin overview
  - `/api/platform/v32/*` — V32 production platform (workspaces, object storage, jobs, observability)
  - `/api/platform/v52/*` — V52 event ecosystem
  - `/api/ai-agent/*` — AI agent (V28/V35/V53.1)
  - `/api/ai/assist` — assistant endpoint
  - `/api/billing/*` — billing webhooks
  - `/api/studio/*` — studio automation
  - `/api/templates*`, `/api/uploads/*`, `/api/public/*`
  - `/i/{slug}` — public invitation page
  - `/uploads/`, `/vendor/`, `/assets/` — static asset routes
  - Page HTML routes
- **Auth**: Cookie-first (HttpOnly `SameSite=Lax`, optional `Secure`); Bearer tokens only when `EINVITE_DEV_AUTH_TOKENS=1`.
- **Dependencies**: SQLite (default) or PostgreSQL (psycopg); optional Redis; optional SMTP; optional S3/R2/MinIO via boto3. Loads `ai_agent/`, `platform_v32/`, `future_platform_v52/` from repo root — **`PYTHONPATH=.` is required at startup.**

### 3.2 Authentication & Identity Layer

- **Files**: `src/python/security_v13.py`; `src/python/server.py` (register/login/logout/MFA/passkey routes at lines 3192–3211, 3952–4190; `user()` line 2676; `require_user()` line 2690; `guard_cookie_origin()` line 2601).
- **What it does**:
  - **Argon2id** passwords (time_cost=3, memory_cost=64 MB, parallelism=2, hash_len=32, salt_len=16, type=Type.ID). PBKDF2-HMAC-SHA256 (310 k iterations) fallback when `argon2-cffi` is unavailable. `verify_password` returns `(valid, should_rehash)` for in-place algo upgrade.
  - **MFA (TOTP, RFC 6238)** — `new_totp_secret`, `totp_code`, `verify_totp` (±1 window), `otpauth_uri`. Routes: `/api/account/mfa/*`, `/api/auth/mfa/complete`.
  - **Passkeys (WebAuthn)** — ES256-only attestation, sign-count replay protection. CBOR decoder, `parse_attestation_object`, `cose_ec2_to_pem`, `verify_es256_signature`, `verify_client_data`, `parse_assertion_auth_data`. Routes: `/api/auth/passkeys/*`, `/api/account/passkeys/*`. Audit events: `passkey.added`, `passkey.removed`, `login.passkey_success`.
  - **Double-submit CSRF token** bound to session hash.
  - Optional email-verification gate.
- **Dependencies**: `argon2-cffi` (optional), `cryptography` (optional, passkey ES256 verify); SQLite/PostgreSQL `users`, `sessions`, `passkeys`, `auth_challenges` tables.

### 3.3 AI Agent Tool Registry & Capability Discovery

- **Files**: `ai_agent/tools.py`, `ai_agent/capabilities.py`, `ai_agent/__init__.py`, `ai_agent/storage.py`, `ai_agent/service.py`.
- **What it does**:
  - **80 typed `ToolDefinition` entries** across 30+ groups: `read`, `object`, `transform`, `style`, `image`, `gallery`, `photo`, `page`, `invitation`, `event`, `guest`, `rsvp`, `analytics`, `account`, `materials`, `design`, `asset`, `check`, `fix`, `preview`, `export`, `publish`, `message`, `editor`, `marketplace`, `enterprise`, `animation`, `publishing`, `merge`, `plugin`.
  - Permission tiers remain `read` / `edit` / `manage` / `admin` as the compatibility fallback; **9 of the 80 tools currently have resource-scoped grant mappings**, and unmapped tools continue to use the legacy tier check during the staged rollout (`ai_agent/capabilities.py::TOOL_REQUIRED_GRANTS`, `availability()`). A mapped tool uses an active resource grant authoritatively when a matching resource/action grant exists, with legacy fallback only when no matching grant exists.
  - **JIT elevation is implemented** for 13 high-risk tools (`ai_agent/jit_elevation.py::JIT_ELIGIBLE_TOOLS`): high-risk tool authorization checks a short-lived, unconsumed database grant; absent grants trigger an elevation request, and an approved grant is consumed once. `publish.prepare` may be auto-approved for an owner/manager; other JIT-eligible operations require manual approval.
  - `TOOL_BINDINGS` dict declares every tool's bound API path or editor function for runtime HTTP verification.
  - `build_access_snapshot()` gates tools by account/invitation role, plan, storage, archived state, workspace AI policy, resource grants, and feature-table existence (`event_tasks_v52`, `plugin_installations_v48`, `animation_projects_v44`, `custom_domains_v45`, `data_merge_jobs_v47`, `marketplace_templates_v36`).
- **Dependencies**: SQLite/PostgreSQL.

### 3.4 AI Provider Adapters (provider-neutral with offline fallback)

- **Files**: `ai_agent/providers.py`, `ai_agent/local_providers.py`, `ai_agent/config.py`, `ai_agent/design_blueprints.py`, `ai_agent/context.py`.
- **What it does**: Six provider classes:
  - `FakeProvider` — test stub
  - `OfflineTemplateProvider` — deterministic template-filling fallback
  - `ExternalProvider` — HTTP POST to `EINVITE_AI_ENDPOINT` with bounded response schema + `projectDataIsUntrusted` policy
  - `LocalGovernedProvider` — server-only local-model planner
  - `FallbackProvider` — primary → fallbacks chain
  - `RoutedProvider` — ordered failover up to 8 routes
- Local providers default to Ollama (`http://127.0.0.1:11434`), LM Studio (`:1234`), GPT4All (`:4891`); loopback-only or admin allowlist; HTTP-only, no redirects.
- Capability gates for tools / vision / structured-output.
- **Dependencies**: optional external AI endpoint; optional local AI runtime.

### 3.5 V32 Production Platform

- **Files**: `platform_v32/service.py`, `platform_v32/storage.py`, `platform_v32/jobs.py`, `platform_v32/schema.py`, `platform_v32/config.py`, `platform_v32/observability.py`.
- **What it does**:
  - Multi-tenant workspaces (personal + organization); roles `viewer < reviewer < content-editor < designer < manager < owner` (`ROLE_ORDER` + `ROLE_PERMISSIONS`).
  - `ObjectStorage` provider-neutral abstraction (local | s3 | r2 | minio) with SSE-S3, multipart uploads, presigned URLs.
  - `JobQueue` (1–32 workers, 10 k queue, exponential retry, cancellation, idempotency keys).
  - Collaboration server endpoints (`collaboration_snapshot` / `updates` / `checkpoints` / `presence`).
  - Raster edit documents (2 MB cap, pixel-limit enforced).
  - `Observability` per-workspace metrics + secret-redacting logger.
  - Publication readiness validator walks every asset reference.
- **Dependencies**: SQLite/PostgreSQL; optional S3/R2/MinIO via boto3; thread pool.

### 3.6 V52 Future Platform (V34–V52 capability layer)

- **Files**: `future_platform_v52/service.py`, `future_platform_v52/schema.py`, `future_platform_v52/__init__.py`.
- **What it does**: Builds on V32 to provide:
  - V34 unified editor profiles
  - V35 production AI agent (workspace routing policies, saved workflows, monthly budget ledger, model role assignment)
  - V36 template marketplace
  - V42 enterprise/government (protocols, approval steps, directory, classification levels)
  - V44 animation projects + export jobs
  - V45 custom domains + publication environments
  - V47 data merge sources/jobs/variants
  - V48 plugin manifests/installations/grants (13 extension points)
  - V52 event ecosystem (programs/tasks/vendors/incidents/automations/automation_runs)
- Registers 4 job handlers: `animation-export-v44`, `bulk-generation-v47`, `event-automation-v52`, `marketplace-package-v36`.
- Schema version 27 (additive migrations only).
- **Dependencies**: V32 `PlatformService` + `AgentService` + audit callback.

### 3.7 CRDT Collaboration Adapter (pure client-side)

- **Files**: `src/js/crdt-adapter.js` (38-line dense IIFE).
- **What it does**: Pure-JS CRDT engine frozen as `window.EInviteCRDTV31`. Operations: `set`, `delete`, `sequence-insert`, `sequence-move`, `rich-text` (paragraphId/runId/start/end spliced), `checkpoint`. Each update carries `version/id/documentId/epoch/actor/clock/type/objectType/path/payload/timestamp/origin`. `compareClock` (numeric clock → actor string tiebreak) resolves register conflicts. State vector per actor.
- Limits: `MAX_UPDATE_BYTES=256000`, `MAX_PENDING=2000`, `MAX_APPLIED=20000`.
- Functions: `createState`, `nextUpdate`, `apply`, `receive`, `acknowledge`, `compact`, `diff`, `fingerprint` (FNV-1a), `serialize`. Epoch mismatch throws `code=EPOCH_MISMATCH`.
- **Dependencies**: `window.EInviteDocumentV32`; localStorage for actor ID.

### 3.8 Collaboration Studio UI (transport + presence)

- **Files**: `src/js/collaboration-studio.js` (36-line dense IIFE), `src/css/collaboration-studio.css`, `src/js/canva-scale.js`.
- **What it does**:
  - Joins room via `GET /api/invitations/{id}/collaboration/v31/snapshot`.
  - **Short-polls** `.../updates?since=N` every 800 ms (3 s offline).
  - Submits local CRDT updates via `POST .../updates` (epoch_mismatch check, max 500/batch).
  - Posts presence + cursor every 5 s via `POST .../presence`.
  - Creates durable checkpoints via `POST .../checkpoints` (calls `EInviteCRDTV31.compact()`).
  - Listens to `einvite:editor-command` events → diffs against `lastDocument` → emits CRDT updates.
  - Offline queue persisted to `localStorage[einvite-crdt-queue-v31:{invitationId}:{actor}]`. Recovery export = JSON blob.
- **Dependencies**: `window.EInviteCRDTV31`, `window.EInviteEditorBridge`, `window.EInviteContext`, `fetch credentials:'same-origin'`.

### 3.9 Pre-CRDT SSE Awareness Channel

- **Files**: `src/python/server.py::invitation_events` (line 4481).
- **What it does**: Short-lived `text/event-stream` at `GET /api/invitations/{id}/events` (30 ticks × 2 s ≈ 60 s). Emits `event: invitation-update` with `{updatedAt, clientId, mutationId}` when `invitations.updated_at` changes; `": keep-alive\n\n"` every 5th tick. EventSource reconnects automatically.
- **Awareness only — NOT a CRDT transport.**

### 3.10 V54 Security Hardening (scanner + secrets + preflight)

- **Files**: `src/python/security_scanner_v54.py`, `src/python/secrets_v54.py`, `src/python/production_preflight.py`, `src/python/dependency_preflight.py`, `deploy/linux/install-einvite-laptop.sh`, `deploy/.env.example`, `deploy/.env.production.example`.
- **What it does**:
  - **On-startup fail-closed malware scanner gate**:
    - Linux: ClamAV INSTREAM over UDS (`/run/clamav/clamd.ctl` + 3 fallbacks) and TCP `127.0.0.1:3310`.
    - Windows: `MpCmdRun.exe -Scan -ScanType 3 -File <path> -DisableRemediation`.
    - 60 s timeout. `scan_file` / `scan_bytes` never raise. `startup_preflight` raises `RuntimeError` unless `EINVITE_ALLOW_NO_SCANNER=1`. `MalwareDetected` → HTTP 422.
  - **Auto-secret generation** (`ensure_secret()`): generates `EINVITE_SECRET_KEY` + `EINVITE_BILLING_WEBHOOK_SECRET` (`secrets.token_urlsafe(64)`) into repo-root `.env` (mode 0600) when missing/placeholder; never overwrites non-placeholder values; refuses length < 32.
  - **Production preflight** (`production_preflight.py`): enforces `EINVITE_COOKIE_SECURE`, `EINVITE_ALLOWED_HOSTS`, `EINVITE_REQUIRE_MALWARE_SCAN` in production mode.
- **Dependencies**: optional clamd / clamdscan (Linux); optional MpCmdRun.exe (Windows); repo-root `.env`.

### 3.11 Asset Pipeline & Build System (route-bundle manifests)

- **Files**: `src/python/build/build_route_bundles.py`, `src/python/build/build_editor_bundle.py`, `src/python/build/build_page_manifests.py`, `src/python/build/sync_frontend_assets.py`, `docs/route-bundle-sources.json`, `docs/route-bundles.json`. The repo-root `build_route_bundles.py`, `build_editor_bundle.py` and `build_page_manifests.py` are **deprecated shims** that forward to these; `build.py` is the only supported entry point.
- **What it does**: Concatenates source JS/CSS files declared in `docs/route-bundle-sources.json` into `bundle-<page>.js` / `.css` written to **both** `src/python/` (server-served) AND `src/js/` + `src/css/` (repo truth). `--check` mode verifies byte-identical hashes. `sync_frontend_assets.py` mirrors HTML, `vendor/`, `assets/`, `licenses/` into `src/python/`. `server.py::ensure_frontend_assets` runs all three builders with `--check` at startup (and rebuilds in dev mode). Step order is `editor → bundles → manifests → mirror`, because the manifest measures bundle bytes and the mirror must verify a fully-generated tree.
- **The editor route ships two startup scripts.** `docs/route-bundle-sources.json` gives `index.html` a `scriptSplitAt` of 24, so the eager editor JavaScript is cut into `bundle-index.js` and `bundle-index-2.js`. The two files carry the same bytes in the same order and execute in document order (behaviour unchanged, and the page keeps its script count by folding a former head script into the first part); the split exists so a ~1 MB editor bundle does not land as one ~700 ms long task — each file compiles in its own task. A third artifact, `bundle-index-deferred.js`, is generated the same way but never referenced from HTML: `route-deferred-loader.js` injects it after first paint. `docs/route-bundles.json` records both startup hashes, the split index and the deferred chunk.
- **The editor enhancement bundle is one JS + one CSS artifact, written to three roots.** `build_editor_bundle.py` concatenates five JS modules (`canvas-plus`, `editor-builders`, `editor-pro`, `photo-editor`, `creative-packs`) into `editor-suite.js` and seven CSS modules (those five plus `collaboration` and `collaboration-live`) into `editor-suite.css`, then writes each to `src/python/` (the server's ROOT), `src/js` / `src/css` (the source mirror) and `src/python/build/` (legacy readers). Collaboration **JavaScript** is deliberately excluded from the JS bundle: it has its own network lifecycle (SSE plus polling) and bundling it duplicated connections and listeners when the bundle was regenerated. Its **styles** stay in the CSS bundle, so the separately loaded UI keeps its appearance without another stylesheet request.
- **Dependencies**: Python 3 stdlib only.

---

## 4. Storage Abstraction

### 4.1 Object Storage (`platform_v32/storage.py::ObjectStorage`)

| Provider | Env var | Production required? | Notes |
|---|---|---|---|
| **Local** (filesystem) | `EINVITE_OBJECT_STORAGE_PROVIDER=local` (default) | No (dev only) | Root `DATA/objects-v32`; HMAC-SHA256 signed URLs for `/api/platform/v32/objects/{key}` |
| **AWS S3** | `EINVITE_OBJECT_STORAGE_PROVIDER=s3` | Yes | boto3; SSE-S3 AES256 on every PUT; presigned GET/POST URLs; multipart uploads |
| **Cloudflare R2** | `EINVITE_OBJECT_STORAGE_PROVIDER=r2` | Yes | S3-compatible via `EINVITE_OBJECT_STORAGE_ENDPOINT` |
| **MinIO** | `EINVITE_OBJECT_STORAGE_PROVIDER=minio` | Yes | S3-compatible via `EINVITE_OBJECT_STORAGE_ENDPOINT` |

### 4.2 Relational Database (`server.py::connect` line 1370)

| Backend | Trigger | Notes |
|---|---|---|
| **SQLite** (default) | `DB = DATA/invites.db` | `sqlite3.connect(DB, timeout=10)` |
| **PostgreSQL** | `EINVITE_DATABASE_URL` starts with `postgres://` or `postgresql://` | psycopg + dict_row; `PostgresAdapter` wraps connection; `_ensure_postgres_schema` runs idempotent migrations; legacy guest `token_hash` migration |

### 4.3 Cache / Rate-limit / Presence (`server.py::redis_client` line 205)

| Component | Backend | Notes |
|---|---|---|
| Rate-limit counters | Redis (optional via `EINVITE_REDIS_URL`) — `INCR` + `EXPIRE` per window bucket | In-process fallback: `RATE_BUCKETS` dict + `RATE_LOCK` |
| Presence | Redis (optional) — hash keys | In-process fallback: `PRESENCE_STATE` dict + `PRESENCE_LOCK` (60 s TTL) |

### 4.4 Background Job Queue (`platform_v32/jobs.py::JobQueue`)

- In-process `queue.Queue` (maxsize 10 000) + 0–32 worker threads.
- DB-backed `platform_jobs` table for durability + idempotency keys + retry tracking + cancellation flag.
- **Webhook delivery is queued, not threaded** (`src/python/core/webhooks.py`, Stage E 2026-10-29):
  `dispatch_webhook_event` writes one `webhook.deliver` row per endpoint into `background_jobs`, and
  `process_webhook_jobs` performs one attempt per due job — 1/2/4/8 s backoff, the fifth failure
  final, non-retryable statuses final immediately. The worker tick is every second under
  `EINVITE_BACKGROUND_MEDIA=1`; otherwise dispatch drains the queue inline. `now_ms` is injectable, so
  the backoff is tested with a clock rather than sleeps. `validate_destination` is the single SSRF
  guard: https only (`allow_private` is the explicit local-receiver opt-out), no userinfo, every
  resolved address public, re-resolved per attempt with the socket pinned to the validated address,
  no redirect followed, 5 s timeout and a 64 KiB reply cap.

### 4.5 SMTP (optional)

- `server.py::send_platform_email` line 220.
- Transactional email via `EINVITE_SMTP_*` for verification, password reset, security notifications.

### 4.6 Browser Persistence

- **localStorage**: workspace state, CRDT actor IDs, offline CRDT queues, sidebar collapse, theme.
- **IndexedDB**: offline editor fallbacks.

---

## 5. Collaboration Model

The platform uses **POLLING + CRDT + DURABLE CHECKPOINTS + SNAPSHOT PUBLISHING** (not pure SSE, not operational transform).

```mermaid
sequenceDiagram
    participant Browser as Editor (collaboration-studio.js)
    participant CRDT as crdt-adapter.js
    participant Server as server.py + platform_v32
    participant DB as invitations / collaboration_updates

    Browser->>Server: GET /collaboration/v31/snapshot
    Server->>DB: SELECT document, recent updates, presence
    Server-->>Browser: snapshot (document + epoch + revision + checkpoint)
    Browser->>CRDT: createState(snapshot)

    loop Every 800 ms
        Browser->>Server: GET /collaboration/v31/updates?since=N
        Server-->>Browser: updates (epoch_mismatch check)
        Browser->>CRDT: receive(updates)
    end

    Browser->>CRDT: nextUpdate(localEdit)
    Browser->>Server: POST /collaboration/v31/updates (max 500/batch)
    Server->>DB: INSERT collaboration_updates (unique on invitation+epoch+actor+clock)
    Server->>DB: UPDATE invitations SET draft_json = applied
    Server-->>Browser: ack (new revision)

    loop Every 5 s
        Browser->>Server: POST /collaboration/v31/presence (cursor, 45 s TTL)
    end

    Browser->>Server: POST /collaboration/v31/checkpoints
    Server->>DB: INSERT collaboration_checkpoints
    Browser->>CRDT: compact()
```

### DB tables

- `collaboration_updates` — unique on `invitation_id + document_epoch + actor_id + logical_clock`.
- `collaboration_checkpoints` — durable checkpoints for compaction + recovery.

### Roles

`viewer < reviewer < content-editor < designer < manager < owner` (defined in `platform_v32/service.py::ROLE_ORDER` + `ROLE_PERMISSIONS`).

---

## 6. Security Stack

| Control | File | Detail |
|---|---|---|
| **Argon2id** | `src/python/security_v13.py` (lines 20–37) | `PasswordHasher` time_cost=3, memory_cost=64 MB, parallelism=2, hash_len=32, salt_len=16, type=Type.ID. PBKDF2-HMAC-SHA256 310 k-iteration fallback. `verify_password` returns `(valid, should_rehash)`. |
| **MFA (TOTP, RFC 6238)** | `src/python/security_v13.py` + `src/python/server.py` | `new_totp_secret`, `totp_code`, `verify_totp` (±1 window), `otpauth_uri`. Routes `/api/account/mfa/*`, `/api/auth/mfa/complete`. |
| **Passkeys (WebAuthn)** | `src/python/security_v13.py` + `src/python/server.py` | ES256-only attestation; sign-count replay protection; CBOR decoder; `parse_attestation_object`, `cose_ec2_to_pem`, `verify_es256_signature`, `verify_client_data`, `parse_assertion_auth_data`. Routes `/api/auth/passkeys/*`, `/api/account/passkeys/*`. Audit events `passkey.added` / `passkey.removed` / `login.passkey_success`. |
| **CSP** | `src/python/server.py::csp_header` + `end_headers` | Per-response policy with a fresh `style-src 'self' 'nonce-…'` (the nonce is injected into served `<style>` tags); `img-src 'self' data: blob:` plus only the configured HTTPS object-storage origin. `default-src 'self'; script-src 'self'; style-src 'self' 'nonce-…'; img-src 'self' data: blob:[storage]; media-src 'self' blob:; font-src 'self' data:; frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://w.soundcloud.com; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'` |
| **Same-origin** | `src/python/server.py::guard_cookie_origin` (line 2601) + `guard_request_boundary` (line 2506) | Origin + Sec-Fetch-Site + double-submit CSRF token bound to session hash + host allowlist + Transfer-Encoding/Content-Length framing validation + HTTPS-308 redirect. Headers: `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-site`, `X-Frame-Options: SAMEORIGIN` (SAMEORIGIN not DENY — preserves editor storyboard iframe preview). |
| **Rate limiting** | `src/python/server.py::rate_limit` (line 2754) | Redis-first via `EINVITE_REDIS_URL` (INCR + EXPIRE per window bucket); in-process `RATE_BUCKETS` + `RATE_LOCK` fallback. Per-IP: register 10/600 s, login 30/600 s, mfa-login 20/600 s, passkey-options/login 30/600 s, password-reset 8/3600 s, password-reset-confirm 20/3600 s. Per-user: verify-email 6/3600 s, ai-agent 120/3600 s, ai/assist 60/3600 s. |
| **Audit events** | `src/python/server.py::write_audit_event` (line 1376) + `audit_events` table (schema line 1137) | Hash-chained (`previous_hash` + `event_hash`). Immutability triggers (lines 1206–1207 — `BEFORE UPDATE/DELETE → RAISE ABORT 'audit events are immutable'`). Retention `EINVITE_AUDIT_RETENTION_DAYS` (30–3650, default 730). Surfaced via `GET /api/account/audit` (line 3029, last 200/user) + admin overview. |
| **Malware scanning** | `src/python/security_scanner_v54.py` | ClamAV INSTREAM over UDS/TCP on Linux; `MpCmdRun.exe -Scan -ScanType 3` on Windows; 60 s timeout; `MalwareDetected` → HTTP 422; `startup_preflight` fail-closed. |
| **Auto-secret generation** | `src/python/secrets_v54.py::ensure_secret` | Generates `EINVITE_SECRET_KEY` + `EINVITE_BILLING_WEBHOOK_SECRET` (`secrets.token_urlsafe(64)`) into repo-root `.env` mode 0600 when missing/placeholder; never overwrites non-placeholder values; refuses length < 32. |
| **HSTS** | `src/python/server.py::end_headers` (line 2442) | `Strict-Transport-Security: max-age=31536000; includeSubDomains` only when `COOKIE_SECURE=1`. |
| **HTTPS enforcement** | `src/python/server.py::guard_request_boundary` (line 2539) | 308 Permanent Redirect to first `ALLOWED_HOSTS` entry when `COOKIE_SECURE=1` and request not TLS and not trusted-proxy `X-Forwarded-Proto: https`. |
| **Host allowlist** | `src/python/server.py::guard_request_boundary` (line 2551) | 421 Misdirected Request when `Host` not in `EINVITE_ALLOWED_HOSTS` (comma/space-separated) AND not a published invitation `custom_domain`. Skip-when-unset preserves dev. |
| **Request framing validation** | `src/python/server.py::guard_request_boundary` (lines 2523–2528) | Rejects non-identity Transfer-Encoding + ambiguous duplicate Content-Length with 400. |
| **Production preflight** | `src/python/production_preflight.py` | Enforces `EINVITE_COOKIE_SECURE`, `EINVITE_ALLOWED_HOSTS`, `EINVITE_REQUIRE_MALWARE_SCAN` in production mode. |
| **Field-level encryption** | `src/python/core/crypto.py` + `src/python/core/db.py` | Fernet key resolution (env → per-data-dir sidecar → ephemeral), `protect()` on the write path and a read wrapper for six columns: `users.email`, `guests.email`, `guests.phone`, `delivery_attempts.recipient`, `audit_events.metadata_json`, `invitation_edit_history.diff_json`. `users.email_hash` is the blind index for sign-in; `encrypt_field` / `decrypt_field` / `hash_for_lookup`, dual-read keeps pre-encryption rows working, and `scripts/migrate_encrypt_sensitive_fields.py` has `--dry-run`, `--rollback` and `--reencrypt`. Default **on**; `EINVITE_FIELD_ENCRYPTION=off` is the stop-switch. Operator path: `docs/ops/FIELD-ENCRYPTION-RUNBOOK.md`. |
| **Scoped API keys** | `src/python/core/auth.py` + `src/python/server.py` | `eik_`-prefixed keys shown once and stored as SHA-256, constant-time compare, route allowlist by scope (`invitations:read`, `invitations:write`, `rsvps:read`; anything else `403 api_key_scope_denied`), per-key `rate_limit(1000/h, EINVITE_API_KEY_RATE_LIMIT)`, `X-API-Key` auth path and `api.request` audit rows with `auth=api_key`. Create/list/revoke routes and the account-security card. |
| **Admin step-up** | `src/python/server.py::require_admin_with_stepup` | 15 destructive admin routes require a live `admin-stepup` grant issued after password + TOTP; the grant lives in a module variable only (no browser storage), the admin shell can obtain it, and Escape dismisses the prompt without replaying the refused request. |

---

## 7. Browser Application Boundaries

The project deliberately remains **build-tool-free**. The editor has been decomposed into focused modules rather than continuing to grow one enhancement file.

### 7.1 Core

- `app.js` — legacy editor state/document orchestration and compatibility layer.
- **Icons — no sprite ships.** `plans/004-ux-ui-and-code-quality-pass.md` UX-4 proposes a single
  inline-SVG sprite at `assets/icons.svg` used through `<use>`; it was never executed. The tree has
  no `assets/icons.svg`, no `<svg>`/`<use>` in `src/html/index.html` or `dashboard.html`, and the
  shell's affordances are text glyphs (the inspector toggle is `▤`) plus CSS-drawn shapes. A doc that
  describes an icon set is ahead of the code; adding one is the UX-4 work order, not a doc change.
- `renderer-core.js` — shared safe object renderer used by editor/public rendering paths.
- `storage.js` — browser persistence boundary.
- `upload-client.js` — shared material-upload boundary; prefers signed browser-direct R2/S3 uploads, falls back to authenticated server uploads for local deployments.
- `tokens.css` / `theme-hardening.css` — canonical application theme tokens and legacy-theme bridge.

### 7.2 Creation Studio modules

- `studio-experience.js` — studio shell, navigation, command palette, design checks.
- `editor-pro.js` — persistent tools, contextual toolbar, direct rich-text editing.
- `editor-builders.js` — visual schedule, venue, and section-order builders.
- `font-browser.js` — searchable/favorite/recent font workflow.
- `photo-editor.js` / `canvas-plus.js` — photo adjustment, local background cut, exact transforms and advanced canvas tools.
- `ai-assistant-pro.js` — invitation-specific AI workflow with backend provider adapter and local fallback.
- `creative-packs.js` — invitation-specific reusable element compositions.
- `collaboration.js` / `collaboration-live.js` — roles, sharing, near-real-time remote-change awareness via SSE (with polling fallback).
- `ui-dialogs.js` — application dialogs/toasts replacing browser `prompt`/`confirm`/`alert` UX.
- `editor-suite.js` / `editor-suite.css` — generated browser runtime bundle for editor-only enhancement modules; source modules remain separate and are rebuilt with `build_editor_bundle.py`.

### 7.3 Management modules

Dashboard, materials, templates, guests, responses, analytics, billing, account, designer, and admin each have isolated page controllers (`dashboard.js`, `materials.js`, `templates.js`, `guests.js`, `responses.js`, `analytics.js`, `billing.js`, `account.js`, `designer.js`, `admin.js`).

### 7.4 Inspector shell (markup-first)

The editor's right aside is a five-tab inspector: `object` (Edit), `layers`, `sections`, `theme`
(Design) and `publish` (Share). The shell ships **in markup**, not in script:
`src/html/index.html` contains the `.v54-inspector-mode` bar with `[data-v54-inspector-toggle]`, the
empty `.studio-inspector-tabs` nav, and `.studio-inspector-host` with the active
`[data-inspector-pane="object"]` section, its heading and the no-selection placeholder.

`studio-experience.js::buildInspector()` therefore only fills the row: it creates one
`[data-inspector-tab]` button per tab and adds any pane a later module contributes. It does not
create the row or the host. This matters for layout rather than tidiness — before OD-23 the row and
host were created at ~1.8 s, which pushed `#canvasViewport` up by 62 px after first paint. Tab
activation (`activateRight(id)`) toggles `.active` on `[data-inspector-pane]` and persists the choice
in `localStorage['einvite-editor-right-tab']`. Pages without the shipped shell fall back to the
legacy path, which wraps existing children into panes by heading.

Modules mount **inside** the shell instead of adding tabs: `typography-editor.js` owns
`#typographyControls` in the Edit pane, and `properties` / `noSelection` are the object pane's own
containers.

### 7.5 Bilingual pipeline (map-driven)

One resolver plus declarative maps — there is no per-page language code.

- **Resolver.** `src/js/core/i18n.js` is listed in `earlyScripts` and runs synchronously in `<head>`,
  so `<html lang>` is correct before first paint (no flash of both languages). `<html lang>` is the
  source of truth; the choice persists in `localStorage['einvite-lang']`; a first visit follows
  `navigator.language` (`km…` → Khmer, otherwise English). API: `EInviteI18n.get()/set()/t()/
  langText()/subscribe()`, with `EInviteI18N.getLocale()` kept as an alias for the page modules that
  already call it. A change dispatches `einvite:lang-changed` on `<html>` for surfaces that re-render.
- **Markup maps.** Pairs live in the DOM as `data-en` / `data-km` attributes (the resolver sets
  `placeholder` and `aria-label` from them) and as sibling `.i18n-en` / `.i18n-km` elements toggled
  by CSS, so switching language needs no re-render. `src/js/core/khmer-format.js` owns Khmer digits
  and dates; Khmer numerals are always produced from code points, never typed literally.
- **String tables.** Module tables use either shape — per-key `{key: {en, km}}` or per-locale
  `{en: {…}, km: {…}}`. `scripts/check-bilingual-consistency.py` walks `src/js/*.js` (skipping
  generated `bundle-*.js`) and **fails** when an `en` string has no `km` counterpart; byte-identical
  pairs are reported as `fallback` and listed in `docs/i18n/TRANSLATIONS.csv` for the translation
  pass. New Khmer text is applied from `docs/i18n/KHMER-TRANSLATION-MAP-*.md` by script (paste, never
  generate) and every applied string is tracked in `docs/i18n/KHMER-REVIEW-QUEUE.md` pending native
  review.

### 7.6 Template-pack loader (36 Khmer event templates)

The pack is data, not code in a bundle. `src/js/template-pack-loader.js` is loaded on demand by the
Template Studio and fetches:

```text
/assets/template-pack/catalog.js      the 36-entry catalogue
/assets/template-pack/built/<id>.js   one template's native document
```

Both are **ES modules rather than JSON**: the server's static whitelist refuses every `.json`
(a disclosure fix), and a new API route would add a server surface for assets that are already
cacheable. Nothing in the pack is imported by `index.html`, so the editor's two script bundles and
`editor-suite.js` do not change when the pack grows (TP-OD-4, measured: the editor page assets and
the editor bundle stay byte-identical with and without the pack). The loader caches the catalogue
promise and one document promise per id, validates catalogue shape (`count === templates.length`),
and restricts ids to `^[a-z0-9-]+$`.

`src/js/template-pack-gallery.js` renders the pack as its own section above the Template Studio grid
and hands a chosen built document to `templates.js` through a custom event, so the existing
create-from-document flow stays in one place. `docs/ASSETS.md` owns the asset/hash inventory for the
ornaments and thumbnails.

---

## 8. Rendering

`renderer-core.js` owns the shared object-level rendering contract: safe rich text, dimensions, filters, transforms, shape fills and animation styles. Both editor-generated preview markup and the public renderer (`advanced-public-renderer.js`) delegate artistic object rendering to it.

**Print/PDF** (`src/js/export-quality.js`) rasterises the stage and prints through a dedicated
`body.print-doc` document. That class exists for two measured reasons: the app's
`body:not(.guest) p:not(#stage *)` rule otherwise repaints printed paragraphs in the muted UI ink
instead of the document ink, and the live `.reveal` markup otherwise replays its 900 ms entrance so
`pdf()` can snapshot a half-faded page. Print pages take `{bleedMm, cropMarks}` — page = trim +
2 × bleed (0/3/5 mm exposed in the export dialog), backgrounds continue through the bleed, the trim
stays pixel-identical and eight vector ticks sit outside it.

**Draft version snapshots** (`src/python/features/invitation_versions.py`, wired in by D-7
2026-10-29) run inside the server-side draft save: one snapshot when the canonical content hash
changed **and** at least five minutes passed since the last auto snapshot, 50 kept with the oldest
pruned, documents above 2 MB skipped with one log line. Rows join the publication list as `isAuto`
and restore through the existing restore-as-draft endpoint.

---

## 9. Future Direction

Phase 1+ of `docs/ROADMAP.md` will introduce:

- **Complete the staged resource-scoped permission rollout** — extend `TOOL_REQUIRED_GRANTS` beyond the current 9 mapped tools while retaining the legacy tier fallback only for tools that have not yet migrated. Resource-scoped matching is already authoritative for mapped tools.
- **Continue JIT elevation hardening** — the short-lived, one-shot grant lifecycle is implemented for 13 tools; expand coverage only with matching tool-specific policy and regression tests.
- **Agent-security dashboard** — anomaly detection on tool-invocation patterns.
- **ASVS L2 self-assessment** — gap analysis across all 14 chapters.
- **pgBackRest + PITR** — continuous WAL archiving for PostgreSQL.
- **Guest features** — sign-up sheets, polls, shared photo album, post-send editing, multi-channel delivery (Phase 2a).
- **Y.js CRDT upgrade** — replace the custom V31 CRDT engine with Y.js + y-indexeddb + per-user `UndoManager` (Phase 4b).
- **Plugin sandbox** — cross-origin iframe + MessageChannel for UI plugins, WASM isolation for logic plugins (Phase 4a).

---

## 10. QA Deep-Dive Hardening (2026-11-08)

This section records behavior added or proven on `qa/deep-dive-improvements`. It does not
change the public API.

### 10.1 CSP nonce lifecycle

`Handler.__init__` creates `self.csp_nonce` with `secrets.token_urlsafe(16)` for every
response. `csp_header()` embeds it as `style-src 'self' 'nonce-…'`, server-rendered `<style>`
tags receive the same value, and `end_headers()` emits the policy. Pages without inline styles
or scripts (for example `dashboard.html`) expose the nonce only through the response header.
The Playwright visual harness therefore reads the nonce from the navigation response's
`Content-Security-Policy` header; copying `script[nonce]` does not work on those pages, and a
second HTTP request would receive a different nonce.

### 10.2 Static delivery and cache policy

`Handler.static_cache_policy()` is applied by both `do_GET` and `do_HEAD` after
`public_static_path()` approves the request:

| Path class | Header |
|---|---|
| `/assets/template-pack/…` (content-addressed artwork) | `public, max-age=86400` |
| Root bundles, `/assets/`, `/vendor/`, `/core/`, `/licenses/` | `public, max-age=3600, must-revalidate` |
| API responses | unchanged `no-store` |

`SimpleHTTPRequestHandler.send_head()` still emits `Last-Modified`, so the one-hour policy
supports conditional revalidation rather than forcing a full download.

### 10.3 Session lifecycle

Sessions are cookie-first (`HttpOnly`, `SameSite=Lax`, optional `Secure`). Logout deletes the
server-side `sessions` row and clears both the session and CSRF cookies; idle expiry does the
same. Invalid or expired sessions preserve the documented API contract:
`GET /api/auth/me` returns `200 {"user": null}` (never a breaking 401 for that endpoint).
`tests/qa_deep_dive_sessions_test.py` asserts the row deletion, the response contract and the
five-failure/15-minute account lockout under ten rapid invalid logins.

### 10.4 Pagination indexes

Two indexes support dashboard pagination without changing response shapes:

- `idx_invitations_owner_archived_updated(owner_id, archived, updated_at DESC)` — owner list
  and archive filters. `EXPLAIN QUERY PLAN` reports
  `SEARCH invitations USING INDEX idx_invitations_owner_archived_updated (owner_id=? AND archived=?)`.
- `idx_invitation_collaborators_user_invite(user_id, invitation_id)` — collaborator list and
  membership checks; the existing `idx_invitation_collaborators_user` remains in use.

### 10.5 Verification commands

```bash
.venv/bin/python scripts/qa_api_fuzz.py
.venv/bin/python -m pytest tests/qa_deep_dive_sessions_test.py tests/qa_deep_dive_static_cache_test.py -q
npx playwright test --config=e2e/playwright.config.ts --project=chromium e2e/specs/06-a11y.spec.ts
npx playwright test --config=e2e/playwright.config.ts --project=chromium e2e/specs/07-visual.spec.ts
```

Large refactors and deferred optimizations are tracked in `docs/FUTURE-IMPROVEMENTS.md`.

---

*Phase 0.2 deliverable of `docs/ROADMAP.md`. Verified against actual code 2026-10-29 (Stage F); QA hardening section added 2026-11-08.*
