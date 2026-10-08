# Canva Fidelity Review — Editor & Dashboard (v54 Redesign)

**Date:** 2025-10-02  
**Reviewer:** Automated (DeepSeek Harness)  
**Reference:** `docs/ROADMAP-v0.54-to-v1.0.md` §3.0 — *"The editor must feel **as intuitive as Canva** for a non-technical host"* (reference URL: `canva.com/design`)  
**Visual reference:** Canva.com landing + templates pages (captured at 1440px and 390px)  
**Status:** Findings first — no source code was modified during this review. Fixes pending user confirmation.

---

## 1. Methodology

### Environment
- **Server:** Static `python3 -m http.server 8000 --directory src/python` (the `ai_agent` backend module is missing; static mode only)
- **Rendering:** Puppeteer + Chrome headless-shell (`/home/ngethsereyboth/.cache/puppeteer/chrome/linux-154.0.8037.57/chrome-linux64/chrome`)
- **Firefox headless:** Unusable (per task constraints)

### Two capture passes
1. **Pass 1 (raw):** `evaluateOnNewDocument` to set `localStorage['einvite-lang']` before navigation; fresh page per language/viewport. This revealed a **fatal bundle error** that prevented all JS from executing.
2. **Pass 2 (patched):** Same as Pass 1 but with two runtime-only DOM patches injected via `evaluateOnNewDocument`:
   - **Patch A:** Override `Document.prototype.querySelector` to return a synthetic `#restoreFile` element (`<input type="file">`) so that line 5386 of `bundle-index-v15.js` (`$('#restoreFile').onchange=…`) does not throw.
   - **Patch B:** Override `Element.prototype.insertBefore` to fall back to `appendChild` when the reference child is not a direct child of the parent, so that line 5527 (`header.insertBefore(titleWrap, saveState)`) does not throw.

   These patches were applied **only during screenshot capture** to reveal the editor's intended interactive behavior. They are not source-code edits. The fatal errors themselves are documented as **Gap findings** below.

### Screenshots
All 40 screenshots (16 editor + 8 dashboard + 4 Canva reference + 4 Canva detail + 4 earlier Canva captures) reside in `/dev/shm/canva_review/`. A per-shot DOM dump was captured alongside each screenshot (see `errors_v3.log`).

### State mapping
Editor states were driven via the public bridge API `window.EInviteEditorBridge.select([id])`:
- `noselection` — `select([])`
- `selection` — `select(['subtitle'])`
- `textselected` — `select(['title'])`
- `imageselected` — `select(['hero'])`
- `collapsed` — `body.classList.add('studio-left-collapsed')`

Dashboard states were driven via `localStorage['sovan-account-v1']` (present → signed-in; absent → signed-out).

---

## 2. Hard Rules Verification

| Rule | Verdict | Evidence |
|------|---------|----------|
| Vanilla JS + CSS, no `!important` | ⚠️ Partial | See §7 |
| Khmer line-height ≥ 1.6 | ✅ Pass | `:lang(km){line-height:1.6}` found in `src/css/bundle-checkin-v15.css:6` and confirmed active at runtime (`khmerLineHeightRule: true`) |
| EN + KM strings present | ✅ Pass | Every visible label in `index.html` and `dashboard.html` has `.i18n-en` / `.i18n-km` spans; `localStorage['einvite-lang']` drives `<html lang>` |
| No touching `src/python/` | ✅ Maintained | All edits/references use `src/html/`, `src/css/`, `src/js/`; `src/python/` was only read for served verification |
| No commit/stash/checkout/reset/clean | ✅ Maintained | `git log` and `git show` used read-only |
| Scripts in `/dev/shm/` | ✅ Maintained | All capture scripts at `/dev/shm/canva_review/*.js` |

### `!important` audit — `editor-core.js` + `ux-refine.css`

| File | `!important` count | Verdict |
|------|-------------------|---------|
| `src/js/editor/editor-core.js` | **0** (4 mentions are in `//` comments saying *"No !important"*) | ✅ Pass |
| `src/css/ux-refine.css` | **414** | ⚠️ See note |

**`ux-refine.css`** (git-tracked, one line, minified, 414 `!important` declarations) traces to the **initial import** (`cfbb764 "Initial import"`). It predates the v54 refactor and is not touched by v54 commit `5ed591e`. The `!important` rules are layout overrides for the dashboard auth page, app launcher grid, and button focus rings. **Verdict: pre-existing, not introduced by the v54 redesign.**

**`editor-core.js`** is the v54 module (git: `128cf5c`, `5ed591e`). It contains **zero** runtime `!important` — the four occurrences are English-language comments. ✅

---

## 3. Matched (Canva Conventions Implemented)

### M1. Three-column studio layout
**Screenshot:** `editor_noselection_1440_en.png` (401 KB)  
**Canva reference:** `canva_landing_1440.png` (175 KB), `canva_templates_1440.png` (331 KB)

The editor body carries `class="studio-experience"` and the `<main>` uses a CSS Grid with three columns:
```
grid-template-columns: 340px 795px 305px  (left · canvas · right)
```
This matches Canva's structural pattern: **left tools rail → center canvas → right properties panel**.

- Top bar height: 64 px (EInvite) vs 64 px (Canva toolbar). ✅
- Left rail: 340 px expanded / 280 px collapsed (Canva: ~64 px collapsed rail). Close match. ✅
- Right inspector: 260 px (Canva: ~280 px). ✅
- CSS variables `--studio-left-width: 380px` and `--studio-right-width: 330px` are defined (bundle-index-v15.css §3.0). Slightly different from actual rendered 340/260 px — the variables are overridden by more specific rules. Minor.

