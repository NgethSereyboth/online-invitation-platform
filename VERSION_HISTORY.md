# Version History

This project uses **semantic versioning**. `0.x` is pre-1.0; `1.0.0` is the first
production-certified release.

> **Legacy history:** the pre-reset version history (V1 → V54.34) is preserved
> in [`docs/LEGACY-VERSION-HISTORY.md`](LEGACY-VERSION-HISTORY.md). Some audit
> trail references may cite those entries.

---

## Version numbering scheme

| Bump | When | Example |
|---|---|---|
| **MAJOR** (`0` → `1`) | Only at production certification. Never before. | `0.99.5` → `1.0.0` |
| **MINOR** (`0.54` → `0.55`) | A completed roadmap part. One minor per part. | `0.54.0` → `0.55.0` |
| **PATCH** (`0.54.0` → `0.54.1`) | A completed task within a part. | `0.54.0` → `0.54.1` → `0.54.2` |

The six parts of the `ROADMAP-v0.54-to-v1.0.md` roadmap map to:

| Part | Version range |
|---|---|
| 1 — Version reset | `0.54.0` |
| 2 — Structure reorg | `0.55.0` (patch bumps per module moved) |
| 3 — Editor UX/UI | `0.56.0` … `0.60.0` (patch bumps per feature) |
| 4 — Backend security | `0.61.0` … `0.63.0` |
| 5 — Admin tools | `0.64.0` … `0.66.0` |
| 6 — Creator analytics | `0.67.0` … `0.69.0` |

`1.0.0` is the certification release, after all six parts plus the execution
items from `ROADMAP-V2.md` §5.

---

---

## 0.54.0 — Version reset & conventions

- Reset from the legacy V54.x scheme to semantic versioning `0.54.0`.
- Read as "the pre-1.0 project at its 54th feature milestone."
- Preserved the full pre-reset history (V1 → V54.34, 31 V54.x entries) in `docs/LEGACY-VERSION-HISTORY.md`.
- Established branch conventions: short-lived branches named `v0.54-part2-structure`, `v0.55-part3-editor-ux`, etc.
- Established commit format: `<part-slug>: <imperative summary>` on the first line, then a blank line, then a bullet list of what changed and why.
- **Primary files:** `VERSION_HISTORY.md` (rewritten), `docs/LEGACY-VERSION-HISTORY.md` (new — pre-reset archive)

---

## Pre-reset history (V1 → V54.34)

The project's pre-reset history spans 31 V54.x entries covering:

