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
| S12c (part) | Analytics, jobs and reports reads | `tools/analytics-read-parity.py` 20/20; `tools/reports-read-parity.py` 20/20 |
| S12c (part) | Admin console reads: overview, users, users-v2, invitations, audit events (JSON + CSV), job status | `tools/admin-reads-parity.py` 42/42 |

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

**Status:** the lease/lock is implemented and proven for both job queues Node could run. The
`webhook.deliver` runner, the local-disk half of `storage.delete` and `image.derivatives` are ported
on top of it. The `social.*` card renderers, `maintenance.cleanup`, `admin.bulk_*` and the platform
runners still run in Python (`media_worker.py`, `platform_v32/jobs.py`), and `storage.delete` stays
with Python whenever object storage is configured.

**Controlling text** (plan §5 S12b, verbatim):

> A job must be claimed by exactly one backend; add a lease/lock before any job runs in Node.

**Decider: plan precondition (engineering, not owner).** A lease/lock must exist first; it now
does.

**Landed:** `services/api-node/lib/jobs.mjs` covers both queues: `background_jobs`
(webhook/storage) and `platform_jobs` (`platform_v32/jobs.py`). Each claim is one
`UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED)` that records `lock_owner` and
`lease_expires_at`; renewal and release require that owner on a `running` row. A running row is
reclaimable when its Node lease expired, or, when Python owns it (no lease), after a 30-minute
no-touch window. Python's queued-only claims cannot take a running Node row, and Node cannot take
a live Python row.
`platform_v32/jobs.py` now also requires the `claimed → running` CAS to succeed before running a
handler, so a duplicate queue entry or a row Node already claimed is not executed twice. The
storage-delete claim gained the queued-state guard the webhook claim already had.
`lock_owner`/`lease_expires_at` are declared in the SQLite and PostgreSQL schemas; Node adds them
lazily to a database booted by an older build. Python's own stale sweep covers `background_jobs`
only; it has no platform-job recovery, so Node's lease is the recovery path there.

**Webhook runner:** `services/api-node/lib/webhook-runner.mjs` is the Node port of
`process_webhook_jobs()`, with `bin/webhook-runner.mjs` as the standalone worker (`npm run
webhook:runner`, `--once` for one pass). It claims through the lease, signs `t=<ms>,v1=<hmac>`
with the endpoint secret, validates and pins the destination address (https/public unless
`EINVITE_ALLOW_PRIVATE_WEBHOOKS` is set), refuses redirects, reads at most 64 KiB, and matches
Python's completion rules: 2xx done, 400/3xx final, 408/409/425/429/5xx retried at 1/2/4/8 s,
the fifth failure final, missing/inactive endpoint `done` with `endpoint removed`, and the
endpoint's `last_delivery_at`/`last_status`/`failure_count` updated the same way.

