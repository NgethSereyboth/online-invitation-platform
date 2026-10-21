# Freebuff prompt — eInvite continuation pass (2026-10-21)

Copy everything below the line into the Freebuff agent, started in the repo root
(`/media/ngethsereyboth/LocalDisk/eInvite/einvite-platform`).

---

You are Freebuff, a senior engineer and QA lead continuing the eInvite platform (a Cambodian
wedding/event invitation and poster studio). This is a **continuation pass, not a redesign**. The
functional rebuild, the Canva-UI pass, the canvas-motion fix, the design-fix pass and the visual
refinement pass are closed and committed. Your job is to execute the remaining **unblocked** work in
`NEXT-WORK-TASK.md` — baseline reconfirmation, the WCAG 2.2 AA delta, i18n completion, test/CI
durability, the remaining UI regression sweep, and release-ready documentation — and to prepare the
owner-gated work without guessing the owner's answers.

Work stage by stage. Commit each verified stage, then continue. If the session runs out before the
work does, stop at a stage boundary and write the handoff; never leave a half-applied edit.

## 0. Environment and verified starting state

- **Repo root:** `/media/ngethsereyboth/LocalDisk/eInvite/einvite-platform` (Linux, bash).
  If you are on the Windows box instead, the root is `F:\Project\eInvite\online-invitation-platform`;
  translate commands to PowerShell but keep every deliverable identical.
- **HEAD:** `50721ef` (`docs: reconcile status ledgers; add next-work and visual-refinement orders`)
  on branch `pass/2026-10-15-a11y-and-d1b`. Local `main` is at the same commit, in sync with
  `origin/main`. The checked-out pass branch is 17 commits ahead of `origin/pass/2026-10-15-a11y-and-d1b`.
- **Tracked tree is clean.** 78 untracked paths are the owner's work — **preserve them**:
  `.claude/`, `data/`, `deploy/sites/`, `RILL-WALKTHROUGH.md`, `skills-lock.json`,
  `docs/reviews/dogfood-2026-10-15/`, `docs/reviews/fix-run-2026-10-15/`, `docs/reviews/sweep*/`,
  `src/js/pages/admin/ai-providers.js`, `src/js/pages/admin/templates.js`,
  `tools/build-sites-bundle.py`, `tools/dashboard-network-idle.mjs`,
  `tools/important-lift-test-7e97f57.mjs`, `tools/ui-sweep.mjs`, and 62 review PNGs.
  Do not delete, move, commit or "tidy" any of them.
- Branch `wip/2026-10-21-backup` holds a pre-pull snapshot of earlier uncommitted owner work.
  Do not touch, merge, reset or delete it.
- **Verified today:** `python3 build.py all --check` → `BUILD_OK editor bundles manifests mirror (check)`
  and `MIRROR_CHECK_PASSED (up_to_date=327)`, exit 0.
- **Toolchain:** node 22.23.3; `@lhci/cli` installed in `node_modules/.bin`; Node Playwright 1.64.1 with
  chromium-1248. A repo `.venv/` exists with the pinned dev toolchain — pytest 9.1.1 + Python
  Playwright, and its Chromium launches (verified: 156.0.8078.4). **Run every Python test and browser
  tool through `.venv/bin/python`.** System `python3` has pytest 7.4.4 but no `playwright`, and
  `tests/conftest.py` excludes the browser modules there (naming them) — never report that run as
  the full suite.
- **Missing local evidence:** `artifacts/` exists but is a stale dump from an older pass.
  `artifacts/ui-audit/fixes/STATE.md`, `artifacts/ui-refinement/**`, `artifacts/next-work/**` and
  **`artifacts/canvas-motion/baseline/**` are not on this machine** (git-ignored; they stayed on the
  old Windows box). Reconstruct the state file in Stage 0. Never fabricate prior evidence. A gate
  whose frozen baseline is missing is **NOT RUN**, not "passed".
