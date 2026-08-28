# E-invitation Platform V13 — Future Development Report

**Build:** `future-studio-foundation-v13`  
**Date:** 2026-07-24  
**Baseline:** V12 Immediate Stabilization  
**Document schema:** 13

## Scope

V13 continues the existing V12 application in place. It does not replace the framework, renderer, editor, publishing model, Khmer features, materials, music, RSVP, guest management, analytics, collaboration, public renderer, or production adapters. The release implements the future-development roadmap across Phases 7–13 as a compatibility-preserving foundation plus usable product features.

The release deliberately keeps the proven legacy document/rendering path synchronized with the new normalized editor model so older invitations continue to open and publish.

---

## Phase 7 — Account and security hardening

Implemented:

- Argon2id password hashing for new/rehash-capable installations.
- Transparent verification and post-login rehash of legacy PBKDF2 password records.
- Algorithm/version metadata for password records.
- TOTP authenticator MFA setup, enable, disable and MFA login challenge.
- WebAuthn-compatible passkey registration and authentication ceremonies using ES256 verification.
- Active-session list with individual revocation and sign-out-all-devices controls.
- Optional SMTP-backed login/security notifications.
- Production-sensitive email-verification enforcement while retaining local/offline development usability.
- Session-bound double-submit CSRF protection for cookie-authenticated browser mutations.
- Origin validation for browser mutations.
- Script CSP hardened so public executable JavaScript no longer depends on `unsafe-inline`.
- Trusted-proxy allowlisting before honoring forwarding headers.
- Redis-backed distributed rate limiting when Redis is configured, with local fallback.
- Bot-protection abstraction for public/account abuse-sensitive endpoints.
- Tamper-evident chained audit records for important account, publishing, collaboration and administrative operations.
- SQLite immutability triggers for audit records.
- Full account data export, including a media-inclusive archive.
- Delayed account deletion with cancellation before permanent purge.
- Configurable guest-data retention.
- Guest-facing privacy and external-media consent controls.
- Invitation password minimum raised to eight characters.

### Important security boundary

The script CSP no longer allows inline executable scripts. `style-src-attr 'unsafe-inline'` remains because the existing visual editor and renderer still use dynamic inline style attributes for canvas coordinates, transforms and invitation styling. Removing that safely requires a larger renderer/style-property migration.

---

## Phase 8 — Production storage and database architecture

Implemented or extended:

- Existing PostgreSQL, Redis and S3/R2-compatible adapters preserved.
- Tenant/owner-prefixed object keys for new managed uploads.
- Provider-side server encryption headers for S3-compatible storage: KMS when configured, otherwise AES-256 server-side encryption.
- Original assets remain separate from generated responsive derivatives/previews.
- Stored-object metadata and reference tracking remain the authority for physical deletion.
- Background media-job queue and standalone `media_worker.py`.
- Background derivative/social-card warming jobs.
- Per-account bandwidth accounting and quota enforcement hooks.
- Invitation trash/recovery period and permanent purge path.
- Abandoned upload cleanup retained from V12.
- Portable SQLite/database + media backup and restore utility.
- Restore test covers the actual application database, `invites.db`.
- PostgreSQL custom-format backup support through `pg_dump` when a PostgreSQL URL and client tools are supplied.
- PostgreSQL archive verification through `pg_restore --list`.
- PostgreSQL restore support through `pg_restore` when explicitly requested.

Provider-side object versioning, lifecycle rules, managed PostgreSQL PITR, encrypted off-site backup policies, DNS/CDN configuration and KMS policies remain deployment responsibilities. V13 exposes compatible application behavior but does not claim those external systems were configured without credentials/infrastructure.

---

## Phase 9 — Canva-like editor foundation

Added a normalized schema-version-13 editor model around the existing invitation format:

- Stable scene-graph identifiers.
- Page/canvas/object normalization.
- Collision-safe migration when legacy object IDs repeat across pages.
- Schema validation/migration hooks.
- Transactional command bridge for mutations.
- Legacy renderer synchronization for backward compatibility.
- Existing undo/redo retained and integrated with the command layer where new tools use it.
- Cross-page and cross-invitation copy/paste foundation.
- Copy/paste object styles.
- Responsive constraints and breakpoint override metadata.
- Nested group metadata.
- Tidy and layout operations.
- Draggable layer ordering.
- Context-menu and shortcut extensions.
- Reusable document-backed text styles.
- Reusable document-backed color styles.
- Reusable document-backed effect styles.
- Existing multi-select, marquee selection, smart guides, snapping, distribution, frames, masks, lock/hide, layer rename, reusable groups/components, page templates and master-page features preserved.
- Brand-kit integration extended with studio identity.
- Comments, approval requests, version comparison and version restore.
- Collaboration presence indicators and heartbeat state.
- Existing optimistic conflict-safe autosave/revision handling preserved.

### Architecture note

V13 intentionally does not rewrite the full editor into TypeScript or replace the legacy DOM renderer. The normalized scene graph and command bridge are migration infrastructure that allow future modules to move off direct DOM mutation incrementally without breaking existing invitations.

---

## Phase 10 — Photoshop-like non-destructive editing foundation

Implemented or extended:

- Original upload preservation.
- Separate editing-operation state.
- Generated preview/export separation.
- Existing crop, rotation and basic filter workflows preserved.
- Advanced brightness/contrast/saturation/vibrance/temperature/hue controls.
- Gamma, shadow/highlight shaping and levels processing.
- Sharpen processing.
- Worker-backed histogram generation.
- Worker-backed PNG/WebP export processing.
- Before/after comparison.
- Perspective, rotate-X/Y and skew/warp transform controls.
- Mask feather and gradient-mask metadata.
- Ordered reversible adjustment layers.
- Adjustment-layer enable/disable, tuning and reordering.
- Smart-source promotion and source restoration.
- Connected-area Magic Erase.
- Brush erase.
- Clone stamp with Alt source selection.
- Heal/blend brush.
- Local retouch undo/reset.
- Generated retouch preview saved as a new material while preserving the original.
- Existing frame/mask/blend/effect capabilities retained.
- Existing local automatic background-removal capability retained.

### Non-destructive editing limits

This is a substantial browser-based non-destructive editing foundation, not complete Adobe Photoshop parity. It does not provide arbitrary-point professional curves, PSD-compatible nested smart-object documents, full semantic AI object selection, or a complete Photoshop clipping-layer model.

---

## Phase 11 — Animation and timeline

Implemented:

- Per-object animation tracks.
- Keyframes for position, scale, rotation and opacity.
- Entrance, emphasis, continuous and exit presets.
- Delay and duration controls.
- Standard and custom cubic-bezier easing.
- Staggering.
- Timeline scrubbing.
- Section markers.
- Audio synchronization offset.
- Copy/paste motion.
- Reusable motion presets.
- Selectable editor play range.
- Timeline playback waits for the guest opening interaction when an opening scene is enabled.
- Reduced-motion-safe public behavior.
- Performance warning tooling.
- Motion JSON export.

MP4/GIF rendering/export is not included in V13. Implementing reliable client/server video rendering would add a separate encoding pipeline and is not represented as complete.

---

## Phase 12 — Invitation-specific product features

Implemented or extended:

- Multiple ceremonies/events in one invitation.
- Invitation timezone metadata.
- Per-event calendar download.
- Map/directions actions.
- Guest groups and household metadata.
- Guest segmentation tags.
- Table and seat assignment metadata.
- Scheduled delivery-campaign abstraction for email, SMS, Telegram and WhatsApp.
- Delivery records/status plumbing without pretending unavailable providers sent messages.
- Scheduled publication.
- Scheduled unpublishing/expiration.
- Custom-domain lifecycle metadata.
- Protected photo galleries with underlying media authorization.
- Gift-registry link blocks.
- Separate payment/contribution link blocks.
- Dress-code information.
- Accommodation information.
- Transport information.
- Guest-facing analytics/external-media consent.
- Comments and designer/customer approval workflow.
- Publication version comparison and restore-to-draft workflow.
- White-label studio profile and public studio identity.
- Studio identity import into invitation Brand Kits.
- Marketplace licensing levels and optional moderation.
- Authenticated event-day check-in page.
- Offline-capable service-worker/PWA check-in queue.
- Reconnect synchronization.
- Duplicate check-in warning while preserving the first check-in timestamp.
- Optional on-device QR scanning through `BarcodeDetector` when the browser supports it.