- **V54.0–V54.1** — Initial v54 refactor (editor chrome, UX bugs, security hardening, AutoFitGuard fix, bundle rebuild).
- **V54.2** — Khmer typography + WCAG AA audit (W3C guide, font registry, 16-page audit, contrast fixes, skip-links).
- **V54.3–V54.4** — Phase 2a guest features (multi-channel delivery, sign-up sheets, polls, photo album, post-send editing).
- **V54.5** — Certification framework (native platform matrix, browser matrix, pen test scope, load test plan, DR drill).
- **V54.6** — Plugin marketplace governance (manifest spec, double-signing, sandbox, moderation pipeline, SDK + example plugin).
- **V54.7** — Y.js CRDT upgrade (design doc, 4 new JS modules, 5 new routes, offline merge test).
- **V54.8** — Hosted tier design (storage tiers, nonprofit discount, Canva bridge, onboarding flow, billing integration).
- **V54.9** — sec-1: Fix reflected HTML injection in `serve_public` (P1-A from ASVS L2).
- **V54.10** — sec-4: Security notification emails on MFA/passkey/password changes (P1-D).
- **V54.11** — sec-2: Per-account login lockout (P1-B — 5 failures/15min → 423, sliding window, persists across restart).
- **V54.12** — sec-3: MFA recovery codes (10 codes, Argon2id hashed, regenerate + recover routes).
- **V54.13** — sec-5: Enforce JIT elevation (close Phase 1a stub — `evaluate()` real lookup + 3 routes + auto-approval).
- **V54.14** — ux-1: Host-side signup sheets UI (295 lines — create/edit/delete/view claims).
- **V54.15** — sec-6: Resource-scoped permissions Stage 3 (`scopes.py` + shadow eval logging + 3 grant routes).
- **V54.16** — ux-2: Host-side polls UI (528 lines — create/edit/close/results bar chart).
- **V54.19** — ux-5: WCAG P1 items (`:lang(km)` rule + `lang="km"` on all Khmer text + dynamic `<html lang>` + `.sr-only` labels + `aria-modal`).
- **V54.20** — ux-6: Empty/loading/error states (37 CSS rules + skeleton + retry patterns).
- **V54.21** — ux-4: Real upload progress bar for album (XHR + live % + cancel + retry + malware message).
- **V54.22** — ux-3: Wire edit-history view into dashboard.
- **V54.23** — ux-7: Toast notification system (`toast.js` + `toast.css`, replaced all `alert()` calls).
- **V54.24** — ux-9: Dark mode audit (3 contrast failures fixed — 4.00:1 → 4.61:1, 4.06:1 → 5.89:1, 2.80:1 → 5.40:1).
- **V54.25** — ux-8: Mobile responsiveness pass (279 lines CSS + 16-page viewport audit).
- **V54.26** — ux-10: Bilingual consistency pass (CI check — 239 strings, 0 missing, 0 byte-identical).
- **V54.27** — sec-7: Chapter 10 SAST/SCA/SBOM tooling (`security-scan.sh` + `generate-sbom.py` + CODEOWNERS + GitHub Actions).
- **V54.28** — sec-8: CSP report-only + `/api/csp-report` endpoint + monitoring doc.
- **V54.29** — sec-9: Rate-limit coverage audit (220 routes, 2 missing JIT limits added, CI check script).
- **V54.30** — vendor: Y.js vendored + wired into editor + dashboard (4 SRI-hashed script tags, 85KB bundle).
- **V54.31** — phase-4b: Y.js dual-write + V31→V52 migration verified end-to-end (8-phase test).
- **V54.32** — phase-2c: Calendar + venue maps + gift registry (11 handler methods, 2 new tables, CSP allows OpenStreetMap).
- **V54.33** — phase-4a: Plugin sandbox host runtime (`plugin_marketplace_ca.py` + `plugin_sandbox_host.js` + 2 DB tables + 5 routes).
- **V54.34** — phase-5: Canva bridge (5 endpoints) + onboarding flow (3 endpoints) + 4 new `users` columns.

For the full pre-reset entry text with primary file paths, see
[`docs/LEGACY-VERSION-HISTORY.md`](LEGACY-VERSION-HISTORY.md).

---

*Next version: `0.55.0` — Part 2 (Project Structure Reorganization).*

---

## 0.55.0 — Project structure reorganization

- Reorganized backend Python modules from flat `src/python/` into feature-based structure: `core/` (auth, preflight, deps), `features/` (malware_scanner, secrets, plugin_marketplace_ca, backup), `build/` (build_route_bundles, build_editor_bundle, build_page_manifests, sync_frontend_assets, prepare_production_env).
- Created target frontend directory structure: `src/js/{core,editor/{canvas,text,media,chrome,collab,history},pages/{public,dashboard,admin,auth,checkin},components,ai,plugins,vendors}` + `src/css/{base,components,editor,pages,themes}`.
- Moved 3 frontend files to new structure: `toast.js` → `components/toast.js`, `plugin_sandbox_host.js` → `plugins/sandbox-host.js`, `theme-init.js` → `core/theme.js`.
- Moved `toast.css` → `components/toast.css`.
- Updated all imports in `server.py` to reference new module paths (`core.auth`, `features.malware_scanner`, `features.secrets`, `features.plugin_marketplace_ca`, `core.preflight`).
- Updated build scripts' `REPO_ROOT` + `SCRIPT_DIR` path calculations for new locations.
- Updated `docs/route-bundle-sources-v15.json` to reference new source paths.
- Updated all 16 HTML files' `<script src>` and `<link href>` tags.
- Wrote `scripts/audit_file_structure.py` (audit tool — outputs `docs/STRUCTURE-AUDIT.csv`).
- Wrote `docs/STRUCTURE-MAPPING.md` (full mapping manifest for all 353 files).
- Wrote `scripts/migrate_structure.py` (idempotent migration script with state tracking).
- **Primary files:** `scripts/audit_file_structure.py`, `docs/STRUCTURE-AUDIT.csv`, `docs/STRUCTURE-MAPPING.md`, `scripts/migrate_structure.py`, `docs/.structure-migration-state.json`, `src/python/core/__init__.py`, `src/python/features/__init__.py`, `src/python/build/__init__.py`, `src/python/core/auth.py` (moved from `security_v13.py`), `src/python/features/malware_scanner.py` (moved from `security_scanner_v54.py`), `src/python/features/secrets.py` (moved from `secrets_v54.py`), `src/python/features/plugin_marketplace_ca.py` (moved), `src/python/features/backup.py` (moved from `backup_restore.py`), `src/python/core/preflight.py` (moved from `production_preflight.py`), `src/python/core/deps.py` (moved from `dependency_preflight.py`), `src/python/build/*.py` (5 build scripts moved), `src/js/core/theme.js`, `src/js/components/toast.js`, `src/js/plugins/sandbox-host.js`, `src/css/components/toast.css`

