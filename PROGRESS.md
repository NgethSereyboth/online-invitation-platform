# PROGRESS — autonomous mission log

## Current status
- **Branch:** `chore/cleanup`, local commits only (OD-3). Nothing pushed.
- **Queue of record:** `docs/NEXT-WORK.md` — 18 open defects, 5 untriaged suite failures, 36 work-order
  tasks, 18 owner decisions, 12 verification debts. History: `docs/HISTORY.md`.
- **Step 1 (finish leftover work):** in progress. Two root causes diagnosed on 2026-11-01.
- **Live site:** not yet redeployed in this mission. Deploy surface is `deploy/sites/` + `deploy/local/`;
  the Python backend runs on this PC and Sites hosts the front end. Deployment is Step 5, after the
  first sweep.
- **Baseline already measured:** build/bundles/smoke green; layout grazed 600 ms once and passed on a
  quiet rerun; pytest **5 failed / 218 passed** (15:01). Full log under `artifacts/next-work/gates/`.

## Log

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

## Open questions
- **Live deploy target:** `deploy/sites/site-id.txt` exists but no deployment was performed in this
  mission. If the Sites project is not the intended target, say so; otherwise Step 5 deploys there.
- **`#templatePackGallery` injection:** module path is relative (`template-pack-gallery.js`) and the
  mirror for the server root is being checked; the four browser failures are diagnosed but not fixed.
