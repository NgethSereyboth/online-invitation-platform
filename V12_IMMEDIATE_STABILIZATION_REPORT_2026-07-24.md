# V12 Immediate Stabilization Report — 2026-07-24

## Scope

V12 continues the existing V11 codebase and implements the requested immediate stabilization release covering Phases 1–6 only:

1. Critical data, storage and private-media fixes
2. Invitation-specific routing and page context
3. Confirmed UI, first-use and accessibility fixes
4. Music, YouTube and external-media experience
5. RSVP-optional behavior and response safety
6. QR, personalized sharing and social-card reliability

The project architecture, framework choices, invitation editor, templates, Khmer features, publishing workflow, materials, music, guest management, collaboration and analytics remain in place. The invitation document remains backward compatible.

---

## 1. Critical data and storage fixes

### Reference-safe physical storage

A `stored_objects` layer now separates a physical stored object from the logical asset rows that reference it. Identical files can still be deduplicated, but deleting one invitation or one material no longer deletes the physical object while another asset references it.

Invitation deletion and individual material deletion now use the same reference-safe release logic. Final physical deletion occurs only after the last logical reference has been removed.

Regression coverage verifies the complete lifecycle: the same file referenced by two invitations survives deletion of one invitation and is physically removed only after the final reference is deleted.

### Private invitation media

Material delivery is now authorization aware. The first-party media gateway evaluates the invitation/publication context instead of treating all uploaded files as permanently public static assets.

Protected invitation documents receive short-lived signed first-party media URLs. Direct access to protected original or responsive derivative media without authorization is rejected. Public delivery is limited to media intentionally referenced by a current non-password-protected publication.

Social-card generation continues to use generic protected-invitation metadata and does not reveal protected event details or private photos.

### Hardened responsive derivatives

Responsive image generation now uses bounded variant rules:

- Width allowlist: 320, 480, 768, 960, 1440 and 1920
- Limited output-format allowlist
- Source dimension and megapixel limits
- Pillow decompression-bomb handling
- Derivative-generation rate limits
- Cache file/byte quotas with eviction
- ETag and Last-Modified support
- Common derivative pre-generation where practical

Invalid widths, unsupported formats, invalid image signatures and oversized image payloads are covered by regression tests.

### Upload processing

The upload pipeline now supports:

- Quarantine state before acceptance
- File-signature and MIME verification
- SHA-based checksums and physical-file deduplication
- Optional malware-scanner command abstraction
- Image metadata extraction
- EXIF orientation handling
- Configurable derivative EXIF privacy stripping
- Failed/incomplete upload cleanup
- Resumable upload sessions
- Progress reporting
- Cancellation and retry
- Original-file preservation
- User-facing failure messages

Direct object-storage completion validates and registers the object that was already uploaded instead of performing an unnecessary second upload.

---

## 2. Invitation-specific routing and data context

Management pages now support invitation-specific paths:

- `/invitations/{id}/editor`
- `/invitations/{id}/guests`
- `/invitations/{id}/responses`
- `/invitations/{id}/analytics`
- `/invitations/{id}/materials`

The active invitation is derived from the current URL. The remembered browser value is retained only as a convenience fallback and is no longer authoritative.

Cross-page management links are rewritten to preserve the current invitation ID. Direct management-route requests are validated server-side before the protected page is returned.

Deterministic regression coverage confirms that two simulated tabs using different invitation URLs remain bound to their own invitation records even when a remembered local value points to another invitation.

---

## 3. UI, first-use and accessibility fixes

### Dashboard first-use state

The no-invitations experience now uses application-level theme surface and foreground tokens rather than ambiguous inherited colors. The empty state was visually checked in dark mode after an initial real-browser review exposed insufficient contrast.

### Built-in template discovery

Template Studio now contains built-in invitation templates for first-time accounts in addition to personal and marketplace sources. New users no longer reach an empty template screen when recommended templates are available.

### Editor overlay scoping

Canvas-only experience, focus and quick-edit controls are hidden when the user enters non-canvas Event, Blocks or media workflows, reducing form obstruction on desktop and mobile.

### Guest language semantics

The public invitation language switch now updates:

- `document.documentElement.lang`
- English/Khmer root classes and language state
- Khmer font treatment
- Accessible control names and pressed state
- Per-invitation guest language preference

### Accessibility hardening

V12 adds or strengthens:

- Visible focus indicators
- Approximate 44×44 minimum interactive targets
- Dialog focus trapping and restoration
- Escape-to-close behavior
- Hidden/inert/ARIA synchronization for closed drawers and dialogs
- Accessible labels for icon-only controls
- Lunar-date selector accessible names
- Image alt fallbacks
- Nested anchor/button cleanup
- Reduced-motion behavior

A full independent screen-reader certification is outside the automated environment, but the DOM and keyboard behaviors above are regression-tested where practical.