> **Note:** The `server.py` monolith split into `core/server.py` + `routes/*.py` is deferred — it requires careful extraction of ~150 handler methods. The versioned frontend files (`*-vNN.js`, 116 files) are also deferred — they need the bundle manifest + HTML script tags updated in lockstep. Both are documented in `docs/STRUCTURE-MAPPING.md` for a follow-up batch.

---

---

## 0.56.0 — Editor UX: alignment guides, multi-select, context menu, viewport controls

- **ROADMAP Part 3.1 — Canvas interaction layer.** Four new canvas-interaction modules + one CSS sheet, all wired into the `bundle-index-v15.{js,css}` editor bundle:
  - **`src/js/editor/canvas/guides.js`** — `EInviteAlignmentGuides` service (§3.1.1). Shows pink/blue SVG guide lines when dragging an element near a sibling's edge/center/canvas-center. Snap threshold 6px. Pointer Events API + `setPointerCapture()`. 1px SVG `<line>` overlay spanning the canvas. Fades out 200ms after `pointerup`. Emits `einvite:alignment-snapped` event with `{type, value, source, delta, axis, stringKey, label}`. Bilingual `align.snapped.{center,left,right,top,bottom,centerX,centerY}` strings (EN + KH).
  - **`src/js/editor/canvas/snapping.js`** — `EInviteSnapping` service (§3.1.4). Grid snapping (default 8px, configurable 2-200) + page-margin guides (default 40px, configurable 0-400). Grid renders as SVG `<line>` overlay (NOT divs). State persisted to localStorage (`ei-grid-enabled`, `ei-grid-size`, `ei-margin-size`). Toggleable via `setGridEnabled()`.
  - **`src/js/editor/canvas/selection.js`** — `EInviteMultiSelect` service (§3.1.2). Selection is a `Set<elementId>`. Shift-click toggle, marquee drag-select. Group bounds = union + 8px padding. Group transforms (move/resize/delete/duplicate) delegate to `EInviteProfessionalEditor.commands`. Keyboard: Ctrl+G group, Ctrl+Shift+G ungroup, Ctrl+A select all, Escape deselect.
  - **`src/js/editor/chrome/context-menu.js`** — `EInviteContextMenu` service (§3.1.3). Right-click shows `<div role="menu">` at `event.clientX/clientY` with edge clamping. Context-dependent items: empty canvas → Paste/Select all/Zoom to fit; single element → Cut/Copy/Duplicate/Delete/Reorder/Lock/Hide/Add comment; multiple → Group/Ungroup/Align/Distribute/Duplicate/Delete. Keyboard navigation: Arrow keys, Enter, Escape. Close on Escape, click outside, blur. Bilingual EN+KH on every item.
  - **`src/js/editor/canvas/viewport.js`** — `EInviteViewport` service (§3.1.5 + §3.4.5). Zoom presets (25%/50%/75%/100%/150%/200%/Fit/Fill). Zoom to cursor via Ctrl+scroll. Fit-to-screen computes scale with 40px margin (per ROADMAP §3.4.5). Pan with Space+drag (existing `EInviteCanvasPanController`) or middle-mouse drag (new in this module).
  - **`src/css/editor/canvas.css`** — appended section 8 with rules for `.alignment-guide-overlay`, `.alignment-guide` (pink `.is-center` / blue default / amber `.is-margin`), `.einvite-grid-overlay`, `.einvite-marquee`, `.einvite-context-menu`, `.einvite-viewport-hud`, body state classes.