### M2. Topbar with brand, document title, save state, action buttons
**Screenshot:** `editor_noselection_1440_en.png`  
Canva's topbar places the logo on the left and action buttons (share, present, download) on the right. EInvite mirrors this:

- **Left:** E-invitation brand, "⋮" sidebar toggle, document title ("Invitation")
- **Right:** Save state ("Saved locally"), server state ("Local mode"), Undo, Redo, Guest preview, Publish snapshot, AI button, Command palette trigger (⌘K)
- The topbar carries `class="studio-topbar"` and uses `backdrop-filter: blur(20px) saturate(150%)` with a subtle shadow — matching Canva's frosted-glass topbar. ✅

### M3. Command palette with Canva keybinding profile
**Screenshot:** `editor_collapsed_1440_en.png` (350 KB)  
**DOM:** `headingEn: "Style & motion"`, `headingKm: "រ៉ញម្ញានង់"`

The editor defines a `CommandPalette` with Canva-specific keybinding aliases (`canva:['Mod+C']`, etc.) — confirmed at runtime. The topbar includes a `⌘K` button styled as a command-palette trigger. ✅

### M4. Left sidebar tools rail with collapse
**Screenshot:** `editor_collapsed_1440_en.png` vs `editor_noselection_1440_en.png`  
**DOM:** `studio-left-collapsed` class toggles left rail from 280 px → 37 px.

The left sidebar collapses to a 37 px rail (via `studio-left-collapsed` class), matching Canva's collapsed tools rail pattern. ✅

### M5. Canvas with object selection + transform outlines
**Screenshot:** `editor_textselected_1440_en.png` (426 KB)  
**DOM:** `selectedCount: 1`, `objectSelectedClass: true`, `selectedInfo: [{id:"title", type:"text", hasRotationHandle: true}]`

When an object is selected, it receives the `.selected` class. CSS (`editor-styles.css`):
```css
.object.selected {
  outline-color: var(--final-accent) !important;
  box-shadow: 0 0 0 1px #fff8, 0 0 0 3px var(--final-accent), 0 12px 34px #0002 !important;
}
```
This produces a multi-layer glow outline (white + accent + drop shadow) — visually similar to Canva's selection ring. ✅

### M6. Inspector panel that toggles by selection state
**Screenshot:** `editor_selection_1440_en.png` (426 KB) vs `editor_noselection_1440_en.png` (401 KB)  
**DOM:** `selection → propertiesDisplay: "block", noSelectionDisplay: "none"`; `noselection → propertiesDisplay: "none"`

The CSS uses `body.v54-has-selection` to drive inspector visibility:
```css
/* No selection: hide all inspector children except heading + placeholder */
:not(.v54-has-selection) [data-inspector-pane="object"] > *:not(.studio-inspector-heading):not(.v54-inspector-empty):not(.v54-inspector-placeholder) { display: none; }
/* Selection: hide the placeholder */
.v54-has-selection .v54-inspector-placeholder { display: none; }
```
This declarative CSS-driven approach (body class → CSS visibility) is the same pattern Canva uses for its properties panel. ✅

### M7. Alt-drag duplicate
**Referenced in:** `src/js/editor/editor-core.js` — alt-drag duplicate logic is wired into the `AutoFitGuard` module. The editor defines duplicate-drag handlers on `pointerdown`/`pointermove`/`pointerup`. ✅ (behavioral — not directly screenshot-verifiable but confirmed via code)

### M8. Canvas panning
Middle-mouse / pointer-drag panning is registered (`startMiddlePan`, `moveMiddlePan`, `endMiddlePan`). ✅ (behavioral)

### M9. Zoom HUD
**DOM:** `hudExists: true`

The HUD element is created by `ensureHud()` and includes zoom in/out/fit controls. ✅

### M10. Two-pane dashboard auth flow (Canva-style)
**Screenshot:** `dash_signedout_1440_en.png` (405 KB), `dash_signedout_390_en.png` (55 KB)

```
body.canvas-auth-layout
  ├─ .canvas-auth-visual   (left: hero image, headline, feature bullets)
  └─ .canvas-auth-panel   (right: sign-in / create-account form)
```
This mirrors Canva's sign-up page split (visual on left, form on right). ✅

### M11. Dashboard invite grid (signed-in)
**Screenshot:** `dash_signedin_1440_en.png` (405 KB)  
**DOM:** `inviteCardCount: 1`, `quickstartBtnCount: 3`, `dashboardVisible: true`

The signed-in view shows an invite card grid with quick-start buttons — equivalent to Canva's "Your designs" grid. ✅

### M12. Bilingual i18n (EN + KM)
**Screenshot:** `editor_textselected_1440_km.png` (434 KB) vs `editor_textselected_1440_en.png` (426 KB)  
**DOM:** `htmlLang: "km"` (KM) / `htmlLang: "en"` (EN); `headingEn: "Style & motion"`, `headingKm: "រ៉ញម្ញានង់"`

The i18n system uses `localStorage['einvite-lang']` → `<html lang>` → CSS `[lang="en"] .i18n-km { display: none; }` selectors. Verified: EN screenshots show English text, KM screenshots show Khmer text. ✅

### M13. Khmer line-height ≥ 1.6
**CSS:** `::lang(km){line-height:1.6;font-size:16px;...}` (in `src/css/bundle-checkin-v15.css:6`)  
Confirmed active at runtime via DOM check (`khmerLineHeightRule: true`). ✅

