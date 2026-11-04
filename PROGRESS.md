# PROGRESS — autonomous mission log

## Mission revision — 2026-11-03 (owner-directed)
- **Primary origin:** the local PC server at **`http://127.0.0.1:4175`** (`einvite-app`,
  `src/python/server.py`). The Freebuff Sites deployment and its daily request allowance are
  **out of scope** for this mission. No `sites_deploy` call is part of the loop.
- **Loop:** use the same Playwright six-width pattern against the PC origin; record every state
  under `bugs/round-N/`; fix confirmed product defects at the root; rebuild the generated bundle,
  restart the local service when source changes, and repeat. The local service is authoritative.
- **Security workstream:** treat GitHub's open security feedback as a first-class gate. The
  2026-11-03 snapshot is **92 Dependabot alerts**, **118 CodeQL alerts**, **0 secret-scanning
  alerts**, and a failed scheduled Security Scan (`41472118974`, 2026-11-02T15:29Z). Raw API/CI
  evidence is in gitignored `artifacts/security/2026-11-03/`; the triage and fix record is
  `docs/security/GITHUB-SECURITY-TRIAGE-2026-11-03.md`.
- **Security gate:** after fixes, run the local security scan and `npm audit`; a clean result means
  no new high/critical findings and every remaining warning triaged as a false positive or an
  explicit, owner-held follow-up. Do not suppress or downgrade a finding to make CI green.
- **Deployment definition changed:** “deploy” now means rebuild the served bundle and restart
  `einvite-app` on this PC, then verify `127.0.0.1:4175` serves the new hashes. The Cloudflare
  tunnel/public site is ignored unless the owner explicitly reopens it.

## Round 10 — `/templates` layout shift fixed (2026-11-03)
- **Baseline sweep:** the six-width harness passed unchanged — **249/249 checks, 0 failures,
  6/6 widths**, clean page/console/network (only the deliberate missing-invitation 404s).
  The harness does not measure layout stability, so a Playwright CLS/LCP probe was run on
  the two routes with open performance rows. Guest LCP measured **1004 ms** desktop /
  **1328 ms** mobile (LCP element `STRONG`) and guest CLS **0 / 0.031** — both already inside
  target, so D-2 is closed by measurement with no code change.
- **BUG-R10-1 (P1, fixed):** `/templates` measured **CLS 0.825** at 1440×900 and **0.267**
  at 390×844. `template-pack-gallery.js` inserted its section above `#studioGrid` after
  first paint; the catalogue then grew it from 126 px to 3188 px at ~630 ms and pushed the
  studio grid's visible state from y≈442 to y≈3500.
- **Fix:** `templates.html` now ships the gallery section, status line and **36 skeleton
  cards** in the initial markup (with its stylesheet and a static
  `data-pack-gallery-module` script); `mount()` adopts that section, hydrates it, clears
  `aria-busy` and removes the skeletons. Height is reserved before first paint, so nothing
  below moves. After rebuild/restart: CLS **0.0101** desktop / **0.0009** mobile, LCP
  568/500 ms, 36 real cards, 0 skeletons, Khmer switch intact, console/network clean, no
  horizontal overflow.
- **Full re-run after the fix:** **249/249 checks, 0 failures, 6/6 widths**, clean
  page/console/network. Record: `bugs/round-10/` (`FINDINGS.md`, `FIX_PLAN.md`,
  `cls-before`/`cls-after` measurements, 213 sweep captures under `shots/flows-v2/`).
- **Gates:** `build.py all --check` → `BUILD_OK` + `MIRROR_CHECK_PASSED`; `compileall`
  exit 0; every `src/js/*.js` passes `node --check`; `npm audit` 0 vulnerabilities;
  `git diff --check` clean. `einvite-app` restarted and `/api/health` returned 200 before
  the re-run. No push and no Sites deploy — owner-held.

## Verification close-out — 2026-11-03
- **Manual runners:** `v17_professional_editor_core_test.py` (rotation) and
  `v0_52_free_canvas_drag_test.py` (canvas drag) both exit 0 on real runs; the broader
  `v17_professional_editor_test.py` and `v17_professional_editor_mobile_test.py` also exit 0.
  The repairs are test-harness only: wait for both the transformed object and the overlay rects
  to settle before comparing (the 220 ms read was mid-animation), open the Transform disclosure
  before typing, boot a fresh page per mobile width, and reuse the runner's existing 1 px
  tolerance for subpixel quick-sheet width. No product code changed.
- **Full suite:** **252 passed, 16 warnings in 1069.40 s (0:17:49), exit 0** on 2026-11-03.
  The 16 warnings are the example-plugin `PytestReturnNotNoneWarning`s; no failures.
- **Accessible names:** audited every input, select, textarea, button and icon-only control in
  `responses.html`/`materials.html` plus their generated card markup — **12/12** and **26/26**
  named; no markup change was needed. Evidence:
  `artifacts/verify/a11y_names_2026-11-03.json` (gitignored).
- **Docs:** NEXT-WORK #23 is fixed (not stuck), the missing-label bullet is closed, verification
  debt #13 is superseded by the local-origin mission revision, and #7 records the suite run.

## Round 9 — guest/RSVP sweep and harness repair (2026-11-03)
- **Result:** the full six-width sweep passed on the local PC origin —
  **249/249 checks, 0 failures, 6/6 widths**, exit 0, with clean page/console/network
  records. The only 404s are the deliberate missing-invitation pair. Record:
  `bugs/round-9/live-flows-six.json`; report: `bugs/round-9/FINDINGS.md`; 231 captures
  under `bugs/round-9/shots/flows-v2/`.
- **Guest/RSVP coverage added:** the published local invitation `qa-ui-sweep-wedding`
  is now exercised at every width — cover dismissal, heading/sections, one platform
  credit, zero feature panels, English↔Khmer, empty-name rejection, and a valid RSVP
  that must return 200/201 and render its confirmation.
- **No product defect was reproduced.** Two verification defects were fixed at the
  root and committed separately: **BUG-R9-1** (`7f283d5`, v17 mobile runner still
  expected Quick-Edit-first; aligned with the deliberate canvas default) and
  **BUG-R9-2** (`a5d8cc0`, guest harness assumed retired selectors and inferred RSVP
  success from a delay; now asserts the POST response and both language variants).
- **Gates:** `build.py all --check` → `BUILD_OK` + `MIRROR_CHECK_PASSED`; `compileall`
  exit 0; every `src/js/*.js` passes `node --check`; `git diff --check` clean; both v17
  runners exit 0. No `src/` file changed, so the served bundle and its SHA-256 are
  unchanged and current.
- **Push and any hosted deploy remain owner-held.** No push and no Sites deployment
  were performed in this round.