- **Bundle manifest** — added 5 new JS entries to the `index.html` page's `scripts` array (after `editor/ui-components.js`) in `docs/route-bundle-sources-v15.json`. The 5 modules are concatenated into `bundle-index-v15.js` and `bundle-index-v15.css` by `build_route_bundles.py`. Bundle grew by ~30KB JS / ~5KB CSS. `python3 src/python/build/build_route_bundles.py --check` passes.
- **Test** — `tests/editor_alignment_guides_test.py` (Playwright headless Chromium, 5 phases): (1) module loads + exposes the public API with correct version + threshold + STRINGS keys; (2) `computeSnap()` correctly snaps a dragged element whose center-x is within 6px of a sibling's center-x → returns deltaX≈-0.5 and a match with `type:'center-x'` source `'a'` value `200`; (3) `computeSnap()` returns no matches when the dragged element is far (>40px) from every snap target; (4) `beginDrag()`+`updateDrag()`+`endDrag()` drive the live SVG overlay AND emit the `einvite:alignment-snapped` event with `{type, source, label:{en,km}}` payload, and the overlay's guide `<line>` has class `is-center` (pink); (5) the overlay's `.is-fading` class is applied and the overlay is cleared 200ms after `endDrag`. Test prints `EDITOR_ALIGNMENT_GUIDES_TEST_PASSED`.
- **Smoke verified** — all 5 new modules load cleanly in a headless browser via `bundle-index-v15.js`, exposing their globals with version `56` and no page errors. Bundle JS syntax verified via `node --check`.
- **Constraints honoured** — no new build tools (vanilla JS + plain CSS, IIFE pattern with `window.EInviteXxx` exports). Bilingual EN+KH on every user-facing string (snap events, context-menu items, viewport labels, snapping toggles). Idempotent module loads (guarded by `version` check). Cleanup registered with `window.EInviteLifecycle`.
- **No regressions** — existing editor chrome (`editor-core.js`, `ui-layout.js`, `ui-components.js`) unchanged. Existing context menu in `bundle-index-v15.js` (lines ~5847) and existing pan controller (`EInviteCanvasPanController`) left intact; the new modules are additive layers that delegate to the existing pro-editor commands.
- **Primary files:** `src/js/editor/canvas/guides.js`, `src/js/editor/canvas/snapping.js`, `src/js/editor/canvas/selection.js`, `src/js/editor/canvas/viewport.js`, `src/js/editor/chrome/context-menu.js`, `src/css/editor/canvas.css` (appended), `tests/editor_alignment_guides_test.py`, `docs/route-bundle-sources-v15.json` (5 new script entries).

---

---

## 0.56.1 — Editor UX: inline text editing, text effects, text on curve, image crop/filters/masks

**Part 3.2 — Text editing layer:**

- **3.2.1 — Inline rich text editing** (`src/js/editor/text/inline-editor.js`): double-click a text element to mount a transparent `contenteditable` overlay exactly over the canvas text. Ctrl+B/I/U via `document.execCommand` (deprecated but universally supported per the ROADMAP §3.2.1 directive — do NOT chase newer `InputEvent` APIs). Color / font-family / font-size applied via `Range` + `surroundContents`. On blur / Escape / outside-click the HTML is committed to the document model, the underlying canvas text is re-rendered, and the overlay is destroyed. Client-side sanitiser (`InlineEditor.sanitize`) mirrors the server-side `_RichTextSanitizer` — strips `<script>`, `<iframe>`, `<style>`, `<object>`, `<embed>`, `<svg>`, `<math>`, `<template>`, `<noscript>` (entire subtree), keeps only `<b>`, `<i>`, `<u>`, `<strong>`, `<em>`, `<span style="color:...">`, `<br>`. Khmer-safe: `letter-spacing` forced to `normal` while editing (Khmer shaping breaks under spacing).
- **3.2.2 — Text effects** (`src/js/editor/text/effects.js`): shadow (color, blur, offset-x, offset-y via `text-shadow`), outline (color, width 0–8px via `-webkit-text-stroke` + `text-stroke`), gradient (two-stop linear gradient, angle 0–360°, 8 presets + custom via `background-clip: text` + `-webkit-text-fill-color: transparent`). Inspector panel section built via `TextEffects.buildInspectorPanel`. Persists as `{shadow: {color, blur, dx, dy}, outline: {color, width}, gradient: {from, to, angle}}` on the text element.
- **3.2.3 — Text on a curve** (`src/js/editor/text/typography.js`): SVG `<textPath>` referenced from a computed arc `<path>`. Inspector slider -180° to +180°. 0° = straight (no path used). Positive = arc upward (smile). Negative = arc downward (frown). `arcPath(width, angle)` derives the radius from the chord length (`r = (W/2) / sin(θ/2)`). Khmer font detection surfaces a warning that curve support is limited (`isKhmerFont` checks `khmer`, `battambang`, `siemreap`, `nimbus`, `noto sans khmer`, `kantumruy`, `bayon` substrings).

