# V17 Professional Transform and Layers Foundation

**Baseline:** `einvite-v16.1-codex-fixed.zip`  
**Release:** `e-invitation-platform-professional-transform-layers-v17.zip`  
**Date:** 2026-07-27  
**Invitation schema:** 13 (unchanged)  
**README:** intentionally unchanged, as requested

## Release summary

V17 strengthens the existing normalized scene graph and command bridge into one authoritative desktop-first selection, transform, layout-assistance, layers, grouping, clipboard, and history subsystem. It does not replace the invitation renderer, server architecture, or V16.1 workflows.

The editor-only selection and pointer-interaction state are separate from the invitation document. Direct manipulation previews in the DOM and commits one validated command transaction on pointer-up, so a drag, resize, or rotation produces one history entry and one autosave rather than one save per pointer event.

## Implemented and verified

### Selection

- Click selection for text, image, shape, and group content.
- Shift/Ctrl/Cmd-click toggle selection.
- Empty-canvas drag marquee selection.
- Escape clears selection.
- Ctrl/Cmd+A selects all unlocked objects on the active canvas.
- Selection outlines use the visible transformed bounds.
- Pure selection changes have editor-only undo/redo without being persisted in the invitation JSON.
- Locked objects remain visible but cannot be selected or transformed directly on the canvas.

### Transforms

- Eight resize handles and one rotation handle.
- Shift preserves aspect ratio.
- Alt/Option resizes from the center.
- Arrow keys nudge by one pixel; Shift+Arrow nudges by ten pixels.
- Position, width, height, and rotation inputs stay synchronized with direct manipulation.
- Multi-object movement, resizing, and rotation commit as one transaction.
- Invalid, NaN, zero-size, negative-size, and corrupt group states are rejected before autosave.
- Transform results are clamped to valid canvas dimensions.

### Snapping and layout assistance

- Grid, ruler, snapping, and guide toggles.
- User-created horizontal and vertical guides.
- Canvas edge/center snapping.
- Object edge/center snapping.
- Grid and user-guide snapping.
- Temporary smart guides and equal-spacing measurements.
- Align Left, Center, Right, Top, Middle, and Bottom.
- Horizontal and vertical distribution.

### Layers

- Active-page objects shown in actual render order.
- Layer/canvas selection synchronization.
- Drag reordering.
- Bring Forward, Send Backward, Bring to Front, and Send to Back.
- Rename, duplicate, delete, hide/show, and lock/unlock.
- Nested groups with expansion and collapse.
- Group-level visibility and locking metadata are persisted consistently with descendants.
- Layer selection remains available for locked items so they can be unlocked deliberately.

### Groups and clipboard

- Ctrl/Cmd+G groups selected objects.
- Ctrl/Cmd+Shift+G ungroups.
- Copy, cut, paste, duplicate, and delete.
- Pasted objects and groups receive new stable IDs.
- Pasted content receives a visible offset.
- Nested group relationships and relative transforms are preserved.
- Clipboard data is validated before insertion.

### Command history and persistence

- One gesture equals one command/history entry.
- Undo/redo covers transforms, reorder, visibility, locking, grouping, duplication, deletion, property changes, and editor-only selection changes.
- Document commands are validated before commit.
- Autosave receives only committed valid documents.
- Existing optimistic-revision conflict handling remains active.
- Draft edits do not alter the existing public publication snapshot until republished.
- Existing V13 documents migrate safely without changing `schemaVersion: 13`.

## Architecture

### Authoritative interaction owner

`professional-editor-v17.js` owns canvas pointer interactions in capture phase. Historical drag, resize, marquee, and keyboard handlers defer when V17 is active. This prevents competing transform implementations while preserving the older source modules for compatibility.

### Document versus UI state

- Invitation content and normalized scene data remain in the existing document model.
- Temporary selection, marquee, pointer interaction, guide rendering, and overlays remain editor-only state.
- Legacy `editorModel.selectionIds` values can still be read during migration but are removed from subsequent document commits.

