# V16 Windows and Editor UI Hardening Report

**Build:** `windows-ui-hardened-v16`  
**Date:** 2026-07-27  
**Baseline:** `e-invitation-platform-integration-hardened-v15.zip`  
**Invitation schema:** 13 (unchanged)

## Purpose

V16 is a focused bug-fix and portability release. It keeps the V15 product architecture, invitation data model, compatibility source modules, Khmer features, publishing, optional RSVP, media, collaboration, templates, timeline, privacy, check-in, and account-security functions. It does not add a new feature phase.

The release addresses confirmed Windows release-gate failures and editor geometry defects found by an independent Windows audit.

## Implemented fixes

### 1. Cross-platform deterministic route bundles

`build_route_bundles.py` now normalizes generated text to LF and encodes it to UTF-8 bytes before both hashing and atomic writing. The exact bytes written are the exact bytes hashed on Windows, Linux, and macOS.

The generator retains atomic replacement. The V16 regression rebuilds the bundles, immediately runs `--check`, rejects CRLF in generated assets, and verifies manifest SHA-256 values against the written bytes.

### 2. Windows SQLite cleanup

The affected storage/privacy tests now wrap SQLite connections with `contextlib.closing(...)`. Transaction context management is retained, but the underlying handle is explicitly closed before `TemporaryDirectory` cleanup.

Affected tests:

- `tests/v12_storage_privacy_test.py`
- `tests/v12_immediate_stabilization_test.py`

### 3. Platform-aware graceful shutdown

The graceful-shutdown test no longer treats Windows `TerminateProcess` as graceful termination.

- Windows: starts the server in a new process group and sends `CTRL_BREAK_EVENT`.
- Server: handles `SIGBREAK` when the platform exposes it.
- POSIX: starts a new session and sends `SIGTERM` to the process group.
- Both paths require bounded exit, return code 0, released SQLite handles, and removable temporary data directories.

### 4. UTF-8-safe release output

`run_review_checks.py` and `release_check.py` now:

- configure their own stdout and stderr as UTF-8 with replacement-safe error handling where supported;
- set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` for every child process;
- preserve real Khmer assertions and Khmer output.

Release markers are consistently V16:

- `EINVITATION_V16_ALL_REQUIRED_REVIEW_CHECKS_PASSED`
- `EINVITATION_V16_RELEASE_CHECK_PASSED`

### 5. Mobile page dock

The mobile dock is now a reserved layout row rather than a translated fixed overlay.

- inherited centering transforms are removed;
- left/right positioning uses coherent automatic width;
- the dock remains inside 360, 390, and 430-pixel viewports;
- only the active page chip is shown on compact screens;
- the active page is automatically scrolled into view when page state changes;
- Add and Flow remain available.

### 6. Fixed-control collision removal

Focus, Style & Experience, Timeline, Studio Ops, Flow, and secondary canvas actions are no longer competing fixed buttons around the canvas.

They are preserved as their original controls and handlers, but moved into one keyboard-accessible native `details` More surface. Escape and click-away close it, and focus remains keyboard reachable.

The selection context toolbar now occupies a reserved row instead of floating over the artboard. The page dock is also a reserved row after the visible canvas viewport.

### 7. Desktop toolbar overflow

The primary canvas toolbar no longer attempts to fit roughly 1,376 pixels of controls inside a roughly 758-pixel area.

Primary viewport/navigation controls remain visible. Grid, rulers, safe margins, copy/paste, Focus, Flow, Style, Timeline, and Studio Ops move into More at constrained widths. No toolbar control is half-visible.

### 8. Mobile tool-rail scrollbar

The horizontal tool rail remains touch-scrollable but suppresses the native Windows/Chromium scrollbar with standards and WebKit rules. Active tools are automatically scrolled into view. Practical touch targets remain approximately 44×44 CSS pixels.

### 9. Theme contrast stability

The theme test now emulates reduced motion and waits for the 150–260 ms theme transitions to settle before measuring contrast. It checks light, dark, and system-resolved themes.

The V16 final style layer also limits tour transition properties to transform/opacity, avoiding transient foreground/background contrast interpolation.

### 10. Release documentation

`README.md`, `BUILD_INFO.json`, release markers, dependency preflight output, and this report identify V16 consistently. The invitation schema remains version 13.

## Browser geometry coverage

`tests/v16_browser_geometry_test.py` checks:

- 1440×900 desktop;
- 390×844 mobile;
- 360×800 mobile;
- 430×932 mobile;
- 1440×900 → 390×844 → 1440×900 without reload;
- no document-level horizontal overflow;
- dock fully inside the viewport;
- active page chip intersecting the visible dock track;
- dock after the visible canvas viewport;
- More surface not overlapping the right inspector;
- no toolbar horizontal overflow or partially clipped child controls;
- moved Focus/Style/Timeline controls not remaining as fixed overlays;
- mobile bottom navigation inside the viewport and safe area;
- hidden native tool-rail scrollbar;
- English and Khmer editing/capture after responsive transitions;
- zero page errors and console errors.

## Build and deterministic validation

Executed:

```text
python build_editor_bundle.py
python build_editor_bundle.py --check
python build_route_bundles.py
python build_route_bundles.py --check
python build_page_manifests.py
python build_page_manifests.py --check
python dependency_preflight.py
```

Final output:

```text
EDITOR_BUNDLE_BUILT
EDITOR_BUNDLE_CHECK_PASSED
WROTE 16 route bundles
ROUTE_BUNDLE_CHECK_PASSED
WROTE page-assets-v15.json
PAGE_ASSET_MANIFEST_CHECK_PASSED
[OK] Pillow: responsive images, social cards and image processing
[OK] qrcode: public, personalized and authenticator QR images
[OK] argon2-cffi: Argon2id password hashing
[OK] cryptography: WebAuthn/passkey verification
[OK] Playwright: required live Chromium acceptance tests
[OK] Chromium launch: /usr/bin/chromium