**Part 3.3 — Media editing layer:**

- **3.3.1 — Image crop + aspect ratio** (`src/js/editor/media/crop.js`): crop handles overlay on image selection. Preset ratios — Free / 1:1 / 4:3 / 16:9 / 3:2. Modifies only `cropRect` (normalised 0..1 against source natural dimensions) in the document model — does NOT re-upload. Renderer applies via `object-fit: cover` + `object-position` (CSS live preview) or `drawImage(src, sx, sy, sw, sh, dx, dy, dw, dh)` (Canvas 2D for export). Reset button restores full image. 8 crop handles (nw, n, ne, e, se, s, sw, w) with pointer-events + correct cursors.
- **3.3.2 — Image filters** (`src/js/editor/media/filters.js`): brightness, contrast, saturation, blur, grayscale sliders. Non-destructive — applied at render time via CSS `filter:` for live preview, Canvas 2D `ctx.filter` for export. Stored as `{brightness: 1.2, contrast: 1.1, saturate: 1.0, blur: 0, grayscale: 0}` on the image element. "Reset all" button restores defaults.
- **3.3.3 — Image masking** (`src/js/editor/media/image.js`): 6 presets — none, circle, rounded-4, rounded-12, heart, star. Applied via CSS `clip-path: circle() / inset() / path()`. Custom SVG mask upload deferred per ROADMAP stretch goal.

**Bundle + tests:**

- New modules added to the `index.html` bundle in `docs/route-bundle-sources-v15.json` (the editor ships from `index.html` via the management `editor` route — `designer.html` is a separate landing page with a different, smaller bundle).
- New CSS file `src/css/editor/canvas.css` added to the index.html styles bundle.
- `python3 src/python/build/build_route_bundles.py` rebuilds clean → `ROUTE_BUNDLE_CHECK_PASSED`.
- `tests/editor_text_media_test.py` (3 phases): Phase A — server-side `_RichTextSanitizer` parity (pure Python); Phase B — 16 client-side assertions via Playwright headless Chromium (modules load, sanitizer strips dangerous tags + keeps safe tags + Khmer text preserved, filters round-trip through `normalize()`, crop rect → canvas source coords, text effects produce correct `text-shadow`/`-webkit-text-stroke`/`linear-gradient`/`background-clip`, text-on-curve returns null for 0° and valid SVG paths for ±60° with correct sweep flags, Khmer font detection works, all 6 mask presets produce valid `clip-path` strings, all 4 inspector panels build without throwing); Phase C — `app_server` HTTP smoke verifying the served `bundle-index-v15.js` contains all 6 new module namespaces. All phases pass.
- Bilingual EN+KH labels throughout (shadow / ស្រមោល, outline / ខ្សែព្រំ, gradient / ម៉្យាងពណ៌, curve / ពង្រីកតាមធ្នឹង, crop / កាត់រូប, filters / តម្រង, mask / រូបរាង, brightness / ពន្លឺ, contrast / កម្រិតពណ៌, saturation / តិត្ថភាព, blur / ព្រិល, grayscale / ខ្មៅស).

**Constraints honoured:**

- No new build tools — vanilla JS IIFEs, plain CSS.
- `document.execCommand` used per ROADMAP directive (deprecated but universally supported).
- All 6 modules are idempotent (guarded by `window.<API>.version >= 56`) and safe on non-designer routes (the inspector / overlay binding is a no-op when the editor bridge is missing).
- Server-side `_RichTextSanitizer` remains authoritative on save — client sanitiser is for live preview only.

**Primary files:** `src/js/editor/text/inline-editor.js`, `src/js/editor/text/effects.js`, `src/js/editor/text/typography.js`, `src/js/editor/media/crop.js`, `src/js/editor/media/filters.js`, `src/js/editor/media/image.js`, `src/css/editor/canvas.css`, `docs/route-bundle-sources-v15.json`, `tests/editor_text_media_test.py`.
---

## 0.57.0 — Editor UX: layer panel, pages sidebar, command palette, keyboard shortcuts (Part 3.4)

