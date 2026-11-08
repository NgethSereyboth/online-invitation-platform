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
