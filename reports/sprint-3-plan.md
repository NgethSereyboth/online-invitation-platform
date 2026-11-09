# Sprint 3 Plan — post-consolidation hardening

**Status:** **Blocked until the consolidated draft PR merges.**
**Entry point:** `release/consolidated-2026-11-08` → `main`.
**Rule:** do not start these on top of the unmerged release branch. Rebase each task onto
`main` after the consolidated PR lands, or carry it as a separately reviewed branch.

## Goal

Close the four release caveats without weakening any gate:

1. make the `!important` ratchet honest;
2. make the layout timing check reproducible on a quiet host;
3. verify the PostgreSQL fallback and indexes against a real disposable instance;
4. remove the Canva credential from history with owner approval.

## Workstreams

### S3-1 — `!important` ratchet decision and cleanup

**Owner:** CSS owner + release owner.
**Problem:** release total 3,833; `main` 3,829; frozen pin 3,791. The consolidated release adds
four intentional occurrences in `src/css/dashboard-page.css`; the rest is pre-existing debt.
**Tasks:**

- classify the 3,829 `main` occurrences by file and identify the highest-value removable rules;
- remove or replace `!important` where specificity and cascade layers can carry the rule;
- regenerate bundles and run the visual/a11y suites after each batch;
- lower the pin only after the measured count is below it; never raise the pin merely to pass.

**Acceptance:** count ≤ pin; inventory gate green; visual and a11y evidence attached; no
regression in dashboard/template-select or editor behavior.
**If 42 removals are not safe:** obtain an explicit owner decision to raise the pin to the
measured `main` count plus new occurrences, and record that decision in the release notes.

### S3-2 — layout long-task reproducibility

**Owner:** frontend performance owner.
**Problem:** full matrix runs produced one long-task row at 711 ms (375×667 light en) and one at
602 ms (1440×900 light en) against a 600 ms ceiling under load average ~9. A targeted
1440×900 dark km run passed all 30 checks. No product code in the consolidated merge adds
index-page boot work.
**Tasks:**

- rerun the full layout matrix on an idle host and capture load average, CPU and result;
- if it still fails, profile the editor boot path and identify the single long task before any
  ceiling change;
- consider separating structural layout checks from the performance budget, or documenting a
  host-load allowance, but only with measurements;
- keep the `#sectionOrder` clipped-ancestor fix and its negative-control self-test.

**Acceptance:** three consecutive full layout runs on an idle host, or a measured fix that
brings the worst editor task under 600 ms. Do not raise the 600 ms ceiling without benchmark
evidence and owner approval.

### S3-3 — PostgreSQL runtime verification

**Owner:** data/platform owner.
**Problem:** the sign-off branch adds schema fallback and pagination indexes; this host only
ran static tests. The release packet explicitly says it is not signed off on PostgreSQL.
**Tasks:**

- start a disposable PostgreSQL instance;
- run the migration/schema path and create the added indexes;
- exercise the dashboard list query and the `i.id IN (...)` membership path;
- run the relevant tests against PostgreSQL, including the fallback path;
- record exact commands, versions, plans and results; destroy the instance.

**Acceptance:** migration/index creation succeeds on a clean database; query tests pass; no
SQLite-only assumptions; evidence attached to the next release packet.

### S3-4 — Canva credential history scrub

**Owner:** security owner; requires explicit approval.
**Problem:** the credential file is removed from the tree but remains in git history.
**Tasks:**

- confirm whether the exposed credential is still valid and rotate/revoke it first;
- approve a history rewrite window and coordinate all clones/forks;
- rewrite history with the approved tooling, force-push only with explicit authorization;
- verify the file is absent from all reachable refs and document the new SHAs.

**Acceptance:** credential rotated; file absent from history; no secret printed in logs or
reports; all collaborators re-cloned/re-synced. This cannot be done as part of the consolidated
PR.

### S3-5 — post-merge closure

**Owner:** release owner.
**Tasks:**

- merge the consolidated PR only after S3-1/S3-2 conditions are cleared;
- close/supersede PR #27 and confirm the QA branch is merged before deleting it;
- keep `wip/*` safety snapshots untouched;
- update `docs/NEXT-WORK.md` and the owner queue with the resolved/remaining items;
- run the full release matrix once on the merged `main` tip.

**Acceptance:** `main` contains the release; all gates reported honestly; no orphaned branches
deleted without merge confirmation.

## Suggested order

1. S3-1 decision (unblocks the actual merge).
2. S3-2 quiet-host rerun (cheap, can run in parallel with S3-1 analysis).
3. S3-3 PostgreSQL verification (independent, needs a disposable instance).
4. S3-4 history scrub (security-sensitive; separate approval).
5. S3-5 closure after the consolidated PR merges.

## Out of scope

- New product features.
- Re-merging the excluded `wip/*` snapshots.
- Raising any analysis, layout or `!important` baseline without measured evidence.
- Force-pushing `main` or rewriting shared history without explicit owner authorization.
