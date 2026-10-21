# UI Visual Audit & Design-Fix Task

**Companion to `CANVAS-MOTION-FIX-TASK.md` — both files go to the fixing agent together.**
Audit date: 2026-10-18. Basis: real-render capture sweep (16 pages × auth states × viewports × themes × languages, 150 screenshots + in-page layout heuristics + Lighthouse).
**Scope at authoring time: findings and work order only — no fixes had been applied.** The fixes have since landed; see the status line below, and treat §2–§3 as the historical pre-fix analysis.

**Status (2026-10-20): CLOSED.** Pass 1 (P0/P2/P3 fixes) and pass 2 (U1 design page, U2 app pages) are implemented and verified; evidence is in `artifacts/ui-audit/fixes/RESULTS.md`. The nine Definition-of-done boxes in §4 are closed with pointers to that evidence.

---

## 0. Severity legend and the short list

| Sev | Meaning |
|---|---|
| **P0** | Breaks the page or blocks a gate: blank/broken page, unreachable control, `make perf` cannot complete, console error on every load. |
| **P1** | Clearly wrong to a human eye: overlapping panels, clipped toolbar buttons, invisible text, content under a fixed bar, horizontal page scroll on mobile. |
| **P2** | Polish/consistency: tiny text, duplicated controls, dev-note copy, unstyled controls in dark theme. |
| **P3** | Nice-to-have / robustness; owner decision needed. |

Short list (details below):

- **P0-1** `lhci collect` aborts on `dashboard.html` (NO_FCP) → `make perf` / `make reproduce` cannot complete until dashboard paints something or is excluded.
- **P0-2** `gpu-loader.js` requests `*-v22.js` files that do not exist → 404 + MIME refusal on **every** editor load; **all four GPU scripts never load** (the loader chain rejects on the first 404). Lighthouse `errors-in-console` fails on index.html.
- **P0-3** `dashboard.html` pageerror `Cannot set properties of null (setting 'onclick')` — `dashboard.js:101` assigns to `#authSignInTab` etc. that no longer exist (page intentionally emptied 2026-10-16; see §H).
- **P1-1** Design page (`index.html`) tablet mode (768/1024): the mobile editor pane host opens as a **big empty white panel over the canvas**; selection toolbar sits mid-canvas on top of it; context toolbar (`Assets/Text/Shape/Quick`) is clipped; top toolbar shows ghost/overlapping pills and a black rectangle (768).
- **P1-2** Design page desktop 1440: the right inspector extends ~75 px past the viewport (last tab cut); the canvas toolbar runs under it ("Position" clipped); **two zoom readouts** on one screen; device segmented control labels collide (`MobileTabletDesktop`).
- **P1-3** Systemic at ≤375 px: the header language switch is overlapped by page content on every app page (occlusion rows: `button#lang-en / #lang-km` covered by `main#main …`, 13 pages; on `admin.html` it is fully invisible).
- **P1-4** Horizontal page scroll (WCAG 1.4.10): `analytics.html` 375/320 (scrollW 395), `admin.html` 320 (371), `privacy.html` 320 (364), `templates.html` 320 (345).
- **P1-5** Dark-theme invisible text: `templates.html` "Built-in" tags (contrast **1.03:1**, 40 hits); `public.html` venue/strong (1.27), muted paragraphs (~3.0), journey buttons (1.37); `checkin.html` breadcrumb + labels (3.2); `privacy.html` language pill (2.8); `index.html` studio status texts (1.99–2.31).
- **P1-6** Design page mobile 375/320: language card overlaps the "Hide controls" chip row; two **empty white chips**; "Class…" chip clipped; the desktop-recommended banner's text is covered by the bottom bar; canvas page initially off-screen right (pairs with canvas task 3).
- **P2-1** Duplicated status text: `index.html:97` `#saveState` renders "Saved locallySaved locally" (the `i18n-km` span contains the **English** string and is not hidden in EN mode).
- **P2-2** Tiny text: studio UI labels at **8–9 px** (`studio-nav-label` 9px, `DESIGN STUDIO` 9px, `CURRENT INVITATION` 8px, `Main hero canvas`/`Nothing selected` 8px, `×` 10px), `WORKSPACE` rail labels 11px on every app page, admin `<th>` 11px.
- **P2-3** Unstyled default controls in dark theme (gray checkbox squares on `templates.html` "Favorites only", `guests.html` select-all).
- **P2-4** User-facing dev note on `billing.html`: "Card checkout is designed and ready, but it stays disabled until the owner adds production gateway credentials and a webhook secret."
- **P3-1** `public-page.js:82` date rendering has no `isNaN` guard (lines 40/54 do); a non-ISO `fields.date` renders "Invalid Date" to guests.
- **P3-2** Owner decisions: rebuild vs exclude the emptied dashboard; converge the layered `!important` patch CSS (editor-suite 660, canvas-plus 542, modern-ui 296, stabilized 220, final-polish 217, ux-refine 209 occurrences) onto `tokens.css`.

