# V20 Typography System Report

## Release identity

- Product: **E-invitation-website**
- Release: **V20 Shared Typography System and Editor UX — Completion Pass**
- Date: **2026-07-29**
- Sole baseline: `e-invitation-platform-advanced-typography-v19.1.zip`
- Baseline SHA-256: `dfcdf3ec080e67cf0613c550778aafbaf8101e5464b8281cb933d486e6c0e77a`
- Baseline preservation: V19.1 remains untouched; V20 was developed in a separate directory.
- Invitation compatibility: **`schemaVersion: 13`**
- Typography model version: **`1`**
- Output directory name: `e-invitation-platform-typography-system-v20-completed`

## Executive result

V20 turns the repaired V19.1 typography features into a shared system rather than a collection of page-specific controls and renderer fragments. The release adds one normalized typography document model, one generated trusted font contract, one layout/measurement/diagnostic service, renderer adapters, semantic invitation-level styles, linked style updates, object overrides and detachment, undoable style management, a reorganized editor inspector, contextual toolbar controls, responsive editor/public comparison, thumbnail overflow indicators, mobile editing refinements, Khmer grapheme safeguards, and typography accessibility diagnostics.

The implementation preserves the V19.1 security boundary: documents store trusted font IDs and pairing IDs, not arbitrary CSS font-family strings. Server normalization remains strict. Responsive public fitting changes only DOM presentation and never writes a computed size into the persisted invitation document.

### Verification classification

This package is an **implementation candidate with substantial verified coverage**, not a falsely certified cross-platform final release:

- The complete deterministic suite passed **42/42 checks three consecutive times on Linux** after the final toolbar correction.
- **21 direct real-Chromium suites passed** after the completion work, including the V20 editor, font, rendered Khmer shaping, keyboard/focus accessibility, semantic editor/public parity, inherited V19 typography, and inherited editor/runtime suites.
- Seven browser suites that navigate to a locally served HTTP URL cannot complete in the current sandbox because Chromium returns `ERR_BLOCKED_BY_ADMINISTRATOR` for both loopback and non-loopback container addresses. Their non-browser API setup runs until the blocked navigation point.
- Native Windows execution is not available in this environment. `RUN_V20_GATE_3X.bat` is included for three-run Windows certification.

## Deliverables

- `e-invitation-platform-typography-system-v20-completed.zip`
- `V20_TYPOGRAPHY_SYSTEM_REPORT.md`
- `FONT_LICENSES_AND_REGISTRY.md`
- `UPDATED_TEST_MATRIX.md`
- `V21_RICH_TEXT_AND_PARAGRAPH_PLAN.md`

## Phase A — shared typography architecture

### 1. Authoritative TypographyDocumentModel

The browser model is implemented in `typography-document-model.js`, with the strict server-side mirror in `typography_document_model.py`.

The model owns:

- the semantic style catalog;
- text-style IDs and ordering;
- style normalization;
- legacy flat-field migration;
- linked/detached object state;
- per-field overrides;
- resolved typography snapshots used to distinguish a real legacy flat-field edit from an unchanged compatibility projection;
- locale detection;
- color-token resolution;
- object traversal across the hero canvas and design pages;
- create, rename, duplicate, update, delete-with-replacement, link, detach, override, reset, and linked-count operations.

The authoritative persistence boundary is server-side `normalize_document_typography(document, strict=True)`, invoked from `server.py` before document acceptance. The browser model is loaded before schema, renderer, editor, public, and dashboard code through `route-bundle-sources-v15.json`.

### 2. Trusted FontRegistry

`typography-contract.json` is the editable source of truth. `generate_typography_contract.py` deterministically generates:

- `typography-contract.js` for browsers;
- `typography_contract.py` for server validation;
- `typography-fonts.css` for bundled `@font-face` declarations.

The registry provides stable IDs, fixed stacks, metadata, script coverage, pairings, license metadata, WOFF2 assets, per-asset SHA-256 digests, and exact legacy migrations. Full details are in `FONT_LICENSES_AND_REGISTRY.md`.

### 3. TypographyLayoutService

`typography-layout-service.js` owns the shared runtime behavior for:

- outer flex geometry and vertical alignment;
- inner `.typography-flow` wrapping and columns;
- deterministic style-object and style-string generation;
- available-space measurement;
- binary-search auto-fit using the inherited deterministic fitter;
- DOM-only computed font size;
- overflow measurement and diagnostics;
- resize and font-ready refitting;
- contrast measurement;
- narrow-column warnings;
- Khmer/locale-aware grapheme segmentation and cluster preservation checks;
- real renderer-backed thumbnail construction, 390×844 hidden measurement, responsive scaling, and measured overflow badges.

### 4. Renderer adapters

`renderer-core.js` exposes `EInviteTypographyRendererAdapters`. Editor rendering, public rendering, responsive previews, and thumbnail surfaces now project through the normalized model and shared layout service rather than accepting document CSS strings.

Duplicate style builders and page-specific fitting controllers were removed. Renderer adapter functions require `TypographyLayoutService`; bundle ordering guarantees that the shared model and service load before renderer/editor/public/dashboard code.