## Round 7 — PC route parity + GitHub security close-out (2026-11-03)
- **BUG-R7-1 (P1, fixed):** the direct PC origin returned 404 for production-style
  `/templates`, `/dashboard`, and `/designer`; only the `.html` paths worked. Added an
  explicit 15-page `PAGE_ALIASES` allowlist in `src/python/server.py` and a byte-for-byte
  alias regression (`tests/page_route_alias_test.py`). No arbitrary HTML fallback exists.
- **Baseline before the fix:** 18 failures across six widths — three per width, all the
  `/templates` 404 and its console/network consequences. **Final after rebuild/restart:**
  **225/225 checks, 0 failures, 6/6 widths**, with clean page/console/network checks.
  Record: `bugs/round-7/live-flows-six.json`; report: `bugs/round-7/FINDINGS.md`.
- **GitHub security feedback:** captured **92 Dependabot alerts / 49 advisories**, **118
  CodeQL alerts**, **0 secret-scanning alerts**, and failed run `41472118974`. The old CI
  failure was Pillow `12.3.0` / Brotli `1.2.0`; current pins are `13.0.0` / `1.2.1`.
  Fixed workflow permissions, preflight logging, scanner temp paths, timeline prototype
  writes, HTTP header values, rich-text regex/fallback, and the npm Puppeteer chain.
- **Security gates:** local scan **PASS** (bandit 0 HIGH, pip-audit clean, SBOM 10
  components); `npm ci` succeeded; `npm audit` **0 vulnerabilities**; `build.py all`
  **BUILD_OK**; `compileall`, `node --check`, and `git diff --check` clean. gitleaks and
  Trivy remain unavailable/skipped. The remote CodeQL ledger is not claimed cleared — it
  needs a push and rescan; remaining dispositions are in
  `docs/security/GITHUB-SECURITY-TRIAGE-2026-11-03.md`.
- **No push and no Sites deploy.** The PC origin is authoritative for this mission.

## Current status
- **Round 10 final (2026-11-03, local):** `/templates` CLS **0.825 → 0.0101** at 1440×900
  and **0.267 → 0.0009** at 390×844 (BUG-R10-1, `fix-round-10`; static gallery skeletons
  reserve the first screen in markup). Guest LCP measured 1.0 s desktop / 1.3 s mobile and
  guest CLS 0/0.031, both already inside target. Post-fix six-width re-run: **249/249
  checks, 0 failures**, clean console/page/network. Record: `bugs/round-10/`.
- **Round 11 final (2026-11-04, local):** clean re-run confirming no regressions since round 10 —
  **249/249 checks, 0 failures, 6/6 widths**, clean console/page/network (only deliberate 404s).
  Editor (add, drag, resize, rotate, multi-select, undo/redo, save, reload/recover, PNG export),
  template studio (cards, search, source/category/favorite filters, Khmer), dashboard (signed-out
  shell, registration, sign-in), designer, missing-404 route, guest invitation (load, language toggle,
  RSVP invalid + submit) all pass at every width. Record: `bugs/round-11/`.
  The first sweep attempt was cut short by the 300 s timeout cap; the second (unbuffered) attempt
  completed successfully — the lone `FAILED 768 drag` line in `sweep.log` is from the overlapping
  first-run writer and is not reflected in `live-flows-six.json`, which shows drag passing at all
  widths. No product defect found; no code change.
- **Round 6 final (2026-11-02, local):** the corrected harness passed at all six widths —
  **225/225 checks, 0 failures**, clean console/page/network. Record: `bugs/round-6/live-flows-six.json`.
  The 15 earlier failures were harness assumptions (drawer, redo identity, Appearance menu, deliberate
  404); the 1024 gestures now reset the canvas scroll, scroll the selected title into the viewport and
  assert its center is in-view before dragging. App fixes: Canvas/X dismissal, static context-row/toolbar
  geometry, Pages tip placement, boot-safe inspector selection (including silent prewarm), deterministic
  mobile/brand shell from first parse, and SQLite job-queue shutdown before data-directory teardown.
  Editor CLS on the final bundle, three consecutive runs: desktop **0.0698 / 0.0679 / 0.0810**, mobile
  **0.0973 / 0.0973 / 0.0943**; all six < 0.1, and the former 0.0573 / 0.0523 Pages-group reflow is
  absent (residual `.ix-groups` movement ≤ 0.0020). The hosting allowance is still paused at
  **10,301 / 10,000**, reset **2026-11-03T00:00Z**, so no live deploy or live pass is claimed.
  The single production deploy attempt (`593d9b20-ecfb-4e0d-9d88-799f4c6099ed`) was refused by
  that allowance before a receipt; the latest successful deployment remains 2026-11-02T01:46:34Z.
  No retry was made.
- **Deployed (2026-11-02T01:46Z):** the post-reset `sites_deploy` succeeded on the first try
  (`state: succeeded`, `published: true`, daily requests 0 / 10,000) and the production origin
  **https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page** now serves this build. The
  allowance is the only thing that had blocked rounds 2–4; no code change was needed to deploy.
- **CLS fixed and measured:** round 6 final editor first paint is **0.0698 / 0.0679 / 0.0810**
  desktop and **0.0973 / 0.0973 / 0.0943** mobile on the final bundle, against baselines 0.4067 /
  0.6219. Every run is < 0.1. The late 220 → 502 → 220 px Pages-group growth is gone; the only
  remaining `.ix-groups` movements are ≤ 0.0020, within normal settled text layout.
- **Manual runners refreshed (BUG-R1-4 closed):** `v17_professional_editor_test` and
  `v0_52_free_canvas_drag_test` now assert v17 behaviour and both exit 0. The v17 fixture waits
  for settled rects, reveals the Transform panel, asserts `.motion-line.motion-snap`, the Guides
  toggle's persisted `editorModel.guidesVisible`, and the quick-inspector mobile default with its
  numeric transform. The stale expectations are listed in `bugs/round-4/FINDINGS.md`.
- **Manual runners verified (2026-11-03):** all four manual Playwright runners exit 0 on real
  runs against the inline v17 fixture — rotation core, canvas drag, the full professional-editor
  runner, and the isolated mobile runner. The repairs were test-side only (settle the animated
  rects, open the Transform disclosure, use a fresh page per mobile width, allow the existing
  1 px subpixel tolerance); no product code changed.
- **Final gates (2026-11-02):** full suite **247 passed, 16 warnings in 1092.83 s (exit 0)**.
  The warnings are the 16 example-plugin `PytestReturnNotNoneWarning`s only; the SQLite teardown /
  `PytestUnhandledThreadExceptionWarning` is gone. `build.py all --check` printed `BUILD_OK` +
  `MIRROR_CHECK_PASSED`; `compileall` exited 0; changed JS passes `node --check`;
  `git diff --check` is clean. No ESLint/TypeScript toolchain exists in this repo.
- **Branch:** `main`, fast-forwarded from `chore/cleanup` at `1b93d57` on 2026-11-01. It was
  **207 commits ahead at the start of phase-2/3**; phases 2–10 plus this close-out make it
  **218 commits ahead of `origin/main`, not pushed**. `origin/chore/cleanup` remains at
  `7e22bef`. The push decision remains open.