**Storage-delete runner:** the same module's `processStorageDeleteJobs()` port covers the local
half of `process_storage_delete_jobs()`: basename sanitation, upload removal, and the exact
`image-cache` entries keyed by `sha256(f"{path}|{hash[:20]}|{width}|{format}")` for all 30
width/format pairs. It keeps Python's 30 s base, doubling to a 1,920 s cap and **no terminal
failure**; a missing file is a successful no-op. When `EINVITE_OBJECT_STORAGE_BUCKET` is set the
Node runner claims no `storage.delete` job, so Python's boto3 path remains the only deleter until
S12c ports object storage. **Media-derivative runner:** `services/api-node/lib/media-runner.mjs` ports `media_worker.py`'s
`image.derivatives` handler — the one media kind that is a resize plus an encode rather than a
Pillow text composition. It warms the same 320/768/1440 WEBP variants at quality 84, keys each file
by `sha256(f"{basename}|{sha256(source)[:20]}|{width}|format")` under `image-cache/`, reuses an
existing entry, never upscales (it reproduces PIL's round-half-even for the resized height), honours
`EINVITE_MAX_IMAGE_DIMENSION`/`EINVITE_MAX_IMAGE_MEGAPIXELS` and evicts by the same file/byte
budgets. A non-image or GIF payload is a no-op, a failing width stops the loop, and a missing source
completes as a no-op; a payload without `path` fails. Failures requeue with Python's 60 s doubling
capped at 3,600 s and are final on the fifth attempt, with `available_at` written on both states.
When `EINVITE_OBJECT_STORAGE_BUCKET` is set the Node runner claims no `image.derivatives` job,
because the source bytes come from boto3. `sharp@0.35.5` is the owner-approved D2 extension
(2026-11-22) for this handler only; `social.warm`/`social.guest_warm` stay Python's until S13, whose
benchmark and ClamAV gate are unchanged.

The standalone worker (`npm run webhook:runner`, `--once`) drains `webhook.deliver`, local
`storage.delete` and `image.derivatives` jobs.

**Proof:** `tools/job-lease-harness.py` reports **49/49 checks on two consecutive runs** against one
fresh disposable PostgreSQL shared by the real Python claims and the Node module. Two workers of
each backend drain 18 `background_jobs` and 18 `platform_jobs` exactly once; live leases cannot be
claimed, renewed or released by another worker; a heartbeat survives the original expiry; expired
leases are recovered; a fresh Python row is untouched until 31 minutes. `tools/webhook-runner-parity.py`
reports **61/61 identical on two consecutive runs** across the eight webhook cases (success,
retry-then-success, five-attempt exhaustion, terminal 400, redirect 302, missing endpoint, inactive
endpoint, invalid URL), six storage cases (success, missing file, directory failure, failure past
the webhook retry limit, duplicate queued jobs, live lease) and eight media cases (three derivatives
from one 900×600 PNG, non-image body, GIF body, missing upload, missing payload path, exhaustion to
`failed`, duplicate queued jobs, live lease). It compares state, attempts, `available_at` backoff,
normalized error class, endpoint counters, upload existence, surviving derivative-cache files — with
each derivative's dimensions and format — and every received body/signature. Service `npm test`
**101 passed**;
`tests/v14_lifecycle_signing_test.py` and `tests/lt_7_2_webhook_delivery_test.py` pass;
`build.py all --check` green; `tools/pg-schema-parity.py` reports **0 missing columns**.

### S12c — storage, backup, analytics, reports, plugins

**Status:** analytics, jobs, reports and the admin console reads landed; backup, object storage and the plugin host are open.

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

The reports queue read (`GET /api/admin/reports`) is ported as well: `tools/reports-read-parity.py`
reports **20/20 identical on two consecutive runs** (admin, super_admin, customer 403, anonymous 401,
filters, limit clamping, cursor paging, invalid input 400, and the admin IP allowlist denying and
allowing). Its handler carries no rate limiter — `admin_reports_list` opens with
`admin=self._admin_gate("/api/admin/reports","GET")` — so P7 does not pin it, and no D2 package is
involved. Only the resolve write is limited (`admin-report-resolve:{admin['id']}`) and stays in
Python.

Two baseline defects surfaced while proving the read. First, invalid `status`/`limit` raised an
unhandled `ValueError`, so the request ended with no response at all; `admin_reports_list` now
answers 400 `{"error": "Invalid status"|"Invalid limit"}` like the analytics ingest route does.
Second, `reports.created_at`/`resolved_at` were `INTEGER`, which cannot hold epoch milliseconds on
PostgreSQL, so every insert failed with `integer out of range`; the declaration is now `BIGINT` and
`features/reports.ensure_schema` widens a table created by an older build.

The rest of the admin console reads are ported too: the overview counts, the legacy user array,
`users-v2` (masking, exact/substring search, cursor paging, and an unmask action that writes the
same chained audit event as Python), the invitation list, the audit explorer (filters, limit
clamp, admin-only bit, date parsing and the CSV byte format) and one background-job status.
`tools/admin-reads-parity.py` reports **42/42 identical on two consecutive runs** against one
PostgreSQL serving both backends, including the allowlist denying and allowing loopback across
restarts. Three validation paths that used to end with no response at all now answer 400 like the
reports route: `users-v2`'s invalid `limit` and `cursor`, and the audit explorer's invalid `limit`
and `date`. The denied-IP audit event is now written by both backends under the same 60-second
per-IP throttle; before this port only Python left that trace.

**Decider: plan rule for backups; engineering for the rest.** Still open in S12c: `backup.py` and the
object-storage migration (pinned by P7 row 2, quoted above), and the plugin sandbox host —
**unmeasured**.

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
- **Backup/object storage, plugin host, media, decommission** — no attempt made.
- **Reports writes** (`POST /api/reports`, `PUT /api/admin/reports/:id`) — not ported; the resolve
  route is rate-limited (`admin-report-resolve`) and both write, so they stay in Python.
- **Analytics writes** (`POST /api/analytics/events`, consent/purge/export) — not ported; the ingest
  route carries `rate_limit(f"analytics-ingest:{self.client_ip()}",60,60)`, so P7 row 1 pins it.

## Summary of deciders

- **Owner only:** S9 (D2 allow-list extension), the `pg` record discrepancy, D9 packaging, D11
  baseline targets.
- **Plan rule (no owner):** S11 pinning, S12a single-writer/presence pin, S12b lease precondition,
  S13 benchmark + ClamAV, D4 build generators.
- **Deployment traffic:** P1, shadow/ramp, 6-platform, S15.
- **Unblocked but unattempted:** S12c backup/object storage and the plugin host, S14 proxy
  (needs a sidecar). S12b's lease precondition is done; its job runners remain.
