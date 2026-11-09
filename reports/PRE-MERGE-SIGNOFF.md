# Pre-Merge Sign-off Packet

**Date:** 2026-11-08
**Branch:** `release/pre-merge-signoff` (created from `main` at `140aa77`)
**Scope:** CSP nonce verification, `list_invitations` pagination/index validation, Canva evidence disposition.

## Status

| Area | Result |
|---|---|
| CSP style nonce (`/` and `/checkin`) | **PASS** — header nonce present, no `'unsafe-inline'`, nonce-bearing probe applied, 0 style-src violations |
| SQLite pagination indexes and query plans | **PASS with caveat** — no full-table scan on `invitations`; free-text search still scans the member's rows by design |
| PostgreSQL index DDL | **NOT RUNTIME-VERIFIED** — no PostgreSQL binaries on this host; schema changes are DDL-only here |
| Canva evidence history | **NOT SCRUBBED** — file is untracked and ignored, but still present in git history; owner action required |
| Overall sign-off | **NOT SIGNED OFF (conditional)** — see the human checklist |

No merge was performed. No destructive database command was run. No history rewrite was executed.

## Base-state correction

The mission brief says `integration/consolidated-2026-11` is checked out and a "Mega PR" is open against `main`. That is stale:

- PR #25 is already **MERGED** at `adf703b`.
- PR #26 is already **MERGED** at `140aa77`.
- `main` and `origin/main` are both at `140aa77`.
- There is no open Mega PR to merge. This packet is therefore a post-merge / pre-next-release gate, not a gate on an open PR.

The QA branch was created from `main` so the evidence describes the deployable head. It does not modify `integration/consolidated-2026-11`.

## Changes on this branch

| File | Change |
|---|---|
| `src/python/server.py` | Added the three list indexes at SQLite bootstrap; rewrote `list_invitations` into indexable owner/collaborator UNION branches; added a `docs/postgres_schema.sql` fallback for PostgreSQL boot |
| `docs/postgres_schema.sql` | Added the collaborator covering index, the `is_published` backfill ALTER, and both owner list indexes |
| `src/python/migrate_sqlite_to_postgres.py` | Uses the same `docs/postgres_schema.sql` fallback |
| `.gitignore` | Ignores `/tools/evidence/rea-canva-bundle.json` |
| `tools/evidence/rea-canva-bundle.json` | Removed from the index with `git rm --cached`; the file remains on disk |
| `scripts/verify-csp-nonce.py` | Standalone Playwright verifier for the enforcing CSP style nonce |
| `reports/sql/2026-11-08-invitation-list-indexes.sql` | Idempotent DBA migration for SQLite and PostgreSQL |
| `reports/csp-nonce-verification-2026-11-08.json` | Machine-readable CSP result |

## CSP nonce verification

**Command:** `.venv/bin/python scripts/verify-csp-nonce.py --json-out reports/csp-nonce-verification-2026-11-08.json`

**Result:** `PASS` (exit 0). This boots the real `src/python/server.py` through `tests/v14_test_utils.fresh_server` and drives Chromium through `tests/browser_runtime.launch_chromium`.

| Page | HTTP | CSP header | `style-src` nonce | `'unsafe-inline'` | `<style>` elements | DOM nonce check | Nonce probe | Style-src violations | Console errors |
|---|---|---|---|---|---|---|---|---|---|
| `/` | 200 | present | yes | absent | 0 | vacuous (0/0) | applied | 0 | 0 |
| `/checkin` | 200 | present | yes | absent | 0 | vacuous (0/0) | applied | 0 | 0 |

The enforcing header has the shape:

```text
default-src 'self'; script-src 'self'; style-src 'self' 'nonce-<per-response>'; ...
```

What was actually proven:

- The header exists on both HTML responses and carries a fresh `nonce-` source in `style-src`.
- `style-src` does not contain `'unsafe-inline'`.
- A nonce-bearing stylesheet injected after load was **applied** by the browser, so the policy accepts the server's nonce. This is the positive control.
- No `Refused to apply inline style` message, no other style-src console error, and no `securitypolicyviolation` event was recorded.