- **Queue of record:** `docs/NEXT-WORK.md` — 11 open/owner-blocked defects, **0 stuck**,
  editor CLS **0.0698–0.0810** desktop and **0.0943–0.0973** mobile with no Pages-group reflow,
  **0 untriaged suite failures**, 36 work-order tasks, 18 owner decisions, 11 open verification
  debts (#7 closed by the 2026-11-03 suite run, #13 superseded). History: `docs/HISTORY.md`.
- **Step 1 (finish leftover work):** the two pre-existing suite fixes, the three editor
  baseline failures, the round-10 templates CLS and all manual runners are closed. The product
  backlog's remaining code work is owner-held; the live-only deploy is out of scope under the
  2026-11-03 mission revision.
- **Phase 4–6 (2026-11-01, local):** D-3 is fixed: every editor session refreshes the server row
  and its `updatedAt` while keeping a newer local draft's content, so a second tab no longer
  autosaves against the previous tab's revision. Regression: `editor_multi_tab_autosave_test`
  drives two real tabs. Admin suspension now has UI coverage (`admin_users_suspension_test`),
  and the test environment is isolated (autouse `EINVITE_DATA_DIR` restore +
  `env_isolation_test`). The inline editor fixture inserts its storage/fetch prelude after
  `<head>` and includes `professional-editor.js`; the old `theme-init.js` match silently skipped
  the prelude after the shell changed. Commits: `a9c5e51`, `98d0306`, `e4a81c0`, generated
  bundle metadata `3d6ff85`, and Khmer-fixture policy fix `f2bfcfe`. Final full suite:
  **230 passed, 2 warnings in 1125.10 s (exit 0)**. Details are in the log below.
- **Deploy retry (2026-11-01T12:50Z) — still refused:** the recorded sequence was run end to
  end. `python3 tools/build-sites-bundle.py` exited 0 and the bundle contained
  `manifest.webmanifest` (391 B), `assets/icon-192.png` (8,362 B), `assets/icon-512.png`
  (20,993 B), `og:image:alt`, `twitter:image:alt` and `noindex, nofollow`. The production
  `sites_deploy` then returned the exact error:
  `sites_request_failed — Your sites have reached a hosting allowance and are paused. Open Sites to view usage and reset dates. Your data is preserved.`
  `sites_inspect` reports `quota.state: suspended`, daily requests **10,755 / 10,000 exhausted**,
  monthly 10,755 / 100,000, reset **2026-11-02T00:00:00Z**. A second attempt explicitly requested
  by the owner at **2026-11-01T13:40Z** returned the identical refusal; the platform allowance is
  the only blocker. No further retry is queued.
- **Post-reset deploy (one terminal command + one tool call):** after
  **2026-11-02T00:00:00Z**, run `python3 tools/build-sites-bundle.py`; assert the four bundle
  artifacts above; then call
  `sites_deploy(siteId="5f0c2a7e-3b1d-4c8e-9a6f-2d7e1b9c4a10", environment="production", requestId="<fresh-uuid>", manifestPath="deploy/sites/manifest.json")`.
  There is no shell-only deploy path: the Freebuff Sites API is the deploy command. After the
  receipt succeeds, confirm publication with `sites_inspect`, open the live URL, and repeat the
  live checks for metadata, missing-slug 404, signed-out editor, manifest/icons and second-tab
  autosave. Until then every phase-2–10 change is local-only.
- **P1 editor first-paint CLS — earlier attempts (superseded by round 6):** the 1440×900 probe
  (`artifacts/verify/cls-before.json`) measured **0.5287** over 17 shifts. Attempt 1 shipped
  `page-experience.css` with the document: **0.5075**. Attempt 2 trusted the workflow section
  instead of the synthetic first pane: **0.5179**, so it was reverted. Attempt 3 put
  `#designPagesManager` in its final static position and kept the static stylesheet:
  **0.4959** over 17 shifts (commit `ff5f5c1`). An initial 0.4194 reading was **invalid**: the
  manager had been grouped into the hidden Event pane, and the full suite caught the displaced
  Pages cards. Explicit `data-studio-group="pages"` grouping fixed it; the corrected probe is
  0.4959. The remaining contributors are deferred editor modules growing the canvas toolbar
  (0.1537, 0.0628, 0.0443) and expanding/collapsing the inspector `ix-groups` (0.0581 +
  0.0523); reaching the 0.1 target needs the deferred UI loaded before paint, which is a larger
  boot redesign than the no-rewrite rule allows. The two safe invariants are guarded by a
  collected test in `tests/v22_2_page_experience_contract_test.py`. Round 6 then removed the
  prewarm and post-paint shell causes: the final six-run record is **0.0698 / 0.0679 / 0.0810**
  desktop and **0.0973 / 0.0973 / 0.0943** mobile in `bugs/round-6/FINDINGS.md`.
- **Round 1 (live sweep):** 114 live route/viewport records + 31 authenticated local checks,
  **0 failed checks**; final full suite **223 passed, 2 warnings in 883.42 s (exit 0)**; one P1
  fixed (BUG-R1-1) and proven live, two P2s logged (soft 404, CSP console), one stale
  manual-runner fixture marked stuck. Findings: `bugs/round-1/FINDINGS.md`. The two P2s were
  fixed in round 2.
- **Round 2 (live sweep):** 120 live route/viewport records + 42 authenticated local checks,
  **0 failed checks / 0 application console errors**; the three new P2s are fixed and live:
  empty guest-feature panels removed, album upload row reflowed, duplicate platform credit
  removed. PNG export remains valid (39,023 B); findings and evidence are in
  `bugs/round-2/`. Retested live 200/404 contract, signed-out redirect, Khmer digits and all
  six widths.
- **Round 3 (live sweep, partial — external quota):** 120 live route/viewport records and 120
  screenshots. **118 records verified** (107 × 200, 11 × deliberate 404); the two 1440 records
  `/missing-route-round-3` and the signed-out editor returned **429** because the Sites daily
  request allowance was exhausted, not because of an application response. There was **0
  horizontal overflow, 0 page errors, 0 unlabelled inputs, 0 unnamed buttons and 0 missing alt
  text**. Authenticated flow: **44 checks, 0 failed, 0 application console errors**; PNG export
  40,937 B. Local production-mode 1440 fallback: valid invitation 200, missing slug 404, missing
  route 404, signed-out editor 200 → dashboard, all with zero overflow. **No new product bugs.**
  Findings: `bugs/round-3/FINDINGS.md`; plan: `bugs/round-3/FIX_PLAN.md`.
- **Round 4 (local production bundle, 2026-11-02):** the phase-10 bundle was served on
  loopback (proxy 4180, isolated backend 4181) because Sites is still suspended; per the
  owner's instruction **no `sites_deploy` was attempted**. Public matrix: **120 records**
  (20 routes × six widths), **120 screenshots**, 108 × 200, 12 × expected 404, **0 horizontal
  overflow, 0 page errors, 0 failed requests**, 0 unlabelled inputs, 0 unnamed buttons; the
  18 console errors are the deliberate missing-route 404s. Authenticated flow: **61 checks,
  0 failed, 0 application console errors**; PNG export 38,876 B; the Pages pane shows a real
  card at all six widths; RSVP, gallery reflow and Khmer digits pass. Three P1s fixed:
  **BUG-R4-1** body no longer carries `data-inspector-tab` (`efafe0f`), **BUG-R4-2** the
  creation bar now covers the whole drawer range 601–820 (`1e26fe7`), **BUG-R4-3**
  `syncInspectorDrawer` no longer closes the creation drawer via `closeInspector` (`04270a5`,
  which also removes the old boot-restore observation). Guards are in
  `tests/v14_live_layout_test.py` (768 bar/drawer, stray-attribute, selection-refresh).
  `python3 build.py all --check` is clean (`up_to_date=533`), `compileall` exits 0, and the
  post-fix full suite is **231 passed, 1 warning in 1055.53 s (exit 0)** — the same count as the
  pre-round gate. The
  live site is **not** claimed to run this build; a post-reset deploy plus a repeat of the
  matrix and the 360/768 editor checks is the only external step. CLS is unchanged (stuck at
  0.4959, not re-measured this round).
- **Brotli follow-up (done):** `940a799` raised `docs/requirements-production.txt` and
  `tools/requirements.txt` from 1.2.0 to **1.2.1**. A temporary venv resolved both requirement
  sets with `pip check` clean; the runtime `.venv` is now 1.2.1 and `einvite-app` restarted
  healthy (`/api/health` 200). Build and route-bundle checks pass.
- **Privacy/metadata close-out (phase-2/3, 2026-11-01):** `e9f2ee5` makes published
  invitations link-only (`og:image:alt`, `twitter:image:alt`, absolute canonical, meta and
  header `noindex, nofollow`); missing slugs keep `noindex`. `b58bbaf` makes the check-in
  manifest installable (`id`, `scope`, `/checkin.html` start, local 192/512 icons) and teaches
  the Sites bundle walker to include manifest icons. Full suite **226 passed, 2 warnings in
  1103.27 s (exit 0)**; live deployment remains quota-blocked.
- **Improvement research (docs only, 2026-11-01):** the first pass reviewed current
  web.dev/Chrome performance guidance, W3C/WAI WCAG 2.2, W3C Khmer resources and Noto/MDN and
  captured eight source-backed opportunities. A second pass used the installed performance,
  accessibility and Web Interface Guidelines skills plus targeted research on invitation
  metadata/privacy, check-in PWA/offline, album-photo EXIF and multi-tab autosave; it added
  IMP-9–IMP-12 and a small guideline table. Sharpest new anchors: published invitations are
  indexable and lack social-image alt text; `manifest.webmanifest` has `icons:[]`; album upload
  stores raw bytes while only derivatives strip EXIF; the check-in queue is `localStorage`; and
  D-3 second-tab initialisation remains the highest-risk autosave item. No application source
  changed.
- **Round 0 (baseline close-out):** `lt_4_3`, `lt_4_4` and `lt_2_2` pass — `4 passed in 51.59 s`.
  Verdicts and evidence: `bugs/round-0/FINDINGS.md`; plan: `FIX_PLAN.md`.
- **Live site:** last successful production deploy is `7265e709-7c1a-4af1-9d20-c60d98b092a5`,
  published 2026-11-01 04:15 UTC at
  `https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page`. Served
  `bundle-public.js` SHA-256 is `c44ae93b…858899cc` and served `bundle-public.css` is
  `32c7f20a…4448d87c`; both match `artifacts/sites-public`. The round-3 deploy attempt
  (`8c1d4e2f-…`) was **rejected before a receipt was created**: Sites quota is
  `state: suspended` because daily requests reached **10,755 / 10,000** (monthly 10,755 /
  100,000). The site is paused until **2026-11-02T00:00Z**; no new build is being served. The
  served build is still the last deploy; the phase-10 static-manager/styles changes are local-only.
  `/i/<missing>` and the signed-out editor are verified at 1440 on the local production server.
  `einvite-app` and `einvite-tunnel` are active; preview remains on its 2026-10-31 build.
- **Baseline already measured:** build/bundles/smoke green; layout grazed 600 ms once and passed on a
  quiet rerun; pytest profile before the fixes was **5 failed / 218 passed** (15:01). Full log under
  `artifacts/next-work/gates/`.

## Log

### 2026-11-01 — phase-10: editor first-paint CLS mitigation (P1 stuck)
- The 1440×900 CLS probe measured **0.5287** over 17 shifts before the change. Static
  `page-experience.css` alone reached **0.5075**; the workflow-section boot experiment reached
  **0.5179** and was reverted. Moving `#designPagesManager` to its final static position on top
  of the static stylesheet, with explicit `data-studio-group="pages"` grouping, reached
  **0.4959** over 17 shifts (`ff5f5c1`). The earlier 0.4194 reading was invalid because the
  manager was hidden in the Event pane; the corrected probe is the only measurement used here.
- The remaining shifts are deferred editor modules resizing the canvas toolbar (0.1537, 0.0628,
  0.0443) and the inspector `ix-groups` (0.0581 + 0.0523). Reaching the 0.1 target needs those
  modules to render before first paint, which is a boot redesign rather than a targeted fix. The
  P1 is therefore marked **stuck**, not fixed; the two safe structural invariants are guarded by
  `tests/v22_2_page_experience_contract_test.py`.
- The recorded deploy was retried at 12:50Z and again at 13:40Z after the owner explicitly
  requested it; both attempts were refused by the Sites daily quota. The exact error, quota
  numbers and post-reset sequence are at the top of this file. No further retry is queued.
- The first full run after the static placement failed `template_pack_edit_export_test` because
  the manager was grouped into the hidden Event pane. Explicit `data-studio-group="pages"` fixed
  the regression; the collected contract guard covers the boot invariants. Final suite:
  **231 passed, 1 warning in 1068.91 s (exit 0)**; the warning is the known worker-thread SQLite
  teardown message. `build.py all --check` and `compileall` are green.

### 2026-11-01 — phase-7/8 close-out: generated metadata, suite green
- `3d6ff85` (`phase-7`) records the 86-byte editor bundle change and its new SHA-256 in the
  checked-in page-asset and route-bundle manifests. These are the build's tracked outputs, not
  hand edits.
- The first final suite run (`artifacts/verify/pytest-full-phase4-6.log`) was **229 passed, 1
  failed**: the new D-3 fixture contained Khmer literals, which
  `test_no_khmer_typed_outside_allowed_files` correctly rejects. `f2bfcfe` (`phase-8`) replaced
  them with Unicode escapes; no assertion or allow-list changed. The final rerun
  (`artifacts/verify/pytest-full-final.log`) is **230 passed, 2 warnings in 1125.10 s (exit 0)**.
  The warnings are unrelated worker-thread SQLite messages (`no such table: platform_jobs`, the
  idempotent `ALTER TABLE users` race) emitted during browser-test teardown; no test failed.
- Final gates: `python3 build.py all --check` exited 0 with `MIRROR_CHECK_PASSED
  (up_to_date=533)` and `BUILD_OK`; `python3 -m compileall -q src/python tests` exited 0;
  `python3 tools/build-sites-bundle.py` exited 0. The bundle has `manifest.webmanifest` (391 B),
  `assets/icon-192.png` (8,362 B), `assets/icon-512.png` (20,993 B), and `public.html` contains
  `og:image:alt`, `twitter:image:alt`, and `noindex, nofollow`.
- Live-only checks remain queued for the Sites quota reset at **2026-11-02T00:00:00Z**; nothing was
  deployed.

### 2026-11-01 — phase-4/5/6: D-3, admin coverage, test isolation
- **D-3 root cause:** a second tab reused the cached `sovan-server-invite:*` row and skipped the
  server GET, so its `updatedAt` was the revision from before the first tab's save. The first
  edit sent a stale `expectedRevision` and the server correctly returned `409 revision_conflict`.
  `src/js/app.js` now refreshes the server row every session and only replaces local content when
  there is no cached row or no draft. The local draft is preserved; the revision is not.
- `tests/editor_multi_tab_autosave_test.py` creates an invitation, saves in tab one, forces tab
  two to start from tab one's stale cached row, edits tab two, and asserts both tabs' fields
  reach SQLite with no `serverSaveErrorCode` and `Server connected`. Targeted run: **4 passed in
  31.80 s** together with the two tests below before the runner-fixture fix.
- **D-12 admin:** the Users page already renders the suspension badge from `users-v2`; no product
  change. `tests/admin_users_suspension_test.py` pins the actual `tr[data-user-id]` row and the
  Suspended/Active `.ei-tag` state so the display cannot regress silently.
- **Test isolation:** an autouse fixture in `tests/conftest.py` snapshots and restores
  `EINVITE_DATA_DIR` around every test, fixing the five in-process suites that left a deleted
  temporary path in the environment. `tests/env_isolation_test.py` proves the restore runs between
  tests rather than merely documenting it.
- **Inline runner:** `tests/inline_editor_runtime_test.py` now inserts its storage/fetch prelude
  immediately after `<head>` instead of matching the removed `theme-init.js` tag, and adds
  `professional-editor.js` to the inlined extras. `v17_professional_editor_test` now boots to
  version 17 instead of timing out. Its two behavioural assertions and
  `v0_52_free_canvas_drag_test` were written against the older overlay model and were marked
  stuck at the time; both were repaired on 2026-11-03 (verification close-out above) and remain
  outside the pytest gate.
- **Gates:** `python3 build.py all --check` reported `MIRROR_CHECK_PASSED` and `BUILD_OK`;
  `python3 -m compileall -q src/python tests` exited 0; `tools/build-sites-bundle.py` exited 0 with
  the manifest, icons, and metadata present. Final full suite: **230 passed, 2 warnings
  in 1125.10 s (exit 0)**. The first final attempt found one policy failure in the new D-3 test
  (Khmer literals); `f2bfcfe` replaced them with Unicode escapes and the rerun passed. Live
  deployment remains blocked by the Sites quota until **2026-11-02T00:00:00Z**; no deploy was
  attempted.

### 2026-11-01 — merge `chore/cleanup` into `main`
- `main` was the merge base and had **0** commits not already in `chore/cleanup`; the merge was a
  conflict-free fast-forward from `50721ef` to **`1b93d57`**. No conflict resolution was needed.
- Re-ran the merged-tree gates: `build.py all --check` → `MIRROR_CHECK_PASSED`;
  `build.py bundles --check` → `ROUTE_BUNDLE_CHECK_PASSED`; both exit 0.
- `main` is **205 commits ahead of `origin/main`** and has not been pushed. The feature branch
  remains at the same commit; the remaining live verification/deploy block from round 3 is
  unchanged (Sites daily quota resets 2026-11-02T00:00Z).

### 2026-11-01 — improvement research (docs only)
- Reviewed generic LCP/INP guidance against the actual source: the shared image renderer in
  `src/js/renderer-core.js` adds `loading="lazy"` to every image object (used by the public
  page); `src/css/bundle-public.css` sets hero headings at 1.08/1.05 line-height; the check-in
  service worker is intentionally narrow and network-first; the editor/target-size work is
  already in `NEXT-WORK`.
- Added `docs/IMPROVEMENT-RESEARCH-2026-11-01.md` with eight prioritized opportunities and
  source links, including LCP eager/priority handling, INP measurement, WCAG 2.5.8 hit areas,
  2.5.7 non-drag controls, Khmer line-height/stress testing, AVIF/WebP fallbacks, RSVP error
  messaging and service-worker scope. No app source changed; no new tests were required for a
  docs-only change. `git diff --check` is clean.

### 2026-11-01 — second-pass improvement research (docs only)
- Added IMP-9–IMP-12 to `docs/IMPROVEMENT-RESEARCH-2026-11-01.md`: published-invitation
  metadata/privacy, check-in installability and offline queue, album-photo EXIF retention, and
  multi-tab autosave/lock behaviour. The pass used the installed performance, accessibility and
  Web Interface Guidelines skills and checked the current server/source anchors.
- Confirmed anchors: `src/html/public.html` omits `og:image:alt`/`twitter:image:alt` and uses a
  relative canonical; the only `X-Robots-Tag: noindex` in `serve_public` is for missing slugs;
  `manifest.webmanifest` has an empty icon list and a dashboard/check-in naming mismatch;
  `server.py` stores raw album bytes while derivatives strip EXIF; `checkin.js` keeps its
  unsynced queue in `localStorage`; `collaboration-studio.js`/`workflow-continuity.js` keep tab
  state there too.
- No app source changed. The new items are research findings; indexability, original-photo
  retention and offline-PWA scope are owner decisions, not silent product changes. Docs-only
  verification: `git diff --check` clean; build gates were already green on the unchanged tree.

### 2026-11-01 — round 3: no product defect; Sites quota blocks the final live leg
- Live matrix: 20 routes × 6 widths = **120 records**, **120 screenshots**. 107 × 200, 11 ×
  deliberate 404, 2 × external 429; **0 horizontal overflow**, 0 page errors, 0 unlabelled inputs,
  0 unnamed buttons, 0 missing alt. The 35 console errors are all expected 404s, the quota 429s,
  or the host-injected Cloudflare beacon CSP message.
- The last 1440 width hit the Sites daily request limit. `sites_inspect` shows
  `dailyRequests 10,755 / 10,000`, `state: suspended`, reset **2026-11-02T00:00Z**. The two 1440
  documents interrupted were `/missing-route-round-3` and the signed-out editor; the valid
  invitation and all other widths loaded. This is an external hosting pause, not an app 429.
- Local 1440 fallback against the same source: valid invitation 200, missing slug 404, missing
  route 404, signed-out editor 200 → dashboard, all overflow 0; log
  `artifacts/verify/round3-local-1440.log`.
- Authenticated flow: **44 checks, 0 failed, 0 console errors**. Editor add/drag/resize/rotate,
  multi-select, undo/redo, save/reload and PNG export (40,937 B) passed; gallery form 390/1440
  passed with no clipping; template filter 36 → 1; Khmer digits present; RSVP submitted.
- No product source change. The rebuild is byte-identical to the last deployed static build
  (`bundle-public.js` `c44ae93b…`, CSS `32c7f20a…`). `sites_deploy` was rejected before a receipt
  because the quota is suspended; no new deployment exists. Findings and triage:
  `bugs/round-3/FINDINGS.md`; plan: `bugs/round-3/FIX_PLAN.md`.
- This round is **not fully closed live**: after the reset, redeploy and repeat the two 1440
  records. The app behaviour at that width is proven locally; the remaining gap is host access.

### 2026-11-01 — Brotli 1.2.1 (commit 940a799)
- Updated both requirement pins from 1.2.0 to 1.2.1 and committed separately from the sweep.
- A temporary venv installed production + tools together: module/dist 1.2.1, `pip check` clean.
  The runtime `.venv` was upgraded to 1.2.1 and `einvite-app` restarted; `/api/health` reached
  200 after the normal startup interval.
- Gates: `build.py all --check` → `MIRROR_CHECK_PASSED`; `build.py bundles --check` →
  `ROUTE_BUNDLE_CHECK_PASSED`. Full pytest was not rerun after this dependency-only change; the
  previous full suite was 223 passed.

### 2026-11-01 — Dependabot inventory (docs complete; follow-ups open)
- Created `docs/security/DEPENDABOT-ALERTS-2026-11-01.md` and committed it as `16fd826`;
  the commit is **local only and not pushed**.
- Confirmed counts: **92 alerts / 49 unique advisories**; **13 critical, 49 high, 29 medium,
  1 low** alerts (6/26/16/1 unique by severity). The report includes every alert ID, manifest,
  installed version, fix and advisory link.
- Three open follow-ups identified by the report:
  1. **Pillow:** 82 alerts remain counted against `main` until the already-committed Pillow
     `13.0.0` bump (`dac38e0`) reaches `main`.
  2. **Brotli:** upgrade `1.2.0` → `1.2.1` in `docs/requirements-production.txt` and
     `tools/requirements.txt`.
  3. **npm:** resolve the dev-only advisories through `puppeteer-core` → `chromium-bidi` → `zod`;
     the current `npm audit` reports three high findings.
- No dependency pins were changed in this pass.

### 2026-11-01 — round 2: guest-page P2s fixed, deployed and re-swept
- Live matrix: 20 routes × 6 widths = **120 records**, screenshots per state; **0 horizontal
  overflow**, no unexpected statuses. Expected 404s account for the 18 non-beacon console errors
  (missing-slug document + API, missing route). The host-injected Cloudflare beacon remains the
  only third-party CSP violation.
- Authenticated flow: **42 checks, 0 failed, 0 application console errors** — RSVP, Khmer digits,
  template filter, editor add/drag/resize/rotate/multi-select/undo/redo/save/reload, signed-out
  redirect, wrong-password error, and a 39,023 B PNG export with the PNG signature.
- **BUG-R2-1 (P2, fixed `0604f2c`):** every guest page mounted sign-up, poll and album panels
  before knowing whether the host had data. Empty sheets/polls now remove themselves; the album
  is gated by the gallery setting; the branded credit is reordered after the mounted panels.
- **BUG-R2-2 (P2, fixed `ef2f52a` + `33b43eb`):** the album form's fixed grid clipped “Choose
  photo” and collapsed the caption. Auto-fit columns stack the fields in the narrow card, the
  button owns a full row, and `Load more[hidden]` is actually hidden. Gallery-enabled fixture
  proves both fields are usable at 390 and 1440.
- **BUG-R2-3 (P2, fixed `ef78d67`):** `public.html` shipped a static credit while the renderer
  appended another. The static duplicate is gone; the live page has exactly one credit.
- **Not kept:** the apparent blank design pages are deferred reveal animations; scrolling each
  page into view shows all text at opacity 1. The renderer was left unchanged.
- Gates: `build.py all --check` → `MIRROR_CHECK_PASSED`; `build.py bundles --check` →
  `ROUTE_BUNDLE_CHECK_PASSED`; `compileall` exit 0. Production deploy `7265e709` published
  04:15:09Z; served JS/CSS hashes match the local bundle.
- Final full suite: **223 passed, 2 warnings in 1033.18 s (exit 0)**. The warnings are the known
  teardown-time `sqlite3.OperationalError` on a worker thread; no test failed.

### 2026-11-01 — round 1: live sweep and P1 fix
- Live production matrix: 19 routes × 6 widths, 114 screenshots, **zero horizontal overflow**,
  no unlabelled inputs, no unnamed buttons, no missing alt text. Only the deliberate 404 and the two
  route-level findings produced console/network errors.
- Authenticated local flow (same source, production cannot exercise writes): **31 checks, 0 failed** —
  RSVP, Khmer digits, template filter 36→1, editor Pages pane, save/reload, 1× PNG export (41,042 B),
  390 editor with no overflow, wrong-password error, signed-out redirect.
- **BUG-R1-1 (P1, fixed):** signed-out editor navigations showed raw JSON. HTML `Accept` now gets a
  302 to `/dashboard.html?next=…`; API clients still get 401 (`v12` passes).
- **BUG-R1-2 (P2, open):** missing slug renders "Invitation unavailable" but returns HTTP 200.
- **BUG-R1-3 (P2, open):** CSP blocks a generated `data:image/svg+xml` fetch (two console errors;
  export still valid).
- **BUG-R1-4 (tooling, stuck):** `v0_52_free_canvas_drag_test` times out because the inline fixture
  no longer loads the bundle defining `EInviteProfessionalEditor`; real editor boots in the flow.
- Known defect #6 (second concurrent editor session) reproduced and is not re-scored.
- First full re-run failed only on the Khmer source guard because the sweep fixture carried Khmer
  literals; they were escaped to ASCII (rendered data unchanged), the guard passes, and the fixture
  is committed. The green re-run above is from that tree.
- **Production proof:** deployment `31aca594` succeeded (`published: true`,
  `deployed_at 2026-11-01T02:57:05.865Z`). Live signed-out editor with `Accept: text/html` returns
  **302** to `/dashboard.html?next=…`, with `Accept: application/json` returns **401**, `/api/health`
  returns 200, and the served `bundle-index-2.js` SHA-256 equals the local build
  (`2207b4a8…d021fd04`).

### 2026-11-01 — verification and production deploy
- Full suite: **223 passed, 2 warnings in 866.15 s** (`artifacts/verify/pytest-full.log`), exit 0.
  The warnings are a teardown-time `sqlite3.OperationalError` on a worker thread, not failures.
- Gates: `build.py all --check` → `MIRROR_CHECK_PASSED`; `bundles --check` →
  `ROUTE_BUNDLE_CHECK_PASSED`; `compileall` clean. This repo configures no ESLint, tsc or ruff; those
  build gates are its lint/type-check equivalent.
- Deployed production with the existing `deploy/sites/manifest.json`. Before: live bundle had
  `reorgBody=0`; after: `reorgBody=1` and byte-identical SHA-256 to `artifacts/sites-public`.
- Restarted `einvite-app`; `/api/health` through the Site returns 200. Round 1 not started, per order.

### 2026-11-01 — round 0: the three editor baseline failures
- **BUG-R0-1 (product, P1):** `typography-editor.js` installs after `inspector-reorg.js` and rebuilt
  its shell inside the legacy `#typographyControls`, which the reorg had already hidden after filing
  the controls into the visible Text group. Colour, digit-conversion and run controls were dragged
  back into a hidden container. The shell now mounts into the Text group when the reorg is present;
  the superseded `#advancedTextLayout` is removed so the id stays unique.
- **BUG-R0-2 (stale test):** the shared harness hunted a button labelled `Event details`; the rail is
  rebuilt with the label `Event` and the stable `data-studio-tab="event"` attribute. `open_studio_tab`
  now clicks that attribute (opening the tools drawer at narrow widths).
- **BUG-R0-3 (stale test):** `lt_4_4` waited for `#typographyControls` to be visible, but the
  2026-10-30 reorganisation deliberately hides it. `reveal_inspector_control` opens the real closed
  `<details>` ancestors and the test waits for `#v20RunFont`, the control it drives.
- **No assertion was weakened or removed.** `lt_2_2`'s public-render leg had already passed; the
  public page was never the failure.

### 2026-11-01 — phase-1: platform_jobs table in the SQLite bootstrap
- **Why:** `platform_v32/jobs.py` queries `platform_jobs`, but only `docs/postgres_schema.sql` created
  it. The worker raised `no such table: platform_jobs`, which surfaced as `RemoteDisconnected` in
  `ai_resource_scopes_test`.
- **Change:** the three DDL statements added to `_P2A_SCHEMA_STATEMENTS` (portable SQLite/PostgreSQL),
  so `connect_sqlite()` creates the table and both indexes on the first connection.
- **Verify:** `tests/ai_resource_scopes_test.py`; `build.py all` mirror check.

### 2026-11-01 — phase-1: guest-row actions + public 401 blocks (already shipped)
- `12087a8` delegated row actions on the stable guest-list container; `bbd3b9d` removes the signup /
  poll / album sections on a `401` instead of printing "HTTP 401" on a public invitation.

### 2026-11-01 — phase-1: gallery test aligned with the shared studio filter
- PW-7 removed the per-gallery filter chips so one toolbar filters both lists; the gallery follows
  `einvite:studio-filter`. The test still clicked the removed chips, so it timed out *after* the 36
  cards had rendered. It now drives `#studioCategory` / `#studioSearch` and asserts the same counts
  (15 wedding, 5 ceremony, 36 all, 1 on "maroon") — no assertion removed or weakened.

### 2026-11-01 — phase-2: link-only invitation metadata and robots headers
- `src/html/public.html` now emits generic `og:image:alt`/`twitter:image:alt`
  (“Invitation preview”) with no guest, venue or address data, and a
  `<meta name="robots" content="noindex, nofollow">`. The canonical uses the existing
  `__INVITATION_PUBLIC_URL__` placeholder, so `serve_public()` renders
  `absolute_url('/i/<slug>')` rather than a hardcoded or build-time domain.
- `serve_public()` now sends `X-Robots-Tag: noindex, nofollow` for a published invitation and
  keeps the existing `noindex` for missing/unpublished slugs. No `robots.txt` Disallow was
  added, so crawlers can see the directive. No Event JSON-LD was added.
- Tests: new `tests/public_invitation_metadata_test.py` exercises a real published response
  (alt tags, absolute canonical, meta robots, header) and a missing slug (404 + `noindex`).
  `tests/security_reflected_injection_test.py` was updated to require the absolute,
  percent-encoded canonical while preserving its raw-slug/XSS assertions.
- Pre-fix targeted run failed as intended (`3 failed in 17.40s`); after the fix the targeted
  set passed `3 passed in 17.17s`, then the wider adjacent set passed `34 passed in 65.63s`.
  `python3 build.py all` reported `MIRROR_CHECK_PASSED`.

### 2026-11-01 — phase-3: installable check-in manifest and local icons
- `src/html/manifest.webmanifest` now has `id: /checkin.html`, `scope: /`,
  `start_url: /checkin.html`, and local 192×192/512×512 PNG icons under `/assets/`. The icons
  are generated from the repository's `assets/favicon.svg` mark (rounded `#8d6e46` square,
  white sparkle and dot); no third-party image is referenced.
