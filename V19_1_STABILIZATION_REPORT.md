# V19.1 Typography Stabilization Report

## Release identity

- Product: **E-invitation-website**
- Release: **V19.1 Typography Stabilization**
- Date: **2026-07-28**
- Input baseline: `e-invitation-platform-advanced-typography-v19.zip`
- Input SHA-256: `59df337fa6970de1b72d64dcb19dcea73950f514824f90534b611de471e410f3`
- Output artifact: `e-invitation-platform-advanced-typography-v19.1.zip`
- Invitation compatibility: **`schemaVersion: 13`**
- Development rule: the V19 input ZIP was inspected and preserved; V19.1 was developed from that ZIP without a broad rewrite or unrelated feature phase.

## Executive result

V19.1 closes the confirmed V19 server-contract, validation, font-security, editor/public parity, responsive auto-fit, multi-column alignment, inspector geometry, mobile transform, thumbnail, and offline-font defects.

The final Linux artifact passed three consecutive executions of:

```text
python release_check.py
```

Each run passed **41 deterministic checks** and **23 required browser suites**, emitted both V19.1 success markers, and exited with code `0`.

```text
EINVITATION_V19_1_ALL_REQUIRED_REVIEW_CHECKS_PASSED
EINVITATION_V19_1_RELEASE_CHECK_PASSED
```

Windows execution is not claimed from the Linux build environment. `RUN_V19_1_RELEASE_CHECK_3X_WINDOWS.ps1` is included for the required target-machine certification.

## Defect-by-defect root cause and correction

### 1. Live server rejected justified text

**Root cause:** Browser schema and renderer accepted `textAlign: "justify"`, but the authoritative `server.py` document validator allowed only `left`, `center`, and `right`. A justified V19 object could appear valid in an inline browser test yet fail authenticated persistence or publication.

**Changed files:**

- `server.py`
- `typography_contract.py`
- `tests/v19_server_typography_contract_test.py`
- `run_review_checks.py`

**Correction:** The server contract now permits `left|center|right|justify`, normalizes the value before storage, and applies the same contract during authenticated create/save/reload/publish. The live test verifies the persisted invitation, publication API, and public browser output.

### 2. V19 typography fields were not authoritatively normalized on the server

**Root cause:** V19 added fields in the client but the server did not enforce matching enums, numeric types, bounds, integer requirements, or the minimum/maximum relationship.

**Changed files:**

- `server.py`
- `typography-contract.json`
- `generate_typography_contract.py`
- `typography_contract.py`
- `editor-schema-v13.js`
- `tests/v19_typography_invalid_input_test.py`
- `tests/v19_server_typography_contract_test.py`

**Correction:** Server-side validation now enforces:

- `font`: trusted registry ID or exactly recognized legacy stack;
- `textAutoFit`: `none|fit`;
- `textAutoFitMax`: finite numeric type, `8..200`;
- `textMinFontSize`: finite numeric type, `8..72`;
- `textWrap`: `normal|balance|pretty`;
- `textColumns`: integer, `1..3`;
- `textColumnGap`: finite numeric type, `0..64`;
- `textAlign`: `left|center|right|justify`;
- `textMinFontSize <= textAutoFitMax`.

Booleans, nulls, arrays, objects, numeric strings at the strict server boundary, non-finite values, malformed values, unknown enums, and out-of-range values are rejected.

### 3. Stored font values were arbitrary CSS strings

**Root cause:** V19 persisted full `font-family` CSS fragments and inserted them into styles. That made the stored document a CSS-string boundary and allowed unsafe or unavailable font promises.

**Changed files:**

- `typography-contract.json`
- `generate_typography_contract.py`
- generated `typography-contract.js`
- generated `typography_contract.py`
- generated `typography-fonts.css`
- `editor-schema-v13.js`
- `renderer-core.js`
- `app.js`
- `font-browser.js`
- `final-polish.js`
- `workflow-final-audit-v7.js`
- `dashboard.js`
- `creative-packs.js`
- `dashboard-enhancements.js`
- `editor-suite.js`
- `final-experience.js`
- `studio-experience.js`
- `ux-refine.js`
- `public-page.js`
- `tests/inline_editor_runtime_test.py`
- `tests/v19_typography_model_test.py`

