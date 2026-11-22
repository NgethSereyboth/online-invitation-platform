# ADR 0001 — The language-migration pattern (freeze before the next slice)

- **Status:** Accepted
- **Date:** 2026-11-14
- **Deciders:** owner (D2 dependency set, D8 PostgreSQL, OD-3 local commits); repository gates are
  authoritative (**OD-6**)
- **Scope:** every route, query and test that moves from the Python server to
  `services/api-node/` from S8 onward. S2–S7 are the reference implementations this records.

## Context

The migration is a strangler fig: Python keeps the whole product, and one slice at a time moves to a
Fastify service that shares the same PostgreSQL database. S2–S7 built the pieces — static parity,
the query layer, Fernet field encryption, sessions/CSRF and the public read path — and each step
was proved against the running Python backend rather than against a written spec. Several bugs only
appeared when two backends touched one database (#25, #26, #27), so the pattern is worth freezing
exactly as it was verified.

This ADR is the reference every later slice copies. If a slice needs to break a rule, it amends this
ADR first and says why.

## Decision

### 1. Routing ownership is explicit and never inferred

- The router sends a path to **exactly one** backend. Node serves only the paths listed in
  `docs/language-migration/ROUTE-INVENTORY.md` as ported; everything else stays Python.
- Node's catch-all `/*` handler serves mirrored pages/assets and, for anything else, the Python 404
  body. It is **not** a production fallback — an unported path must be routed to Python, not to
  Node's 404.
- The following stay pinned to Python until the step that owns them:
  - every rate-limited route (`RATE_BUCKETS` is process-local; two backends would double a client's
    budget),
  - presence and collaboration polling (shared-state, Redis-optional),
  - auth mutations beyond the ported `GET /api/auth/me` and `POST /api/auth/logout` (S9),
  - anything reading `RATE_LIMIT`, lockout counters or `idempotency_records` without a shared store.
- Rollback is a router change, never a data change: both backends use the same schema, so flipping
  a path back to Python loses nothing.

### 2. The response contract is copied, not designed

- JSON bodies match Python field for field, including keys that are `null`, and status codes match
  (`200`, `403`, `404`, `409`, `504`). The wire shape is a contract; "equivalent" is not enough.
- JSON is UTF-8 with non-ASCII characters emitted **raw** (`ensure_ascii=False` in Python), never
  escaped as `\uXXXX`.
- Every response carries the shared header set from `lib/headers.mjs`: `x-request-id`,
  `x-content-type-options: nosniff`, `referrer-policy`, `permissions-policy` (camera carve-out only
  on `/checkin`), `x-frame-options`, COOP/CORP, CSP plus CSP-report-only and `report-to`.
- `x-request-id` is the inbound id sanitised by `safeRequestId()` — `[A-Za-z0-9._:-]`, 80 characters,
  fresh 32-hex if nothing usable remains. This is Python's `safe_request_id()`; a request crossing
  the boundary must keep one id.
- Cached responses state their caching explicitly (`no-store` for API and error paths, `no-cache`
  for pages); omission is a bug.

### 3. Errors and deadlines are centralised

- `QueryDeadlineExceeded` is mapped **once**, in the app's error handler, to Python's 504 body
  `{error, code: "database_timeout", requestId}` with `retry-after: 1`. Routes never catch it.
- Budget: `EINVITE_DB_BUDGET_MS`, default 2000 ms, applied both as `statement_timeout` server-side
  and as a client-side race, so a stalled connection still returns 504.
- Unhandled errors return Python's `{error: "Internal server error"}` and never a stack trace, SQL or
  column name. Route-specific bodies are copied verbatim from the Python handler.
- Error bodies use `jsonBody()`, which reproduces Python's `": "` / `", "` spacing for the flat
  objects these paths send.

### 4. Auth is a function called at the route boundary, not ambient middleware

- Reads that need a session call `resolveSession(db, {cookieHeader})`; it returns `null` rather than
  throwing, so a signed-out read can answer `{user: null}` like Python.
- Every **mutating** cookie-authenticated route calls `guardCookieOrigin()` **before reading the
  body**, in Python's order: `Sec-Fetch-Site` → `Origin` allow-list → double-submit pair → stored
  `csrf_hash`. Its three 403 bodies (`csrf_rejected`, `csrf_required`, `csrf_invalid`) are wire
  contract.
- Tokens are compared as `sha256` hex; cookies are `HttpOnly; SameSite=Lax`; logout clears **both**
  cookies as an array, because setting them one at a time leaves only the last.
- No route trusts a client-supplied user id, invitation id or email for authorisation; ownership is
  re-derived from the session and the row.

### 5. Data access is one thin layer plus explicit rules

- `pg` and Fastify only (D2). No ORM, no query builder, no second driver.
- SQL keeps Python's `?` placeholders; `toPlaceholders()` rewrites them to `$n` without touching
  string literals, identifiers or comments. Never hand-write `$1` — one style, one rewriter.
- `int8` is parsed to a JS number only when lossless, because Python's `sqlite3` returned an int and
  a string would change the JSON on the wire.
- Every row that may carry an encrypted field passes through `cipher.revealRow(row)` before use;
  every value written into a protected column passes through `cipher.protect(value)`.
- `assertSchema()` runs at boot against the columns the ported queries need; a half-migrated
  database refuses to start rather than 500 per request. Python still owns migrations.
- No cross-request in-process state. Caches, buckets and counters that Python keeps in memory stay
  Python-only (rule 1) until a shared store exists.

### 6. Logging is structured, correlated and redacted

- Node logs are JSON lines on stdout via Fastify/pino (`LOG_LEVEL`); Python's `EINVITE_JSON_LOGS`
  mode emits `{ts, client, requestId, method, path, message}`. Both are machine-readable; neither
  format is a stable interface for parsing beyond `requestId`, `method`, `path`, level and message.
- Every log line for a request carries that request's `x-request-id`.
- Never log: cookies, CSRF tokens, access/guest tokens, passwords, document JSON, secrets, or signed
  URLs (the signature is a bearer credential until it expires). Query strings are redacted for
  `access`, `guest`, `g`, `token` and `code`.
- The corpus is the same in both runtimes, so a log-based alert keeps working across the boundary.

### 7. Text, Unicode and the Khmer rule

- **Agents never author Khmer strings.** Khmer copy in the product is owner-authored; migrations
  carry it through byte-identically and never "fix", translate or romanise it.
- The database and wire format are UTF-8. Server code must pass strings through unchanged: no
  normalisation, no `ensure_ascii`, no locale-dependent casing. Where Python used `str.lower()` for
  identifiers, the port uses `pystr.mjs`'s Python-compatible helpers, not JS `toLowerCase()`.
- Any slice that touches user-visible strings needs a parity case containing non-ASCII text, and a
  Khmer sample supplied by the owner — an agent must not invent one.

### 8. No slice ships without a proof

A slice is "ported" only when all four exist:

1. **A parity harness** in `tools/` that runs both backends against one real PostgreSQL database
   (or the S1 record/replay harness where a DB is impossible) and makes both produce the same
   responses. Status codes, bodies and headers that matter are compared; wall-clock values
   (signatures' expiry, timestamps) are verified by recomputation, not by masking alone.
2. **Unit tests** for the pure helpers (`npm test`), so failures point at a function, not a stack.
3. **A written record** in `docs/language-migration/` stating what passed, what did not run, and
   which exit criteria are deployment steps (traffic ramp, p95) rather than code.
4. **A clean `build.py all --check`**, and the full gate matrix before a release (the matrix is the
   authority, not this ADR).

A slice that cannot be proved stays pinned to Python. "It looks equivalent" is not evidence.

### 9. Dependencies and supply chain

- The service has its own lockfile and the minimal approved set (D2): `fastify`, `pg`. A new
  dependency needs a written override, not a code review comment.
- CI audits the service lockfile; the container is built from the lockfile and verified by booting
  it and serving a page.

## Consequences

- Every later slice pays for a harness before it can merge. That is the point: three of the six
  defects found so far were invisible to single-backend tests.
- Pinned routes mean the parallel run is partially duplicated by design, not accidentally.
- The pattern is deliberately boring — copy, compare, then cut over — because the failure mode it
  defends against (silent divergence behind one database) is expensive to discover later.

## What this ADR does not decide

- Which domain moves next (S9–S12 are owner-ordered), or whether the migration continues at all past
  S8.
- Deployment topology, the 72 h shadow, and the percentage ramp: those live with the deployment
  runbooks.
- Frontend build tooling: the product stays build-tool-free; Node serves mirrored files.

## References

- `docs/language-migration/{ROUTE-INVENTORY,P2-REPORT,S1-HARNESS,CLASS-A-COVERAGE,P6-ENCRYPTION-SPEC,P7-SHARED-STATE}.md`
- `docs/language-migration/{S2-NODE-SERVICE,S3-STATIC-PARITY,S4-DATA-LAYER,S5-FIELD-ENCRYPTION,S6-SHARED-STATE,S7-PUBLIC-READ}.md`
- `services/api-node/{app,server}.mjs`, `services/api-node/lib/*.mjs`
- `docs/HISTORY.md` (defects #25–#27 and the lessons behind them), `docs/NEXT-WORK.md`
