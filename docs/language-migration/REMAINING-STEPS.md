# Remaining migration steps — status and the exact text that controls each

Compiled 2026-11-14. Every still-open step below quotes the plan or decision text that blocks it,
verbatim, and names who can clear it. Anything not executed is marked **unmeasured**, never "met".
Proof references are the harnesses that actually ran; see the per-step documents for detail.

## Landed (verified locally, not deployed)

| Step | What | Proof that ran |
|---|---|---|
| S1 | Parity harness + `EINVITE_TEST_BASE_URL` | `--self-check` 95/96 identical |
| S2 | Service skeleton, `/healthz`, own lockfile | container boot; 5 tests at the time |
| S3 | Pages/assets/`/api/health`/`/i/` 404 | `tools/static-parity.py` 59/59 |
| S4 | Data layer (`?`→`$n`, int8, deadline→504) | `tools/db-parity.py` 9/9 |
| S5 | Fernet field encryption | `tools/fernet-parity.py` 11/11 |
| S6 | Sessions, CSRF, `/api/auth/me`, `/api/auth/logout` | `tools/session-parity.py` 18/18 |
| S7 | Public read path `/api/public/<slug>` | `tools/public-parity.py` 9/9 |
| S8 | Pattern ADR | `docs/adr/0001-language-migration-pattern.md` |
| S10 | Invitation reads: invitation, guests, RSVPs, versions, trash | `tools/invitation-read-parity.py` 27/27 |
| S12c (part) | `GET /api/feature-flags` public projection | `tools/feature-flags-parity.py` 4/4 |

## Still open

### S9 — auth domain

**Status:** owner-gated. No auth route is ported beyond the S6 session endpoints.

**Controlling text** (`docs/NEXT-WORK.md`, owner answer, verbatim):

> **Approved and used at S2: `fastify@5.12.8` only** (closure pinned by
> `services/api-node/package-lock.json`); each package listed at S2 and installed with
> `npm ci --ignore-scripts` into the Node service's own `package.json`/lockfile.

**Controlling text** (`language-optimization-plan-v3.1.md` §13, P3, verbatim):

> Owner-written override of "never add a dependency" (**D2**), listing each package and why

**Decider: owner only.** Argon2id cannot be implemented from `node:crypto`; every option
(pure-JS or WASM included) is a new package, and the allow-list names `fastify` only. A written D2
extension naming the package clears this. The earlier "native addon" reasoning is retracted — the
constraint is the allow-list, not compilation. Separately, the record and lockfile disagree about
`pg` (see the `D2 discrepancy` row in `NEXT-WORK.md`); that also needs the owner.

### S11 — guests / RSVPs / check-in writes

**Status:** pinned to Python by the plan's own shared-state rule, not by an owner decision.

**Evidence:** every write handler in this domain calls the rate limiter — `rsvp` (1 call),
`submit_wish` (1), `record_public_view` (1), `add_guest` (1), `update_guest` (1), `delete_guest` (1).

**Controlling text** (`docs/language-migration/P7-SHARED-STATE.md`, row 1, verbatim):

> Share via Redis when `REDIS_URL` is set; otherwise **pin every rate-limited route to one backend**.
> Never "average" the two.

**Controlling text** (`language-optimization-plan-v3.1.md` §5 S11, verbatim):

> For writes, compare the **resulting DB state on a snapshot** (Rule 8); never double-write.

**Decider: plan rule + deployment choice.** The plan permits pinning, which is what is in place, so
this is not owner-blocked — it is a deliberate "one backend" state. It becomes portable when either
(a) Redis is configured for the parallel run and Node gains a Redis client (a D2 package), or
(b) the owner accepts a shared-state store for buckets. Neither is a code-only decision.

### S12a — collaboration writes and presence

**Status:** open; pinned in part.

**Controlling text** (plan §5 S12a, verbatim):

> **S12a Collaboration (new in v3.1):** `PUT /api/invitations/{id}/collab/mutations`, Lamport
> timestamps, 409 optimistic locking, checkpoint compaction (≥ 1 checkpoint per 100 mutations or
> 60 s), polling transport. The highest-contention endpoint (L3: 20 VUs on one invitation).
> Compaction state must be single-writer.

**Controlling text** (P7 row 3, verbatim):

> Pin presence routes, or require Redis for the parallel period.

**Decider: plan precondition (single-writer) + deployment (Redis for presence).** Collaboration
snapshot responses embed presence, so porting even the read half would split presence across
processes without Redis. Writes additionally need the snapshot comparison Rule 8 requires.

### S12b — jobs and workers

**Status:** open, not started.

**Controlling text** (plan §5 S12b, verbatim):

> A job must be claimed by exactly one backend; add a lease/lock before any job runs in Node.

**Decider: plan precondition (engineering, not owner).** A lease/lock must exist first; no owner
decision is needed, but the work has not been done.

### S12c — storage, backup, analytics, reports, plugins

**Status:** analytics and jobs reads landed; backup, object storage, reports and the plugin host are open.

