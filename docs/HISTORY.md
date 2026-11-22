# eInvite — Project History (consolidated)

> Generated during clean-up on 2026-11-01. Source files were removed; recover them from the git ref
> `backup/pre-cleanup` (commit `a125343`, the `chore/cleanup` base). The work order asked for a tag
> `pre-cleanup`; the project's own rule OD-3 forbids tags, so the identical snapshot is a branch.
> Untracked files that had no git copy were archived before deletion (see §6).

## 1. Summary

- **What it is.** eInvite (brand: OKID) is a self-hosted, bilingual (English + Khmer) invitation design
  and event-management platform: 16 routes, a canvas editor with a governed AI agent (80 typed tools),
  guest pages with RSVP, an admin console, and a Python/SQLite backend.
- **Current state.** Version **0.70.13** on a single local branch (`fix/2026-10-22-open-issues`, now
  `chore/cleanup` for this pass). Work is local-only by owner decision **OD-3**: no push, tag, PR or merge.
- **Gate of record.** `GATES_PASSED` at `4880fcb` (Stage E, 2026-10-29), all ten phases exit 0:
  build, bundles, smoke 16/0/0, layout, pytest **223 passed**, budgets 6/6, LHCI 16/16 `minA11y 1.00`,
  CSP 0 violations, canvas 22/0/2, `!important` 3791 ≤ 3791.
- **After that matrix.** UI commits followed (mobile topbar, header at ≤400 px, route-weight diet,
  390 editor targets, dashboard type scale). Each carried build/bundles/layout/smoke checks, not a fresh
  ten-phase matrix. Treat the Stage E matrix as the last full one.
- **What this file is.** The single written record of bugs, decisions, tests and lessons. It replaces
  178 superseded work orders, version reports, review passes and plans; their paths and sizes are in
  `docs/CLEANUP_MANIFEST.md`.
- **Not recorded here.** Product behaviour is documented in `README.md`, `docs/ARCHITECTURE.md`,
  `docs/design/DESIGN.md`, `docs/SECURITY.md` and the per-domain docs under `docs/`. The authoritative version
  timeline stays in `VERSION_HISTORY.md` (pre-0.52 detail in `docs/LEGACY-VERSION-HISTORY.md`).

## 2. Bugs and fixes

> **Still open?** Everything that is not fixed below — plus the unfinished work-order phases, the
> owner-held decisions and the verification debt — is queued in `docs/NEXT-WORK.md`. This section
> records what happened; that file records what remains.

### Fixed

Grouped by area. IDs are the historical ones (audit letters, `FB-nn` items, `PW-n` items) so an old
report can still be matched; dates are the fix date, `[unknown]` where the record did not carry one.