### Renderer isolation

Selection outlines, handles, layers UI, smart guides, and transform controls exist only in the editor route bundle. The public renderer and publication snapshots contain no editor overlays.

### Command and route synchronization

Professional commands expose a committed-command event and sequence after the synchronous document transaction completes. The new selection is applied synchronously with that commit, so an immediate follow-up shortcut such as Delete cannot race the next animation frame. This gives browser tests and future integrations a deterministic completion point without changing command semantics. Keyboard ownership is registered at window capture phase so legacy document-level shortcuts cannot intermittently win the same chord.

Collaboration and presence now require an explicit invitation route or a hydrated `serverInvite.id`; they no longer fall back to a remembered/demo invitation. This prevents unauthenticated root navigation and cross-tab remembered IDs from generating unrelated 401 presence/event requests.

## Exact source inventory relative to V16.1

### Added — 10 files

- `V17_PROFESSIONAL_TRANSFORM_LAYERS_REPORT.md`
- `professional-editor-v17.css`
- `professional-editor-v17.js`
- `review-screenshots/v17-editor-1440x900.png`
- `review-screenshots/v17-editor-390x844.png`
- `tests/v17_layers_clipboard_history_test.py`
- `tests/v17_persistence_snapshot_test.py`
- `tests/v17_professional_editor_test.py`
- `tests/v17_professional_foundation_test.py`
- `tests/v17_served_editor_test.py`

### Changed — 21 files

- `BUILD_INFO.json`
- `app.js`
- `bundle-index-v15.css`
- `bundle-index-v15.js`
- `canvas-plus.js`
- `collaboration-live.js`
- `dependency_preflight.py`
- `collaboration.js`
- `editor-schema-v13.js`
- `editor-suite.css`
- `editor-suite.js`
- `page-assets-v15.json`
- `release_check.py`
- `route-bundle-sources-v15.json`
- `route-bundles-v15.json`
- `run_review_checks.py`
- `tests/v14_dashboard_mobile_test.py`
- `tests/v16_browser_geometry_test.py`
- `tests/v16_windows_ui_hardening_test.py`
- `windows-ui-v16.js`
- `workflow-pro-editor-v6.js`

### Removed

None.

## Generated bundles changed

- `editor-suite.js`
- `editor-suite.css`
- `bundle-index-v15.js`
- `bundle-index-v15.css`
- `route-bundles-v15.json`
- `page-assets-v15.json`

`professional-editor-v17.js` and `professional-editor-v17.css` are last in the editor source order so they can claim interaction ownership without deleting historical compatibility sources.

## Release validation

### Exact release command

```text
python release_check.py
```

**Exit code:** `0`

Final unedited markers:

```text
EINVITATION_V17_ALL_REQUIRED_REVIEW_CHECKS_PASSED
EINVITATION_V17_RELEASE_CHECK_PASSED
```

### Build stages completed

```text
python build_editor_bundle.py
python build_editor_bundle.py --check
python build_route_bundles.py
python build_route_bundles.py --check
python build_page_manifests.py
python build_page_manifests.py --check
python -m compileall -q server.py security_v13.py media_worker.py backup_restore.py build_editor_bundle.py build_route_bundles.py build_page_manifests.py run_review_checks.py tests
node --check <all 90 top-level JavaScript files>
python dependency_preflight.py
python run_review_checks.py
```

Results:

```text
EDITOR_BUNDLE_CHECK_PASSED
ROUTE_BUNDLE_CHECK_PASSED
PAGE_ASSET_MANIFEST_CHECK_PASSED
JAVASCRIPT_SYNTAX_CHECKS_PASSED
V17 dependency preflight passed
```

### Deterministic/backend/security tests

**39 of 39 passed. No deterministic test was skipped.**