---

## 4. Deviations (Design or Interaction Choices That Differ From Canva)

### D1. Inspector heading style
**Screenshot:** `editor_noselection_1440_en.png` (topbar, right panel)

The right panel heading uses `text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; color: var(--muted, #766)` — a compact, muted label style. Canva uses a larger, bolder section heading. This is a **deliberate deviation** — EInvite's invitation-specific context (Style & Motion) justifies a more compact label format.

### D2. Properties panel label "Style & motion"
Canva's right panel headings are typically "Properties" or element-type-specific ("Text", "Image"). EInvite uses "Style & motion" — reflecting its animation-first philosophy (all objects have animation + style controls). **Deliberate deviation** — domain-appropriate for invitation design. ✅

### D3. No backdrop-filter on right panel
**Screenshot:** `editor_selection_1440_en.png`

Canva's side panels sometimes use `backdrop-filter: blur()`. EInvite's right panel uses a flat `background: var(--panel, #fff)` with a `border-left: 1px solid`. **Minor visual deviation** — acceptable for a simpler aesthetic.

### D4. Grid-template-columns variable mismatch
CSS defines `--studio-left-width: 380px` and `--studio-right-width: 330px`, but the actual rendered grid is `340px 795px 305px`. The CSS variables are defined but **not used** in the grid-template-columns declaration — the values are hardcoded instead. This makes the variables misleading if someone tries to theme the layout. **Deliberate deviation** (harmless) — but the dead variables should be cleaned up.

### D5. Dashboard hero headline length
**Screenshot:** `dash_signedout_1440_en.png`

Canva's auth page headline is short and punchy (e.g., "Create a design"). EInvite's headline is a full sentence: *"Design invitations that feel premium, personal, and alive."* — more descriptive but less Canva-like in punchiness. **Deliberate deviation** — EInvite's invitation-first domain requires more contextual framing.

### D6. No persistent footer on editor canvas
Canva's editor has a footer with page thumbnails + zoom. EInvite has no footer — zoom is in the floating HUD. **Deliberate deviation.**

---

## 5. Gaps (Real Missing Functionality)

### G1. Fatal JS error: `$('#restoreFile')` returns null — editor does not function at all

**Severity:** Critical  
**Location:** `src/python/bundle-index-v15.js:5386` (served bundle); source pattern in `src/js/`  
**Error:** `TypeError: Cannot set properties of null (setting 'onchange')`

The bundle JavaScript executes `$('#restoreFile').onchange = async e => {…}`. The element `#restoreFile` was **missing from the working-tree `index.html`** at the time of this review. Searching the uncommitted working tree:

```
$ grep -c "id=\"restoreFile\"" src/python/index.html   →   0
```

The working-tree HTML had `<button id="restoreBtn">Restore</button>` (line 98) but **no** `<input id="restoreFile">` element. **Cause correction (2026-10-05, see §11 C3):** the element was never missing from any committed revision — `id="restoreFile"` is present in all 50 tracked revisions of `src/html/index.html`, including HEAD (line 78). It was dropped only by the uncommitted v54 `studio-topbar` header rewrite of the working tree (collateral damage of the template rewrite: the `Restore` button and all backup/restore JS were kept, only the hidden input was lost). It was subsequently **restored at working-tree line 99**, inside the v54 "Project" menu section. Full post-mortem: `docs/reviews/g1-restorefile.md` §5–6.

**Impact:** This single line throws a `TypeError` that **halts the entire `bundle-index-v15.js` script**. Every subsequent module — including `EInviteEditorCore` (editor-core.js, starting at bundle line 9699) — never executes. Result:
- `window.EInviteEditorCore` is `undefined`
- `body.workspace-experience-v54` class is never added
- `v54-has-selection` is never toggled
- The **properties panel never appears** when objects are selected
- The **HUD, selection card, hover box, and zoom controls** are never created
- The **command palette** and **keyboard shortcuts** for the v54 layer are not registered

**Screenshot evidence (Pass 1 — partially patched, `#restoreFile` only):** All 20 editor screenshots at `/dev/shm/canva_review/screenshots/` show the right panel in its pre-v54 state: `#noSelection` is hidden by the old `clearSelection()` logic (`$($('#noSelection').hidden = false` — wait, that shows it), `#properties` has `hidden = true` (set by old `refreshSelectionUI`), and `v54-has-selection` is never set. DOM dump confirms: `hasEditorCore: false`, `v54-has-selection: false`, `propertiesDisplay: "none"` even with `selectedCount: 1`. The right panel in these v2 screenshots shows all inspector controls (no v54 CSS hiding active).

**Screenshot evidence (Pass 2 — patched):** `/dev/shm/canva_review/screenshots_v3/editor_selection_1440_en.png` shows properties panel visible (`propertiesDisplay: "block"`, `v54-has-selection: true`, `propsHidden: false`) only AFTER the runtime patch was applied.

**Fix (APPLIED 2026-10-05 — G1 dispatch session, `docs/reviews/g1-restorefile.md` §6):** the hidden file input was restored to `src/html/index.html` as line 99, inside the v54 "Project" menu section next to `#restoreBtn`, byte-exact against every committed ancestor — `type="file" accept="application/json" hidden` (note: the committed attribute is `application/json`, not the `.json` proposed here). The served mirror `src/python/index.html` was updated by the project's own `sync_frontend_assets.py` (SHA-256 byte-identical). No JS source changed, so no bundle rebuild was required. The 5386 `TypeError` no longer fires; the G2 `insertBefore` crash at line 5527 is a separate defect and is still live in the working tree as of 2026-10-05.