**Correction:** Documents store only stable IDs. The renderer resolves those IDs through fixed stacks generated from the trusted registry. No document font value is concatenated directly into a style attribute.

#### Font-registry security boundary

Trusted IDs in V19.1 are:

- `noto-sans`
- `noto-serif`
- `noto-sans-khmer`
- `noto-serif-khmer`
- `serif-georgia`
- `sans-arial`
- `sans-trebuchet`

The JSON registry is the editable source. `generate_typography_contract.py` creates matching browser, Python, and CSS artifacts. The server accepts only registry IDs or exact entries from the legacy migration map. The renderer receives a normalized ID and looks up a fixed stack; it never interprets the stored value as CSS.

#### Legacy migration behavior

Known historical values migrate deterministically, for example:

- `Georgia, serif` → `serif-georgia`
- `Arial, sans-serif` → `sans-arial`
- `'Trebuchet MS', sans-serif` → `sans-trebuchet`
- known Noto/Khmer OS Serif stacks → `noto-serif-khmer`
- known Noto/Khmer OS Sans stacks → `noto-sans-khmer`
- known Muol/Noto Serif stack → `noto-serif-khmer`
- empty/inherit client values repair to the safe default `noto-serif`

Unknown raw strings are not guessed. The server rejects them, requiring an explicit supported font selection.

### 4. Hostile font and malformed typography inputs were not negatively tested

**Root cause:** V19’s green report exercised expected values but did not prove that CSS-like strings or malformed types could not cross the persistence/publication boundary.

**Changed files:**

- `tests/v19_typography_invalid_input_test.py`
- `tests/v19_server_typography_contract_test.py`
- `server.py`
- `typography_contract.py`

**Correction:** Negative coverage includes semicolons, CSS comments, `url()`, control characters, unknown IDs, huge strings/content, arrays, objects, nulls, empty strings, unknown enums, non-integer column values, booleans, and non-finite numbers. Tests verify rejection, no partial mutation, no injected published CSS, and no browser console errors.

### 5. Client numeric normalization could create `NaN`

**Root cause:** `Math.max/min(Number(value))` returns `NaN` for malformed input, while the previous validator could still report a usable model. JSON serialization then silently converts non-finite values to `null`.

**Changed files:**

- `editor-schema-v13.js`
- `typography-contract.js`
- `tests/v19_typography_model_test.py`
- `tests/v19_typography_invalid_input_test.py`

**Correction:** A shared `finiteNumber(value, fallback, min, max)` contract repairs invalid client state to finite bounded values. Validation covers `NaN`, infinities, null, empty strings, arrays, objects, malformed strings, and ranges. Serialization assertions prove typography numbers remain finite JSON numbers and never silently become `null`.

### 6. Auto-fit persisted one computed size and overflowed responsively

**Root cause:** V19 mixed the configured size with a single computed result and used inconsistent fit predicates. Public fitting could compare content against its natural height, and responsive public layout did not reliably refit after fonts or container changes.

**Changed files:**

- `renderer-core.js`
- `app.js`
- `public-page.js`
- `editor-schema-v13.js`
- `tests/v19_responsive_autofit_test.py`
- `tests/v19_editor_public_parity_test.py`
- `tests/v19_font_loading_test.py`

**Correction:** V19.1 keeps configured size, minimum, maximum, and computed rendered size separate. The shared fitting engine is side-effect-free and uses the actual available inner width/height and overflow geometry. It runs after initial layout, `document.fonts.ready`, font `loadingdone`, debounced `ResizeObserver`, window resize, text changes, and object resize. Public refitting changes only DOM presentation and never persists into the invitation/publication model.

#### Before/after responsive measurements

Confirmed V19 defect supplied for 320px:

- client width: **134px**
- scroll width: **277px**
- horizontal overflow: **143px**

V19.1 measurements using the final renderer and the same long English/Khmer content:

| Viewport | Client width | Scroll width | Horizontal overflow | Client height | Scroll height | Vertical overflow | Computed size |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 320px | 134px | 118px | 0px | 148px | 140px | 0px | 8px |
| 360px | 151px | 135px | 0px | 166px | 151px | 0px | 8.6px |
| 390px | 164px | 148px | 0px | 180px | 165px | 0px | 9.4px |
| 430px | 181px | 165px | 0px | 198px | 183px | 0px | 10.4px |
| 768px | 323px | 307px | 0px | 354px | 339px | 0px | 19.3px |


