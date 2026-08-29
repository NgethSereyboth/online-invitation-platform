# V15 Integration Hardening Report

**Product:** E-invitation-website  
**Release:** integration-hardened-v15  
**Date:** 2026-07-25  
**Baseline:** e-invitation-platform-stabilized-v14.zip

## Purpose

V15 is a defect-reduction and integration release. It preserves the V14 invitation editor, Khmer date and multilingual support, media, publishing, optional RSVP, guest management, analytics, templates, timeline, privacy, check-in and account-security capabilities. It does not introduce another large product phase and does not change the invitation schema version (still 13).

## Implemented hardening

### Deterministic route bundles

All original source modules remain editable and authoritative. V15 generates page-specific JavaScript and stylesheet bundles in their exact prior order, reducing independent network/startup layers without deleting compatibility code.

Request-count changes:

- Editor: **42 scripts / 30 stylesheets → 3 scripts / 1 stylesheet**
- Public invitation: **9 source modules / 4 stylesheets → 1 script / 1 stylesheet**
- Dashboard: **11 source modules / 13 stylesheets → 3 scripts / 1 stylesheet**
- Other management pages: route-specific bundles with no duplicate source initialization

The bundle specification, generated hashes and page asset manifest are deterministic. Generated files are written atomically, so interrupted local builds cannot leave partial JavaScript, CSS or manifest files.

### Local and production build behavior

`server.py` checks the editor bundle, route bundles and page manifest at startup.

- Local mode regenerates stale generated assets automatically.
- Production mode remains immutable and fails startup with a useful stale-build error.
- Normal no-build local development remains available.

### Restricted-browser storage fallback

The material repository no longer assumes IndexedDB is always usable. Denied, blocked, unavailable or failed IndexedDB operations now fall back to a session-memory repository instead of preventing editor startup. Persistent storage resumes normally where IndexedDB is allowed.

### Collaboration lifecycle

- Presence now returns the complete current presence list from the heartbeat response.
- The former additional presence-list polling request is removed.
- Redis/in-process presence is deduplicated and stale entries expire.
- Requests use abort controllers and stop on real page unload.
- SSE fallback/retry remains available.
- Existing optimistic revision/conflict behavior remains unchanged.

### Public guest reliability

- RSVP and wish forms prevent repeated submissions while a request is active.
- Recoverable network/server failures preserve the guest's entered information and expose an accessible status message.
- Buttons are restored after recoverable failure.
- Public JSON remains no-cache through the existing server policy.
- Countdown timers stop at zero and replace earlier timers rather than stacking.

### Editor lifecycle cleanup

- Guest-preview countdowns replace and clear earlier timers.
- Structure-builder polling is registered with the shared lifecycle.
- Audio/video pause and timers/network controllers are cleaned on real unload.
- Back/forward-cache navigation is preserved: a persisted `pagehide` no longer permanently closes the lifecycle registry.

### Check-in service worker scope

The service worker now caches only the event check-in shell and its required static assets. It does not intercept APIs or cache dashboard, account or unrelated invitation-management pages. Check-in navigation and assets use network-first behavior so updated bundles refresh when online.

### Server and test-process shutdown

- The HTTP server uses reusable addresses, daemon request threads and bounded shutdown polling.
- SIGTERM/SIGINT initiate graceful shutdown.
- Storage-deletion jobs receive a final processing pass.
- The deterministic test gate defaults to sequential execution for predictable SQLite/process cleanup on Windows. Higher concurrency remains an explicit development option.

### Honest asset accounting

The page-budget generator now counts root-relative files correctly. Previous accounting could report public assets as zero bytes. V15 stores accurate raw asset totals and route budgets.

## Schema and document compatibility

- Invitation document schema remains **13**.
- No migration is required for existing V9–V14 invitation documents.
- Database tables and publishing snapshots are unchanged by this release.
- Existing page/object ordering, Khmer data, RSVP history, guest links and protected-media references remain compatible.

## Exact verification performed

### Deterministic/backend/security matrix

Command:

```text
python run_review_checks.py --skip-browser
```

Result: **36/36 passed together; exit code 0.**

The development-only browser skip was not treated as browser release acceptance.

Included V15-specific results:

```text
V15_INTEGRATION_HARDENING_TEST_PASSED
V15_HTTP_INTEGRATION_TEST_PASSED
ROUTE_BUNDLE_CHECK_PASSED
PAGE_ASSET_MANIFEST_CHECK_PASSED
```

The real-HTTP test starts `server.py` and verifies health, CSP, bundled HTML, JavaScript/CSS MIME types, registration, invitation creation, all invitation-specific management routes, publication, the public slug page and public JSON.

### Browser suites that genuinely ran

The following nine Chromium suites ran with a launchable system Chromium and passed with no browser skip:

```text
INLINE_EDITOR_RUNTIME_TEST_PASSED
V10_BROWSER_RUNTIME_TEST_PASSED
V11_BROWSER_RUNTIME_TEST_PASSED
V12_BROWSER_STABILIZATION_TEST_PASSED
V13_BROWSER_RUNTIME_TEST_PASSED
EDITOR_LAYOUT_GEOMETRY_TEST_PASSED
PUBLIC_LAYOUT_RUNTIME_TEST_PASSED
PUBLIC_GUEST_FEATURE_RUNTIME_TEST_PASSED
THEME_LAUNCHER_RUNTIME_TEST_PASSED
```

After the final lifecycle/bfcache adjustment, the editor, public guest and theme suites were rerun and passed again.

### Source and dependency checks

```text
Pillow PASS
qrcode PASS
Argon2 PASS
cryptography PASS
Playwright PASS
Chromium launch PASS
Python compileall PASS
All top-level JavaScript syntax checks PASS
EDITOR_BUNDLE_CHECK_PASSED
ROUTE_BUNDLE_CHECK_PASSED
PAGE_ASSET_MANIFEST_CHECK_PASSED
STATIC_INTEGRITY_TEST_PASSED
```

### Tests not represented as run

This hosted Chromium session began rejecting every direct URL navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`, including public domains, before Playwright routing could intercept the request. Therefore the four URL-navigation V14 browser tests were not rerun successfully in this V15 environment:

- `v14_static_server_test.py`
- `v14_live_server_acceptance_test.py`
- `v14_live_layout_test.py`
- `v14_dashboard_mobile_test.py`

They are still required by `release_check.py`; V15 does not convert or silently skip them. The application/server portions they cover were exercised through the new real-HTTP integration test, and all executable inline Chromium geometry/runtime suites passed. These four direct-navigation tests should be run again on the review PC where Chromium is allowed to navigate to the local server.

## Screenshots

- `review-screenshots/v15-editor-1440x900.png`
- `review-screenshots/v15-editor-390x844.png`

Both were generated from the final bundled editor runtime in Chromium.

## Exact file inventory relative to V14

### Added (43)

```text
V15_INTEGRATION_HARDENING_REPORT_2026-07-25.md
build_route_bundles.py
bundle-account-v15.css
bundle-account-v15.js
bundle-admin-v15.css
bundle-admin-v15.js
bundle-analytics-v15.css
bundle-analytics-v15.js
bundle-billing-v15.css
bundle-billing-v15.js
bundle-checkin-v15.css
bundle-checkin-v15.js
bundle-dashboard-v15.css
bundle-dashboard-v15.js
bundle-designer-v15.css
bundle-designer-v15.js
bundle-guests-v15.css
bundle-guests-v15.js
bundle-index-v15.css
bundle-index-v15.js
bundle-materials-v15.css
bundle-materials-v15.js
bundle-privacy-v15.css
bundle-privacy-v15.js
bundle-public-v15.css
bundle-public-v15.js
bundle-reset-v15.css
bundle-reset-v15.js
bundle-responses-v15.css
bundle-responses-v15.js
bundle-templates-v15.css
bundle-templates-v15.js
bundle-verify-v15.css
bundle-verify-v15.js
page-assets-v15.json
review-screenshots/v15-editor-1440x900.png
review-screenshots/v15-editor-390x844.png
route-bundle-sources-v15.json
route-bundles-v15.json
runtime-lifecycle-v15.js
tests/route_bundle_sources.py
tests/v15_http_integration_test.py
tests/v15_integration_hardening_test.py
```

### Changed (41)

```text
BUILD_INFO.json
account.html
admin.html
analytics.html
app.js
billing.html
build_editor_bundle.py
build_page_manifests.py
checkin.html
collaboration-live.js
dashboard.html
dependency_preflight.py
designer.html
editor-builders.js
editor-suite.js
guests.html
index.html
materials.html
privacy.html
public-page.js
public.html
release_check.py
reset.html
responses.html
run_review_checks.py
server.py
service-worker.js
storage.js
templates.html
tests/build_integrity_test.py
tests/final_visual_polish_test.py
tests/final_workflow_audit_v7_test.py
tests/inline_editor_runtime_test.py
tests/private_access_header_test.py
tests/pro_editor_v6_test.py
tests/ux_ai_v5_test.py
tests/v10_experience_test.py
tests/v12_media_source_test.py
tests/v14_performance_budget_test.py
tests/workflow_continuity_test.py
verify.html
```

### Removed (1)

```text
page-assets-v14.json
```

`page-assets-v14.json` is replaced by the accurately measured V15 manifest rather than being retained as a second source of truth.

## Remaining limitations

- Route bundles concatenate proven source modules; they are not minified or tree-shaken. This is deliberate to preserve source order and simplify debugging.
- The editor bundle remains large in raw bytes because the historical compatible functionality is retained. HTTP compression/CDN delivery is still recommended in production.
- If IndexedDB is denied, the fallback material repository is intentionally session-only.
- CRDT-level simultaneous character editing, full Photoshop parity and MP4/GIF timeline rendering remain outside this stabilization release.
- Real PostgreSQL, Redis, R2/S3/KMS/CDN, SMTP, passkey hardware, messaging, billing and AI providers were not exercised without supplied production infrastructure and credentials.
