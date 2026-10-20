# Canva-UI Pass — Work Order & Planning Ledger (Do Not Lose Track)

Repo: `F:\Project\eInvite\online-invitation-platform`
Written: 2026-10-19 · Author of this work order: Freebuff / Buffy (verify each `[x]` before closing)
Owner decisions frozen in this brief — do **not** re-litigate:

- **"Canva type" = Canva-style smooth UI in normal HTML/CSS/JS.** Keep the old page templates as the base; NOT html5-canvas page rendering. `/i/{slug}` behavior and poster rendering do not change.
- **Scope = all 16 app pages.** The published invitation/template artwork stays as-is; the app around it is restyled in place (routes, copy, i18n spans, behavior preserved).
- **Dashboard rebuild authorized** (supersedes "dashboard deferred / do NOT rebuild"): `dashboard.html` returns as a full Canva-style home — signed-out auth two-pane (visual left, sign-in/create-right, EN+KM) + signed-in "Your designs" card grid + quick-start. No WIP shell; no dead dashboard.js null-onclick errors.
- **Testing phase runs only after every page is built**, then one verified commit.

Evidence ledger: `artifacts/ui-audit/fixes/canva-ui/RESULTS.md` (one row per page/fix: page → files → command + observed result → screenshots).

---

## 0. Quick map / where things live

- 16 static pages in `src/html/` (`index.html` IS the editor at `/invitations/{id}/editor`). Server root `src/python/` = build mirror.
- Token + shell truth: `src/css/modern-ui.css` (tokens: `--motion-fast 150ms`, `--motion 260ms`, `--motion-slow 420ms`, `--spring cubic-bezier(.2,.9,.2,1.15)`, `--smooth cubic-bezier(.2,.7,.2,1)`; dark theme `html[data-theme="dark"]`) and `src/css/app-shell.css` (data-shell="a" topbar·rail·content, data-shell="b" focused flow; last-loaded member of every route bundle).
- Cascade contract: `@layer reset, tokens, base, layout, components, utilities, overrides;` — respect it; no new `!important`.
- Build gate after ANY `src/` JS/CSS edit: `python3 build.py all` → `BUILD_OK` + `MIRROR_CHECK_PASSED`; group ends also `python3 build.py bundles --check` → `ROUTE_BUNDLE_CHECK_PASSED`. Known caveat: verify the served mirror actually refreshed.
- dashboard.js (`src/js/dashboard.js`) is a full behavior engine driven by `#loginView / #dashboardView / #inviteGrid / #authSignInTab / #authRegisterTab / #authTitle / #authIntro / #loginBtn / #authStatus / #registerConfirmWrap / #registerConfirmPassword / #passkeyLoginBtn / #logoutBtn / #adminBtn / #designerBtn / #accountName / #newBtn / #createDialog / #createForm / #cancelCreate / #newTitle / #newType / #newTemplate / #templateSearch / #templateChoices / #templateSummary / #quickstartNew / #staticModeNotice(dyn)`. The rebuild restores this markup in Canva-style form (`artifacts/dashboard-page-wip/dashboard.html.orig` holds the removed markup as reference for IDs, not final visuals).

## 1. Motion spec — pinned values (the "exactly smooth" contract)

- Transitions on `transform`/`opacity` only (plus color/border/bg_REPO cheap props); 60fps; interruptible; never gate content on animation completion.
- Durations/eases: hover/press = `--motion-fast` (150ms); open/close drawers, dialogs, toasts, menus = `--motion` + `--spring`; page/fade/pane lifts = `--motion-slow` (420ms) or `--motion`; standard release = `--smooth`.
- Page-enter/exit via the existing app-shell pattern (`body.ui-boot → ui-ready → ui-page-leaving`).
- Hover lift + press feedback already global in modern-ui.css (`.button-link/.cta/.secondary` + cards). Extend to any new control; no double transitions.
- List/card stagger ≤ ~40ms/step, capped ≤ 240ms total, only via CSS `animation-delay` on already-visible content — never delays first paint (CLS safe).
- `prefers-reduced-motion` disables tweens/stagger everywhere (modern-ui.css already kills transitions; add page-local restores where needed).
- `@layer reset, tokens, base, layout, components, utilities, overrides` respected; new CSS lives in `src/css/canva-ui.css` (new member appended to relevant route-bundle sources), `overrides` layer, no `!important`.
- Hard styling floor on every page (shared component floor): frosted topbar + rail/drawer shell, breadcrumbs where present, buttons (`.button-link/.cta/.secondary`), cards/panels, form controls with focus-visible rings, tables with sticky headers, skeletons where data loads, empty states with an action, toasts, dialogs.
- Bilingual: every NEW user-visible string gets `.i18n-en` + `.i18n-km` spans (KM line-height ≥ 1.6, vendored Khmer font). Use the `EInviteI18n.langText` helper in JS.
- Budgets: route-weight (`tests/v55_route_weight_budget_test.py`) and Lighthouse (`tools/lighthouserc.js`, `docs/perf/lighthouse-budgets.json`) stay green by construction — if an idea cannot fit, it is an owner decision, never a budget edit. No new external dependencies.
- Pressure points that must end clean: no horizontal scroll at 320/375 on ANY page (past offenders: analytics, admin, privacy, templates); ≤375px header language switch stays visible/tappable; tablet 768/1024 editor never shows an empty overlay pane; deferred-chunk loader contract intact.