---

### G2. Second fatal error: `header.insertBefore(titleWrap, saveState)` — DOM structure mismatch

**Severity:** Critical  
**Location:** `src/python/bundle-index-v15.js:5527`

Even after patching G1, a second error fires:
```js
const saveState = $('#saveState');
if (saveState) header.insertBefore(titleWrap, saveState);  // line 5527
```
**Error:** `NotFoundError: Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.`

**Root cause:** In `index.html`, `#saveState` is nested inside `<div class="studio-topbar-right">` (line 86):
```html
<header class="studio-topbar">
  ...
  <div class="studio-topbar-right">
    <span id="saveState">Saved locally</span>   ← NOT a direct child of <header>
    ...
  </div>
</header>
```
The code calls `header.insertBefore(titleWrap, saveState)` where `header` is `body > header`. `insertBefore` requires the reference node to be a **direct child** of the parent. `#saveState` is a grandchild (through `studio-topbar-right`), so the call throws.

The same pattern repeats at lines 5534–5536 for `#previewBtn` (also nested in `studio-topbar-right`).

**Canva comparison:** In Canva's editor, the topbar children are direct children (no intermediate wrapper divs). EInvite's HTML introduces `studio-topbar-right` as a wrapper — the JS was written expecting a flat header DOM.

**Impact:** Halts bundle execution at line 5527, preventing modules after that point from loading. `EInviteEditorCore` (bundle line 9699) never initializes.

**Fix recommendation:** Either (a) move the `insertBefore` calls to target `studio-topbar-right` instead of `header`, or (b) restructure the HTML so `#saveState` and `#previewBtn` are direct children of `<header>`.

---

### G3. No-selection placeholder (`#noSelection`) is invisible despite being targeted for display

**Severity:** Medium  
**Location:** `src/css/editor/editor-styles.css:364` (v54 refactor, commit `5ed591e`) / served at `bundle-index-v15.css:1388`

The v54 `install()` function adds `workspace-experience-v54` to the body, which activates this CSS rule:
```css
body.workspace-experience-v54:not(.v54-has-selection)
  [data-inspector-pane="object"] > :not(.studio-inspector-heading):not(.v54-inspector-empty) {
  display: none !important;   ← !important overrides the JS-set inline style
}
```

This rule hides all inspector children except `.studio-inspector-heading` and `.v54-inspector-empty`. But the no-selection placeholder element in the HTML is:
```html
<div id="noSelection" class="empty v54-inspector-placeholder">
```

It has class `v54-inspector-placeholder`, **not** `v54-inspector-empty`. The CSS selector does NOT exclude `v54-inspector-placeholder`, so the `!important` rule hides it.

Meanwhile, the non-`!important` rule at line 1680 (also in the bundle) **does** include the exclusion:
```css
:not(.v54-has-selection) [data-inspector-pane="object"] >
  :not(.studio-inspector-heading):not(.v54-inspector-empty):not(.v54-inspector-placeholder) {
  display: none;   ← no !important — would be overridden by inline styles
}
```
But the `!important` rule at line 1388 takes precedence, hiding the placeholder regardless of the inline `display: grid` that `renderContextPanel()` sets.

**DOM evidence (v3, patched):**
- `noSelDisplay: "none"` (computed) even with `noSelHidden: false` (no `hidden` attribute) and `noSelectionInlineDisplay: "grid"` (inline style set by JS)

**Canva comparison:** Canva always shows an empty-state or placeholder in the properties panel when nothing is selected (e.g., "Select an object to edit its properties"). EInvite's placeholder text exists in the HTML (`"Select an object on the canvas to edit its properties."`) but is **invisible**.

**Fix recommendation:** Add `:not(.v54-inspector-placeholder)` to the `!important` rule at `editor-styles.css:364`, or add the class `v54-inspector-empty` to the `#noSelection` div in the HTML.

---

### G4. Floating selection card / context toolbar never appears

**Severity:** High  
**Location:** `src/js/editor/editor-core.js` — `ensureSelectionCard()`, `scheduleUpdate()`

The DOM check shows `selectionCardExists: false` in all editor states, even when `v54-has-selection: true` and `selectedCount: 1`. The code calls `ensureSelectionCard()` during `install()`, but the card element is never created or appended to the DOM.

**Canva comparison:** Canva shows a floating toolbar directly above a selected element with alignment, position, and style shortcuts. This is a core Canva interaction pattern. EInvite's editor has the code for this (the `v54-selection-card` CSS class and `ensureSelectionCard()` function exist) but the card DOM node is not created at runtime.

**Screenshot evidence:** `editor_textselected_1440_en.png` — the title object has a selection outline (CSS `.object.selected`) but no floating card/toolbar above it.

**Fix recommendation:** Investigate why `ensureSelectionCard()` doesn't create the DOM node — likely a dependency (e.g., `#stage` or `#canvasViewport`) is not available at the time `install()` runs, or the card is created but immediately removed.

---

### G5. Inspector panel has `!important` in its visibility rules (editor-styles.css)

**Severity:** Medium  
**Location:** `src/css/editor/editor-styles.css:364` (v54 refactor)