- `tools/build-sites-bundle.py` now follows `icons[].src` from a `.webmanifest`; without that,
  the manifest was in the bundle but the icons were not. `tests/served_asset_resolution_test.py`
  checks the required manifest fields, on-disk PNG dimensions, and the assembled Sites bundle.
- No offline outbox/queue behavior changed; the manifest metadata only. Targeted adjacent set:
  `34 passed in 65.63s`. `python3 build.py all` reported `MIRROR_CHECK_PASSED` and the Sites
  bundle contained both icons.

### 2026-11-01 — phase-2/3 verification
- Full suite: **226 passed, 2 warnings in 1103.27 s** (`artifacts/verify/pytest-full-phase2-3.log`,
  exit 0). The two warnings are the known teardown-time `sqlite3.OperationalError` on a worker
  thread; no test failed.
- `python3 -m compileall -q src/python tests` clean. This repository configures no ESLint, tsc or
  ruff; `python3 build.py all --check` is its lint/type-check/build equivalent and reports
  `MIRROR_CHECK_PASSED` with 533 mirrored artifacts up to date.
- `python3 tools/build-sites-bundle.py` exit 0; `artifacts/sites-public` contains both icons
  (`icon-192.png` `bc14072c…`, `icon-512.png` `cf116d95…`). No browser sweep was added for this
  scoped metadata/manifest change; the prior six-width visual evidence remains the live baseline.

