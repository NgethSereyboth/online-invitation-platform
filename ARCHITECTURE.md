# E-invitation-website architecture

## Product model

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

## Browser application boundaries

The project deliberately remains build-tool-free for the current review version, but the editor has been decomposed into focused modules rather than continuing to grow one enhancement file.

### Core

- `app.js` — legacy editor state/document orchestration and compatibility layer.
- `renderer-core.js` — shared safe object renderer used by editor/public rendering paths.
- `storage.js` — browser persistence boundary.
- `upload-client.js` — shared material-upload boundary that prefers signed browser-direct R2/S3 uploads and falls back to authenticated server uploads for local deployments.
- `tokens.css` / `theme-hardening.css` — canonical application theme tokens and legacy-theme bridge.

### Creation Studio modules

- `studio-experience.js` — studio shell, navigation, command palette, design checks.
- `editor-pro.js` — persistent tools, contextual toolbar, direct rich-text editing.
- `editor-builders.js` — visual schedule, venue, and section-order builders.
- `font-browser.js` — searchable/favorite/recent font workflow.
- `photo-editor.js` / `canvas-plus.js` — photo adjustment, local background cut, exact transforms and advanced canvas tools.
- `ai-assistant-pro.js` — invitation-specific AI workflow with backend provider adapter and local fallback.
- `creative-packs.js` — invitation-specific reusable element compositions.
- `collaboration.js` / `collaboration-live.js` — roles, sharing, and near-real-time remote-change awareness through Server-Sent Events (SSE), with polling fallback.
- `ui-dialogs.js` — application dialogs/toasts replacing browser prompt/confirm/alert UX.
- `editor-suite.js` / `editor-suite.css` — generated browser runtime bundle for editor-only enhancement modules; source modules remain separate and are rebuilt with `build_editor_bundle.py`.

### Management modules

Dashboard, materials, templates, guests, responses, analytics, billing, account, designer, and admin each have isolated page controllers.

## Rendering

`renderer-core.js` owns the shared object-level rendering contract: safe rich text, dimensions, filters, transforms, shape fills and animation styles. Both editor-generated preview markup and the public renderer delegate artistic object rendering to it.

Structured event sections remain specialized components because they contain behavior (RSVP, maps, countdown, guest wishes) rather than being generic canvas objects.

## Persistence

### Local review mode

- Browser storage/IndexedDB for offline editor fallbacks.
- SQLite for server-backed accounts, invitations, publications, guests, RSVP, templates and assets.
- Local disk media under the configured data directory.

### Production adapters

- PostgreSQL runtime by setting `EINVITE_DATABASE_URL` and installing `psycopg`.
- S3-compatible/R2 object storage through `EINVITE_OBJECT_STORAGE_*`, including signed browser-direct uploads with verification/registration on completion and raw server-upload fallback for local deployments.
- Redis distributed rate limits through `EINVITE_REDIS_URL`.
- SMTP verification/reset delivery through `EINVITE_SMTP_*`.
- External AI through `EINVITE_AI_*`.
- Provider-neutral billing checkout/webhooks through `EINVITE_BILLING_*`.

## Publishing contract

Drafts and public invitations are deliberately separated. Publishing validates the complete invitation document and writes an immutable publication snapshot. Later draft edits do not change the guest-facing invitation until a new publication occurs.

## Collaboration contract

Invitation owners can grant registered users viewer, content, designer, or manager access. The current review build uses server authorization plus Server-Sent Events (SSE) for near-real-time remote-change notifications, with polling as a browser/network fallback. It is intentionally not a CRDT: simultaneous conflicting edits are surfaced as a remote-change notification rather than silently merged.

## Security boundary

- Passwords: PBKDF2-HMAC-SHA256 with unique salts.
- Sessions: hashed server-side; production browser flow uses an HttpOnly SameSite cookie, while bearer responses remain available for API/backward-compatibility tests.
- Cookie-authenticated state changes receive same-origin validation.
- Content Security Policy and related browser security headers are sent by the backend.
- File signatures are verified before normal server uploads are accepted.
- Ownership/collaboration permissions are enforced server-side.
- Rate limiting supports Redis with in-process fallback.

## Next architectural migration after product review

The current no-build architecture is intentionally easy to inspect. For a larger engineering team, the natural next migration is to package the existing boundaries as ES modules or a TypeScript monorepo without changing the invitation document contract or backend API surface.