| ID | Area | Problem | Root cause | Fix | Source file(s) | Date |
|---|---|---|---|---|---|---|
| J2 | Editor | Every tool-rail click threw `root.querySelectorAll is not a function` | `requestAnimationFrame(keepActiveToolVisible)` passed the frame timestamp into the `root` parameter | Callback wrapped; TypeError gone for all seven rail buttons | `src/js/editor-*` | 2026-10-13 |
| D1 | Editor | `•••` overflow menu painted permanently over the workspace (286 × 505 px at `z-index:12000`) | Menu was a sibling of `.canvas-header-more`, shipped un-hidden, so `organizeHeader()` bailed before hiding it | Menu nested + `hidden`, real trigger wired once, popup joined the Escape ladder. 95 checks × 5 widths, 0 failures | `src/css/canvas-plus.css`, `src/js/*` | 2026-10-13 |
| E4 | Editor | Mobile pane handle painted 34 × 42 px over the stage and opened one-way | Handle was owned by a derived state it could not set; all seven `.fp-mobile-pane-close` were `display:none` at every width | Handle moved into the rail column, delegated to the owner, hidden < 821 px, close button shown ≤ 1180 | `src/js/editor-responsive-contract*` | 2026-10-13 |
| J1 | Guests | Export CSV threw instead of downloading | `URL.createObjectURL(a.href)` — a string passed where a Blob belongs | Blob created, anchor clicked, URL revoked | `src/js/guests*` | 2026-10-13 |
| A1 | Shell | 37 failed requests + a console error on every signed-out load | The shell sent session-only `/api` requests without a session | Session contract in `backend-mode`: refuses to send while signed out, answers the same 401 JSON | `src/js/backend-mode*` | 2026-10-13 |
| A3 | Guest page | Literal `__INVITATION_SLUG__` fetched → 404 | Page served without slug substitution | Bootstrap refuses an unsubstituted slug; language falls back to `einvite-lang` | `src/js/public*` | 2026-10-13 |
| C1/C2/D2/D3 | CSP | Inline `<script>` blocks and inline handlers refused on 16 routes | Blocks shipped inline in the pages | Moved into `core/theme.js` / the modules they drove; `inlineScripts=0` on all pages | `src/html/*`, `src/js/core/theme.js` | 2026-10-13 |
| M2 | Materials / Responses | Filter options read every label twice (`All typesAll types`) | Parser drops `<span>` children inside `<option>` | Plain-text option labels | `src/html/materials.html`, `responses.html` | 2026-10-13 |
| E1 | Editor | Page-dock chips collided and escaped their grid | Chip footprint frozen at 112–118 px against a 147 px grid | Footprint tokenised; 0 collisions 900→1920 | `src/css/*` | 2026-10-13 |
| E3 | Editor | Floating tool rail covered 46 px of the canvas at 1200 px | A layered `position:absolute` fix could not beat unlayered `position:sticky` | Fixed in the file that wins the cascade; 12 px gap at every width ≥ 1181 | `src/css/organized/styles.css` | 2026-10-13 |
| S1–S4 | Shell | Below 1025 px: `main` starved to 150 px, 64 px drawer, wrong drawer control, clipped labels | Duplicate high-specificity sticky rule + persisted `rail-collapsed` | Four fixes; 40-row sweep passes | `src/css/app-shell.css` | 2026-10-13 |
| E5 | Editor | App-level Escape handlers swallowed Escape from every other owner | Ladder always consumed the key | `consumeOnlyWhenHandled`; inspector + mobile drawer joined the ladder | `src/js/editor-command-system*` | 2026-10-15 |
| A4 | Account | Signed-out load replaced `<main>` | `renderSignedOut()` replaced the element | Keeps the frame, hides session-only cards, writes notices into `noticeHost()` | `src/js/account.js` | 2026-10-15 |
| D1b | Editor | `•••` popover never flipped upward | `position:absolute` → containing block was the 42 px trigger wrapper, so the `position-try` option could never fit | `.canvas-header-more-menu` is `position:fixed`; measured `bottom = anchor(top) - space-1` | `src/css/canvas-plus.css`, `editor-suite.css` | 2026-10-15 |
| A2 | Admin | `-v2` admin panels rendered empty | Endpoints never existed; a strict xfail named the gap | Implemented server-side (`users-v2`, `metrics-v2`, `system-status`, `invitations-v2`, `audit-events`, `health-detail`); xfail removed | `src/python/server.py` | 2026-10-15 |
| FB-19 | CSS | 4,033 `!important` occurrences, no ratchet | Accumulated overrides | Dead-rule cleanup (214 tokens), 5 proven-superseded tokens, then a pinned ratchet started at 3,823 | `src/css/**` | 2026-10-22 |
| FB-24 | CSP | Inline handlers still refused | Markup handlers | Removed; CSP gate now a runner phase | `src/html/*` | 2026-10-22 |
| FB-28 | Auth card | Inputs < 16 px, an empty icon button, header > 96 px, breadcrumb overflow | Sizing rules | All three fixed (VB-01…VB-03) | `src/css/*` | 2026-10-22 |
| FB-29 | Editor | Canvas-share and auto-fit races on resize | Responsive contract gaps | Contract closes both (VB-04…VB-06) | `src/css/editor-responsive-contract.css` | 2026-10-22 |
| FB-30 | Khmer | Headings used the wrong face under `:lang(km)`; language pill state unclear | Font stack + state class | `var(--font-khmer)` for headings; one justified `!important`; pill state verified (VB-07/VB-08) | `src/css/typography-*` | 2026-10-23 |
| FB-36 | Editor @375 | Header 489 px wide on a 375 px viewport; artboard unusable | Chrome did not reflow | Title/« one-line ellipsis, `.stage-wrap` scoped ≥ 701, `fitView()` centred with tween-aware settle, palette docked left | `src/css/editor-*`, `src/js/editor-suite.js` | 2026-10-23 |
| FB-37 | Public header | Two language controls; impostor `InterPlayText` face | Duplicate markup; unregistered family | One control (persists), bundle Inter registered for `--font-latin`, header fits 375 | `src/html/public.html`, `src/css/*` | 2026-10-23 |
| FB-38 | Layout guard | Guard could not see empty controls, clipped fields or editor artboard size | Missing checks | Four checks + a deliberately broken fixture; caught blank Khmer link labels and the demo badge | `tools/ui-layout-guard.py` | 2026-10-23 |
| FB-39 | Admin | Non-admin fired three doomed requests and a mock-403 console row | Role probe ran after the requests | Probe first; "Administrator access required" + dashboard link | `src/js/pages/admin*` | 2026-10-23 |
| FB-41 | Canvas | `pan-middle-drag` and `reduced-motion-no-tween` regressed | Fit settle loop re-centred after user input | Settle cancelled on any non-`fit` view change; fit floor 0.35 → 0.25 for 320 px | `src/js/editor-suite.js` | 2026-10-23 |
| FB-42 | SEO | 15 of 16 routes shipped no `<meta name="description">`; SEO 89–91 | Missing tags | One describing sentence per route; LHCI SEO **91 → 100** (public stays 91 — substituted per invitation) | `src/html/*` | 2026-10-23 |
| FB-43 | Editor | First-paint CLS 0.334 | Two defaults disagreed: the pane host opened on **Event** at y=126, `workflow-refine` switched to **Design** 1.3 s later and `main` dropped to y=56 | Section drives content mode only once the workflow owns it; session-accurate start tab; geometry class moved into static `<body>` | `src/js/editor-layout-stability.js`, `workflow-continuity.js` | 2026-10-23 |
| FB-44 | Materials | CLS 0.162, library stack jumped 347 px | Upload box shipped open, collapsed behind a toggle by JS | `hidden` attribute in markup; **CLS 0.162 → 0.005**, perf 0.93 → 1.00 | `src/html/materials.html` | 2026-10-23 |
| FB-45 | Layout guard | No tripwire for one long main-thread task | Missing check | Fails on any single task > 600 ms (ceiling set from measured 137–498 ms); 925 → 1,345 checks | `tools/ui-layout-guard.py` | 2026-10-23 |
| FB-46…FB-57 | UI | Round-4 refinement: Khmer map, brand OKID, 375 editor/dashboard, public date/CTA, RSVP jump, dashboard width | Assorted | Ten commits; see `VERSION_HISTORY.md` and the manifest's source rows | `src/**` | 2026-10-24 |
| FB-54 | i18n | 23 Khmer map rows unapplied | Translation map not wired | Map applied; three checker rules with negative controls; `VERIFIED 88/88` | `docs/i18n/KHMER-TRANSLATION-MAP-*`, `tools/i18n-apply-khmer-map.py` | 2026-10-24 |
| FB-55 | Brand | Three name spellings; credit in the header | Legacy naming | OKID lockup, editor mark `E`→`O`, credit moved to a footer line | `src/html/*`, `src/css/*` | 2026-10-24 |
| FB-57 | Dashboard | 1200 px → content-width repaint | Width known only after first paint | `main` capped from the first byte | `src/css/app-shell.css` | 2026-10-24 |
| FB-49 | Guest page | Date rendered "2026 M12 12"; blank band; CTA pills collided | Wrong `Intl` usage; layout | `Intl` in the viewer's locale, re-rendered on language switch; band removed; pills separated | `src/js/public*.js` | 2026-10-24 |
| FB-61 | i18n | 72 English occurrences / 42 unique strings inside `<span class="i18n-km">` | Shared header rebuilt faster than the map | Inventory committed; needs owner-supplied Khmer rows (never written by an agent) | `docs/i18n/KHMER-GAP-SHARED-HEADER-2026-10-24.md` | 2026-10-24 |
| FB-62/65 | Canvas check | `ctrl-wheel-no-page-scroll` failed 4/5 runs | The check asserted an **inner** scroll box whose range collapses with zoom; the page never scrolled | Assert `window.scrollY` + `document.scrollingElement.scrollTop`; 15/15 P5 runs, phase 22/0/2 | `tests/canvas_motion_playwright.py` (frozen; owner-approved amendment) | 2026-10-24 |
| FB-64/65/66 | Build | `index.html` max long task 741 ms — all of it V8 compile of a 1.07 MB startup bundle | One parser-blocking bundle | Split at an IIFE boundary into 535 KB + 537 KB with `backend-mode` folded in; max task 741 → **418 ms**, layout gate 11 red rows → 0, probe max 710 → 549 ms | `build_route_bundles.py`, `docs/route-bundle-sources.json` | 2026-10-24 |
| FB-66 | Build | `index.html` loaded two stylesheets while the budget says one | Stale mirror hid the extra sheet | `design-fix.css` folded into the route bundle (before the responsive contract, so v22's ordering assertion holds) | `build_route_bundles.py` | 2026-10-24 |
| FB-67 | Editor | CLS 0.625 | Inspector shell and footer Tools trigger injected ~1.8 s and ~1 s after paint | Shell, tab row and panes shipped in markup; `buildInspector()` fills them. CLS 0.625 → **0.199** median (LHCI mobile 0.129) | `src/html/index.html`, `src/js/editor-core.js` | 2026-10-24 |
| FB-68/71/78 | Khmer | Maps unapplied; 13 route sources missing the font sheet; no Khmer numerals | Assorted | `VERIFIED 88/88`; `var(--font-khmer)` on guest KM, editor input, 8 rail labels × 4 routes; `core/khmer-format.js` (digits + dates, default off) | `src/css/typography-fonts.css`, `src/js/core/khmer-format.js` | 2026-10-24/25 |
| FB-69 | Public | Date ignored the guest's chosen language | Node rendered once | Hero node re-renders on switch; CTA cells size to labels above 520 px | `src/js/public*.js` | 2026-10-25 |
| FB-70 | Dashboard | Cover pill over cards, chip overflow, rail height | Layout | Pill removed, chip 65×31.6 with no overflow, rail 844/900; guard gained `empty-pill` + two negative controls | `src/css/canva-ui.css` | 2026-10-25 |
| FB-72 | Editor @375 | Orphan `::before` slash; picker and HUD off-screen | Absolute positioning | Title one line (97×19.5), chip 116 px, picker inside 375, HUD 201 px right-aligned; rail/HUD intersection 0 | `src/css/editor-*` | 2026-10-25 |
| FB-73 | Editor @1440 | Two panel searches, repeated `Inspector` eyebrow, brand misaligned, Studio Ops over the inspector | Duplication | One search, one eyebrow, brand on one flex line, 4,752 px² overlap → 0 | `src/js/*`, `src/css/*` | 2026-10-25 |
| FB-74 | Admin | Non-admin got a bare 403 page | No empty/error state | Shared `.admin-access-state` card (icon, bilingual title, one sentence, two actions), light/dark, 320–1440 | `src/html/admin.html`, `src/css/*` | 2026-10-25 |
| FB-75 | Editor | CLS 0.5526 | Content mode decided after first paint | `studio-design-mode` + `data-studio-section` on `<body>`; probe **0.5526 → 0.1438**, LHCI median 0.1415 (target 0.1 not met) | `src/html/index.html`, `src/js/*` | 2026-10-25 |
| FB-76 | CSP | `designer.html` outside the CSP gate; `unsafe-eval` suspected | Gate coverage | Page added to `csp-violation-check.py` signed in and out; 13/13 checks, 0 violations; `unsafe-eval` did not reproduce | `tools/csp-violation-check.py` | 2026-10-25 |
| D-5 | Print/PDF | `lt_2_6` PDF metric sat on its 4.5 tolerance | Two product defects: the app's muted-paragraph rule repainted printed text, and the print page replayed the 900 ms `fadeUp` | `body.print-doc` + animations frozen; MAE byte-identical **3.5922** over 30 runs incl. 4-way CPU load | `src/css/print*`, `src/js/*print*` | 2026-10-29 |
| D-6 | Print | No bleed/crop marks | Print CSS | Marks added | `src/css/print*` | 2026-10-29 |
| D-7 | Data | Version snapshots existed but were never taken | Module unused | Wired into draft save (hash change **and** ≥ 5 min, keep 50) | `src/js/*` | 2026-10-29 |
| D-8 | Templates | Template copy overflowed its boxes | Copy longer than the drawn box | Shortened copy + geometry; `wd-royal-maroon-gold` hand-edited (generator fonts absent) | `template-pack/templates/*.json` | 2026-10-29 |
| E-2/E-3/E-4 | Security | API keys were route-scoped only; webhooks not durable; field encryption absent | Design gaps | Scoped keys + per-key 429; durable signed webhooks under the SSRF guard; 6 encrypted columns with dual-read, `--rollback`/`--reencrypt`, 1,000-row proof | `src/python/*`, `platform_v32/*` | 2026-10-29 |
| PW-1 | Editor | Presence pill covered the inspector's **Essentials** button (right computed 18 px, not 348) | The intended rule lost the cascade | Winning declaration removed (no `!important`); pill docks right of the 330 px inspector | `src/css/studio-experience.css` | 2026-10-30 |
| PW-2 | Editor | Transform group looked disabled while an object was selected | `is-disabled` set from a stale selection signal | Driven from the same selection state as the inspector tabs; hint only when nothing is selected | `src/js/*inspector*` | 2026-10-30 |
| PW-3 | Editor | Typography bar clipped its own values (1,073 px content in 660 px) | 32 px right padding reserved for an arrow that is never drawn (`appearance:none`, no background image) | Bar removed; every control already exists in the inspector / selection toolbar; `Responsive preview` kept | `src/html/index.html`, `src/css/*` | 2026-10-30 |
| PW-4 | Editor | Unanchored 7-row menu opened over the artwork on every click | Floating menu duplicated the selection toolbar | Menu removed; all seven actions reachable in the inspector / toolbar | `src/js/*` | 2026-10-30 |
| PW-5 | Editor | Status strip clipped Templates / Quality / Team at 1440 | 18 duplicate launchers in a 30 px bar | Bar keeps save state, readout, approval, shortcuts and **Tools**; duplicates removed; still 30 px | `src/js/editor-core.js`, `src/css/*` | 2026-10-30 |
| BUG-R4-1 | Editor (mobile) | Every tap at ≤820 px was classified as an inspector-tab click, so the new bottom bar's Tools tap opened the wrong drawer | `<body>` carried `data-inspector-tab` as state — the same attribute delegated handlers use as a contract | Body state renamed `data-active-inspector`; v14 asserts only `.studio-inspector-tab` carries the attribute and that Tools/Quick yield `creation`/`inspector` | `src/js/studio-experience.js`, `src/css/editor-inspector.css` | 2026-11-02 |
| BUG-R4-2 | Editor (601–820) | Creation bar `display:none` at 768; rail off-canvas at `x=-351` and inert, so Pages/Elements/Text were unreachable | `mobile-editor.js` used `max-width:600px` while the drawer contract switches at 820; bar rules existed only ≤600 | Both breakpoints use `EInviteResponsiveLayout.MOBILE_MAX`; bar rules extended to 601–820 with the six-column grid (six columns, not five); 768 px gate | `src/js/mobile-editor.js`, `src/css/editor/editor-styles.css` | 2026-11-02 |
| BUG-R4-3 | Editor (mobile) | Tools closed ~20 ms after the tap while boot finished; a programmatic `openCreation()` was reverted the same way | `syncInspectorDrawer(false)` called `closeInspector()`, which means "drawer → canvas" regardless of which drawer was open | On mobile, close the inspector only when it is the open drawer; v14 clears the selection while Tools is open and requires `creation` | `src/js/editor/editor-core.js` | 2026-11-02 |
| PW-6 | Account | Dark and Light toasts stacked and contradicted each other | One timer per toast, no dedupe key | New theme toast replaces the previous one; one toast naming the current theme | `src/js/modern-ui.js` | 2026-10-30 |
| PW-7 | Templates | Two search fields and three filter rows on `/templates` | Duplicated pack + studio controls | One search that filters both lists, one filter row, ellipsis on overflow | `src/js/template-pack-gallery.js`, `src/html/templates.html` | 2026-10-30 |
| PW-8 | Editor | "Current invitation" thumbnail was a purple gradient on a rose design | Placeholder card | Card removed (duplicated the topbar title) | `src/html/index.html` | 2026-10-30 |
| PW-9 | Editor | Artboard started at 64 % (250×540) inside 660 px | 340 px of chrome above the canvas | Tip card, duplicate heading, start grid, readout, zoom HUD (desktop), Timeline/Studio Ops pills removed; HUD kept ≤ 768 px | `src/html/index.html`, `src/js/*` | 2026-10-30 |
| PW-10 | Admin | Two endpoints polled every 30 s through 429 (~110 failed requests in 28 min, one tab) | Poller ignored visibility and status | Visibility-gated, backoff honouring `Retry-After`, stops after N failures with a paused state | `src/js/pages/admin*` | 2026-10-30 |
| PW-11 | Auth | `Password field is not contained in a form` DOM warning on `/` and `/dashboard` | Markup | Real `<form>` with `autocomplete` values; Enter submits; hidden username field on the password-change form | `src/html/*` | 2026-10-30 |
| PW-12 | Mobile | Three 328 × 32 buttons in the create dialog at 390 px | No coarse-pointer rule | `min-height: 44px` under `(pointer: coarse)` and ≤ 640 px | `src/css/*` | 2026-10-30 |
| 2026-10-30 sweep | Hosting | Editor status bar overflow; 36 template-pack assets 404 on the host; Khmer gallery header painted as the app topbar | A 30 px bar held 18 launchers; bundle omitted `/assets/template-pack/`; undefined colour tokens | Launchers removed, assets bundled, header tokens fixed | `tools/build-sites-bundle.py`, `deploy/sites/worker.js` | 2026-10-30 |
| 2026-10-30 hosting | Hosting | Dynamic routes dead on a static-only host; UI stuck in "Static preview mode" | Sites serves Workers + assets only; the health probe was skipped without a marker | Worker reverse-proxies `/api`, `/uploads/`, `/i/`, `/invitations/`, `/_marketplace/` to the PC backend through a Cloudflare Quick Tunnel; live origin kept in D1 (`backend_config`) and re-registered on tunnel start; build injects `<meta name="einvite-backend" content="full">` | `deploy/sites/worker.js`, `deploy/local/*`, `tools/build-sites-bundle.py` | 2026-10-30 |
| 2026-10-31 header | Shell | 56 layout `header-height` reds at 320/375 on non-editor pages | Topbar could not fit one row | `--shell-topbar-pad`/`--shell-topbar-gap` at ≤ 400 (two rows, no pad/gap), brand capped at 44 px < 360, empty page cluster out of flow; guard **1693 checks / 0 failed** | `src/js/app-shell.js`, `src/css/organized/styles.css` | 2026-10-31 |
| 2026-10-31 budgets | Build | Five pre-existing route-weight reds | Shipped bytes | Whole-line comment stripping (line-preserving), CSS punctuation tightening, privacy no longer ships `modern-ui.css`, 17 unreferenced utility rules dropped; `v55` green at 6 pages, ceilings unchanged | `build_route_bundles.py`, `src/css/*` | 2026-10-31 |
| FB-150 | Editor a11y | 13 controls under 44 px at 390; outline jumped `h1 → h3` | Sizing + heading structure | 44 px targets (drawer toggles, toolbar, Flow/Position, zoom HUD; 30 px status bar untouched); hidden page `h1`, `h2 Pages`, `h3 Recent tools` | `src/css/*`, `src/html/index.html` | 2026-10-31 |
| FB-151 | Dashboard | 10 px meta text; card menu targets < 44 px on touch | Type scale | 10 → 11 px; 44 px targets on coarse pointers; 0/155 controls under 44 px at 390 | `src/css/canva-ui.css` | 2026-10-31 |

| UX-9b | Guest page | Three "HTTP 401" blocks rendered on every published invitation | Guest modules fetched host routes with no session | A 401 removes the feature section instead of writing the error | `src/js/{signup-sheets,polls,album}.js` | 2026-11-01 |
| UX-8b | Guests | Edit / Link / QR / Check-in / Remove buttons did nothing | `[data-edit]` delegation dropped in `92806ad`; container re-rendered on every filter | Delegated click handler on the stable list container | `src/js/guests.js` | 2026-11-01 |

### Still open

| ID | Area | Problem | Severity | Notes | Source file(s) |
|---|---|---|---|---|---|
| OD-23 | Editor | First-paint CLS re-measured at **0.5003** at 1440 px | P1 | Late `.ei-section-order-builder` mount shifts the page grid 184 px; `page-experience.js` rebuilds the Pages host with `innerHTML` after the builder is inserted. Needs a boot-order fix; nine CSS reservations were measured and refuted | `src/js/page-experience.js` |
| — | Guest page | Three `HTTP 401` blocks on every public invitation (`signup-sheets`, `polls`, `album` fetch host routes anonymously) | P1 | Needs public read routes with the access checks of `/api/public/`, or hiding the blocks when unauthenticated — a product decision | `src/js/signup-sheets.js`, `polls.js`, `album.js` |
| — | Guests | Row actions Edit / Link / QR / Check-in / Remove do nothing | P1 | The functions and API routes exist; the `[data-edit]` delegation was removed in `92806ad`. Needs restoration + one browser test per action | `src/js/pages/guests*` |
| — | Editor | Artboard default fit ≈ 251–275 px at 1440 (target ≥ 300) | P2 | Blocked: fit is height-bound; needs +53 px viewport height or a change to `updateCanvasView`, which the work orders forbid | `src/js/editor-suite.js` |
| — | Build | Editor route still 1.52 MB before images | P2 | Diet arithmetic: 600 ms compile needs ~217 KB removed; deferred candidates sum to ~148 KB, so the split (already shipped) is the working fix | `docs/route-bundle-sources.json` |
| PW-14.4 | Editor | Design check has no Publish menu to join | P3 | `#publishBtn` publishes directly and the check is a standalone topbar button; owner decision recorded, default kept | `src/js/app.js` |
| PW-14 | Editor | Tier-2 merges 2, 3, 5, 6 (inspector header, invitation styles, recipes, duplicate links) | P3 | Items 1/2/5/6 were not reproduced or already satisfied when measured 2026-10-31; item 3 not found | — |
| UX-1 | Shell | Topbar still needs a swipe at 320/375 | P2 | One-row scroll contract measured: budget 487 px at 320 with the account chip already hidden; two rows exceed the 96 px guard limit. Documented as partial | `src/css/organized/styles.css` |
| D-1 | Templates | `templates.html` CLS 0.604 | P2 | Never executed | `src/html/templates.html` |
| D-2 | Guest page | Guest LCP above the 4G target | P2 | Never executed | `src/html/public.html` |
| D-3 | Editor | Two tabs on one invitation never signal ready | P2 | Second tab renders four objects and never sets `editorReady`; likely the draft lock | `src/js/editor-*` |
| UX-4 / D-4 | Assets | No icon sprite; 12 display fonts substituted | P3 | Documented as absent in `docs/ARCHITECTURE.md` §7.1 and `docs/FONT_LICENSES_AND_REGISTRY.md`; both owner-held | `src/css/*` |
| LT-7.2 | API | Per-key 1000/h limit wired but not flood-tested; API-key scope is route-level, not per invitation | P3 | Proving the limit means 1,000 real requests | `src/python/*` |
| LT-7.2 | Ops | A malformed `EINVITE_FIELD_ENCRYPTION_KEY` is a soft failure (logs `source=env-invalid`, falls back) | P3 | A typo silently encrypts under a different key than intended | `src/python/core/crypto*` |
| LT-7.2 | Admin | Users tab does not show suspension | P3 | Reads `/api/admin/users`, which does not select `suspended_at`; `users-v2` does | `src/js/pages/admin*` |
| A-4 | Hosting | No phone-reachable host for the device checklist | P2 | Lifted 2026-10-30: static front end + API are public via Sites + PC tunnel; the real-phone checklist still has not run | `docs/qa/DEVICE-CHECKLIST.md` |
| LT-8.3 | Release | Load test, DR drill and penetration test not run or commissioned | P1 (for 1.0.0) | Templates exist; `docs/certification/CERTIFICATION.md` §1–§5 stays `pending` | `docs/certification/*` |
| — | Release | Canvas **visual** gate not run; real-device checklist not run | — | The frozen baseline lives on the owner's Windows box; the motion gate (22/0/2) is behavioural, not pixel | `artifacts/canvas-motion/**` |

### Won't fix / duplicate / not reproducible

| ID | Reason |
|---|---|
| E2, M1, M2-spacing | Reported as clipping/overlap; measured correct at every width. No change applied |
| D4 (112 "dead controls") | Detector artifacts: fingerprint could not see state, navigation or hit-testing. After the fix 13 candidates remained and each was triaged as wired, hidden or false positive |
| Billing gradient contrast rows | Documented heuristic false positive — the gradient is read as a flat colour |
| Admin mock-403 console rows | Historical mock responses in the admin page, replaced by a real role probe (FB-39) |
| Sticky-header occlusion rows | Produced by re-scanning while scrolled; not a layout defect |
| Icon-only buttons as "tiny text" | Heuristic false positive — measured by text size, not hit area |
| `color(srgb…)` / `color-mix` low contrast | Translucent values read without compositing |
| `h1 → h3` skip on the editor | Axe best-practice (not a WCAG failure); score already 1.00. Fixed as FB-150 anyway |
| 89 `:focus{outline:none}` rules | Every one pairs with a visible paint change; live focus audit found 0 silent focusables of 186 |
| `transition: all` | Count 0 |
| `lt_2_6` PDF metric as a flake | Not a flake: two product defects (D-5), fixed without touching the tolerance |

## 3. Issues and decisions

| Date | Decision | Reason | Source |
|---|---|---|---|
| 2026-10-22 | **OD-1** approved: staged `!important` cleanup | 4,033 occurrences had no ratchet | FB-19 |
| 2026-10-22 | **OD-2** approved subset (dead CSS removal) | Measured, cascade-safe only | FB-20 |
| 2026-10-22 | **OD-3**: local-only release — no push, PR, merge or tag | Owner decision; the repo is public | all passes |
| 2026-10-22 | **OD-4/OD-5** confirmed: resize-handle exception, Khmer option labels | Product calls | — |
| 2026-10-22 | **OD-7** Option A: normalise line endings before hashing the README pin | The pin split Windows CRLF from Linux LF without weakening content addressing | `tests/v27_3_5_release_evidence_test.py` |
| 2026-10-22 | **OD-8** deferred: 11 translation strings need owner-supplied Khmer | Agents never write Khmer | `docs/i18n/*` |
| 2026-10-22 | **OD-6**: the 600 ms long-task ceiling is frozen | Thresholds are not edited to go green | `tools/ui-layout-guard.py` |
| 2026-10-23 | Image budgets and Lighthouse config are read-only | Same reason | `tools/lighthouserc.js` |
| 2026-10-24 | **OD-22**: amend the frozen canvas check, not the product | The check asserted the wrong scroll box; owner-approved change | FB-62/65 |
| 2026-10-24 | **OD-23**: ship the inspector shell in markup | Measured; nine CSS reservations refuted | FB-67 |
| 2026-10-24 | Split the startup bundle instead of editing the script budget | Same bytes as two scripts cut max task 633 → 418 ms; `backend-mode.js` folded in to stay at 3 scripts | FB-65/66 |
| 2026-10-25 | **OD-30** condition not met: no Khmer zero-width-space helper | 67/67 breaks landed on word boundaries, 0 inside a grapheme cluster | LT-2.1 |
| 2026-10-28 | Version history is pasted by the agent from now on (D-12 supersedes the owner-held rule) | Kept the timeline current without a release tag | `VERSION_HISTORY.md` |
| 2026-10-29 | 1.0.0 stays uncertified | Load test, DR drill and pen test are templates only | `RELEASE-CANDIDATE.md` (now §6 here) |
| 2026-10-30 | Host the front end on Freebuff Sites, the backend on this PC + Quick Tunnel | Sites is Workers + static assets only | `deploy/local/README.md` |
| 2026-10-30 | `EINVITE_FIELD_ENCRYPTION` defaults **on** | A new install must not write plaintext by accident; dual-read keeps old rows working (documented deviation from the item text) | `docs/ops/FIELD-ENCRYPTION-RUNBOOK.md` |
| 2026-10-31 | Retire the left Design pane; Pages is the default rail item (owner Tier-3 yes) | One entry point; the inspector's Page & palette group stays reachable | `src/js/*`, tests |
| 2026-10-31 | Keep the standalone Design check | There is no Publish menu to move it into | `OWNER-QUEUE` row (now §2) |
| 2026-11-01 | Keep `tests/` during clean-up | The suite **is** the project's verification contract (`make test`, ten gate phases, four tests read build/doc inputs); deleting it would break every acceptance check in the clean-up order itself | this pass |

## 4. Test history

### 2026-11-01 baseline attempt

`tools/run-gates.py --phase all` at `1bd1717` stopped at layout: three long-task rows (index.html at
375 light 622 ms, 375 dark 613 ms, 1440 light 606 ms) against the frozen 600 ms ceiling, then
`UI_LAYOUT_GUARD_PASSED` on a quiet rerun with long-task 0 failed (173 s). Build, bundles and smoke
passed (16 pages, 0 console errors, 0 non-2xx). The pytest phase, run separately, gave
**5 failed / 218 passed in 901.65 s**: `ai_resource_scopes_test::test_ai_resource_scopes`,
`lt_2_2_khmer_format_test::test_public_rendering_and_editor_round_trip`,
`lt_4_3_color_picker_test::test_colour_picker_extras`,
`lt_4_4_run_typography_test::test_run_typography_from_inspector` and
`template_pack_gallery_test::test_pack_gallery_lists_filters_and_opens_a_design`. All five are
untriaged and recorded in `docs/NEXT-WORK.md` §1. The gate of record (223 passed at `4880fcb`) no
longer describes HEAD.

### 2026-11-02 round-4 suite

`pytest -q tests` after the three round-4 drawer fixes: **231 passed, 1 warning in 1055.53 s
(exit 0)** — the same count as the pre-round gate, so no test regressed. Focused checks:
`tests/v14_live_layout_test.py` passed at 1440/768/390 (bar, drawer, stray-attribute and
selection-refresh guards); `bugs/round-4/flow_sweep.py` **61 checks, 0 failed, 0 console
errors**; `bugs/round-4/live_sweep.py` **120 records** (108 × 200, 12 expected 404), 0
horizontal overflow, 0 page errors, 0 failed requests. PNG export 38,876 B.

### Coverage that existed (retained — see the manifest's Group C note)

| Area | Type | What it checked | Original path |
|---|---|---|---|
| Platform suite | pytest (223 tests, ~12 min) | Editor, typography, canvas, i18n, security, admin, hosting, release evidence | `tests/` |
| Gate runner | script | build → bundles → smoke → layout → pytest → budgets → lhci → csp → canvas → important | `tools/run-gates.py` |
| Layout guard | Playwright (1,693 checks) | 16 routes × widths × themes × languages; empty controls, clipped fields, artboard size, console baseline, long tasks > 600 ms | `tools/ui-layout-guard.py` |
| Canvas motion | Playwright (22 pass / 0 fail / 2 skipped) | Pan, zoom, fit, selection, reduced motion, ctrl-wheel page-scroll contract | `tests/canvas_motion_playwright.py` (frozen) |
| Route budgets | pytest + script | Six page weight ceilings and the split-bundle sum | `tests/v14_*`, `tests/route_budget_utils.py` |
| Lighthouse | LHCI (16 routes) | Performance/accessibility/SEO budgets, `minA11y 1.00` | `tools/lighthouserc.js` |
| CSP | script (13 checks) | No inline scripts/handlers or violations, signed in and out, incl. `designer.html` | `tools/csp-violation-check.py` |
| `!important` ratchet | pytest | Pin 3,791; only downward | `tests/*important*` |
| Smoke | script | 16 pages, 0 console errors, 0 non-2xx | `tools/page-errors.mjs --all` |
| UI audit | Playwright harness | 64 page/variant captures, 70 function shots, 703 raw findings | `tools/ui-audit.py`, `ui-audit-report.py` |
| Interaction sweeps | Playwright | 62/62 interactions, 48/48 route × theme, 0 console errors | `artifacts/ui-audit-2026-10-30/*.mjs` |
| RILL walkthrough | Playwright | Nine-step create → publish → RSVP flow, 0 console errors | `RILL-WALKTHROUGH.md` (archived) |
| Clean clone | manual | README steps on a fresh clone; 223 passed in 661.90 s | LT-8.1 |

### Known flaky or failing tests

| Test | Symptom | Cause / resolution |
|---|---|---|
| `lt_2_6` PDF metric | MAE 4.24–4.75 against a 4.5 tolerance | Two product defects in `printAllPages()`, fixed as **D-5**; MAE now byte-identical 3.5922 |
| `ctrl-wheel-no-page-scroll` | Failed 4/5 runs | Asserted an inner scroll box whose range collapses with zoom; amended to assert document scroll (**FB-65**) |
| `plain-wheel-scrolls-native` | Failed 2/15 | Stage not yet rendered when the zoom guard ran; now waits and skips with a reason (**FB-66**) |
| Layout long-task rows | 11 red rows 601–1010 ms, later sporadic 600–653 ms | Single 1.07 MB bundle compile; fixed by the split (**FB-66**). Isolated probe still showed 5/108 cells over on a loaded host before the split |
| 375 px editor GPU crash (headless) | GPU process dies after `set_viewport_size` on a heavy canvas page | Harness uses a separate 375 page; not a product fix |
| Two editor tabs on one invitation | Second tab never sets `editorReady` | Open (D-3) |

### Commands that existed

| Command | What it does |
|---|---|
| `make build` | `python3 build.py all` — regenerate bundles, manifests, mirror |
| `make check` | `python3 build.py bundles --check` |
| `make test` | `.venv/bin/python -m pytest tests/` |
| `make serve` / `make serve-gzip` | static preview (plain / compression-correct) |
| `make dev` | real server (API + assets) |
| `make perf` | `npx @lhci/cli autorun --config=tools/lighthouserc.js` |
| `make smoke` | `node tools/page-errors.mjs --all` |
| `make reproduce` | `bash tools/reproduce.sh` (build, tests, LHCI, determinism) |
| `.venv/bin/python tools/run-gates.py --phase all` | the ten-phase matrix |
| `npm run serve:lhci` / `npm run lhci` | gzip server / pinned LHCI CLI |
| `python3 tests/v27_3_5_release_evidence_test.py --repin` | prints the README digest for the pin |

## 5. Lessons learned

- **Measure before fixing.** The editor's first-paint CLS theories (late layout class, font swap, header
  clamp) were all disproved; the real cause was two components disagreeing about the starting tab.
