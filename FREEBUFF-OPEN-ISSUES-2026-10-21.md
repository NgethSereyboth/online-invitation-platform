# Freebuff Work Order — Every Open eInvite Issue

**Repository:** `/media/ngethsereyboth/LocalDisk/eInvite/einvite-platform`
**Prepared:** 2026-10-21
**Owner-approved:** 2026-10-22 — answers recorded in §6.1; proceed without re-asking for the approved scope
**Executor:** Freebuff (autonomous coding agent)
**Baseline branch:** `pass/2026-10-21-next-work`
**Baseline HEAD:** `6f7de27` (same as `origin/pass/2026-10-21-next-work`)
**Baseline main:** `50721ef` (ten commits behind the branch)
**Branch delta:** 10 commits, 84 files changed, +3,185 / −492
**Tracked tree:** clean; **78 untracked owner paths preserved** (this work order is an additional untracked planning file; do not stage it unless the owner asks)
**Status of this document:** owner-approved 2026-10-22; research complete; uncommitted; no code changed by writing it.
**Execution authority:** the owner approved this plan and the answers in §6.1. Freebuff may execute the approved scope without asking again. Stop only for OD-6/frozen-gate changes or a genuinely new product decision. OD-8 Khmer is deferred — leave feature flags English and continue.

> **Freebuff: read this file completely before touching the repository.** It is a work order, not a suggestion list. Each item has a reproduction, a fix boundary, acceptance criteria, and traps. Execute one item at a time. Do not “fix” the false positives in §10.

---

## 0. Executive summary

The repository looks greener than it is. The branch has substantial completed work (a11y, i18n, harnesses, docs), but the release evidence is not clean:

1. **CI on `main` is red in two workflows**: Security Scan (Pillow CVEs) and Performance Budgets (Lighthouse CI cannot determine its build directory). See FB-01 and FB-02.
2. **The branch introduces a new budget regression**: `v55_route_weight_budget_test.py` fails because `admin.html` is 716 bytes over its frozen script budget. See FB-03.
3. **The full test suite cannot be green on Linux until FB-04**: the README digest pin is a Windows CRLF hash (`OD-7`, now approved for the normalization fix). The last clean run read 142 passed / 1 failed; a later repeat exposed a second, intermittent failure (item 4). See FB-04.
4. **Repeatability is not proven**: a second consecutive full-suite run produced a *different* failure — an intermittent app-server readiness timeout in `analytics_privacy_test.py`. Isolated, the same test passes in 4.85 s. See FB-09. The “three consecutive runs” acceptance for NW-5.2 has therefore **not** been met.
5. **CI never runs pytest**: only Lighthouse and Security workflows exist, and they trigger on `main`/PR (Security also on `v54`), not on this branch. `make test` uses the system Python, which lacks Playwright and produces six collection errors; `make reproduce` prefers that same interpreter and treats test failures as non-fatal. See FB-06 and FB-07.
6. **226 of 261 test-pattern files contain no `def test_`**, and the budget gates `v55`/`v14` are among them. They are not run by pytest or by `tools/run-gates.py`; CI’s Performance workflow does run them on `main`/PRs (v14 non-blocking), but this branch’s push did not trigger CI. The suite is green partly because large parts of it do not run. See FB-08.
7. **Six Dependabot alerts remain open**, all npm development/transitive dependencies under `@lhci/cli`. The two high `extract-zip` alerts and the medium `sprintf-js` alert have no fixed release; `tmp` and `uuid` do. See FB-10.
8. **Several ledgers contradict reality** (push status, WCAG “none applied”, wrong frozen-file path, stale HEADs, stale workflow comments). See FB-12.
9. **Three verification gates have never run on this host**: canvas visual baseline, canvas performance, and the RILL end-to-end walkthrough. See FB-16, FB-17, FB-18.
10. **Owner decisions were answered on 2026-10-22**: OD-1 (25–40%) and OD-2 (recommended subset) approved; OD-4/OD-5 confirmed; OD-7 Option A approved; OD-8 deferred; i18n audit-first; v14 stays non-blocking; release is **local commits only**. See §6.1. No further questions for the approved scope.

**Work-item count:** 22 primary items (FB-01 … FB-22), plus the OD-1…OD-8 register. Of these, **10 are release/CI/test-infrastructure fixes (FB-01–FB-10)**, **7 are verification/close-out/audit items (FB-13–FB-18 and FB-22)**, **2 are approved implementations (FB-19, FB-20)**, **1 is deferred (FB-21)**, and **2 are documentation truth-ups (FB-11–FB-12)**. Dependency hygiene is inside FB-10; canvas visual/perf and RILL are inside the verification group.

**First actions, in order:** FB-01 → FB-02 → FB-03 → FB-04 → FB-06 → FB-07 → FB-09 → FB-10 → FB-05 → FB-08 → FB-12 → FB-19/FB-20. FB-21 stays deferred (OD-8). Release is local-only: no push/PR/merge/tag.

### Work-item index

| ID | Title | Priority | Gate / status | Wave |
|---|---|---|---|---|
| FB-01 | Security Scan red: Pillow 12.3.0 CVEs | P0 | none — start | 1 |
| FB-02 | LHCI `staticDistDir` failure + artifact path | P0 | none — start | 1 |
| FB-03 | v55 admin +716 B regression | P0 | OD-6 (no budget change) — start | 1 |
| FB-04 | OD-7 README digest pin | P0 | **OD-7 approved — Option A** | 1 |
| FB-05 | NW-5.1 child-process capture | P1 | none (after FB-04) | 1 |
| FB-06 | Makefile/reproduce wrong Python; non-fatal tests | P0 | none — start | 1 |
| FB-07 | No pytest CI / branch trigger gap | P0 | none — start | 1 |
| FB-08 | 226 zero-test files; v55/v14 not in run-gates | P1 | none — start | 1 |
| FB-09 | Intermittent app-server readiness flake | P1 | none — start | 1 |
| FB-10 | Six Dependabot alerts | P1 | remove local chains; remote closure deferred | 1 |
| FB-11 | v14 known-red quarantine + stale comments | P2 | **owner: keep non-blocking** | 2 |
| FB-12 | Documentation truth-up cluster | P1 | none — start | 2 |
| FB-13 | NW-5.2: stale test reference / repeatability | P1 | none — verify | 2 |
| FB-14 | 305 i18n fallback rows | P1 | **owner: audit first** (no translations) | 2 |
| FB-15 | Final release gate matrix | P0 | **local commits only** | 3 |
| FB-16 | Canvas visual gate (baseline missing) | P1 | record NOT RUN if baseline absent | 3 |
| FB-17 | Canvas performance gate (environment) | P1 | record environment-blocked if no hardware | 3 |
| FB-18 | RILL walkthrough (never executed) | P2 | local run; cloud URL not required | 3 |
| FB-19 | OD-1 CSS cleanup | P1 | **OD-1 approved 25–40% — start** | 3 |
| FB-20 | OD-2 dashboard parity | P1 | **OD-2 approved subset — start** | 3 |
| FB-21 | OD-8 feature-flags Khmer | P1 | **OD-8 deferred — do not start** | — |
| FB-22 | OD-3/4/5 close-out | P2 | **confirmed; local-only release** | 2 |

Status values in this document: **open** (ready to work), **approved** (owner answer recorded; proceed), **deferred** (do not start), **verify** (run/evidence, may close with no code), **doc** (truth-up), **blocked** (dependency). A P0 item is release/CI-blocking; P1 is required for a trustworthy release; P2 is hygiene/verification.

---

## 1. What is already done (do not redo)

These were verified in the branch history. Re-doing them wastes the budget and risks regressions.

| Commit | Work | Status |
|---|---|---|
| `ec0cf91` | Six WCAG 2.2 AA code asks: focus-not-obscured measurement, bilingual Move earlier/later + 8/8 keyboard check, autocomplete, 24×24 live handle hit box, doc relabels | shipped |
| `ca53dbe` | Gradient AA close for the billing empty state | shipped |
| `6a30d9e` | Runtime bilingual `<option>` label rewrite (`data-i18n-en` / `data-i18n-km`), no custom listbox | shipped, but caused FB-03 |
| `11e549f` | Quick-toolbar keyboard reachability | shipped |
| `8952381`, `cd56ac0` | Allowlist startup race; suite moved from 3 failures to 1 (OD-7) | shipped |
| `1f28cbc` | Hardened the WinError-50 path in `canvas_motion_contract_test.py` | shipped |
| `6f7de27` | Eight verification harnesses, continuation brief, HEAD/count corrections | shipped |
| — | Branch pushed to `origin/pass/2026-10-21-next-work` | done; new work is **local commits only** |

**Closed items that should stay closed:** NW-6.3 toolbar reachability, the two allowlist failures, the six a11y asks, the bilingual option labels, gradient contrast. See §10 before reopening any of them.

---

## 2. Verified baseline (2026-10-21)

### 2.1 Local gates

| Gate | Command | Observed |
|---|---|---|
| Build | `python3 build.py all --check` | exit 0; `MIRROR_CHECK_PASSED (up_to_date=327)` |
| Bundles | `python3 build.py bundles --check` | exit 0; `ROUTE_BUNDLE_CHECK_PASSED` |
| Smoke | `node tools/page-errors.mjs --all` | `TOTAL pages=16 consoleErrors=0 non2xx=0` |
| LHCI (local assert) | `npx lhci assert --config=tools/lighthouserc.js` | exit 0; a11y 1.00 on 16/16 reports |
| Bilingual checker | `python3 scripts/check-bilingual-consistency.py` | exit 0 |
| Canvas acceptance | `tests/canvas_motion_playwright.py --phase all` | 22 pass / 0 fail / 2 expected console rows |
| Full pytest | `.venv/bin/python -m pytest tests/ -q` | 142 passed, 1 failed (OD-7) in 4:39 |
| Full pytest, repeat 1 | same | 142 passed, 1 failed (OD-7) in 4:26 |
| Full pytest, repeat 2 | same | **141 passed, 2 failed** — OD-7 **plus** `analytics_privacy_test::test_phase4_public_privacy_page` (server readiness), 4:54 |
| Route budget (v55) | `python3 tests/v55_route_weight_budget_test.py` | **FAIL** — admin 163,532 B > 162,816 B by 716 B |
| Aspirational budget (v14) | `python3 tests/v14_performance_budget_test.py` | **FAIL** — editor index.html styles 2 > 1; **owner chose keep non-blocking** (2026-10-22) |
| Canvas visual | `tools/canvas-motion-visual.py` | **NOT RUN** — baseline directory absent |
| Canvas performance | `tools/canvas-motion-perf.mjs` | **NOT VERIFIED** — headless timing environment |
| RILL walkthrough | `RILL-WALKTHROUGH.md` | **NEVER EXECUTED** |

The two other full-suite runs are not proof of repeatability: run 1 was clean apart from OD-7; run 2 failed differently. The isolated rerun of the newly failing test passed in 4.85 s. That is the signature of a harness/load issue, not a product assertion failure. See FB-09. These are pre-fix baseline counts: **OD-7 is now approved**, so FB-04 should remove the digest failure; FB-09 must remove the readiness flake before the suite is called repeatable.

### 2.2 CI on `main` at `50721ef`

| Workflow | Run | Result | Root cause |
|---|---|---|---|
| Security Scan | `39557451856` | **red** | `pip-audit` finds 8 CVEs in `Pillow 12.3.0`; fixed in `13.0.0` |
| Performance Budgets | `39557451848` | **red** | Lighthouse CI `autorun` fails: `Error: Failed to automatically determine staticDistDir`; layer 2 (`v14`) also red but `continue-on-error` |
| CodeQL / Pages | recent runs | green | not part of this work order |

The current branch push did **not** trigger CI. `.github/workflows/lighthouse.yml` and `security.yml` trigger on `main` and PRs; Security also includes `v54-refactor-security-ui`. There is no pull request for this branch. Adding a pytest workflow and PR coverage is FB-07.

### 2.3 Dependabot (open alerts on the default branch)

All six are npm **development/transitive** dependencies in `package-lock.json`, not runtime application code. “No fix” means no patched release exists at the time of research.

| # | Package | Severity | Fix available | Chain |
|---|---|---|---|---|
| 8 | `sprintf-js` | medium | **no** | `@lhci/cli@0.15.1` → `@lhci/utils@0.15.1` → `js-yaml@3.15.2` → `argparse@1.0.10` → `sprintf-js@1.0.3` |
| 6 | `extract-zip` | high | **no** | `@lhci/cli` → `lighthouse@12.6.1` → `puppeteer-core@24.43.1` → `@puppeteer/browsers@2.13.2` → `extract-zip@2.0.1` |
| 5 | `extract-zip` | high | **no** | same chain (second advisory) |
| 4 | `tmp` | high | `0.2.6` | `@lhci/cli` → `inquirer@6.5.2` → `external-editor@3.1.0` → `tmp@0.0.33` |
| 3 | `uuid` | medium | `11.1.1` | `@lhci/cli@0.15.1` → `uuid@8.3.2` |
| 2 | `tmp` | low | `0.2.4` | `@lhci/cli` direct `tmp@0.1.0` |