## Phase B — reusable text styles

### 5. Built-in semantic styles

V20 creates six invitation-level semantic styles:

| Stable style ID | Display name | Typical role |
|---|---|---|
| `display` | Display | Main invitation names/title |
| `heading` | Heading | Section headings |
| `subheading` | Subheading | Supporting heading text |
| `body` | Body | General invitation copy |
| `caption` | Caption | Small labels and supporting metadata |
| `khmer-ceremonial` | Khmer Ceremonial | Prominent formal Khmer text |

Each style supports:

- English/Khmer font pairing;
- configured size;
- auto-fit mode;
- maximum and minimum size;
- weight and italic style;
- line height and letter spacing;
- color token and optional validated hex override;
- horizontal and vertical alignment;
- wrapping mode;
- one to three columns;
- column gap and text-box padding.

### 6. Link, detach, and override behavior

A text object stores:

- `textStyleId` — linked semantic/custom style;
- `typographyDetached` — whether the object owns a complete resolved copy;
- `typographyOverrides` — only the fields that differ from the linked style;
- `typographyResolvedSnapshot` — the previous normalized projection used for safe legacy command compatibility;
- `typographyModelVersion` — current model version.

A linked object receives style updates automatically. Detaching captures the resolved typography into the object. Resetting an override restores the linked style value. No raw `font-family` string is stored.

### 7. Undoable style management

All style and object operations execute through the existing `EInviteCommands`/history transaction boundary. The V20 editor includes accessible dialogs for:

- create;
- edit;
- rename;
- duplicate;
- delete with required replacement selection;
- link;
- detach;
- reset override.

Deletion and replacement are one command, so undo restores both the style and previous object links. Editing a linked style is one command and updates all linked objects together.

## Phase C — editor experience

### 8. Contextual toolbar

`typography-editor-v20.js` adds a text-only contextual toolbar containing:

- style;
- font;
- configured size or auto-fit maximum;
- bold;
- italic;
- alignment;
- color;
- auto-fit status;
- responsive typography preview.

The preview trigger was deliberately placed in the V20 contextual toolbar rather than the inherited fixed canvas toolbar. This corrected a detected 19px V16 toolbar overflow and preserved the inherited desktop geometry budget.

### 9. Full-width inspector groups

The typography inspector is reorganized into exactly five full-width groups:

1. **Text**
2. **Paragraph**
3. **Auto-fit and overflow**
4. **Columns**
5. **Advanced appearance**

It exposes configured maximum, current computed size, minimum size, overflow state, and warning messages.

### 10. One-click actions

- **Fit**: refits the current DOM box without persisting a computed size.
- **Expand box**: increases object height in one undoable command.
- **Reduce text**: reduces configured size or auto-fit maximum in one undoable command.
- **Reset override**: removes object-specific typography overrides.

### 11. Responsive comparison

The editor provides side-by-side editor/public rendering at:

- 320px
- 360px
- 390px
- 430px
- 768px

The left pane clones and refits the actual live editor DOM; the right pane constructs the actual public-renderer DOM. Both resolve the same normalized semantic-style model. The dedicated semantic parity suite compares all five widths, linked styles, overrides, computed font sizes, and overflow without altering the saved document.

### 12. Faithful thumbnails

Hero/design-page and dashboard thumbnails are created through the public renderer adapter, measured in an off-screen 390×844 artboard with the bundled fonts and shared fitter, then scaled into the thumbnail surface. Overflow badges are based on actual scroll geometry rather than character-capacity estimates and carry screen-reader labels.

### 13. Mobile editing

`typography-system-v20.css` retains the canvas peek while the inspector becomes a bottom sheet, adds a compact selected-text summary, uses visually small transform handles with expanded hit areas, keeps typography inputs at least 44px high, and preserves the canvas viewport scroll position across V20 commands.

## Phase D — language quality and accessibility

### 14. Khmer behavior

The shared layout service uses `Intl.Segmenter` with grapheme granularity when available and a conservative Khmer-mark fallback otherwise. It merges coeng/ZWJ continuation sequences, verifies exact source reconstruction, rejects leading combining-mark segments, and exposes rendered-cluster integrity measurement.

The real-Chromium Khmer test loads the bundled Noto Serif Khmer WOFF2 font and measures DOM `Range` rectangles for every grapheme in narrow boxes, left/justified alignment, and one/two-column layouts. It covers consonants, dependent vowels, combining signs, coeng sequences, zero-width controls, and mixed English/Khmer text, and fails if one grapheme occupies more than one rendered line.

### 15. Diagnostics

The shared service emits warnings for:

- unreadably small text;
- potentially difficult small text;
- clipped horizontal or vertical content;
- insufficient contrast using WCAG-style luminance ratios;
- excessive columns for the available width.

Error-state diagnostics set `aria-invalid="true"`. Inspector status and warnings use polite live regions.

### 16. Keyboard and screen-reader support