At 320px, scroll width decreased from **277px to 118px**, and measured horizontal overflow decreased from **143px to 0px**. The configured size remained 52px, with the computed fit stored only in the rendered DOM.

### 7. Columns broke vertical alignment and editor/public markup diverged

**Root cause:** Multi-column text changed the content box from flex to block, so top/middle/bottom alignment stopped working. Editor and public CSS also differed (`column-fill: balance` versus `auto`), producing different fit results.

**Changed files:**

- `renderer-core.js`
- `app.js`
- `ux-refine.css`
- generated route bundles
- `tests/v19_editor_public_parity_test.py`

**Correction:** Both editor and public output use an outer flex container for vertical positioning and an inner `.typography-flow` wrapper for wrapping and columns. The parity suite covers 1/2/3 columns × top/middle/bottom × short/overflowing content, with English and Khmer, and verifies matching computed sizes and no overflow.

### 8. Advanced layout controls were trapped in a narrow grid cell

**Root cause:** The fieldset inherited one column of `#typographyControls`, measuring about 99px desktop and 140px in the mobile sheet.

**Changed files:**

- `index.html`
- `ux-refine.css`
- `app.js`
- `tests/v19_typography_visual_geometry_test.py`

**Correction:** The section is a full-width grouped accordion with `grid-column: 1 / -1`. Final measurements:

- desktop advanced section: **204px**, approximately **90.3%** of the typography grid width;
- 390px mobile advanced section: **288px**, approximately **92.9%** of the controls width;
- minimum measured mobile input/button height: **44px**.

### 9. Auto-fit size disagreed with the font-size slider

**Root cause:** Auto-fit could compute 8px while the slider’s minimum was 10px, leaving model, label, and native control in conflicting states.

**Changed files:**

- `index.html`
- `app.js`
- `ux-refine.css`
- `tests/v19_typography_runtime_test.py`
- `tests/v19_typography_visual_geometry_test.py`

**Correction:** Configured typography uses one `8..200` contract. While auto-fit is active, the computed size is displayed separately as read-only rendered state. The slider remains the configured maximum rather than being overwritten by responsive computation.

### 10. Mobile transform targets visually overlapped on small objects

**Root cause:** V19 enlarged the visible handles along with touch targets, and normal/tiny selection geometry did not distinguish the interaction area from the visual knob.

**Changed files:**

- `professional-editor-v17.css`
- `professional-editor-v17.js`
- `tests/v19_typography_visual_geometry_test.py`
- inherited `tests/v17_professional_editor_test.py`

**Correction:** Interaction targets remain at least 44×44px, while pseudo-element knobs render at 10–14px. Ordinary mobile objects retain all eight resize handles plus rotation. A tiny-selection layout separates all nine hit targets to avoid overlap; the test checks every pair on a 30×30 object.

### 11. Page thumbnails ignored V19 typography

**Root cause:** `pageThumbnailObjects` used a fixed 5px font and did not project font registry, weight, alignment, wrap, columns, spacing, or line height.

**Changed files:**

- `app.js`
- `renderer-core.js`
- `tests/v19_typography_visual_geometry_test.py`

**Correction:** Thumbnail text uses the shared normalized typography projection and represents trusted font stack, computed/configured size, weight, style, alignment, wrap, columns, gap, letter spacing, and line height.

### 12. No bundled or synchronized English/Khmer font catalog

**Root cause:** V19 named fonts but included no WOFF2 files, `@font-face` rules, license files, or font-readiness synchronization. Offline rendering therefore depended on the operating system.

**Changed files:**

- `assets/fonts/noto-sans-latin-400.woff2`
- `assets/fonts/noto-sans-latin-700.woff2`
- `assets/fonts/noto-serif-latin-400.woff2`
- `assets/fonts/noto-serif-latin-700.woff2`
- `assets/fonts/noto-sans-khmer-400.woff2`
- `assets/fonts/noto-sans-khmer-700.woff2`
- `assets/fonts/noto-serif-khmer-400.woff2`
- `assets/fonts/noto-serif-khmer-700.woff2`
- `licenses/fonts/Noto-OFL-1.1.txt`
- generated `typography-fonts.css`
- `route-bundle-sources-v15.json`
- generated page/route bundles and manifests
- `tests/v19_font_loading_test.py`