---

## 1. How this audit ran (and how to re-run it)

Everything is reproducible; the instruments are committed under `tools/`:

```
# 1) capture sweep: 16 pages × states × viewports × themes × langs
#    (screenshots + layout heuristics JSONL). Needs the app server.
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/ui-audit-capture.py --out artifacts/ui-audit/capture
#    narrowed runs, e.g. one page / one combo:
python3 ... tools/ui-audit-capture.py --out artifacts/ui-audit/capture --only index.html --states user --themes dark --langs en --viewports 1440x900,375x667

# 2) read the results
python3 tools/ui-audit-summary.py --section hscroll|overflow|contrast|occlusion|tiny|errors
python3 tools/ui-audit-digest.py --dir artifacts/ui-audit/capture --out artifacts/ui-audit/digest.txt

# 3) Lighthouse a11y/perf (needs tools/serve-gzip.py on 8124 + CHROME_PATH)
$env:CHROME_PATH = "$env:LOCALAPPDATA\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
python3 tools/serve-gzip.py --port 8124     # in one terminal
npx lhci collect --config=tools/lighthouserc.js
```

- Raw evidence: `artifacts/ui-audit/capture/` (shots + `heuristics.jsonl` + `console.jsonl` + `summary.txt`), digest at `artifacts/ui-audit/digest.txt`.
- Capture profiles: `user` = seeded account + published invitation (slug auto-seeded), `guest` = logged out. Themes `light|dark`, langs `en|km`, reduced-motion on. The capture tool also seeds 4 guests + 1 RSVP.
- Known heuristic caveats (do not mis-file these as bugs):
  - **`.sr-only` labels behind inputs are not occlusion bugs** (clipped 1×1 parents). `ui-audit-summary.py` already filters them.
  - Occlusion rescans run mid-page/at bottom too, so a sticky header over scrolled text is **not** automatically a bug; verify with a scroll-0 capture.
  - The contrast heuristic reads `background-color` only (gradients/disabled states misread). `billing.html` "Pay securely by card" white-on-white rows are a **disabled-state gradient** — not a bug.
  - Canvas-world elements at low zoom legitimately produce tiny-text/overflow rows; interpret with page context.
- Fixed during this audit: `tools/ui-audit-capture.py` used to resolve the public slug *before* seeding, so the first combo of any run captured `/i/no-invite`. Fixed; the corrected combo was merged back (see `artifacts/ui-audit/probes/merge-publicfix.py`, `artifacts/ui-audit/capture-publicfix/`). `DOCUMENT.date` is now ISO (`2026-12-12`) so captures stop showing "Invalid Date".

---

## 2. Findings detail

### A. Design page (`index.html`) — desktop 1440 (user / light)

Evidence: `artifacts/ui-audit/capture/shots/user/index.html/en-light-1440x900.png`; digest rows for `index.html user en/light 1440`.

