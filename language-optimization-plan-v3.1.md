# Language Optimization Migration Plan — v3.1 (Blueprint, repo-verified)

**Supersedes:** `language-optimization-plan-v3.md` (and v1, v2 before it)
**Target repo:** `einvite-platform` @ `44a25f4` (branch `improve/sprint-11-supply-chain-release`) — **verified**
**Scope:** plan only — no code written yet
**Reviewed:** 2026-11-11 against the plan text, the Freebuff work order, and the local repo

---

## 0. What changed from v3

v3.1 keeps v3's strategy (strangler fig, parallel run, shadow mode, kill criteria). It changes
three things: it fixes internal inconsistencies, it corrects facts that the repo contradicts,
and it adds the steps v3 missed.

### 0.1 Corrections forced by the repo

| # | v3 said | Repo shows | Effect on the plan |
|---|---|---|---|
| C1 | `server.py` is 12,975 lines; ROOT is `src/python/` | The real backend is `src/python/server.py` (~921 KB). Root `server.py` is a 1,179-byte forwarder (`runpy`) that many tests spawn | Contract-test base-URL switch is **not free**: the spawner (`tests/conftest.py`, `tests/browser_runtime.py`) must learn to start or target the Node service (§8) |
| C2 | Deployment is Caddy → Python/Node → shared PostgreSQL | The **running** deployment is Freebuff Sites Worker → Cloudflare Quick Tunnel → `127.0.0.1:4175` (Python, **SQLite + local media**), as systemd user units. Caddy + PostgreSQL 15 is the *reference production* deployment only (`deploy/Caddyfile`, `docs/certification/LOAD-TEST-PLAN.md`) | Two deployment targets, not one. Where traffic is split, and which DB the parallel run uses, differ per target (§3.2) |
| C3 | S5: Node `protect`/`reveal` "same algorithm, key derivation, framing" | Fernet (AES-128-CBC + HMAC-SHA256); key resolved env → sidecar file `.field-encryption-key` in the data dir → generated; optional `…_KEY_PREVIOUS` rotation key; `email_hash` lookup column; `reveal` runs at the connection boundary on **every string column**; **writes are not intercepted** and call `protect()` explicitly | S5 rewritten with a concrete spec (§5, S5) |
| C4 | S9: Argon2id verifies in Node | Argon2id (t=3, m=64 MiB, p=2) **plus** legacy PBKDF2-SHA256 (210k and 310k iterations, separate salt, `algorithm` column), rehash-on-login, and recovery codes in two formats (`$argon2…` and `pbkdf2_sha256$iter$salt$digest`). Argon2 is an *optional* dependency in Python with a PBKDF2 fallback | S9 verification list extended (§5, S9) |
| C5 | P1 targets "<100 ms p95 reads, <300 ms p95 writes" | The repo's actual budgets: RSVP burst p95 < 500 ms, AI tool call p95 < 2 s, collab mutation p95 < 500 ms, public page GET p95 < 200 ms, view-beacon POST p95 < 100 ms, zero 5xx. The "expected results" in that file are **extrapolated, not measured** | P1 and the "within 10%" gate now use the real budgets (§4, §9) |
| C6 | Gate = `build.py all --check` + 9 CI workflows | Gate of record is `tools/run-gates.py` (ten phases). Full pytest ≈ 15–18 min (252 passed in 1069 s on 2026-11-03). The layout long-task guard flaked once at its 600 ms ceiling and passed on rerun | Gate list and a flake policy added (§9) |
| C7 | "PR-sized steps", CI on PR | Repo rule OD-3: **local commits only — no push, PR, merge or tag**. `CLAUDE.md`: never add a dependency, never change a budget/threshold, agents never write Khmer | Steps are *commit-sized*; pushing is owner-held; D2 override is mandatory (§3.1) |
| C8 | S9–S13 can run in parallel with one owner each | `AGENTS.md`: Freebuff has **no subagent dispatch**. Parallelism needs human owners | Parallel band only if humans own the tracks; otherwise sequential (§6) |
| C9 | 17 HTML pages | `NEXT-WORK.md` smoke covers **16** pages; I count 16 product pages in `src/python/`. The mirror also holds fixtures (`test-a.html`…`test-d.html`, `i18n-*.html`, `pw_verify*.js`) | P2 must reconcile 16 vs 17 and decide whether fixtures are served (§4) |
| C10 | Test porting = "keep suite as HTTP contract tests" | Many tests are browser/Playwright runners, plus tests that import Python modules (`core.crypto`, `core.db`, `security_*`). Pytest collects ~250 tests, not 329 | §8 splits the suite into three classes with different treatment |

### 0.2 Fixes from the review of v3

