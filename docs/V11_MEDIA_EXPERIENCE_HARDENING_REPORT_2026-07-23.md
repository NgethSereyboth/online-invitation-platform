# E-invitation Platform — V11 Media & Experience Hardening

**Build:** `media-experience-hardening-v11`  
**Date:** 2026-07-23  
**Baseline:** `e-invitation-platform-style-experience-v10.zip`

## Purpose

V11 extends the existing V10 codebase in place. It does not change frameworks, restart the project, or replace the invitation-document/renderer architecture. The release closes the known V10 media limitations, fixes issues discovered during a second regression audit, and preserves all V9 stabilization and V10 visual-experience functionality.

## Implemented improvements

### 1. Real generated social cards

- Added first-party server-rendered PNG social cards using the published invitation snapshot.
- Supports Open Graph `1200×630`, square `1080×1080`, and story `1080×1920` output.
- The selected uploaded social-cover photo is now actually rendered into the generated card.
- Supports invitation name, Khmer/English/bilingual text, date, venue, monogram, alignment, light/dark text, invitation colors, and safe private-invitation fallbacks.
- Long text is fitted/wrapped instead of overflowing.
- The browser editor preview still works independently for immediate design iteration.
- Public Open Graph/Twitter metadata uses the generated card when Pillow is available and retains the existing SVG fallback otherwise.

### 2. Real QR generation

- Replaced the placeholder/branded pseudo-QR output with real first-party QR images.
- Added branded public-invitation QR cards.
- Replaced the external `quickchart.io` personalized guest QR dependency with an authenticated internal QR endpoint.
- General public QR cards never contain guest tokens or private access credentials.
- Personalized guest QR codes are owner-only and are returned with no-store caching.
- Long invitation names are fitted on branded QR cards.

### 3. Responsive uploaded-image pipeline

- Uploaded image assets now record intrinsic width, intrinsic height, and dominant color.
- EXIF orientation is applied before dimensions are measured.
- Added a stable first-party `responsiveBase` URL for each uploaded image, including when the original asset is hosted on R2/S3.
- Public image markup can emit responsive WebP `srcset` derivatives at 480, 960, 1440, and 1920 widths.
- Added an on-demand responsive image endpoint with immutable derivative caching.
- The endpoint supports WebP, JPEG, PNG, and AVIF when the installed Pillow build supports AVIF; AVIF requests fall back to WebP when necessary.
- Non-image files are rejected by the derivative endpoint.
- Dominant-color placeholders reduce visual blankness during image loading.
- Newly inserted editor images preserve intrinsic metadata and the responsive derivative URL through document save/publish.

### 4. Public performance improvements

- Below-fold gallery images are lazy loaded.
- Images use asynchronous decoding.
- Intrinsic width/height attributes are emitted where metadata exists.
- Only an enabled opening scene's selected background image is preloaded.
- Lower public sections retain `content-visibility: auto` from V10.
- The Design Check now detects missing intrinsic dimensions rather than confusing CSS object dimensions with real source-image dimensions.

### 5. Style Kit corrections and deeper application

- Fixed the malformed Khmer Unicode detector in the Style Kit font application path.
- Heading-like objects now receive kit heading fonts while body text receives kit body fonts, with Khmer-specific heading/body fonts used when appropriate.
- Style Kit motion profiles now coordinate section-animation defaults.
- Style Kit background values propagate to the master page styling.
- Public guest layouts now expose scoped kit tokens for spacing, radius, shadow, buttons, photo framing, section dividers, and ornaments.
- The three V10 kits therefore affect more of the complete guest presentation instead of only basic color/font variables.

### 6. Genuine non-persistent Style Kit preview

- V10's Preview action saved the preview before asking whether it should be kept.
- V11 makes preview genuinely temporary.
- Preview can be applied or cancelled from an in-product banner.
- Cancelling restores the exact pre-preview state without adding a saved preview revision.
- Leaving the Style Kit tab or closing the experience dialog safely cancels an uncommitted preview.
- Normal Apply continues through the existing save/history path for undo support.

### 7. Opening-scene hardening

- Opening background image URLs are constrained to supported safe image sources.
- Unsafe CSS URL characters and unsupported schemes are rejected.
- Opening scene duration is bounded.
- Finished opening covers leave the accessibility tree after their exit transition.
- Reduced-motion opening scenes hide immediately without relying on animation.
- Added a material-library picker for opening background images.
- Opening scenes remain direct children of the public guest root so desktop framing does not constrain the full-viewport opening.

### 8. Music interaction fix

- Fixed an existing public-renderer behavior that attempted music autoplay when the opening scene was disabled.
- With no opening scene, uploaded/YouTube music now waits for an explicit guest tap on the music control.
- Music-control accessible labels now update between Play and Pause states.
- Opening-scene interaction remains the music-start gesture when an opening scene is enabled.

### 9. Desktop guest-layout fixes

- Fixed the desktop layout shell incorrectly absorbing the full-screen opening scene.
- Fixed a Full Width selector that targeted a nonexistent nested `.guest` element.
- Added stronger scoped Style Kit presentation tokens without adding broad global selectors.
- Rechecked horizontal overflow at all required V10 viewport sizes.

### 10. Share and security cleanup

- Public and editor share URLs continue to remove `g`, `guest`, `guestToken`, `access`, `access_token`, and generic `token` parameters.
- Server-generated public QR URLs are always clean general invitation URLs.
- Personalized guest QR generation no longer leaks guest links to a third-party QR service.
- Uploaded project images used for server social cards are resolved only from project storage; the server does not fetch arbitrary remote image URLs, avoiding an SSRF path.