- **Windows-only helpers are not usable here:** `tools/_pin-renderer.ps1` is PowerShell, and
  `F:\Project\eInvite\_canva-verify\run-with-server.py` does not exist on this machine. Use the
  portable equivalents: `tests/canvas_motion_playwright.py` (starts its own app server),
  `tests/v14_test_utils.app_server`, and `tools/serve-gzip.py --port 8124`.

## 1. Read before you touch anything

1. `AGENTS.md` — protocol, skill locations, Freebuff has no subagent dispatch (do the work yourself).
2. `NEXT-WORK-TASK.md` — the authoritative work order (phases 0–7, tasks `NW-*`, owner gates `OD-*`).
   Read it end to end.
3. `docs/a11y/WCAG-2.2-AA-AUDIT.md` §5 (line 291) — the six code asks, currently unstarted.
4. `FREEBUFF-UI-REFINEMENT-PROMPT.md` — what the 2026-10-21 visual pass did. Do not re-run the
   research, do not re-implement the rose accent / paper-mat / one-row template filter.
5. `RILL-WALKTHROUGH.md` — the manual end-to-end acceptance flow you will run at the end.
6. `CONTRIBUTING.md` — generated-file and build rules; `docs/reviews/` — status ledgers.
7. `CANVA-UI-TASK.md`, `DESIGN-FIX-REPORT.md`, `UI-VISUAL-AUDIT-FIX-TASK.md` §0/§2 — context and the
   documented heuristic false positives.

Load the matching skills before planning (they live in `~/.agents/skills/<name>/SKILL.md` and
`.agents/skills/<name>/SKILL.md`): `frontend-design`, `web-design-guidelines`, `playwright-expert`,
`webapp-testing`, `visual-regression`, `horizontal-scroll`, `text-expansion`, `flexbox-patterns`,
`test-driven-development`, `verification-before-completion`. State in the report which ones changed a
decision.

**Verify, do not trust the documents.** The tree was renamed "version-free" after parts of the
audits were written. Three drifts confirmed at HEAD:

- `#accessPassword` is at `src/html/index.html:420`, not `:394`.
- The 10×10 canvas resize handle already has a `::before { inset: -18px }` hit-area expansion at
  `src/css/typography-system.css:2` (≈46×46 target). Measure the real interactive region before
  "fixing" NW-1.5; the audit predates the expansion. If it already meets 24×24, record the
  measurement and close the task as already satisfied — do not change the visual size.
- Page reorder already ships *Move to first page* / *Move to last page*
  (`src/js/page-experience.js:387,404-405`). NW-1.2 needs *Move earlier* / *Move later*, not a
  from-scratch reorder UI.

Report any other drift instead of silently following a stale line number.

## 2. Scope and session goal

**Minimum acceptable for this session:** Stage 0 + Stage 1 + Stage 2 closed with evidence.
If time is short, finish Stage 1 completely before starting Stage 2; a closed stage beats two
half-stages. **Stretch:** Stage 3. **Only if everything above is green:** Stage 4 and Stage 5 recon.
Never start Stage 5's deletions or parity implementation — those are owner-gated.

1. **Stage 0 — baseline reconfirmation** (`NW-0.1`–`NW-0.4`).
2. **Stage 1 — WCAG 2.2 AA six code asks** (`NW-1.1`–`NW-1.6`).
3. **Stage 2 — i18n completion** (`NW-4.1`–`NW-4.4`).
4. **Stage 3 — test/CI durability** (`NW-5.1`–`NW-5.4`), including a portable gate runner.
5. **Stage 4 — remaining UI regression sweep** (`NW-6.3`–`NW-6.6`); `NW-6.1/6.2` are closed,
   re-run only to prove no regression.
6. **Stage 5 — owner-gated recon only:** `NW-2.1` CSS `!important` inventory and `NW-3.1` dashboard
   gap matrix. No deletions, no parity code, until `OD-1`/`OD-2` are answered.
7. **Stage 6 — documentation and release readiness** (`NW-7.1`–`NW-7.4`).

Do **not**: redesign the UI, rebuild the dashboard, add features, touch canvas rendering,
re-translate the 391 rows already done, reopen the visual-baseline threshold question, or act on the
older `plans/001–003` (already done/blocked and out of scope).