## 2. Build order (all coding before all testing)

### Task A — shared shell/tokens/motion primitives — DONE
- [x] `src/css/canva-ui.css` created: motion utilities (cuStagger 260ms release ease, reduced-motion kill), one-language row surfaces, dashed empty-state component, sticky host-table headers, header-chrome press feel — @layer components, no !important.
- [x] Wired into `docs/route-bundle-sources.json` for 12 host routes (privacy excluded: only 562 B headroom under its 154 KB LHCI ceiling; its reading surface needs none of the shared floor). Build+mirror+bundles all green; v55 PASSED after the backend-mode cause-fix (CRLF drift + comment compaction, token-verified semantics).

### Task B — editor (index.html) — DONE (zero source edits; re-verified live on today's build)
- [x] Studio M1–M9 present: 3-col layout, frosted topbar, collapsible rail, ⌘K palette, selection ring, inspector toggle.
- [x] G3/G4/G6/G7 re-audit on today's build: all four ALREADY FIXED pre-pass (G3 placeholder grid↔none; G4/G7 card builds + floats above selection after real dialog dismiss; G6 drawer reachable via Toggle inspector + mobile Hide controls; earlier "hidden" readings were an onboarding-dialog capture confound).
- [x] Floating selection card above selection (desktop), Position popover states, Flow open, mobile "Hide controls" reachable; 721–1024 contract (editor desktop or non-empty drawer/closed pane).
- Acceptance: screenshots at 1440/1024/768/375 × light/dark × en/km; zero console errors; no empty pane at 768/1024.

### Task C — dashboard + auth rebuild (authorized)
- [x] Signed-out: two-pane auth (left Canva-style visual hero panel, right sign-in/create form, EN+KM tabs, passkey row, validation states).
- [x] Signed-in: topbar + "Your designs" card grid (cover, title, status pill, stats, ⋮ overflow menu with working handlers) + quick-start row (new design row routed through Template Studio) + template filter chips live beneath create dialog.
- [x] No null-onclick console errors from dashboard.js (markup satisfies dashboard.js contracts incl. `#templateChoices/#templateSummary` + filter chips).
- Acceptance: signed-out + signed-in states × {1440,768,375} × {light,dark} × {en,km}; zero console errors.

### Task D — public-guest — DONE (zero source edits; 16 captures in `taskd-public/`)
- [x] Journey smoothness: cover → hero → schedule → RSVP focus → footer; sticky guest header clean at ≤375px; dark + KM states; poster/invitation artwork untouched.
- Acceptance: capture both entry paths; 0 hscroll at 320/375; occlusion rows only known-heuristic.

### Task E — event-operations group — DONE (zero source edits; 84 captures in `taske-eventops/`)
- [x] One visual language for lists/filters/empty states (Task A floor applied per page).
- [x] `checkin.html` + `designer.html` share the app-shell smoothness.
- [x] `templates.html` keeps the gallery feel (cards, filters) + no 320/375 hscroll.
- Acceptance: 0 hscroll 320/375; empty states have actions; per-page screenshots.

### Task F — account-admin group — DONE (zero source edits; 96 captures in `taskf-account/`)
- [x] One Canva-like language for cards/forms/tables; `verify.html` + `reset.html` match the dashboard auth look; privacy keeps reading-surface rules.
- [x] `admin.html` 403 mock view + `billing.html` gradient rows stay within contrast heuristics w/o budget edits.
- Acceptance: per-page screenshots; 0 hscroll 320/375.