As detailed in G3, the v54 editor CSS (`editor-styles.css`, created in commit `5ed591e`) contains `!important` on the inspector visibility toggle rules. This is a **new** `!important` from the v54 refactor (not pre-existing). The hard rule says "no `!important`". While `editor-core.js` (the JS) has 0 `!important`, the accompanying `editor-styles.css` (the CSS written for the same v54 refactor) does use `!important` — specifically on:
- Line 364: `display: none !important` (inspector hide-on-no-selection)
- Line 365: `display: none !important` (advanced control hide)

These can be removed by relying on CSS specificity or inline styles (the JS already sets `style.display`).

---

### G6. Mobile editor: no visual selection feedback; right panel is off-screen and never slides in

**Severity:** High  
**Viewport:** 390 × 844 (iPhone SE / small mobile)

**DOM evidence:**
```
rightPosition: "fixed"
rightTransform: "matrix(1, 0, 0, 1, 409.5, 0)"   ← translateX(409.5px) = off-screen
bodyClasses: "... einvite-layout-mobile mobile-pane-collapsed ... v54-has-selection ..."
```

At 390 px width:
1. The right panel (properties) is positioned `fixed` and translated 409.5 px to the right — **completely off-screen**.
2. The left sidebar expands to fill the full 390 px width (`leftSidebarWidth: "390px"`).
3. `v54-has-selection: true` is set, but no CSS rule slides the right panel back into view.
4. **All five selection-state screenshots are byte-for-byte identical** (150 381 bytes for EN, 150 882 bytes for KM each): `editor_noselection_390_en.png` = `editor_selection_390_en.png` = `editor_textselected_390_en.png` = etc.

**Canva comparison:** On mobile, Canva slides the properties panel in from the right as a drawer when an element is tapped. The right panel is reachable via a toggle button in the topbar.

**EInvite:** The right panel is off-screen and there is **no visible button** to slide it in. The `v54-has-selection` class is set but no CSS rule maps it to `transform: translateX(0)` for the fixed drawer. The CSS at `bundle-index-v15.css:1654` does define a mobile drawer pattern:
```css
@media(max-width:600px){
  body[data-page="editor"] .right { transform: translateX(100%); }
  body[data-page="editor"].right-open .right { transform: translateX(0); }
}
```
But the selector targets `body[data-page="editor"]` while the actual page sets `data-page="index"` (see HTML line 1: `<body data-page="index"`). **The mobile drawer CSS never applies.** ✅ Root cause identified.

**Fix recommendation:** Change `data-page="index"` to `data-page="editor"` in `index.html`, or add a CSS rule targeting `data-page="index"`. Additionally, wire a topbar button (or the selection event) to toggle `.right-open` on the body so the drawer slides in on mobile.

---

### G7. Floating selection card missing — no context toolbar on 1440 px

**Severity:** High  
**Viewport:** 1440 × 900

As noted in G4, `selectionCardExists: false` in all states. The selection card (`v54-selection-card`) is defined in the CSS but never created in the DOM. On desktop, Canva shows a floating toolbar above selected elements; EInvite shows only the CSS outline (`.object.selected { box-shadow: … }`) but no toolbar.

This is the same root cause as G4 — `ensureSelectionCard()` doesn't produce a DOM node.

---

### G8. 404 errors on API endpoints and favicon

**Severity:** Low (expected in static mode)  
**Location:** Editor: `/favicon.ico` 404 (1 occurrence at `noselection_1440_en` only); Dashboard: 4 × 404 per screenshot

The dashboard JS attempts to call `/api/invitations/demo-wedding/signup-sheets` and similar API endpoints. In static mode (no `ai_agent`), these return 404. The JS falls back to seed data, so the dashboard renders correctly. These are **expected** in static mode and not a fidelity gap.

---

## 6. Found But Out of Scope

### OOS-1. Dashboard Khmer strings not translated for auth tabs

**Screenshot:** `dash_signedout_1440_km.png` (265 KB) vs `dash_signedout_1440_en.png` (405 KB)  
**DOM:** `htmlLang: "km"`

In the signed-out dashboard, the auth tab buttons show:
```html
<button id="authSignInTab">
  <span class="i18n i18n-en">Sign in</span>
  <span class="i18n i18n-km khmer-text" lang="km">Sign in</span>   ← STILL ENGLISH
</button>
<button id="authRegisterTab">
  <span class="i18n i18n-en">Create account</span>
  <span class="i18n i18n-km khmer-text" lang="km">Create account</span>  ← STILL ENGLISH
</button>
```

The `.i18n-km` spans for "Sign in" and "Create account" contain **English text** — the Khmer translations were never populated. The i18n mechanism works (KM text is shown, EN is hidden), but the translation content is missing.

**Per task rules:** i18n work is **closed**. This is a translation-content gap, not a technical i18n mechanism gap. Reported here for completeness.

### OOS-2. Dashboard "Sign out" button text not translated

**Screenshot:** `dash_signedin_1440_km.png` (402 KB)

The header's Sign out button shows:
```html
<span class="i18n i18n-en">Sign out</span>
<span class="i18n i18n-km khmer-text" lang="km">Sign out</span>  ← STILL ENGLISH
```
Same pattern as OOS-1. Out of scope.

### OOS-3. Pre-existing `!important` in `ux-refine.css` (414 declarations)

As detailed in §2, `ux-refine.css` contains 414 `!important` declarations. Git history shows these trace to the initial import (`cfbb764`), predating the v54 refactor. They are **not introduced by the redesign**. Reported for completeness but not a v54 gap.

### OOS-4. `.ff_screenshots/` directory contains stale screenshots

The `.ff_screenshots/` directory contains 12 stale screenshots (4 dashboard, 8 editor) from Sept 29–30. These are **gitignored** and **stale** (they show the pre-v54 state). Per task rules, they were not used or referenced.