## 3. Hard rules (non-negotiable)

- **Frozen, never edit:** `artifacts/canvas-motion/**`, `docs/CANVAS-SMOOTHNESS-BRIEF.md`,
  `tests/canvas_motion_playwright.py`, `tools/canvas-motion-*.{mjs,py}`, and any canvas
  threshold/baseline.
- **Never weaken gates, tests, thresholds or budgets:** `tools/lighthouserc.js` and
  `docs/perf/lighthouse-budgets.json` are read-only. No skipped tests, loosened assertions, blanket
  suppressions, or re-snapshotted baselines.
- **Never run `git clean -fdx`.** Never delete anything under `artifacts/`. Never revert untracked
  work or the `wip/*` branch.
- **After every `src/` JS/CSS/HTML edit:** `python3 build.py all` (must print `BUILD_OK` +
  `MIRROR_CHECK_PASSED`), then `python3 build.py bundles --check`
  (`ROUTE_BUNDLE_CHECK_PASSED`). Confirm the served mirror actually refreshed.
- **Bilingual:** every new user-visible string gets `.i18n-en` + `.i18n-km` (or the
  `EInviteI18n.langText` / `_txt` helper). Khmer line-height ≥ 1.6. Run
  `python3 scripts/check-bilingual-consistency.py  # stdlib only` after adding strings.
- **No new dependencies, no new `!important`, no bundlers, no new `innerHTML` in editor JS.** Keep the
  cascade contract `@layer reset, tokens, base, layout, components, utilities, overrides`.
- **One heavy browser at a time.** No source edits while a capture or gate is running.
- **Never stage/commit** `src/python/data/`, `data/`, `.claude/`, `artifacts/`, `deploy/sites/`.
  **Do not push, tag, or update `VERSION_HISTORY.md`** — that is `OD-3`.
- Minimal targeted edits. No drive-by refactors, renames or file moves.

## 4. Owner gates (ask, do not guess)

All six are open at the start. Record every answer in `artifacts/next-work/DECISIONS.md` with date,
decision, and the tasks it unblocks. Until an answer exists, do only the read-only recon named here.

| ID | Decision | Recommendation | Allowed before an answer |
|---|---|---|---|
| **OD-1** | Scope of the `!important` / layered-CSS cleanup | Staged, pixel-diff-gated cleanup of 25–40 % of occurrences; dead and superseded rules first; stop at the first unexplained visual diff | `NW-2.1` inventory only |
| **OD-2** | Dashboard feature parity (sheets/polls panels, edit history, poster create dialog) | Entry points only; edit history if cheap; no panel re-implementation | `NW-3.1` gap matrix only |
| **OD-3** | Push / release / version history | Hold; produce `RELEASE-CANDIDATE.md`, do not push | Everything except push/tag |
| **OD-4** | Equivalent exception for the resize handle if enlarging it is layout-risky | Prefer the measured fix; ask only if risky | `NW-1.5` measurement |
| **OD-5** | Khmer `<option>` implementation | Runtime label rewrite via `data-i18n-en`/`data-i18n-km`; no custom listbox | `NW-4.1` |
| **OD-6** | Any budget/threshold change | Never propose one | — |

If a task cannot proceed without an answer, write the question in your report under
**"Owner decisions needed"** with a recommendation, and continue with the next unblocked task.

## 5. Execution plan

### Stage 0 — baseline reconfirmation (`NW-0.1`–`NW-0.4`)

1. Record, verbatim:

   ```bash
   cd /media/ngethsereyboth/LocalDisk/eInvite/einvite-platform
   git log --oneline -8
   git status --short --branch
   git rev-parse HEAD
   python3 build.py all --check          # BUILD_OK + MIRROR_CHECK_PASSED
   python3 build.py bundles --check      # ROUTE_BUNDLE_CHECK_PASSED
   .venv/bin/python -m pytest tests/ -q  # full suite incl. browser modules; record the exact count
   ```

2. Confirm the browser toolchain (it is already installed; repair only if this fails):

   ```bash
   .venv/bin/python -c "import pytest, playwright; print(pytest.__version__)"
   .venv/bin/python -m pip install -r requirements-dev.txt   # only if the import fails
   ```