V16 dependency preflight passed.
```

Python compilation and JavaScript syntax validation also passed:

```text
JAVASCRIPT_SYNTAX_CHECK_PASSED 89 files
```

## Deterministic/backend/security results

All 37 registered deterministic/backend/security tests passed in a completed sequential runner invocation with exit code 0. The unedited runner output is included at `review-logs-v16/deterministic-full.log`. The development-only browser skip in that command is explicitly labeled and is not treated as release browser acceptance.

Passed test markers include:

```text
BUILD_INTEGRITY_TEST_PASSED
V10_EXPERIENCE_TEST_PASSED
V11_MEDIA_EXPERIENCE_TEST_PASSED
V12_STORAGE_PRIVACY_TEST_PASSED
V12_IMMEDIATE_STABILIZATION_TEST_PASSED
V12_ROUTING_CONTEXT_TEST_PASSED
V12_MEDIA_SOURCE_TEST_PASSED
V13_FUTURE_FOUNDATION_TEST_PASSED
V13_ACCOUNT_SECURITY_TEST_PASSED
V13_EDITOR_MODEL_TEST_PASSED
V13_BACKUP_RESTORE_TEST_PASSED
V13_PRODUCT_LIFECYCLE_TEST_PASSED
V13_PRIVACY_LIFECYCLE_TEST_PASSED
V14_LIFECYCLE_SIGNING_TEST_PASSED
V16_PERFORMANCE_BUDGET_TEST_PASSED
V15_INTEGRATION_HARDENING_TEST_PASSED
V15_HTTP_INTEGRATION_TEST_PASSED
V16_WINDOWS_UI_HARDENING_TEST_PASSED
STATIC_INTEGRITY_TEST_PASSED
SMOKE_TEST_PASSED
PLAN_LIMIT_TEST_PASSED
FINAL_FEATURES_TEST_PASSED
PRODUCTION_FOUNDATIONS_TEST_PASSED
PROVIDER_ADAPTERS_TEST_PASSED
REALTIME_STORAGE_TEST_PASSED
SIGNED_UPLOAD_BACKEND_TEST_PASSED
FINAL_VISUAL_POLISH_TEST_PASSED
UX_AI_V5_TEST_PASSED
PRO_EDITOR_V6_TEST_PASSED
WORKFLOW_CONTINUITY_TEST_PASSED
FINAL_WORKFLOW_AUDIT_V7_TEST_PASSED
SECURITY_REGRESSION_TEST_PASSED
SECURITY_MAINTENANCE_TEST_PASSED
PRIVATE_ACCESS_HEADER_TEST_PASSED
COLLABORATION_ASSET_PERMISSIONS_TEST_PASSED
OPTIMISTIC_REVISION_TEST_PASSED
COLLABORATION_REVISION_TEST_PASSED
```

## Chromium results genuinely executed in this environment

These ten required Chromium suites completed their assertions with no skip:

```text
V16_BROWSER_GEOMETRY_TEST_PASSED
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