| # | Fix |
|---|---|
| R1 | P6 (encryption spec) now blocks **S5**, not S6. P2 (route inventory) now blocks **S1**, not S3+ |
| R2 | S15 and D5 reconciled: the AI sidecar is **proxied through Node and exempt** from "all routes on Node" |
| R3 | Shadow mode no longer assumes Caddy mirrors traffic. Stock Caddy has no request mirroring (verify before assuming); the tee lives in the S1 harness or a small mirror proxy |
| R4 | The 72 h shadow window gets a replay/synthetic-traffic alternative for low-traffic deployments |
| R5 | Added: shared mutable state inventory (rate limits, lockout, JIT elevation), SQLite-vs-Postgres rule, DB connection limits, schema-migration ownership, second-runtime packaging, supply-chain coverage, passkey fields beyond the public-key format |
| R6 | Evidence section re-labelled: TechEmpower figures are 2020 and illustrative; Standish CHAOS is contested; npm versions must be re-resolved when pinning |
| R7 | New §3: how this plan sequences against `WORKORDER_FREEBUFF.md` ("do NOT migrate frameworks") |

### 0.3 What was and was not verified

| Verified in the repo | Not verified (carried from v3 as stated) |
|---|---|
| HEAD `44a25f4`; branch name | 155 `/api` paths; 716 SQL statements |
| 9 workflow files in `.github/workflows/` | 24,889 Python LOC; 226 JS files / 63,196 LOC |
| k6 script + `LOAD-TEST-RESULT-TEMPLATE.md` exist; no result file | `ai_agent` = 3,758 LOC, 80 tools, 9 providers (11 modules exist) |
| `src/python/server.py` is the real backend; root file is a shim | Where passkeys and sessions are implemented (no file named for either; probably inside `server.py`) |
| `core/crypto.py`, `core/db.py`, `core/auth.py` behaviour (first ~200 lines each) | Rest of `core/crypto.py` (`CIPHERTEXT_PREFIX`, `hash_for_lookup`) |
| Four Python build generators at repo root; `build.py` | `serve.py`/waitress and the WSGI adapter behaviour |
| `.nvmrc` and `engines.node >=22.12 <23` already present (dev tooling) | 202 mirrored JS / 138 CSS asset counts |
| Local deployment path (`deploy/local/README.md`), Caddy files, PG migration script | Test-file count of 329 (the listing is consistent in scale; I did not count) |

> **Rule for the executor:** anything in the right-hand column is a P2 task (§4), not a fact.

---

## 1. Decision basis — read before Step 1

The plan is sound regardless of these numbers, but do not carry a performance promise into a
steering meeting.

### 1.1 Performance evidence is weak and dated

TechEmpower Round 19 (2020), micro tier, as reproduced in the FastAPI maintainer discussion
(figures carried from v3, **not re-checked**):

| Test | fastapi | express | Winner |
|---|---|---|---|
| JSON serialization | 171,055 | 246,627 | Node ×1.4 |
| Plaintext | 159,445 | 369,533 | Node ×2.3 |
| Single query | 66,185 | 57,588 | Python ×1.15 |
| 20 queries | 13,022 | 4,261 | Python ×3.1 |
| Fortunes | 52,080 | 44,166 | Python ×1.2 |
| Data updates | 5,926 | 2,075 | Python ×2.9 |

Read this as "driver and configuration choices dominate", **not** as a result about today's
stacks. It is six years old. Do not put this table in front of a steering group. The honest
conclusion is the one v3 already reached: **do not promise latency improvements.** The
justification is maintainability and a single language, measured by P1, not by benchmark
folklore.

### 1.2 Where Node may genuinely win

| Area | Reality |
|---|---|
| CPU-bound image work | `sharp` beats Pillow by a wide margin, but `pyvips` runs at ~1.1× of libvips C, so the gap versus *pyvips* is small. If image speed is the goal, swapping the Python library is the cheaper half |
| High idle-connection fan-out | Only matters above the concurrency this deployment sees (reference box: 2 vCPU / 4 GB; owner's PC: one machine behind a tunnel) |
| One language across front and back end | Real, non-performance benefit. This is the justification |

### 1.3 The workload is not I/O-concurrency-bound

Synchronous DB calls, Argon2id hashing (deliberately CPU-heavy), image processing, static files
and per-invitation AI calls. A Node port that keeps blocking DB access reproduces the
threading-overhead problem reported in published WSGI→ASGI migrations.

### 1.4 Project-class risk

Standish CHAOS figures are widely quoted and widely criticised on methodology. Use them only as
loose motivation for small increments, never as a statistic. The phasing and kill criteria below
exist for that reason, not because of a percentage.

---

## 2. Strategy: strangler fig with parallel run

Run both backends against the same data and shift traffic **by route**, behind a router.

```
 browser ──▶ front router (location depends on target, §3.2)
                 │  per-route split, config-only rollback
        ┌────────┴─────────┐
        ▼                  ▼
  Python (existing)    Node/Fastify (new)         AI sidecar (Python, stays)
  src/python/          separate service  ──────▶  ai_agent/ over internal HTTP
        └────────┬─────────┘
                 ▼
        one database, one schema
```

**Rules**

1. **One database, one schema.** No schema change accompanies a port. Python must keep working
   against the same rows at all times.
2. **Route-level cutover**, never per-user flags. A page must not load half from each backend.
3. **Shadow mode before cutover.** The new route sees real or replayed requests; its response is
   compared with Python's and discarded.
4. **Rollback is a config change**, never a deploy.
5. **Feature freeze applies per phase, not globally** *(revised)*: before S8, features may land in
   Python; after S8, new **backend routes** go to Node only; frontend-only work is unaffected.
   A feature that needs a route which exists only in Python lands in Python and is added to the
   migration ledger.
6. **Decommission is a planned step (S15) with an owner and a date.**
7. **Shared mutable state is inventoried before the second backend serves a request** *(new, §5 S6)*.
8. **Shadow backends never write to the live database.** Writes are compared against a snapshot
   copy (SQLite file copy or a PostgreSQL template database), never double-applied.

---

## 3. Sequencing and constraints

### 3.1 Relationship to `WORKORDER_FREEBUFF.md` *(new)*

The work order says "do NOT migrate frameworks" and "do not rewrite what works". This plan is a
language migration. They cannot drive the same agent run. Recommended order:

1. **Track W** — finish the work order's phases on the current stack (Khmer text engine, editor
   gaps, templates, guest page, RSVP, accessibility, tests). This is mostly frontend plus a few
   routes (RSVP, personalised links, gift section, CSV export).