**Honest limitation:** both pages currently use external bundle CSS and contain **zero** `<style>` elements. The "every `<style>` has the matching nonce" assertion is therefore vacuous (0/0), not evidence that an existing inline style tag was rewritten. The new verifier will catch a regression as soon as an inline `<style>` is added, and the injected nonce probe already proves the header nonce is usable. The landing page's external stylesheet list includes a same-origin absolute URL; it loaded without a CSP error.

This does not replace the existing authenticated CSP gate (`tools/csp-violation-check.py`); it is a focused nonce/header check for these two pages.

## Database index and pagination validation

### Actual columns, not the brief's examples

`list_invitations` (`src/python/server.py`) filters `deleted_at IS NULL`, scopes to `owner_id` or an `invitation_collaborators` membership, optionally filters `archived` / `is_published`, orders by `(archived, updated_at DESC)`, and paginates with `LIMIT/OFFSET`.

The brief's examples do not exist as such:

- There is no `created_at` on `invitations`; ordering is by `updated_at`.
- There is no `status` column; status is derived from `archived` and `is_published`.
- There is no `title` column; the title lives in `draft_json.fields.names`.

### Indexes

Existing relevant indexes:

- `idx_invitations_owner` on `invitations(owner_id, updated_at DESC)`
- unique `slug`
- `idx_invitation_collaborators_user` on `invitation_collaborators(user_id, created_at)`
- primary key `invitation_collaborators(invitation_id, user_id)`
- `idx_rsvps_invitation` on `rsvps(invitation_id, created_at DESC)`

Added by this branch (idempotently, at SQLite bootstrap and in the PostgreSQL schema):

| Index | Definition | Serves |
|---|---|---|
| `idx_invitations_owner_archived_updated` | `invitations(owner_id, archived, updated_at DESC) WHERE deleted_at IS NULL` | owner scope, archived-first ordering, all list |
| `idx_invitations_owner_status_updated` | `invitations(owner_id, archived, is_published, updated_at DESC) WHERE deleted_at IS NULL` | owner + published/draft filters |
| `idx_invitation_collaborators_user_invite` | `invitation_collaborators(user_id, invitation_id)` | collaborator membership lookup and covering join |

Boot-created DDL was confirmed from a real test database: all three names and their exact definitions were present, and `GET /api/invitations` with no query string (the default `limit=-1` path) returned the expected row.

### Query rewrite

The original query used `(owner_id=? OR EXISTS(SELECT 1 FROM invitation_collaborators ...))`. With that shape, SQLite's plan for the owner/all case was:

```text
SCAN i
USE TEMP B-TREE FOR ORDER BY
```

That is a full scan of `invitations`; the new indexes alone could not fix it. `list_invitations` now builds two branches:

1. owner branch: `i.owner_id=?`
2. collaborator branch: `i.id IN (SELECT c.invitation_id FROM invitation_collaborators c WHERE c.user_id=?)` plus `(i.owner_id IS NULL OR i.owner_id<>?)`, then `UNION ALL` with the owner branch and an outer `ORDER BY archived, updated_at DESC LIMIT/OFFSET`.

This preserves the result set (including NULL-owner invitations shared with a collaborator, and no duplicate when the user is both owner and collaborator) while making both branches index-driven.

### Measured plans (12,000 invitations, 300 collaborator memberships, `ANALYZE`)

```text
[owner/all]
  SEARCH i USING INDEX idx_invitations_owner_archived_updated (owner_id=?)
  SEARCH r USING COVERING INDEX idx_rsvps_invitation (invitation_id=?)
  SEARCH c USING INDEX sqlite_autoindex_invitation_collaborators_1 (invitation_id=? AND user_id=?)
  SEARCH i USING INDEX sqlite_autoindex_invitations_1 (id=?)
  LIST SUBQUERY 6
  SEARCH c USING COVERING INDEX idx_invitation_collaborators_user_invite (user_id=?)
  USE TEMP B-TREE FOR ORDER BY

[owner/published]
  SEARCH i USING INDEX idx_invitations_owner_status_updated (owner_id=? AND archived=? AND is_published=?)
  ...
  SEARCH c USING COVERING INDEX idx_invitation_collaborators_user_invite (user_id=?)
  USE TEMP B-TREE FOR RIGHT PART OF ORDER BY

[owner/archived]
  SEARCH i USING INDEX idx_invitations_owner_archived_updated (owner_id=? AND archived=?)
  ...
  SEARCH c USING COVERING INDEX idx_invitation_collaborators_user_invite (user_id=?)
  USE TEMP B-TREE FOR RIGHT PART OF ORDER BY

[owner/search]
  SEARCH i USING INDEX idx_invitations_owner_archived_updated (owner_id=?)
  ... LIKE filter applied to the owner's rows ...
  SEARCH c USING COVERING INDEX idx_invitation_collaborators_user_invite (user_id=?)
  USE TEMP B-TREE FOR ORDER BY
```