1. **Right inspector wider than its column.** `#mobileQuickInspector` and its `nav.studio-inspector-tabs > button` extend to `right=1515` at 1440 (75 px past the viewport; `right=1298` at 1024). The last tab ("↗ Share") is cut off by the right edge. The **canvas toolbar runs underneath the panel** — visible as the clipped "Position" button in the screenshot; occlusion rows at 1440: `#v23ContextToolbar` "Text"/"Shape"/"Review"/"Assets" buttons covered by `#mobileQuickInspector`.
   - Fix direction: make the inspector column a proper grid/flex track (`width: min(360px, 100%)`, `min-width: 0`, `box-sizing` audit), so the toolbar and the panel share the layout instead of overlapping; verify no element has `right > innerWidth` at 1440/1024.
2. **Two zoom controls on one screen.** Top toolbar shows `38%` + slider; bottom-right cluster shows `− 38% + | Fit | Selection | Focus`. Decide on one primary zoom surface (recommend: keep the bottom cluster, make the top read-out display-only or remove it).
3. **Device segmented control text collision.** Labels render jammed ("MobileTabletDesktop") with the selection knob overlaying text at 1440; at 1024 the control shows **ghost overlapping pill outlines** plus truncation.
   - Fix direction: flex with `gap`, `white-space: nowrap`, explicit per-option padding; re-check at 1024/768 where the control wraps.
4. **Statusbar duplication (P2-1).** `src/html/index.html:97`:
   `<span id="saveState"><span class="i18n i18n-en">Saved locally</span><span class="i18n i18n-km khmer-text" lang="km">Saved locally</span></span>`
   The KM span holds the **English** string and both render ("Saved locallySaved locally  Server connected") in EN captures at 1440/768/375/320.
   - Fix: put the Khmer translation in the KM span and ensure the inactive-language span is actually hidden for `#saveState` (check the rule that hides `.i18n-km`; this node has an extra `khmer-text` class).
5. **Tiny studio text (P2-2).** Cluster list in §0; sources are studio labels (`studio-nav-label` 9px, `#flowProjectMeta` 9px, `.flow-section small` 10px, `#workflowV5Status` 8px, page/selection pills 8px, `Ctrl K` 11px kbd). Raise the studio floor (11px meta / 12px labels is a safe minimum consistent with `tokens.css`).
6. **First-run tour dialog** (`dialog.final-tour`, from `final-experience.js`) auto-opens on first guest visit and covers the topbar (`#undoBtn`, `#publishBtn`, language switch…). Verify its anchoring/close affordance; the capture can dismiss it via storage if you add a "seen" flag — recommended so future captures show the editor itself.
7. **"Timeline" pill** floats over the canvas bottom edge overlapping the zoom bar at some widths (visible at 1440 and 375) — re-anchor it to the statusbar track.

### B. Design page — tablet 768 / 1024 (the worst states)

Evidence: `.../shots/user/index.html/en-light-1024x768.png`, `.../en-light-768x1024.png` + digest rows for 1024/768.

1. **Big empty white panel over the canvas (P1-1).** At both widths the canvas is covered by a large blank white rounded panel; the stage content *exists in the DOM* (digest shows `#stageTransform :: ✦ Sokha & Dara …` at 768) — so this is an open pane, not a render failure. Occlusion rows name it: `…covered by aside#mobileCreationPanel>div.studio-pane-host>section.studio-pane.flow-design-pane` and `…by main#main>aside#mobileQuickInspector` at 768/1024. Body class is `studio-experience mobile-editor-v14` — the **mobile editor mode is active at 768/1024** and opens the creation pane as an empty sheet.
   - Fix direction: define the responsive contract for 721–1024 (tablet): either stay in desktop editor (single row: rail + creation pane + canvas + inspector) or open mobile mode with the pane **closed by default** (drawer, not covering sheet). The white sheet must never be empty — if it opens, it must contain the flow/design panes.
