# S4 · Data layer with raw-SQL parity

Status: **complete 2026-11-14** for the first slice. Plan reference: §5 S4; driver choice from
**D8** (PostgreSQL for the parallel period).

## What exists

```
services/api-node/lib/db.mjs        pg Pool, ?→$n rewrite, deadline, schema contract, int8 parser
services/api-node/lib/queries.mjs   findUserByEmail (hash-first + legacy fallback), findGuestBySlug
services/api-node/server.mjs        boot-time schema assertion; refuses to start on mismatch
services/api-node/app.mjs           504 mapping for QueryDeadlineExceeded (Python's body + headers)
```

`pg@8.23.1` is the second and only other package in the service (D2). No ORM, no codegen, no
migration tool: **Python still owns the schema**, and the service only asserts it.

Four parity decisions, each with a reason:

| Decision | Why |
|---|---|
| `?` → `$n` with a quote/comment-aware scanner | the backend's statements are written for SQLite; a naive `replace('?', …)` corrupts `"what?"` and `-- why?` |
| `int8` parser → number when lossless | `created_at` is BIGINT; SQLite hands Python an `int`, so a string here would change the JSON on the wire. IDs above 2^53 stay strings rather than silently rounding |
| `statement_timeout` **and** `query_timeout`, both mapped to `QueryDeadlineExceeded` | `pg` reports its own timeout as `Error: Query read timeout` with **no code**, so a `57014`-only check never fires — caught by probing, not by reading |
| a **schema contract** instead of a version number | `docs/postgres_schema.sql` has no version counter to compare, so the service asserts the tables and columns its queries depend on |

## Two real findings

1. **The PostgreSQL schema file is incomplete.** `docs/postgres_schema.sql` never creates
   `users.email_hash`; `server.py:2018` adds it at boot. A fresh PostgreSQL instance is therefore
   *not* the schema `find_user_by_email` expects until Python has started once. Recorded as a
   defect rather than silently patched: **Node must not migrate**, so the parity harness applies
   the same `ALTER TABLE … ADD COLUMN IF NOT EXISTS` Python applies, and documents that a new PG
   deployment must be booted by Python before the Node service can start.
2. **`pg` timeouts are uncoded.** The first implementation checked `error.code === '57014'`; a
   `SELECT pg_sleep(1)` under a 150 ms budget raised a bare `Error`. The message pattern was added
   after observing it, and the probe now reports `QueryDeadlineExceeded after=185ms`.

## Verification (all run 2026-11-14)

| Check | Result |
|---|---|
| `tools/db-parity.py` — same fixtures through `core.db` (SQLite) and the service (PostgreSQL) | **9/9 identical**: hash hit, case/space normalisation, legacy plaintext fallback, miss, empty string, `None`, guest hit, guest miss |
| Field types | `created_at` is a **number** on both sides, including `1700000000123` and `storage_used_bytes=1234567890123` |
| `npm test` in the service | **9 passed** (placeholder scanner incl. literals/comments/escaped quotes, hash vector, deadline raise, 504 body + `Retry-After`, plus the S2/S3 tests) |
| Boot with a valid schema | logs `schema contract satisfied`, `/healthz` **200** |
| Boot against an empty database | **exit 1** with `SchemaMismatchError` — refuses to start |
| Real statement timeout | `pg_sleep(1)` at 150 ms → `QueryDeadlineExceeded` at 185 ms → 504 body with `database_timeout` |

## Known divergences (documented, not hidden)

1. **`lower()` is not the same function.** SQLite lowercases ASCII only; PostgreSQL lowercases
   Unicode. The legacy-plaintext fallback would therefore match a non-ASCII e-mail on PostgreSQL
   that SQLite misses. Every migrated row uses `email_hash`, so this only affects unconverted
   rows during the parallel period.
2. **Python's deadline is per request; the port's is per statement.** Python sets a budget on the
   request thread (`set_deadline`); Node applies `statement_timeout` plus a `withDeadline` wrapper
   per operation. A request issuing five statements can take five budgets on Node. Tighten at S7
   by wrapping the whole handler in `withDeadline`.
3. **`numeric` stays a string.** psycopg would hand Python a `Decimal`; the port leaves it as the
   driver's string to avoid a lossy float conversion. No ported query selects a `numeric` column
   yet — the first one that does must decide this explicitly.
4. **Pool size defaults to 10** (`EINVITE_DB_POOL_MAX`). Against PostgreSQL's default
   `max_connections=100`, two runtimes plus a migration session stay well inside the limit; a
   multi-instance deployment must divide that budget (R5).