The matrix includes build integrity, V10–V16 compatibility, storage/privacy, routing, media, account security, normalized editor model, backups, lifecycle, signing, performance budgets, real HTTP integration, static integrity, core smoke, plan limits, production/provider adapters, realtime storage, signed uploads, security regression/maintenance, protected access, collaboration permissions, and optimistic revision handling.

V17-specific deterministic markers:

```text
V17_PROFESSIONAL_FOUNDATION_TEST_PASSED
V17_PERSISTENCE_SNAPSHOT_TEST_PASSED
```

### Required Chromium tests

**17 of 17 passed. No browser test was skipped.**

```text
V14_STATIC_SERVER_TEST_PASSED
V14_LIVE_SERVER_ACCEPTANCE_TEST_PASSED
V14_LIVE_LAYOUT_TEST_PASSED
V14_DASHBOARD_MOBILE_TEST_PASSED
V16_BROWSER_GEOMETRY_TEST_PASSED
V17_PROFESSIONAL_EDITOR_TEST_PASSED
V17_LAYERS_CLIPBOARD_HISTORY_TEST_PASSED
V17_SERVED_EDITOR_TEST_PASSED
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

The V17 served-browser test used the real HTTP server and verified editor persistence/reload, English and Khmer content, preview, publication snapshot isolation, public navigation, and responsive mobile/public behavior.

### Viewports and visual modes

Verified by the combined browser matrix:

- Desktop 1440×900
- Mobile 390×844
- Existing 360×800 and 430×932 responsive coverage
- Light and dark themes
- English and Khmer object content
- Root, dashboard, editor, preview, public invitation, and management navigation
- Console errors, page errors, and unhandled promise failures

## Screenshots

- `review-screenshots/v17-editor-1440x900.png`
- `review-screenshots/v17-editor-390x844.png`

## Local-demo requirements

The local project continues to work without production credentials. The included setup and dependency preflight cover the local Python, Node.js, Playwright Chromium, Pillow, qrcode, Argon2, and cryptography requirements.

## Production-only credentials and infrastructure not tested here

These existing adapters remain optional and were not certified against live services because credentials were not supplied:

- Managed PostgreSQL and point-in-time recovery
- Redis cluster/rate-limit infrastructure
- Private Cloudflare R2, Amazon S3, or compatible object storage
- KMS and production CDN signing
- SMTP delivery
- Hardware passkeys on a production HTTPS origin
- SMS, Telegram, and WhatsApp delivery providers
- Custom-domain DNS and TLS automation
- Billing provider
- External AI providers
- Production malware-scanning service

The absence of these services does not block the local demo workflow.

## Later phases — planned, not implemented in V17

1. **Advanced typography:** rich-text spans, Khmer-aware font management, OpenType controls, auto-fit, columns, and path text.
2. **Vector tools:** editable paths/shapes, Boolean operations, strokes, gradients, and clipping masks.
3. **Non-destructive image editing:** deeper crop/focal-point, color, curves, masks, blend modes, filters, and provider-backed background removal.
4. **Animation studio:** expanded keyframe/easing/path editing, stagger, scroll triggers, and media export.
5. **Reusable design system:** components, symbols, masters, brand kits, design tokens, and package migrations.
6. **Asset/storage productionization:** signed multipart storage, CDN derivatives, lifecycle policies, quotas, recycle bin, backups, EXIF privacy, MIME inspection, and malware scanning.
7. **Security and scale:** explicit deployment configuration, row-level authorization, distributed jobs/rate limits, dependency scanning, tenant isolation, and restore drills.
8. **Collaboration:** operation-level conflict handling, comments/approvals, named versions, and richer presence.
9. **Performance:** route-level code splitting, workers/offscreen processing, virtualized layers/assets, progressive media, and memory profiling.

These later capabilities were deliberately not expanded during this milestone so the professional transform and layers foundation could be completed and regression-tested coherently.
