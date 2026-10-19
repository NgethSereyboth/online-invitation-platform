# Design-Page Fix Task — Planning Ledger (Do Not Lose Track)

Repo: `F:\Project\eInvite\online-invitation-platform`
Written: 2026-10-19 · Author of this work order: Freebuff / Buffy (verify each ✅ before closing)
Live verification server: `PYTHONPATH=. EINVITE_ALLOW_NO_SCANNER=1 python src/python/server.py` → http://127.0.0.1:4175 (background PID in this session)

---

## 0. How the app is put together (quick map)

- 16 static HTML pages in `src/html/` — **there is no `editor.html`**; the editor lives on **`index.html`** (`#stage`, `#canvasViewport`, `#stageTransform`, `.stage-wrap`), opened at `/invitations/{id}/editor`.
- Sources are hand-authored vanilla JS in `src/js` + `src/css`. Bundles (`bundle-*.{js,css}`, `editor-suite.*`) are GENERATED — run `python3 build.py all` after editing `src/js` / `src/css` and verify the **served mirror** in `src/python/` actually refreshed (check file mtimes or served bytes).
- Server root is `src/python/`; `build.py mirror` copies html/js/css/vendor there.
- Reversible constraint from repo rules: **no npm bundlers**, vanilla JS only, CSP allows no eval/innerHTML in editor JS… Historical reality: several files already use `innerHTML` (e.g. `designer.js`, `editor-pro.js`). Rule for this task: do not ADD new `innerHTML` in these fixes; existing usage left as-is unless touched.
- Frontend routing: template page → "Use" → POST /api/invitations → redirect to `/invitations/{id}/editor` (served as index.html).

## 1. What the user reported

> "design place — couldn't use anything there at all … couldn't create poster whatever size or make an invitation or design it at all."

## 2. Findings from live testing (agent-browser, signed-in designer account)

| # | Severity | Finding | Root cause (files) |
|---|---|---|---|
| F1 | HIGH | **No way to create a poster or choose canvas size.** There is no poster/social-size preset flow at all; only template "Use" and "blank free design" page (fixed 390×844). | `src/js/dashboard.js` (builtInDocument only has templates), `src/html/index.html` stage is fixed `width:min(390px,100%);height:844px` in CSS; `data-device` buttons only change **width** in `src/js/app.js:2698`. |
| F2 | HIGH | **index.html editor shows a blank stage** when no signature/template url param (client already has hide logic — must re-verify after fixes; earlier session saw blank on some visits). | Confirmed collapsed stage on first visits; relates to `.studio-experience` pre-init; retest needed. |
| F3 | MED | Clicking **Event / Blocks** panels hides the canvas entirely (`stageWrap.hidden=content`) — user loses the poster they were arranging. | `src/js/editor-layout-stability.js:35-39`, `workflow-refine.js:96`, `workflow-continuity.js:46`. |
| F4 | MED | `designer.html` throws a bare "Designer Workspace unavailable / Authentication required" if you're not signed in with the right role. Users see nothing. | `src/js/designer.js:15`, `bundle-designer.js:334`. |
| F5 | LOW | `dashboard.html` "My Invitations" is a stub ("This page is being rebuilt"). | `greens` task in `docs/…` need not be done now but was noticed; do not depend on it for poster creation. |

## 3. Do-this-next order of work (plan → edit → build → verify → next)

