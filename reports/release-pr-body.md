# release: consolidated security, QA, and improvement branches

> **Draft — do not merge yet.** The consolidated tree is structurally green, but the
> `!important` gate is blocked by a stale baseline that `main` also fails, and the layout
> timing check needs a quiet-host rerun. See **Merge blockers** below.

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
| Layout structural matrix | **PASS — 1,692/1,693 checks; zero structural failures** |
| Layout long-task timing | **FAIL (host-load-sensitive)** — 602 ms vs 600 ms; 711 ms in the prior full run; a separate 1440×900 dark-Khmer editor run passed 30/30, but the failing light-mode cells were not individually rerun. Load average was ~9. |
| `!important` ratchet | **FAIL — 3,833 > 3,791** |

No speedup is claimed from the QA query/index work: the query-plan tests pass, but no
before/after benchmark was captured in this release.

## Merge blockers

1. **Stale `!important` pin (real blocker).** Release total: **3,833**. `main` total:
   **3,829**. Pin: **3,791**. QA adds four intentional occurrences in
   `src/css/dashboard-page.css`; the pin was not raised. Merging would carry a gate that was
   already red on `main`, but this PR cannot honestly be called fully merge-ready until the
   owner chooses either a pin update or a verified 42-occurrence cleanup.
2. **Layout timing.** Structural checks are clean, but the 600 ms long-task ceiling was missed
   by 2 ms under desktop/Electron load. Rerun on an idle host before merge; do not raise the
   ceiling without evidence.
3. **PostgreSQL runtime verification.** Schema fallback and indexes are statically tested only;
   no PostgreSQL instance was available for a runtime DDL/index verification.
4. **Canva history.** `.evidence/rea-canva-bundle.json` is removed from the working tree, but
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

- **Before merge:** close this draft; `main` and production are untouched.
- **After merge:** revert the three merge commits in reverse order
  (`3591f90`, `64c44b6`, `0746c3f`) with `-m 1`, then drop the added indexes if the deployment
  created them. Re-run the focused query/index tests. No user data was deleted or rewritten.

## Reviewer checklist

- [ ] Decide the `!important` pin: owner-approved pin change or a verified cleanup.
- [ ] Rerun the layout gate on an idle host and confirm the long-task row.
- [ ] Review the retained `i.id IN (...)` dashboard query against the discarded `UNION` form.
- [ ] Confirm PostgreSQL DDL/index behavior in a disposable PostgreSQL instance.
- [ ] Decide whether to scrub the Canva credential from history and rotate it.
- [ ] Confirm `main` remains at `140aa77` before merge.
- [ ] Close/supersede PR #27 after this PR lands.

## Related work

- Supersedes PR #27 (`qa/deep-dive-improvements`) — do not merge both.
- Related branches: `release/pre-merge-signoff`, `improve/sprint-2-hardening-and-polish`.
- Excluded: `wip/2026-11-07-pre-hygiene`, `wip/2026-10-21-backup`, Dependabot PR #16.
