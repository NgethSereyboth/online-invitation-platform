# Branch Consolidation Map — 2026-11-08

**Release branch:** `release/consolidated-2026-11-08` (created from `main` at
`140aa77491e1b712e38beeb564f9f1482bd6d1e2`)
**Policy:** no merge into `main`; no force-push; no branch deletion until merge confirmation.

## Base

| Ref | SHA | State |
|---|---|---|
| `main` | `140aa77491e1b712e38beeb564f9f1482bd6d1e2` | clean base |
| `origin/main` | `140aa77491e1b712e38beeb564f9f1482bd6d1e2` | matches local `main` |

## Branches with commits not in `main`

| Branch | Base | Ahead | Behind | Open PR | Dependency / overlap | Decision |
|---|---|---:|---:|---|---|---|
| `qa/deep-dive-improvements` | `140aa77` | 6 | 0 | **#27**, draft, `MERGEABLE` | None declared; base QA hardening | **Merge first** |
| `release/pre-merge-signoff` | `140aa77` | 1 | 0 | none | Overlaps QA on `list_invitations`, indexes and `server.py`; no declared branch dependency | **Merge second, conditional on a safe conflict resolution** |
| `improve/sprint-2-hardening-and-polish` | `140aa77` | 5 | 0 | none | Adds add/add report files versus QA; independent tooling/security work | **Merge third, keeping the analysis gate last** |
| `wip/2026-11-07-pre-hygiene` | `9a0bf82` | 1 | 27 | none | Old safety snapshot of a pre-hygiene working tree | **Exclude — snapshot, not release work** |
| `wip/2026-10-21-backup` | `84c2aad` | 1 | 297 | none | Old safety snapshot from 2026-10-21 | **Exclude — snapshot, not release work** |

All other local heads are already contained in `main` (`ahead=0`): `backup/pre-cleanup`,
`chore/cleanup`, `fix/2026-10-22-open-issues`, `fix/print-popup-click-wait`,
`integration/consolidated-2026-11`, `pass/2026-10-15-a11y-and-d1b`,
`pass/2026-10-21-next-work`, and `v54-refactor-security-ui`. They are not re-merged.

## Commit inventory

### `qa/deep-dive-improvements` — PR #27, head `623b766`

- `fa716ae` — QA edge cases, accessibility, caching, visual determinism, generated bundles.
- `1129bd7` — QA continuous-improvement log.
- `29f7722` — dashboard set-membership scope and query-plan regression test.
- `6c47cb9` — full-suite contract regressions.
- `3a9719d` — release-candidate packet.
- `623b766` — final release evidence.

Changes: 69 files, +1,511/−136. The only open PR is #27 (draft); the separate Dependabot
PR #16 is not part of this release and is not merged here.

### `release/pre-merge-signoff` — head `d6a4a2b`

- `d6a4a2b` — pre-merge sign-off packet, pagination indexes, PostgreSQL schema fallback,
  CSP-nonce verifier, and removal of the tracked Canva evidence file.

The packet says it is **not signed off**: PostgreSQL DDL is not runtime-verified on this host and
the Canva credential file remains in git history pending an owner-approved scrub. Those items
must stay visible in the release PR; they are not fixed by this consolidation.

### `improve/sprint-2-hardening-and-polish` — head `294be50`

- `d639471` — baseline-diff `radon`/`vulture` analysis gate.
- `eed6bb6` — NUL stripping in `safe_header_value()` plus Hypothesis property tests.
- `a8b5631` — Sprint 2 evidence packet.
- `492cd20` — analysis gate wired into `tools/run-gates.py` and CI.
- `294be50` — Sprint 2 close documentation.

Changes: 14 files, +1,050/−7.

## Merge order and rationale

1. **QA first.** It is the larger product branch, has the only open PR (#27) and its own
   regression tests. It establishes the dashboard query and cache behavior.
2. **Sign-off second.** It adds index DDL and the PostgreSQL schema fallback. Its
   `list_invitations` UNION rewrite overlaps QA's tested set-membership rewrite, so the
   consolidation keeps QA's `IN` form and the QA test, while retaining sign-off's additional
   index/fallback/security changes. If that cannot be done without weakening either behavior,
   the merge stops and is documented.
3. **Sprint 2 last.** Its analysis gate can then inspect the combined Python tree. Its docs
   collide with QA's add/add report paths, so both histories will be preserved rather than
   choosing one side.

There is no declared parent/child dependency among the three branches; this order is chosen to
minimize semantic conflicts and to leave the static-analysis gate on the final code.

## Conflict watchpoints

- `src/python/server.py`: QA changes imports, indexes, cache policy and the dashboard query;
  sign-off changes indexes, the PostgreSQL fallback and a different query shape; Sprint 2 changes
  header sanitization. Resolve by retaining all independent fixes and one tested dashboard
  query.
- `docs/FUTURE-IMPROVEMENTS.md`: QA and Sprint 2 both add this path. Preserve both backlogs.
- `reports/CONTINUOUS-IMPROVEMENT-LOG.md`: QA and Sprint 2 both add this path. Preserve both
  histories with clear branch sections.
- Generated bundles, page manifests and mirror files: regenerate with
  `python3 build.py all`; verify with `--check`.
- Visual baselines: QA changed two committed screenshots intentionally. Verify them, do not
  refresh blindly.
- `.gitignore` / `tools/evidence/rea-canva-bundle.json`: sign-off removes the tracked file and
  ignores it. Do not read or print the file's contents; treat the history issue as an owner
  action.

## Excluded refs

The two `wip/*` branches are safety snapshots, not improvement branches. They are hundreds of
commits behind and contain no declared release dependency. They remain untouched for recovery.