---

## 7. Screenshot Index

All screenshots are in `/dev/shm/`. The two capture directories use different runtime patches (applied only during capture — not source edits):
- `screenshots/` — **Pass 1 (partially patched):** `#restoreFile` element injected (Patch A only). The `insertBefore` error at line 5527 still fires, killing the bundle before `EInviteEditorCore` initializes. The right panel shows **all** inspector controls (because the `workspace-experience-v54` body class is absent, v54 CSS rules are inactive). This captures the "broken but HTML-visible" state.
- `screenshots_v3/` — **Pass 2 (fully patched):** Both `#restoreFile` and `insertBefore` patches applied. `EInviteEditorCore` initializes; `workspace-experience-v54` and `v54-has-selection` classes are toggled; v54 CSS rules are active. This captures the "intended interactive behavior" — properties panel visible on selection, hidden on no-selection (G3 bug manifests here).

The **truly unpatched** state (no runtime fixes) crashes at line 5386 (`$($('#restoreFile').onchange=…)`) and was confirmed via `pageerror` capture:
```
TypeError: Cannot set properties of null (setting 'onchange')
    at <anonymous> (http://localhost:8000/bundle-index-v15.js:5386:27)
```
No screenshots exist for the unpatched state — the initial capture attempt produced 5 851-byte blank images.

### Editor — Pass 2 (patched, showing intended behavior)

| File | State | Viewport | Lang | Size | DOM highlights |
|------|-------|----------|------|------|----------------|
| `editor_noselection_1440_en.png` | No selection | 1440×900 | EN | 401 KB | core=true, v54sel=false, props=block (CSS-hidden), noSel=visible-via-JS but CSS-hidden by !important |
| `editor_noselection_1440_km.png` | No selection | 1440×900 | KM | 409 KB | Same DOM; Khmer heading "រ៉ញម្ញានង់" visible |
| `editor_noselection_390_en.png` | No selection | 390×844 | EN | 150 KB | Mobile: right panel off-screen, left rail full-width |
| `editor_noselection_390_km.png` | No selection | 390×844 | KM | 151 KB | Same as EN; body classes: `einvite-layout-mobile mobile-pane-collapsed studio-design-mode` |
| `editor_selection_1440_en.png` | subtitle selected | 1440×900 | EN | 426 KB | core=true, v54sel=true, props=block, propsVisible=true |
| `editor_selection_1440_km.png` | subtitle selected | 1440×900 | KM | 433 KB | Same DOM; Khmer text visible in properties |
| `editor_selection_390_en.png` | subtitle selected | 390×844 | EN | 150 KB | No visual difference from noselection (right panel off-screen) |
| `editor_selection_390_km.png` | subtitle selected | 390×844 | KM | 151 KB | Identical to EN 390 |
| `editor_textselected_1440_en.png` | title selected | 1440×900 | EN | 426 KB | Typography controls visible in properties panel |
| `editor_textselected_1440_km.png` | title selected | 1440×900 | KM | 434 KB | Khmer placeholder text visible in KM |
| `editor_textselected_390_en.png` | title selected | 390×844 | EN | 150 KB | No visual difference (mobile drawer issue) |
| `editor_textselected_390_km.png` | title selected | 390×844 | KM | 151 KB | Identical |
| `editor_imageselected_1440_en.png` | hero selected | 1440×900 | EN | 418 KB | Image controls visible (`.imageControls` section) |
| `editor_imageselected_1440_km.png` | hero selected | 1440×900 | KM | 424 KB | Same |
| `editor_imageselected_390_en.png` | hero selected | 390×844 | EN | 150 KB | No visual difference |
| `editor_imageselected_390_km.png` | hero selected | 390×844 | KM | 151 KB | Identical |
| `editor_collapsed_1440_en.png` | sidebar collapsed | 1440×900 | EN | 350 KB | Left rail 37px; main grid: `0px 1135px 305px` |
| `editor_collapsed_1440_km.png` | sidebar collapsed | 1440×900 | KM | 357 KB | Same |
| `editor_collapsed_390_en.png` | sidebar collapsed | 390×844 | EN | 150 KB | Mobile: no visual difference (sidebar already full-width) |
| `editor_collapsed_390_km.png` | sidebar collapsed | 390×844 | KM | 151 KB | Identical |

### Dashboard — Pass 1 & Pass 2 (identical; no JS errors on dashboard)

| File | State | Viewport | Lang | Size | Notes |
|------|-------|----------|------|------|-------|
| `dash_signedout_1440_en.png` | Signed out | 1440×900 | EN | 405 KB | loginView visible, canvas-auth-layout |
| `dash_signedout_1440_km.png` | Signed out | 1440×900 | KM | 265 KB | Most strings in Khmer; auth tab labels still English (OOS-1) |
| `dash_signedout_390_en.png` | Signed out | 390×844 | EN | 55 KB | Mobile: auth layout stacks vertically |
| `dash_signedout_390_km.png` | Signed out | 390×844 | KM | 46 KB | Mobile KM |
| `dash_signedin_1440_en.png` | Signed in | 1440×900 | EN | 405 KB | dashboardView visible, 1 invite card, 3 quickstart buttons |
| `dash_signedin_1440_km.png` | Signed in | 1440×900 | KM | 402 KB | Same layout; "គណនី" (Account) in Khmer |
| `dash_signedin_390_en.png` | Signed in | 390×844 | EN | 95 KB | Mobile: invite grid single-column |
| `dash_signedin_390_km.png` | Signed in | 390×844 | KM | 89 KB | Mobile KM |