### Task G — full test phase — DONE (log: `pytest-after.log`; gate logs under `canva-ui/`)
- [x] `python3 build.py all` → BUILD_OK + MIRROR_CHECK_PASSED; `python3 build.py bundles --check` → ROUTE_BUNDLE_CHECK_PASSED.
- [x] Smoke: `node tools/page-errors.mjs --all` → **16 pages, 0 console errors, 0 non-2xx**.
- [x] Full pytest `python3 -m pytest tests/ -q -s` → all green (baseline 141/0; log `artifacts/ui-audit/fixes/canva-ui/pytest-after.log`).
- [x] Frozen canvas gate 1 — Playwright acceptance → 22 pass / 0 fail / 2 skip (`artifacts/canvas-motion/verify/acceptance-canva-ui/`).
- [x] Frozen canvas gate 2 — perf → exit 0, failures=[], nothing ≥50ms, p95 6.4 ms (`perf-canva-ui/`).
- [x] Frozen canvas gate 3 — visual: 5 pairs asserted ≤0.95 % + 6th via the same-pipeline matrix (documented register-limiter split): 375D 0.06 % / 1366D 0.06 %; pair race evidence before/after diffs kept (`visual-canva-ui3/`, `_canva-verify/visual-matrix/`). Threshold untouched.
- [x] LHCI: collect (16 pages) + `npx lhci assert` → assert exit 0; a11y 1.00 verified on every lhr report; server stopped.
- [x] After-sweep capture + review: `after/` (240+ shots) + `after-digest.txt` → 0 rows with docScrollW > viewport; interactive states covered per-page in Tasks B–F evidence.
- [x] UI-guidelines review: 0 `!important`, transform/opacity-only transitions, reduced-motion kills, focus-visible parity via modern-ui global rules, native `<dialog>` keyboard dismissal, i18n spans balanced 53/53 — no fixes needed.
- [x] RESULTS.md rows complete; ledger update; this checklist ticked.

### Task H — commit
- [ ] `git add` the pass only (never `src/python/data/`); commit message in the prior style e.g. `feat(ui): canva-style pass — <one-line summary>`; do **not** push. Then update `artifacts/ui-audit/fixes/STATE.md` (Done/Active/Next).

## 3. Review Focus — what most likely bites

1. **New no-`!important` CSS collides with the responsive contract at the bundle end** (equal-specificity ties: last wins). Expect mobile overrides to need later positions, not `!important`.
2. **Dashboards' rebuilt markup must satisfy dashboard.js contracts exactly** (e.g. missing `#templateSummary` would crash `updateTemplateSummary`; missing filter buttons silently breaks chips; `#quickstartNew` there or a null onc).
3. **i18n arrays in JS render helpers with `_html(en,km)`** — new strings in list renders must not bypass the helper; KM line-height 1.6 applies to `.khmer-text`.
4. **A11y-1.00 Lighthouse** is the baseline and must not regress — hover-only affordances need focus-visible parity; ⋮ menus need aria-pressed + keyboard dismissal.
5. **Bundle contract** — new CSS is a `canva-ui.css` member **added to route-bundle sources**; a missing route copy FAILS `build.py bundles --check`.

## 4. Exact gates (verifiable commands)

1. build gates → `python3 build.py all` (BUILD_OK + MIRROR_CHECK_PASSED); `python3 build.py bundles --check` (ROUTE_BUNDLE_CHECK_PASSED).
2. smoke → `node tools/page-errors.mjs --all` (needs server on 8124) → `TOTAL pages=16 consoleErrors=0 non2xx=0`.
3. full pytest → `python3 -m pytest tests/ -q -s` → `141 passed` (or better).
4. canvas gates → **frozen** commands per `CANVAS-MOTION-FIX-TASK.md` §gates (verify at gate time).
5. LHCI → `python3 tools/serve-gzip.py --port 8124` + `npx lhci collect|assert --config=tools/lighthouserc.js` → 16/16 exit 0.
6. capture → `python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/ui-audit-capture.py --out artifacts/ui-audit/fixes/canva-ui/after` + `python3 tools/ui-audit-digest.py --dir .../after --out .../after-digest.txt`.

## 5. Owner decisions surfaced during the pass (do NOT act; list w/ recommendation)

From DESIGN-FIX / earlier audit — still open:
- Poster-doc left-panel countdown/RSVP controls still shown (should hide when `eventType==='Poster'`).
- Hide Event/Blocks rail buttons on poster docs.
- Custom units (in/cm) in the poster size prompt (px-only today).
- Billing gradient-contrast heuristic rows (known false-positive rows).
- Admin mock-view 403 audit rows (heuristic, not a real defect).
- designer.html CSP `unsafe-eval` pageerror (baseline, not ours).
- Inventory doc `docs/reviews/dashboard-feature-inventory-2026-10-16.md` marked some rebuild features (edit-history/sheets/polls event panels on dashboard) as removed; this rebuild restores only the owner-approved core (auth + grid + create) — not sheets/polls dashboards (live on guests page / event sections already).