### Provider boundaries

Real message delivery, custom DNS/TLS, payment processing and external provider webhooks require deployment credentials and provider configuration. The local application uses safe preview/fallback behavior rather than reporting simulated sends as real delivery.

---

## Phase 13 — Testing and quality

The cross-platform test foundation was retained and expanded:

- Every audited Python `Path.read_text()` / `Path.write_text()` call explicitly specifies UTF-8.
- Test processes use isolated temporary data directories.
- Dependency preflight checks Pillow, qrcode, Argon2 and cryptography with useful messages.
- Browser-heavy tests run sequentially in the review runner to reduce Chromium contention on ordinary Windows PCs.
- Existing V9–V12 compatibility suites remain in the matrix.
- New V13 tests cover account security, privacy lifecycle, editor normalization, backup/restore, product lifecycle and browser runtime.

### Final deterministic test result

All **32 fast deterministic/backend/security tests passed together** after the final code changes.

The passing matrix includes:

- Build integrity.
- V10 compatibility.
- V11 media compatibility.
- V12 storage/privacy, routing, media-source and stabilization checks.
- V13 future foundation.
- V13 account security.
- V13 editor-model migration and globally unique scene IDs.
- V13 backup/restore.
- V13 product lifecycle.
- V13 privacy lifecycle.
- Static integrity.
- Core smoke tests.
- Plan limits.
- Production foundations.
- Provider adapters.
- Realtime storage.
- Signed uploads.
- Security regression and maintenance.
- Private invitation access.
- Collaboration permissions and revisions.
- Existing workflow/editor regression suites.

### Final Chromium result

The following browser suites passed individually:

- `inline_editor_runtime_test.py`
- `v10_browser_runtime_test.py`
- `v11_browser_runtime_test.py`
- `v12_browser_stabilization_test.py`
- `v13_browser_runtime_test.py`
- `editor_layout_geometry_test.py`
- `public_layout_runtime_test.py`
- `public_guest_feature_runtime_test.py`
- `theme_launcher_runtime_test.py`

The final visual pass additionally found and corrected two issues:

1. The privacy-consent banner lived outside the guest language container and could show English and Khmer simultaneously. It now follows the selected guest language.
2. Mobile timeline/studio launch controls could cover an open creation panel. Canvas launch controls now yield while that panel is expanded.

Affected browser suites were rerun after these fixes and passed.

The combined release wrapper still exceeds the hosted command-duration limit after it enters the sequential Chromium phase. This is an execution-host limit, not a test assertion failure. Every browser suite listed above was run individually to completion.

---

## Local server verification

The final V13 working tree was started with a fresh isolated data directory.

Verified HTTP 200 responses:

- `/api/health`
- `/dashboard.html`
- `/index.html`
- `/privacy.html`
- `/checkin.html`
- `/templates.html`

The health response detected the configured local SQLite/local-storage mode and optional dependency availability without requiring production credentials.

---

## Fully implemented and tested in this release

- Argon2id migration path and legacy PBKDF2 rehash.
- TOTP MFA flows.
- Session listing and revocation.
- Browser CSRF protection.
- Audit records.
- Account export/deletion lifecycle.
- Privacy/retention lifecycle.
- Invitation trash/restore.
- Normalized scene graph migration and command bridge.
- Shared styles.
- Advanced non-destructive image adjustments and local retouch tools.
- Smart-source preservation.
- Timeline/keyframes/play ranges.
- Multi-event/timezone invitation journey.
- Guest grouping/seating metadata.
- Protected gallery authorization.
- Campaign/scheduling abstractions.
- Comments/approval/version restore.
- White-label studio and marketplace licensing/moderation foundations.
- Offline-capable check-in queue and duplicate warning.
- Local SQLite/media backup and tested restore.
- Desktop/mobile editor and public browser regression coverage.

---

## Implemented but requiring a real production environment for complete verification