2. **Selection toolbar mid-canvas.** `div.studio-selection-toolbar` ("Duplicate | Copy style | Paste style | Forward | Lock | Group | Tidy | Delete") renders as a floating bar across the middle of the white sheet (1024) — it must dock to a tracked edge (top of canvas or above selection), not float center-canvas.
3. **Toolbar-on-toolbar collisions.** Occlusion rows at 1024/768: `div.studio-selection-toolbar` covering `#canvasZoomReadout (32%)`, `#workflowV5Focus`, `#workflowV6FlowBtn`, `#workflowV6PositionBtn`, `span.ei-context-name`, `v54-device-button` ("Tablet"), and `#v20TypographyToolbar` buttons (`B`, `I`, `Style`, `Hide controls ▴`) covered by it/`studio-selection-toolbar`. One toolbar surface per breakpoint, stacked with spacing, z-index documented.
4. **Topbar collision at 768:** `span#documentTitle` ("Sokha & Dara") covered by `button#undoBtn`; `•••` (`canvas-header-more-trigger`) under `#undoBtn`. Fix the topbar to a grid (brand | title | actions) with `min-width: 0` + `text-overflow: ellipsis` on the title.
5. **Broken toolbar render at 768 (screenshot):** a solid black rectangle inside the toolbar row, ghost pill outlines, and overlapping text near "Search tools and settings…"; `#v23ContextToolbar` clipped at `right=1106` ("Quick Actions" cut) — inspect `.v20-context-toolbar` (`overflow-x:auto` is fine, but siblings must not overlap) and the toolbar's internal stacking (`z-index:24`).
6. **Statusbar again**: "Saved locallySaved / Server … / trl K" — the statusbar clips its own items at 768.

### C. Design page — mobile 375 / 320

Evidence: `.../shots/user/index.html/en-light-375x667.png`, `.../en-light-320x568--full.png` + digest rows.

1. **Language card overlaps the chip row (P1-6).** The `.language-switch` (English pill card) floats over `#v20TypographyToolbar`'s chips ("Hide controls ▾"), which are cut off at the right edge ("Class…") and include **two empty white chips** (buttons with no content).
2. **Desktop-recommended banner text covered.** Occlusion + screenshot: `aside.mobile-desktop-hint` text covered by `nav#mobileEditorV14Bar > button#mobilePreviewV14` / `#mobileQuickMode` — the hint is bottom-anchored under the fixed bottom bar. Reserve its space (padding-bottom on the hint container = bar height) and let it wrap to 3+ lines unharmed.
3. **Canvas page off-screen right** — pairs with `CANVAS-MOTION-FIX-TASK.md` task 3 (initial framing/`fit()` per viewport). Verify after that fix that the page is visible at 375/320 with controls not overlapping it.
4. **Zoom pill / "Timeline" / toolbar floats** overlap canvas content at 375; consolidate mobile floating controls into the top/bottom bars (one row each).
5. **Top-left logo clipped** at the viewport top edge in the mobile topbar (375) — give the mobile topbar a min-height that fits the 44px logo tile.

### D. Systemic: header language switch overlapped at ≤375 (P1-3)

Occlusion rows on **13 pages**: admin, verify, reset, privacy, guests, responses, materials, checkin, public, account, billing, analytics, templates, designer — `header > div.language-switch > button#lang-en | #lang-km` covered by `main#main` / the page `h1` span. On `admin.html` the switch is invisible at 375 (screenshot). Root cause shape: the header does not reserve height for the language-switch block at narrow widths, so `main` (or its heading) slides over it.
- Fix direction: one shared rule for the app header — flex-wrap with `row-gap`, language switch as its own row at ≤375 (or shrink to two icon buttons); verify each page at 320/375 that the switch is visible, clickable (elementFromPoint = the button), and not covering the H1.
- Note: several pages additionally pin content **under the topbar** at 1440 (`billing.html`: intro paragraph covered by `header>div.app-topbar-left`; `account.html` dark "DATA EXPORT" covered by `nav.app-crumbs`), i.e. missing `scroll-margin`/top offsets or negative margins — verify with a scroll-0 capture.

### E. Horizontal page scroll at 320/375 (P1-4)

| Page | Viewport | scrollW | Offending elements (digest) |
|---|---|---|---|
| `analytics.html` | 375 + 320 | 395 | `div.analytics-grid > section.chart-card` / `aside.summary-card` (right=395) |
| `admin.html` | 320 | 371 | `main#main > h1 > span.i18n` ("Administration", right=371) |
| `privacy.html` | 320 | 364 | `div.i18n > p > code` long token `EINVITE_ANALYTICS_RETENTION_DAYS` (right=364; not internally scrollable) |
| `templates.html` | 320 | 345 | `label.toggle-row` ("Favorites only", right=345) |

