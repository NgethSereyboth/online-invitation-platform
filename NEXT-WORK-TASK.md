# eInvite — Next Work Order: Improvement, Refinement & Hardening

**Repo:** `F:\Project\eInvite\online-invitation-platform` (Windows / PowerShell)
**Written:** 2026-10-20
**Status:** proposed work order — owner-approval gates are marked `OD-n`; do not start a gated task before the owner answers.
**Baseline HEAD:** `1f28cbc` (`main`, ahead 8 of `origin/main`, not pushed; working tree clean except untracked `src/python/data/`). **Updated:** 2026-10-21 after the ui-refinement pass (`1cd09d2`) and the harness commit (`1f28cbc`).
**Predecessor state:** `artifacts/ui-audit/fixes/STATE.md` (read it first, then this file).

> **For the next agent — read this before touching anything.**
> 1. Read `artifacts/ui-audit/fixes/STATE.md` in full. It carries the hard rules, the current gate
>    procedure, and the evidence map. This file assumes you have read it. If it is absent on this
>    machine (`artifacts/` is git-ignored), reconstruct the baseline via Phase 0 and write
>    `artifacts/next-work/00-baseline/STATE-SNAPSHOT.md` before editing.
> 2. Read this file end-to-end. Start at **Phase 0**; do not jump to a later phase because it looks
>    more interesting. Each task ends with a verification step and an evidence path.
> 3. Tick the `- [ ]` boxes as you finish steps. Never tick a box you did not verify with a command
>    you actually ran in this session.
> 4. Keep `artifacts/ui-audit/fixes/STATE.md` current at the end of every work session (Done /
>    Active / Next Move), and point it at this file.
> 5. If a gate is red and the cause is not yours, stop and report. Do not "fix" a gate by relaxing
>    it. Do not edit frozen canvas files, thresholds, budgets, or baselines.

---

## 0. Executive summary

The UI/canvas rebuild programme is closed: design-page fix, pass 2 (U1/U2), canvas-motion fix,
Canva-UI pass, owner-decision batch, regression fix, and the visual-baseline re-anchor are all
committed and gate-verified. What remains is **not a redesign**. It is a bounded set of
improvements that were explicitly deferred, plus the durability work needed to stop paying for the
same environment problems on every run:

1. **Accessibility:** six WCAG 2.2 AA code changes that the audit recorded but nobody started.
2. **CSS architecture:** the deferred `!important` / layered-override cleanup (the largest source of
   future visual regressions).
3. **Product parity:** decide and implement what the rebuilt dashboard should expose (sheets/polls
   entry points, edit-history, poster create path), or document the omission as intentional.
4. **i18n completion:** the 59 structured fallback rows (`<option>` labels and the feature-flags
   module) and the 59 stale CSV rows left by the Khmer pass.
5. **Test/CI durability:** the two pytest harness artifacts (child-process std handles; order-
   sensitive rate limiter) and a single serialized gate runner that starts and stops its own server.
6. **UI refinement:** a fresh capture sweep to prove nothing regressed, plus a small number of
   deterministic-capture and floating-control refinements.
7. **Documentation truth:** an authoritative status index, checked DoD boxes, and a release
   candidate handoff.

Success is a repository where one command reproduces every gate, every open item has either a
closed task or a written owner decision, and the next agent can resume from markdown alone.

---

## 1. Verified starting state (do not re-litigate)

| Item | State | Evidence |
|---|---|---|
| Canva-UI pass (16 pages, dashboard rebuild) | closed, committed `37bfc8d` | `CANVA-UI-TASK.md` (all boxes ticked), `artifacts/ui-audit/fixes/canva-ui/RESULTS.md` |
| Owner-decision batch (poster panel cleanup, custom units, build output root) | closed, committed `508f95a` | `artifacts/ui-audit/fixes/RESULTS.md` §Task I |
| Editor boot regression (`runPosterTreatments` ReferenceError) | fixed, committed `8b014e2` | `STATE.md` §Active/next, item 3 |
| Loopback registration cap / one-command visual gate | fixed, committed `af2b723` | `tests/auth_register_rate_limit_test.py`, `artifacts/canvas-motion/verify/visual-full/` |
| UI-refinement visual pass (rose accent, paper-mat, one-row template filters) | closed, committed `1cd09d2` | `artifacts/ui-refinement/REPORT.md`, 240-shot sweeps, LHCI 16/16, canvas visual 6/6 max 0.57 % |
| Capture determinism + std-handle hardening | committed `1f28cbc` | `tests/browser_runtime.py`, `tools/ui-audit-capture.py`, `artifacts/next-work/nw-6-2/NOTES.md` |
| Design-fix pass (poster, sizes, canvas visibility, designer error) | closed, committed `708e675` | `DESIGN-FIX-REPORT.md`, `artifacts/design-fix/` |
| Pass 2 U1 design page / U2 app pages | closed, committed `6449fcc` / `ab81ead` | `artifacts/ui-audit/fixes/RESULTS.md` §Pass 2 |
| Canvas motion fix pass | accepted, committed `d9818a6` | `artifacts/canvas-motion/ledger.md` "Fix pass r11" |
| Visual baseline re-anchor | owner-approved 2026-10-20 | `artifacts/canvas-motion/baseline/REBASELINE-2026-10-20.md` |
| Khmer translation pass | applied (391 rows), CSV reconciled | `artifacts/i18n-km/REPORT.md` |
| Full pytest | 143 passed / 0 failed (clean run; the default-capture std-handle caveat for `v27_3_5_release_evidence_test` is still open) | `STATE.md` §Baseline, `artifacts/ui-refinement/` |
| Smoke / LHCI | 16/16 pages, 0 console, 0 non-2xx; LHCI 16/16, a11y 1.00 | `canva-ui/RESULTS.md`, `STATE.md` |
| Canvas gates | acceptance 22/0/2; perf exit 0 `failures:[]`; visual 6/6, max 0.57 % (`1cd09d2`) | `artifacts/canvas-motion/verify/`, `artifacts/ui-refinement/verify/visual/` |

**Do not redo:** any of the rows above unless a fresh gate run proves a regression. In particular,
do not re-open the visual-gate threshold question (the owner re-anchored the baseline and kept
3.5 %), do not "clean up" the canvas modules, and do not re-translate the 391 rows that are already
translated. The `1cd09d2` visual pass already unified the rose accent, added the paper-mat tokens,
and made the Template Studio filter band one row — build on it, do not re-run that direction.

**Known false positives (do not chase):** billing gradient contrast rows, admin mock-403 console
rows, `designer.html` CSP `unsafe-eval` baseline pageerror, sticky-header occlusion rows from
scrolled rescans, icon-only buttons reported as tiny text, and `color(srgb …)` / `color-mix`
translucent surfaces read as low contrast. These are documented in `RESULTS.md` §Still open and
`STATE.md` §Gotchas.