`npm audit` locally reports 17 advisories because it counts paths/advisories that GitHub collapses or has dismissed. The release metric is the six **open GitHub alerts**, not “17”; do not chase all 17 blindly. See FB-10 for remediation options.

---

## 3. Non-negotiable constraints

These apply to every item.

1. **Never change a budget, threshold, or frozen gate (OD-6).** This includes `docs/perf/lighthouse-budgets.json`, the `BUDGETS` maps in `tests/v14_performance_budget_test.py` and `tests/v55_route_weight_budget_test.py`, all thresholds in `tools/canvas-motion-perf.mjs`, and the Lighthouse assertions in `tools/lighthouserc.js`. If a gate is wrong, stop and document; only the owner can approve a change.
2. **Never edit frozen canvas files:** `artifacts/canvas-motion/**`, `docs/CANVA-SMOOTHNESS-BRIEF.md` (this is the real filename — several docs misspell it as `CANVAS-SMOOTHNESS-BRIEF.md`), and `tests/canvas_motion_playwright.py`.
3. **Never stage untracked owner work.** There are 78 untracked paths (`.claude/`, `data/`, `deploy/sites/`, review PNGs, etc.). Use explicit `git add <path>`; never `git add -A` / `git add .`; never clean, stash, reset, or checkout those paths.
4. **Do not push, force-push, open a PR, merge, tag, or rewrite history.** The existing branch push was already approved and is at `6f7de27`; **new work uses local commits only** (owner answer 2026-10-22). `main` remains at `50721ef` until the owner explicitly changes this.
5. **Use the test virtualenv for anything browser-related:** `.venv/bin/python`. The system `python3` has pytest but **not** Playwright; it produces six collection errors. Do not install packages into the system interpreter (PEP 668). Use `PYTHONIOENCODING=utf-8`.
6. **Do not make tests pass with `-s`, `--capture=sys`, retries, skips, or weaker assertions.** Fix the harness at the process boundary (see FB-04/FB-05/FB-09).
7. **Do not machine-translate Khmer.** The module convention (`KH_PENDING`, repo convention `c2ec627`) permits only owner-supplied Khmer; an agent fill previously produced mojibake and was reverted. OD-8/FB-21 depend on the owner.
8. **One item, one commit (unless the item explicitly groups sub-fixes).** Conventional commit messages; include the evidence path in the body. Do not amend the existing ten commits.
9. **Record evidence for every item** under `artifacts/next-work/fb-<id>/`: `NOTES.md`, command lines, exit codes, logs, before/after measurements, screenshots. `artifacts/` is gitignored; never commit logs or generated PNGs.
10. **Stop only at the remaining gates.** OD-1/OD-2/OD-7 are approved; OD-4/OD-5 are confirmed; OD-8 is deferred; i18n is audit-first; v14 stays non-blocking; release is local-only. Do not re-ask those. Stop only for an OD-6/frozen-gate change, missing owner Khmer (leave English and continue), or a genuinely new product decision. A partial, well-evidenced deliverable is acceptable when an environment/owner dependency remains.

---

## 4. Environment and command map

```bash
cd /media/ngethsereyboth/LocalDisk/eInvite/einvite-platform

# Interpreter / deps
.venv/bin/python --version
.venv/bin/python -m pytest --version
.venv/bin/python -c "import playwright; print(playwright.__file__)"

# Build / bundles
python3 build.py all --check
python3 build.py bundles --check

# Smoke (16 pages, no auth)
node tools/page-errors.mjs --all

# Static server with gzip — the only server that reproduces Lighthouse byte counts
python3 tools/serve-gzip.py --port 8124

# Real dev server (for RILL / browser flows)
EINVITE_DATA_DIR=$(mktemp -d) EINVITE_DEV_AUTH_TOKENS=1 EINVITE_ALLOW_NO_SCANNER=1 \
  PYTHONPATH=src/python:. python3 src/python/server.py --port 4175

# LHCI (after FB-02; from repo root)
npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js

# Focused gates
python3 tests/v55_route_weight_budget_test.py
python3 tests/v14_performance_budget_test.py
.venv/bin/python -m pytest tests/v27_3_5_release_evidence_test.py -q
.venv/bin/python -m pytest tests/analytics_privacy_test.py::test_phase4_public_privacy_page -q
```

**Ports used by existing docs/tools:** `8124` static gzip server; `8137` canvas visual default; `4175` dev server; LHCI URLs use `127.0.0.1:8124`. Check listeners before starting; do not kill a process you did not start.

**Important distinction:** `python3 -m http.server` serves uncompressed bytes and makes Lighthouse budgets fail. Always use `tools/serve-gzip.py` for byte-budget work.

---

## 5. How Freebuff should execute this

1. **Read §0–§4, then confirm the baseline.** Run `git rev-parse --short HEAD`, `git status --porcelain`, and the three quick gates (build, bundles, smoke). If HEAD is not `6f7de27`, stop and record drift; do not apply this document blindly.
2. **Create one local work branch** (recommended: `git switch -c fix/2026-10-22-open-issues`). This leaves the 78 untracked paths untouched. If the owner says to stay on the current branch, stay; do not push either way.
3. **Work in waves.** Wave 1 is the release-blocking set. Do not jump to Wave 3 until the release blockers are stable; FB-19/FB-20 are approved once you get there, and FB-21 stays deferred.
4. **For each item:** reproduce before changing; read the linked evidence; make the smallest fix that satisfies acceptance; run the targeted commands and the full suite where indicated; write the evidence file; commit only the intended paths.
5. **At the end of each day/wave:** update the ledgers in FB-12 only with verified results. Do not mark a gate green if it was not run; write “NOT RUN” with the reason.
6. **If a command fails in a way not described here:** capture the full output, check whether the failure is a known false positive (§10), and either fix or report it. Do not silently change the test.

---

## 6. Owner decisions (OD register)

This is the authoritative decisions register. **The owner answered on 2026-10-22; the answers in §6.1 override the earlier recommendations.** The source ledgers (`artifacts/next-work/DECISIONS.md`, `OPEN-ITEMS.md`) still need to be reconciled by FB-12.

| ID | Decision | Status (2026-10-22) | Owner answer / action | Blocks |
|---|---|---|---|---|
| **OD-1** | Scope/target for `!important` / layered-CSS cleanup | **APPROVED** | **25–40%**, staged, pixel-diff-gated, dead rules first; stop at first unexplained diff | FB-19 / NW-2.2–2.4 — **unblocked** |
| **OD-2** | Dashboard parity subset | **APPROVED** | **Recommended subset**: sheets/polls entry points, passkey row + poster type, document event-role picker absent, edit history only as cheap ⋮ link | FB-20 / NW-3.2–3.5 — **unblocked** |
| **OD-3** | Push / release / version history | **ANSWERED** | Existing branch already pushed at `6f7de27`; **local commits only for now**; no push/PR/merge/tag; `VERSION_HISTORY.md` untouched | release publication — **no push** |
| **OD-4** | “Equivalent” exception for the 10×10 canvas resize handle | **CONFIRMED** | Owner confirmed; close the ledger item. No code work | close-out only |
| **OD-5** | Khmer `<option>` implementation choice | **CONFIRMED** | Owner confirmed the runtime rewrite, no custom listbox; close the ledger item | close-out only |
| **OD-6** | Any budget/threshold change | **STANDING RULE** | Unchanged: never propose or make one without explicit owner approval | all budget work |
| **OD-7** | Linux portability of the README digest pin | **APPROVED — Option A** | Normalize `\r\n` → `\n` before hashing; pin LF digest `38ce744d…`; add the CRLF/LF regression test and dated note | FB-04 — **unblocked** |
| **OD-8** | Trusted Khmer for `feature-flags.js` doc-strings | **DEFERRED** | Owner deferred translation supply. **Do not machine-translate.** Feature flags remain English for now; revisit later | FB-21 — **stays deferred** |

### 6.1 Owner answers recorded 2026-10-22

The owner reviewed the work order and supplied these exact answers, with approval to proceed without further questioning for this scope:

```text
OD-1: approve 25–40%
OD-2: approve recommended subset
OD-4: confirm
OD-5: confirm
OD-7: A (normalize + LF pin)
OD-8: defer for now
i18n: audit first
v14: keep non-blocking for now
release: local commits only for now
```

**Authority and stop conditions.** These answers are sufficient for the approved scope. Freebuff does **not** need to ask again about OD-1, OD-2, OD-4, OD-5, OD-7, the i18n audit-first policy, the v14 non-blocking policy, or the local-only release policy. Stop only if:

- a change would alter a budget, threshold, or frozen gate (OD-6);
- a genuinely new user-visible/product decision appears that is not covered here.

OD-8 is deferred: do **not** stop for missing Khmer; leave feature flags English and continue. If an environment prerequisite is missing (canvas baseline, Windows perf hardware, public RILL URL, remote GitHub alert closure), record **NOT RUN/deferred** and continue; that is not a question. Otherwise: execute, commit locally, record evidence, and keep moving. “Local commits only” means **no push, no PR, no merge, no tag**.

### OD-1 — `!important` cleanup scope — APPROVED 25–40%

**Evidence:** `artifacts/next-work/nw-2-1/important-inventory.md` records **4,033 occurrences across 67 source CSS files**; layers: **3,544 components, 489 unlayered**. The audit’s six per-file counts reproduce at ±1 (editor-suite 659/660; all others exact).

**Owner answer (2026-10-22): APPROVED.** Proceed with a staged, pixel-diff-gated cleanup of **25–40%** of occurrences, dead rules and superseded declarations first; stop at the first unexplained visual diff. Do not exceed the approved range or remove rules without the NW-2.2 page matrix. FB-19 is unblocked.

### OD-2 — Dashboard parity subset — APPROVED

**Evidence:** `artifacts/next-work/nw-3-1/gap-matrix.md`: 60 of 67 inventory rows already exist in the rebuilt dashboard. Real gaps: row 62 poster-type branch, row 64 edit history, rows 65/66 sheets + polls panels, row 67 passkey row.

**Owner answer (2026-10-22): APPROVED — recommended subset.** Entry points for sheets/polls (links to guests/events sections), restore passkey row + poster type (cheap), document the event-role picker as intentionally absent, and add edit history only in the cheap ⋮-link variant. No panel reimplementation. FB-20 is unblocked.

### OD-3 — Push / release / version history — LOCAL COMMITS ONLY

The owner approved the existing push earlier; the branch is at `origin/…` `6f7de27`; `main` is still `50721ef`. **New answer (2026-10-22): local commits only for now.** Do not push, open a PR, merge, or tag. `VERSION_HISTORY.md` must not be edited.

**Stale docs to fix (FB-12):** `RELEASE-CANDIDATE.md` still says “Push instruction (blocked)” in one section while its top note says approved; `STATE.md` still lists OD-3 as awaiting an answer.

### OD-4 — Canvas resize handle “Equivalent” exception — CONFIRMED

The 10×10 visual handle has a 24×24 live hit box (NW-1.5, `ec0cf91`). **Owner confirmed (2026-10-22).** Close the ledger item; no code work. If a future review rejects the exception, that is a new design change, not a silent tweak.

### OD-5 — Khmer `<option>` implementation — CONFIRMED

The runtime rewrite of `<option>` text from `data-i18n-en` / `data-i18n-km`, with no custom listbox, shipped in `6a30d9e`. **Owner confirmed (2026-10-22).** Close the ledger item. FB-22 should still do the live 375 px EN/KM spot-check as evidence; if it finds a real defect, file a fix.

### OD-6 — No budget/threshold changes — UNCHANGED

Standing rule. It directly constrains:

- **FB-03:** fix the admin weight by reducing bytes, not by raising `docs/perf/lighthouse-budgets.json`.
- **FB-11:** cannot re-baseline `v14`’s style count to 2; owner chose **keep non-blocking**.
- **FB-16/17:** cannot relax canvas thresholds to get a pass.

### OD-7 — README digest pin — APPROVED Option A

**Verified hashes:**