Fix directions: grid children `min-width:0` + `overflow-wrap:anywhere` on `code`/URLs; `clamp()`/`text-wrap: balance` for the giant H1s; wrap the toggle row. Verify `document.scrollWidth <= innerWidth` at 320/375.

### F. Dark-theme contrast (P1-5, P2)

Numbers are fg/bg/ratio from real computed styles (evidence: `ui-audit-summary.py --section contrast`):

- **`templates.html` — "Built-in" chips: 1.03:1 (n=40).** Light theme chips are correct (dark text on light chip); in dark theme the chip keeps its light background while the text flips to `#f2f3f7` → invisible. Fix `.tags > span` / `.version-badge` to theme-aware colors (or `color-scheme`-aware tokens). Verify 1440+375 dark.
- **`public.html` — venue card / muted / journey:** `div.venue-card.primary-venue > strong` 1.27:1; `section.guest-feature… > p.muted` 3.02; `form#rsvp > label > span` 2.97; `nav.guest-journey > button > span` ("‹") 1.37; `button.guest-journey-current > small` ("1 / 4", 10px) 3.04; `.language-switch > button` (km glyph on light pill) 1.12. These are genuinely unreadable in dark mode.
- **`checkin.html`:** breadcrumb "Event Check-in" 3.2:1; `label.checkin-search > span` "Find guest" 3.2:1.
- **`privacy.html`:** language-switch active pill 2.8:1 (white on `#d5829c`).
- **`index.html` (studio):** `#workflowV6Flow header small` "PUBLISHED INVITATION" 2.31 (8 px); `#workflowV5Status b` 1.99 (8 px); `aside#workflowV6Flow header strong` "Invitation flow" 1.11 (**recheck while the panel is open** — it was sampled off-canvas); `.v20-fit-pill` "Auto-fit —" 1.05 at 375 (recheck in the open toolbar).
- Not a bug (do not "fix"): `billing.html` checkout buttons (disabled state + gradient bg) — heuristic artifact, confirmed by screenshot.
- Also check: editor canvas `span.rt-run` text 2.16 in dark — likely template-controlled colors; only change if it's theme CSS, not the document.

### G. Tiny text (P2-2)

Cluster summary (full list: `ui-audit-summary.py --section tiny`): studio 8–11px labels; `WORKSPACE` rail label 11px on every app page; admin table `<th>` 11px; `Built-in` tags 11px; account "Signed in as" 11.67px; checkin "Online"/"DOOR TEAM" 11px. The design system already has a 9-step type scale in `tokens.css` — these hard-coded values bypass it. Set a floor (11px meta / 12px labels / 16px Khmer body, per `docs/i18n/KHMER-TYPOGRAPHY.md` §4) and move the offenders onto tokens. Khmer must never inherit Latin line-height (`:lang(km){line-height:1.6}` is documented but **not yet shipped**).

### H. Broken assets, console noise, gates (P0)

1. **`gpu-loader.js` requests versioned filenames that no longer exist.**
   `src/js/gpu-loader.js:1` loads `gpu-texture-cache-v22.js`, `webgl-scene-backend-v22.js`, `gpu-projection-v22.js`, `adaptive-gpu-quality-v22.js`. All four exist **version-free** in `src/js` and `src/python` (the versioned names 404; served as JSON error page → "Refused to execute script … MIME type ('application/json')"). Because the loader chains with `s.onerror=j`, **the first 404 rejects the chain and none of the four scripts load**. Reproduce: `ui-audit-summary.py --section errors` shows the 404 + MIME console pair on every index capture (4 errors); Lighthouse `errors-in-console` FAIL.
   - Fix: drop `-v22` (match the version-free migration), keep a friendly `onerror` that logs once, and re-check `gpu-*.js` load in DevTools.