---

## 2. Non-negotiable constraints (copy of the project hard rules)

These apply to every task in this file. A task that violates one is failed even if its tests pass.

- **Frozen canvas files — never edit:** `artifacts/canvas-motion/**`, `docs/CANVAS-SMOOTHNESS-BRIEF.md`,
  `tests/canvas_motion_playwright.py`, `tools/canvas-motion-*.{mjs,py}`, and the canvas gate
  thresholds/baselines.
- **Never weaken gates, tests, thresholds, or budgets:** `tools/lighthouserc.js` and
  `docs/perf/lighthouse-budgets.json` are read-only. Do not skip tests, loosen assertions, add
  blanket suppressions, or change snapshots to make a gate pass.
- **Never run `git clean -fdx`.** Never delete anything under `artifacts/`.
- **One heavy Chrome at a time.** Restart `tools/_pin-renderer.ps1` before gate/capture runs.
  No source edits while a gate or capture run is in flight.
- **After any `src/` JS/CSS/HTML edit:** run `python3 build.py all` (must print `BUILD_OK` +
  `MIRROR_CHECK_PASSED`), then `python3 build.py bundles --check`
  (`ROUTE_BUNDLE_CHECK_PASSED`). Confirm the served mirror actually refreshed; a build that exits 0
  with a stale mirror is a failure (see the historical wrinkle in `STATE.md`, now fixed at cause).
- **`PYTHONIOENCODING=utf-8`** for Python runs. Write Python scripts to files; PowerShell mangles
  inline quoting. Use absolute paths under `F:\Project\eInvite\...` when a tool silently no-ops on
  relative paths (documented in `artifacts/i18n-km/REPORT.md`).
- **No new `!important`**, no new `innerHTML` in editor JS, no new external dependencies, no npm
  bundlers. Vanilla JS/CSS and the generated bundle pipeline only.
- **Bilingual:** every new user-visible string gets `.i18n-en` + `.i18n-km` (or the
  `EInviteI18n.langText`/`_txt` helper in JS). Khmer line-height ≥ 1.6. Run
  `scripts/check-bilingual-consistency.py` after adding strings.
- **Do not stage `src/python/data/`** (runtime data). Do not commit before verifying. Do not push
  without `OD-3`.
- **Minimal, targeted edits.** No drive-by refactors, no file moves, no renames outside the task's
  stated files. If a task needs a wider change, stop and write it up as a new work order.

---

## 3. Owner decision gates (blocking)

| ID | Decision | Why it blocks | Recommendation |
|---|---|---|---|
| **OD-1** | Scope/target for `!important` and layered-CSS cleanup (Phase 2) | Removing override rules without an agreed risk envelope can regress 16 pages; the audit explicitly deferred this | Approve a **staged, pixel-diff-gated** cleanup targeting **25–40 % of occurrences**, dead rules and superseded declarations first; stop at the first unexplained visual diff |
| **OD-2** | Dashboard feature parity (Phase 3): restore sheets/polls panels, edit-history, poster create dialog, or document them as intentionally absent | The rebuild deliberately restored only auth + design grid + create; the inventory doc lists features that used to live there | Produce the gap matrix first, then approve a subset. Recommend: entry points only (links to guests/event sections), edit-history if cheap, no panel re-implementation |
| **OD-3** | Release / push / version-history update | `main` is 6 commits ahead; the owner has kept everything local so far | Hold until Phase 7 produces a release candidate; push only on explicit approval |
| **OD-4** | Accept an "Equivalent" exception for the 10×10 canvas resize handle if enlarging the hit area disturbs the canvas layout | WCAG 2.5.8 permits an equivalent-exception with evidence | Prefer the fix (≥24×24 hit area); ask only if the fix proves layout-risky |
| **OD-5** | Khmer `<option>` implementation: runtime label rewrite vs a custom listbox | `<option>` cannot hold spans; a custom listbox is more work and changes interaction | Recommend runtime rewrite via `data-i18n-en`/`data-i18n-km` + a language-change hook; no custom listbox |
| **OD-6** | Any proposed budget/threshold change | Forbidden by the project rules | Never propose one; reduce weight or accept the documented headroom instead |

Record every answer in `artifacts/next-work/DECISIONS.md` with date, decision, and the tasks it
unblocks.

---

## 4. Workstream map and execution order

| Phase | Workstream | Tasks | Depends on | Gate |
|---|---|---|---|---|
| 0 | Baseline reconfirmation | NW-0.1 … NW-0.4 | — | all baseline numbers reproduced |
| 1 | WCAG 2.2 AA delta | NW-1.1 … NW-1.6 | Phase 0 | build + smoke + LHCI + targeted a11y |
| 2 | CSS architecture cleanup | NW-2.1 … NW-2.5 | **OD-1**, Phase 1 (tests exist) | pixel-diff + v55 + bundles |
| 3 | Dashboard/editor parity | NW-3.1 … NW-3.5 | **OD-2**, Phase 0 | smoke + LHCI + 0 console |
| 4 | i18n completion | NW-4.1 … NW-4.4 | Phase 0 | checker + khmer tests + build |
| 5 | Test/CI durability | NW-5.1 … NW-5.4 | Phase 0 | full pytest twice + runner exit 0 |
| 6 | UI refinement & regression sweep | NW-6.1 … NW-6.6 | Phases 1–5 | capture digest + LHCI + 0 hscroll |
| 7 | Documentation & release readiness | NW-7.1 … NW-7.4 | all | docs consistent + release candidate |

**Parallelisation rule:** read-only recon (NW-0.x, NW-2.1, NW-3.1, NW-5.1/5.2 reproduction) may run
in parallel. **Edits to `src/` are serialized** unless the file sets are provably disjoint. **Heavy
Chrome runs are always serialized** — one renderer, one gate at a time.

Suggested waves:

- **Wave A (no owner gate):** NW-0.1 → NW-0.4, then NW-1.6, NW-3.1, NW-4.3 analysis, NW-5.1/5.2
  reproduction.
- **Wave B:** NW-1.1 … NW-1.5, NW-4.1/4.2, NW-5.3/5.4.
- **Wave C:** NW-2.x (after OD-1), NW-3.2 … NW-3.4 (after OD-2).
- **Wave D:** NW-6.1 … NW-6.6, then NW-7.1 … NW-7.4.

---

## 5. Phase 0 — Baseline reconfirmation

**Goal:** prove the repository is where this document says it is before changing anything, and
produce the open-items ledger the rest of the work references.

### NW-0.1 — Confirm HEAD, tree, and state file

**Files:** read-only; write `artifacts/next-work/00-baseline/STATE-SNAPSHOT.md`.