2. **Gate to start v3.1:** Track W's RSVP/guest routes are done and `docs/NEXT-WORK.md` has no
   open P1.
3. **Track M** — this plan, starting at P1.

If the owner wants both at once, apply Rule 5 above and record it as a decision. Never give one
agent run both documents.

**Repo constraints the executor must honour** (from `CLAUDE.md`, `AGENTS.md`, `NEXT-WORK.md`):

- No new dependency without a recorded override (**D2**, precondition P3).
- Never change a budget, threshold, frozen canvas, or `tools/lighthouserc.js`.
- Local commits only. No push, PR, merge or tag; those are owner-held.
- Agents never write Khmer. Error strings and UI text come from
  `docs/i18n/TRANSLATIONS.csv` by key or code point; the Node service copies them, never retypes.
- Rebuild from source (`python3 build.py all`). Do not stage `artifacts/`, `data/`,
  `src/python/data/`, `.claude/`, `deploy/sites/`.
- Record the migration as an owner decision in `docs/NEXT-WORK.md` and the ledger in
  `docs/HISTORY.md`. Do **not** create a competing queue (work order 9.4 forbids contradictory docs).

### 3.2 Deployment targets *(new)*

| | Target A — owner's PC (running today) | Target B — reference production |
|---|---|---|
| Path | Worker (`deploy/sites/worker.js`) → Quick Tunnel → `127.0.0.1:4175` | Caddy → app → PostgreSQL 15 + MinIO |
| Database | **SQLite** (WAL), local media | PostgreSQL |
| Process manager | systemd user units (`einvite-app`, `einvite-tunnel`) | Docker/compose or systemd |
| Where to split routes | A new local router in front of `:4175` (or by path in the Worker) | Caddy |
| Parallel-run DB rule | See below | PostgreSQL |

**SQLite rule.** Two processes can share one SQLite file in WAL mode on one host, but writers
serialise. The parallel run on Target A is allowed only if: both services set a `busy_timeout`,
write transactions are short, and the file is on a local filesystem (never a network mount).
Otherwise run the parallel period on PostgreSQL (`migrate_sqlite_to_postgres.py` exists). Decide
once, in D8.

Also note: the deploy README states the Worker's free-tier request limits apply to every proxied
call, and `PROGRESS.md` (2026-11-03) puts the Sites deployment out of scope. 100 % shadow
sampling doubles upstream load; on Target A, shadow from the S1 harness or locally, not through
the Worker.

---

## 4. Preconditions — do not start Step 1 until all pass

| ID | Gate | Why | Blocks |
|---|---|---|---|
| P1 | k6 baseline recorded as `docs/certification/LOAD-TEST-RESULT-<date>.md`, **per target** (A and/or B), using the repo's real budgets (RSVP p95 < 500 ms; AI < 2 s; collab < 500 ms; page GET < 200 ms; beacon POST < 100 ms; zero 5xx) | The script exists, the result file is only a template, and the plan's "expected" numbers are extrapolated. No before-number, no proof of no regression. Needs `EINVITE_LOAD_TEST_MODE=1` on staging (never production) | all |
| P2 | Route inventory frozen: every `/api/*` path, method, auth requirement, trailing-slash behaviour; **plus** the 16-vs-17 page reconciliation, the `PAGE_ALIASES` map, and the fixture-file decision | 155 is unverified; the inventory is the unit of accounting | **S1**, S3+ |
| P3 | Owner-written override of "never add a dependency" (**D2**), listing each package and why | A Node service cannot exist without packages. `CLAUDE.md` rejects it by default | S2 |
| P4 | Capacity decision: who owns this for 12+ months, and are they humans or a single agent | Biggest failure predictor; fixes whether the parallel band exists | all |
| P5 | `tools/run-gates.py` green on `main` **and** `python3 build.py all --check` green | Clean baseline so a red gate is never ambiguous | all |
| P6 | Byte-compatibility spec for field encryption (§5, S5) written and reviewed | Silent data corruption risk | **S5** |
| P7 | Shared-state inventory (§5, S6) written | In-process state doubles when a second backend appears | S6 |
| P8 | Deployment target and DB rule decided (D8) | Determines the router, the DB driver, and the baseline | S2 |