**Correction:** V19.1 bundles subsetted Noto Sans, Noto Serif, Noto Sans Khmer, and Noto Serif Khmer regular/bold WOFF2 files with the included OFL license. `font-display: swap` is intentional. Fixed stacks include `Khmer UI` and safe generic fallbacks. The renderer waits/refits after font readiness and loading completion. Tests cover delayed loading and offline public rendering.

## Generated assets and compatibility

- Invitation `schemaVersion` remains `13`.
- Existing V19 invitations migrate recognized legacy font stacks on normalization.
- Existing optional V19 typography fields remain compatible.
- Legacy generated names such as `bundle-*-v15.js/css`, `route-bundles-v15.json`, `page-assets-v15.json`, and `professional-editor-v17.js/css` remain intentionally unchanged to avoid an unrelated route/cache/deployment migration.
- Generated typography/browser/Python/CSS contracts are built from `typography-contract.json` and checked during release.

## Automated test evidence

### Targeted tests added

- `tests/v19_server_typography_contract_test.py`
- `tests/v19_typography_invalid_input_test.py`
- `tests/v19_editor_public_parity_test.py`
- `tests/v19_responsive_autofit_test.py`
- `tests/v19_font_loading_test.py`
- `tests/v19_typography_visual_geometry_test.py`

### Official gate

- deterministic checks per run: **41**
- required browser suites per run: **23**
- Linux consecutive complete runs: **3 passed**
- platform: `Linux-6.12.13-x86_64-with-glibc2.41`
- Python: `3.13.5`
- Chromium executable: `/usr/bin/chromium`

| Run | Command | Deterministic | Browser | Markers | Exit |
|---:|---|---:|---:|---|---:|
| 1 | `python release_check.py` | 41/41 | 23/23 | both present | 0 |
| 2 | `python release_check.py` | 41/41 | 23/23 | both present | 0 |
| 3 | `python release_check.py` | 41/41 | 23/23 | both present | 0 |

Retained logs:

- `V19_1_RELEASE_LINUX_FINAL_1.txt`
- `V19_1_RELEASE_LINUX_FINAL_2.txt`
- `V19_1_RELEASE_LINUX_FINAL_3.txt`

Additional exact commands used during implementation:

```text
python generate_typography_contract.py
python build_editor_bundle.py
python build_editor_bundle.py --check
python build_route_bundles.py
python build_route_bundles.py --check
python build_page_manifests.py
python build_page_manifests.py --check
python run_review_checks.py --skip-browser
python tests/v19_server_typography_contract_test.py
python tests/v19_typography_invalid_input_test.py
python tests/v19_editor_public_parity_test.py
python tests/v19_responsive_autofit_test.py
python tests/v19_font_loading_test.py
python tests/v19_typography_visual_geometry_test.py
python release_check.py
python release_check.py
python release_check.py
```

## Windows acceptance

Windows validation is **pending external execution** because the development environment is Linux. Run from the extracted project directory on the target Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V19_1_RELEASE_CHECK_3X_WINDOWS.ps1
```

Windows acceptance is complete only when all three runs pass and the script prints:

```text
EINVITATION_V19_1_WINDOWS_3X_RELEASE_CHECK_PASSED
```

Any Windows-only failure requires a minimal correction, regression coverage, and restarting all three Windows runs from zero.

## Remaining known limitations

- Three consecutive Windows runs are not certified in this Linux report.
- The bundled subsets cover the supported English/Khmer catalog, not arbitrary scripts or every Unicode character.
- `font-display: swap` may briefly show a fixed fallback during slow font loading; the fitting engine deliberately refits after font completion.
- Arbitrary user-supplied font-family CSS and custom font uploads are intentionally unsupported at this security boundary.
- Unknown historical raw font strings are rejected rather than heuristically interpreted.
- Browser visual geometry is certified with the required Chromium engine; Windows Chromium execution remains pending.
- Advanced masks, vector paths, effects stacks, collaboration expansion, and unrelated feature work were not started in V19.1.
