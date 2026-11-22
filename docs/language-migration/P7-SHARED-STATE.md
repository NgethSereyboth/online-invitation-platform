# P7 — Shared-state inventory (blocks S6)

**Date:** 2026-11-14 · **Plan:** `language-optimization-plan-v3.1.md` §4 (P7), §5 (S6)
**Question:** when a second backend serves requests, which state is in two places at once?
**Status:** inventory **complete for the state found in the code**. Nothing here is fixed by
this document; it assigns each item a treatment and the step that owes it.

Legend: **shared** = lives in the database, safe across processes · **local** = lives in one
process, doubles or splits the moment a second one runs · **disk** = per-data-directory.

---

## 1. The inventory

| # | State | Where | Kind | What breaks with 2 backends | Treatment | Owes |
|---|---|---|---|---|---|---|
| 1 | `RATE_BUCKETS` — RSVP 12/60 s per IP+slug, login 30/600 s, register, API keys | `server.py:396`, `rate_limit()` `server.py:4561–4581` | **local** | Two processes hold two bucket sets, so a client alternating backends gets **double the budget**. This is the plan's own example and it is real. | Share via Redis when `REDIS_URL` is set; otherwise **pin every rate-limited route to one backend**. Never "average" the two. | S6 |
| 2 | `STUDIO_BACKUP_LOCKS` | `server.py:398` | **local** | Two backup runs for the same workspace can start concurrently, both writing a backup artefact. | Pin studio-backup routes to one backend, or use a DB advisory row. | S12c |
| 3 | `PRESENCE_STATE` + `PRESENCE_LOCK` | `server.py:456–457`, `current_presence()` `460–477` | **local, Redis-first** | With `REDIS_URL` the truth is Redis (fine). Without it, each process sees only its own presence and the union is never computed → users appear offline to each other. Target A runs **without Redis**, so this is the live deployment's behaviour. | Pin presence routes, or require Redis for the parallel period. | S6 / S12a |
| 4 | Account lockout (`users.failed_login_attempts`, `failed_login_first_at`, `locked_until`) | schema `server.py:1878`, logic `7415–7462` | **shared**, **not atomic** | Counters are read, then written with a computed value (`SELECT` → `new_attempts=prev+1` → `UPDATE`). Two concurrent failures across processes both read N and both write N+1, losing a count; 5 attempts can take more than 5 failures to lock. | Accept (weakens a brute-force control) or make it a single conditional `UPDATE … SET failed_login_attempts=failed_login_attempts+1` with the window in `WHERE`. Decide before S9 ports it — porting the race is worse than fixing it once. | S9 |
| 5 | JIT elevation requests/grants | `ai_agent/jit_elevation.py` (`JITElevationManager`, DB schema) | **shared** | Reads and writes go through the DB; no in-process cache was found. The repo already has an atomicity test (`jit_elevation_atomic_test`). | No change needed; S6 must re-run that test across the boundary. | S6 |
| 6 | `idempotency_records` (24 h dedupe) | DB; swept by `platform_scheduler_v32.py:17` | **shared** | Correct across processes *if* the insert is a uniqueness constraint. Verify the constraint, not the convention, before S6 signs off. | Verify unique key. | S6 |
| 7 | Collaboration revisions / Lamport state | DB via the platform service (`platform_v32/`, v31 + v52 endpoints) | **shared** | Revision ordering is DB-mediated, so it survives two backends. Risk is **single-writer compaction**: two compactors can race. | Pin compaction to one backend (compaction is not a request-handled action). | S12a |
| 8 | Job queue claim | `platform_v32/jobs.py:65,72` (`platform_jobs`) and `server.py:claim_background_job` (`background_jobs`) — `SELECT …` then `UPDATE … WHERE id=? AND status/state='queued'` with a `rowcount` check | **shared, atomic; Node lease landed 2026-11-22** | Both claims are compare-and-swaps, so **double-claiming is not the risk**; recovery was. `services/api-node/lib/jobs.mjs` claims either table with `FOR UPDATE SKIP LOCKED`, records `lock_owner`/`lease_expires_at`, and only that owner can renew or release. A running row is stale at lease expiry, or after a 30-minute no-touch window when Python owns it (Python's sweep covers `background_jobs` only). Python's `JobQueue._run` now requires the `claimed → running` CAS, so it cannot execute a row Node already claimed. Python's completion stays unconditional and its workers still rely on the sweep. | Port the runners (webhook/storage/media and platform kinds); give Python owner-checked completion if it ever runs alongside Node workers. | S12b |
| 9 | Sessions (`sessions` table, `token_hash`) | DB, `user()` `server.py:4461–4484` | **shared** | A session created by one backend is valid in the other. This is the part S6 can rely on. | None; S6 proves it with the cross-backend test. | S6 |
| 10 | Image / social-card caches | `DATA/image-cache`, `DATA/social-cache` (`server.py:300–350`) | **disk, per data dir** | Two processes sharing one data dir share the cache (ok); two data dirs duplicate entries (waste, not corruption). | No action; document that the parallel run must share one data dir on Target A. | S4 |
| 11 | Field-encryption key | `core/crypto.py` — env or sidecar | **per process** | Two processes must resolve the **same** key. Different `EINVITE_DATA_DIR` values mean different sidecar keys and unreadable cross-written rows. | Assert key fingerprint equality at boot in the parallel run (P6 §8 gives the diagnostic). | S5 |
| 12 | Plan limits / tier prices / allowlists | module constants, `server.py:401–420` | **code** | Not state, but a divergence source: two backends deployed from different commits enforce different limits silently. | Deploy both from one commit during a wave; assert a build id. | S2 |

---

## 2. What this changes about the plan

- **S6's test list is correct but its order is not.** Items 1 and 3 fail on Target A *today*
  because Redis is optional and the running deployment has none. S6 should verify those two
  first; the session/CSRF proof (item 9) is the easy half.
- **S12b**: the plan says to add a lock before any job runs in Node. The claim is already
  atomic. The missing piece was recovery of stale `claimed` rows, which is a different (and
  smaller) change — and it is also a bug in the single-backend deployment, not only a
  migration risk. Node's lease landed for both queues on 2026-11-22; Python's background workers
  still recover through the 30-minute sweep, platform jobs have no Python recovery, and Python
  completion remains unconditional.
- **S9**: porting the lockout read-modify-write preserves a race. That needs an owner answer,
  because "byte-identical" and "don't port a known race" conflict.

---

## 3. Verification S6 must produce (from the plan, made concrete)

1. A session created on Python authenticates on Node, and the reverse.
2. Both backends reject a mismatched CSRF token, with the same status and body.
3. A rate-limited client cannot double its budget by alternating backends
   (`RATE_BUCKETS` shared or the route pinned).
4. Lockout counts persist across the boundary — and the concurrency case in item 4 is
   documented as accepted or fixed.
5. Presence written on A is visible on B when Redis is absent (item 3) — this is expected to
   **fail** until the treatment is applied; recording it as a known gap is the honest start.
6. A job claimed on A is not executed on B, and a stale claim is recovered after a worker
   kill.

---

## 4. Method and limits

- Found by reading `src/python/server.py`, `src/python/core/{db,crypto}.py`,
  `platform_v32/jobs.py`, `ai_agent/jit_elevation.py`, `platform_scheduler_v32.py`, and by
  grepping every module-level mutable literal in `server.py`.
- Not covered: state inside the browser bundles (client-side caches are per tab and outside
  the plan's scope), and Redis key names beyond presence (`redis_client()` call sites were
  only inspected where they define behaviour above).
- Grep for module-level mutable state is only as good as its pattern (`NAME = {`, `[`, `set(`).
  A cache created lazily inside a function would not appear. The inventory is therefore
  "everything declared at module level plus whatever the auth/job/collab paths read", not a
  proof of absence.