## Product decisions (not code)
- **Invitation visibility:** published invitations are **link-only by default** for this pass.
  That is why phase-2 adds `noindex, nofollow` in both HTML and HTTP, while still serving the
  page crawlably. This is a product default, not access control: the unguessable token/password
  remains the privacy boundary. If the owner wants public search landing pages, reverse the
  directive; do not add `Disallow` to `robots.txt`. Do not add Event JSON-LD for invite-only
  events.
- **Album originals:** **unchanged this turn.** Album upload stores raw bytes after validation;
  responsive derivatives strip EXIF. The owner must decide whether originals are scrubbed on
  ingest (privacy) or retained for print/edit. That decision blocks further album privacy work;
  no storage or upload behavior was changed here.
- **D-3 (editor second tab/autosave):** **fixed in phase-4.** `connectServer()` always GETs the
  invitation so `serverInvite.updatedAt` is current, but adopts the server document only when
  there is no cached row or no local draft. Local draft content therefore survives while the
  next autosave uses the latest revision. Covered by a two-tab browser regression.

### 2026-11-01 — deploy gate: still quota-blocked after phase-2/3
- At **11:05 UTC** the live Sites API reports `state: suspended`; the daily allowance is
  **10,755 / 10,000** and the exact reset is **2026-11-02T00:00:00.000Z**. Production is marked
  `published: true`, but serving is paused by the quota. No deployment was attempted.