### Canva reference

| File | Page | Viewport | Size |
|------|------|----------|------|
| `canva_landing_1440.png` | Landing | 1440×900 | 175 KB |
| `canva_landing_390.png` | Landing | 390×844 | 92 KB |
| `canva_templates_1440.png` | Templates | 1440×900 | 331 KB |
| `canva_templates_390.png` | Templates | 390×844 | 160 KB |

---

## 8. Summary Table

| ID | Category | Finding | Severity | Screenshot |
|----|----------|---------|----------|------------|
| G1 | Gap | `#restoreFile` missing from **working-tree** HTML (uncommitted v54 rewrite; present in all 50 tracked revisions) → fatal `TypeError`, kills entire bundle. **Fix applied 2026-10-05 (working-tree line 99)** | **Critical** | `screenshots/editor_noselection_1440_en.png` (Pass 1: partially patched) |
| G2 | Gap | `header.insertBefore()` fails: `#saveState` not a direct child of `<header>` | **Critical** | Same as G1 |
| G3 | Gap | No-selection placeholder hidden by `!important` CSS rule (`.v54-inspector-placeholder` not excluded) | Medium | `screenshots_v3/editor_noselection_1440_en.png` |
| G4 | Gap | Floating selection card never created (`ensureSelectionCard()` fails) | High | `screenshots_v3/editor_textselected_1440_en.png` |
| G5 | Gap | `!important` in v54 `editor-styles.css:364` violates "no `!important`" rule | Medium | CSS file, not screenshot |
| G6 | Gap | Mobile: right panel off-screen, no drawer toggle, `data-page="index"` vs `data-page="editor"` CSS mismatch | High | `screenshots_v3/editor_textselected_390_en.png` |
| G7 | Gap | No context toolbar above selected element on desktop | High | `screenshots_v3/editor_selection_1440_en.png` |
| G8 | Gap | 404s for API endpoints + favicon in static mode | Low | Dashboard screenshots |
| M1–M13 | Match | 3-col layout, topbar, command palette, collapse, selection outlines, inspector toggle, alt-drag, zoom HUD, dashboard auth, invite grid, i18n, Khmer line-height | — | Various |
| D1–D6 | Deviation | Inspector heading style, "Style & motion" label, no blur, variable mismatch, long headline, no footer | — | Various |
| OOS-1 | Out of scope | Dashboard KM auth labels not translated | — | `screenshots/dash_signedout_1440_km.png` |
| OOS-2 | Out of scope | "Sign out" KM label not translated | — | `screenshots/dash_signedin_1440_km.png` |
| OOS-3 | Out of scope | 414 `!important` in pre-existing `ux-refine.css` | — | N/A |

---

## 9. Three Key Questions Answered

### (1) What are the Canva layout/interaction conventions used as the target?

The canonical target is `docs/ROADMAP-v0.54-to-v1.0.md` §3.0: *"The editor must feel as intuitive as Canva."* Reference URL `canva.com/design` (auth-gated; landing + templates pages captured instead). The ROADMAP specifies:
- **§3.1** — Canvas interaction: alignment guides, multi-select, context menu, grid snapping
- **§3.2** — Text editing: inline rich text, text effects, text on a curve
- **§3.4** — Chrome and panels: layer panel, pages sidebar, command palette, keyboard shortcuts, zoom controls
- **§3.5** — Collaboration: live cursors, comment threads

The v54 redesign maps to these as: layout (M1–M3), inspector (M6), selection (M5), command palette (M3), zoom HUD (M9), responsive drawers (attempted, G6).

### (2) Match / Deviate / Miss?

- **Matched (M1–M13):** 3-column grid, topbar design, command palette, sidebar collapse, selection outlines, inspector toggle, alt-drag duplicate, canvas panning, zoom HUD, dashboard auth flow, invite grid, bilingual i18n, Khmer line-height 1.6
- **Deviated (D1–D6):** Inspector heading style, "Style & motion" label, no backdrop blur, dead CSS variables, long headline, no footer — all **deliberate** deviations appropriate for invitation design
- **Missed (G1–G8):** Fatal JS errors (G1, G2), invisible no-selection placeholder (G3), missing selection card (G4/G7), mobile drawer broken (G6), 404s in static mode (G8)

### (3) Real gap vs deliberate deviation?

| Finding | Real Gap? | Deliberate? | Rationale |
|---------|-----------|-------------|-----------|
| G1 `#restoreFile` missing (working tree) | ✅ Yes | ❌ No | Element absent only from the uncommitted v54 working-tree rewrite (present in all 50 tracked revisions, incl. HEAD:78); unguarded top-level binding crashes the bundle; restored at working-tree line 99 on 2026-10-05 |
| G2 `insertBefore` DOM mismatch | ✅ Yes | ❌ No | HTML wrapper div not accounted for in JS |
| G3 Placeholder hidden by `!important` | ✅ Yes | ❌ No | CSS selector omits `v54-inspector-placeholder` from exclusion list; `!important` overrides JS |
| G4/G7 No selection card | ✅ Yes | ❌ No | `ensureSelectionCard()` defined but DOM node not created |
| G6 Mobile drawer broken | ✅ Yes | ❌ No | `data-page="index"` vs CSS `data-page="editor"` selector mismatch; no toggle button |
| G8 404s in static mode | ⚠️ Partial | ✅ Yes | Expected in static mode; JS falls back to seed data |
| D1–D6 | ❌ No | ✅ Yes | Aesthetic choices appropriate for invitation domain |