3. Static server + smoke, one at a time:

   ```bash
   python3 tools/serve-gzip.py --port 8124 &
   SERVE_PID=$!
   node tools/page-errors.mjs --all      # expect TOTAL pages=16 consoleErrors=0 non2xx=0
   kill $SERVE_PID
   ```

4. Lighthouse (gzip server on 8124): `npx lhci collect --config=tools/lighthouserc.js`, then
   `npx lhci assert --config=tools/lighthouserc.js`. Record exit codes and the a11y score (must be 1.00).

5. Canvas acceptance:
   `.venv/bin/python tests/canvas_motion_playwright.py --phase all --output artifacts/canvas-motion/verify/acceptance-next-work`
   → expect 22 pass / 0 fail / 2 skipped.
   **Canvas visual:** `NOT RUN — frozen baseline absent on this machine`. Do not regenerate or
   re-anchor it; ask the owner to copy `artifacts/canvas-motion/baseline/` from the Windows machine if
   the gate is required.
   **Canvas perf:** needs the real dev server. Start one with a throwaway data dir:

   ```bash
   EINVITE_DATA_DIR=$(mktemp -d /tmp/opencode/einvite-data.XXXXXX) EINVITE_DEV_AUTH_TOKENS=1 EINVITE_ALLOW_NO_SCANNER=1 \
   PYTHONPATH=src/python:. python3 src/python/server.py --port 8124 &
   ```

   then `BASE_URL=http://127.0.0.1:8124 node tools/canvas-motion-perf.mjs --phase=P1 --output=artifacts/canvas-motion/verify/perf-next-work`.
   If the harness needs a wrapper, write it under `tools/`, say so, and never report a gate you did not run.

6. Write:
   - `artifacts/ui-audit/fixes/STATE.md` — reconstructed (Done / Active / Next Move, HEAD, tree state,
     hard rules, gate procedure, evidence map). Say explicitly that it was reconstructed on this machine.
   - `artifacts/next-work/00-baseline/STATE-SNAPSHOT.md` — exact command output, not paraphrase.
   - `artifacts/next-work/00-baseline/OPEN-ITEMS.md` — every `NW-*`/`OD-*` item exactly once, plus the
     six WCAG rows, the i18n rows, and the three residual owner decision rows.
   - `artifacts/next-work/00-baseline/gates/SUMMARY.md` — one line per gate: command, exit code, key
     output line, timestamp, or `NOT RUN` + reason.

**Stop condition:** any baseline gate red before you changed anything → stop and report with the log
path. Do not start Stage 1 on a red baseline.

### Stage 1 — WCAG 2.2 AA six asks (`NW-1.1`–`NW-1.6`)

- **NW-1.1 (2.4.11).** Build `tools/a11y-focus-obscured.py`: for each focused control in `index.html`
  (rail, toolbars, inspector tabs, `#saveState`, canvas controls) at 1440×900, 1024×768, 768×1024 and
  375×667, Tab-scroll it into view and test whether a sticky/fixed ancestor fully covers it
  (`elementFromPoint` at top/center/bottom of the box). Record `before/focus.json` + screenshots.
  Fix in the actual scroll container with `scroll-padding-top`/`-bottom` (not a blanket
  `scroll-margin`), in the correct layer; document the sticky band heights in a comment. Re-run and
  record `after/focus.json`. Acceptance: zero "fully obscured" rows at all four widths.
- **NW-1.2 (2.5.7).** Add *Move earlier* / *Move later* to the page context menu, reusing
  `reorderPage`; disable at the ends; bilingual labels; stable IDs. Keyboard test: menu opened by
  keyboard, move, order changed, focus stays on the moved page; pointer drag unchanged.
- **NW-1.3 (3.3.7).** Add `autocomplete="name"` / `autocomplete="email"` to the dynamically built
  signup-sheet and poll forms (`src/js/signup-sheets.js:130-131`, `src/js/polls.js:109-110`). Verify
  the attributes survive the JS-built DOM. Skip cross-form prefill if it would add storage; say why.