- The last successful production deploy remains **`7265e709-7c1a-4af1-9d20-c60d98b092a5`** at
  **2026-11-01T04:15:09.426Z**. The live site is therefore still the older build; the phase-2
  metadata and phase-3 manifest/icons are committed locally, not live.
- Once the quota clears, the deploy path is: `python3 tools/build-sites-bundle.py` (default
  `artifacts/sites-public`) then the Sites deploy operation
  **`sites_deploy(siteId=5f0c2a7e-3b1d-4c8e-9a6f-2d7e1b9c4a10, environment="production", manifestPath="deploy/sites/manifest.json")`**.
  Then restart `einvite-app` so the Python backend loads the new `src/python/public.html` and
  `src/python/server.py`; fetch a published `/i/<slug>` and assert the alt tags, absolute
  canonical and `X-Robots-Tag: noindex, nofollow`. There is no standalone shell deploy command
  in this repository; the Sites operation is the project's deploy method.
- This is an external quota block, not an application failure. Do not retry in a loop before
  **2026-11-02T00:00:00.000Z**.

## HEAD verification — 2026-11-03
- **Audited commit:** `main` source at **`ebb96d4`**, evidence HEAD **`286080e`**; working
  tree had only the deliberately untracked workspace folders before this evidence commit.
- **Artifact proof:** rebuilt with `python3 build.py all` (`BUILD_OK`, `MIRROR_CHECK_PASSED`),
  restarted `einvite-app`, and confirmed the served `bundle-index.js` SHA-256 is
  **`94570322281650015cd8ea4bc4672fe6649de5f9a08865f8421ea1d31ce2c06a`**, identical to both
  `src/python/bundle-index.js` and `src/js/bundle-index.js`. `/api/health`, `/`, `/templates`,
  `/dashboard`, and `/designer` return 200 on `127.0.0.1:4175`.
