# Branch Consolidation Map — 2026-11-08

**Release branch:** `release/consolidated-2026-11-08` (created from `main` at
`140aa77491e1b712e38beeb564f9f1482bd6d1e2`)

**Policy:** no merge into `main`; no force-push; no branch deletion until merge confirmation.

**Draft PR:** [#28](https://github.com/NgethSereyboth/online-invitation-platform/pull/28)
against `main`.

## Base

| Ref | SHA | State |
|---|---|---|
| `main` | `140aa77491e1b712e38beeb564f9f1482bd6d1e2` | clean base |
| `origin/main` | `140aa77491e1b712e38beeb564f9f1482bd6d1e2` | matches local `main` |

## Branches with commits not in `main`

| Branch | Base | Ahead | Behind | Open PR | Dependency / overlap | Decision |
|---|---|---:|---:|---|---|---|
| `qa/deep-dive-improvements` | `140aa77` | 6 | 0 | **#27**, draft, `MERGEABLE` | None declared; base QA hardening | **Merged first** |
| `release/pre-merge-signoff` | `140aa77` | 1 | 0 | none | Overlaps QA on `list_invitations`, indexes and `server.py` | **Merged second, after conflict resolution** |
| `improve/sprint-2-hardening-and-polish` | `140aa77` | 5 | 0 | none | Adds add/add report files versus QA; independent tooling/security work | **Merged third, keeping the analysis gate last** |
| `wip/2026-11-07-pre-hygiene` | `9a0bf82` | 1 | 27 | none | Old safety snapshot of a pre-hygiene working tree | **Excluded — snapshot, not release work** |
| `wip/2026-10-21-backup` | `84c2aad` | 1 | 297 | none | Old safety snapshot from 2026-10-21 | **Excluded — snapshot, not release work** |

All other local heads are already contained in `main` (`ahead=0`): `backup/pre-cleanup`,
`chore/cleanup`, `fix/2026-10-22-open-issues`, `fix/print-popup-click-wait`,
`integration/consolidated-2026-11`, `pass/2026-10-15-a11y-and-d1b`,
`pass/2026-10-21-next-work`, and `v54-refactor-security-ui`. They are not re-merged.
Dependabot PR #16 is not part of this release.

## Commit inventory

### `qa/deep-dive-improvements` — PR #27, head `623b766`

- `fa716ae` — QA edge cases, accessibility, caching, visual determinism, generated bundles.
- `1129bd7` — QA continuous-improvement log.
- `29f7722` — dashboard set-membership scope and query-plan regression test.
- `6c47cb9` — full-suite contract regressions.
- `3a9719d` — release-candidate packet.
- `623b766` — final release evidence.

Changes: 69 files, +1,511/−136. This is the only release branch with an open PR (#27).

### `release/pre-merge-signoff` — head `d6a4a2b`

- `d6a4a2b` — pre-merge sign-off packet, pagination indexes, PostgreSQL schema fallback,
  CSP-nonce verifier, and removal of the tracked Canva evidence file.

The packet says it is **not fully signed off**: PostgreSQL DDL is not runtime-verified on this
host and the Canva credential file remains in git history pending an owner-approved scrub. Those
items remain visible in the release PR; this consolidation does not fix them.

### `improve/sprint-2-hardening-and-polish` — head `294be50`

- `d639471` — baseline-diff `radon`/`vulture` analysis gate.
- `eed6bb6` — NUL stripping in `safe_header_value()` plus Hypothesis property tests.
- `a8b5631` — Sprint 2 evidence packet.
- `492cd20` — analysis gate wired into `tools/run-gates.py` and CI.
- `294be50` — Sprint 2 close documentation.

Changes: 14 files, +1,050/−7.

## Actual consolidation

| Step | Merge commit | Source tip | Result |
|---|---|---|---|
| Branch map | `b9b2fcb` | release branch | Inventory and merge policy committed. |
| QA | `0746c3f` | `623b766` | Clean merge; QA dashboard query, cache policy, tests and reports retained. |
| Sign-off | `64c44b6` | `d6a4a2b` | One semantic conflict in `src/python/server.py`; resolved as described below. Indexes, PostgreSQL fallback, CSP verifier and credential-file removal retained. |
| Sprint 2 | `3591f90` | `294be50` | Documentation add/add collisions combined; analysis gate and NUL-sanitization tests retained. |
| Analysis repair | within `3591f90` | — | Extracted `_postgres_schema_path()` to remove the new `CC-12` complexity finding rather than raising the analysis baseline. |
| Layout-guard correction | `4f9759b` | release branch | Ignore controls inside deliberately clipped raw-field ancestors; this removes the false-positive `#sectionOrder` rows without weakening the guard's negative-control self-test. |

### Conflict resolution: `src/python/server.py`

QA and sign-off both changed the dashboard invitation query. The consolidation keeps **QA's
tested `i.id IN (...)` set-membership form** and its query-plan regression test, and discards
sign-off's competing `UNION` rewrite. All independent sign-off changes were retained:

- pagination indexes;
- PostgreSQL schema fallback;
- CSP-nonce verifier;
- removal of `.evidence/rea-canva-bundle.json` from the working tree.

No known behavior from either branch was intentionally dropped. The combined tree passes the
focused QA and sign-off test batches and the full suite.

### Documentation collisions

`docs/FUTURE-IMPROVEMENTS.md` and `reports/CONTINUOUS-IMPROVEMENT-LOG.md` were add/add conflicts
between QA and Sprint 2. Both histories/backlogs were combined rather than selecting one side.

## Verification snapshot

All commands were run on this checkout. Evidence is under `artifacts/release-*` and
`artifacts/next-work/gates/`.

| Check | Result |
|---|---|
| `python3 build.py all --check` | **PASS** — `BUILD_OK`; 730 mirror files checked |
| `python3 -m compileall` | **PASS** |
| `npm run lint` | **PASS** |
| `npm run lint:security` | **PASS** |
| Full `pytest` | **PASS — 256 passed in 1130.37s** |
| QA API fuzz | **PASS — 44 cases, 0 failures** |
| Playwright accessibility | **PASS — 20 passed** |
| Playwright visual | **PASS — 11 passed** |
| Security/session focused batch | **PASS — 13 passed** |
| CSP-nonce verifier | **PASS — all 14 `/` and `/checkin` checks** |
| `make analyze` | **PASS** — 213/213 complexity, 6 vulture, `ANALYSIS_OK` |
| LHCI | **PASS — 16/16 reports, minA11y 1.00** |
| Gates: build, bundles, analyze, smoke, budgets, csp, canvas | **PASS** |
| Layout structural checks | **PASS — 1,692/1,693 checks; zero structural failures after the guard correction** |
| Layout timing check | **FAIL (host-load-sensitive)** — 602 ms vs 600 ms in the final full run; 711 ms in the prior run. A separate 1440×900 dark-Khmer editor run passed 30/30; the failing light-mode cells were not individually rerun. Load average was ~9. |
| `!important` ratchet | **FAIL — 3,833 > pin 3,791** |

The source tree at the verified code tip (`3591f90`) changed **89 files, +3,451/−146**; the
guard correction adds one file and 20 lines. Release reports are separate commits.

## Open release blockers

1. **`!important` ratchet is stale, not introduced by this merge.** The release count is 3,833;
   `main` is already 3,829; the frozen pin is 3,791. QA adds four intentional occurrences in
   `src/css/dashboard-page.css`. The pin was **not** raised. This needs an owner decision (pin
   update or a 42-occurrence CSS cleanup).
2. **Layout timing is not proven on a quiet host.** Structural checks are clean, but the full
   gate's 600 ms long-task ceiling was exceeded by 2 ms while the desktop was heavily loaded.
   The failing light-mode cells were not individually rerun. Rerun on an idle host before merge.
3. **PostgreSQL DDL was not runtime-verified.** The fallback and indexes are covered by static
   tests only on this host.
4. **Canva credential history remains.** The file is removed from the working tree but was not
   scrubbed from git history; that requires owner approval and credential rotation.

## Excluded refs

The two `wip/*` branches are safety snapshots, not improvement branches. They are hundreds of
commits behind and contain no declared release dependency. They remain untouched for recovery.