> **P1 decides whether the rest is worth doing.** If the Python server already meets its
> documented budgets on both targets, escalate to the owner before spending months. Stopping
> there is a decision, not a deviation.

---

## 5. The plan — phases and steps

Each step lands as one or more **local commits** and is independently revertible.

### Phase A — Foundations (serial)

**S1 · Round-trip equivalence harness** *(no production code)*
- **Build:** a harness that sends a captured request to both backends and diffs status,
  headers and body. Seed it from the P2 inventory. It also hosts the **shadow tee** (R3) and a
  **replay mode** that re-sends recorded traffic, so shadow proof does not depend on live volume (R4).
- **Verify:** runs against Python-only and reports N/N self-consistent (N from P2).
- **Exit:** every route the harness cannot exercise is a documented known gap.
- **Rollback:** none (additive).

**S2 · Node service skeleton + supply-chain wiring** *(no route ported)*
- **Build:** Fastify serving only `/healthz`. Own `package.json`, own lockfile, own container
  image; pin Node to the repo's `.nvmrc` / `engines`. **Must not touch the root `package.json`**
  (eslint, playwright, axe, SBOM tooling). Install with `npm ci --ignore-scripts`.
- **Wire in:** add the Node service to `supply-chain.yml`, `security.yml`/CodeQL, and the SBOM
  (`sbom.cdx.json` / `cyclonedx-npm`), so the new surface is scanned from day one.
- **Verify:** `/healthz` returns 200; the 9 existing workflows and `run-gates.py` still pass.
- **Exit:** service runs behind the front router at 0 % traffic.
- **Rollback:** remove the service; nothing else changed.

**S3 · Static-file and shell parity**
- **Build:** Node serves the `src/python/` mirror with identical headers, caching, range support,
  CSP and the security headers the Python server injects. Port: `PAGE_ALIASES`
  (`/templates`, `/dashboard`, `/designer` etc.), `/api/health`, `service-worker.js`,
  `manifest.webmanifest`, and the rule that a missing `/i/<slug>` returns **404 with `no-store`
  and `noindex`** (a fixed defect; do not regress it).
- **Verify:** byte-diff of every response for the product pages and every mirrored asset against
  Python. Fixtures are in or out per P2.
- **Exit:** 100 % byte-identical.
- **Rollback:** route static paths back to Python.

### Phase B — Data and trust boundary (serial, highest risk)

**S4 · Data layer with raw-SQL parity**
- **Build:** a thin query layer over the chosen driver. No Prisma/Drizzle codegen (they want to
  own the schema). Kysely only if a builder is wanted.
- **Parity items the repo makes concrete:**
  - Python writes `?` placeholders; the layer must match results on both SQLite and PostgreSQL.
  - Null/boolean/integer affinity differences between SQLite and PostgreSQL.
  - **Per-request DB deadline → 504.** Python raises `QueryDeadlineExceeded` and maps it to
    504. Node needs an equivalent (statement timeout / abort) with the same status and body.
  - Connection-pool sizing across both backends against PostgreSQL `max_connections` (R5).
- **Verify:** every ported query runs against a seeded DB and its result set and types match Python.
- **Exit:** the first slice's queries are parity-verified.
- **Schema migrations:** during the parallel period **Python owns migrations**. The Node service
  asserts the expected schema version on boot and refuses to start otherwise.

**S5 · Field-encryption compatibility** *(the step most likely to silently corrupt data — never compress it)*
- **Spec to implement (from `core/crypto.py` and `core/db.py`):**
  - Cipher: Fernet. The Fernet token format is public and small; implement it with
    `node:crypto` rather than adding a package, unless D2 approves one.
  - Token shape: `reveal` leaves any value alone unless it starts with `CIPHERTEXT_PREFIX`
    (**read the rest of `core/crypto.py` first** to confirm the prefix and `hash_for_lookup`).
  - Key resolution order: `EINVITE_FIELD_ENCRYPTION_KEY` → sidecar `<data dir>/.field-encryption-key`
    → generated and persisted. Node must read the **same sidecar file** and must never generate a
    different key. Support `EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS` (decrypt-only).
  - Toggle: `EINVITE_FIELD_ENCRYPTION` off → stop encrypting, keep decrypting.
  - Lookup: `users.email_hash` = SHA-256 of the lower-cased, trimmed email; fall back to the
    legacy plaintext column when `email_hash` is empty.
  - Read side: apply `reveal` to **every string column** of every row at the connection boundary
    (a handler must not be able to forget).
  - Write side: Python does **not** intercept writes. Every statement that writes a protected
    column calls `protect()` explicitly. Protected columns: `users.email`,
    `guests.email`, `guests.phone`, `delivery_attempts.recipient`, `audit_events.metadata_json`,
    `invitation_edit_history.diff_json`. **A missed `protect()` silently stores plaintext**, which
    reads tolerate, so a dedicated check is required (below).