2. **`dashboard.html` is an intentional WIP stub** (HTML comment "DASHBOARD PAGE EMPTIED 2026-10-16 … rebuilt from scratch"; backup at `artifacts/dashboard-page-wip/dashboard.html.orig`, inventory at `docs/reviews/dashboard-feature-inventory-2026-10-16.md`). Two live consequences:
   - `pageerror: Cannot set properties of null (setting 'onclick')` — `src/js/dashboard.js:101-119` assigns `$('#authSignInTab').onclick`, `#loginBtn`, `#newBtn`, `#passkeyLoginBtn`… which no longer exist. Not a visual bug per se, but it aborts dashboard.js before anything renders.
   - **`lhci collect` aborts here** (`NO_FCP: The page did not paint any content`) — so `make perf` / `make reproduce` **cannot run at all** right now. Owner decision required (§J): either exclude `dashboard.html` from `tools/lighthouserc.js` URLs + `docs/perf/lighthouse-budgets.json` behind a WIP marker, or paint a minimal shell (brand + "rebuilding" notice) and neutralize the dead JS.
3. **Admin 403s** (`/api/admin/*` with a non-admin account) are expected; verify the admin page's *error state* renders as a designed empty state, and re-capture with a real admin account before judging admin visuals.
4. **Unlabeled inputs** (heuristic counts): `account.html` 16, `admin.html` 9, `public.html` 4. Identify each (`label[for]` / `aria-label` missing) and fix; the tool only counts them.

### I. Public guest page (`public.html`) — mostly good

The cover state at 375 and 1440 is clean and well-composed (`capture-publicfix/shots/.../en-light-375x667.png`), and the published page renders correctly with the fixed ISO date. Remaining: dark-mode contrast (§F), the `320` overflow pair (inspect with `--section overflow --page public`), and **P3-1**: `src/js/public-page.js:82` (also `bundle-public.js` twin) builds the date with `new Date(f.date+'T00:00:00').toLocaleDateString(...)` **without** the `isNaN` guard that lines 40/54 have — any non-ISO `fields.date` shows "Invalid Date" to guests. Add the same fallback.

Note: `button#openCover` covering the topbar/journey is the intended cover gate — not an occlusion bug.

### J. Design-system convergence (the design plan)

The site has a token system (`src/css/tokens.css`: space scale 4→96, 9-step type scale, motion 150/200/250ms, `--ease-out`, shadow roles) plus `typography-system.css` / `typography-fonts.css` / `docs/i18n/KHMER-TYPOGRAPHY.md`. The defects above are largely places where pages **bypass** it with layered patch files (`editor-suite.css` 660 `!important`, `canvas-plus.css` 542, `modern-ui.css` 296, `stabilized.css` 220, `final-polish.css` 217, `ux-refine.css` 209). Converge rather than patch again:

1. One source of truth per concern: spacing/size/lead → tokens; component chrome (buttons, chips, toolbars, statusbar) → component CSS that reads tokens; page-specific overrides → only where layout differs.
2. Kill the duplication at the component level: two zoom surfaces → one; `v20`/`v23` context toolbars → one responsive surface; `.studio-selection-toolbar` vs `.v20-context-toolbar` vs `#v23ContextToolbar` → one docked bar with documented z-index layers.
3. Themed primitives: `input[type=checkbox]`/radio/switch need dark-theme styling (currently raw gray squares on `templates.html`, `guests.html`).
4. Touch/click targets: keep ≥24 px visual / ≥44 px hit area on mobile (icon buttons in the studio rail are 22 px per prior audit; re-verify after the studio restructure).
5. Copy: owner-facing dev notes (billing checkout banner) must not render in the user UI.
6. Focus visibility: `outline:none` appears in `app-shell.css` (3×) — pair every removal with `:focus-visible` styling (prior audit item §5 in `docs/a11y/WCAG-2.2-AA-AUDIT.md`).

---

## 3. Screenshot-driven hunting protocol (do this before, during, and after fixes)

Goal: catch *everything a human eye would call off*, on **every page**, not just the design page.