- **Assert the right box.** Two frozen canvas checks were red for months because they asserted an inner
  scroll container whose range follows zoom, not the page.
- **A stale mirror hides budget bugs.** `index.html` loaded two stylesheets for a long time because the
  `src/python/` copy was out of date.
- **Duplicate chrome is not free.** Presence pill, typography bar, status launchers and the mid-canvas
  menu each cost a P1 collision; removal beat every override.
- **Never write Khmer.** 42 strings still need native copy because an agent must not invent them.
- **Regenerable is a claim to verify.** `artifacts/` is gitignored, so nothing there can be restored from
  git; treating it as "just evidence" is how a clean-up destroys the only proof.
- **Refs before deletion.** A fourteen-month pile of reports is safe to remove only when the restore ref
  exists and the tests that read them are identified first (four tests read docs/build files here).
- **Ceilings, pins and digests are load-bearing.** The README SHA pin, the `!important` pin, the route
  budgets and the long-task ceiling each encode a decision; none may be edited to make a gate green.

## 6. Removed files index

- Every removed path, its group, size and one-line summary: **`docs/CLEANUP_MANIFEST.md`**.
- Restore one file: `git checkout backup/pre-cleanup -- <path>`.
- Restore everything: `git checkout backup/pre-cleanup -- .`.
- Untracked material (work orders, review screenshots, capture output) was archived before deletion to
  `artifacts/cleanup-backup-2026-11-01.tar.gz`, which is gitignored and stays on this machine.