There is no `SCAN i` or `SCAN c` in these plans. The remaining `USE TEMP B-TREE FOR ORDER BY` sorts the merged per-user candidate set; it is not a full-table scan. The collaborator branch uses the covering `(user_id, invitation_id)` index and then the invitations primary key.

### Search caveat

Free-text search uses leading wildcards:

```sql
LOWER(COALESCE(json_extract(draft_json,'$.fields.names'),'')) LIKE '%q%'
OR LOWER(slug) LIKE '%q%'
```

A leading `%` cannot use a b-tree index, in SQLite or PostgreSQL. The search path now scans only the owner/collaborator candidate rows, not the entire `invitations` table, but it is still linear in the user's library. For a large library, add SQLite FTS5 or PostgreSQL `pg_trgm` with a backfill. That is intentionally **not** in this migration: it changes the search contract, needs an extension/backfill, and should be measured separately.

### Endpoint verification

A booted-server test exercised the real endpoint:

- owner list with `limit=100`: 4 rows, all `shared=false`
- collaborator list: 1 row, `shared=true`, `collaborationRole=editor`
- `status=published`: 1 row; `status=archived`: 1 row; `status=draft`: 2 rows in expected order
- `q=ALPHA`: 1 row (title search); `q=gamma`: 1 row (slug search)
- `limit=2&offset=1`: expected 2 rows in archived/updated order
- collaborator + `status=published`: empty
- default request with no `limit`/`offset`: 200 and the expected row

Result: `LIST_ENDPOINT_OK`, `DEFAULT_LIMIT_OK`.

### PostgreSQL

The index DDL and the `is_published` backfill were added to `docs/postgres_schema.sql`. The server previously read `src/python/postgres_schema.sql`, which does not exist; `_ensure_postgres_schema` and `migrate_sqlite_to_postgres.py` now fall back to `docs/postgres_schema.sql`. The fallback resolves to the existing file in a static check.

**Not runtime-verified:** this host has no `postgres`, `initdb`, `pg_ctl`, or `psql`. The schema was not executed against a live PostgreSQL. Also note that the search SQL uses SQLite's `json_extract`, and `docs/postgres_schema.sql` defines no equivalent function; the search path must be validated/adapted before PostgreSQL production. Treat PostgreSQL production as blocked until the DBA runs the migration and an `EXPLAIN (ANALYZE, BUFFERS)` check on staging.

## Canva secret final disposition

### Current state

- Before this branch, `tools/evidence/rea-canva-bundle.json` was tracked.
- The secret content appears in history at commit `5bb5ac7`; this branch's deletion commit removes the path from the current tree.
- This branch added `/tools/evidence/rea-canva-bundle.json` to `.gitignore` and removed it from the index with `git rm --cached tools/evidence/rea-canva-bundle.json`.
- The file is still present on disk (intentionally; it was not deleted) and `git check-ignore` resolves the new rule.
- **The file's contents were not opened or printed.**
- Key rotation is **not verified** by this agent. The owner must confirm the Canva keys were rotated/revoked before the history rewrite.

### History scrub command — do not execute until rotation is confirmed

Exact command for the integration branch named in the brief:

```bash
git filter-repo --path tools/evidence/rea-canva-bundle.json --invert-paths --refs refs/heads/integration/consolidated-2026-11
```

Because PR #25 already merged that branch into `main`, the file is in `main` history too. The command that actually removes it from the deployable history is the all-refs form:

```bash
git filter-repo --path tools/evidence/rea-canva-bundle.json --invert-paths
```

Recommended safe sequence on a fresh mirror (force-push requires owner approval):