### P0 — Poster creation + sizes (design page's main ask)
- [ ] **A:** Build a **"New design" choice UI**: poster vs invite, plus size presets. Where: `src/js/dashboard.js` — extend existing create form (already wired to `#createForm` POST /api/invitations). Add type options + width/height.
- [ ] **B:** Extend `baseDocument` to accept `canvas: {width,height}` so a poster doc persists its real stage size (persist `document.canvas` — the editor will read it back on load, see P2.
- [ ] **C:** Make `#stage` read `document.canvas.width/height` on load; wire `data-device` buttons + a **new Sizes picker** (A4 portrait/landscape, 1080×1080 IG post story, 1080×1350 portrait, Stories 1080×1920, A5, Letter, Facebook cover 1200×630, YouTube thumb 1280×720) — plus free W×H inputs (pt/px).
- [ ] **D:** `/invitations/{id}/editor` route must accept poster docs and render correctly (no crash from RSVP-dependent sections when `settings.rsvpEnabled=false`, poster type has no guest flow).
- Acceptance: from either dashboard or editor, "New design → Poster → Instagram Post 1080×1080" creates & persists a doc whose stage is 1080×1080 after reload, has a Publish snapshot that still resolves, and design-page + thumbnails consistently honour size.

### P1 — Editor security of the "blank stage" (F2)
- [ ] Seed default objects when a fresh invitation is created (no template) instead of falling back to empty stage; and add "�finance Blank canvas" interstitial only when `objects` is empty rather than a hard break-of-layout.
- [ ] Re-verify the collapse bug via wired template route (documented as F3 once retested).

### P2 — Keep canvas visible when Event/Blocks tabs open (F3)
- [ ] Change `editor-layout-stability.js` so Event/Blocks set `studio-content-mode` **without** hiding stage: keep stage visible on desktop ≥1180px; auto-hide only on mobile/compact widths.
- [ ] Keep content panel usable on right (overlay it as a drawer like inspector on desktop, not by killing the stage).

### P3 — designer.html + docs ghost wall (F4, F5)
- [ ] `designer.js`: if not signed in or role miss, show a friendly "Sign in as Designer or Admin" page with a **sign-in link and the list of missing capabilities** — not bare "Authentication required".
- [ ] Also fix the "open the design studio" on dashboard when not signed in: route to register/login with `?next=` so the user lands back where they started.

### P4 — Style refresh (aimed at "rea-canva" look: cleaner, Canva-like)
- [ ] Sharper focus on the canvas: drop the dotted canvas background to subtle dot-grid; increase spacing discipline.
- [ ] Unify accent color tokens in studio panels with the Khmer-rose-appropriate brand tone.
- [ ] Make the "toolbar" more Canva-like: grouped tool buttons, floating style.
- [ ] Improve the left rail icons/labels rendering (currently very small fonts).

### P5 — Test & evidence collection (agent-browser)
- [ ] Create poster → inspector R/W → resize → Publish → visit public URL.
- [ ] Take before/after screenshots into `artifacts/design-fix/`.

---

## 4. Freebuff/agent working rules

- Do NOT skip: after any JS/CSS edit in `src/`, run `python3 build.py all` and check exit + mirror succeeded (`bytes(mirror)==bytes(src)` spot-check with `git status`). Else the fix "works in source but not served".
- Bundle check gate: `python3 build.py bundles --check` must stay green.
- `tests/` gates: no weakened thresholds. If a domain test pins `builtInDocument` shape, update the test ONLY when the plan doc says the change is intentional and say why in the PR text.
- Use `agent-browser` (session task-3cbec8aceed3 active) for screenshots of all fixed flows.

## 5. Verification checklist before closing the task

- [x] Server running + browser session live.
- [x] Create → Poster → sizes → editor loads with correctly sized canvas → `artifacts/design-fix/ui-poster-final.png`, `persist-1080x1920-after-reload.png`.
- [x] Event/Blocks panels keep the canvas on desktop → body of the final report + screenshots.
- [x] designer.html shows guidance/sign-in affordance instead of dead end → `artifacts/design-fix/designer-friendly-error.png`.
- [x] `build.py all` + `build.py bundles --check` pass → BUILD_OK / ROUTE_BUNDLE_CHECK_PASSED / MIRROR_CHECK_PASSED.
- [x] Final report: [`DESIGN-FIX-REPORT.md`](../../DESIGN-FIX-REPORT.md)

## FINISHED — 2026-10-19. All P0–P4 items implemented, built, and browser-verified. Report: DESIGN-FIX-REPORT.md.

## Continuation round (same day)
- [x] Custom W×H canvas size (Custom size… picker option) — verified 800×600 live.
- [x] Poster docs auto-open the Elements pane — verified on reload.
- [x] Publish snapshot on a poster — verified, public URL toast (screenshot publish-poster.png).
- Deferred (needs product decision): hide Event/Blocks rail buttons entirely on poster docs; custom units (in/cm) in the size prompt.

## Second continuation (2026-10-19, after continuation round)

Goal: run the full pytest suite that had been skipped during the design fixes.

- Found the pre-existing v55 route-weight budget gate **failing on `bundle-public.css`** (134,281 B > 131 KB budget by 137 B) — a breach predating this task (file byte-identical to HEAD).
- Root-cause fix, no budget bump: extended [`css_bundle()` in `src/python/build/build_route_bundles.py`](src/python/build/build_route_bundles.py) with `css_compact_whitespace()` — collapses indentation/blank-line bytes outside quoted-string and url() payloads while keeping newline presence (newlines between tokens are preserved as `\n`). Proved token-equivalence of the rebuilt bundle against HEAD (don't adopt a whitespace-only transformation without an equivalence proof).
- Rebuilt: all 16 route CSS bundles, page manifests, route-bundle digests; `build.py all` (BUILD_OK, MIRROR_CHECK_PASSED), `build.py bundles --check` (ROUTE_BUNDLE_CHECK_PASSED), v55 gate `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)`.
- Full pytest suite (`python -m pytest tests -q`): **129 passed, 12 failed** in 11m05s. All 12 attributed to environment/repo drift, none to this task: import_decoding ×9 (Node-subprocess harness on Windows), analytics_ingestion ×1 (`/tmp` SQLite path on Windows), khmer_font_fallback ×1 (asserts POSIX `'vendor/noto-khmer/'` but Windows prints backslashes), v27_3_5_release_evidence ×1 (pinned README digest ladder out of date — repo drift). Evidence in verbose log tracebacks.
- Ran test run against a quiet server, then restarted the dev server on http://127.0.0.1:4175.

## Third continuation (2026-10-19): all MD work orders closed out

Read every root-level task/report MD (`CANVAS-MOTION-FIX-TASK.md`, `UI-VISUAL-AUDIT-FIX-TASK.md`, `DESIGN-FIX-*.md`) and drove the remaining problems to a verified end:

- **All 12 suite failures fixed at the root, gates untouched** (assertions unchanged; only how the harness executes):
  1. `import_decoding_test.py` — the Node stdin pipe (`node -`) never sees EOF under pytest on Windows, so each test burned a 60 s timeout. Now the identical program runs from a temp file (`node <file>`), stdout decoded as UTF-8. **×10 now pass.**
  2. `analytics_ingestion_test.py` — literal `/tmp` DB path → `tempfile.gettempdir()`. **Passes.**
  3. `khmer_font_fallback_test.py` — separator-normalise before the same `'vendor/noto-khmer/'` assertion. **Passes.**
  4. `v27_3_5_release_evidence_test.py` — README digest repinned via the test's own `--repin` flow (README was rewritten by committed checkpoint `23f7cf6`). **Passes** (includes the three build `--check` subprocess gates).
  - Full suite after repairs: **141 passed, 0 failed** (a later rerun hit the known `test_phase4_rate_limit` ordering flake, which passes in isolation and passed in the clean run).
- **Canvas-motion work order (CANVAS-MOTION-FIX-TASK.md): ACCEPTED.** Fresh acceptance run: **22 pass / 0 fail / 2 skip** (`CANVAS_MOTION_VERIFY_PASSED`); perf gate with the ledger's renderer pinning procedure: **exit 0**, zero ≥50 ms frames / zero long tasks across 3 runs × 4 gestures, crop engaged. Unperf-pinned runs reproduce the ledger's documented environment amplifier (Windows E-core demotion), so no code change was needed; an experiment to pre-create undo transactions at pointerdown was tried and reverted (it worsened unpinned numbers and the pinned gate is clean). Full evidence appended to `artifacts/canvas-motion/ledger.md`; new diagnostic tool `tools/canvas-motion-attribution.mjs` kept.
- **UI-Visual-Audit (UI-VISUAL-AUDIT-FIX-TASK.md):** spot-checked the P0/P2/P3 items against the current tree — P0-2 (gpu-loader 404 chain), P0-3 (dashboard.js null onclick) and P2-1 (duplicated "Saved locally" status) are already fixed in source since the audit (guards/Khmer strings present); P3-1 (`public-page.js` NaN date guard) is present. The heavyweight per-viewport/tablet layout items (P1-1…P1-6) are a separate work order in that file and remain for the owner — they need the capture sweep to re-run, which this session's scope (tests + gates + MDs) doesn't include.
- Post-rebuild gates all green: `build.py all` (BUILD_OK/MIRROR_CHECK_PASSED), `bundles --check` (ROUTE_BUNDLE_CHECK_PASSED), v55 budget gate (6 pages within budget).