- The evidence trees themselves (`artifacts/`, 2.7 GB) were **not** deleted: they are untracked, so no
  git backup exists. The manifest records them as deferred, pending the owner's word.

## 7. Round-4 close-out (2026-11-02)

- **Deploy unblocked.** After the daily allowance reset, `sites_deploy` returned
  `state: succeeded` at 2026-11-02T01:46:34Z and `sites_inspect` reports
  `published: true`, daily requests 0 / 10,000. Production:
  https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page. No code change was
  needed to clear the blocker; the previous rounds were correct to record it as external.
- **CLS 0.4959 → 0.4840 → 0.3927.** Same harness (`artifacts/verify/cls_bundle_probe.py`,
  1440×900, load-only, 7 s settle, buffered Layout Instability API) against the built bundle:
  15 shifts, 0 page errors. The two causes fixed were a toolbar that computed `flex-wrap: wrap`
  (118 → 60 → 106 px as children arrived) and `#advancedTextLayout` being injected open into the
  Text group. Residual: first-paint 62 px toolbar/topbar ramp, Pages builder remount (~0.05), a
  6 px layout step, and a late inspector-group growth. Target ≤0.1 still not met, so this is
  recorded as improved, not closed.
- **BUG-R1-4 closed.** Both manual runners assert current v17 behaviour and exit 0. The drift was
  fixture-side: settled rects were read mid-transition; snapping renders `.motion-line.motion-snap`;
  guides go through `EInviteMotion.measurements.addGuide()`; mobile defaults to the quick inspector;
  `v0_52` expected the pre-v17 hidden outline. Details in `bugs/round-4/FINDINGS.md`.