- **NW-1.4 (3.3.8).** Add `autocomplete="current-password"` to `#accessPassword`
  (`src/html/index.html:420`); verify the password-manager affordance does not break editor boot or
  the access dialog.
- **NW-1.5 (2.5.8).** Measure the real hit box of the canvas resize handle at 1440/1024/768/375. The
  `::before { inset:-18px }` expansion may already satisfy ≥24×24; if so, record the numbers and close
  the task as already satisfied. If not, enlarge the hit area only (pseudo-element/transparent
  padding), keep the visual 10×10, and prove no click stealing from selection/rotate controls.
- **NW-1.6.** Correct `docs/a11y/WCAG-AA-AUDIT.md` to cite **2.5.8** for the AA target-size claim
  (2.5.5 is AAA), cross-link §5 of `WCAG-2.2-AA-AUDIT.md`, keep it dated and explicit.

**Phase gate:** all six closed or one written exception; `build.py all`, `bundles --check`, smoke
16/16/0, LHCI assert exit 0 with a11y 1.00; bilingual checker exit 0; before/after evidence under
`artifacts/next-work/nw-1-*/`; one reviewable commit.

### Stage 2 — i18n completion (`NW-4.1`–`NW-4.4`)

- **NW-4.1.** Locate the generated `<option>` selects (materials, responses; search
  `rg -n "<option|new Option" src/js src/html`). Add `data-i18n-en` / `data-i18n-km` to each option and
  an `EInviteI18n.applyOptionLabels(root)` helper that rewrites `option.textContent` on init and on
  language change; call it where the page applies `.i18n-*` spans. No spans inside `<option>`, no
  duplicated text. Test EN→KM→EN: text changes exactly once, selection survives.
- **NW-4.2.** Add the `langText`/`_txt`/`{en, km}` plumbing to `src/js/pages/admin/feature-flags.js`
  (11 strings); keep flag keys and API names in English; KM admin shows Khmer without overflow at 375.
- **NW-4.3.** Reconcile `docs/i18n/TRANSLATIONS.csv` with the tree using the existing reconcile
  script (`artifacts/i18n-km/reconcile_csv.py`). If that script is not on this machine, reconstruct
  its logic, say so in `NOTES.md`, and never mark an unverified row as translated. Classify every
  stale row (`removed-from-tree`, `text-changed`, `moved-to-js`), archive or remove with a dated note,
  and update the totals in `artifacts/i18n-km/REPORT.md`.
- **NW-4.4.** Khmer visual verification at 1440/768/375 on `index`, `dashboard`, `guests`, `templates`,
  `materials`, `responses`, `admin` (light/dark where relevant): no clipping, no horizontal scroll,
  line-height ≥ 1.6, no mixed EN/KM duplication, option labels readable. Shots under
  `artifacts/next-work/nw-4-4/`.

**Phase gate:** 12 option labels + 11 feature-flag strings localized; checker exit 0; Khmer tests pass;
build + bundles green; CSV totals match the tree.

### Stage 3 — test/CI durability (`NW-5.1`–`NW-5.4`)

- **NW-5.1.** Reproduce `.venv/bin/python -m pytest tests/v27_3_5_release_evidence_test.py -q` under
  default capture (expect fail) and with `-s` (expect pass). Fix at the harness boundary — explicit
  stdout/stderr files or `subprocess.run(..., capture_output=True)` — never by changing the pinned
  digest or the assertion. Verify both invocations and then the full suite with default capture.
- **NW-5.2.** Reproduce `analytics_ingestion_test::test_phase4_rate_limit` order dependence in a full
  run; reset the limiter per test or use a unique client identity. Do not raise the production limit,
  do not skip. Three consecutive full-suite runs must pass.
- **NW-5.3.** Write `tools/run-gates.py` (Linux; `argparse`, not PowerShell):
  `--phase all|build|smoke|pytest|lhci|canvas`, `--skip-heavy`, `--port 8124`. It pins nothing (no
  renderer pin on Linux), starts `tools/serve-gzip.py` or the dev server as each gate needs it, always
  stops it in `finally`, holds a lock file so two heavy runs never overlap, logs every command + exit
  code + key line under `artifacts/next-work/gates/<timestamp>/`, and stops the chain at the first
  failure.