Landed and proven (`tools/analytics-read-parity.py`, **20/20 identical on two consecutive runs**):
`GET /api/invitations/:id/analytics`, `/analytics/live`, `/api/account/analytics/summary`,
`/api/account/analytics/creations` (sort, order, status filter, paging), `GET /api/studio/bulk-jobs`,
`GET /api/invitations/:id/materials/import-jobs`, plus `GET /api/feature-flags` from the earlier slice.
None of these handlers calls `rate_limit`, so P7 row 1 does not pin them; no D2 package is needed.

**Defect found and fixed while proving the port:** `features/analytics/queries.py` and the
reconstruction job call `ensure_schema(db)` without a dialect, which defaulted to SQLite and emitted
`AUTOINCREMENT` on PostgreSQL — every analytics read died with an unhandled error and an empty
reply there. `model.ensure_schema` now detects the dialect from the driver connection when none is
passed; Python's 24 analytics tests pass.

**Controlling text** (plan §5 S12c, verbatim):

> **S12c Storage, backup, analytics, reports, plugins:** `backup.py`, object-storage migration,
> `features/analytics`, `features/reports`, plugin sandbox host.

**Controlling text** (P7 row 2, verbatim):

> Pin studio-backup routes to one backend, or use a DB advisory row.

**Decider: plan rule for backups; engineering for the rest.** The read half of
`features/analytics` is now ported (above). Still open in S12c: `backup.py` and the object-storage
migration (pinned by P7 row 2), `features/reports`, and the plugin sandbox host — **unmeasured**.

### S13 — media pipeline

**Status:** open.

**Controlling text** (plan §5 S13, verbatim):

> **S13 · Media pipeline** — `sharp` + worker threads or a separate media service.
> `security_scanner_v54.py` and `features/malware_scanner.py` (ClamAV) gates must be preserved
> (port or sidecar). Benchmark `pyvips` against `sharp` before committing (§1.2).

**Decider: plan precondition + D2.** `sharp` is a new package outside the allow-list and the plan
requires a benchmark before committing; the ClamAV gate must be preserved.

### S14 — AI agent proxy

**Status:** open, not attempted.

**Controlling text** (plan §5 S14, verbatim):

> **S14 · AI agent** — keep `ai_agent/` as a Python sidecar behind an internal HTTP boundary.
> Node **proxies** `/api/invitations/{id}/ai/*` to it.

**Decider: deployment configuration.** No policy blocker; proving a proxy needs a running sidecar
and its internal endpoint. **Unmeasured.**

### S15 — decommission Python from the request path

**Status:** open. Not startable.

**Controlling text** (plan §5 S15, verbatim):

> **Preconditions:** every route served by Node **or proxied to the AI sidecar**; shadow diff green
> for 30 days (or replay green on every release); P1 numbers matched or beaten on each target;
> 6-platform matrix re-certified; 9 workflows and `run-gates.py` green; build-pipeline decision
> executed (§6).

**Controlling text** (plan §5 S15, verbatim):

> **Exit:** one request-serving language. Skipping S15 means the project is not done.

**Controlling text** (plan §13, D9, verbatim):

> Ship and certify a Node runtime on all 6 platforms | Required before S15; decide packaging
> (bundled runtime vs prerequisite)

**Decider: owner (D9 packaging) + deployment traffic (30-day shadow, P1, 6-platform).** Every
route is not yet ported, so the precondition cannot be met today.

### Build generators

**Status:** open, by plan design.

**Controlling text** (plan §6, verbatim):

> **Recommendation:** keep until S15, then port as S15's first task. Schedule it; do not let it
> become accidental permanent debt.

**Decider: plan schedule.** D4's answer keeps them in Python through the migration.

## Unmeasured (never claimed as met)

- **P1 load baseline.** Plan §14: *"Run the k6 baseline (P1) on each target in use. The script
  exists; no result has ever been recorded."* k6 is not installed locally; D11 (targets) is
  unanswered. No p95 number exists, so every "p95 within 10 %" exit criterion is **unmeasured**.
- **Shadow / replay at 100 % for 72 h** and the 5 %/25 %/100 % ramp — deployment actions, not run.
- **Full gate matrix** (`tools/run-gates.py`) — not re-run since S2; the checks run per step are the
  parity harnesses, `npm test`, and `build.py all --check`.
- **6-platform certification** and the 9 CI workflows — not run here; they require the owner's CI.
- **Reports, backup/object storage, plugin host, media, decommission** — no attempt made.
- **Analytics writes** (`POST /api/analytics/events`, consent/purge/export) — not ported; the ingest
  route carries `rate_limit(f"analytics-ingest:{self.client_ip()}",60,60)`, so P7 row 1 pins it.

## Summary of deciders

- **Owner only:** S9 (D2 allow-list extension), the `pg` record discrepancy, D9 packaging, D11
  baseline targets.
- **Plan rule (no owner):** S11 pinning, S12a single-writer/presence pin, S12b lease precondition,
  S13 benchmark + ClamAV, D4 build generators.
- **Deployment traffic:** P1, shadow/ramp, 6-platform, S15.
- **Unblocked but unattempted:** S12b lease work, S12c reports/backup/plugin host, S14 proxy
  (needs a sidecar).