- **Independent sweep:** **225/225 checks, 0 failures, 6/6 widths**, clean page/console/network;
  record `bugs/round-8/live-flows-six.json`, report `bugs/round-8/FINDINGS.md`.
- **Fresh GitHub ledger:** 92 Dependabot / 49 unique advisories, 118 CodeQL, 0 secret-scanning.
  The full per-advisory reconciliation is `docs/security/HEAD-RECONCILIATION-2026-11-03.md`:
  **0 current vulnerable packages** (Pillow 13.0.0, Brotli 1.2.1; all seven old npm packages
  absent from the committed lock), 86 generated-mirror CodeQL alerts, and 32 non-generated
  locations reconciled. Hosted counts require an owner-authorized push/rescan.
- **Gates:** security scan PASS (bandit 0 HIGH, pip-audit, SBOM 10 components); `npm audit` 0;
  `build.py all --check` BUILD_OK; `compileall` exit 0; every `src/js/*.js` `node --check` exit 0;
  `git diff --check` clean. gitleaks/Trivy unavailable locally and skipped.

## Open questions
- **Owner-held push + GitHub rescan:** the remote ledger — **92 Dependabot alerts (49 unique
  advisories) / 118 CodeQL alerts / 0 secret-scanning alerts as last fetched** — still
  describes the old default branch because **no push was performed and no rescan was run**.
  The committed HEAD has no current vulnerable pins and all 32 non-generated CodeQL
  locations are reconciled, but the hosted counts will not move until the owner authorizes a
  push and GitHub rescans its ledger. No push has been made; clearing the remote ledger is
  owner-held.