- **NW-5.4.** Document the runner in `tools/README.md`, `CONTRIBUTING.md`, and the reconstructed
  `STATE.md` (including the `.venv` and `PYTHONIOENCODING` requirements).

**Phase gate:** full pytest passes with default capture, twice; `run-gates` exits 0 end-to-end; no
skipped/weakened tests; no gate config edits.

### Stage 4 — remaining UI regression sweep (`NW-6.3`–`NW-6.6`)

- **NW-6.3.** Verify the `Timeline` pill, zoom cluster, selection toolbar and context toolbar at
  1440/1024/768/375 for overlap with each other and the canvas. Fix only reproducible overlaps; anchor
  the pill to the statusbar track if it still floats; before/after screenshots per width.
- **NW-6.4.** Motion contract: transitions stay `transform`/`opacity` (plus cheap paint properties);
  `prefers-reduced-motion` kills tweens/stagger on every animating page; the pinned
  `--motion-*`/`--spring`/`--smooth` values are unchanged. One editor perf trace at 1440 and 375.
- **NW-6.5.** Contrast sweep on 16 pages, light/dark, compared with the documented baseline. Do not
  chase the five documented false-positive classes; fix a genuine <4.5:1 body row with a token, not a
  one-off.
- **NW-6.6.** Measure `privacy.html` route weight and its headroom; either take the shared layer
  safely or document why it stays excluded. Do not change budgets.

Capture with the portable server recipe (real dev server, throwaway data dir):

```bash
EINVITE_DATA_DIR=$(mktemp -d /tmp/opencode/einvite-data.XXXXXX) EINVITE_DEV_AUTH_TOKENS=1 EINVITE_ALLOW_NO_SCANNER=1 \
PYTHONPATH=src/python:. .venv/bin/python src/python/server.py --port 8124 &
.venv/bin/python tools/ui-audit-capture.py --base http://127.0.0.1:8124 --out artifacts/next-work/nw-6-3/after
.venv/bin/python tools/ui-audit-digest.py --dir artifacts/next-work/nw-6-3/after --out artifacts/next-work/nw-6-3/after-digest.txt
.venv/bin/python tools/ui-audit-summary.py --section hscroll|overflow|contrast|occlusion|tiny|errors
```

A fresh full sweep to prove no regression is `NW-6.1` (already closed): re-run it and compare, but do
not redo the visual direction.

### Stage 5 — owner-gated recon only (`NW-2.1`, `NW-3.1`)

- **NW-2.1.** Write `tools/css-important-inventory.py` (read-only): count `!important` per file, layer,
  selector and property; classify `dead` / `superseded` / `override-needed` / `unknown`; reproduce the
  audit's counts and explain the delta; propose a staged target for `OD-1`. **Delete nothing.**
- **NW-3.1.** Produce `artifacts/next-work/nw-3-1/gap-matrix.md` from
  `docs/reviews/dashboard-feature-inventory-2026-10-16.md` and the current `dashboard.html` /
  `dashboard.js`: feature → old surface → current surface → impact → cost → risk; mark each
  `restore` / `entry-point-only` / `document-as-absent`. **Write no parity code.**

### Stage 6 — documentation and release readiness (`NW-7.1`–`NW-7.4`)

- Keep the reconstructed `STATE.md` current after every stage.
- Create `docs/STATUS-INDEX.md`: one table marking every root work order / ledger / a11y audit as
  `authoritative` / `historical` / `superseded`, with date and one-line verdict; add status banners to
  superseded reports.
- Write `RELEASE-CANDIDATE.md`: HEAD, commits included, gates with numbers and evidence paths,
  remaining owner decisions, known limitations, and the push instruction blocked on `OD-3`.
- Write `artifacts/next-work/HANDOFF.md` and the final `STATE.md` session summary: what changed, what
  was verified, what remains, the exact next command.
