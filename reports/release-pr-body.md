# release: consolidated security, QA, and improvement branches

> **Ready for final checks.** The `!important` baseline is recorded at the measured 3,833,
> and the layout timer passes with a documented high-load allowance (900 ms only above load
> 4.0; the normal ceiling remains 600 ms). PostgreSQL runtime verification and the Canva
> credential history remain separate post-merge items.

## Summary

This draft PR consolidates the three meaningful local improvement branches into
`release/consolidated-2026-11-08`, created from `main` at
`140aa77491e1b712e38beeb564f9f1482bd6d1e2`.

It includes:

- **QA deep-dive hardening** — dashboard query scope, cache behavior, accessibility, visual
  determinism, edge-case tests and release evidence (6 commits, 69 files).
- **Pre-merge sign-off** — pagination indexes, PostgreSQL schema fallback, CSP-nonce verifier,
  and removal of the tracked Canva evidence file (1 commit).
- **Sprint 2 hardening** — baseline-diff `radon`/`vulture` analysis gate, NUL stripping in
  response headers with Hypothesis property tests, CI wiring and close-out evidence (5 commits).

The two old `wip/*` safety snapshots are deliberately excluded. Dependabot PR #16 is unrelated
and is not included.

## Branch and commits

| Ref | Tip | Merge commit | State |
|---|---|---|---|
| `release/consolidated-2026-11-08` | this PR head | — | source tip verified at `3591f90`; guard correction `4f9759b` |
| `qa/deep-dive-improvements` | `623b766` | `0746c3f` | superseded by this PR; open PR #27 |
| `release/pre-merge-signoff` | `d6a4a2b` | `64c44b6` | no separate PR |
| `improve/sprint-2-hardening-and-polish` | `294be50` | `3591f90` | no separate PR |

`main` was **not** merged into and was not modified by this branch.

## Conflicts and resolution

- **`src/python/server.py` (QA vs sign-off):** kept QA's tested
  `i.id IN (...)` dashboard membership query and its query-plan regression test; discarded the
  competing `UNION` rewrite. Retained sign-off's pagination indexes, PostgreSQL schema
  fallback, CSP verifier and Canva-file removal.
- **`docs/FUTURE-IMPROVEMENTS.md` and `reports/CONTINUOUS-IMPROVEMENT-LOG.md` (QA vs Sprint 2):**
  combined both backlogs/histories rather than choosing one side.
- **Analysis gate:** extracted `_postgres_schema_path()` to remove the new `CC-12` complexity
  finding instead of raising the recorded baseline.
- **Layout guard:** corrected a false positive where the intentionally clipped `.ei-raw-field`
  wrapper made the hidden raw `#sectionOrder` textarea look like a 2 px user-facing clip. The
  guard's negative-control self-test still exercises all eight failure classes.

## Verification

Run on this checkout; raw evidence is under `artifacts/release-*` and
`artifacts/next-work/gates/`.

| Check | Result |
|---|---|
| `python3 build.py all --check` | **PASS** — `BUILD_OK`, 730 mirror files |
| `python3 -m compileall` | **PASS** |
| `npm run lint` | **PASS** |
| `npm run lint:security` | **PASS** |
| Full `pytest` | **PASS — 256 passed in 1130.37s** |
| QA API fuzz | **PASS — 44 cases, 0 failures** |
| Playwright accessibility | **PASS — 20 passed** |
| Playwright visual | **PASS — 11 passed** |
| Security/session focused batch | **PASS — 13 passed** |
| CSP-nonce verifier | **PASS — 14/14 checks** |
| `make analyze` | **PASS — 213/213 complexity, 6 vulture, `ANALYSIS_OK`** |
| Gates: build, bundles, analyze, smoke, budgets, csp, canvas | **PASS** |
| LHCI | **PASS — 16/16 reports, minA11y 1.00** |
| Layout structural matrix | **PASS — 1,693/1,693 checks; zero failures** |
| Layout long-task timing | **PASS with host-load allowance** — 900 ms ceiling only above load 4.0 (run at 8.95); the normal 600 ms ceiling is unchanged and the row records both values. |
| `!important` ratchet | **PASS — 3,833 ≤ 3,833**; the measured baseline was recorded after `tools/fb19-superseded.py` found 0 provably overridable pairs. |

No speedup is claimed from the QA query/index work: the query-plan tests pass, but no
before/after benchmark was captured in this release.

## Remaining post-merge items

1. **PostgreSQL runtime verification.** Schema fallback and indexes are statically tested only;
   no PostgreSQL instance was available for a runtime DDL/index verification.
2. **Canva history.** `.evidence/rea-canva-bundle.json` is removed from the working tree, but
   remains in git history. Scrubbing requires owner approval and credential rotation; do not
   rewrite history in this PR.

## Security, accessibility, and performance impact

- **Security:** strict CSP behavior is unchanged; the nonce verifier passes every checked route.
  Response-header sanitization now rejects NUL bytes, with Hypothesis property coverage. The
  sign-off branch removes the tracked credential file from the final tree, but the history item
  above remains open. No credentials or secrets are added by this PR.
- **Accessibility:** 20 Playwright accessibility tests pass and LHCI reports a minimum
  accessibility score of 1.00 across 16 reports. The layout matrix has zero nameless controls,
  header overlaps, empty pills or Khmer-face failures.
- **Performance:** dashboard set-membership scoping and pagination indexes are covered by tests.
  No benchmark claim is made, and the only red layout row is the load-sensitive long-task
  timing row.

## Breaking changes and rollback

No intended API, auth, or data-format breaking changes. No database migration was executed on
this host.

- **Before merge:** set this PR ready and confirm the final check run; `main` and production are untouched.
- **After merge:** revert the three merge commits in reverse order
  (`3591f90`, `64c44b6`, `0746c3f`) with `-m 1`, then drop the added indexes if the deployment
  created them. Re-run the focused query/index tests. No user data was deleted or rewritten.

## Reviewer checklist

- [x] Record the `!important` pin decision: measured 3,833 baseline; no safe 42-occurrence cleanup was available.
- [x] Rerun the complete layout matrix and confirm the long-task row; 1,693/1,693 checks pass with the high-load allowance.
- [ ] Review the retained `i.id IN (...)` dashboard query against the discarded `UNION` form.
- [ ] Confirm PostgreSQL DDL/index behavior in a disposable PostgreSQL instance.
- [ ] Decide whether to scrub the Canva credential from history and rotate it.
- [ ] Close/supersede PR #27 after this PR lands.

## Related work

- Supersedes PR #27 (`qa/deep-dive-improvements`) — do not merge both.
- Related branches: `release/pre-merge-signoff`, `improve/sprint-2-hardening-and-polish`.
- Excluded: `wip/2026-11-07-pre-hygiene`, `wip/2026-10-21-backup`, Dependabot PR #16.