---

## 4. Music, YouTube and external media

The editor now has an explicit background-media source model:

- None
- Uploaded audio
- YouTube
- SoundCloud through the official embed path

Playback options include:

- Enable background music
- Start after invitation opening interaction
- Loop
- Volume
- Fade-in preference
- Show/hide guest music control

YouTube supports standard `youtube.com`, `music.youtube.com`, `m.youtube.com`, `youtu.be`, Shorts and embed URL forms. Valid YouTube input automatically selects the YouTube source. YouTube embeds use the privacy-enhanced `youtube-nocookie.com` domain.

Visible video and background-audio use separate players. Background-only mode does not show a large player. No arbitrary iframe domain is accepted.

The guest control starts in the truthful “Play music” state. Music begins only after guest interaction; browser-blocked pre-interaction autoplay is not attempted.

SoundCloud support is restricted to its official embed path. Third-party owner restrictions or provider outages cannot be guaranteed by local testing and are handled as external availability conditions.

---

## 5. RSVP-optional experience

RSVP remains optional and invitation-only mode remains a first-class path.

When RSVP is disabled:

- The public RSVP form is absent
- The editor clearly indicates invitation-only mode
- Dashboard/analytics avoid presenting empty RSVP statistics as if responses were expected
- Guest wishes remain independently configurable
- Historical RSVP data is preserved

When RSVP is enabled, V12 adds:

- Personalized-response update semantics
- Duplicate-response reduction
- RSVP closing date
- Maximum guest count
- Optional meal, transport and accommodation questions
- Existing custom-question preservation
- RSVP and wish rate limiting
- Honeypot abuse checks

A personalized guest updates the prior response associated with that guest instead of creating an additional duplicate row.

---

## 6. QR, guest-link and social-sharing reliability

### QR dependency handling

`qrcode` and Pillow are included in the relevant dependency definitions, and `dependency_preflight.py` provides an explicit startup/test preflight with useful status output.

QR generation failures return a clear server response. Share and guest interfaces hide or replace failed QR images/actions rather than leaving broken image elements.

Regression tests cover:

- Public invitation QR
- Personalized guest QR
- Branded QR card
- Revoked personalized-link behavior

### Personalized guest-link security

New personalized guest credentials are hash-backed in storage with version/salt metadata. The system supports:

- Token rotation
- Revocation
- Optional expiry
- Copy personal link
- Download personalized QR

General public sharing strips personalized guest and password-access parameters.

Legacy token data is migrated in a backward-compatible manner where possible. Request logging continues to redact sensitive guest/access/token query parameters.

### Social cards

Generated social cards are cached internally by invitation/publication version and card format. Publishing triggers background cache warming where practical.

Supported card shapes remain:

- Landscape / Open Graph
- Square
- Story

Protected invitations continue to receive safe generic social metadata rather than private names, images or event details.

---

## Invitation/document compatibility

The invitation-document schema remains compatible with V9–V11 documents. New media-source and RSVP settings receive safe runtime defaults through the existing schema migration layer.

V12 adds relational/storage metadata and database migrations for stored objects, upload sessions, RSVP update fields and personalized-token security. Existing invitation content, page order, style kits, opening scenes, Khmer content, publishing snapshots, guest wishes and RSVP history are preserved.

---

## New files

- `accessibility-v12.css`
- `builtin-templates.js`
- `dependency_preflight.py`
- `invitation-context.js`
- `tests/v12_browser_stabilization_test.py`
- `tests/v12_immediate_stabilization_test.py`
- `tests/v12_media_source_test.py`
- `tests/v12_routing_context_test.py`
- `tests/v12_storage_privacy_test.py`
- `V12_IMMEDIATE_STABILIZATION_REPORT_2026-07-24.md`

## Main changed files

- `BUILD_INFO.json`
- `accessibility-polish.js`
- `analytics.html`
- `analytics.js`
- `app.js`
- `canvas-plus.js`
- `collaboration-live.js`
- `collaboration.js`
- `dashboard-empty-state.css`
- `dashboard.html`
- `dashboard.js`
- `editor-suite.js`
- `experience-schema.js`
- `final-polish.js`
- `guest-layouts.css`
- `guests.html`
- `guests.js`
- `index.html`
- `materials.html`
- `materials.js`
- `postgres_schema.sql`
- `public-share-panel.js`
- `public.html`
- `release_check.py`
- `renderer-core.js`
- `requirements-test.txt`
- `responses.html`
- `responses.js`
- `run_review_checks.py`
- `server.py`
- `social-card.css`
- `social-card.js`
- `style-kits.css`
- `templates.html`
- `templates.js`
- `upload-client.js`
- selected inherited regression tests updated to use valid image fixtures and the protected first-party media architecture

---

## Test results

### Combined deterministic/backend/security review

All 26 configured fast checks passed together:

- Build integrity
- V10 experience compatibility
- V11 media compatibility
- V12 storage/privacy
- V12 immediate stabilization
- V12 routing context
- V12 media-source parsing
- Static integrity
- Smoke tests
- Plan limits
- Final features
- Production foundations
- Provider adapters
- Realtime storage
- Signed-upload backend
- Final visual polish
- UX/AI V5
- Pro Editor V6
- Workflow continuity
- Final workflow audit V7
- Security regression
- Security maintenance
- Private-access headers
- Collaboration asset permissions
- Optimistic revisions
- Collaboration revisions

### Browser/Chromium tests

Passed individually after the final changes:

- `inline_editor_runtime_test.py`
- `v10_browser_runtime_test.py`
- `v11_browser_runtime_test.py`
- `v12_browser_stabilization_test.py`
- `editor_layout_geometry_test.py`
- `public_layout_runtime_test.py`
- `public_guest_feature_runtime_test.py`
- `theme_launcher_runtime_test.py`

Browser checks include desktop/mobile editor behavior, required responsive geometry, public layouts, guest personalization, dark/light theme behavior, V10/V11 compatibility and V12 stabilization scenarios. No test-reported console/page errors remain.

### Build and dependency checks

Passed:

- Deterministic editor-bundle check
- Python compilation
- Top-level JavaScript syntax validation
- UTF-8 `Path.read_text()` / `Path.write_text()` audit
- Pillow dependency preflight
- qrcode dependency preflight

### Local server check

The server was started against an isolated temporary data directory. The health endpoint and main HTML entry points returned HTTP 200 successfully.

The execution environment blocks browser automation from navigating directly to localhost/file/data URLs with `ERR_BLOCKED_BY_ADMINISTRATOR`. Therefore visual browser checks used real Chromium with the actual project HTML/CSS/JavaScript loaded through the existing test harness and mocked API payloads, while local HTTP routes and invitation routing were verified separately through server requests and deterministic tests. This limitation is environmental and is not presented as a full end-to-end browser-navigation test.

---

## Fully implemented and tested in V12

- Reference-safe shared material deletion
- Protected invitation media gateway and signed media delivery
- Bounded responsive derivative generation and cache safety
- Upload quarantine/validation/checksum/metadata/resumable workflow
- Invitation-specific management routing and cross-tab context isolation
- Dark-mode empty-state repair
- Built-in template discovery for first-time accounts
- Canvas-overlay scoping
- Guest language semantics and major accessibility cleanup
- Explicit uploaded-audio / YouTube / SoundCloud source model
- RSVP-disabled invitation-only behavior with preserved history
- Personalized RSVP update handling and standard optional questions
- RSVP/wish abuse controls
- QR dependency preflight and graceful failure behavior
- Hash-backed personalized guest credentials with rotation/revocation/expiry support
- Publication-version social-card caching

## Implemented but requiring production credentials or services for live verification

- Real managed PostgreSQL deployment
- Real Cloudflare R2 / Amazon S3 / compatible private-bucket credentials
- CDN signed-cookie/signed-URL integration beyond the built-in first-party signed media gateway
- Optional external malware-scanner executable/service
- Real Redis-backed distributed rate limiting (the current immediate-release protections remain process/local; distributed production rate limiting belongs to the next security phase)
- Real third-party YouTube/SoundCloud availability and owner embed permissions

Provider adapters and deterministic local tests remain in place, but unprovided external credentials were not fabricated or claimed as live.

## Planned, not implemented in this immediate release

The user explicitly requested stabilization Phases 1–6 first. The deeper roadmap remains future work and was not represented as complete:

- Phase 7: Argon2id/password migration, passkeys, TOTP MFA, session management UI, advanced CSRF/CSP/trusted-proxy/audit/privacy lifecycle work
- Phase 8: full managed production-storage/database/backup architecture and tested disaster recovery
- Phase 9: normalized Canva-like scene graph and command architecture
- Phase 10: deeper non-destructive Photoshop-like image editing
- Phase 11: full animation/keyframe timeline
- Phase 12: later invitation-specific operational product features
- Phase 13: broader cross-platform/security/backup quality expansion beyond the immediate V12 tests

---

## Remaining limitations

1. A full screen-reader/manual assistive-technology certification was not available in the automated environment; keyboard/ARIA/focus behaviors were tested programmatically and visually where practical.
2. True cross-tab browser navigation to the local server could not be automated because localhost navigation is blocked by the execution environment. URL-context selection and route authorization are covered independently by deterministic tests and direct HTTP checks.
3. SoundCloud and YouTube embeds can still be rejected by the remote content owner or provider; the application can preserve layout and report external-media availability but cannot override third-party embed policy.
4. Malware scanning is an abstraction until a scanner command/service is configured in the deployment environment.
5. Phases 7–13 intentionally remain outside this immediate stabilization release.