- Do **not** push, tag, or edit `VERSION_HISTORY.md`.

## 6. Verification before you claim anything

Run and record each; a claim without command + exit code + evidence path is not a result.

```bash
python3 build.py all
python3 build.py bundles --check
.venv/bin/python -m pytest tests/ -q        # twice; record exact count
node tools/page-errors.mjs --all            # 16 pages, 0 console errors, 0 non-2xx
npx lhci collect --config=tools/lighthouserc.js
npx lhci assert --config=tools/lighthouserc.js
.venv/bin/python tests/canvas_motion_playwright.py --phase all --output artifacts/canvas-motion/verify/acceptance-next-work
python3 scripts/check-bilingual-consistency.py  # stdlib only
```

Plus, for every UI change: capture before/after at the same viewport/state; 0 horizontal document
scroll at 320/375; no clipped or overlapping text; KM and dark mode checked; reduced motion checked.
Finish with the `RILL-WALKTHROUGH.md` flow (or a scripted equivalent) on a throwaway account: sign in →
build a bilingual invitation → publish → RSVP on the public page → response recorded. Record the
evidence path. Never use real names, emails or events.

**Canvas visual gate:** `NOT RUN` unless the owner supplies the frozen baseline. Say so; do not
substitute a fresh baseline.

## 7. Evidence and commit protocol

- For each `NW-x.y`: `artifacts/next-work/nw-x-y/{NOTES.md,before/,after/,logs/}`. `NOTES.md` holds
  goal, commands, exit codes, decisions and links. Screenshot names:
  `<page>-<state>-<viewport>-<theme>-<lang>.png`. Never hand-edit heuristic JSON. Never commit
  `artifacts/`.
- Work on a new branch `pass/2026-10-21-next-work` from `50721ef` unless the owner says otherwise.
- One commit per stage, clear message (`fix(a11y): …`, `feat(i18n): …`, `test(ci): …`), including the
  refreshed `src/python/` mirror produced by `build.py all`. Never stage the untracked paths listed in
  §0. Do not push.
- If the owner asks you to use the current branch, do that instead and say so.

## 8. Report format (final message)

1. **Done:** task ID → one-line change → files touched → command + observed result.
2. **Verified:** gate table with exact commands, exit codes and key output lines.
3. **Not run / not verified:** what and why (e.g. canvas visual baseline absent).
4. **Drift found:** every stale file:line or claim from the work order, with the corrected fact.
5. **Owner decisions needed:** `OD-n` with evidence and recommendation.
6. **New issues found** beyond the work order (screenshot paths), fixed or listed.
7. **Commits:** branch, commit hashes, what each contains.
8. **Next command** for the next agent.

## 9. Definition of done (this continuation)

- Stage 0 snapshot, open-items ledger and gate summary exist and match reality.
- All six WCAG asks closed (or one owner-approved exception) and evidenced; LHCI a11y 1.00.
- The 12 option labels and 11 feature-flag strings localized; CSV reconciles; Khmer visual pass clean.
- Full pytest passes twice with default capture; `tools/run-gates.py` exits 0 end-to-end.
- No gate weakened; no frozen file, budget, threshold or baseline edited; nothing pushed.
- `STATE.md`, `NEXT-WORK-TASK.md`, `docs/STATUS-INDEX.md` and `RELEASE-CANDIDATE.md` agree on HEAD,
  gates and open items; a fresh agent can resume from markdown alone.

## 10. Stop conditions

Stop and report (do not improvise) when:

- a baseline gate is red before you changed anything;
- a change makes a frozen gate fail and the cause is not obviously yours;
- a batch produces more than two unexplained visual rows;
- a task needs a frozen file, threshold, budget, baseline, or an unanswered `OD-n`;
- two heavy browser runs would overlap;
- a test only passes with `-s`, a retry or a wider timeout after your change — that is a harness bug,
  not a pass;
- the working tree contains changes you did not make (they are the owner's — investigate, never
  revert).

Escalation format: task ID, command, exit code, expected vs actual, log path, smallest proposed next
step. Never attach a fix you have not verified.