- **Verify:**
  - Bidirectional: Node decrypts a Python-encrypted row and Python decrypts a Node-encrypted row,
    for every protected column, plus empty string, `None`, and maximum length.
  - Mixed-state DB: plaintext and ciphertext rows in one table both read correctly; nothing is
    double-encrypted.
  - **Plaintext-leak check:** after every Node write test, scan protected columns for values that
    are not tokens.
  - Rotation: a row encrypted under the previous key still reads.
  - Malformed key env: matches Python's documented soft-fail (open defect #13 in `NEXT-WORK.md`);
    do not "fix" it differently in Node without owner sign-off.
- **Exit:** round-trip byte-stable in both directions; leak check clean.
- **Rollback:** n/a — nothing writes until a route is cut over.

**S6 · Session, CSRF and shared-state interoperability**
- **Build:** shared session store so a session created by one backend is valid in the other;
  CSRF validation must agree. **Plus the shared-state inventory (P7):** every in-process
  structure becomes shared or pinned to one backend. Known so far:
  - `RATE_BUCKETS` rate limiter (RSVP: 12 per 60 s per IP+slug). Two processes means two bucket
    sets and effectively double the limit. Redis is optional in the repo; either share it or pin
    rate-limited routes to one backend.
  - Account lockout, JIT elevation (`ai_agent/jit_elevation.py`, `jit_elevation_atomic_test`),
    `idempotency_records` (24 h dedupe), collaboration revisions.
- **Verify:** create a session on Python and use it on Node, and the reverse; both reject a
  mismatched CSRF token; lockout counts persist across the boundary; a rate-limited client cannot
  double its budget by alternating backends.
- **Exit:** a user crosses the boundary mid-session without being logged out or gaining limits.
- **Rollback:** pin all auth routes to Python.

### Phase C — First vertical slice (proves the pattern)

**S7 · One low-risk read-heavy slice**
- **Recommended:** the public invitation read path (`GET /i/<slug>` data and public RSVP status
  read). High traffic, no write risk, easy to diff.
- **Verify:** shadow (or replay) with **zero diffs**, then 5 %, 25 %, 100 %. Shadow duration is
  72 h at 100 % *or* a replay of ≥ N recorded requests per route covering every status code,
  whichever the deployment's traffic allows (R4).
- **Exit:** 100 % traffic; error rate and p95 within 10 % of the P1 baseline.
- **Rollback:** flip the route back to Python.
- If this takes > 2.5× its estimate, stop and re-forecast (kill criterion 1).

**S8 · ADR: freeze the pattern**
- Record routing, error shape, logging, auth middleware, query conventions, deadline/504
  handling and the Khmer-string rule as the reference every later slice copies. Link it from `docs/`.
- **This is also the first legitimate stopping point** (§11).

### Phase D — Business domains

Parallel **only if humans own separate tracks** (C8) and only after S8; otherwise sequential.
Disjoint files, shadow proof before each cutover.

**S9 · Auth domain** — register, login, MFA, passkeys, CSRF, API keys, account lockout.
- **Passwords:** every seeded credential authenticates. That includes **Argon2id**
  (t=3, m=64 MiB, p=2), **legacy PBKDF2-SHA256 at 210k and 310k iterations** (hex salt, `algorithm`
  column) and **rehash-on-login** exactly as Python does it. Account for Python's optional-Argon2
  path: if a deployment ran without `argon2-cffi`, its hashes are PBKDF2 and must still verify.
- **Recovery codes:** both stored formats verify (`$argon2…` and `pbkdf2_sha256$iter$salt$digest`);
  single-use semantics preserved; the alphabet and code format are unchanged.
- **TOTP:** existing secrets stay valid; same window and drift tolerance.
- **Passkeys:** the public-key format is one risk (stored COSE bytes vs the `Uint8Array` that
  `@simplewebauthn/server` expects; the library has changed its format across majors, so budget a
  migration pass). Also test, per credential: credential-ID encoding, signature counter handling,
  transports, user handle, and RP ID/origin under **both** deployment targets (the origin differs
  between the tunnel and a production domain). *Where Python implements passkeys is unverified;
  locate it in P2.*
- **Rollback:** pin `/api/auth/*` to Python.