- Hardware-authenticator/passkey completion on real devices and browsers.
- Live SMTP security notifications.
- Managed PostgreSQL behavior under real production load.
- PostgreSQL `pg_dump`/`pg_restore` against a real remote database.
- Redis distributed rate limiting/presence under a real Redis service.
- Private R2/S3 storage with real bucket policies/KMS.
- CDN signed cookies/URLs beyond the built-in first-party signed-media gateway.
- Managed database PITR.
- Object-storage versioning and lifecycle policies.
- Off-site backup scheduling and production restore drills.
- Real email/SMS/Telegram/WhatsApp delivery providers.
- Custom-domain DNS and TLS provisioning.
- Billing/payment-provider operation.
- External AI provider operation.

No real credentials are included in the project.

---

## Remaining technical limitations

- Collaboration has presence plus optimistic revision/conflict protection, but not CRDT/OT simultaneous character-level merge.
- The normalized editor model coexists with the legacy renderer; this is a staged migration rather than a full renderer rewrite.
- The source remains JavaScript rather than a mandatory TypeScript build because the no-build local development requirement was preserved.
- `style-src-attr 'unsafe-inline'` remains necessary for existing dynamic canvas/public style attributes.
- Non-destructive image editing is not full Photoshop parity.
- Timeline video/GIF rendering export is not implemented.
- QR camera scanning depends on browser `BarcodeDetector` and camera support.
- Provider-backed operations cannot be honestly certified without the corresponding accounts, credentials and infrastructure.

---

## Files added in V13

- `account-page-v13.css`
- `account-security-v13.css`
- `account-security-v13.js`
- `admin-page-v13.css`
- `analytics-page-v13.css`
- `backup_restore.py`
- `billing-page-v13.css`
- `checkin-v13.css`
- `checkin-v13.js`
- `checkin.html`
- `dashboard-page-v13.css`
- `designer-page-v13.css`
- `editor-canva-v13.css`
- `editor-canva-v13.js`
- `editor-commands-v13.js`
- `editor-schema-v13.js`
- `editor-shared-styles-v13.css`
- `editor-shared-styles-v13.js`
- `guests-page-v13.css`
- `manifest.webmanifest`
- `materials-page-v13.css`
- `media_worker.py`
- `photo-editor-v13.css`
- `photo-editor-v13.js`
- `photo-retouch-v13.css`
- `photo-retouch-v13.js`
- `photo-worker-v13.js`
- `privacy-v13.css`
- `privacy.html`
- `product-operations-v13.css`
- `product-operations-v13.js`
- `public-page.js`
- `reset-page-v13.css`
- `responses-page-v13.css`
- `security_v13.py`
- `service-worker.js`
- `templates-page-v13.css`
- `timeline-runtime-v13.js`
- `timeline-v13.css`
- `timeline-v13.js`
- `verify-page-v13.css`
- `tests/v13_account_security_test.py`
- `tests/v13_backup_restore_test.py`
- `tests/v13_browser_runtime_test.py`
- `tests/v13_editor_model_test.py`
- `tests/v13_future_foundation_test.py`
- `tests/v13_privacy_lifecycle_test.py`
- `tests/v13_product_lifecycle_test.py`
- `V13_FUTURE_DEVELOPMENT_REPORT_2026-07-24.md`

## Existing files changed in V13

- `BUILD_INFO.json`
- `account.html`
- `admin.html`
- `analytics.html`
- `app.js`
- `billing.html`
- `collaboration-live.css`
- `collaboration-live.js`
- `dashboard.html`
- `dashboard.js`
- `dependency_preflight.py`
- `designer.html`
- `editor-suite.css`
- `experience-schema.js`
- `guest-layouts.css`
- `guests.html`
- `guests.js`
- `index.html`
- `invitation-context.js`
- `materials.html`
- `postgres_schema.sql`
- `public.html`
- `release_check.py`
- `renderer-core.js`
- `requirements-production.txt`
- `requirements-test.txt`
- `reset.html`
- `responses.html`
- `run_review_checks.py`
- `server.py`
- `style-kits.css`
- `templates.html`
- `templates.js`
- `theme-init.js`
- `verify.html`
- Several inherited regression tests were updated only where the public runtime moved to CSP-safe external JavaScript or where the current schema version is now 13.

No V12 project files were intentionally removed.