## Required live-navigation suites blocked by the hosted browser policy

The following four suites remain registered as mandatory in `release_check.py` and are not converted into skips or successes:

```text
tests/v14_static_server_test.py
tests/v14_live_server_acceptance_test.py
tests/v14_live_layout_test.py
tests/v14_dashboard_mobile_test.py
```

In this hosted environment Chromium rejects navigation before application code executes:

```text
Page.goto: net::ERR_BLOCKED_BY_ADMINISTRATOR at http://127.0.0.1:<port>/dashboard.html
```

Therefore:

- these four suites are **not claimed as passed** for V16 here;
- the monolithic `python release_check.py` cannot honestly emit its V16 success marker in this host;
- they must be rerun on the Windows review machine or ChatGPT Work environment where localhost navigation is available;
- their assertions remain strict and browser skips remain release failures.

The independent Windows audit reported that its audit-only corrected copy completed all deterministic and Chromium suites. V16 permanently implements those corrections, but the final V16 Windows path still requires a fresh Windows run.

## Screenshots

- `review-screenshots/v16-editor-1440x900.png`
- `review-screenshots/v16-editor-390x844.png`

## Production credentials and infrastructure not tested

No real credentials were added. These existing adapters still require their deployment environments:

- managed PostgreSQL and point-in-time recovery;
- production Redis;
- private R2/S3-compatible storage and KMS;
- CDN signing/caching configuration;
- SMTP;
- hardware passkeys on a production HTTPS origin;
- SMS, Telegram, and WhatsApp providers;
- custom-domain DNS/TLS;
- billing and external AI providers.

## Remaining limitations

- V16 fixes the reported Windows/UI defects but this container is not Windows; the Windows-only signal and filesystem behavior requires the mandatory Windows release run.
- The historical source modules remain authoritative and are still concatenated into route bundles; this release does not delete compatibility code.
- The editor remains a large mature application. V16 changes layout ownership and request geometry, not the schema or feature set.

## Exact V15 → V16 file inventory

**Added: 13**

```text
V16_WINDOWS_UI_HARDENING_REPORT.md
review-logs-v16/browser-executable.exit
review-logs-v16/browser-executable.log
review-logs-v16/build-and-preflight.log
review-logs-v16/deterministic-full.log
review-logs-v16/direct-navigation-host-block.exit
review-logs-v16/direct-navigation-host-block.log
review-screenshots/v16-editor-1440x900.png
review-screenshots/v16-editor-390x844.png
tests/v16_browser_geometry_test.py
tests/v16_windows_ui_hardening_test.py
windows-ui-v16.css
windows-ui-v16.js
```

**Changed: 22**

```text
BUILD_INFO.json
README.md
build_route_bundles.py
bundle-index-v15.css
bundle-index-v15.js
dependency_preflight.py
page-assets-v15.json
release_check.py
route-bundle-sources-v15.json
route-bundles-v15.json
run_review_checks.py
server.py
tests/theme_launcher_runtime_test.py
tests/v10_browser_runtime_test.py
tests/v11_browser_runtime_test.py
tests/v12_browser_stabilization_test.py
tests/v12_immediate_stabilization_test.py
tests/v12_storage_privacy_test.py
tests/v13_browser_runtime_test.py
tests/v14_live_server_acceptance_test.py
tests/v14_performance_budget_test.py
tests/v15_integration_hardening_test.py
```

**Removed: 0**

## Included unedited test logs

The project archive contains:

```text
review-logs-v16/build-and-preflight.log
review-logs-v16/deterministic-full.log
review-logs-v16/browser-executable.log
review-logs-v16/direct-navigation-host-block.log
```

The accompanying `.exit` files record the completed browser group exit code (`0`) and the environment-blocked direct-navigation check (`1`).