### 11. Accessibility and editor polish fixes

- Compact quick-edit buttons now have explicit accessible names.
- Previously nonfunctional Bring Forward and Send Backward quick-edit actions are wired to the existing layer-order system.
- Temporary Style Kit preview state is announced with an in-product status banner.
- Existing V10 dialog focus return, hidden/inert handling, Escape behavior, reduced motion, and icon-label cleanup remain intact.

### 12. Release-check reliability

- Added V11 deterministic media and Chromium runtime tests to the review runner.
- Browser-heavy tests now run sequentially in isolated temporary runtimes instead of competing for Chromium resources in parallel.
- Each test subprocess has an explicit timeout and a private data directory.
- This avoids the resource-stall pattern seen when multiple Chromium suites were launched concurrently on constrained machines.

## Invitation document and data changes

The invitation document **remains `schemaVersion: 10`**. V11 does not change the meaning or ordering of invitation content and therefore does not require a new document-schema migration.

New optional image-object metadata may be stored when available:

- `intrinsicWidth`
- `intrinsicHeight`
- `sizeBytes`
- `dominantColor`
- `responsiveBase`

Older V9/V10 documents without these values continue to render normally. The Design Check may warn that older images lack intrinsic metadata until they are re-added or refreshed from the material library.

The asset database schema adds backward-compatible columns:

- `width`
- `height`
- `dominant_color`

SQLite startup migration and PostgreSQL schema migration statements cover existing installations.

## Added dependencies

`requirements-production.txt` now includes:

- `Pillow` for raster social cards and responsive image processing.
- `qrcode[pil]` for first-party QR generation.

The core local server can still start without these optional packages, while the supplied one-click setup installs the production requirements automatically. Without Pillow/qrcode, enhanced raster/QR endpoints may fall back where possible or return a clear unavailable response.

## Files added

- `tests/v11_media_experience_test.py`
- `tests/v11_browser_runtime_test.py`
- `V11_MEDIA_EXPERIENCE_HARDENING_REPORT_2026-07-23.md`

## Files changed from V10

- `BUILD_INFO.json`
- `app.js`
- `experience-schema.js`
- `guest-layouts.css`
- `guest-layouts.js`
- `guests.js`
- `opening-scenes.js`
- `postgres_schema.sql`
- `public-share-panel.js`
- `public.html`
- `release_check.py`
- `renderer-core.js`
- `requirements-production.txt`
- `run_review_checks.py`
- `server.py`
- `social-card.css`
- `social-card.js`
- `storyboard.js`
- `style-kits.css`
- `style-kits.js`

## Verification completed

### Build and syntax

- `build_editor_bundle.py --check` — **PASS**
- Python compilation / compileall — **PASS**
- All 53 top-level JavaScript files with `node --check` — **PASS**
- Static local-asset and inline-JavaScript integrity — **PASS**

### Deterministic/backend/security tests

All passed:

- `build_integrity_test.py`
- `v10_experience_test.py`
- `v11_media_experience_test.py`
- `static_integrity_test.py`
- `smoke_test.py`
- `plan_limit_test.py`
- `final_features_test.py`
- `production_foundations_test.py`
- `provider_adapters_test.py`
- `realtime_storage_test.py`
- `signed_upload_backend_test.py`
- `final_visual_polish_test.py`
- `ux_ai_v5_test.py`
- `pro_editor_v6_test.py`
- `workflow_continuity_test.py`
- `final_workflow_audit_v7_test.py`
- `security_regression_test.py`
- `security_maintenance_test.py`
- `private_access_header_test.py`
- `collaboration_asset_permissions_test.py`
- `optimistic_revision_test.py`
- `collaboration_revision_test.py`

### Chromium/browser tests

All passed when executed individually:

- `inline_editor_runtime_test.py`
- `v10_browser_runtime_test.py`
- `v11_browser_runtime_test.py`
- `editor_layout_geometry_test.py`
- `public_layout_runtime_test.py`
- `public_guest_feature_runtime_test.py`
- `theme_launcher_runtime_test.py`

V11 browser coverage includes the required 390×844, 768×1024, 1024×768, 1280×720, 1440×900, and 1920×1080 widths, temporary Style Kit preview behavior, social-card controls, opening-scene safety, desktop-layout overflow, and light/dark editor-theme readability checks.

The hosted execution wrapper can still reach its overall command-duration ceiling when every Chromium suite is chained in one very long command. This is an execution-environment limit rather than a failing assertion. The review runner has nevertheless been improved to run browser tests sequentially with individual timeouts, and every constituent browser test completed successfully when run directly.

## Remaining limitations / intentional boundaries

1. Server-side cover-photo rendering accepts uploaded/project assets. It intentionally does not fetch arbitrary remote image URLs because doing so would create an SSRF risk. A remote CORS-enabled URL may still preview in the browser canvas, but it should be uploaded to Materials for guaranteed server-generated social cards.
2. Responsive derivatives are generated for platform-managed uploaded assets. Unmanaged external images remain the responsibility of their original image/CDN provider.
3. AVIF output depends on AVIF support in the installed Pillow build; WebP is the compatibility fallback.
4. Real external production providers (SMTP, live R2/S3 accounts, Redis, PostgreSQL, billing, AI, and social platforms) were not authenticated against real credentials. Their existing adapters and deterministic provider tests remain intact.
5. The large historical editor/CSS patch stack remains a maintainability concern from V9/V10. It was not rewritten during this targeted hardening phase because doing so would introduce unnecessary regression risk immediately before hands-on product review.