V20 controls use native button/input/select/dialog semantics, programmatic labels or associated label text, visible `:focus-visible` outlines, toolbar/group/dialog roles, `aria-pressed` for toggles, `aria-live` status regions, and descriptive overflow labels. The completion pass also prevents legacy capture shortcuts from consuming Enter on focused controls, supports Enter and Space activation, keeps modal Escape from clearing canvas selection, assigns dialog names, moves focus into dialogs, and restores it to the invoking control.

## Security and validation guarantees preserved

- Font persistence accepts trusted stable IDs or exact legacy migration strings only.
- CSS-like font payloads, unknown pairings, malformed IDs, unsupported override keys, non-finite values, numeric strings at strict boundaries, arrays/objects, control characters, invalid enums, and out-of-range values are rejected.
- Style catalogs are bounded to 64 entries and IDs/names are length-limited.
- Columns remain integer `1..3`.
- Minimum size cannot exceed maximum size.
- Hex colors are restricted to six-digit `#RRGGBB` values.
- Public responsive fitting never mutates the persisted configured size.
- Existing CSP, authentication, storage, upload signing, privacy, revision, permission, and hostile-input tests remain enabled.
- V20 does not add masks, vector paths, collaboration features, or Photoshop filters.

## Principal source changes

### Added

- `typography-document-model.js`
- `typography_document_model.py`
- `typography-layout-service.js`
- `typography-editor-v20.js`
- `typography-system-v20.css`
- `tests/v20_typography_architecture_test.py`
- `tests/v20_typography_editor_runtime_test.py`
- `tests/v20_font_registry_loading_test.py`
- `tests/v20_khmer_shaping_test.py`
- `tests/v20_typography_accessibility_test.py`
- `tests/v20_semantic_style_parity_test.py`
- `RUN_V20_GATE_3X.sh`
- `RUN_V20_GATE_3X.bat`

### Integrations changed

- `typography-contract.json`
- `generate_typography_contract.py`
- generated typography contract files
- `editor-schema-v13.js`
- `renderer-core.js`
- `app.js`
- `public-page.js`
- `dashboard.js`
- `final-polish.js`
- `workflow-ux-v5.js`
- `server.py`
- route source/manifests and generated bundles
- `run_review_checks.py`
- `release_check.py`
- `BUILD_INFO.json`
- `README.md`

## Test evidence summary

### Deterministic Linux evidence

| Run | Result | Evidence |
|---:|---|---|
| 1 | 42/42 passed | `test-results/v20-completion/deterministic-gate-1.log` |
| 2 | 42/42 passed | `test-results/v20-completion/deterministic-gate-2.log` |
| 3 | 42/42 passed | `test-results/v20-completion/deterministic-gate-3.log` |

### Direct Chromium suites completed

The following completed successfully after the final source/bundle regeneration:

- `v20_typography_editor_runtime_test.py`
- `v20_font_registry_loading_test.py`
- `v20_khmer_shaping_test.py`
- `v20_typography_accessibility_test.py`
- `v20_semantic_style_parity_test.py`
- `v19_typography_runtime_test.py`
- `v19_editor_public_parity_test.py`
- `v19_responsive_autofit_test.py`
- `v19_typography_visual_geometry_test.py`
- `inline_editor_runtime_test.py`
- `v16_browser_geometry_test.py`
- `v17_professional_editor_test.py`
- `v17_layers_clipboard_history_test.py`
- `v10_browser_runtime_test.py`
- `v11_browser_runtime_test.py`
- `v12_browser_stabilization_test.py`
- `v13_browser_runtime_test.py`
- `editor_layout_geometry_test.py`
- `public_layout_runtime_test.py`
- `public_guest_feature_runtime_test.py`
- `theme_launcher_runtime_test.py`

### Environment-blocked suites

The current Chromium binary launches and executes inline/data-backed tests, but policy blocks navigation to any locally served HTTP address. The observed failure is:

```text
Page.goto: net::ERR_BLOCKED_BY_ADMINISTRATOR at http://127.0.0.1:<port>/...
```

This affects seven server-backed browser suites. It is not converted to a skip or pass. A final `python release_check.py` execution regenerated and verified all assets, passed all 42 deterministic suites, then stopped at `v14_static_server_test.py` with this policy error. The complete raw output is retained in `test-results/v20-completion/full-release-check-sandbox.log`; all seven served suites remain required.

### Required external completion

Run on an unrestricted Linux host:

```bash
./RUN_V20_GATE_3X.sh
```

Run on native Windows:

```bat
RUN_V20_GATE_3X.bat
```

All three complete runs must produce `EINVITATION_V20_ALL_REQUIRED_REVIEW_CHECKS_PASSED` and `EINVITATION_V20_RELEASE_CHECK_PASSED` before promoting the candidate to a fully cross-platform certified release.

## Explicit V20 non-goals

Not implemented in V20:

- per-range rich-text formatting;
- paragraph style hierarchy;
- lists, tabs, or links as structured runs;
- vector paths;
- masks;
- nested scene-tree transformation redesign;
- collaboration foundations;
- Photoshop-style filters.

The next typography phase is documented in `V21_RICH_TEXT_AND_PARAGRAPH_PLAN.md` only.