- [ ] Record `git log --oneline -8`, `git status --short --branch`, and `git rev-parse HEAD`.
- [ ] Confirm HEAD is `af2b723` (or a descendant), `main` is ahead of `origin/main` by 6, and the
      only untracked path is `src/python/data/`.
- [ ] Confirm `STATE.md` points at the correct HEAD. If it does not, fix the header **in this
      session** (Done/Active/Next too) and say so in the snapshot.
- [ ] Copy the current `STATE.md` Done/Active/Next sections into the snapshot so later phases can
      diff against them.

**Verify:** the snapshot contains the exact command output, not a paraphrase.
**Acceptance:** any mismatch between this file and the repo is written down and resolved before
NW-0.2.

### NW-0.2 — Run the full gate matrix once (baseline)

**Files:** no source edits. Logs under `artifacts/next-work/00-baseline/gates/`.

- [ ] Pin the renderer: `powershell -ExecutionPolicy Bypass -File tools\_pin-renderer.ps1`.
- [ ] Set `$env:CHROME_PATH = "$env:LOCALAPPDATA\ms-playwright\chromium-1228\chrome-win64\chrome.exe"`.
- [ ] `python3 build.py all` → expect `BUILD_OK` + `MIRROR_CHECK_PASSED`.
- [ ] `python3 build.py bundles --check` → expect `ROUTE_BUNDLE_CHECK_PASSED`.
- [ ] Start the static server on 8124 (`python3 tools/serve-gzip.py --port 8124`), run
      `node tools/page-errors.mjs --all`, expect `TOTAL pages=16 consoleErrors=0 non2xx=0`, then
      stop the server. Do not leave it running.
- [ ] `python3 -m pytest tests/ -q -s` → expect all pass. Do **not** assume a count: the last
      clean log records 141 passed / 0 failed, while `STATE.md` §Session detail records 143 tests at
      `af2b723` with two harness artifacts (fixed in Phase 5). Record the exact count and any
      failure verbatim.
- [ ] Canvas acceptance: `python3 tests\canvas_motion_playwright.py --phase all --output
      artifacts\canvas-motion\verify\acceptance-next-work` → expect 22 pass / 0 fail / 2 skipped.
- [ ] Canvas perf:
      `python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- node tools/canvas-motion-perf.mjs --phase=P1 --output=artifacts/canvas-motion/verify/perf-next-work`
      → expect exit 0, `failures: []`, no frame ≥ 50 ms.
- [ ] Canvas visual:
      `python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/canvas-motion-visual.py --base "{base}" --phase P1 --out artifacts/canvas-motion/verify/visual-next-work`
      → expect 6/6 pairs ≤ 3.5 % and `CANVAS_MOTION_VISUAL_PASSED`.
- [ ] LHCI: serve on 8124, `npx lhci collect --config=tools/lighthouserc.js`, then
      `npx lhci assert --config=tools/lighthouserc.js` → exit 0; 16 pages collected; a11y 1.00.
- [ ] Write `artifacts/next-work/00-baseline/gates/SUMMARY.md` with one line per gate: command,
      exit code, key output line, timestamp.

**Stop condition:** if any baseline gate is red, stop. Report the failure with the log path. Do not
start Phase 1 on a red baseline.

### NW-0.3 — Rebuild the open-items ledger

**Files:** create `artifacts/next-work/00-baseline/OPEN-ITEMS.md`.

- [ ] Copy every open item from this file into the ledger with its ID (`NW-*`, `OD-*`), source path,
      owner (agent/owner), and status (`open`, `blocked`, `done`).
- [ ] Add the six WCAG rows from `docs/a11y/WCAG-2.2-AA-AUDIT.md` §5 with exact file/line.
- [ ] Add the three remaining owner-decision rows from `RESULTS.md` §Still open.
- [ ] Add the i18n rows: 10 + 2 `<option>` labels, 11 `feature-flags.js` strings, 59 stale CSV
      rows, 59 fallback rows.
