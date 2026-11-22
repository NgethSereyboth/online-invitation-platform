# S6 · Session, CSRF and shared-state interoperability

Status: **complete 2026-11-14.** `tools/session-parity.py` reports **18/18 identical** and a fresh
PostgreSQL database reaches schema parity with SQLite. Plan reference: §5 S6; inventory:
`P7-SHARED-STATE.md`.

## What exists

```
services/api-node/lib/session.mjs       cookie parsing, SHA-256 token lookup, idle timeout,
                                        once-a-minute last_seen touch, CSRF guard
services/api-node/lib/auth-routes.mjs   GET /api/auth/me, POST /api/auth/logout
services/api-node/test/session.test.mjs 9 tests over a stub query layer
tools/session-parity.py                 cross-backend proof (18 checks)
tools/pg-schema-parity.py               SQLite-vs-PostgreSQL schema drift watchdog
```

Sessions were already DB rows keyed by `sha256(token)` with a `csrf_hash` column, so **cross-backend
validity is a property of the schema**; what the port had to reproduce is the checks around it, not
the storage:

- the exact lookup (`JOIN users`, `expires_at > now`, `deleted_at IS NULL`, `suspended_at IS NULL`);
- the idle timeout — 30 minutes for `role='admin'`, `session_idle_days_nonadmin` days (default 7)
  otherwise — and the once-a-minute `last_seen_at` write;
- `guard_cookie_origin()` in the same order: `Sec-Fetch-Site` → `Origin` allow-list → double-submit
  pair (`X-CSRF-Token` vs `einvite_csrf`) → `sha256(header)` matches the session row, with Python's
  three bodies (`csrf_rejected`, `csrf_required`, `csrf_invalid`) and 403 status.

The proof is a session created once and used from both runtimes against one database: the Node
service resolves it to the same user, rejects the same bad CSRF token with the same body, and sees
state Python wrote (and vice versa).

## The detour: Python's PostgreSQL path had never worked

The cross-backend test needs both backends on one database, which is what **D8** chose. Starting
Python with `EINVITE_DATABASE_URL` failed, and each failure was a real portability bug:

1. **`BLOB` does not exist in PostgreSQL.** `platform_v32/schema.py` declares the V52 collaboration
   tables with SQLite's binary type. PostgreSQL parses the statement even when `CREATE TABLE IF NOT
   EXISTS` is a no-op, so boot aborted in an `InFailedSqlTransaction`. **Fixed** in the PostgreSQL
   adapter: ` BLOB` → ` BYTEA` for `CREATE TABLE` statements.
2. **`_try()` poisoned the transaction.** The helper swallows exceptions, which is harmless on
   SQLite but aborts the whole PostgreSQL transaction. **Fixed** in `platform_v32/schema.py` with a
   savepoint per statement.
3. **The core schema was SQLite-only (defect #27).** Every core `CREATE TABLE` and the runtime
   `ALTER`s live inside `connect_sqlite()`; `connect_postgres()` applies `docs/postgres_schema.sql`,
   which had drifted. Measured on a real pair: **6 tables and 12 columns missing**, including
   `users.session_never_expires` — so `/api/auth/me` dropped the connection instead of answering.
   **Fixed** by completing the schema file (keys and indexes included, `INTEGER` → `BIGINT` because
   these columns hold epoch milliseconds) and adding `tools/pg-schema-parity.py`, which builds a
   real SQLite schema, compares it with a real PostgreSQL database and **exits non-zero on drift**.
   `PRAGMA table_info` discovery is backend-aware now too (`_table_columns`).

## Verification (run 2026-11-14)

| Check | Result |
|---|---|
| `tools/session-parity.py`, booted database | **18/18 identical, 0 failing** |
| `tools/session-parity.py`, never-before-booted database | **18/18 identical, 0 failing** |
| `tools/pg-schema-parity.py`, both databases | **0 missing tables, 0 missing columns** (exit 0) |
| Service tests (`npm test`, stub DB) | **26 passed** — every CSRF rejection path and the exact hashes sent to the query |
| Full Python suite after the adapter/schema fixes | **301 passed** |
| SQLite boot unaffected | `/api/health` 200, `/checkin` 200, zero tracebacks |
| `build.py all --check` | `BUILD_OK`, no mirror drift |

## Shared-state treatments decided by this step

- **Rate limiter (`RATE_BUCKETS`)** — the plan's own example. It stays process-local, so **every
  rate-limited route is pinned to Python** during the parallel run; Node must not serve them, or a
  client could double its budget by alternating. Node implements no rate limiting, which is the
  pinning by construction.
- **Presence** — Redis-first in the repo and Redis is optional; with no Redis the union is never
  computed. Presence routes stay pinned to Python until a shared store exists.
- **Lockout counters** — shared but not atomic (read-modify-write). Porting the race is worse than
  fixing it; decision deferred to S9 with the owner, as P7 recorded.

## Scope notes

- `email_hash` is added but not backfilled on PostgreSQL; the parallel run starts from a fresh
  database, and a migrated one needs the same backfill the SQLite path performs on write.
- Logout's cookie clearing is implemented, but its `Set-Cookie` pair is not byte-compared with
  Python's two headers.
- `tools/pg-schema-parity.py` is a manual/CI-able check, not yet wired into the gate matrix.