```bash
git clone --mirror <repo-url> einvite-scrub.git
cd einvite-scrub.git
git filter-repo --path tools/evidence/rea-canva-bundle.json --invert-paths
git push --force --all
git push --force --tags
```

Notes:

- `git-filter-repo` is **not installed** on this host. Install it with `pipx install git-filter-repo` (or the equivalent) before running the commands.
- `git filter-repo` refuses a non-fresh clone unless forced; use the mirror clone above rather than rewriting the working repository in place.
- The force-push rewrites `main`, the integration branch and tags. Coordinate open PRs, forks, CI caches and any local clones first.
- GitHub may retain unreachable objects after a force-push. If the secret must be unrecoverable, open a GitHub support request to purge cached views/objects after the rewrite.
- `.gitleaks.toml` currently allowlists this path (lines 21–24). Leave it in place until the history rewrite is complete; removing it earlier makes the current history fail the scan. Remove the allowlist and rerun gitleaks after the scrub.

Verification after the scrub (both must be empty):

```bash
git log --all --full-history --oneline -- tools/evidence/rea-canva-bundle.json
git rev-list --all --objects | grep rea-canva-bundle || true
```

## Verification ledger

| Check | Result |
|---|---|
| `python -m py_compile` on `server.py`, `migrate_sqlite_to_postgres.py`, `scripts/verify-csp-nonce.py` | PASS |
| `scripts/verify-csp-nonce.py` on `/` and `/checkin` | PASS, exit 0 |
| Real `/api/invitations` owner/collaborator/status/search/pagination test | PASS (`LIST_ENDPOINT_OK`) |
| Default no-query list path | PASS (`DEFAULT_LIMIT_OK`) |
| Boot-created SQLite index DDL | PASS (all three definitions present) |
| Seeded `EXPLAIN QUERY PLAN` | PASS — no `SCAN i`/`SCAN c`; temp sort only |
| `git diff --check` | PASS (exit 0) |
| `tests/smoke_test.py` | **FAIL (outside this diff):** `PUT /api/admin/users/<id>/plan` returned 403 `step_up_required`; the test does not perform the step-up. This endpoint is untouched by this branch. |
| Full pytest suite | **NOT RUN** in this pass; the last recorded full run was 237 passed in 1076.01 s before these edits. Do not treat that as coverage of this diff. |
| Live PostgreSQL schema apply | **NOT RUN** — no PostgreSQL binaries on this host. |
| Authenticated DAST on staging | **NOT RUN** — owner/manual step. |

## Human reviewer checklist

- [ ] Confirm the Canva keys have been rotated/revoked. Do not run the history rewrite before this.
- [ ] Approve the rewrite, then run the filter-repo sequence on a fresh mirror and force-push all refs/tags. Verify both post-scrub commands return nothing. Remove the `.gitleaks.toml` allowlist and rerun gitleaks.
- [ ] Apply `reports/sql/2026-11-08-invitation-list-indexes.sql` to staging PostgreSQL. Run `EXPLAIN (ANALYZE, BUFFERS)` for owner/all, published, archived and search; confirm no `Seq Scan on invitations`. Adapt/validate the `json_extract` search expression for PostgreSQL.
- [ ] Verify the staging deployment: `/` and `/checkin` return the CSP header at the edge (CDN/proxy must not strip or rewrite the nonce), no `'unsafe-inline'`, and no style-src console violations.
- [ ] Run authenticated DAST manually on staging. The pipeline evidence in this packet is unauthenticated/browser-only.
- [ ] Run the full pytest and browser suites. Note the current `tests/smoke_test.py` failure at the admin step-up endpoint; do not present the suite as green until it is resolved or explicitly waived.
- [ ] If a new PR is opened for `release/pre-merge-signoff`, review and click **Merge** only after the items above. PR #25 and PR #26 are already merged; there is no Mega PR to click.
- [ ] If the owner decides not to rewrite history, record that decision explicitly and treat the Canva keys as compromised; the file's removal from the index alone does not remove it from history.

## Evidence paths

- `reports/csp-nonce-verification-2026-11-08.json` — full CSP result, including per-page headers, nonces, probe result and console/violation lists.
- `reports/sql/2026-11-08-invitation-list-indexes.sql` — idempotent DBA migration.
- `scripts/verify-csp-nonce.py` — reproducible verifier.