- **Round 5** verified the deployed origin (16 routes at 1440/360, key screenshots) — see
  `bugs/round-5/FINDINGS.md` and `bugs/round-5/live-smoke.json`. All 32 loads were clean, and the
  live `bundle-index.css` SHA-256 matches the local built file (`8e323747…1aced`), confirming the
  deployed worker serves this build.
- **Final gates:** `python3 build.py all --check` → `BUILD_OK` / `MIRROR_CHECK_PASSED`;
  `python3 -m compileall -q src/python tests tools` → 0 (one pre-existing `SyntaxWarning` in
  `tools/proof-public-page.py`); full suite **231 passed, 1 warning in 1291.81 s (exit 0)**. The
  repo has no ESLint or TypeScript toolchain, so `node --check` on the changed JS plus the build
  check are the available static gates.

## 8. Round 6 — six-width sweep and local fixes (2026-11-02)

- **Coverage.** All 19 routes at 360/390/768/1024/1280/1440 on the published origin: **114/114
  loads**, every one 200 or the intended 404, 0 horizontal overflow, 0 page errors, 0 unexpected
  console errors. 108 “clipped” records are `.skip-link`/`.sr-only`; the 8 px right-edge buttons are
  the landing demo’s horizontal tool strip (same hits as round 4); the missing-slug 404 reports its
  deliberate subresources plus Cloudflare’s CSP-blocked beacon.
- **First interaction pass.** `live_flows.py` at all six widths: **219 checks, 204 passed, 15
  failed**, 202 state captures. All 15 were harness assumptions: the responsive drawer covered the
  pointer target, redo re-inserts an object with a new id, Appearance is a Light/Dark menu, and the
  missing-slug page deliberately fetches a second 404 API path. No product defect was confirmed.
- **Fixes.** Canvas/X now closes and keeps closed the responsive inspector while preserving the
  selection (`mobile-editor.js`, `editor-core.js`). The selection context row ships at its final
  position instead of being reparented after paint (`editor-pro.js`, `index.html`). The Pages tip is
  appended after the manager instead of above it (`studio-experience.js`). Boot-safe selection and a
  silent prewarm stop transient inspector groups from opening (`app.js`, `inspector-reorg.js`,
  `first-selection-prewarm.js`). Toolbar/geometry stabilization lives in `stabilized.css`.
- **Final local pass.** **225/225 checks, 0 failures** at six widths, clean console, page errors and
  unexpected requests. The final 1024 gesture fix scrolls the selected title into the canvas and
  requires its center to be in-view before dragging; the earlier failure screenshot showed the drag
  click hitting the topbar preview. Record: `bugs/round-6/live-flows-six.json`.
- **CLS.** Editor first paint on the final bundle measures desktop **0.0698 / 0.0679 / 0.0810**
  and mobile **0.0973 / 0.0973 / 0.0943** over three consecutive runs each, against baselines
  0.4067 / 0.6219. All six runs are < 0.1. The late 220 → 502 → 220 px Pages-group reflow is gone:
  the prewarm selection keeps non-page groups hidden, and the mobile class plus final brand markup
  now ship in the initial HTML. Residual `.ix-groups` movement is ≤ 0.0020.
- **SQLite teardown.** `get_platform_v32_service()` now shuts down the old job queue when the DB
  path changes, and the autouse data-dir fixture stops it before restoring `EINVITE_DATA_DIR`, so
  workers no longer poll a removed database during teardown.
- **Local guest/editor depth.** `bugs/round-4/flow_sweep.py` **61/61**, 0 console errors, six widths:
  guest hero/Khmer digits, zero empty feature panels, single credit, RSVP validation + thank-you,
  gallery form, editor drag/resize/rotate/multi-select/undo-redo/add/save/reload/export.
- **Live deploy still blocked.** The origin hit **HTTP 429** at 03:40Z: daily requests **10,301 /
  10,000**, site **paused**, reset **2026-11-03T00:00Z**; data preserved. The single production
  deploy attempt (`593d9b20-ecfb-4e0d-9d88-799f4c6099ed`) was refused before a receipt; the
  latest successful deployment remains 2026-11-02T01:46:34Z. No live deploy or live pass is
  claimed for these app fixes, and no retry was made.
- **Gates:** `build.py all` exit 0, `build.py all --check` → `BUILD_OK` / `MIRROR_CHECK_PASSED`;
  `compileall` exit 0; changed JS passes `node --check`; full suite **247 passed, 16 warnings in
  1092.83 s (exit 0)**. The 16 warnings are the example plugin's `PytestReturnNotNoneWarning`s;
  no SQLite/thread warning remains. The repo has no ESLint or TypeScript toolchain.

## 2026-11-03 — round 10: `/templates` layout shift

- **BUG-R10-1 fixed.** `/templates` shipped the 36-design pack gallery only after first paint:
  `template-pack-gallery.js` inserted its section above `#studioGrid` when the module loaded,
  and the catalogue fetch grew it from 126 px to 3188 px at ~630 ms. The studio grid's visible
  state was pushed from y≈442 to y≈3500 — CLS **0.825** at 1440×900 and **0.267** at 390×844.
- **Fix.** `templates.html` now ships the gallery section and **36 skeleton cards** in the
  initial markup, with the gallery stylesheet and a static `data-pack-gallery-module` script.
  `mount()` adopts that section instead of inserting one, hydrates the cards, clears
  `aria-busy` and removes the skeletons. The reserved height means nothing below the gallery
  moves. Measured after rebuild/restart: CLS **0.0101** desktop / **0.0009** mobile, LCP
  568/500 ms, 36 real cards, 0 skeletons, Khmer switch intact, no horizontal overflow,
  console/network clean.
- **Sweep.** Post-fix six-width run: **249/249 checks, 0 failures, 6/6 widths**, clean
  page/console/network (only the deliberate missing-invitation 404s). Record: `bugs/round-10/`.
- **D-2 closed by measurement.** Guest LCP is **1004 ms** desktop / **1328 ms** mobile (LCP
  element `STRONG`, not the hero image) and guest CLS is **0 / 0.031**; no change needed.
- **Gates:** `build.py all --check` → `BUILD_OK` + `MIRROR_CHECK_PASSED`; `compileall` exit 0;
  all `src/js/*.js` pass `node --check`; `npm audit` 0 vulnerabilities; `git diff --check` clean.
  `einvite-app` restarted, `/api/health` 200 before the re-run. No push, no Sites deploy.

## 2026-11-03 — verification close-out

- **Manual runners repaired and green.** `v17_professional_editor_core_test.py` (rotation) and
  `v0_52_free_canvas_drag_test.py` (canvas drag) both exit 0; the full
  `v17_professional_editor_test.py` and `v17_professional_editor_mobile_test.py` also exit 0.
  The fixes are test-side only: wait for the animated object and overlay rects to settle, open
  the Transform disclosure before typing, boot a fresh page per mobile width, and reuse the
  existing 1 px subpixel tolerance. No product code changed.
- **Full suite:** **252 passed, 16 warnings in 1069.40 s (0:17:49), exit 0** on 2026-11-03.
  The 16 warnings are the example-plugin return-value warnings; no test failed.
- **Accessible names:** every control on the Responses and Materials pages has an accessible
  name — **12/12** and **26/26**, audit including each page's generated card markup; no markup
  change was needed.
- **Docs:** NEXT-WORK #23 is fixed, the missing-label bullet is closed, verification debt #13
  is superseded by the local-origin revision, and #7 records the suite run.

## 2026-11-14 — language-migration P2 (route inventory freeze)

- **Scope.** `language-optimization-plan-v3.1.md` §14 item 3 (precondition P2), the only
  precondition that is fully executable inside this repo. No product code, no dependency, no
  gate, no budget changed. The plan file itself stays untracked until the owner answers D10.
- **What was missing.** The plan's numerator (“155 `/api` paths”) was unverified, the route
  table does not exist (`src/python/server.py` is a hand-written `if` chain), and the 16-vs-17
  page disagreement had no record. Each of those is an accounting unit a migration cannot do
  without.
- **Built:** `tools/route-inventory.py` — indexes defs by indentation, walks reachability from
  each `do_<METHOD>` through `self.<helper>(path)` calls, extracts the five declaration forms
  (exact, set, prefix+suffix, regex, dispatch dict), classifies auth from guard symbols across
  the handler's callees, and probes GET-only against a running backend.
- **Frozen:** **345** declarations (GET 143 / POST 144 / PUT 36 / DELETE 22); **336** `/api`
  declarations over **194** distinct patterns (113 distinct exact strings). Auth: 121 user,
  121 invitation-scoped, 36 platform-service, 32 admin, 24 public, 11 unclassified (listed for
  manual read). Artifacts: `docs/language-migration/ROUTE-INVENTORY.md` and `P2-REPORT.md`.
- **Verified, not inferred — the trailing-slash law.** 125 GET declarations probed twice against
  `http://127.0.0.1:4175` (read-only, no writes): **88 pairs differ**. Exact `path ==` routes
  accept no trailing slash (401 → 404 for account, admin, studio and auth routes; 200 → 404 for
  `/api/health`, `/api/auth/me`, `/api/feature-flags`, `/_marketplace/crl.json`); regex routes
  ending `/?` accept both. D6 (“byte-identical”) now has a testable list instead of a slogan.