**S10 · Invitations, templates and the template pack** — core CRUD, optimistic revisions (409),
publish barrier, versions. Template pack is generated by Python tooling (§6), so the Node routes
only *serve* it.

**S11 · Guests, RSVPs, check-in, delivery** — the write-heavy domain.
- For writes, compare the **resulting DB state on a snapshot** (Rule 8); never double-write.
- RSVP is the primary load-test scenario (1000 VUs, p95 < 500 ms) and the hottest write path:
  re-run P1's RSVP scenario on Node before cutover.

### Phase E — Platform subsystems

**S12 · Platform subsystems** — split into separately shadowed sub-steps:
- **S12a Collaboration (new in v3.1):** `PUT /api/invitations/{id}/collab/mutations`, Lamport
  timestamps, 409 optimistic locking, checkpoint compaction (≥ 1 checkpoint per 100 mutations or
  60 s), polling transport. The highest-contention endpoint (L3: 20 VUs on one invitation).
  Compaction state must be single-writer.
- **S12b Jobs and workers:** `platform_worker_v32.py`, `platform_scheduler_v32.py`,
  `media_worker.py`, `outbound_queue.py`, `webhooks.py` (signing), `delivery_channels/`.
  A job must be claimed by exactly one backend; add a lease/lock before any job runs in Node.
- **S12c Storage, backup, analytics, reports, plugins:** `backup.py`, object-storage migration,
  `features/analytics`, `features/reports`, plugin sandbox host.

**S13 · Media pipeline** — `sharp` + worker threads or a separate media service.
`security_scanner_v54.py` and `features/malware_scanner.py` (ClamAV) gates must be preserved
(port or sidecar). Benchmark `pyvips` against `sharp` before committing (§1.2).

**S14 · AI agent** — keep `ai_agent/` as a Python sidecar behind an internal HTTP boundary.
Node **proxies** `/api/invitations/{id}/ai/*` to it. Preserve the JIT elevation and scope model
and the per-user AI rate limit (default 10 calls/min). Porting is last and optional. The reason
to defer is surface area, not language (Ollama/LM Studio/GPT4All are plain HTTP).

### Phase F — Decommission

**S15 · Remove Python from the request path**
- **Preconditions:** every route served by Node **or proxied to the AI sidecar**; shadow diff
  green for 30 days (or replay green on every release); P1 numbers matched or beaten on each
  target; 6-platform matrix re-certified; 9 workflows and `run-gates.py` green; build-pipeline
  decision executed (§6).
- **Then:** delete the Python request path (`src/python/server.py`, the root shim, `serve.py`,
  waitress/WSGI adapter). Keep Python for the AI sidecar, offline tooling, and migrations only if
  the owner chooses.
- **Packaging:** the 6-platform matrix assumes owners install this themselves. A second runtime
  (Node) must be bundled and certified on every platform, including the three Windows targets
  (D9). Do this before S15, not at S15.
- **Exit:** one request-serving language. Skipping S15 means the project is not done.

---

## 6. Build pipeline — the dependency everyone forgets

`src/python/` is a byte-compared mirror of `src/js`, `src/css`, `src/html`, produced by four
Python generators at the repo root: `build_editor_bundle.py`, `build_route_bundles.py`,
`build_page_manifests.py`, `sync_frontend_assets.py` (plus `build.py`). The template pack is also
generated by Python tooling (`tools/build-template-pack.py`, `template-pack/generator/`).
`python3 build.py all --check` is the merge gate.

| Option | Cost | Consequence |
|---|---|---|
| **Keep generators in Python** through the migration | ~0 | Node serves the mirror; Python remains build-time only. The "single language" claim is partial |
| Port generators to Node | 4 scripts + template generator + `--check` byte-equality | Needed for the honest claim; most likely to break the gate if done late |

**Recommendation:** keep until S15, then port as S15's first task. Schedule it; do not let it
become accidental permanent debt.

---

## 7. Dependency graph

```
P1..P8 (gates)
   │
   S1 ──▶ S2 ──▶ S3 ───────────────┐
            │                      │
            └──▶ S4 ──▶ S5 ──▶ S6 ──▶ S7 ──▶ S8 ──┬──▶ S9  (auth)
                                                   ├──▶ S10 (invitations)
                                                   ├──▶ S11 (guests/RSVP)
                                                   ├──▶ S12a/b/c (platform)
                                                   └──▶ S13 (media)
                                                          │
                                           S14 (AI proxy; port optional)
                                                          │
                                                          ▼
                                                  S15 (decommission)
```

**Serial spine:** S1→S2→S3, S4→S5→S6→S7→S8. **Parallel band:** S9–S13 only with human owners.
**Never parallel:** S5 with anything that writes; S12b with anything that touches the same job
tables; S15 with anything.

---

## 8. Test strategy — three classes, not one

The suite is large (pytest collects ~250 tests over a ~330-file `tests/` tree) and takes
15–18 minutes. Do not port it wholesale and do not assume it is HTTP-only.

