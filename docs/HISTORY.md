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