- **Correction to the plan's auth model.** 36 routes (`/api/platform/v32/*`, `/api/platform/v52/*`,
  collaboration and raster families) are guarded inside `get_platform_v32_service()` /
  `get_future_v52_service()`, not in `server.py`. S6/S9 must port that guard or those routes
  arrive unauthenticated. Recorded in the report §4.
- **Fact table resolved** (report §6): 24,889 Python LOC, 226 JS files / 63,196 LOC,
  `ai_agent` 3,758 LOC / 12 files, 329 test files with **301** tests collected under `.venv`
  (ambient `python3` lacks playwright and stops at 291 + 8 errors), `CIPHERTEXT_PREFIX =
  "gAAAAA"`, passkeys in `server.py:7861–7932`. The 155-path and 716-SQL figures do not
  reproduce; 695 SQL lines in `server.py` and 868 across `src/python` do.
- **Pages:** 16 product pages + 11 test fixtures = 27 HTML files; `PAGE_ALIASES` has 15 entries.
  Fixtures are served by the `.html` passthrough; recommendation is to keep that behaviour and
  exclude fixtures from the S3 parity corpus.
- **Blocked, recorded as blocked:** P1 (no result file, `k6` not installed, needs a staging
  `EINVITE_LOAD_TEST_MODE=1`), P3/D2, P4, P8/D8, P6, P7. Decision D10 is added as owner row
  #19 in `NEXT-WORK.md`.
- **Gates:** `python3 build.py all --check` → `EDITOR_BUNDLE_CHECK_PASSED`,
  `ROUTE_BUNDLE_CHECK_PASSED`, `PAGE_ASSET_MANIFEST_CHECK_PASSED`, `MIRROR_CHECK_PASSED
  (up_to_date=732)`; `python3 -m compileall -q tools/route-inventory.py` exit 0. Full pytest
  was **not** re-run (docs/ and tools/ only); the last full record stays 252 passed on
  2026-11-03.

## 2026-11-14 — language-migration S1 (round-trip equivalence harness)

- **Decision recorded:** D10 answered **Track M now**, Track W parked (owner row #19 in
  `docs/NEXT-WORK.md`; nothing was deleted from that queue). S1 is the first Track M step
  that is not blocked by P1.
- **Built:** `tools/parity-harness.py` with four modes — `--record`, `--replay`,
  `--compare A B` (the shadow tee, R3) and `--self-check`. The corpus is a JSON file seeded
  from the frozen P2 inventory, which is the plan's R4 replay alternative to a 72-hour
  shadow window. It diffs status, nine headers and a normalised body, printing the first
  differing offset with context; exit code is 1 on any diff so it can gate a wave.
- **Exit criterion met:** `--self-check` boots two independent Python instances and reports
  **PARITY 95/96 identical · 0 diff · 1 skipped**, exit 0. Two initial diffs were instance
  facts, not behaviour — `uptimeSeconds`, and `localRoot` pointing at each instance's temp
  dir — and were normalised with that reason recorded. The per-boot CSP nonce (`nonce-…`
  header and `nonce="…"` markup) was the first noise source; folding only one form left
  95/96 red, which is why both forms are normalised.
- **Base-URL switch (plan C1).** `tests/v14_test_utils.fresh_server` now yields
  `(None, EINVITE_TEST_BASE_URL, None)` instead of spawning when the variable is set;
  unset keeps the old behaviour including the FB-09 port-race retry. `tests/conftest.py`
  `server_url` inherits it, so Class A tests target another backend with one variable.
  Verified: set → 0.11 s, `process=None`, no data dir.
- **Known gaps, reported by every run:** no non-GET verb (writes need the plan's Rule 8
  snapshot copy; S11), no authenticated corpus (needs the S6 shared session store), 16
  artefact route families skipped, one route unexercised by transport
  (`campaigns/<id>/deliveries`), and tests that spawn their own server are not yet
  enumerated/converted — that enumeration is the next S1 task.
- **Enumeration (S1 follow-up).** `tools/class-a-coverage.py` classified all **327** test
  files: **153 covered** by the switch, **35** inline their own `Popen` of `server.py`
  (`needs-convert`), **119** spawn a non-backend process, **20** import the backend in-process
  (Class C, not portable by design), **0** hard-code the owner's origin. Artifacts:
  `docs/language-migration/CLASS-A-COVERAGE.md`; the conversion recipe is in `S1-HARNESS.md`
  §4.1. **No file was converted** — deliberate: 35 contract tests each carry their own env,
  port and seeding, and rewriting them without running each would be an unverified change
  dressed up as progress. A “4175” search hit turned out to be `port = 14175`, so `external`
  is genuinely zero; that was checked before being reported.
- **Why it is safe:** no production code, no dependency, no gate or budget touched; the
  helper edits are inert unless the variable is set. Docs: `docs/language-migration/S1-HARNESS.md`.

## 2026-11-14 — ten-phase gate matrix (P5 attempt)

- **Run:** `tools/run-gates.py --phase all`, stamp `artifacts/next-work/gates/20261114-162656`,
  started 16:26:56, finished 16:55:28. Ten of eleven phases exit 0; the chain stops at the last.

| Phase | Result | Evidence |
|---|---|---|
| build | ✅ 5.3 s | `MIRROR_CHECK_PASSED (after sync)` + `BUILD_OK` |
| bundles | ✅ 4.6 s | `ROUTE_BUNDLE_CHECK_PASSED` |
| analyze | ✅ 4.4 s | exit 0 |
| smoke | ✅ 36.2 s | `TOTAL pages=16 consoleErrors=0 non2xx=0` |
| layout | ✅ 218.3 s | `UI_LAYOUT_GUARD_PASSED`, long-task 0 failed (**no flake this run**) |
| pytest | ✅ 1064.7 s | **301 passed in 1063.37 s (0:17:43)** |
| budgets | ✅ 0.0 s | `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED` (6 pages) |
| lhci | ✅ 267.1 s | `Healthcheck passed!` |
| csp | ✅ 59.5 s | `CSP_CHECK_PASSED` |
| canvas | ✅ 43.8 s | `CANVAS_MOTION_VERIFY_PASSED`, 22 pass / 0 fail / 2 skipped |
| important | ❌ 1.2 s | `FAIL important ratchet exceeded: 3837 > pin 3833` |

- **The red is real and pre-existing, not a flake.** The tree carries no working changes; the
  ratchet pin was set on 2026-11-09 at 3833 after measurement, and commit **`3ea09f5`
  (2026-11-10)** — which precedes this session — added exactly four `!important`
  declarations inside its critical-CSS block: `.guest-summary{min-height:260px!important;
  padding-top:42px!important;padding-bottom:42px!important}` and `[hidden]{display:none!important}`.
  The gate is doing its job.
- **Not fixed here on purpose.** OD-6 forbids changing a threshold to pass, and removing
  those declarations is a visual decision about the check-in/guest layout that needs a
  screenshot comparison, not a blind edit. P5 therefore stays **open**: one gate is red.
- **Consequence for the migration:** S2's "the existing workflows and run-gates still pass"
  exit criterion could not be claimed until this was resolved.

## 2026-11-14 — owner decisions, the four-declaration ratchet, and a green matrix

Seven decisions were answered by the owner and recorded in `docs/NEXT-WORK.md` §3: **D2** a
minimal package set for the Node service, **P1** local disposable staging, **D8** PostgreSQL
for the parallel run, **P4** undecided so phases stay serial, plus three code decisions.
The three code decisions were implemented and verified in this pass.

### The `!important` ratchet — 3837 → 3833, no threshold moved

`src/css/critical.css` held exactly four `!important` declarations and was the whole excess:
`.guest-summary{min-height:260px!important;padding-top:42px!important;padding-bottom:42px!important}`
and `[hidden]{display:none!important}`. Every route bundle already carries the identical
unlayered `.guest-summary` rule, so the critical copy only needs to win *before* the bundle
arrives — where nothing competes with it, because `critical.css` lives in `@layer components`
and layered rules lose to unlayered ones regardless. The four markers were removed; the
declarations and their values are unchanged.

- `important` phase: `OK important ratchet holds: 3833 ≤ pin 3833`.
- Visual check on a disposable instance (`artifacts/lang-migration/checkin-1440.png`,
  `checkin-390.png`): check-in page renders correctly at 1440×900 and 390×844, no horizontal
  overflow, and **2 elements carry `[hidden]`, 0 of them compute to a visible display** — the
  UA default plus the bundle rule keep hidden panels hidden.
- Not claimed: a rendered published invitation page (the disposable instance has no
data); `.guest-summary` is untouched in value and the layout guard covers its geometry.

### Defects #24 and #13 (owner rows #24, #12)

- **#24 webhook secret rotation.** `webhook_endpoints` → `secret` added to `PROTECTED_COLUMNS`
  (`core/db.py`) and to `SENSITIVE_COLUMNS` in `scripts/migrate_encrypt_sensitive_fields.py`,
  so `--reencrypt` now rewrites it instead of stranding the secret under the previous key.
- **#13 malformed key.** `core/crypto.py` now raises when `EINVITE_FIELD_ENCRYPTION_KEY` is
  set but malformed **and** `EINVITE_PRODUCTION` is truthy, refusing to boot instead of
  minting an unpersisted key. Development keeps the soft path so scratch data dirs still start.
  The Node port must match (`P6-ENCRYPTION-SPEC.md` §1.1).

### Verification

- **Full matrix, single run, final tree:** `run-gates.py --phase all`,
  `artifacts/next-work/gates/20261114-192448` → **GATES_PASSED**, all eleven phases exit 0:
  build, bundles, analyze, smoke (16 pages / 0 console errors), layout (no flake), pytest
  **301 passed in 987.38 s**, budgets, LHCI, CSP, canvas (22 pass / 0 fail), important (3833).
  This closes verification debt #1 and satisfies precondition **P5**.
- Targeted tests before the matrix: `security_field_encryption_test`,
  `lt_7_2_webhook_signing_test`, `lt_7_2_webhook_delivery_test` → **11 passed in 64.05 s**.
- `python3 build.py all` → `BUILD_OK`; `compileall` on the three touched Python files exit 0.
- No budget, threshold, baseline or frozen canvas was changed (OD-6).

### S2 — the Node service now exists, with no route ported

`services/api-node/` is a Fastify skeleton pinned to **`fastify@5.12.8`** — the whole of the D2
package set — with its own `package.json`, its own committed lockfile (47-component closure) and
its own image. The root `package.json` is untouched, so the lint, bundle and SBOM tooling for the
Python app cannot be perturbed by a service dependency.