| Class | Examples | Treatment |
|---|---|---|
| **A. Black-box HTTP/contract** | `api_contract_test`, `security_*_test` (headers, injection, tenant isolation), `public_*_test` | Keep. Point at Node via a **base-URL switch** that must first be added to the spawner (`conftest.py`, `browser_runtime.py`, root `server.py` shim usage). This is S1 work, not free |
| **B. Browser/Playwright runners** | `v17_*`, `v22_*`, `v24_*`, visual regression | Mostly backend-agnostic (they hit a URL). Run against Node after each cutover wave; keep the visual-baseline rule: never change a baseline to pass |
| **C. Python-internal** | `security_field_encryption_test`, `core.db`/`core.crypto` imports, `build_integrity_test`, generator tests | Do **not** port to Node. Keep for Python-only code that remains; replace each by a Node unit test **plus** a cross-backend parity test (S5 style) |

Rules:
1. A route is not "ported" until its Class A tests pass against Node. No manual substitute.
2. S1's parity suite is permanent and outlives the migration.
3. Any test that is slow or flaky is recorded in `docs/HISTORY.md` with its cause; never skipped.

---

## 9. Verification gates per step (definition of done)

A step is done only when **all** hold:

- [ ] Shadow diff: 0 unexpected differences (live 72 h at 100 %, **or** replay of the agreed corpus)
- [ ] Class A contract tests pass against the new backend
- [ ] p95 within 10 % of the P1 baseline **and** inside the repo budget for that scenario
- [ ] Error rate ≤ Python's; zero 5xx on the load scenarios
- [ ] `python3 build.py all --check` green
- [ ] `tools/run-gates.py` green; 9 workflows green when the owner pushes
- [ ] Rollback executed once on each deployment target in use and confirmed
- [ ] Route recorded in the migration ledger (`docs/HISTORY.md`)

**Flake policy.** The layout long-task guard has a 600 ms ceiling and has flaked under load.
A single red from a known flaky gate is rerun once with no other browser running and both runs
are recorded. A second red is a real failure. Never raise a ceiling to pass.

---

## 10. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Node is slower on DB-bound routes | High | High | P1 per target; per-step p95 gate; justify on maintainability |
| R2 | Encryption mismatch corrupts or hides data | Medium | **Critical** | S5 spec, bidirectional test, plaintext-leak check; never compress |
| R3 | A write omits `protect()` and stores plaintext | Medium | High | S5 leak check after every write test |
| R4 | Passkeys stop working | Medium | High | Credential-migration script; "all seeded credentials log in" test; both RP origins |
| R5 | Legacy password/recovery-code formats fail in Node | Medium | High | S9 verifies Argon2id, PBKDF2 210k/310k, both recovery formats, rehash-on-login |
| R6 | Session/CSRF split logs users out at the boundary | Medium | High | S6 cross-backend test |
| R7 | In-process state (rate limits, lockout, JIT) doubles or desyncs | **High** | High | P7 inventory; share via Redis/DB or pin to one backend |
| R8 | SQLite write contention with two processes | Medium | High | D8 rule; `busy_timeout`; or PostgreSQL for the parallel run |
| R9 | Two-language long tail becomes permanent | **High** | High | S15 has an owner and a date; ledger tracks % migrated |
| R10 | Build generators block the final cutover | High if ignored | Medium | §6 decision at S2, executed at S15 |
| R11 | Test suite effectively lost | Medium | High | §8 three-class split |
| R12 | Shadow mode skipped under schedule pressure | Medium | High | Rollback test is a gate item; no shadow/replay means not done |
| R13 | 6-platform certification invalidated by a second runtime | Medium | High | Package and certify Node per platform before S15 (D9) |
| R14 | New Node surface escapes supply-chain scanning | Medium | Medium | S2 wires it into `supply-chain.yml`, CodeQL and the SBOM |
| R15 | Khmer or bilingual strings drift in error paths | Low | Medium | `docs/i18n/TRANSLATIONS.csv` is the only source; no retyping |
| R16 | Migration crowds out the existing queue (`NEXT-WORK.md` lists 36 open tasks, 11 open defects, 18 owner decisions) | **High** | Medium | §3.1 sequencing; record the migration as an owner decision |

---

## 11. Cost model *(estimates, not measurements — unchanged from v3 and not validated)*