1. **Baseline first.** Run the full sweep (command in §1) on the unfixed tree; keep it. All "after" claims must name the matching before/after files.
2. **Cover the matrix per page.** 16 pages × {user, guest} × {light, dark} × {en, km} × {1440, 1024, 768, 375, 320} — the default tool profiles do this; use `--only` for iterations.
3. **Also capture interactive states** (a scripted pass or manual Playwright):
   - `index.html`: object selected (toolbar + inspector populated), workflow "Flow" panel open, "Position" popover open, mobile "Hide controls" collapsed/expanded, quick-inspector open at 768/1024, first-run tour dismissed.
   - The emptied dashboard: skip until rebuilt (or capture once to document the WIP state).
   - `public.html`: cover open → hero → schedule → RSVP form (with focus) → footer; dark + km.
   - Forms: focus rings, validation error states, empty states (`guests.html` with 0 guests, `templates.html` favorites-only with none).
4. **For every screenshot, run the three checks by eye:** (a) anything overlapping/clipped/cut at an edge; (b) anything that should align but does not (grid axis, baselines, card paddings); (c) anything illegible (contrast < 4.5:1, < 12px text, invisible controls).
5. **Every finding needs:** page, state, viewport, screenshot path, the DOM selector, the computed cause (which CSS rule wins), and the proposed fix. Use `ui-audit-digest.py`/`--section` summaries to name offenders instead of guessing.
6. **Regression guard:** after a fix, re-run the same capture and diff the affected shots (keep both files). Ensure `document.scrollWidth <= innerWidth` at 320/375, no `elementFromPoint` covering interactive controls at scroll 0, and no new console errors.
7. **Do not weaken gates**: `make check`, `make test`, `make smoke` stay green; budgets/thresholds/baselines unchanged (`CANVAS-MOTION-FIX-TASK.md` carries the canvas gates that are currently red — they must go green, not be relaxed).

---

## 4. Definition of done

- [x] All P0 items resolved; `lhci collect` completes for the shipped page set (dashboard decision documented). — evidence: fixes/RESULTS.md §Pass 1
- [x] No console errors on the 16 pages in user/guest states (editor GPU loader fixed). — evidence: fixes/RESULTS.md §Pass 1
- [x] No horizontal document scroll at 320/375 on any page. — evidence: fixes/RESULTS.md §Pass 1
- [x] The design page renders and is usable at 1440/1024/768/375/320: no overlap between rail/creation pane/canvas/inspector/toolbars; one zoom surface; no clipped controls; the canvas page visible on first paint at every width; mobile hint text fully readable. — evidence: fixes/RESULTS.md §Pass 2 — U1
- [x] The ≤375 header language-switch overlap is gone on all 13 pages (switch visible + clickable). — evidence: fixes/RESULTS.md §Pass 2 — U1/U2
- [x] Dark mode: no text below 3:1 (target 4.5:1 for body); templates tags, public venue/muted, checkin, privacy, studio status texts fixed. — evidence: fixes/RESULTS.md §Pass 2 — U1/U2
- [x] Type floor applied (≥11px meta, ≥12px labels; Khmer per the typography doc) across the studio and app pages. — evidence: fixes/RESULTS.md §Pass 2 — U1/U2
- [x] Before/after screenshots for every fixed item under `artifacts/ui-audit/fixes/<issue-id>/` and a short `RESULTS.md` mapping issue ID → files touched → verification command. — evidence: fixes/RESULTS.md §Pass 1
- [x] Canvas tasks 1–5 from `CANVAS-MOTION-FIX-TASK.md` verified by its own gates (see that file; do not edit its thresholds). — evidence: artifacts/canvas-motion/verify/acceptance-*

## 5. Out of scope / owner decisions

- Rebuilding `dashboard.html` (out of scope here; only the LHCI/abort consequence is in scope).
- The `!important` mass-removal refactor beyond what the listed fixes need (track as cleanup once the fixes land).
- Khmer translations themselves (`docs/i18n/*` has the gap reports); only the visual consequences are in scope.
- No changes to `docs/a11y/*` audit conclusions; this file adds the real-render layer those audits explicitly lacked.