- **Route surface:** `GET /healthz` → 200 with `cache-control: no-store` and
  `{status, service, version, uptimeSeconds}`; every other path is a JSON 404. Nothing product-
  facing is routed to it, so it carries 0 % traffic by construction.
- **Supply chain:** the existing `npm-sbom` job now also installs the service closure with
  `npm ci --ignore-scripts`, emits `npm-service.cdx.json` through the root `cyclonedx-npm`
  binary, and audits it at Critical. CodeQL's `javascript-typescript` job already covers
  `services/**` because its config only ignores generated bundles.
- **Verified:** `npm test` **3 passed**; `/healthz` **200** from a live process and from the
  container built by the new Dockerfile; SBOM validates with **47 components**; critical audit
exit 0; `supply-chain.yml` parses; `build.py all --check` still `BUILD_OK` with no drift.
- **Not run:** CodeQL (no local binary — CI covers it) and the workflow end-to-end (runs on
  push/PR; each command it invokes was run by hand instead).
- **Deliberately absent:** any Caddy/compose upstream (arrives at S3 with something to route),
  the S4 schema assertion, and the S6 session/CSRF interop.

### S3 — the Node service serves the shell, byte for byte

The contract was measured from a running Python instance first, which is why the port is
faithful rather than plausible: pages get the critical-CSS inline, a per-response `<style>`
nonce and the `<meta einvite-backend>`/`<base>` head bits, in that order; assets carry
`public, max-age=3600, must-revalidate` plus `Last-Modified`; `If-Modified-Since` yields 304;
**Range is ignored** (Python answers 200 with the whole body, so Node does too); a missing file
is a `no-store` JSON 404 with Python's spacing; and `/i/<unknown>` is a 404 HTML shell with
`no-store` and `X-Robots-Tag: noindex`.

- **Parity:** `tools/static-parity.py` diffed 16 page routes + `/`, 40 mirrored assets, a
  missing asset, `/i/no-such-invitation` and a Range request between Python `:8901` and Node
  `:8902` → **59/59 identical, 0 failing**. Only the nonce, request id and each backend's own
  `host:port` are folded.
- **Service tests:** `npm test` → **5 passed**, including that the body's nonce equals the
  header's and `/checkin` keeps `camera=(self)`.
- **Container:** the first build omitted `lib/` and crashed on boot; fixed and re-verified —
  `/checkin` 200 with one `data-critical` block and `/healthz` 200 with the mirror mounted.
- **Known gaps:** published invitations (`/i/*` serves only the no-row branch until S9), the
  social-card extension when Python lacks Pillow, and no router upstream — so traffic is still
  0 % by construction, not by weight.

### S4 — the data layer runs on PostgreSQL with the same answers

