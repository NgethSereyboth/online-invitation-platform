# PROGRESS — autonomous mission log

## Current status
- **Branch:** `chore/cleanup`, local commits only (OD-3). Nothing pushed.
- **Queue of record:** `docs/NEXT-WORK.md` — 18 open defects, **0 untriaged suite failures**, 36
  work-order tasks, 18 owner decisions, 12 verification debts. History: `docs/HISTORY.md`.
- **Step 1 (finish leftover work):** the two pre-existing suite fixes and the three editor
  baseline failures are closed. Remaining Step 1 work is the product backlog in `NEXT-WORK.md`
  (P0/P1/P2), not test triage.
- **Round 0 (baseline close-out):** `lt_4_3`, `lt_4_4` and `lt_2_2` pass — `4 passed in 51.59 s`.
  Verdicts and evidence: `bugs/round-0/FINDINGS.md`; plan: `FIX_PLAN.md`.
- **Live site:** not yet redeployed in this mission. Deploy surface is `deploy/sites/` + `deploy/local/`;
  the Python backend runs on this PC and Sites hosts the front end. Deployment follows the full
  verification batch.
- **Baseline already measured:** build/bundles/smoke green; layout grazed 600 ms once and passed on a
  quiet rerun; pytest profile before the fixes was **5 failed / 218 passed** (15:01). Full log under
  `artifacts/next-work/gates/`.

## Log

### 2026-11-01 — round 0: the three editor baseline failures
- **BUG-R0-1 (product, P1):** `typography-editor.js` installs after `inspector-reorg.js` and rebuilt
  its shell inside the legacy `#typographyControls`, which the reorg had already hidden after filing
  the controls into the visible Text group. Colour, digit-conversion and run controls were dragged
  back into a hidden container. The shell now mounts into the Text group when the reorg is present;
  the superseded `#advancedTextLayout` is removed so the id stays unique.
- **BUG-R0-2 (stale test):** the shared harness hunted a button labelled `Event details`; the rail is
  rebuilt with the label `Event` and the stable `data-studio-tab="event"` attribute. `open_studio_tab`
  now clicks that attribute (opening the tools drawer at narrow widths).
- **BUG-R0-3 (stale test):** `lt_4_4` waited for `#typographyControls` to be visible, but the
  2026-10-30 reorganisation deliberately hides it. `reveal_inspector_control` opens the real closed
  `<details>` ancestors and the test waits for `#v20RunFont`, the control it drives.
- **No assertion was weakened or removed.** `lt_2_2`'s public-render leg had already passed; the
  public page was never the failure.

### 2026-11-01 — phase-1: platform_jobs table in the SQLite bootstrap
- **Why:** `platform_v32/jobs.py` queries `platform_jobs`, but only `docs/postgres_schema.sql` created
  it. The worker raised `no such table: platform_jobs`, which surfaced as `RemoteDisconnected` in
  `ai_resource_scopes_test`.
- **Change:** the three DDL statements added to `_P2A_SCHEMA_STATEMENTS` (portable SQLite/PostgreSQL),
  so `connect_sqlite()` creates the table and both indexes on the first connection.
- **Verify:** `tests/ai_resource_scopes_test.py`; `build.py all` mirror check.

### 2026-11-01 — phase-1: guest-row actions + public 401 blocks (already shipped)
- `12087a8` delegated row actions on the stable guest-list container; `bbd3b9d` removes the signup /
  poll / album sections on a `401` instead of printing "HTTP 401" on a public invitation.

### 2026-11-01 — phase-1: gallery test aligned with the shared studio filter
- PW-7 removed the per-gallery filter chips so one toolbar filters both lists; the gallery follows
  `einvite:studio-filter`. The test still clicked the removed chips, so it timed out *after* the 36
  cards had rendered. It now drives `#studioCategory` / `#studioSearch` and asserts the same counts
  (15 wedding, 5 ceremony, 36 all, 1 on "maroon") — no assertion removed or weakened.

## Open questions
- **Live deploy target:** `deploy/sites/site-id.txt` exists but no deployment was performed in this
  mission. If the Sites project is not the intended target, say so; otherwise the verification batch
  is followed by the existing deploy path there.
- **Inspector disclosures:** the 2026-10-30 reorganisation files text controls one disclosure deep.
  Round 1 should judge whether that is acceptable interaction cost for colour/digit conversion, or
  whether the Text group should open its first sub-section by default. No change made in round 0.