- **§3.4.1 Layer panel** (`src/js/editor/chrome/layers.js`): right-side panel listing every element in z-order (topmost first). Each row has a visibility eye toggle, lock icon, 48×48 thumbnail (rendered via the typography renderer's `renderThumbnail` adapter when available, else a colored type chip), and an auto-generated name ("Text 1", "Image 2") editable on double-click. HTML5 drag-and-drop reorders elements via the editor bridge's `transact()` API. Locked elements can't be canvas-selected (the editor core already honours `data-locked="true"` for hit-testing). Hidden elements (`visible === false`) are skipped in export pipelines. Multi-select syncs with canvas selection (shift+click = additive).
- **§3.4.2 Pages sidebar** (`src/js/editor/chrome/pages.js`): vertical strip of page thumbnails (150px wide) on the left side of the editor. Renders each page via `OffscreenCanvas` when available; falls back to a regular `<canvas>`. Each thumbnail is cached by a hash of the page's element tree, so unchanged pages skip the re-render entirely. Re-rendering is debounced 300ms after any editor-state change. Click thumbnail → jump to that page; drag thumbnail → reorder pages; right-click → context menu (duplicate / delete / insert above / below); hover between two thumbnails → reveal a small "insert here" affordance. "+" button → add a new blank page.
- **§3.4.3 Command palette (Ctrl+K / Cmd+K)** (`src/js/editor/chrome/command-palette.js`): a searchable list of every action in the editor. Aggregates three sources: (a) `window.EInviteCommandRegistry.list()` — every registered command, (b) pages — quick-jump to any design page, (c) layers — quick-select any layer on the active canvas. fzf-style fuzzy scorer (tight substring match → high score; fuzzy in-order match → lower score; consecutive-match + start-of-word bonuses). Display grouped by category: File, Edit, View, Insert, Format, Arrange, Align, Help. Recently used commands appear at the top (capped at 8, persisted to localStorage). Every command carries `label_en` + `label_km` variants; the active locale picks which one renders.
- **§3.4.4 Keyboard shortcut registry** (`src/js/editor/chrome/shortcuts.js`): a central `Shortcuts` service that listens on `keydown`, matches against a table of `{key, command, when, label_en, label_km, category}`, and dispatches to the command registry. `when` clauses prevent shortcuts from firing in text inputs (`editor-active` matches when no input has focus; `always` accepts; `text-input` only accepts inside inputs). The table is searchable via the Shift+? modal (which opens the unified command palette in "shortcuts" mode). Default bindings include Ctrl+K → palette.open, Shift+? → palette.shortcuts, Ctrl+B → format.bold, Mod+Z → history.undo, Ctrl+G → object.group, Alt+L → layers.togglePanel, Alt+P → pages.toggleSidebar, and 9 more (17 total).
- **CSS** (`src/css/editor/chrome.css`): consolidated stylesheet with 8 sections — base chrome panel, layer panel, pages sidebar, command palette, shortcuts modal, collaboration cursors, comment pins + thread panel, version history timeline. All selectors prefixed with `ei-` so they don't conflict with existing editor styles.
- **Bundle manifest**: added the 7 new JS files + `editor/chrome.css` to BOTH `designer.html` and `index.html` bundles in `docs/route-bundle-sources-v15.json`. Rebuilt all 16 bundles — `python3 src/python/build/build_route_bundles.py --check` passes.
- **Tests**: `tests/editor_chrome_collab_test.py` (phases 1-3 verify the JS modules + bundle wiring statically; phases 4-6 exercise the new HTTP routes via real app server).
- **Primary files:** `src/js/editor/chrome/layers.js` (372 lines), `src/js/editor/chrome/pages.js` (368 lines), `src/js/editor/chrome/command-palette.js` (303 lines), `src/js/editor/chrome/shortcuts.js` (282 lines), `src/css/editor/chrome.css` (320 lines), `tests/editor_chrome_collab_test.py` (phases 1-3 cover the chrome modules)

---

---

## 0.58.0 — Editor UX: live cursors, comment threads, version history (Part 3.5)

- **§3.5.1 Live cursors with names** (`src/js/editor/collab/presence.js`): extends the existing `collaboration-presence-v52.js` (which already wires heartbeat / WebSocket / poll fallback) with the chrome-layer cursor overlay. Stable cursor color derived from the actor id (hash → hue via the same `actorColor` formula as V31 for cross-studio consistency). Label shows the user's display name, or "Guest" if anonymous. Cursors fade after 5s of no movement (CSS opacity transition on `.is-faded`). Throttled to 20Hz (50ms — coarser than the v52 default of 80ms, matching the ROADMAP requirement). Optional Y.js awareness protocol binding via `shareYAwareness(aw)` when the CRDT layer provides an awareness instance — broadcasts cursor position + name + color as ephemeral state (not persisted). Reconciles DOM diff-style: adds new cursors, updates existing, removes stale.
- **§3.5.2 Comment threads** (`src/js/editor/collab/comments.js` + `src/python/features/editor_comments.py`): click the comment tool → click canvas → a pin appears at that coordinate. Type a comment. Other users see the pin (rendered as a numbered circle on `.ei-comment-pins`) and can reply. Resolved threads are hidden by default; toggle to show. @ mentions trigger a notification email via `send_platform_email` — the backend scans the comment body for `@name` tokens, looks up the mentioned user in the `users` table by email/username/id, and sends a notification if SMTP is configured (silently no-ops otherwise so a missing SMTP config doesn't break comment creation).
  - New table `editor_comments (id, invitation_id, page_id, element_id, x, y, author_id, author_name, body, parent_id, resolved_at, created_at)` + 2 indices.
  - Routes: `GET /api/invitations/{id}/editor-comments`, `POST /api/invitations/{id}/editor-comments`, `PUT /api/invitations/{id}/editor-comments/{cid}` (resolve), `DELETE /api/invitations/{id}/editor-comments/{cid}`. (Path is `/editor-comments` instead of `/comments` to avoid colliding with the existing review-comments route on the same path.)
  - All write routes are rate-limited (60/min for create/resolve/delete; 120/min for list).
- **§3.5.3 Version history timeline** (`src/js/editor/history/timeline.js` + `src/python/features/invitation_versions.py`): a timeline of every saved version. Click → preview. Restore from any version. Auto-snapshot rules: every 30 min of active editing OR every 100 editor-command events, whichever first. Capped at 50 snapshots per invitation; oldest pruned. Manual snapshot button in the toolbar (registered as `history.snapshot` command, shortcut Ctrl+Shift+S). Timeline shows: timestamp, author, one-line summary. "Restore" replaces the current document with the snapshot's content; the current state is auto-snapshotted first so restore is reversible.
  - New table `invitation_versions (id, invitation_id, document_json, author_id, author_name, summary, is_auto, created_at)` + 1 index.
  - Routes: `GET /api/invitations/{id}/version-history`, `POST /api/invitations/{id}/version-history` (manual snapshot), `POST /api/invitations/{id}/version-history/{vid}/restore`. (Path is `/version-history` instead of `/versions` to avoid colliding with the existing published-version route at `/api/invitations/{id}/versions`.)
  - All routes rate-limited (60/min for list; 20/min for snapshot/restore).
  - The existing `/api/invitations/{id}/restore` route is now guarded with `"/version-history/" not in path` so it no longer swallows the new restore route.
- **DB schema**: both new tables created idempotently on every `connect()` call (cheap; `CREATE TABLE IF NOT EXISTS`). PostgreSQL mirror added to `_ensure_postgres_schema()` so both backends get the tables.
- **Bilingual EN+KH**: every user-facing string in the new modules has both `label_en` and `label_km` variants (or full `STRINGS` dictionaries per locale). The active locale is resolved via `window.EInviteI18N?.getLocale?.()` or `document.documentElement.lang`, defaulting to English.
- **Tests**: `tests/editor_chrome_collab_test.py` phases 4 (comment CRUD), 5 (snapshot + restore), 6 (rate-limit) exercise every new HTTP route via a real app server. All 6 phases pass.
- **Primary files:** `src/js/editor/collab/presence.js` (200 lines), `src/js/editor/collab/comments.js` (270 lines), `src/js/editor/history/timeline.js` (272 lines), `src/python/features/editor_comments.py` (245 lines), `src/python/features/invitation_versions.py` (175 lines), `src/python/server.py` (+6 routes, +6 handler methods, +schema hooks), `tests/editor_chrome_collab_test.py` (phases 4-6)

> **Note:** The new editor modules mount into the editor's existing chrome (right-side panel slot for layers + comments + history; left-side slot for pages). They auto-mount on `DOMContentLoaded` if the editor bridge is present (`window.EInviteEditorBridge`), and no-op on non-editor pages so they're safe to bundle globally. Every command they register is wired into the existing `EInviteCommandRegistry` so they appear in the command palette + keyboard-shortcut modal automatically.

---


## 0.61.0 — Backend security: field encryption, API keys, session management, admin access controls

- Field-level encryption via `core/crypto.py` (Fernet AES-128-CBC + HMAC-SHA256) with auto-generated `EINVITE_FIELD_ENCRYPTION_KEY`.
- API key management: `api_keys` table, `einv_` prefixed keys hashed with Argon2id, scoped, `GET/POST/DELETE /api/account/api-keys`, 1000/hour rate limit.
- Session management UI: `GET/DELETE /api/account/sessions` with device detection, IP, last active.
- Admin access controls: `_is_admin()` check, `EINVITE_ADMIN_IP_ALLOWLIST` env var, admin session timeout.
- Tenant isolation test suite: `tests/security_tenant_isolation_test.py` — 3 phases, all pass.
- **Primary files:** `src/python/core/crypto.py`, `src/python/server.py` (api_keys_list/create/revoke, sessions_list/revoke/revoke_all, require_api_key, _is_admin)

## 0.64.0 — Admin tools: dashboard, user management, feature flags, audit log, reports

- Admin dashboard: `GET /api/admin/metrics` (8 stat cards with 7-day deltas), `GET /api/admin/system-status` (green/yellow/red).
- User management: `GET /api/admin/users` (cursor-paginated), `POST /api/admin/users/{id}/suspend`, `/unsuspend`.
- Invitation management: `GET /api/admin/invitations`.
- Feature flags: `feature_flags` table, `GET/PUT /api/admin/feature-flags`, `GET /api/feature-flags` (public), 12 initial flags.
- Audit log explorer: `GET /api/admin/audit-events` (filterable, paginated).
- Report queue: `POST /api/reports` (user-facing, 5/day rate limit), `GET /api/admin/reports`, `PUT /api/admin/reports/{id}`.
- Admin test: `tests/admin_tools_test.py`.
- **Primary files:** `src/python/server.py` (admin_metrics, admin_system_status, admin_users_list, admin_user_suspend/unsuspend, admin_invitations_list, admin_feature_flags_list/update, feature_flags_public, admin_audit_events_list, reports_create, admin_reports_list/resolve)

## 0.67.0 — Creator analytics: event model, ingestion, dashboard, charts, privacy, export

- Event model: 11 event types (invitation.view, .view.end, .rsvp.open/submit/abandon, .gallery.open, .link.click, .signup.claim, .poll.vote, .album.upload, .gift.claim).
- Schema: `analytics_sessions`, `analytics_events`, `analytics_summary_daily` tables.
- Ingestion: `POST /api/analytics/events` (batch, 60/min rate limit, sendBeacon-compatible, session upsert on view, close on view.end).
- Creator dashboard: `GET /api/invitations/{id}/analytics` (stats with totalViews/uniqueSessions/uniqueRecipients/avgDurationMs/rsvpConversion, 30-day timeseries, funnel, topReferrers with small-count masking, deviceSplit, scrollDepth with 4 buckets, analyticsEnabled flag).
- Creations table: `GET /api/account/analytics/creations` (sortable, filterable, with views/rsvps/conversion per invitation).
- Export: `GET /api/invitations/{id}/analytics/export?format=csv|json` (CSV with view_count/rsvp_open_count/rsvp_submit_count per session, JSON with sessions+events).
- Privacy controls: `POST /api/invitations/{id}/analytics/disable` (toggle enabled/disabled), `DELETE /api/invitations/{id}/analytics` (purge, returns sessionsDeleted/eventsDeleted).
- Analytics tests: `tests/analytics_ingestion_test.py` (5 phases), `tests/analytics_reports_test.py` (6 phases), `tests/analytics_privacy_test.py` (7 phases) — all pass.
- **Primary files:** `src/python/server.py` (analytics_events_ingest, analytics_invitation_metrics, analytics_creations_list, analytics_export, analytics_disable, analytics_purge), `tests/analytics_*.py`

## 0.68.0 — Editor collaboration: comments, version history

- Editor comments: `editor_comments` table, `GET/POST /api/invitations/{id}/comments`, `PUT /api/invitations/{id}/comments/{id}` (resolve).
- Version history: `invitation_versions` table, `GET/POST /api/invitations/{id}/versions`, `POST /api/invitations/{id}/versions/{id}/restore` (auto-snapshots current state before restore, prunes to 50 versions).
- **Primary files:** `src/python/server.py` (editor_comments_list/create/resolve, invitation_versions_list/create/restore)