| Phase | Steps | Estimate |
|---|---|---|
| A Foundations | S1–S3 | 6–9 weeks |
| B Data/trust | S4–S6 | 6–10 weeks |
| C First slice | S7–S8 | 4–7 weeks |
| D Business domains | S9–S11 | 14–22 weeks |
| E Platform | S12–S14 | 10–18 weeks (S12a/b add to v3's figure; `ai_agent` stays a sidecar) |
| F Decommission | S15 | 4–8 weeks (generator port + Node packaging on 6 platforms) |
| **Total** | | **44–74 weeks**, single experienced engineer; shorter only with real parallel owners |

Dominated by S9 and S15. Each full gate run costs ~15–18 minutes before any browser re-runs.

### Legitimate stopping points

Pausing is a valid outcome. Stopping after **S8** leaves you with the parity harness, the
cutover pattern, a proven first slice, and the ADR. Stopping after **S1** still leaves the
single most valuable artifact in the plan.

---

## 12. Kill / pause criteria — decide in advance

Pause or abort if any occurs twice:

1. S7 takes > 2.5× its estimate.
2. Post-cutover p95 is > 25 % worse than baseline (or breaks a repo budget) and does not recover
   after two attempts.
3. Shadow or replay diffs keep appearing on routes already declared done.
4. Parity-harness upkeep exceeds ~20 % of engineering time.
5. Any data-integrity incident traced to the encryption layer.
6. A required gate can only be satisfied by changing a budget, threshold or baseline.

---

## 13. Open decisions requiring owner sign-off

| # | Decision | Recommendation |
|---|---|---|
| D1 | Business justification | Maintainability and a single language. **Not** latency |
| D2 | Override of "never add a dependency" | Required before S2; list each package |
| D3 | ORM vs raw SQL/Kysely | Raw SQL or Kysely; schema stays frozen |
| D4 | Keep or port the Python build generators | Keep through migration; port in S15 |
| D5 | `ai_agent/`: sidecar or port | Sidecar until it hurts; exempt from S15 |
| D6 | Trailing-slash and error-body strictness | Byte-identical, no exceptions |
| D7 | Does "done" require S15 | Yes, otherwise it is two systems forever |
| D8 | Parallel-run DB: SQLite-WAL multi-process or PostgreSQL | PostgreSQL for the parallel period; SQLite only with `busy_timeout` and short writes |
| D9 | Ship and certify a Node runtime on all 6 platforms | Required before S15; decide packaging (bundled runtime vs prerequisite) |
| D10 | Sequence against the Freebuff work order | Track W first, then Track M (§3.1) |
| D11 | Which deployment target(s) carry the P1 baseline | Both A and B if both are real |
| D12 | Shadow source when traffic is low | Replay corpus + synthetic load |

---

## 14. Immediate next actions

1. Finish or consciously park Track W (§3.1) and record D10.
2. Run the k6 baseline (P1) on each target in use. The script exists; no result has ever been recorded.
3. Freeze the route inventory and resolve every "not verified" row in §0.3 (P2).
4. Get D2 and D8 in writing.
5. Build S1's harness — the single highest-value artifact — including replay mode.

---

## Appendix A — Repo facts verified for this revision

- HEAD `44a25f496d9122591bf1904a52e9cc0c35b76687` on `improve/sprint-11-supply-chain-release`.
- Real backend `src/python/server.py` (≈ 921 KB); root `server.py` forwards via `runpy`.
- Modules present: `core/{auth,config,crypto,db,db_metrics,deps,preflight,privacy,resilience,security_helpers,webhooks,outbound_queue,admin_ip_allowlist}.py`; `features/{backup,reports,secrets,malware_scanner,invitation_versions,editor_comments,analytics,…}`; `security_scanner_v54.py`; `media_worker.py`; `platform_worker_v32.py`; `platform_scheduler_v32.py`; `migrate_sqlite_to_postgres.py`; `migrate_assets_to_object_storage.py`; `delivery_channels/`; root `ai_agent/` (11 modules).
- `src/python/routes/` contains only `__init__.py`: **routes live in `server.py`**, not in route modules.
- Workflows: `codeql`, `dast-authenticated`, `lighthouse`, `lint`, `publish-release-tag`, `release-drafter`, `security`, `supply-chain`, `tests`.
- `package.json` is dev tooling only (`eslint`, `@playwright/test`, `@axe-core/playwright`, `puppeteer-core`, `@cyclonedx/cyclonedx-npm`, `web-vitals`, …) with `engines.node >=22.12 <23`.
- Production Python deps are a hash-locked closure (`docs/requirements-production.lock`).
- Load-test plan, scenarios and budgets: `docs/certification/LOAD-TEST-PLAN.md`; result file is only a template.

## Appendix B — External evidence (carried from v3, not re-checked)

TechEmpower Round 19 (2020) via FastAPI discussion #7320; FastAPI benchmarks page; Django Forum
WSGI→ASGI report; libvips 8.16 whitepaper and imgproxy/pyvips benchmarks; Standish CHAOS (contested
methodology); Microsoft Learn strangler-fig pattern; SimpleWebAuthn changelog and server docs;
W3C WebAuthn Level 3. Full URLs are in v3's appendix.

**Re-resolve before pinning:** every npm version listed in v3 (fastify, @fastify/session,
@simplewebauthn/server, sharp, zod, drizzle-orm, typescript, argon2, ioredis, pg, subset-font,
fontkit). I cannot confirm several of them, including `typescript 7.0.2` and `ioredis 6.0.0`.
Run `npm view <pkg> version` at S2 and record the result.
