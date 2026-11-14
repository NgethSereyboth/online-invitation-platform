# S6 · Session, CSRF and shared-state interoperability

Status: **partially complete 2026-11-14.** The Node side is implemented and unit-tested; the
cross-backend runtime proof is **blocked by Python's PostgreSQL path**, which S6 discovered to be
incomplete (defects #26 and #27). Plan reference: §5 S6; inventory: `P7-SHARED-STATE.md`.

## What exists

```
services/api-node/lib/session.mjs       cookie parsing, SHA-256 token lookup, idle timeout,
                                        once-a-minute last_seen touch, CSRF guard
services/api-node/lib/auth-routes.mjs   GET /api/auth/me, POST /api/auth/logout
services/api-node/test/session.test.mjs 9 tests over a stub query layer
tools/session-parity.py                 cross-backend harness (blocked, see below)
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

## What S6 found instead: Python's PostgreSQL path never worked

The cross-backend test needs both backends on one database, which is what **D8** chose. Starting
Python with `EINVITE_DATABASE_URL` failed, and each failure was a real portability bug:

1. **`BLOB` does not exist in PostgreSQL.** `platform_v32/schema.py` declares the V52 collaboration
   tables with SQLite's binary type. PostgreSQL parses the statement even when `CREATE TABLE IF NOT
   EXISTS` is a no-op, so boot aborted in an `InFailedSqlTransaction`. **Fixed** in the PostgreSQL
   adapter (`server.py`): ` BLOB` → ` BYTEA` for `CREATE TABLE` statements.
2. **`_try()` poisoned the transaction.** The helper swallows exceptions, which is harmless on
   SQLite but aborts the whole PostgreSQL transaction, so every later statement failed. **Fixed**
   in `platform_v32/schema.py` with a savepoint per statement, giving both backends the behaviour
   the callers already assumed.
3. **The core schema is SQLite-only — not fixed.** `PRAGMA table_info(...)` (12 call sites) is
   SQLite syntax, and the entire core DDL, including ~50 runtime `ALTER`s, lives inside
   `connect_sqlite()`. `connect_postgres()` applies only `docs/postgres_schema.sql`, which is
   missing `users.email_hash`, `users.suspended_at` and `users.session_never_expires`. Result: a
   *fresh* PostgreSQL database — even one Python itself bootstrapped — lacks those columns, and
   `/api/auth/me` closes the connection instead of answering. A new `_table_columns()` helper now
   does backend-appropriate discovery (information_schema on PostgreSQL), but nothing runs the
   core `ALTER`s on PostgreSQL yet. Recorded as **defect #27**; it blocks any PostgreSQL parallel
   run and therefore the rest of S6's proof.

## Verification (run 2026-11-14)

| Check | Result |
|---|---|
| Service tests (`npm test`, stub DB) | **26 passed** — includes all four CSRF rejection paths and the exact hashes sent to the query |
| Python boots on PostgreSQL after fixes 1–2 | **yes** (fresh database, no traceback) |
| SQLite boot unaffected | `/api/health` 200, `/checkin` 200, zero tracebacks |
| Targeted Python tests | 7 passed (`security_field_encryption`, `webhook_signing`, `jit_elevation_atomic`) |
| Cross-backend session proof (`tools/session-parity.py`) | **not run to completion** — Python answers `/api/auth/me` by dropping the connection because the runtime columns are absent (fix 3) |

## Shared-state treatments decided by this step

- **Rate limiter (`RATE_BUCKETS`)** — the plan's own example. It stays process-local, so **every
  rate-limited route is pinned to Python** during the parallel run; Node must not serve them, or a
  client could double its budget by alternating. Node implements no rate limiting, which is the
  pinning by construction.
- **Presence** — Redis-first in the repo and Redis is optional; with no Redis the union is never
  computed. Presence routes stay pinned to Python until a shared store exists.
- **Lockout counters** — shared but not atomic (read-modify-write). Porting the race is worse than
  fixing it; decision deferred to S9 with the owner, as P7 recorded.

## Honest scope

- The `/api/auth/me` body is compared field-by-field once Python can answer; until defect #27 is
  fixed, the Node route is verified only against a stub and against a seeded schema in unit tests.
- Logout's cookie clearing is implemented but its `Set-Cookie` pair is not byte-compared with
  Python's two headers (Python sends both cookies in one `Set-Cookie` array).