The service gained a thin layer over `pg` (D2's second package) and two ported reads:
`findUserByEmail` (hash-first, then the legacy plaintext fallback) and `findGuestBySlug`. Four
parity choices carry the weight: a quote- and comment-aware `?`→`$n` rewrite, an `int8` parser
that returns a number when lossless (so `created_at` does not turn into a string on the wire),
both `statement_timeout` and `query_timeout` mapped to `QueryDeadlineExceeded`, and a **schema
contract** asserted at boot because the schema has no version counter to compare.

- **DB parity:** the same fixtures through `core.db` (SQLite) and the service (PostgreSQL) →
  **9/9 identical**, values *and* types, covering hash hit, case/space normalisation, legacy
  fallback, miss, empty string, `None`, guest hit and guest miss.
- **Two real findings.** `docs/postgres_schema.sql` omits `users.email_hash` — Python adds it at
  boot (`server.py:2018`), so a fresh PG instance is not the schema the queries expect; recorded
  as defect #25 rather than patched, because Node must not migrate. And `pg`'s own timeout is an
  uncoded `Error: Query read timeout`, so the first `57014`-only mapping never fired; a budgeted
  `pg_sleep(1)` now raises `QueryDeadlineExceeded` in 185 ms and the error handler returns
  Python's 504 body with `Retry-After: 1`.
- **Boot assertion proven both ways:** a valid schema logs `schema contract satisfied` and serves
  `/healthz` 200; an empty database exits **1** with `SchemaMismatchError`.
- **Service tests:** `npm test` → **9 passed**.
- **Known divergences:** SQLite's ASCII-only `lower()` versus PostgreSQL's Unicode-aware one (only
  reaches unconverted rows), a per-statement budget where Python has a per-request one, `numeric`
  left as a string, and a pool default of 10 that a multi-instance deployment must divide.

### S5 — field encryption is byte-compatible in both directions

Fernet is implemented on `node:crypto` (no package): the 0x80 header, big-endian timestamp,
AES-128-CBC with PKCS7, HMAC-SHA256, urlsafe base64 **with its padding**. `protect`, `reveal`,
`revealRow`, the previous-key rotation window and `isCurrentKeyCiphertext` are copied from
`core/crypto.py` and `core/db.py`; `email_hash` is computed with Python's `lower()`/`strip()`
semantics rather than JavaScript's.

- **Two bugs the run caught, not the reading.** The key halves were swapped (bytes 0–15 sign and
  16–31 encrypt — the opposite of the intuitive order), so every Python token failed with
  `Signature mismatch` while both HMACs agreed with each other. And `isProduction()` read
  `process.env` instead of the cipher's injected env, so the production refusal could be bypassed.
- **Parity:** `tools/fernet-parity.py` → **11/11 identical** — Python→Node and Node→Python over
  six values (accents, emoji, tabs, 4 KB, empty), previous-key decryption with the rotation
  predicate false, tampered tokens returned unchanged on both sides, prefix-shaped plaintext left
  alone, and identical hashes for `ΣΣ`, `ΑΣ`, `İstanbul`, `""`, `None` and a BOM-prefixed address.
- **Owner decision on #13 now holds in both runtimes:** a malformed key refuses production boot;
  development keeps the ephemeral path.
- **Not yet exercised:** the DB-level plaintext-leak scan (no Node write route exists until S7)
  and the sidecar key file end-to-end.

### Reports queue read ported, with two baseline defects fixed

`GET /api/admin/reports` now runs on Node behind the same gate as Python: the admin IP allowlist is
checked before authentication, then `require_role("admin", "super_admin")` — 403
"Insufficient permissions" for a denied IP or a non-admin, 401 "Authentication required" without a
session. Filters, the 1–200 limit clamp, digit-only cursors and the `nextCursor` rule are copied.
`tools/reports-read-parity.py` compares twenty cases across three restarts (allowlist unset, denying
`10.0.0.0/8`, allowing loopback): **20/20 identical on two consecutive runs**.

Proving it exposed two baseline defects. Invalid `status` or `limit` raised an unhandled
`ValueError`, so Python closed the connection with no response; the route now answers 400
`{"error": "Invalid status"}` or `{"error": "Invalid limit"}`. And `reports.created_at` was declared
`INTEGER`, which cannot hold epoch milliseconds on PostgreSQL, so every report insert failed there
("integer out of range"); both timestamp columns are now `BIGINT`, and `ensure_schema` widens a
table created by an older build. The 12 reports tests pass. Reports writes remain in Python: the
resolve route is rate-limited and both are writes.

### Analytics and jobs reads ported, and a PostgreSQL-only analytics defect fixed

The analytics dashboard and the jobs lists now run on Node: `/api/invitations/:id/analytics`,
`/analytics/live`, `/api/account/analytics/summary`, `/api/account/analytics/creations`,
`/api/studio/bulk-jobs` and `/api/invitations/:id/materials/import-jobs`. None of these handlers
calls the Python rate limiter, so P7's pin rule did not apply, and none needed a new package.
`tools/analytics-read-parity.py` compares twenty cases against one seeded PostgreSQL serving both
backends — owner/collaborator/stranger access, a malformed `draft_json` that must fall back to
`rsvpEnabled: true`, sort/filter/paging, and the live route with the flag off (403
`feature_disabled`) and on — reporting **20/20 identical on two consecutive runs**.

Proving it surfaced a real baseline defect rather than a porting difference: `queries.py` and the
reconstruction job call `ensure_schema(db)` with no dialect, which defaulted to SQLite and emitted
`AUTOINCREMENT` into PostgreSQL. Every analytics read there raised, and the server's `handle_error`
swallowed it into an empty reply. `model.ensure_schema` now detects the dialect from the driver
connection; the 24 existing analytics tests pass, and the parity run is against the fixed baseline.
Still open in S12c: backup/object storage and the plugin host (the reports queue read landed in its
own change).

### Remaining steps closed out with a ledger, and the flag read ported

The migration plan was closed out as far as evidence allows. `docs/language-migration/REMAINING-STEPS.md`
now carries every step S1–S15 with its status, and for each open one the controlling text quoted
verbatim plus who can clear it. Two claims were tested rather than repeated: S11 is not owner-blocked
— every write handler there calls the rate limiter (`rsvp`, `submit_wish`, `record_public_view`,
`add_guest`, `update_guest`, `delete_guest`) and P7 says *"Share via Redis when `REDIS_URL` is set;
otherwise pin every rate-limited route to one backend."* Pinning is therefore the plan's chosen
state, not a missing decision. S9 remains owner-only for the D2 allow-list reason recorded there.

The unblocked step was `GET /api/feature-flags`: defaults, DB merge order, tier filtering, the
maintenance-mode exclusion and Python's 60-second process cache are all copied rather than
"improved". `tools/feature-flags-parity.py` compares anonymous, free, creator and pro callers against
one seeded database: **4/4 identical on two consecutive runs**, the invitation-read harness still
reports **27/27**, service tests are **47 passed**, and `build --check` is green. Nothing beyond that
is claimed: P1, the shadow ramp, 6-platform certification and the full gate matrix are recorded as
unmeasured.

### S10 — the invitation read cluster, and why S9 waits

S9 (auth) is gated by the dependency policy, not by native-code availability: pure-JS and WASM
Argon2id implementations exist, but the recorded D2 answer is **"Approved and used at S2:
`fastify@5.12.8` only"** and P3 requires an owner-written override **listing each package**. No
Argon2 package is listed, so adding one would breach D2 however it is compiled. The audit also found the
record and the lockfile disagree about `pg` (the row says "fastify only", S4 called it "D2's second
package"); that is flagged in `NEXT-WORK.md` for the owner to settle, not resolved unilaterally. Rather than add one
unilaterally, the next unblocked slice moved:
the editor's first load and the guests/RSVP dashboards' first read.

Six routes moved — `GET /api/invitations/:id`, `/guests`, `/rsvps`, `/versions`, `/versions/:version` and `/api/trash` — with the parts that are easy
to "improve" and therefore easy to break: a deleted invitation demotes its owner and answers 404;
`/guests` answers **403** for a missing invitation while `/invitations/:id` answers 404, because
Python's helper collapses both cases; and the guest payload mints personal links as a truncated
HMAC under the shared guest-token secret, with revoked and expired links returning `null`. The
proof compares those tokens as part of the payload, so a different key fails.

`tools/invitation-read-parity.py` seeds four users with sessions, five invitations, both collaborator
roles, four guests and two RSVPs, and compares twenty-seven requests: **27/27 identical, 0 failing**. The
service suite is **42 passed**. The version timeline stays pinned to Python because it merges
auto-snapshots from `features/invitation_versions.py`, which is its own port.

### S8 — the pattern frozen, and two header gaps it exposed

Writing the ADR was the first time the port's conventions were stated as rules rather than
implemented ad hoc, and it immediately found two divergences: the service always generated a fresh
`X-Request-ID` instead of reflecting a sanitised inbound one (so a request crossing the boundary
split into two traces), and `/api/auth/me` / `/api/auth/logout` sent no security headers at all
because only the page and public routes applied them. Both are fixed; logout also sent its two
`Set-Cookie` headers one at a time, which Fastify replaces, so only the CSRF cookie was ever cleared.

`docs/adr/0001-language-migration-pattern.md` now freezes routing ownership and the pinned routes,
the response/error/504 contract, auth-and-CSRF ordering, query conventions, logging and redaction,
the Khmer-string rule, and the four artefacts a slice needs before cutover (parity harness, unit
tests, written record, clean build). It is linked from `docs/ARCHITECTURE.md` §10. The service suite
is **38 passed** and the S7 public parity proof still reports **9/9 identical** after the changes.

This is the plan's first legitimate stopping point.

### S7 — the public read path moved, with its media signatures

`GET /api/public/<slug>` (Python's `get_public`) is the first vertical slice: a read-heavy route with
no write risk, except two writes that had to move with it — the view counter and a guest's first
`opened_at` stamp. Both are copied; a port that dropped them would change the owner's analytics
without anyone noticing.

The subtle parts were the media signatures and gallery locking. Signed URLs use
`hmac-sha256("<file>|<invitation>|<exp>")` with the shared signing secret, so the Node port has to
produce a payload Python's verifier accepts, not merely a URL of the same shape. Gallery-only images
— ones that appear nowhere else in the document — are cleared when locked and signed when
unlocked; password-protected documents rewrite raw `/uploads/…` paths even inside rich-text strings.
Guest tokens resolve only their own guest and bind `guest.*` objects in both canvas groups.

Proof is `tools/public-parity.py`: one seeded PostgreSQL database, both backends, nine requests
covering 404, 403 and 200 — plain, gallery locked, gallery unlocked, guest token, consent-gated,
password required, password accepted. Each response's media signature is recomputed and verified
with the shared secret before the expiry is masked, so the comparison cannot pass on two differently
signed URLs. **9/9 identical, 0 failing**; 34 service tests.

Not done, and recorded as such: the shadow → 5 % → 25 % → 100 % ramp is a deployment action, the p95
"within 10 % of P1" exit criterion is unmeasured because P1 never ran, and the plan's "public RSVP
status read" does not exist as a route — RSVP is write-only and status reads are the host's
authenticated endpoint. The slice is the public document plus its guest data.

### S6 — sessions ported, and Python's PostgreSQL path turned out not to work

Sessions were already database rows keyed by `sha256(token)` with a `csrf_hash`, so the port is the
checks around them: the join, the idle timeout (30 min admin, 7 days otherwise), the once-a-minute
`last_seen_at` touch, and `guard_cookie_origin()` in order — `Sec-Fetch-Site`, `Origin`, the
double-submit pair, then the stored hash — with Python's three 403 bodies. `GET /api/auth/me` and
`POST /api/auth/logout` are wired, and **26 service tests** cover every rejection path over a stub
query layer.

Trying to prove it across backends is what found the larger problem: **the documented PostgreSQL
deployment had never run.**

1. `platform_v32/schema.py` declared V52 columns as `BLOB`, which PostgreSQL does not have, and it
   parses DDL even under `CREATE TABLE IF NOT EXISTS` — boot aborted. The PostgreSQL adapter now
   maps ` BLOB` → ` BYTEA`.
2. `_try()` swallowed a failed statement, which SQLite tolerates and PostgreSQL does not: the
   transaction aborted and every later statement failed with `InFailedSqlTransaction`. Optional
   DDL now runs under a savepoint, restoring the SQLite behaviour on both backends.
3. **The schema itself had drifted (#27).** Every core `CREATE TABLE` and runtime `ALTER` lives
   inside `connect_sqlite()`, so `docs/postgres_schema.sql` — the only thing a PostgreSQL boot
   applied — had fallen behind. Measured against a real pair: **6 tables and 12 columns missing**,
   including `users.session_never_expires`, which is why `/api/auth/me` dropped the connection
   instead of answering. The schema file now carries the missing tables (with their keys and
   indexes) and columns, with `INTEGER` → `BIGINT` for epoch-millisecond columns, and column
   discovery itself is backend-aware.

Because a stale schema file is how this happened, the fix ships its own watchdog:
**`tools/pg-schema-parity.py`** boots a throwaway SQLite database through the server's own DDL,
reads a real PostgreSQL database, and exits non-zero on any missing table or column. It is the check
nobody had; on both a booted and a never-booted database it now reports zero drift.

Verified: `tools/session-parity.py` reports **18/18 identical** on a booted and on a fresh database;
`pg-schema-parity` reports 0 missing on both; the full Python suite is **301 passed**; SQLite boot
still serves `/api/health` and `/checkin` with no tracebacks; `npm test` 26/26; `build --check`
green. **D8 is now viable** — that was invisible until two backends were actually pointed at one
database, which is the argument for proving interoperability by running it rather than reading a
spec.

## 2026-11-14 — preconditions P6 and P7 (encryption spec, shared-state inventory)

- **P6 written from the code**, not from the plan: `docs/language-migration/P6-ENCRYPTION-SPEC.md`
  covers key resolution, the Fernet token layout, every `None`/empty/disabled edge, the
  read boundary (`reveal` on every string column), the write boundary (explicit `protect()`),
  rotation and the proof matrix S5 owes. Hash vectors are reproduced from `core.crypto`.
- **Corrections it produced.** (1) `NEXT-WORK.md` #13 described a malformed key as falling
  back to the data-dir key; `_load_or_create_key` actually mints an **unpersisted** key and
  `decrypt_field` returns undecryptable tokens unchanged — rows written after that boot are
  unreadable after restart. Row #13 is corrected, severity P3 → P2. (2) There are **seven**
  encrypted columns, not six: `webhook_endpoints.secret` is written through `protect()` at
  `server.py:7628/7639` but appears in neither `PROTECTED_COLUMNS` nor the rotation script,
  so a key rotation strands existing webhook signing secrets. Recorded as open defect #24.
- **P7 written** (`docs/language-migration/P7-SHARED-STATE.md`): 12 items classified.
  Three are process-local — `RATE_BUCKETS`, `STUDIO_BACKUP_LOCKS`, `PRESENCE_STATE` — and
  `PRESENCE_STATE` matters on Target A specifically because the deployment has no Redis and
  the code's Redis-first branch never runs. Two plan wordings were corrected: job claiming is
  already an atomic compare-and-swap (`platform_v32/jobs.py:65,72`), so the S12b gap is stale-
  claim recovery rather than a missing lock; and account lockout is read-modify-write, so
  porting it byte-identically would port a lost-update race.
- **No product code changed.** Both documents assign treatments and owners; they do not
  implement them. Gates: `build.py all --check` → `BUILD_OK` + `MIRROR_CHECK_PASSED` (docs
  only).
- **Gates:** `python3 build.py all --check` → `BUILD_OK` + `MIRROR_CHECK_PASSED`;
  `compileall` on both tools exit 0. Full pytest **not** re-run; the two test-helper edits
  are additive branches and the harness itself exercises `fresh_server` on every self-check.

## 2026-11-22 — admin console reads ported, and the denial audit catches up

The six remaining admin GETs now run on Node: `overview`, the legacy `users` array,
`users-v2`, `invitations`, `audit-events` (JSON and CSV) and `jobs/:id`. They share the same
gate as the reports read — IP allowlist first, then admin/super_admin — and none of their
Python handlers calls `rate_limit`, so P7 did not pin them. `tools/admin-reads-parity.py` runs
**42 cases across three restarts** (allowlist unset, denying `10.0.0.0/8`, allowing loopback)
and reports **42/42 identical on two consecutive runs** against one PostgreSQL serving both
backends. `npm test` went 53 → 66 with a new unit suite for the read models, CSV writer and
Python-compatibility helpers; `build.py all --check` stayed green.

The port did not find a schema defect this time — `docs/postgres_schema.sql` already declares
`audit_events.created_at` as `BIGINT`, unlike the reports table repaired earlier. It did find
four validation paths that answered with **no response at all** on Python (an unhandled
`ValueError` in `users-v2`'s limit and cursor parsing, and in the audit explorer's limit and
date parsing); all four now answer 400 with the message Python already used internally.

One behavioural gap surfaced only because the port had to match a *write* inside a read: the
`unmask=1` action calls `self.audit("admin.users_unmasked", …)`, so Node now writes the same
chained `audit_events` row (sorted compact JSON, previous-hash link, protected metadata,
`admin_only`) rather than unmasking without a trace. The allowlist's `admin.ip_denied` event
is also written by Node now, under Python's 60-second per-IP throttle, so a denied admin
request leaves evidence on either backend.

The reports 400 repair from the previous change had also pushed `admin_reports_list` one point
over the complexity baseline (12 → 13), which made the CI static-analysis gate fail. Its filter
parsing now lives in two module-level helpers; `make analyze` reports `ANALYSIS_OK` again and
`tools/reports-read-parity.py` still reports 20/20 on two consecutive runs.

Still unported: the reports resolve/queue writes, `backup.py` and object storage (P7 row 2),
the plugin launch/install routes (rate-limited, so pinned), and the media/AI paths.