- **Improvement sequence:** the research note recommends measuring LCP/INP first, then the
  low-risk LCP-image, 24 px hit-area and Khmer line-height fixes; the editor INP split and AVIF
  variants should follow only if measurement justifies them. No implementation was started.
- **Invitation visibility reversal:** phase-2 implements the link-only default (`noindex`,
  `nofollow` in meta and header). If the product should instead expose published invitations
  to search, reverse that directive and keep the canonical/alt metadata; do not weaken the
  token/password boundary. This is now a product decision, not missing code.
- **Photo-original retention (owner):** album upload stores the raw bytes after image validation,
  while the responsive derivatives strip EXIF. Decide whether originals are retained (print/edit)
  or scrubbed on ingest; do not promise metadata removal while the original remains fetchable.
  No album storage behavior changed in phase-2/3.
- **Offline check-in scope:** the manifest metadata/icons are now complete, but the offline
  outbox is **not** implemented. If offline check-in is in scope, add an IndexedDB outbox with
  idempotency keys and a single sync leader; otherwise keep the current narrow worker and do not
  cache attendee PII blindly. This was deliberately left out of phase-3.
- **Sites quota reset:** live verification and deployment remain externally blocked until
  **2026-11-02T00:00:00.000Z** (10,755 / 10,000 daily requests). Use the exact deploy operation
  and backend restart recorded in the deploy-gate log above; no code change is expected. After
  the reset, repeat the two interrupted 1440 live records as well as the new metadata checks.
- **Inspector disclosures:** the 2026-10-30 reorganisation files text controls one disclosure deep.
  Round 1 should judge whether that is acceptable interaction cost for colour/digit conversion, or
  whether the Text group should open its first sub-section by default. No change made in round 0.
- **Canvas manual-runner drift (#23) — resolved 2026-11-03:** both stale expectations were
  test-side, not product defects. The rotation check read the object 220 ms into a ~300 ms
  transform, and the canvas runner asserted the retired hidden outline. Both runners now pass,
  as do the full and mobile v17 runners; they remain manual-only and outside pytest.
- **Push the Dependabot report?** `16fd826` is committed locally but not pushed. Pushing it would
  publish the vulnerability inventory to the public `chore/cleanup` branch; decide whether to push
  it now, after the Brotli/npm follow-ups, or not at all.