- Pinned CRLF digest in the test: `826e19f441d63a04b16e995e9c70fad6e796f111242a35e6b91248f456a80731`
- Actual Linux LF digest: `38ce744d4e628b4003bdd58df777ca97014e32d97e7c4a8429d70900e1542f08`
- The CRLF pin is the byte-identical LF blob with `\r` inserted at each line end (`git cat-file blob HEAD:README.md | sed 's/$/\r/'`).

**Owner answer (2026-10-22): Option A.** Normalize `\r\n` → `\n` in the test’s `digest()` before hashing, pin the LF digest, add a dated platform note, and add the CRLF/LF regression test. This makes Windows and Linux agree without weakening the assertion. FB-04 is unblocked.

### OD-8 — Trusted Khmer for `feature-flags.js` — DEFERRED

The owner **deferred** translation supply on 2026-10-22. **Do not machine-translate.** Feature flags remain English for now. FB-21 stays deferred; do not start it. When the owner supplies the strings later, reconcile the actual key list against `src/js/pages/admin/feature-flags.js` and the CSV (the register says “11”; the expanded list is 14 — resolve the discrepancy), apply the owner’s Khmer byte-exactly, flip the CSV rows to `translated`, and verify at 375 px.

### 6.2 Other owner answers (2026-10-22)

- **i18n: audit first.** FB-14 builds the 305-row classification report and stops before applying translations. Do not machine-translate; finish the audit and queue any real gaps for later owner input, without asking mid-audit.
- **v14: keep non-blocking for now.** FB-11 keeps `continue-on-error`, updates the stale comments/ledger, investigates whether a real duplicate stylesheet can be removed, and does **not** change the budget or retire the step.
- **release: local commits only for now.** FB-15 runs the full matrix locally and records evidence; no push/PR/merge/tag. Revisit only when the owner explicitly changes this answer.

---

## 7. Wave 1 — Release-blocking and CI-red items

### FB-01 — Security Scan is red: Pillow 12.3.0 has 8 known CVEs

**Priority:** P0
**Type:** fix
**Owner gate:** none
**Blocks:** release, CI green, security evidence

**Evidence (verified):**
- CI run `39557451856`, Security Scan, `pip-audit` step.
- `pip-audit` reports `pillow 12.3.0` with: `CVE-2026-112395`, `CVE-2026-112397`, `CVE-2026-112400`, `CVE-2026-112404`, `CVE-2026-112895`, `CVE-2026-112896`, `CVE-2026-112897`, `CVE-2026-112899`; fixed version `13.0.0`.
- Pin: `docs/requirements-production.txt:26` → `Pillow==12.3.0`.
- The current `docs/reviews/sec-01-scan-92806ad.md` is historical; do not rewrite it. If a current status document claims Pillow 12.3.0 is clean, add a dated correction.

**Exact fix:**
1. Confirm the only production pin:
   ```bash
   grep -rn -i "pillow==" --include="*.txt" --include="*.py" . \
     --exclude-dir=node_modules --exclude-dir=.venv
   ```
   Expected: only `docs/requirements-production.txt` at HEAD. (`src/python/requirements.txt` does not exist at this HEAD; docs that reference it are historical.)
