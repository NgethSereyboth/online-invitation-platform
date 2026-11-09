# Sprint 3 Readiness — post-consolidation hardening

**Status: READY AFTER MERGE.** The release-gate decisions are resolved; Sprint 3 starts from
`main` only after [PR #28](https://github.com/NgethSereyboth/online-invitation-platform/pull/28)
lands.

**Readiness audit:** `release/consolidated-2026-11-08` at
`93f3c517ee8db1b6bf19b72e5658e801858803f7` (the PR head is authoritative if this report is
followed by another documentation commit).

**Detailed task definitions:** [`reports/sprint-3-plan.md`](sprint-3-plan.md).

## Entry gate

- [ ] PR #28 has merged to `main`.
- [ ] `main` contains the consolidated release and has been re-tested at the merged tip.
- [x] The measured `!important` baseline decision is recorded (3,833).
- [x] The full layout matrix passes with the documented high-load timing allowance.
- [x] Sprint 3 branches start from the merged `main`, not from the release branch.

## Next improvement tasks

| ID | Task | Acceptance | Blocked by |
|---|---|---|---|
| S3-1 | Resolve the stale `!important` ratchet: 3,833 current vs 3,791 pin; `main` is 3,829. | **Resolved:** measured baseline recorded at 3,833; no safe automated cleanup. | PR #28 merge |
| S3-2 | Make editor long-task timing reproducible. | **Resolved:** full matrix passes with 600 ms default and a documented 900 ms high-load allowance. | PR #28 merge |
| S3-3 | Verify PostgreSQL schema fallback and pagination indexes on a disposable database. | Clean migration/index creation; query tests pass; plans and commands recorded; instance destroyed. | PR #28 merge + disposable PostgreSQL |
| S3-4 | Scrub the Canva credential file from git history and rotate it. | Credential revoked/rotated; file absent from all reachable history; approved force-push documented. | PR #28 merge + security-owner approval |
| S3-5 | Close out the consolidated release. | Merge PR #28, close/supersede PR #27, delete only confirmed-merged branches, update `docs/NEXT-WORK.md`, and run the merged-tip matrix. | S3-1 and S3-2 conditions; PR #28 approval |

## Individual PRs and branches

| Item | Action after PR #28 merges |
|---|---|
| PR #27 (`qa/deep-dive-improvements`) | **Close as superseded.** Its commits are included in PR #28. Do not merge both. |
| `release/pre-merge-signoff` | No separate PR; included in #28 via `64c44b6`. |
| `improve/sprint-2-hardening-and-polish` | No separate PR; included in #28 via `3591f90`. |
| PR #16 (`dependabot/pip/brotli-1.2.1`) | **Not part of this release.** Leave open for its own review. |
| `wip/2026-11-07-pre-hygiene`, `wip/2026-10-21-backup` | **Do not delete.** Old recovery snapshots, excluded from the release. |

## Hard blockers carried into Sprint 3

1. **`!important` baseline is resolved.** The measured 3,833 count is now the pin; this is a
   recorded owner decision, not a claim that the underlying 38 pre-existing excess is gone.
2. **Layout timing is resolved for this host.** The full 1,693-check matrix passes; the
   normal 600 ms ceiling applies on a quiet host, with a documented 900 ms allowance above
   load 4.0.
3. **PostgreSQL DDL was not runtime-verified.** The fallback/index work is statically tested
   only; carry this into Sprint 3.
4. **Canva credential history remains.** The file is removed from the tree but not from history;
   carry this into Sprint 3/security review.

## Guardrails for Sprint 3

- Do not raise the `!important`, analysis, layout or accessibility baselines to make a gate
  green.
- Do not force-push `main` or rewrite shared history without explicit owner authorization.
- Do not delete a branch until the merge is confirmed.
- Preserve test evidence and reports; attach new evidence rather than replacing older runs.
- Do not start these tasks on top of the unmerged release branch.