- [ ] Add the CSS counts measured in NW-2.1 once that task runs (link, don't duplicate).
- [ ] Add the dashboard inventory gaps from NW-3.1 once that task runs.

**Acceptance:** every item in this file appears exactly once in the ledger; no item is silently
dropped.

### NW-0.4 — Create the evidence tree

- [ ] Create `artifacts/next-work/<task-id>/` directories as tasks start, each with `before/`,
      `after/`, `logs/`, and `NOTES.md`.
- [ ] Put the command, timestamp, exit code, and evidence path in `NOTES.md` for every claim.
- [ ] Never commit `artifacts/` (git-ignored by design).

---

## 6. Phase 1 — WCAG 2.2 AA delta (six code asks)

**Source:** `docs/a11y/WCAG-2.2-AA-AUDIT.md` §5 "Findings requiring a code change". The audit says
explicitly: *"Nothing in this table has been started."* Close all six or record a justified
exception.

**Global verification for this phase:** `python3 build.py all` + `bundles --check` after every
`src/` edit; `node tools/page-errors.mjs --all`; `npx lhci assert` (a11y must stay 1.00);
`scripts/check-bilingual-consistency.py` if any string is added; focused screenshots in
`artifacts/next-work/nw-1-*/after/`.

### NW-1.1 — 2.4.11 Focus Not Obscured (Minimum)

**Problem:** the audit marks it "partial": the editor has two stacked sticky bands and no
per-scroll-container `scroll-padding` measurement.

**Files:**
- Create: `tools/a11y-focus-obscured.py` (measurement harness; Playwright, Python).
- Modify: `src/css/stabilized.css` (or the file the measurement proves is the correct scroll
  container).
- Test: the harness itself doubles as the regression test; add a pytest wrapper if the repo's
  convention expects one (`tests/a11y_focus_obscured_test.py`).

**Steps:**
- [ ] Write the harness: for each focused control in `index.html` (rail buttons, toolbar buttons,
      inspector tabs, `#saveState`, canvas controls) at 1440×900, 1024×768, 768×1024, 375×667:
      focus the element, scroll it into view via keyboard (Tab), then measure whether its bounding
      box is fully covered by a sticky/fixed ancestor using `elementFromPoint` at the box's
      center/top/bottom.
- [ ] Record the **before** matrix in `artifacts/next-work/nw-1-1/before/focus.json` and a
      screenshot per failing case.
- [ ] Decide the fix from the measurements: `scroll-padding-top`/`scroll-padding-bottom` on the
      actual scroll container, not a blanket `scroll-margin` on every element.
- [ ] Implement the smallest rule in the correct layer (`@layer utilities` or `overrides` per the
      cascade contract); document the sticky-band heights in a comment.
- [ ] Re-run the harness; every focused control must have at least one visible band (not fully
      obscured). Record the after matrix.
- [ ] Verify no new horizontal scroll at 320/375 and no change to `.stage-wrap` geometry.

**Acceptance:** zero "fully obscured" rows at all four widths; the harness is committed as a
repeatable test; before/after JSON + screenshots exist.

### NW-1.2 — 2.5.7 Dragging Movements

**Problem:** page reordering in `page-experience.js:387` is pointer-drag only.

**Files:**
- Modify: `src/js/page-experience.js` (the page context menu around line 387).
- Test: `tests/page_reorder_keyboard_test.py` or a Playwright check in `tools/`.

**Steps:**
- [ ] Locate the existing `reorderPage` helper and the page context-menu builder; reuse the helper,
      do not duplicate the reorder logic.
- [ ] Add **Move earlier** and **Move later** actions to the page menu, disabled at the ends.
- [ ] Add bilingual labels (`.i18n-en` + `.i18n-km` or `EInviteI18n.langText`); give the menu items
      stable IDs/data attributes for testing.
- [ ] Keyboard test: open the menu with the keyboard, invoke Move earlier/later, assert the page
      order changed and focus remains on the moved page.
- [ ] Confirm pointer drag still works and produces the same order.

**Acceptance:** reorder is fully operable without dragging; no regression to drag; strings pass the
bilingual checker.

### NW-1.3 — 3.3.7 Redundant Entry

**Problem:** signup-sheets and polls ask for name/email without `autocomplete`.

**Files:**
- Modify: `src/js/signup-sheets.js:130-131`, `src/js/polls.js:109-110`.
- Test: DOM assertion in the existing form tests or a small Playwright check.

**Steps:**
- [ ] Add `autocomplete="name"` and `autocomplete="email"` to the corresponding inputs (use
      `autocomplete="email"` for email, `autocomplete="name"` for a full name; do not use
      `username`).
- [ ] Consider the audit's optional cross-form prefill; implement only if it does not add a new
      storage dependency. If skipped, write why in `NOTES.md`.
- [ ] Verify the attributes survive the JS-built DOM (these forms are rendered dynamically).

**Acceptance:** attributes present in the served pages/JS output; forms still validate; no new
console errors.

### NW-1.4 — 3.3.8 Accessible Authentication (Minimum)

**Problem:** `#accessPassword` in `src/html/index.html:394` has no `autocomplete` value.

**Steps:**
- [ ] Add `autocomplete="current-password"` to `#accessPassword` (it is an unlock/access password,
      not a new-password field). If the field is also used for account creation, split the case and
      document it.
- [ ] Verify the password-manager affordance does not break the editor boot or the access dialog.
- [ ] Re-run the editor smoke at 1440/768/375.

**Acceptance:** attribute present in the served HTML; no functional change to unlocking; LHCI a11y
unchanged.

### NW-1.5 — 2.5.8 Target Size (Minimum)

**Problem:** the canvas resize handle is 10×10 (`src/css/typography-system.css:2`).

**Steps:**
- [ ] Raise the **hit area** to at least 24×24 without changing the visual handle size: use a
      pseudo-element or transparent padding/inset that extends the pointer target.
- [ ] Verify with a pointer test that the interactive region is ≥24×24 at 100 % zoom and at 1440 /
      1024 / 768 / 375.
- [ ] Confirm the larger hit area does not steal clicks from adjacent controls (selection ring,
      rotate handle, object edges).
- [ ] If the fix proves layout-risky, stop and ask `OD-4`; do not ship a 10×10 handle with no
      evidence.

**Acceptance:** measured hit box ≥24×24 in the live page; no selection/rotate regression.

### NW-1.6 — 2.5.5 vs 2.5.8 wording correction

**Files:** modify `docs/a11y/WCAG-AA-AUDIT.md`.

**Steps:**
- [ ] Restate the AA target-size claim against **2.5.8** (the 2.5.5 "Target Size (Enhanced)" is AAA
      and must not be cited as the AA target).
- [ ] Cross-link `docs/a11y/WCAG-2.2-AA-AUDIT.md` §5 and note the six code asks.
- [ ] No source change; no build required.

**Acceptance:** the correction is explicit, dated, and does not rewrite the historical audit
conclusions.

### Phase 1 gate

- [ ] All six tasks closed or one written exception (with `OD-4` if used).
- [ ] `build.py all`, `bundles --check`, smoke 16/16/0, LHCI assert exit 0, a11y 1.00.
- [ ] Bilingual checker exit 0.
- [ ] `artifacts/next-work/nw-1-*/` evidence complete.
- [ ] Commit the phase as one reviewable change set; do not push.

---

## 7. Phase 2 — CSS architecture cleanup (owner-gated `OD-1`)

**Goal:** reduce the deferred `!important` patch stack without changing rendering. This is the
highest-risk phase; the rules below are deliberately conservative.

**Measured starting point (audit `P3-2`):** editor-suite 660, canvas-plus 542, modern-ui 296,
stabilized 220, final-polish 217, ux-refine 209 — 1,735 occurrences across the layered CSS.
**Re-measure before planning**; the passes changed the tree.

### NW-2.1 — Inventory and classification

**Files:** create `tools/css-important-inventory.py` (read-only), output
`artifacts/next-work/nw-2-1/important-inventory.{md,json}`.

- [ ] Parse every CSS file under `src/css/` (including organized modules), count `!important` by
      file, layer, selector, and property.
- [ ] Classify each occurrence: `dead` (selector matches no element on any of the 16 pages),
      `superseded` (same property set by a later layer/rule), `override-needed` (beats a
      third-party/inline rule), `unknown`.
- [ ] Reproduce the audit's counts and explain any delta.
- [ ] Propose a staged target (recommend 25–40 % of occurrences) and submit it to `OD-1`.

**Acceptance:** the inventory is reproducible from the script; every file has a count; the target is
approved before any deletion.

### NW-2.2 — Batch 1: dead rules only

- [ ] Build a page-matrix selector check (Playwright: `document.querySelectorAll(selector).length`
      on every page, both themes, 1440/375). A selector is dead only if it matches zero elements in
      every page/state.
- [ ] Remove dead rules in batches of ≤50 declarations, one file per commit.
- [ ] After each batch: `build.py all`, `bundles --check`, smoke, and a full capture digest
      (`tools/ui-audit-capture.py` + `ui-audit-digest.py`). Any **new** overflow/occlusion/contrast
      row that is not a documented heuristic → revert the batch.
- [ ] Record the count before/after per file.

### NW-2.3 — Batch 2: superseded declarations

- [ ] For one layer at a time (suggested order: `final-polish`, `ux-refine`, `stabilized`,
      `modern-ui`, then the bundle-end responsive contract), remove declarations that are provably
      re-declared later with the same value.
- [ ] Prove equivalence with the editor pixel-diff (canvas visual gate or capture diff) and the
      16-page capture digest; internal tolerance for editor pairs: ≤0.95 % (stricter than the
      frozen 3.5 % gate).
- [ ] Do not touch `!important` that is the only thing beating an inline style or a third-party
      widget; classify those `override-needed` and leave them.

### NW-2.4 — Token convergence

- [ ] Move only repeated literal values (colors, radii, durations, z-index bands) that already
      match a token in `tokens.css`; do not invent new tokens for one-off values.
- [ ] Document any z-index band changes in `docs/` (the cascade contract matters more than the
      count).

### NW-2.5 — Stop/report rules

- [ ] Stop immediately if a batch produces more than **two** unexplained visual rows, a console
      error, horizontal scroll at 320/375, or a route-weight budget failure.
- [ ] Revert the batch, record the diff and the reason, and escalate to the owner.
- [ ] Final report: before/after counts, per-file removals, visual evidence, residual
      `override-needed` list, and the exact commands to reproduce.

### Phase 2 gate

- [ ] Approved target met (or a written explanation of why the remainder is unsafe).
- [ ] Zero visual regressions beyond the internal tolerance; 0 new console errors; 0 new overflow.
- [ ] `v55` route-weight budget still passes; `bundles --check` green.
- [ ] All 16 pages captured before/after; canvas gates green.

---

## 8. Phase 3 — Dashboard/editor parity (owner-gated `OD-2`)

**Context:** the Canva-UI rebuild restored the owner-approved core (two-pane auth, "Your designs"
grid, create flow) but not the sheets/polls event panels or edit-history. The poster `#createForm`
path in `dashboard.js` is dormant because the rebuilt markup does not include it. The inventory doc
`docs/reviews/dashboard-feature-inventory-2026-10-16.md` records what used to exist.

### NW-3.1 — Gap matrix (read-only)

- [ ] Read the inventory doc and the current `dashboard.html` / `dashboard.js`.
- [ ] Produce `artifacts/next-work/nw-3-1/gap-matrix.md`: feature → old surface → current surface
      (or absent) → user impact → implementation cost → risk.
- [ ] Include at least: edit history, sheets panel, polls panel, poster create dialog, template
      filters, passkey row, admin/designer entry points.
- [ ] Mark each row `restore`, `entry-point-only`, or `document-as-absent`, with a recommendation.

**Acceptance:** the matrix is complete enough for `OD-2` to be answered in one pass.

### NW-3.2 — Owner decision

- [ ] Record the `OD-2` answer in `artifacts/next-work/DECISIONS.md`.
- [ ] Do not write code before this is recorded.

### NW-3.3 — Implement the approved subset

- [ ] Keep the existing auth + grid + create behavior intact; add only what was approved.
- [ ] If restoring panels, reuse the existing guests/event components rather than duplicating them;
      link to the canonical surface where possible.
- [ ] If restoring edit history, verify the underlying API exists and is authorized; do not add a
      client-only mock.
- [ ] New strings are bilingual; new controls have focus-visible parity and keyboard dismissal.

### NW-3.4 — Poster create hooks: wire or remove

- [ ] Decide (with the owner if the matrix flags it): restore the `#createForm` poster path in the
      dashboard, or delete the dormant code and document Template Studio as the canonical create
      surface.
- [ ] Whichever way: remove dead null-onclick risk and add a regression test that the dashboard
      boots with zero console errors in both auth states.

### NW-3.5 — Verification

- [ ] Signed-out + signed-in × 1440/768/375 × light/dark × en/km captures.
- [ ] `dashboard.js` contract check: every ID it queries exists in the markup (script or manual
      list); no null onclick.
- [ ] Smoke 16/16/0; LHCI exit 0; a11y 1.00.

### Phase 3 gate

- [ ] Approved features shipped or explicitly documented as absent in `CANVA-UI-TASK.md` §5.
- [ ] No console errors, no dead handlers, no regression to the design grid.
- [ ] Evidence under `artifacts/next-work/nw-3-*/`.

---

## 9. Phase 4 — i18n completion

**Source:** `artifacts/i18n-km/REPORT.md` — 391 rows translated, 59 stale, 59 fallback by design.
The fallbacks are structured, not missing translations: `<option>` labels cannot hold spans, and
`feature-flags.js` has no bilingual plumbing.

### NW-4.1 — `<option>` labels (10 + 2)

**Files:** `src/html/materials.html` (10 labels), `src/html/responses.html` (2 labels), the page
scripts that populate them, and the `EInviteI18n` helper (locate it with
`rg "EInviteI18n" src/js`).

- [ ] Add `data-i18n-en` / `data-i18n-km` to each `<option>` (plain text only).
- [ ] Add a helper (e.g. `EInviteI18n.applyOptionLabels(root)`) that rewrites `option.textContent`
      on init and on language change; call it from the same place the page applies `.i18n-*` spans.
- [ ] Do not put spans inside `<option>`; do not duplicate the label text in the visible option.
- [ ] Test: switch EN→KM→EN, assert option text changes exactly once and the selected value
      survives; no "All typesAll types" duplication.
- [ ] Update `scripts/check-bilingual-consistency.py` if it needs to understand the new attributes;
      do not add an exception that hides a real missing translation.

**Acceptance:** all 12 labels switch language correctly; no duplicate text; checker exit 0.

### NW-4.2 — `feature-flags.js` bilingual path (11 strings)

**File:** `src/js/pages/admin/feature-flags.js` (plus the admin bootstrap that renders it).

- [ ] Add the same `_txt`/`langText`/`{en, km}` plumbing the rest of the admin page uses; keep
      technical terms (flag keys, API names) in English.
- [ ] Render both languages through the existing helper; do not hand-roll DOM string swaps.
- [ ] Test: admin page in KM shows Khmer for the 11 labels, EN shows English, no layout overflow at
      375.

**Acceptance:** 11 strings localized; no untranslated fallback rows remain for this module; admin
smoke clean.

### NW-4.3 — CSV reconcile (59 stale + 59 fallback)

**Files:** `docs/i18n/TRANSLATIONS.csv`, `artifacts/i18n-km/reconcile_csv.py` (reuse; do not
rewrite from scratch).

- [ ] Run the reconcile script and classify every stale row: `removed-from-tree`,
      `text-changed`, `moved-to-js`.
- [ ] Archive stale rows with a reason column (or remove them with a dated note — pick one and be
      consistent); do not leave them counted as "translated".
- [ ] Re-run after NW-4.1/4.2; target **zero fallback rows** except byte-identical technical strings;
      document each remaining exception in the report.
- [ ] Update the per-file counts in `artifacts/i18n-km/REPORT.md` with the new totals and date.

**Acceptance:** CSV totals reconcile against the tree; checker exit 0; the report states the exact
remaining exceptions and why.

### NW-4.4 — Khmer visual verification

- [ ] Capture `index.html`, `dashboard.html`, `guests.html`, `templates.html`, `materials.html`,
      `responses.html`, `admin.html` in KM at 1440/768/375, light/dark where relevant.
- [ ] Check: no clipped text, no horizontal scroll, line-height ≥1.6 on `.khmer-text`, no mixed
      EN/KM duplication, option labels readable.
- [ ] Store shots under `artifacts/next-work/nw-4-4/` and summarize any residual issue.

### Phase 4 gate

- [ ] All 12 option labels + 11 feature-flag strings localized.
- [ ] `scripts/check-bilingual-consistency.py` exit 0; khmer tests pass; build + bundles green.
- [ ] CSV/ledger totals match the tree; report updated.

---

## 10. Phase 5 — Test/CI durability

**Goal:** the suite should pass the same way twice in a row on this machine, without `-s` folklore,
and one command should reproduce every gate.

### NW-5.1 — `v27_3_5_release_evidence_test` child-process failure

**Symptom:** the test spawns `build_editor_bundle.py --check`; the child dies silently (exit 1)
when its inherited std handles are unusable under pytest's default fd capture. It passes with
`-s` / `--capture=sys`.

**Status 2026-10-21:** `1f28cbc` hardened the same class of WinError-50 path in
`canvas_motion_contract_test.py`, but the `v27_3_5_release_evidence_test` failure under default
capture still reproduces. This task remains open.

- [ ] Reproduce: `python3 -m pytest tests/v27_3_5_release_evidence_test.py -q` (expect fail) and
      `python3 -m pytest tests/v27_3_5_release_evidence_test.py -q -s` (expect pass).
- [ ] Fix at the harness boundary, not the assertion: pass explicit `stdout`/`stderr` files or
      `subprocess.DEVNULL` in the test's child invocation, or use `subprocess.run(..., capture_output=True)`
      so the child never inherits an invalid handle.
- [ ] Do not change `build_editor_bundle.py`'s contract or the pinned README digest to make the test
      pass.
- [ ] Verify both invocations pass; then run the full suite with default capture.

**Acceptance:** the test passes with default capture and with `-s`; no assertion weakened.

### NW-5.2 — `analytics_ingestion_test::test_phase4_rate_limit` order dependence

**Symptom:** passes in isolation, fails in a full run when rate state is carried across tests.

- [ ] Reproduce with a full-suite run; identify the shared limiter/identity.
- [ ] Make the test order-independent: reset the limiter in the fixture, or use a unique client
      identity/IP per test. Do not raise the production limit and do not skip the test.
- [ ] Run the full suite three times consecutively; all green.

**Acceptance:** three consecutive full-suite runs pass; the test still exercises the rate limit.

### NW-5.3 — One-command gate runner

**Files:** create `tools/run-gates.ps1` (PowerShell) or `tools/run-gates.py`.

- [ ] Options: `-Phase all|build|smoke|pytest|lhci|canvas`, `-SkipHeavy`, `-Port 8124`.
- [ ] Responsibilities: pin the renderer; start `tools/serve-gzip.py` if a gate needs it; stop it in
      `finally`; run build → bundles → smoke → pytest → LHCI → canvas gates in a fixed order; log
      each command + exit code + key output line to
      `artifacts/next-work/gates/<timestamp>/`.
- [ ] Serialize Chrome: refuse to start if another gate run holds a lock file; never run two heavy
      gates concurrently.
- [ ] Do not modify frozen canvas tools or budgets; call them as-is.
- [ ] On failure: stop the chain, keep the server stopped, print the failing command and log path.

**Acceptance:** a single invocation reproduces the Phase 0 matrix and exits 0 on a clean tree.

### NW-5.4 — Documentation of the runner

- [ ] Update `tools/README.md`, `CONTRIBUTING.md`, and `STATE.md` §Key paths & commands with the
      new command and its options.
- [ ] Note the `PYTHONIOENCODING=utf-8` and pinned-renderer requirements.

### Phase 5 gate

- [ ] Full pytest passes with default capture, twice.
- [ ] `run-gates` exits 0 end-to-end.
- [ ] No skipped/weakened tests; no gate config edits.

---

## 11. Phase 6 — UI refinement and regression sweep

**Goal:** prove the 16 pages still look right after Phases 1–5, and close the small refinement
items the audit left open. Fix only reproducible defects; do not chase documented heuristics.

### NW-6.1 — Fresh capture sweep and digest comparison

- [x] Run the full capture (`tools/ui-audit-capture.py`) with the pinned renderer, at the same
      matrix as the Canva-UI after-sweep: 16 pages × user/guest × 320/375/768/1024/1440 × light/dark
      × en/km (where the tool supports it).
      *(closed 2026-10-21 at HEAD `1cd09d2`: 240 shots under `artifacts/next-work/nw-6-1/after/`)*
- [x] Run `tools/ui-audit-digest.py`; compare against
      `artifacts/ui-audit/fixes/canva-ui/after-digest.txt` (0 overflow rows at close).
      *(0 overflow rows at every viewport, digest `artifacts/next-work/nw-6-1/after-digest.txt`)*
- [x] Classify each new row: real regression / known heuristic / capture race. Fix only the first.
      *(no real or heuristic rows; the one delta class — 10 transient `ei-quick-toolbar` occlusion
      rows at index@375/320 — was reproduced as a compositing capture race in
      `artifacts/next-work/nw-6-1/recheck/`, same known class as the 375-dark 4.85 % precedent)*
- [x] Record the comparison in `artifacts/next-work/nw-6-1/COMPARE.md`.

**Acceptance:** no new real rows; every new row has a classification and evidence.

### NW-6.2 — First-run tour determinism for captures

**Problem:** `final-experience.js`'s `final-tour` dialog remounts per session and swallows the
first canvas click; earlier probes misread this as a G4 failure.

- [x] Add a documented "tour seen" storage key (or reuse an existing flag) that the app honors; set
      it in the capture profile before the editor probe.
      *(closed 2026-10-21: the app honored already had the seen-flag + legacy migration
      (`einvite-final-tour-seen-v1` → `einvite-final-tour-seen-v2:{identity}:studio-v27`,
      final-experience.js:146–153), so the capture harness now seeds the legacy key pre-page-script
      via `tests/browser_runtime.py::mark_editor_onboarding_seen` wired into every capture context.
      No app src/ change; first-run UX untouched by construction.)*
- [x] Do not disable the tour for real users; this is a capture determinism fix.
- [x] Verify: capture `index.html` without dismissing the dialog manually; the canvas is clickable
      on the first probe.
      *(evidence: artifacts/next-work/nw-6-2/{NOTES.md,capture/}; 0 final-tour-covered occlusion
      rows at 1440/375, `stageTransform` reachable, EInviteCanvasViewController.fit() exercised;
      full suite 143/0 via the documented `-s` path after reproducing a host-level std-handle
      breakage in default capture with the changes stashed — environment note, not this task's
      regression.)*

*Acceptance:* capture runs no longer need a manual "Start creating" dismissal; real first-run UX
unchanged.

### NW-6.3 — Floating controls at breakpoints

- [ ] Verify the `Timeline` pill, zoom cluster, selection toolbar, and context toolbar at
      1440/1024/768/375 for overlap with the canvas and each other (the audit's A7 and B3 items).
- [ ] Fix only reproducible overlaps; anchor the pill to the statusbar track if it still floats.
- [ ] Before/after screenshots per width.

**Acceptance:** no toolbar-on-toolbar or toolbar-on-canvas occlusion in the captures; no new
horizontal scroll.

### NW-6.4 — Motion contract audit

- [ ] Verify transitions remain `transform`/`opacity` (plus cheap color/border/background) and that
      `prefers-reduced-motion` kills tweens/stagger on every page that animates.
- [ ] Check the `--motion-fast`/`--motion`/`--motion-slow`/`--spring`/`--smooth` values are still the
      pinned ones; no new duration/easing literals.
- [ ] Run one perf trace on the editor at 1440 and 375; confirm no layout-thrashing transitions.

**Acceptance:** no new motion regressions; perf trace clean; reduced-motion screenshots.

### NW-6.5 — Theme/contrast sweep

- [ ] Re-run the contrast heuristic on the 16 pages in dark/light; compare with the Canva-UI
      baseline.
- [ ] Do not "fix" the five documented false-positive classes; if a genuine <4.5:1 body-text row
      appears, fix it with a token, not a one-off.
- [ ] Confirm the invitation paper's dark-mode appearance matches the owner-approved rebaseline
      decision; do not change it back.

**Acceptance:** no new real contrast failures; the rebaseline decision is documented in the report.

### NW-6.6 — Route-weight headroom (privacy)

**Context:** `privacy.html` was excluded from the Canva-UI shared layer because it had only 562 B of
headroom under its LHCI ceiling.

- [ ] Measure the current route weight; identify safe byte reductions (dead CSS from Phase 2,
      duplicated declarations, unused tokens).
- [ ] Do not change the budget or the LHCI config. If the page cannot safely take the shared layer,
      document the decision and leave it excluded.
- [ ] Re-run `v55` and LHCI.

**Acceptance:** the page stays within budget; the decision (include or exclude) is written down.

### Phase 6 gate

- [ ] 0 horizontal scroll at 320/375; 0 console errors; LHCI 16/16; a11y 1.00.
- [ ] Full capture digest compared; no new real rows.
- [ ] Before/after evidence for every fix; no heuristic chasing.

---

## 12. Phase 7 — Documentation and release readiness

### NW-7.1 — Keep STATE current

- [ ] At the end of every phase, update `artifacts/ui-audit/fixes/STATE.md` Done / Active / Next
      Move, including the new HEAD, the phase gate results, and the next task ID.
- [ ] Keep the header honest: HEAD, ahead count, tree status, last-updated date.

### NW-7.2 — Authoritative status index

- [ ] Create `docs/STATUS-INDEX.md`: one table mapping every root work order, results ledger, and
      a11y audit to `authoritative` / `historical` / `superseded`, with the date and the one-line
      verdict.
- [ ] Add status banners to superseded reports (at minimum: `UI-VISUAL-AUDIT-FIX-TASK.md`,
      `CANVAS-MOTION-FIX-TASK.md`, `DESIGN-FIX-TASK.md` if not already done; the bookkeeping pass
      for 2026-10-20 covers the first three).
- [ ] Link `NEXT-WORK-TASK.md` from `STATE.md` and the project `AGENTS.md` project-memory section.

### NW-7.3 — Release candidate

- [ ] Review the full diff since `37bfc8d` (or since the last accepted checkpoint) file by file;
      list every source change and its gate.
- [ ] Run the full gate matrix one last time from a clean tree (`run-gates`).
- [ ] Write `RELEASE-CANDIDATE.md`: HEAD, commits included, gates with numbers, evidence paths,
      remaining owner decisions, known limitations, and the push instruction (blocked on `OD-3`).
- [ ] Do not update `VERSION_HISTORY.md` or tag anything without the owner's answer.

### NW-7.4 — Handoff

- [ ] Write a final session summary in `STATE.md` and `artifacts/next-work/HANDOFF.md`: what
      changed, what was verified, what remains, and the exact next command.
- [ ] Confirm every checkbox in this file is either ticked with evidence or explicitly deferred with
      an owner decision.

### Phase 7 gate

- [ ] All docs agree on HEAD, gates, and open items.
- [ ] A fresh agent can read `STATE.md` → `NEXT-WORK-TASK.md` → `OPEN-ITEMS.md` and start without
      chat history.

---

## 13. Evidence protocol (applies to every task)

For each task `NW-x.y`, create:

```
artifacts/next-work/nw-x-y/
  NOTES.md            # goal, commands, exit codes, decisions, links
  before/             # screenshots, JSON, logs captured before the change
  after/              # the same matrix after the change
  logs/               # raw command output
```

Rules:

- A claim without a command + exit code + evidence path is not a result. Say "not run" instead.
- Screenshots are named `<page>-<state>-<viewport>-<theme>-<lang>.png`.
- JSON heuristics keep their schema; do not hand-edit them.
- Never commit `artifacts/`.

---

## 14. Definition of done (global)

This work order is done when all of the following are true:

1. **Accessibility:** all six WCAG 2.2 AA code asks are closed or one written, owner-approved
   exception exists; LHCI a11y 1.00 on all 16 pages.
2. **CSS debt:** the approved `!important` reduction target is met with zero visual regressions
   beyond the internal tolerance; residual `override-needed` rules are documented.
3. **Dashboard parity:** every gap in the matrix is either shipped, converted to an entry point, or
   documented as intentionally absent with `OD-2` recorded.
4. **i18n:** the 12 option labels and 11 feature-flag strings are localized; the CSV reconciles;
   fallback rows are zero or documented exceptions.
5. **Tests/CI:** full pytest passes twice with default capture; one command reproduces every gate;
   no test is skipped or weakened.
6. **UI:** fresh capture sweep shows no new real rows; 0 horizontal scroll at 320/375; 0 console
   errors; motion/reduced-motion contract intact.
7. **Docs:** `STATE.md`, this file, `OPEN-ITEMS.md`, `STATUS-INDEX.md`, and the results ledgers agree
   on HEAD, gates, and open items.
8. **Release:** `RELEASE-CANDIDATE.md` exists; nothing is pushed without `OD-3`.

---

## 15. Stop conditions and escalation

Stop the current task and report (do not improvise) when:

- a baseline gate is red before you changed anything;
- a change makes a frozen gate fail and the cause is not obviously yours;
- a batch produces more than two unexplained visual rows;
- a task needs to edit a frozen file, a threshold, a budget, or a baseline;
- two heavy Chrome runs would overlap;
- an `OD-n` gate is unanswered and the next step depends on it;
- a test only passes with `-s`, a retry, or a wider timeout after your change — that is a harness
  problem to fix, not a pass;
- the working tree contains changes you did not make (treat them as the user's work; investigate,
  never revert blindly).

Escalation format: task ID, command, exit code, expected vs actual, log path, smallest proposed
next step. Do not attach a fix you have not verified.

---

## 16. Appendix A — Exact commands

```powershell
# repo
cd F:\Project\eInvite\online-invitation-platform
$env:PYTHONIOENCODING = "utf-8"
$env:CHROME_PATH = "$env:LOCALAPPDATA\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

# renderer pin (before heavy runs)
powershell -ExecutionPolicy Bypass -File tools\_pin-renderer.ps1

# build + bundle gate
python3 build.py all
python3 build.py bundles --check

# static server + smoke
python3 tools/serve-gzip.py --port 8124
node tools/page-errors.mjs --all
# stop the server after the run

# full pytest (the suite is sensitive to capture; default capture is the target after NW-5.1)
python3 -m pytest tests/ -q -s

# canvas gates (frozen; run one at a time)
python3 tests\canvas_motion_playwright.py --phase all --output artifacts\canvas-motion\verify\acceptance-next-work
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- node tools/canvas-motion-perf.mjs --phase=P1 --output=artifacts/canvas-motion/verify/perf-next-work
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/canvas-motion-visual.py --base "{base}" --phase P1 --out artifacts/canvas-motion/verify/visual-next-work

# LHCI
npx lhci collect --config=tools/lighthouserc.js
npx lhci assert --config=tools/lighthouserc.js

# capture + digest
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/ui-audit-capture.py --out artifacts/ui-audit/fixes/next-work/after
python3 tools/ui-audit-digest.py --dir artifacts/ui-audit/fixes/next-work/after --out artifacts/ui-audit/fixes/next-work/after-digest.txt

# bilingual checker
python scripts/check-bilingual-consistency.py

# live server (manual probing)
$env:PYTHONPATH = "."
$env:EINVITE_ALLOW_NO_SCANNER = "1"
python src/python/server.py   # http://127.0.0.1:4175
```

---

## 17. Appendix B — File map (where the work lives)

| Area | Files |
|---|---|
| Editor shell / HTML | `src/html/index.html` |
| Editor JS | `src/js/app.js`, `professional-editor.js`, `direct-manipulation.js`, `editor-layout-stability.js`, `workflow-*.js`, `page-experience.js`, `final-experience.js` |
| Editor CSS | `src/css/editor-styles.css`, `typography-system.css`, `stabilized.css`, `editor-suite*.css`, `ux-refine.css`, `final-polish.css`, `modern-ui.css` |
| Dashboard | `src/html/dashboard.html`, `src/js/dashboard.js`, `src/css/canva-ui.css` |
| Guest/public | `src/html/public.html`, `src/js/public-page.js`, `src/css/public-*.css` |
| Forms / polls | `src/js/signup-sheets.js`, `src/js/polls.js`, `src/html/*.html` |
| Admin / flags | `src/html/admin.html`, `src/js/pages/admin/feature-flags.js`, `src/js/admin.js` |
| i18n | `src/js/i18n.js` (or the module defining `EInviteI18n`), `docs/i18n/TRANSLATIONS.csv`, `scripts/check-bilingual-consistency.py` |
| Build | `build.py`, `src/python/build/*.py`, `docs/route-bundle-sources.json` |
| Tests | `tests/`, `tools/page-errors.mjs`, `tools/ui-audit-*.py`, `tests/canvas_motion_playwright.py` (frozen) |
| Evidence | `artifacts/ui-audit/fixes/`, `artifacts/canvas-motion/`, `artifacts/next-work/` |
| State | `artifacts/ui-audit/fixes/STATE.md`, `NEXT-WORK-TASK.md`, `docs/STATUS-INDEX.md` |

---

## 18. Appendix C — Session log template

Copy into `artifacts/next-work/<task-id>/NOTES.md`:

```markdown
# NW-x.y — <title>
Date:
Agent:
HEAD before / after:
Goal:

## Commands run
| command | exit | key output |
|---|---|---|
|  |  |  |

## Changes
- Files:
- Why:

## Evidence
- before:
- after:

## Verification
- build all:
- bundles --check:
- smoke:
- pytest:
- LHCI:
- canvas gates:

## Open / follow-ups
-

## Next command for the next agent
-
```

---

## 19. Appendix D — Task index (tick as closed)

- [ ] NW-0.1 Confirm HEAD/tree/state
- [ ] NW-0.2 Baseline gate matrix
- [ ] NW-0.3 Open-items ledger
- [ ] NW-0.4 Evidence tree
- [ ] NW-1.1 2.4.11 focus not obscured
- [ ] NW-1.2 2.5.7 dragging movements
- [ ] NW-1.3 3.3.7 redundant entry
- [ ] NW-1.4 3.3.8 accessible authentication
- [ ] NW-1.5 2.5.8 target size
- [ ] NW-1.6 2.5.5/2.5.8 wording
- [ ] NW-2.1 CSS inventory (OD-1)
- [ ] NW-2.2 Dead-rule removal
- [ ] NW-2.3 Superseded declarations
- [ ] NW-2.4 Token convergence
- [ ] NW-2.5 Stop/report
- [ ] NW-3.1 Dashboard gap matrix (OD-2)
- [ ] NW-3.2 Owner decision recorded
- [ ] NW-3.3 Approved parity subset
- [ ] NW-3.4 Poster hooks wire-or-remove
- [ ] NW-3.5 Dashboard verification
- [ ] NW-4.1 `<option>` labels
- [ ] NW-4.2 `feature-flags.js` i18n
- [ ] NW-4.3 CSV reconcile
- [ ] NW-4.4 Khmer visual verification
- [ ] NW-5.1 Child-process test fix
- [ ] NW-5.2 Rate-limit order flake
- [ ] NW-5.3 One-command gate runner
- [ ] NW-5.4 Runner documentation
- [x] NW-6.1 Capture sweep + digest compare
- [x] NW-6.2 Tour capture determinism
- [ ] NW-6.3 Floating controls
- [ ] NW-6.4 Motion contract
- [ ] NW-6.5 Theme/contrast sweep
- [ ] NW-6.6 Privacy route-weight headroom
- [ ] NW-7.1 STATE current
- [ ] NW-7.2 Status index + banners
- [ ] NW-7.3 Release candidate
- [ ] NW-7.4 Handoff

---

**End of work order.** If you are the next agent and something here contradicts the repository,
the repository and its gates win — write the discrepancy into `STATE.md`, update this file, and
report it. Never bend a gate to match a document.