2. Bump the pin to `Pillow==13.0.0` (or the latest patched 13.x that pip-audit accepts; verify, don't guess).
3. Upgrade the test environment only:
   ```bash
   .venv/bin/python -m pip install -q "Pillow==13.0.0"
   .venv/bin/python -c "from PIL import Image; print(Image.__version__)"
   ```
4. Run the image/QR-related tests and the gates:
   ```bash
   .venv/bin/python -m pytest tests/ -q -k "image or qr or media or upload"
   python3 build.py all --check
   node tools/page-errors.mjs --all
   ```
   If no test names match, run the full suite (expected 142/1 until OD-7 is fixed; the Pillow change must not add failures).
5. Verify the advisory set with a clean audit:
   ```bash
   python3 -m venv /tmp/opencode/pipaudit-venv
   /tmp/opencode/pipaudit-venv/bin/pip install -q pip-audit
   /tmp/opencode/pipaudit-venv/bin/pip-audit -r docs/requirements-production.txt
   ```
   Acceptance: no high/critical findings for the packages in this file. If pip-audit reports an unrelated issue, record it and do not expand scope without owner approval.
6. Record evidence in `artifacts/next-work/fb-01/` (audit before/after, commands, test log).

**Acceptance criteria:**
- [ ] `docs/requirements-production.txt` pins a patched Pillow.
- [ ] `pip-audit -r docs/requirements-production.txt` reports no high/critical findings.
- [ ] Full suite has no new failures; image/QR paths work.
- [ ] No other requirements file still pins 12.3.0.
- [ ] Evidence file with before/after audit output.
- [ ] A CI Security Scan re-run is **NOT RUN** in this local-only pass (no push); local `pip-audit` is the evidence, and remote CI verification is explicitly deferred.

**Do not:**
- Do not dismiss the CVEs as “dev-only”; Pillow is a production dependency.
- Do not run `pip install --upgrade` into the system Python.
- Do not edit the historical scan report to make it look like it predicted this; add a dated addendum.
- Do not touch budgets or tests.

**Commit:** `fix(security): bump Pillow to 13.0.0 for CVE-2026-112395…`

---

### FB-02 — Performance Budgets red: LHCI cannot determine `staticDistDir` (and artifacts go to the wrong path)

**Priority:** P0
**Type:** fix
**Owner gate:** none (do not change assertions/thresholds)
**Blocks:** CI green, performance evidence, release

**Evidence (verified):**
- CI run `39557451848`, Performance Budgets, step `npx --yes @lhci/cli@0 autorun` → `Error: Failed to automatically determine staticDistDir`.
- `tools/lighthouserc.js` defines `collect.url` for 16 routes, `chromePath` resolution, `budgetsFile`, and `upload.outputDir: './.lighthouseci/reports'`, but **no** `collect.staticDistDir` and **no** `collect.startServerCommand`.
- `package.json` has no `scripts.serve:lhci`; Lighthouse CI’s `autorun` auto-detection therefore cannot find a build directory or a server command.
- `src/python` is not one of Lighthouse CI’s conventional build-dir names; setting `staticDistDir` to it would serve uncompressed files and make the byte budgets meaningless (the repo’s own config comments say only `tools/serve-gzip.py` reproduces the numbers).
- The workflow uploads `path: docs/reviews/lighthouse`, but the config writes reports to `.lighthouseci/reports`; with `if-no-files-found: ignore`, debugging artifacts are silently empty.
- Local `npx lhci assert` passes because it consumes existing reports; that is **not** proof that `autorun`/`collect` works from a clean checkout. The CI failure is at the collect layer.

**Root cause:** `autorun` needs either a `staticDistDir` or a server command (for example a `serve:lhci` package script). The repo deliberately needs the gzip server, so the server-command route is the correct one; a plain static dir would invalidate the gate.

**Recommended fix (choose one, verify both CI and local):**

**Option A — `serve:lhci` package script (idiomatic Lighthouse CI):**
1. Add to `package.json`:
   ```json
   "scripts": {
     "serve:lhci": "python3 tools/serve-gzip.py --port 8124"
   }
   ```
   `autorun` will use this as the server command. Confirm the exact ready signal; if `autorun` waits for the URL, the health of `/` on 8124 is enough.
2. `tools/reproduce.sh` currently starts the static server itself before running LHCI. If LHCI now starts its own server on 8124, the pre-started one causes a port conflict. Adjust reproduce so LHCI owns the server for its step, then start the server again for the later determinism/report steps. Do not leave a duplicate or an orphan.
3. Run from a clean state:
   ```bash
   rm -rf .lighthouseci
   npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js
   ```
   Verify 16 URLs collected, 16/16 a11y 1.00, assertions pass, and the measured byte counts match the gzip baseline.

**Option B — config server command:**
1. Add to `collect` in `tools/lighthouserc.js`:
   ```js
   startServerCommand: 'python3 tools/serve-gzip.py --port 8124',
   startServerReadyPattern: 'gzip enabled', // verify against serve-gzip output
   ```
2. Resolve the same reproduce port conflict as Option A, or use a CI-only config (e.g. `tools/lighthouserc.ci.js`) that extends the base config with the server command. The repo intentionally keeps one config; if you add a second, document why and make the distinction impossible to miss.
3. Verify exactly as in Option A.

**Also fix in the same item:**
- Workflow artifact path: `docs/reviews/lighthouse` → `.lighthouseci/reports`; set `if-no-files-found: error` (or at least `warn`) so an empty upload is visible.
- Update the stale workflow comments: the repo-root forwarder is no longer truncated (the v14 test executed and failed on style count, not import), and the v14 cause is `editor/index.html styles 2 > 1`, not the old weight ceilings. Link to FB-11.
- Do not add `continue-on-error` to layer 3b; it is the gate that caught the CI failure.

**Acceptance criteria:**
- [ ] From a clean checkout (`rm -rf .lighthouseci`), `npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js` collects 16 URLs and exits 0.
- [ ] No un-gzipped server is used; byte budgets match the baseline.
- [ ] `tools/reproduce.sh` still works and does not start two servers on 8124.
- [ ] A CI Performance Budgets re-run is **NOT RUN** in this local-only pass; the local clean run must be green and the generated report artifact non-empty.
- [ ] No assertion/budget changes (OD-6).
- [ ] Evidence: local clean-run log, local report/artifact listing, and an explicit “CI re-run deferred” note.

**Do not:**
- Do not set `collect.staticDistDir: 'src/python'` and call it done; that serves uncompressed bytes and can make budgets pass/fail for the wrong reason.
- Do not delete `tools/lighthouserc.js` assertions or move the goalposts.
- Do not use `lhci assert` alone as CI proof; it does not collect.
- Do not run against the dev server (different HTML) when the gate expects the static build.

**Commit:** `fix(ci): give Lighthouse CI a gzip server and upload the real reports`

---

### FB-03 — `v55` regression: admin route is 716 bytes over budget

**Priority:** P0
**Type:** fix
**Owner gate:** OD-6 (do **not** raise the budget)
**Blocks:** merge/release; CI layer 3a would fail on this branch

**Evidence (verified):**
- `python3 tests/v55_route_weight_budget_test.py` →
  `admin.html: script 163,532 B exceeds budget 162,816 B (159 KB) by 716 B`.
- `src/js/bundle-admin.js` grew from 154,044 B at `50721ef` to 155,394 B at HEAD (**+1,350 B**). CSS is unchanged.
- The growth comes from `6a30d9e` (NW-4.1), which injected the `applyOptionLabels` helper and its calls into `src/js/core/i18n.js`, so the build propagates it into **every** route bundle.
- CI layer 3a passed at `50721ef`; the branch push did not run CI, so this is branch-introduced and currently invisible to CI.
- The budget file is frozen under OD-6. The failing test names the route and the exact overage; use it as the oracle.

**Recommended fix (in order of preference):**

**A. Move the option-label helper out of the shared core and load it only where `<option>` rewriting is needed.**
- Create a small page-scoped module (e.g. `src/js/i18n-options.js`) containing the helper, and include it in the route sources that actually render localized `<option>` elements (materials/responses, and any other page verified to need it).
- Remove the full helper from `src/js/core/i18n.js`.
- Keep the locale-change hook safe on pages that do **not** load the module: guard the call (`if (typeof EInviteI18n.applyOptionLabels === 'function') …`) or move the calls into the page-scoped module. The guard costs a few bytes; the helper definition is the large win.
- Wire the new source through `build.py`/route-bundle config, run `build.py bundles --check`, and confirm the generated bundles are consistent.
- This should remove roughly the 1,350 B that was added; admin then passes with ~634 B headroom. Verify the exact bytes; do not assume.

**B. If moving is too invasive, shrink the shared helper while preserving behavior.**
- Measure the added lines first: `git diff 50721ef..HEAD -- src/js/core/i18n.js src/js/bundle-admin.js`.
- Remove only comments/whitespace/duplicated selectors, not behavior. Rebuild and re-measure. This is acceptable only if the resulting admin bundle is ≤162,816 B and the live label check still passes.

**C. Remove unrelated dead admin JS bytes ≥716 B** only if A/B fail and the removal is provably dead. This is riskier; do not use it as an excuse to touch budgets.

**Verification:**
```bash
python3 tests/v55_route_weight_budget_test.py
python3 build.py all --check
python3 build.py bundles --check
node tools/page-errors.mjs --all
# Live label check at 375 px in EN and KM, for every page that renders <option>:
.venv/bin/python tools/option_labels_i18n_check.py   # or the harness documented in NW-4.1
```
Then run the full suite (still 142/1 until FB-04; no new failures).

**Acceptance criteria:**
- [ ] `v55` passes with the original budget and the original assertion.
- [ ] Admin bundle is ≤162,816 B; record the exact before/after bytes.
- [ ] Materials/responses/account pages still translate `<option>` labels in EN and KM at 375 px.
- [ ] Build/bundles/smoke pass; no visual regressions on the affected pages.
- [ ] No budget file, threshold, or generated bundle is hand-edited; the build regenerates consistently.
- [ ] Evidence: diff, byte counts, v55 output, live check.

**Do not:**
- Do not raise the 159 KB budget or change the test to “warn”.
- Do not hand-edit `src/js/bundle-admin.js`; it is generated and will be overwritten.
- Do not remove the i18n call without replacing the behavior; OD-5 is already shipped and must keep working.
- Do not claim the branch is CI-green; the layer 3a re-run is deferred until a future push.

**Commit:** `fix(bundles): keep the admin route inside the frozen weight budget`

---

### FB-04 — Full suite is red on Linux: OD-7 README digest pin

**Priority:** P0
**Type:** fix (test harness)
**Owner gate:** **OD-7 APPROVED — Option A (2026-10-22)**. Implement now; no further answer needed.
**Blocks:** green full suite, release evidence, NW-5.1 verification

**Evidence (verified):**
- `tests/v27_3_5_release_evidence_test.py::test_release_evidence` fails with:
  `'38ce744d…' == '826e19f4…'`.
- The pinned constant is the CRLF digest; Linux reads LF bytes. The test reads raw bytes, so the same content hashes differently.
- CRLF pin: `826e19f441d63a04b16e995e9c70fad6e796f111242a35e6b91248f456a80731`
- LF digest: `38ce744d4e628b4003bdd58df777ca97014e32d97e7c4a8429d70900e1542f08`
- The CRLF value is the LF blob with `\r` appended per line; content is byte-identical after normalization.
- The test was frozen for NW-5.1 until OD-7 was answered; **OD-7 is now approved**, so this file may be edited.

**Approved fix (Option A — platform-neutral normalization):**
1. Normalize line endings before hashing, then pin the LF digest:
   ```python
   def digest(path: Path) -> str:
       data = path.read_bytes().replace(b"\r\n", b"\n")
       return hashlib.sha256(data).hexdigest()

   README_SHA = "38ce744d4e628b4003bdd58df777ca97014e32d97e7c4a8429d70900e1542f08"
   ```
   Keep reading whole-file bytes (the README is small). Do not use text mode with platform newline translation without understanding it; explicit byte normalization is testable.
2. Add a dated comment: “CRLF and LF renderings normalize to this digest; verified 2026-10-22.”
3. Add a tiny regression test (same file or a unit test) that writes a CRLF temp file and an LF temp file with identical text and asserts `digest()` returns the same value. This prevents a future “repin” from reintroducing the platform split.
4. Run:
   ```bash
   .venv/bin/python -m pytest tests/v27_3_5_release_evidence_test.py -q
   .venv/bin/python -m pytest tests/v27_3_5_release_evidence_test.py -q -s
   .venv/bin/python -m pytest tests/ -q
   ```
   Expected after the fix: the targeted test passes in both capture modes; the full suite is 143 passed once FB-09 is also clean. Until FB-09 is fixed, the analytics readiness flake may still produce 142/1 on a bad run; do not count that as an OD-7 failure.

**Alternative (Option B — not chosen):** repin to LF and skip on Windows with a dated reason. This is weaker; it stops checking the digest on the platform that produced the original pin and creates a permanent “skip” in release evidence. The owner chose Option A on 2026-10-22.

**Acceptance criteria:**
- [ ] Default-capture pytest passes the release-evidence test on Linux.
- [ ] `-s` also passes; no capture-mode folklore.
- [ ] The CRLF/LF normalization test passes.
- [ ] The digest still matches the real README; the assertion is not removed or weakened.
- [ ] OD-7 is recorded in `DECISIONS.md`/`OPEN-ITEMS.md` by FB-12 with the chosen option and date.
- [ ] Evidence: before/after failure, both hashes, test outputs.

**Do not:**
- Do not change `README.md` or its line endings just to satisfy the test.
- Do not delete the digest assertion or catch the failure.
- Do not combine this with FB-05 in one commit; they are different defects in the same test.
- Do not switch to Option B, skip Windows, or skip the test; the owner approved Option A.

**Commit:** `test(release): normalize README line endings before digest pinning (OD-7)`

---

### FB-05 — NW-5.1: child-process failure under pytest fd capture

**Priority:** P1
**Type:** fix (test harness)
**Owner gate:** none (after FB-04; OD-7 is approved, so the test is no longer frozen)
**Blocks:** reliable default-capture suite

**Evidence:**
- `tests/v27_3_5_release_evidence_test.py:72` spawns three build checks:
  ```python
  subprocess.run([sys.executable, str(ROOT/cmd[0]), *cmd[1:]], check=True, cwd=ROOT)
  ```
- No `stdout`/`stderr`/`capture_output` is set. Under pytest’s default fd capture, the child can inherit unusable standard handles and exit 1. It passes with `-s` / `--capture=sys`.
- The current OD-7 digest failure masks whether this still reproduces. Fix OD-7 first, then test this specifically.
- The prior pass hardened the same class of WinError-50 path in `canvas_motion_contract_test.py`; this test remains open.

**Fix at the harness boundary:**
- Pass explicit handles, for example:
  ```python
  result = subprocess.run(
      [sys.executable, str(ROOT / cmd[0]), *cmd[1:]],
      cwd=ROOT,
      text=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      check=False,
  )
  if result.returncode != 0:
      raise AssertionError(
          f"{cmd[0]} failed ({result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
      )
  ```
  `subprocess.DEVNULL` is acceptable if the output is not needed, but explicit output makes future failures diagnosable. Do not add `-s` to the test command or pytest config.

**Acceptance criteria:**
- [ ] `pytest tests/v27_3_5_release_evidence_test.py -q` passes under default capture.
- [ ] `pytest … -q -s` also passes.
- [ ] A deliberately failing child produces a useful assertion with stdout/stderr, not a silent exit.
- [ ] No assertion content in the test is weakened.
- [ ] Full suite has no new failures.

**Do not:** change the child commands’ semantics; suppress the failure; mark the test `xfail`/`skip`.

**Commit:** `test(release): capture child build output in the release-evidence test (NW-5.1)`

---

### FB-06 — `make test` and `make reproduce` use the wrong Python; failures can be non-fatal

**Priority:** P0
**Type:** fix (developer/CI ergonomics)
**Owner gate:** none
**Blocks:** trustworthy local reproduction; release evidence

**Evidence (verified):**
- `Makefile:12` → `PYTHON ?= python3`; `Makefile:37-38` → `test: $(PYTHON) -m pytest tests/`.
- On this machine, `python3 -m pytest tests/ --collect-only -q` → **143 tests collected, 6 errors** (`ModuleNotFoundError: No module named 'playwright'`) for:
  `tests/ui_smoke_test.py`, `tests/v0_52_ai_live_browser_test.py`, `tests/v0_52_autosave_status_test.py`, `tests/v0_52_dashboard_cover_navigation_test.py`, `tests/v0_52_publish_autosave_barrier_browser_test.py`, `tests/v17_served_editor_test.py`.
- `.venv/bin/python -m pytest tests/ --collect-only -q` → **143 tests collected, 0 errors**.
- `tools/reproduce.sh` picks the interpreter running the script if it already has pytest (it does), so it chooses `python3` and inherits the six errors. The test step reports failures without making the overall reproduction fail; this is exactly how a red suite can look “reproduced”.
- `tools/run-gates.py` already prefers `.venv/bin/python` for pytest; the Makefile/reproduce path is the inconsistent one.

**Fix:**
1. Make the test target prefer `.venv`:
   ```make
   TEST_PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(PYTHON))
   test:
   	$(TEST_PYTHON) -m pytest tests/
   ```
   Keep build/lint targets on `PYTHON` if they don’t need Playwright. Document the override (`make test TEST_PYTHON=python3`).
2. In `tools/reproduce.sh`, prefer `.venv/bin/python` when it has **pytest and Playwright**, not merely pytest:
   ```bash
   if [ -x "$TEST_VENV/bin/python" ] && \
      "$TEST_VENV/bin/python" -c 'import pytest, playwright' >/dev/null 2>&1; then
     PYTEST_PY="$TEST_VENV/bin/python"
   elif python3 -c 'import pytest, playwright' >/dev/null 2>&1; then
     PYTEST_PY=python3
   else
     # create/install the test venv, or exit with an explicit instruction
   fi
   ```
3. Make test failures fatal by default. If a non-fatal mode is useful for triage, add an explicit opt-in flag (e.g. `--allow-test-failures`) and make the default exit non-zero. A “reproduce” that exits 0 with a red suite is worse than no reproduce.
4. Update comments/docs (`Makefile`, `tools/reproduce.sh`, `README`/`CONTRIBUTING`) to state the interpreter requirement and the `make test` behavior.

**Acceptance criteria:**
- [ ] `make test` on this machine collects 143 tests, 0 collection errors, and runs them; it fails only on real failures (OD-7 until fixed, then green).
- [ ] `make reproduce` uses the test venv, and exits non-zero if pytest fails or collection errors occur.
- [ ] A fresh machine without Playwright gets a clear install instruction, not six opaque import errors.
- [ ] `tools/run-gates.py` remains consistent with the same interpreter policy.
- [ ] Evidence: before/after collect + run logs, exit codes.

**Do not:** install Playwright into system Python; hide browser tests; make `reproduce` always green; remove the six browser tests.

**Commit:** `fix(test): use the Playwright-capable venv and fail reproduction on test failures`

---

### FB-07 — CI never runs pytest; branch work is untested

**Priority:** P0
**Type:** fix (CI)
**Owner gate:** none
**Blocks:** knowing whether the suite is green before a future merge; branch coverage

**Evidence:**
- `.github/workflows/` contains only `lighthouse.yml` and `security.yml`; there is no pytest/test workflow.
- `lighthouse.yml` triggers on push to `main` and PRs to `main` (plus dispatch); `security.yml` triggers on push to `main`/`v54-refactor-security-ui`, PRs to `main`, weekly schedule, and dispatch.
- Pushing `pass/2026-10-21-next-work` produced no CI run; the branch’s v55 regression and OD-7 failure have never been seen by CI.
- CI would need Playwright browsers installed; a naive pytest job would hit the same six collection errors.

**Fix: add `.github/workflows/tests.yml`:**
- Triggers: `pull_request` to `main`, `push` to `main`, `workflow_dispatch`. (Optionally push to `pass/**` while this branch is active, but PR coverage is the durable answer.)
- `ubuntu-latest`, Python 3.12, pip cache.
- Install production + test requirements in a venv (or use `pip install -r docs/requirements-test.txt`; verify it includes the app deps and Playwright).
- Install Chromium for Playwright:
  ```bash
  python -m playwright install --with-deps chromium
  ```
- Run, with `PYTHONIOENCODING=utf-8`:
  ```bash
  python -m pytest tests/ -q
  python tests/v55_route_weight_budget_test.py
  ```
  Add `python build.py all --check`, `python build.py bundles --check`, and the smoke check if they are not already covered by another workflow.
- `v14` is known red; the owner chose **keep non-blocking for now** (2026-10-22). Do **not** add it as a blocking step. Either omit it, or run it with `continue-on-error: true` and upload the log, explicitly labeled non-blocking/aspirational. See FB-11.
- Upload pytest output/logs on failure (`.pytest_cache` is not enough; capture the command output to a file).
- Bump stale action versions while here (checkout/setup-python/upload-artifact) to clear Node 20 deprecation warnings; do not change behavior.
- Cache Playwright browsers keyed on the Playwright version; keep the workflow under ~15 minutes.

**Acceptance criteria:**
- [ ] The workflow file exists and is locally validated to use a Playwright-capable interpreter; the exact pytest/v55 commands pass locally.
- [ ] An actual PR/`workflow_dispatch` run is **NOT RUN** in this local-only pass and is explicitly deferred until a future push; do not invent a run URL.
- [ ] The job definition does not wrap pytest/v55 in `continue-on-error`, so it will fail on a real regression.
- [ ] Triggers include branch pushes/PRs (config check), not only `main`.
- [ ] No secrets are required; browser tests use their local fixtures.
- [ ] `v14` is either absent or explicitly non-blocking with a link to the 2026-10-22 owner answer and FB-11.
- [ ] Evidence: workflow diff, local command output, timing/cache documentation; no fabricated run URL.

**Do not:** add `continue-on-error` to pytest; skip browser tests; run against a system Python without installing dependencies; make the workflow depend on the local `.venv`; add a red v14 gate as if it were green.

**Commit:** `ci: run the real pytest suite (with Playwright) on PRs and main`

---

### FB-08 — 226 zero-test files and the budget gates are invisible to pytest/run-gates

**Priority:** P1
**Type:** fix (test inventory)
**Owner gate:** none (but do not convert all 226 files in one pass)
**Blocks:** trustworthy “full suite green” claim; v55/v14 enforcement

**Evidence (verified):**
- 261 files match `tests/*_test.py` or `tests/test_*.py`; **226 contain no `def test_`**.
- Only **12** are listed in `COLLECT_IGNORE` in `tests/conftest.py`; the other 214 are imported and run zero tests (many are intentional manual runner scripts; that is not obvious to a reader).
- `python3 tests/v55_route_weight_budget_test.py` and `python3 tests/v14_performance_budget_test.py` are zero-`def test_` scripts; pytest never executes their assertions.
- CI’s Performance workflow does run v55 (layer 3a) and v14 (layer 2, `continue-on-error`), but only on `main`/PR triggers; this branch’s push did not trigger it.
- `tools/run-gates.py` phases are `build → bundles → smoke → pytest → lhci → canvas`; they omit `v55` and `v14`. `--phase all` would not catch the current admin regression.
- The `v27` test’s own docstring documents this exact failure mode: without a `test_` entry point, the module was imported, called nothing, and reported zero tests.

**Fix (scoped, safe):**
1. Create a manifest (e.g. `tests/runner-manifest.json` or `tests/RUNNERS.md`) listing every zero-`def test_` file with:
   - purpose,
   - invocation command,
   - whether it is a manual runner, a gate, or obsolete,
   - `checked_by` (CI workflow / run-gates phase / none),
   - owner if intentionally deferred.
2. Add `tests/test_runner_manifest.py`:
   - enumerate all zero-`def test_` files (same glob as above);
   - assert each is either in `COLLECT_IGNORE` or in the manifest;
   - assert every manifest entry exists;
   - assert every entry marked `checked_by: gate` is actually wired into `tools/run-gates.py` or CI;
   - fail with a readable list when a new zero-test file appears without a manifest entry.
3. Wire the real budget gates:
   - Add a `budgets` phase to `tools/run-gates.py` that runs `python3 tests/v55_route_weight_budget_test.py` (blocking).
   - Keep `v14` separate and non-blocking per the 2026-10-22 owner answer; label it `aspirational` in the phase list or omit it from `--phase all`. Do not silently call `--phase all` green while v14 is red unless the output states the non-blocking disposition.
   - Update `tools/README`/`NEXT-WORK-TASK` commands so there is one obvious “run everything” command.
4. Do not convert 214 scripts to pytest tests in this item; classify them. A follow-up can convert the high-value ones.

**Acceptance criteria:**
- [ ] Every zero-test file is either in `COLLECT_IGNORE` or the manifest; the manifest test passes.
- [ ] A newly added zero-test file without a manifest entry fails the test.
- [ ] `tools/run-gates.py --phase all` includes v55 and fails on the current 716 B regression; after FB-03 it passes.
- [ ] v14’s status is explicit: non-blocking/aspirational per the 2026-10-22 owner answer.
- [ ] The 12 `COLLECT_IGNORE` entries remain justified; no mass-ignore.
- [ ] Evidence: file counts, manifest coverage, run-gates output before/after.

**Do not:** add 226 ignores; delete runner scripts; rename test files; claim “full suite” means all 261 files ran; change v14/v55 assertions.

**Commit:** `test(infra): make zero-test runners and budget gates explicit`

---

### FB-09 — Intermittent full-suite failure: app server not ready within 12 s

**Priority:** P1 (release-blocking for repeatability)
**Type:** fix (test harness)
**Owner gate:** none
**Blocks:** the “suite passes the same way twice” acceptance; NW-5.2 closure

**Evidence (verified):**
- Run 2 of the full suite: **141 passed, 2 failed** in 4:54. The new failure:
  `tests/analytics_privacy_test.py::test_phase4_public_privacy_page`
  → `RuntimeError: Server did not become ready: http://127.0.0.1:58621/api/health: <urlopen error [Errno 111] Connection refused>`
- Traceback goes through `tests/v14_test_utils.py:75` (`app_server`) and `tests/v14_test_utils.py:20` (`wait_http`, 12 s timeout).
- Captured server log tail only shows the startup banner (`E-invitation-website: …`, `Data directory: …`); no traceback. The process was still not serving `/api/health` after 12 s.
- Isolated rerun: `pytest tests/analytics_privacy_test.py::test_phase4_public_privacy_page -q` → **1 passed in 4.85 s**.
- The failure occurred on the second back-to-back full run (after a 4:26 run), which suggests CPU/startup contention, port reuse, or a leftover process, not a wrong privacy assertion.
- `app_server` uses `free_port()` (bind to port 0, close), then starts `server.py`, redirects output to `server-test.log`, and waits 12 s. `free_port()` has a TOCTOU race, and the harness does not check `process.poll()` during the wait.

**Required work:**
1. Reproduce on demand: run the full suite twice back-to-back (or run the analytics module after the heavy browser modules). Capture the server log, `process.poll()`, and the bound port.
2. Harden `wait_http`/`app_server`:
   - check whether the child exited and include its log immediately, instead of waiting the full timeout;
   - increase the readiness ceiling to a realistic value for loaded CI (e.g. 30 s) **only as a safety margin**, not as the sole fix;
   - if the port is seized between `free_port()` and bind, retry on a new port;
   - ensure teardown kills the whole process group and leaves no server/Chromium orphans;
   - keep the per-test timeout bounded and the failure message actionable.
3. Check for leaked processes from previous runs:
   ```bash
   pgrep -af 'src/python/server.py'
   pgrep -af 'chrom(e|ium)|playwright'
   ```
   Do not kill the owner’s browser; inspect before acting.
4. If the root cause is a real server startup hang (e.g. DB init), fix the server or the fixture; do not mask it with a longer sleep.

**Acceptance criteria:**
- [ ] The analytics privacy test passes in isolation and after the full suite, repeatedly.
- [ ] Five consecutive full-suite runs (or the agreed repeat count) show no server-readiness failures. Before FB-04, OD-7 is the only allowed known red; after FB-04, there should be no known red left from this cluster.
- [ ] On failure, the harness prints the child log, exit code, and port; no silent 12 s wait.
- [ ] No orphan servers/Chromium after the suite.
- [ ] Evidence: failing run log, isolated pass, hardened run logs, process check.

**Do not:** simply change 12 s to 60 s and declare victory; suppress the test; add retries inside the test without fixing the fixture; kill unrelated processes.

**Commit:** `test(infra): make app-server readiness deterministic under full-suite load`

---

### FB-10 — Six Dependabot alerts (npm dev/transitive)

**Priority:** P1
**Type:** dependency hygiene
**Owner gate:** none for the recommended removal; do **not** dismiss no-fix advisories — leave them open and document them
**Blocks:** security-alert zero; not the runtime release, but it is a visible repo-health red

**Evidence:** see §2.3 for the exact six alerts and chains. All are development/transitive dependencies under `@lhci/cli`; the two `extract-zip` high alerts and the `sprintf-js` medium alert have **no fixed release**; `tmp` and `uuid` do. `@lhci/cli` is already at the latest 0.15.1.

**Recommended fix (removes all six chains):**
1. Remove `@lhci/cli` from `package.json` **devDependencies** and refresh the lockfile:
   ```bash
   npm uninstall --save-dev @lhci/cli
   # or edit package.json, then: npm install --package-lock-only
   ```
   All six chains terminate at `@lhci/cli`; removing it should remove `sprintf-js`, the nested `lighthouse`/`puppeteer-core`/`@puppeteer/browsers`/`extract-zip`, `tmp`, and `uuid` from the lockfile.
2. Replace local/CI invocations with an explicitly pinned `npx` command (the workflow already does this):
   ```bash
   npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js
   ```
   Add an npm script if useful (`"lhci": "npx --yes @lhci/cli@0.15.1"`). Pin the version; do not use `@0` in scripts you control.
3. Update `tools/reproduce.sh` preflight: it currently requires `node_modules/@lhci/cli` and will fail after removal. Either require `npx`/network and skip the directory check, or check a pinned cache. Update the comment.
4. Verify the lockfile and audit:
   ```bash
   npm ls @lhci/cli sprintf-js extract-zip tmp uuid --all
   npm audit --audit-level=moderate
   npx --yes @lhci/cli@0.15.1 --version
   ```
   Then run the LHCI gate once (FB-02) to prove the tool still works from `npx`.
5. A lockfile change only closes GitHub alerts after it is eventually pushed; **this pass is local-only**, so the alerts may remain open. Record the before/after local audit and state that closure is deferred until a future push. Do not dismiss an alert without a dated owner sign-off; do not block the rest of the work on the remote alert state.

**Alternative if removing `@lhci/cli` is rejected:**
- Add npm `overrides` for `tmp` (≥0.2.6) and `uuid` (11.1.1); verify LHCI still runs.
- `sprintf-js` and `extract-zip` have no fixed release; leave those alerts open with a written risk note: development-only, not shipped, only processes trusted tooling inputs, no runtime exposure. Do not dismiss them without owner sign-off and do not call them “fixed”.
- Do not run `npm audit fix --force`; it downgrades `@lhci/cli` to 0.1.0 and breaks the gate.

**Acceptance criteria:**
- [ ] `npm ls` shows the vulnerable chains gone locally (or only documented no-fix advisories remain, with rationale).
- [ ] `npm audit` drops the high/critical findings attributable to `@lhci/cli`; the exact before/after counts are recorded.
- [ ] LHCI still runs via a pinned `npx` command; `tools/reproduce.sh` no longer requires `node_modules/@lhci/cli`.
- [ ] GitHub alert state is recorded; closure is explicitly deferred until a future push, and no alert is dismissed without owner sign-off.
- [ ] No runtime dependency was removed; `puppeteer-core` stays if the tools use it.
- [ ] Evidence: lockfile diff, `npm ls`, audit, LHCI run, alert URLs/status.

**Do not:** commit `node_modules`; dismiss a high alert without owner sign-off; remove `puppeteer-core` blindly; trust `npm audit`’s 17-count as the release metric.

**Commit:** `chore(deps): drop the vulnerable Lighthouse CLI tree and pin npx usage`

---

## 8. Wave 2 — Durability, truth-up, and verification

### FB-11 — `v14` is a known-red gate with stale comments; decide, don’t fudge

**Priority:** P2
**Type:** decision/docs (OD-6)
**Owner gate:** **OD-6 — answered 2026-10-22: keep v14 non-blocking for now.** Do not retire the step; do not change the budget.
**Blocks:** a truthful CI signal; not release-blocking because it stays explicitly quarantined

**Evidence:**
- `tests/v14_performance_budget_test.py` fails: `('editor', 'index.html', 'styles', 2, 1)` — 2 stylesheets against a budget of 1.
- `.github/workflows/lighthouse.yml` runs it with `continue-on-error: true` and a comment that blames a truncated repo-root forwarder (76 B) and three routes exceeding weight ceilings. The v14 failure actually executed and failed on **style count**; the forwarder is no longer the blocker (it is ~1.5 KB and imports/runs). The comment is stale and misleads the next agent.
- `tools/lighthouserc.js` already removed resource-count assertions for the same kind of reason; v14 still carries an aspirational count that is known unsatisfiable.
- OD-6 forbids changing the budget.

**Work:**
1. Inspect `editor/index.html` and the built page: are the two stylesheets genuinely required (e.g. base + theme/deferred), or is one a duplicate? If a duplicate can be removed with no visual/perf regression, fix the code; then v14 may pass without touching the budget. This is still worth doing, but it does **not** change the owner’s gating decision.
2. Keep the gate **non-blocking** as instructed: leave `continue-on-error: true` in place for now. Do not retire the step, do not delete the test, and do not change `styles: 1`.
3. Produce a one-page decision note:
   - what the gate measures and why the count is aspirational;
   - evidence that the two styles are intentional (or that one was a duplicate and was fixed);
   - the owner answer: **keep non-blocking for now (2026-10-22)**;
   - what would remove `continue-on-error` later (a real duplicate fix plus a new explicit owner decision);
   - link to `docs/reviews/optimisation-report.md` and OD-6.
4. Update the workflow comments to match reality: remove the truncated-forwarder claim, state the actual `styles 2 > 1` cause, state the quarantine date/owner, and say what would remove `continue-on-error`.

**Acceptance criteria:**
- [ ] v14 remains explicitly non-blocking with `continue-on-error: true`; the owner’s 2026-10-22 answer is recorded.
- [ ] If a real duplicate stylesheet is found, it is fixed without a budget change; the gate still stays non-blocking for now.
- [ ] Workflow comments no longer claim the forwarder is truncated or that weight ceilings are the current cause.
- [ ] No budget/threshold change without OD-6 approval.
- [ ] `RELEASE-CANDIDATE.md` and `docs/reviews/optimisation-report.md` agree with the disposition.
- [ ] Evidence: HTML inspection, before/after v14 output, decision note.

**Do not:** change `styles: 1` to `2`; mark the step green by removing the assertion; retire the step; leave the stale comment in place.

**Commit:** `docs(ci): document the v14 non-blocking decision accurately`

---

### FB-12 — Documentation truth-up cluster

**Priority:** P1
**Type:** docs
**Owner gate:** none (but do not rewrite frozen/historical docs)
**Blocks:** none technically; prevents the next agent from repeating work or trusting false state

**This is one item because the contradictions share a cause: the ledgers were written before the last commits/push.**

**Required corrections (verify each before editing):**

1. **`docs/a11y/WCAG-2.2-AA-AUDIT.md`** — the intro/§5 still says the six findings were “not applied here” / “none applied”, but `ec0cf91` shipped all six, plus `ca53dbe` (gradient AA) and `11e549f` (toolbar reachability). Update the status column with the commit/date and add a change-history entry. Keep the audit measurements and the original findings; do not erase history.
2. **Wrong frozen-file path** — `NEXT-WORK-TASK.md:89`, `docs/STATUS-INDEX.md:18`, and `artifacts/ui-audit/fixes/STATE.md:46` say `docs/CANVAS-SMOOTHNESS-BRIEF.md`; the real file is **`docs/CANVA-SMOOTHNESS-BRIEF.md`**. Fix the references only; never create/rename the frozen file.
3. **`RELEASE-CANDIDATE.md`** — the top says OD-3 push approved, but the push section still says “blocked”. Update to: branch pushed at `6f7de27`; `main` still `50721ef`; **new work uses local commits only — no push/PR/merge/tag**; no tag/version-history edit. Add the current v55 result and v14 non-blocking status to the gate matrix; record the actual full pytest row (target 143/0 after FB-04/FB-09; if a failure remains, state it precisely — do not write PASS prematurely). The “GATES_PASSED” claim must be scoped to the phase actually run (`--phase build`), not all gates.
4. **`docs/STATUS-INDEX.md`** — code HEAD `11e549f` / docs HEAD `8d256e3` are stale; final HEAD is `6f7de27`. Add the new work order to the index. Fix the wrong canvas path.
5. **`artifacts/ui-audit/fixes/STATE.md`** — header still points at `50721ef`; line ~82 labels the allowlist race as “NW-5.2” (NW-5.2 is the rate-limit/analytics order issue; the allowlist race was fixed separately). Line ~102 still lists OD-3 as awaiting an answer. Update the header to `6f7de27`, separate NW-5.x items, mark OD-3 answered, and record OD-1/2/7 approved, OD-4/5 confirmed, OD-8 deferred.
6. **`artifacts/next-work/00-baseline/OPEN-ITEMS.md`** — statuses are stale: NW-1.x, NW-3.1, NW-4.1, NW-6.3/6.4/6.5/6.6 are not all “OPEN”; OD-1/2/7 now have answers, OD-3/4/5 have answers/confirmations, and OD-8 is deferred; the allowlist failures are fixed. Reconcile every row against the commits and add “last reconciled 2026-10-22”. Do not mark NW-5.2 closed until FB-13’s evidence is in.
7. **`.github/workflows/lighthouse.yml`** — stale comments described in FB-11; update alongside the v14 note. The artifact path is fixed in FB-02.
8. **Security status docs** — if any current doc claims Pillow 12.3.0 is clean, add a dated correction; do not rewrite historical `sec-01`/`sec-04` review reports.
9. **New work order index** — add `FREEBUFF-OPEN-ISSUES-2026-10-21.md` to `docs/STATUS-INDEX.md` with status “active work order, approved 2026-10-22” and the owner-answer summary (OD-1/2/7 approved, OD-4/5 confirmed, OD-8 deferred, local-only release).
10. **Link check** — run the repo link checker if one exists (`scripts/check-links.py` or equivalent) and fix only the paths this item touched.

**Acceptance criteria:**
- [ ] No current doc says the six a11y asks are unapplied.
- [ ] All references to the canvas brief use `CANVA-SMOOTHNESS-BRIEF.md` (or a correct relative path).
- [ ] No current doc says the push is blocked or the branch is unpushed.
- [ ] HEAD fields match `6f7de27` (or the new work branch HEAD if this runs later).
- [ ] OPEN-ITEMS statuses match commits; no closed item is marked open, no open item marked done without evidence.
- [ ] Historical review docs are addended, not rewritten.
- [ ] Link check passes; no frozen file edited.

**Do not:** edit `docs/CANVA-SMOOTHNESS-BRIEF.md`; edit `VERSION_HISTORY.md`; change dates to hide drift; mark verification items done because a doc says so.

**Commit:** `docs: reconcile the ledgers with 6f7de27 and the real gate results`

---

### FB-13 — NW-5.2: the cited test does not exist, and three-run proof is not met

**Priority:** P1
**Type:** verification / harness (may close without a code change)
**Owner gate:** none
**Blocks:** truthful “repeatable suite” claim

**Evidence:**
- `NEXT-WORK-TASK.md` NW-5.2’s cited `analytics_ingestion_test::test_phase4_rate_limit` **does not exist at this HEAD** (the file has no such test). The actual 429 coverage is `tests/auth_register_rate_limit_test.py` (tenth registration succeeds, eleventh returns 429; line 53).
- The allowlist startup race (fixed in `8952381`/`cd56ac0`) is a separate issue; `STATE.md` mislabels it as NW-5.2.
- Three observed full-suite runs: 142/1 (4:39), 142/1 (4:26), and **141/2** (4:54, FB-09 server readiness). The rate-limit test itself did not fail. So the “three consecutive green except OD-7” acceptance is not met, but the failure is not the rate-limit test.

**Work:**
1. Run the actual rate-limit tests repeatedly and in context:
   ```bash
   .venv/bin/python -m pytest tests/auth_register_rate_limit_test.py -q
   .venv/bin/python -m pytest tests/auth_register_rate_limit_test.py -q   # repeat
   .venv/bin/python -m pytest tests/ -q                                   # after FB-09/FB-04
   ```
2. If the rate-limit tests pass consistently, close NW-5.2 with evidence and update the work-order reference to the real file. Do not claim the cited test passed; state that the reference was stale and the actual coverage is `auth_register_rate_limit_test.py`.
3. If they are order-dependent (e.g. a global throttle shared with other auth tests), fix the test isolation, not the assertion: unique emails/IPs per test, reset the in-memory limiter, or run the limiter in a temp data dir. Keep the 429 assertion.
4. Coordinate with FB-09: the repeatability blocker may be the server fixture, not the limiter. Do not conflate them in one commit.

**Acceptance criteria:**
- [ ] The real rate-limit test file passes 3× in isolation and in the full suite (after FB-09).
- [ ] The stale `analytics_ingestion_test::test_phase4_rate_limit` reference is corrected everywhere.
- [ ] The allowlist race is recorded as a separate closed fix, not NW-5.2.
- [ ] NW-5.2 is closed with run logs, or left open with a precise failing traceback.
- [ ] No weakened 429 assertion.

**Commit:** `test(auth): verify the real rate-limit gate and correct the NW-5.2 reference`

---

### FB-14 — i18n residual: 305 fallback rows, not 59

**Priority:** P1
**Type:** audit (no translations applied in this pass)
**Owner gate:** **answered 2026-10-22: audit first.** FB-14 may classify the fallback rows; it must not apply translations yet. OD-8 covers only the feature-flags subset and is deferred.
**Blocks:** truthful i18n completeness; not the release gates unless the owner requires zero fallback

**Evidence (verified):**
- `docs/i18n/TRANSLATIONS.csv` has **1,145 rows**: **554 translated**, **305 fallback**, **286 stale** (107 text-changed, 50 removed, and the rest moved-to-JS with per-module labels).
- Sampled fallback rows are real UI text, not only technical keys: e.g. “Skip to content”, “Dashboard”, admin page strings. The CSV `status=fallback` means “English shown in Khmer mode”.
- The earlier work-order figure of “59 fallback” is obsolete; do not use it.
- `scripts/check-bilingual-consistency.py` passes because fallback is allowed; that is not evidence of completeness.
- OD-8 covers only the `feature-flags.js` doc-strings; it does not authorize machine translation of the other rows.

**Work:**
1. Generate an audit grouped by source file/page and status: `artifacts/next-work/fb-14/fallback-audit.md`.
2. Classify every fallback row into:
   - **technical/non-UI** (keys, URLs, identifiers): keep English, mark with a reason/allowlist;
   - **admin-only** (owner-only screens): mark as “English-only admin — future owner review”; do not assume acceptance and do not translate it now;
   - **real user-facing missing Khmer**: mark for a future owner-supplied translation batch; **do not apply any translation in this pass**;
   - **stale/duplicate**: identify and propose cleanup; do not remove or archive in this pass.
3. Do not machine-translate. The CSV remains unchanged except for audit/allowlist metadata that does not alter displayed strings. Preserve owner strings byte-exactly when they arrive later.
4. Update the i18n report/checker only to record the audit policy (e.g. a documented allowlist), not to hide unexplained rows.
5. Finish the audit and produce a short ordered list of real user-facing gaps. That report is the approved checkpoint; do **not** ask questions mid-audit and do **not** mark the fallback rows as translated. Leave them in `fallback` with an explicit deferral until the owner supplies Khmer.

**Acceptance criteria:**
- [ ] All 305 fallback rows are classified with a reason.
- [ ] Technical/admin allowlists are documented; every real user-facing gap is listed and explicitly deferred pending owner Khmer.
- [ ] No translations were applied; no CSV row was flipped to `translated` without an owner string.
- [ ] Bilingual checker still passes; no new hard-coded English in Khmer UI.
- [ ] CSV diff is reviewed; any metadata/allowlist changes are explained.
- [ ] Evidence: audit table, counts, samples, ordered gap list.

**Do not:** trust the “59” figure; bulk-replace with machine Khmer; change the checker to fail on all fallback without an owner decision; translate admin screens or any other UI in this pass.

**Commit:** `docs(i18n): audit the fallback set and queue owner translations`

---

### FB-15 — Final release gate matrix and evidence

**Priority:** P0 (last, after Wave 1)
**Type:** verification
**Owner gate:** **OD-3 answered 2026-10-22: local commits only.** No push/PR/merge/tag. OD-6 still forbids threshold changes.
**Blocks:** release candidate claim (evidence can be complete locally; publication is not approved)

**Work:** After FB-01…FB-10 and the applicable Wave 2 items, run the full matrix from a clean state and record exact outputs in `artifacts/next-work/fb-15/` and `RELEASE-CANDIDATE.md`.

Required matrix:
```bash
python3 build.py all --check
python3 build.py bundles --check
node tools/page-errors.mjs --all
.venv/bin/python -m pytest tests/ -q
python3 tests/v55_route_weight_budget_test.py
# v14 remains non-blocking per the owner answer; run it and record the actual result
python3 tests/v14_performance_budget_test.py   # expected FAIL until a real duplicate fix; do not gate on it
npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js
# pip-audit per FB-01
# npm audit / Dependabot check per FB-10
tools/run-gates.py --phase all          # after FB-08; canvas acceptance included
```

Expected:
- Build/bundles/smoke: pass.
- Full pytest: 143 passed (or the new collected count), 0 failed/errors; no skips that hide browser coverage.
- v55: pass; admin at/below the frozen budget.
- v14: explicitly non-blocking with the owner’s 2026-10-22 answer and a dated note; pass only if a real duplicate fix landed.
- LHCI: 16 URLs, 16/16 a11y 1.00, assertions pass, clean-checkout collect works.
- Security: pip-audit no high/critical; GitHub alerts 0 open (or approved no-fix dismissals).
- Canvas acceptance: 22/0/2; visual/perf statuses documented (FB-16/17).
- `run-gates --phase all`: pass (with v14 disposition stated). If canvas visual/perf are not part of run-gates, do not imply they ran.
- `git status`: only the 78 owner paths plus this work order/evidence remain untracked; nothing staged accidentally.

**Acceptance criteria:**
- [ ] Every row has a command, exit code, and log path.
- [ ] No “PASS” without a fresh run; no “blocked” row hidden.
- [ ] `RELEASE-CANDIDATE.md` accurately distinguishes pass / known-red / not-run / deferred.
- [ ] **No push/PR/merge/tag in this pass — local commits only.**
- [ ] Evidence bundle is complete and reproducible by another agent.

**Commit:** `docs(release): record the verified gate matrix for the fixed branch`

---

### FB-16 — Canvas visual gate has never run (baseline missing)

**Priority:** P1
**Type:** verification, environment-bound
**Owner gate:** none to proceed; the Windows baseline is an environment dependency. If it is absent, record **NOT RUN** and continue — do not ask again mid-pass.
**Blocks:** canvas visual evidence; not the CI build

**Evidence:**
- `tools/canvas-motion-visual.py` requires `artifacts/canvas-motion/baseline/before/` and asserts it exists (`baseline snapshot missing` if absent).
- The directory is absent on this Linux host; the existing baseline was captured on Windows. The tool’s default base is `http://127.0.0.1:8137`, phase `P1`.
- The frozen brief is `docs/CANVA-SMOOTHNESS-BRIEF.md`; do not edit it or the harness.
- The gate has never been executed in this pass; `RELEASE-CANDIDATE.md` correctly marks it not-run.

**Work:**
1. Check for the Windows-captured baseline at `artifacts/canvas-motion/baseline/before/`. If it is absent, record **NOT RUN** with the missing path and continue; do not block the pass and do not ask again. If the owner supplies it during the pass, use it.
2. Only if a new baseline is explicitly approved, capture it on the same pinned renderer/viewport matrix as the original; document the renderer version and date. Do not generate a “baseline” from the current code and compare it to itself.
3. Start the required server on 8137 (or pass `--base`) with the correct data/account; run:
   ```bash
   .venv/bin/python tools/canvas-motion-visual.py --base http://127.0.0.1:8137 --phase P1 --out artifacts/next-work/fb-16/visual
   ```
4. Record the diff report and any visual regressions; fix only real regressions, not the documented false positives (§10).

**Acceptance criteria:**
- [ ] Baseline directory exists and is documented (source/date/renderer), or the gate is recorded **NOT RUN** with the missing path.
- [ ] If run, the tool exits 0 with a diff report; no fabricated baseline.
- [ ] Any visual diff is either explained or fixed; frozen files untouched.
- [ ] `RELEASE-CANDIDATE.md` says PASS or NOT RUN with the exact reason; no invented owner sign-off.
- [ ] Evidence (if run): command, renderer version, diff summary, screenshots if needed.

**Do not:** create a baseline from current output; edit `artifacts/canvas-motion/**` without owner approval; edit the frozen brief/tests; claim visual verification from the acceptance harness.

**Commit:** only docs/evidence if the gate is run; no code change unless a real regression is found.

---

### FB-17 — Canvas performance gate is environment-blocked

**Priority:** P1
**Type:** verification, environment-bound
**Owner gate:** none to proceed; valid measurement needs owner hardware/Windows. If unavailable, record **environment-blocked** and continue. OD-6 still forbids threshold changes.
**Blocks:** performance evidence; not the CI build

**Evidence:**
- `tools/canvas-motion-perf.mjs` requires a running editor at `BASE_URL` and enforces frozen thresholds (p95 frame time, max frame, commits/frames, input-to-paint).
- Headless Chromium vsync quantization makes the numbers non-representative; an earlier probe recorded `inputToPaintMs` ~11.5, which is not a valid Windows/display baseline.
- The acceptance harness (`tests/canvas_motion_playwright.py`) passes 22/0/2 but does **not** prove the perf thresholds.
- The gate has never been verified on this host; do not call it green.

**Work:**
1. Run on a real display/owner Windows machine with the pinned browser and the correct editor/data setup.
2. Capture the full report (p95, max frame, commits, frames, input-to-paint) and compare against the frozen thresholds.
3. If it fails on valid hardware, fix the code; do not relax thresholds (OD-6).
4. If it cannot be run, record “environment-blocked” with the exact reason and hardware in `RELEASE-CANDIDATE.md`. Do not fabricate numbers and do not ask again mid-pass.

**Acceptance criteria:**
- [ ] Valid measurement or explicit environment-blocked record.
- [ ] Thresholds unchanged.
- [ ] No headless numbers presented as a Windows baseline.
- [ ] Evidence: raw report, hardware/display, command.

---

### FB-18 — RILL end-to-end walkthrough has never been executed

**Priority:** P2
**Type:** verification (can surface product bugs)
**Owner gate:** none for a local throwaway run. Do **not** request a public Rill URL/account in this pass; if the cloud-side variant is impossible, the local flow is the required evidence.
**Blocks:** the end-to-end user-flow evidence

**Evidence:** `RILL-WALKTHROUGH.md` defines nine steps: start the app, create a throwaway account, create a wedding invitation, fill bilingual content, preview as a guest, publish a snapshot, open the public page, RSVP, and see the response recorded. It uses the local dev server on `:4175`, `EINVITE_ALLOW_NO_SCANNER=1`, test data only. It has never been executed. Rill cloud cannot reach `localhost`, so a cloud-side walkthrough needs a public URL; the local flow does not.

**Work:**
1. Start the server:
   ```bash
   EINVITE_DATA_DIR=$(mktemp -d) EINVITE_DEV_AUTH_TOKENS=1 EINVITE_ALLOW_NO_SCANNER=1 \
     PYTHONPATH=src/python:. python3 src/python/server.py --port 4175
   ```
2. Execute the nine steps with Playwright or manually; use a throwaway email/password and test names. Capture a screenshot per step and the network/console log.
3. File any product defect as a new issue with a minimal reproduction; do not fix it inside this verification item unless it is trivial and in scope.
4. Stop the server; remove the temp data dir.

**Acceptance criteria:**
- [ ] All nine steps pass locally, or the first failure is documented with a minimal reproduction.
- [ ] No real PII; no public exposure of localhost.
- [ ] Evidence: screenshots/logs per step, server command, data dir removed.
- [ ] Product defects are filed separately, not hidden by test edits.

**Do not:** use real names/emails; expose the dev server publicly; change the flow to avoid a bug without filing it.

---

## 9. Wave 3 — Approved implementation (OD-1/OD-2) and deferred items### FB-19 — OD-1: staged `!important` / layered-CSS cleanup

**Status:** **PHASE 1+2 CLOSED 2026-10-22** — 211 dead tokens (85 occurrences, live-probe-verified,
comma-list union bug fixed) + 5 proven-superseded tokens applied on pristine src/css; inventory
4033 → 3819 (Δ214, 5.31 %, below the approved 25–40 % — remainder justified in the report);
full gate run green; pixel-matrix gate 62 diffs, zero unexplained after classification
(identical-run flake overlap / chip micro-AA ≤51 px / index-mobile canvas per-load flake proven
by same-tool repeats / account sessions data drift). Evidence: `artifacts/next-work/fb-19/REPORT.md`.
A deeper-interaction second wave is optional and NOT approved to invent itself.

**Original brief:**

**Preparation:** finish the NW-2.2 Playwright page matrix and baseline digests, confirm the 4,033/67 inventory, and produce a proposed first batch of provably dead rules with evidence.

**Implementation (approved 25–40% target, dead rules first):**
- Phase 0: page matrix across 16 pages × user/guest × 320/375/768/1024/1440 × light/dark × en/km; baseline screenshots/digests.
- Phase 1: remove dead rules (no matching DOM) first; one batch per commit; run the matrix; stop at the first unexplained diff.
- Phase 2: remove superseded declarations that are provably overridden; pixel-diff gate each batch.
- Phase 3: only if needed to reach the approved range; keep components/unlayered counts in the report. Do not turn this into a full layer/token rewrite.
- Stop/report at 25–40% or at the first unexplained visual diff, whichever comes first. Do not exceed 40% without a new owner answer.

**Acceptance:** target range met; zero unexplained visual diffs; all gates/smoke/LHCI pass; no budget/threshold changes; per-batch evidence; the inventory/report is updated. Do not remove `!important` blindly to hit a number.

**Files/evidence:** `artifacts/next-work/nw-2-1/important-inventory.md`; CSS dirs; page matrix artifacts.

**Commit:** `style(css): remove dead !important declarations in gated batches`

---

### FB-20 — OD-2: dashboard parity subset

**Status:** **APPROVED — proceed with the recommended subset.**

**Implement only this approved subset:**
- passkey row (row 67) and poster type (row 62) — cheap, restore;
- sheets/polls entry points (rows 65/66) — links to the guests/events sections, not panel reimplementation;
- document the event-role picker as intentionally absent;
- edit history (row 64) only as the cheap ⋮-link variant. No full history panel.

**Acceptance:** every approved gap row is either implemented or documented as absent with the owner’s 2026-10-22 decision; 60/67 already-existing rows remain untouched; smoke/LHCI/a11y/KM 375 pass; no dashboard redesign. Do not rebuild panels or invent a new navigation model.

**Files/evidence:** `artifacts/next-work/nw-3-1/gap-matrix.md`; dashboard source.

**Commit:** `feat(dashboard): add the approved parity entry points`

---

### FB-21 — OD-8: trusted Khmer for `feature-flags.js`

**Status:** **DEFERRED by owner (2026-10-22). Do not start.** Feature flags remain English for now. Do not machine-translate and do not ask again; revisit only when the owner supplies the strings.

**When the owner supplies the strings:**
1. Reconcile the actual key list in `src/js/pages/admin/feature-flags.js` with the OD-8 list and the CSV (the register says 11; the expanded list is 14 — resolve the discrepancy).
2. Apply the owner’s Khmer byte-exactly; do not paraphrase, normalize, or “fix” spelling.
3. Flip the corresponding CSV rows to `translated`; no code change should be needed.
4. Verify at 375 px in Khmer and English: labels, confirm dialog, session-policy group, saved/error states; check font rendering.
5. Run the bilingual checker and the full suite.

**Acceptance:** every listed key is owner-supplied Khmer; CSV status matches; no mojibake; UI renders; no code changes beyond what the plumbing requires. Evidence: translation diff, CSV rows, screenshots.

**Commit (only when the owner supplies Khmer):** `i18n(admin): apply owner-supplied Khmer for feature flags`

---

### FB-22 — OD-3/OD-4/OD-5 close-out

**Priority:** P2
**Type:** documentation/owner confirmation
**Owner gate:** **answered/confirmed 2026-10-22** — OD-3 local-only release, OD-4/OD-5 confirmed
**Blocks:** ledger truth only

**Work:**
1. **OD-3:** record that the branch was pushed at `6f7de27`, `main` remains `50721ef`, no tag/version-history edit; **new work uses local commits only — no push/PR/merge/tag**. Remove “push blocked” claims (FB-12).
2. **OD-4:** verify the 24×24 live resize-handle hit box is present and the a11y harness evidence is linked; record the owner’s confirmation and close. Do not ask again.
3. **OD-5:** verify the runtime `<option>` rewrite live in EN/KM at 375 px (materials/responses/account); record the owner’s confirmation and close. Do not ask again.
4. Update `DECISIONS.md`, `OPEN-ITEMS.md`, `STATE.md`, and `RELEASE-CANDIDATE.md` consistently.

**Acceptance:** owner confirmations recorded with dates; no code change unless a verification reveals a real defect; no contradictory “awaiting” rows; no push/PR/merge/tag.

**Commit:** `docs: close OD-3/4/5 and record the local-only release`

---

## 10. False positives and “do not chase” registry

If you see these, **do not fix them** unless they become a new user-visible defect. Capture the evidence, compare with the prior note, and close/annotate.

| Class | Why it is not a defect | What to do |
|---|---|---|
| Billing gradient contrast | The checker samples a gradient stop; the shipped gradient is intentional | Link the prior evidence; close |
| Admin mock-403 console rows | Expected mock responses in admin tooling | Do not chase console noise |
| Designer CSP `unsafe-eval` pageerror | Known CSP/designer harness noise | Verify no functional break; close |
| Sticky-header occlusion rows | Documented heuristic false positive | Compare with prior captures; close |
| Icon-only tiny text at 320 px | Documented heuristic false positive | Do not shrink/expand icons |
| `color(srgb)` / `color-mix` transparency rows | Tooling limitation, not a visual bug | Note the limitation |
| Public `#openCover` pre-open fixed layer | Capture race, not a layout bug | Re-capture with the correct wait; close |
| Editor `#mobileQuickInspector` at 375 px | Hidden because the desktop inspector is active | Do not “fix” the responsive rule |
| Transient quick-toolbar occlusion at 375/320 | Transient capture race | Re-capture; close |
| Canvas acceptance 2 console rows | Expected/known console noise; 22/0/2 is the accepted result | Do not chase |
| `npm audit` 17 vs 6 Dependabot alerts | Different counting/dismissal scope | Target the six open alerts (FB-10) |
| LHCI a11y 1.00 | Passing; no action | Do not churn |

If a new failure looks like one of these, reproduce at the same viewport/route and compare with the evidence before editing. Do not reopen closed NW-6.3 toolbar work.

---

## 11. Suggested execution order and dependencies

### Wave 1 (release/CI unblock)
1. FB-01 (Pillow) — independent.
2. FB-02 (LHCI) — independent, but touches the workflow/config; coordinate with FB-07/FB-11.
3. FB-03 (v55) — independent; must precede FB-08’s full-gates claim.
4. FB-04 (OD-7) — **approved (Option A)**; blocks FB-05 and the green full suite.
5. FB-06 (Makefile/reproduce) — independent; makes FB-04/05/09 verifiable.
6. FB-07 (CI pytest) — after FB-06 so the same interpreter logic is documented; coordinate with FB-02 for workflow edits.
7. FB-09 (server flake) — before claiming repeatability or closing FB-13.
8. FB-10 (Dependabot) — independent; touches `tools/reproduce.sh` preflight, coordinate with FB-06.
9. FB-05 (NW-5.1) — after FB-04.
10. FB-08 (zero-test/run-gates) — after FB-03 so the new gate passes.

### Wave 2 (truth-up/durability)
11. FB-12 (docs) — after Wave 1 results exist; last, so it records reality.
12. FB-11 (v14) — **owner chose keep non-blocking**; can run in parallel after Wave 1. Do not retire the step.
13. FB-13 (NW-5.2) — after FB-09 and FB-04; may close with evidence.
14. FB-14 (i18n audit) — parallel; **audit only**, no translations applied.
15. FB-22 (OD-3/4/5 close-out) — parallel with FB-12.

### Wave 3 (approved implementation and deferred items)
16. FB-19 (OD-1) and FB-20 (OD-2) — **approved; proceed** after the release blockers/Wave 1. FB-21 (OD-8) is **deferred**; do not start it.
17. FB-16/17/18 (canvas visual/perf/RILL) — environment/owner-dependent; can run as soon as the owner provides hardware/baseline; not blockers for code work.
18. FB-15 (final matrix) — last; **local commits only**, no push/PR/merge/tag.

### Dependency summary
- FB-04 → FB-05, FB-15.
- FB-03 → FB-08’s green `--phase all` and FB-15.
- FB-02 → FB-10’s LHCI verification and FB-15.
- FB-06 → reliable FB-04/05/09 reproduction.
- FB-07 → branch CI evidence for FB-01/02/03/08.
- FB-09 → FB-13 repeatability and FB-15.
- FB-11 → FB-15’s v14 disposition (non-blocking per owner).
- FB-14 → FB-15 if the owner later requires i18n completeness; this pass is audit-only.
- FB-16/17/18 → FB-15’s canvas/RILL rows.
- FB-19/20 → FB-15 only if they are in the release scope; otherwise they are post-release.
- FB-21 → **deferred**; it does not block FB-15 or the approved scope.

### Rough effort
- FB-01: 0.5 day (bump + audit + tests).
- FB-02: 0.5–1 day (config/server/reproduce/CI).
- FB-03: 1–2 days (helper relocation + live checks).
- FB-04: 0.5 day — approved (Option A).
- FB-05: 0.5 day.
- FB-06: 0.5–1 day.
- FB-07: 1 day (workflow + Playwright cache).
- FB-08: 1–2 days (manifest + gate wiring).
- FB-09: 0.5–1 day (diagnose + harden + repeat runs).
- FB-10: 0.5–1 day (remove + verify + alerts).
- FB-11/12: 0.5–1 day each.
- FB-13/14: 0.5–1 day each (FB-14 is audit-only; translations are deferred).
- FB-15: 1 day (full matrix + evidence; local commits only).
- FB-16/17/18: environment-dependent; 0.5 day each once the prerequisite exists (otherwise record NOT RUN).
- FB-19/20: multi-day **approved** work; do not estimate as a quick fix.
- FB-21: deferred; no estimate until the owner supplies Khmer.

---

## 12. Definition of done (release-level)

**This pass produces a local release candidate only.** Rows that require a push/PR are marked **NOT RUN** and do not block the local evidence bundle; publication is a separate future decision.

A release candidate may be called green only when **all** of the following are true and evidenced:

- [ ] Build, bundles, smoke: pass.
- [ ] Full suite: all collected tests pass, 0 failed/errors; browser tests actually execute (no silent skips); repeatable on consecutive runs.
- [ ] `v55`: pass with the frozen budget; admin ≤162,816 B.
- [ ] `v14`: explicit owner-approved non-blocking quarantine (2026-10-22), or pass via a real duplicate fix; no threshold change, no retirement.
- [ ] LHCI: clean-checkout `autorun` collects 16 URLs, 16/16 a11y 1.00, assertions pass; artifact uploaded.
- [ ] Security: `pip-audit` no high/critical on production requirements; local dependency chains removed. GitHub alert closure is deferred until a future push; no alerts dismissed without owner sign-off.
- [ ] `make test` and `make reproduce`: use the Playwright-capable interpreter and fail closed on test failures.
- [ ] CI: a pytest workflow file exists and is locally validated; actual PR/main execution and the two existing workflow runs are deferred until the owner approves a future push. Record them as **NOT RUN** in this pass, not PASS.
- [ ] run-gates: `--phase all` passes, includes v55, and states the v14/canvas-visual/canvas-perf status honestly.
- [ ] Canvas acceptance: 22/0/2; visual/perf explicitly PASS or documented NOT RUN/environment-blocked with the exact reason.
- [ ] RILL: nine steps pass locally or the first failure is filed with a reproduction.
- [ ] Docs: WCAG status, canvas path, push status, HEADs, OPEN-ITEMS, workflow comments all match reality.
- [ ] No owner untracked path staged; **local commits only — no push/PR/merge/tag** without a new explicit owner instruction.
- [ ] Evidence bundle: `artifacts/next-work/fb-*/` plus `RELEASE-CANDIDATE.md` updated.

If any row is “not run”, the release is **not** green; it is “green with documented gaps”. Record the gaps and do not claim publication readiness.

---

## 13. Owner answers recorded (no further questions)

The owner answered on **2026-10-22** and approved proceeding without further questioning while Freebuff works. These answers are final for this pass; do not re-ask them.

| # | Decision | Owner answer | Consequence |
|---|---|---|---|
| 1 | **OD-1** | Approve **25–40%**, staged, pixel-diff-gated, dead rules first | FB-19 is unblocked; stay inside 25–40%; stop at the first unexplained diff |
| 2 | **OD-2** | Approve the **recommended subset** | FB-20 is unblocked; no panel rebuild, no new nav model |
| 3 | **OD-4** | **Confirm** the 24×24 hit-box “Equivalent” exception | Close the ledger item; no code work |
| 4 | **OD-5** | **Confirm** the runtime `<option>` rewrite; no custom listbox | Close the ledger item; keep the 375 px verification as evidence |
| 5 | **OD-7** | **Option A** — normalize `\r\n` → `\n`, pin LF digest `38ce744d…`, add CRLF/LF regression test | FB-04 is unblocked |
| 6 | **OD-8** | **Defer for now** | FB-21 stays deferred; feature flags remain English; **no machine translation** |
| 7 | **i18n** | **Audit first** | FB-14 audits/classifies only; do not apply translations or flip CSV rows |
| 8 | **v14** | **Keep non-blocking for now** | FB-11 keeps `continue-on-error`; no budget change; do not retire the step |
| 9 | **Release** | **Local commits only for now** | No push/PR/merge/tag; FB-15 records evidence locally |

**Freebuff instruction:** proceed with the approved scope. Stop only if:

- a change would alter a budget, threshold, or frozen gate (OD-6);
- a genuinely new product/user-visible decision appears that is not covered by these answers.

OD-8 is deferred; do **not** stop for missing Khmer. Missing environment prerequisites (canvas baseline, Windows perf hardware, public RILL URL, remote GitHub alert closure) are recorded **NOT RUN/deferred**, not treated as questions. Do not ask about answers 1–9 again. If the scope changes later, add a new dated decision here; do not silently reinterpret an old one.

---

## Appendix A — Exact Dependabot alert evidence

| Alert | URL | Package | Severity | Scope | Fix |
|---|---|---|---|---|---|
| 8 | `github.com/<owner>/<repo>/security/dependabot/8` | `sprintf-js` | medium | development, transitive | no |
| 6 | `…/6` | `extract-zip` | high | development, transitive | no |
| 5 | `…/5` | `extract-zip` | high | development, transitive | no |
| 4 | `…/4` | `tmp` | high | development, transitive | `0.2.6` |
| 3 | `…/3` | `uuid` | medium | development, transitive | `11.1.1` |
| 2 | `…/2` | `tmp` | low | development, transitive | `0.2.4` |

Replace `<owner>/<repo>` with the actual GitHub slug when recording evidence. The alerts are on the default branch (`main`); fixing the lockfile on a feature branch does not close them until the change reaches the default branch or the alert is dismissed with a reason.

## Appendix B — CI evidence to attach

- Security Scan: run `39557451856`; `pip-audit` finding block with the 8 Pillow CVEs; fixed `13.0.0`.
- Performance Budgets: run `39557451848`; the `Failed to automatically determine staticDistDir` line; the v14 `styles 2 > 1` assertion; the workflow’s `continue-on-error` step.
- Local v55: exact `admin.html` bytes and overage.
- Local full-suite runs: 142/1 (4:39), 142/1 (4:26), 141/2 (4:54); the analytics readiness traceback; the isolated 4.85 s pass.
- Branch state: `git rev-parse --short HEAD` = `6f7de27`; `origin/…` = `6f7de27`; `git log --oneline 50721ef..HEAD | wc -l` = 10; `git status --porcelain` = 78 untracked, no tracked modifications.

## Appendix C — File reference

| Path | Why it matters |
|---|---|
| `artifacts/next-work/DECISIONS.md` | OD-1…OD-8 authoritative text (OD-7/OD-8 are bold table rows) |
| `NEXT-WORK-TASK.md` | Live work order; phases, acceptance, owner gates; NW-5.2 reference is stale |
| `RELEASE-CANDIDATE.md` | Gate matrix, known limitations, push-status contradiction |
| `artifacts/next-work/00-baseline/OPEN-ITEMS.md` | Per-task ledger; stale in places |
| `artifacts/ui-audit/fixes/STATE.md` | Session ledger, environment map, not-run items |
| `tests/v27_3_5_release_evidence_test.py` | OD-7 digest + NW-5.1 child process |
| `tests/v55_route_weight_budget_test.py` | Admin route budget gate |
| `tests/v14_performance_budget_test.py` | Aspirational style/weight gate |
| `tests/auth_register_rate_limit_test.py` | Actual 429/rate-limit coverage |
| `tests/analytics_privacy_test.py` | FB-09 intermittent readiness failure |
| `tests/v14_test_utils.py` | `app_server`, `wait_http` (12 s) |
| `tools/lighthouserc.js` | LHCI config; missing server command; report output dir |
| `.github/workflows/lighthouse.yml` | CI perf; stale comments; artifact path |
| `.github/workflows/security.yml` | pip-audit triggers/scan |
| `docs/requirements-production.txt` | Pillow pin, line 26 |
| `docs/i18n/TRANSLATIONS.csv` | 1,145 rows; 305 fallback |
| `docs/a11y/WCAG-2.2-AA-AUDIT.md` | Stale “none applied” status |
| `docs/CANVA-SMOOTHNESS-BRIEF.md` | Frozen canvas brief (correct spelling) |
| `tests/conftest.py` | 12 `COLLECT_IGNORE` entries |
| `tools/run-gates.py` | Phases; omits v55/v14 |
| `tools/reproduce.sh` | Interpreter selection; preflight; non-fatal test step |
| `package.json` / `package-lock.json` | `@lhci/cli` devDependency and the six alert chains |
| `RILL-WALKTHROUGH.md` | Nine-step local flow, never executed |

## Appendix D — Document conventions

- “Verified” means a command was run and its output recorded in this research session.
- “Documented” means it comes from a repo ledger and still needs a fresh run before being called done.
- “NOT RUN” is a legitimate status; it is not a pass.
- “PASS” requires a command, an exit code, and a log path.
- “Owner-gated” means the owner reserves the decision. The answers are recorded in §6.1/§13: approved items proceed; **FB-21 remains deferred**; do not infer consent from a stale doc.
- “Local commits only” means no push, no PR, no merge, no tag.

*End of work order. Do not commit or push this file unless the owner asks; it is a planning artifact.*