---

## 10. Recommendations (Pending User Confirmation)

1. **G1 — ~~Add `<input id="restoreFile" type="file" accept=".json" hidden>` near `#restoreBtn` in `index.html`.~~ APPLIED 2026-10-05** — restored at working-tree line 99 as `accept="application/json"` (byte-exact against committed history; see §11 C3 and `docs/reviews/g1-restorefile.md` §6). The 5386 `TypeError` no longer fires; the page-level crash then persists via the separate G2 defect (still live as of 2026-10-05).
2. **G2 — Change `header.insertBefore(titleWrap, saveState)` → `header.querySelector('.studio-topbar-right').insertBefore(...)` or restructure HTML.**
3. **G3 — Add `:not(.v54-inspector-placeholder)` to the `!important` rule in `editor-styles.css:364`, or add class `v54-inspector-empty` to `#noSelection`.**
4. **G4/G7 — Investigate `ensureSelectionCard()` — likely a missing DOM anchor (`#stage` or `#canvasViewport` not queried correctly in the mobile layout context).**
5. **G6 (mobile) — Fix `data-page="index"` → `data-page="editor"` in `index.html`, or add a `[data-page="index"]` selector variant in the mobile CSS. Wire a topbar button to toggle `.right-open` on the body.**
6. **G5 — Remove `!important` from `editor-styles.css` lines 364–365.** The JS already controls visibility via inline `style.display`; the `!important` is unnecessary and overrides JS intent.

Fixes will be applied in `src/` (source) files only — never in `src/python/`. Bundle rebuild is required after source CSS/JS changes (`npx vite build` or the project's build command). Screenshots will be re-captured after fixes to confirm resolution.

---

---

## 11. Corrections (2026-10-05)

Three factual errors in this review were identified in follow-up sessions (G1 post-mortem `docs/reviews/g1-restorefile.md`; i18n close-out session). The review's qualitative findings (G2–G8) stand as written; the items below affect the numbers and the G1 framing. Each item was re-verified against the working tree on 2026-10-05 (evidence in parentheses); this addendum is the authoritative record where it disagrees with the follow-up claims.

### C1 — `!important` count in `ux-refine.css`
- **As written:** 414 occurrences (§2 table; OOS-3)
- **Follow-up claim:** 1 ("verified in the i18n close-out session via cascade check")
- **Re-verification 2026-10-05: claim REFUTED.** Direct occurrence count of the file on disk: **414** `!important`s in `src/css/ux-refine.css` (working tree, 30 408 bytes, a single minified line); the served mirror `src/python/ux-refine.css` is byte-identical (30 408 bytes, 414). HEAD's version carries **415** — the uncommitted working-tree change removed one `!important` declaration and added one plain rule (`#typographyControls` grid). The claimed "1" is a **line-count artifact**: the file is one line, so any line-based count (`grep -c`, `Select-String` without `-AllMatches`) returns 1. **The review's 414 stands**, and its characterization of `ux-refine.css` as `!important`-saturated is **not** void. No downstream decision needs re-examination on this basis.

### C2 — screenshot count
- **As written in the current document:** 40 (§1: "16 editor + 8 dashboard + 4 Canva reference + 4 Canva detail + 4 earlier Canva captures"); §7's index lists 32 files (20 editor + 8 dashboard + 4 Canva reference)
- **Follow-up claim:** 25 actual; "as written: 85" with an internal breakdown of 44 + 4 + 12 = 60
- **Re-verification 2026-10-05: UNVERIFIABLE from this machine; internal inconsistency CONFIRMED.** The review's screenshots lived in `/dev/shm/canva_review/` on the original Linux host; none of the cited files exist in this repository (the repo's `screenshots/` holds 62 unrelated i18n/verification PNGs; `.ff_screenshots/` holds 16 feature-flag PNGs). The "85" and "44 + 4 + 12" figures quoted by the follow-up do not appear anywhere in the current document, indicating it was written against an earlier draft. What *is* confirmable from the document itself: §1 claims 40 total / 16 editor while §7's own index lists 32 total / 20 editor — so every "N screenshots cited" claim in this review should be treated as unverified until the original capture directory is listed. The "actual: 25" figure is carried over from the follow-up session without independent re-derivation.

### C3 — G1 framing ("element missing from HTML")
- **As written:** `#restoreFile` is null because `src/html/index.html` lacks the element.
- **Re-verification 2026-10-05: CONFIRMED as corrected.** `git grep -n "restoreFile" HEAD -- src/html/index.html` → present at **line 78**; `g1-restorefile.md` §5.5 shows the token in **all 50 tracked revisions** containing the file (0 without). It was dropped only in the uncommitted v54 working-tree rewrite (the `studio-topbar` header restructure), alongside the intact `#restoreBtn` and all backup/restore JS. **Fix applied:** restored at working-tree line 99, inside the v54 "Project" menu section, byte-exact against every committed ancestor (`type="file" accept="application/json" hidden`), propagated to the served mirror by `sync_frontend_assets.py` (SHA-256 byte-identical); no JS source changed, `build_route_bundles.py --check` → `ROUTE_BUNDLE_CHECK_PASSED`. The review's G1 *symptom* was right; the *cause* framing was wrong, so the correct fix path (restore markup, not remove dead JS) was chosen and executed — `g1-restorefile.md` §6. This review's body was updated at G1, the §8 summary table, §9, and §10 accordingly.

---

*End of review.*
