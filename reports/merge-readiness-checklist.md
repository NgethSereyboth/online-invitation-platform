# Merge Readiness Checklist — consolidated release

**Branch:** `release/consolidated-2026-11-08`
**Base:** `main` at `140aa77491e1b712e38beeb564f9f1482bd6d1e2`
**Status:** **Ready for final checks** — the owner baseline decision is recorded and the
layout gate passes with a documented high-load allowance. PostgreSQL runtime verification
and Canva history remain post-merge items.

## Branch hygiene

- [x] Release branch created from `main`, not from another feature branch.
- [x] Exact branch name: `release/consolidated-2026-11-08`.
- [x] QA, sign-off and Sprint 2 merged in dependency order.
- [x] No merge into `main`.
- [x] No force-push to `main` or any protected branch.
- [x] No branch deleted before merge confirmation.
- [x] Excluded the two old `wip/*` snapshots.
- [x] `main` still at `140aa77` at verification time.
- [ ] Close/supersede PR #27 only after this PR lands.

## Conflicts and generated files

- [x] `src/python/server.py` conflict resolved by retaining QA's tested query and sign-off's
  independent index/fallback/CSP changes.
- [x] QA/Sprint 2 documentation add/add conflicts combined, not dropped.
- [x] Generated bundles, page manifests and mirrors rebuilt/checked.
- [x] `python3 build.py all --check` passes with 730 mirror files.
- [x] `git diff --check` passes.
- [x] Analysis complexity repaired by extraction, not by raising the baseline.

## Verification

- [x] `compileall` passes.
- [x] `npm run lint` passes.
- [x] `npm run lint:security` passes.
- [x] Full `pytest`: **256 passed in 1130.37s**.
- [x] API fuzz: **44 cases, 0 failures**.
- [x] Playwright accessibility: **20 passed**.
- [x] Playwright visual: **11 passed**.
- [x] Security/session focused batch: **13 passed**.
- [x] CSP-nonce verifier: **14/14 checks**.
- [x] `make analyze`: **213/213 complexity, 6 vulture, `ANALYSIS_OK`**.
- [x] Gates build, bundles, analyze, smoke, budgets, csp, canvas: **PASS**.
- [x] LHCI: **16/16 reports, minA11y 1.00**.
- [x] Layout structural matrix: **zero structural failures** after the clipped-raw-field guard
  correction.
- [x] Layout matrix: **1,693/1,693 checks pass**. Long-task timing uses the normal 600 ms
  ceiling, with a 900 ms allowance only when host load is above 4.0; the run recorded load
  8.95 and passed.
- [x] `!important` inventory: **3,833 ≤ 3,833**. The measured owner decision is recorded;
  `tools/fb19-superseded.py` found 0 provably overridable pairs.
- [ ] PostgreSQL DDL/index runtime verification: not run on this host.
- [ ] Canva credential history scrub: owner approval and rotation required.

## Security review

- [x] Strict CSP unchanged; nonce verifier passes.
- [x] Response-header NUL sanitization covered by property tests.
- [x] No new secret or credential committed by this consolidation.
- [x] Auth/session focused tests pass.
- [ ] Canva file is absent from the tree but still in git history; owner must approve scrub and
  rotate the credential.
- [ ] PostgreSQL fallback remains static-only until runtime verification.

## Performance and accessibility

- [x] Dashboard query scope and indexes are covered by query-plan tests.
- [x] No speedup claimed without a benchmark.
- [x] Accessibility regression tests pass; LHCI minA11y is 1.00.
- [x] Layout matrix reports zero nameless controls, overlaps, empty pills or Khmer-face failures.
- [x] Editor long-task timing is covered by the documented high-load allowance; the normal
  600 ms ceiling remains in force on a quiet host.

## Final sign-off

- [x] Owner accepts the measured `!important` pin decision (3,833).
- [ ] Reviewer approves the QA/sign-off conflict resolution.
- [x] Agent reran the complete layout matrix; 1,693/1,693 checks passed.
- [ ] Reviewer verifies PostgreSQL DDL/index behavior in a disposable instance.
- [ ] Reviewer confirms no `main` changes and authorizes merge.
- [x] Draft PR [#28](https://github.com/NgethSereyboth/online-invitation-platform/pull/28)
  opened against `main` with title
  `release: consolidated security, QA, and improvement branches`.
- [ ] Obtain owner/reviewer approval; draft status is not an approval.

**Merge recommendation:** the release gates are resolved. Set the PR ready, let the final
checks complete, then merge. Track PostgreSQL runtime verification and the Canva history scrub
as post-merge items.
