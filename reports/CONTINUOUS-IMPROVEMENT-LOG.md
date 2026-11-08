# Continuous Improvement Log — Sprint 2

**Branch:** `improve/sprint-2-hardening-and-polish` (from `main` `140aa77`)
**Scope:** static-analysis tooling, header-injection properties, test stability.
**Rule:** no merge into `main`; every change stays on this branch for review.

> The QA deep-dive log and sprint plan live on `qa/deep-dive-improvements`
> (draft PR #27), which is not merged. This file starts the Sprint 2 log on the
> stable base; it does not claim the QA branch's commits.

---

## 2026-11-08 — Analysis gate

- **Found:** the repository had no runnable static-analysis gate. Its recorded
  baseline was stale at “157 functions above CC 10”; fresh `radon` evidence on
  `main` reports **213**. `vulture` at >=90% confidence reports **11** existing
  findings, so a raw threshold check would be red on day one.
- **Fixed:** pinned `pytest-cov==7.1.0`, `vulture==2.16` and `radon==6.0.1` in
  `requirements-dev.txt`; added `make analyze` and `make coverage`; added
  `tools/analyze.py` with a baseline-diff gate and
  `tools/analysis_baseline.json`.
- **Tests:** `tests/tooling_analysis_test.py` — 5 new tests (new complexity,
  matching baseline, increased complexity, new vulture finding, repository
  baseline); combined with the existing header tests, **7 passed**. A temporary
  new complex function made the gate return non-zero (tool exit 1, `make`
  exit 2); removing it returned `ANALYSIS_OK` (exit 0).
- **Evidence:** `artifacts/sprint2/analyze.log`,
  `artifacts/sprint2/analyze-write.log`, `artifacts/sprint2/tooling-tests.log`.
- **Docs:** `docs/QUALITY-GATES.md` records the 213 / 11 baseline and the
  regeneration rule.

## 2026-11-08 — Header-injection properties

- **Found:** `safe_header_value()` stripped CR and LF but left NUL, so a
  NUL-containing value could reach a `Location` header. Header filenames and
  the media/download paths had existing example tests but no generated input
  coverage.
- **Fixed:** `safe_header_value()` now strips CR, LF and NUL before the
  4,096-byte cap. Added Hypothesis-generated tests for CR, LF, CRLF, NUL,
  quotes, semicolons, backslashes and Unicode line separators across header
  values, `Location`, filenames, download/binary/media responses and cookie
  construction.
- **Tests:** property + media-header + tooling + reflected-injection suites —
  **16 passed**. The red run recorded 3 genuine NUL failures before the fix;
  the fourth red assertion was a test-helper assumption about `attachment;`
  versus `inline;` and was corrected. `make analyze` stays at the 213 / 11
  baseline.
- **Evidence:** `artifacts/sprint2/header-properties-red.log`,
  `artifacts/sprint2/header-task-tests.log`,
  `artifacts/sprint2/analyze-after-header2.log`.
- **Dependency:** `hypothesis==6.170.15` is pinned in `requirements-dev.txt`; a
  fresh install and `pip check` both pass.

## 2026-11-08 — Sprint close

- **Full suite:** `250 passed in 1120.81s (18:40)`, exit 0
  (`artifacts/sprint2/pytest-full.log`).
- **Playwright:** `13-security.spec.ts` (chromium) — **8 passed** on a disposable
  4310 origin; the server was stopped and the user's 4175 server (PID 3005) was
  left running.
- **Final gates:** `python3 build.py all --check` → `BUILD_OK`/730 mirror files;
  `npm run lint` and `npm run lint:security` → PASS; `make analyze` → 213/213
  complexity and 11/11 vulture, `ANALYSIS_OK`; `pip check`, `compileall` and
  `git diff --check` → PASS.
- **Report:** `reports/sprint-2-summary.md`. Deferrals and rejected work:
  `docs/FUTURE-IMPROVEMENTS.md`.
- **No merge, no push, no production access.**

## 2026-11-08 — Analysis gate wired into local and CI runners

- **Found:** `make analyze` existed as a manual target, but neither
  `tools/run-gates.py` nor the Tests workflow called it. A new complexity or
  vulture finding could therefore pass both the local matrix and CI.
- **Fixed:** added the `analyze` phase after `bundles`, with a fail-closed
  `ANALYSIS_OK` marker; added `make analyze` to
  `.github/workflows/tests.yml`; documented the wiring in
  `docs/QUALITY-GATES.md` and `tools/README.md`.
- **Tests:** the new wiring test was red first; `tests/tooling_analysis_test.py`
  now **6 passed**; `tests/test_runner_manifest.py` and
  `tests/lhci_invocation_test.py` **4 passed**;
  `.venv/bin/python tools/run-gates.py --phase analyze` printed
  `PASS analyze` / `GATES_PASSED`; `make analyze` printed 213/213 and 11/11 with
  `ANALYSIS_OK`; build, compileall and diff checks pass. The workflow parses
  with system PyYAML 6.0.1 and the repo's `js-yaml`.
- **Evidence:** `artifacts/sprint2/wiring-red.log`,
  `artifacts/sprint2/wiring-pytest.log`,
  `artifacts/sprint2/wiring-run-gates.log`,
  `artifacts/sprint2/wiring-related-tests.log`,
  `artifacts/sprint2/workflow-parse.log`.
