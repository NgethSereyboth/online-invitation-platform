# Load Test Plan — k6

> **Phase 3 deliverable.** Companion file to [`CERTIFICATION.md`](./CERTIFICATION.md) §4. This document defines the load-test scenarios, acceptance targets, and reference-deployment benchmarks. The k6 script lives at [`tests/load_test_k6.js`](../../tests/load_test_k6.js).
>
> **Tooling choice.** k6 (preferred) over Locust because:
> - k6 is JS-based — easier to integrate with the stdlib-only setup.
> - k6 is a single static binary (`k6 run script.js`); Locust requires `pip install locust` + a separate runner.
> - k6's VU (virtual user) model is more deterministic than Locust's greenlet-based model — easier to reproduce burst scenarios.
> - The platform already uses JS for the frontend, so contributors can read + extend the k6 script without learning Python's async model.
>
> **Reference deployment.** Single VPS with 2 vCPU + 4 GB RAM + PostgreSQL 15 + Caddy as the HTTPS-terminating reverse proxy. This is the minimum-viable production deployment per [`docs/PRODUCTION_DEPLOYMENT.md`](../PRODUCTION_DEPLOYMENT.md). Numbers in §5 are the expected results on this deployment — actual results may vary ±20% depending on disk IOPS and network latency.

---

## 1. Why k6 (and not Locust)

| Criterion | k6 | Locust |
|-----------|----|----|
| Language | JavaScript (ES2015+) | Python |
| Install | Single static binary | `pip install locust` |
| Run | `k6 run script.js` | `locust -f locustfile.py` |
| VU model | Deterministic goroutines | Greenlet-based, less deterministic |
| Burst scenario | `stages: [{duration, target}]` — exact VU count per stage | Spawn rate (VUs/sec) — less precise |
| Thresholds | First-class `thresholds: {}` block | Manual post-run analysis |
| Reporting | Built-in JSON + InfluxDB + Prometheus | Web UI + CSV |
| Existing tooling | None in repo — script lives at `tests/load_test_k6.js` | None in repo |

**Decision:** k6.

---

## 2. Test environment

| Item | Value |
|------|-------|
| Test host | A staging VPS separate from production |
| OS | Ubuntu 24.04 LTS (Noble) — matches [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §3.5 |
| CPU | 2 vCPU (Intel Xeon or AMD EPYC, 2.4 GHz+ baseline) |
| RAM | 4 GB |
| Disk | 40 GB SSD, ≥ 3000 IOPS |
| PostgreSQL | 15.x, `shared_buffers=1GB`, `effective_cache_size=2GB`, `max_connections=100` |
| Redis | Optional — for the burst scenario, Redis is NOT required (the in-process `RATE_BUCKETS` dict fallback handles rate-limiting; see `server.py::rate_limit`) |
| Object storage | Local MinIO (single-node, single-drive) — simulates the S3/R2 path without external dependency |
| Reverse proxy | Caddy 2.x — terminates HTTPS, forwards to `127.0.0.1:8080` |
| App process count | 1 (the stdlib `http.server` is single-process; for higher throughput, run N copies behind Caddy — see §6 "Scaling beyond the reference deployment") |
| Test invitation | A pre-seeded published invitation with `rsvpEnabled=true`, `rsvpMaxGuests=10`, and zero custom fields. The slug is exported as `EINVITE_LOAD_TEST_SLUG`. |

**Rate-limit relaxation for load testing:**
The platform's per-IP rate limiter (`server.py::rate_limit`) caps RSVPs at 12 per 60 seconds per IP+slug. A k6 run from a single host IP would hit this cap almost immediately. For load testing, set `EINVITE_LOAD_TEST_MODE=1` in the staging environment's `.env` — this multiplies the rate-limit window by 1000 (effectively disabling it for the test). This env var is **never** set in production; `production_preflight.py` rejects it.

```bash
# On the staging host:
echo "EINVITE_LOAD_TEST_MODE=1" >> .env.production
# Restart the server to pick up the env var.
kill $(cat data/einvite.pid) && nohup .venv/bin/python server.py --env-file .env.production > data/logs/server.log 2>&1 &
```

---

## 3. Scenarios

The k6 script at [`tests/load_test_k6.js`](../../tests/load_test_k6.js) implements four scenarios. The RSVP burst is the primary acceptance scenario; the other three are required but secondary.

### 3.1 RSVP burst (wedding-season spike) — L1

**Why bursty, not sustained:** Wedding invitations go out in waves — a host sends 200 invitations on a Saturday morning, and 60-70% of guests RSVP within the first 5 minutes. The platform must handle the **burst**, not just the average.

| Parameter | Value |
|-----------|-------|
| Scenario name | `rsvp_burst` |
| Endpoint | `POST /api/public/{slug}/rsvps` |
| Total VUs | 1000 (over 5 minutes) |
| Ramp-up | 0 → 1000 VUs in 30 seconds (spike profile) |
| Steady state | 1000 VUs for 4 minutes |
| Ramp-down | 1000 → 0 VUs in 30 seconds |
| Total duration | 5 minutes |
| Total requests | ~1000 (each VU submits exactly one RSVP; the VU exits after the request completes) |
| Request body | `{"name":"Guest <vu_id>","status":"Yes, joyfully","count":1}` |
| Headers | `Content-Type: application/json` |
| Expected response | 201 with `{"id":"...","saved":true,"updated":false}` |

**Acceptance:**
- p95 response time < 500 ms.
- p99 response time < 2 s (informational — not a hard gate).
- Zero HTTP 5xx errors.
- HTTP 4xx errors acceptable only if `code=rsvp_closed` AND the `rsvpCloseDate` is in the past — which it is not for the test invitation.

### 3.2 Concurrent AI agent tool invocations — L2

| Parameter | Value |
|-----------|-------|
| Scenario name | `ai_tool_calls` |
| Endpoint | `POST /api/invitations/{id}/ai/execute` |
| Total VUs | 50 |
| Ramp-up | 0 → 50 VUs in 5 seconds |
| Steady state | 50 VUs for 2 minutes |
| Total duration | 2 minutes 5 seconds |
| Per-VU iteration | 1 tool call (`invitation.list_assets` — read-only, deterministic) |
| Auth | Each VU uses a pre-seeded host session cookie (`EINVITE_LOAD_TEST_HOST_COOKIE`) |
| Expected response | 200 with `{"ok":true,"result":[...]}` |

**Acceptance:**
- p95 response time < 2 s.
- Zero HTTP 5xx errors.
- HTTP 4xx errors acceptable only for rate-limit (429) — the AI agent has a stricter per-user rate limit (default 10 calls/minute).

### 3.3 Concurrent collaboration updates — L3

| Parameter | Value |
|-----------|-------|
| Scenario name | `collab_edits` |
| Endpoint | `PUT /api/invitations/{id}/collab/mutations` |
| Total VUs | 20 (all editing the SAME invitation — worst-case contention) |
| Ramp-up | 0 → 20 VUs in 2 seconds |
| Steady state | 20 VUs for 3 minutes |
| Per-VU iteration | Each VU sends a mutation every 200-500 ms (randomized) — a `fields.title` text-insert mutation with a Lamport timestamp |
| Total duration | 3 minutes 2 seconds |
| Auth | Each VU uses a unique pre-seeded collaborator session cookie |
| Expected response | 200 with `{"revision":<n>,"applied":true}` |

**Acceptance:**
- p95 response time < 500 ms.
- Zero HTTP 5xx errors.
- HTTP 409 acceptable (optimistic-locking conflict — the client retries with the new revision). The retry is handled by the k6 script's `exec` function (re-fetch the document, re-apply the mutation, retry up to 3 times).
- After the scenario, the invitation's `collaboration_checkpoints` table should have ≥ 1 new checkpoint row (the compaction threshold is 100 mutations or 60 seconds, whichever comes first).

### 3.4 Public invitation page views — L4

| Parameter | Value |
|-----------|-------|
| Scenario name | `public_views` |
| Endpoint | `GET /i/{slug}` (HTML page) + `POST /api/public/{slug}/view` (analytics beacon) |
| Total VUs | 200 (over 1 hour) |
| Ramp-up | 0 → 200 VUs in 60 seconds |
| Steady state | 200 VUs for 58 minutes |
| Ramp-down | 200 → 0 VUs in 60 seconds |
| Total duration | 1 hour |
| Per-VU iteration | Each VU loads the public page, waits 1-5 seconds (randomized — simulates reading), then fires the view-beacon POST, then exits |
| Expected response | 200 for both GET and POST |

**Acceptance:**
- p95 response time for GET < 200 ms (HTML render, no DB write — only the static asset bundle).
- p95 response time for POST < 100 ms (idempotent analytics beacon; the `idempotency_records` table dedupes within 24 hours).
- Zero HTTP 5xx errors.
- Total `view_events` rows after the scenario: ~10,000 (some dedup due to repeated VU cookies — acceptable; the assertion is that the count is within ±10% of 10,000).

---

## 4. Acceptance targets (summary)

| Metric | Target | Scenario | How measured |
|--------|--------|----------|--------------|
| p95 response time — RSVP | < 500 ms | `rsvp_burst` | k6 `thresholds: { http_req_duration: ['p(95)<500'] }` |
| p95 response time — AI agent | < 2 s | `ai_tool_calls` | k6 `thresholds: { http_req_duration: ['p(95)<2000'] }` |
| p95 response time — collaboration | < 500 ms | `collab_edits` | k6 `thresholds: { http_req_duration: ['p(95)<500'] }` |
| p95 response time — public page view (GET) | < 200 ms | `public_views` | k6 `thresholds: { http_req_duration: ['p(95)<200'] }` |
| HTTP 5xx errors | 0 | all scenarios | k6 `thresholds: { http_req_failed: ['rate==0'] }` (filtered to 5xx only) |
| HTTP 4xx errors | < 1% (excluding 429 + 409) | `rsvp_burst`, `ai_tool_calls`, `collab_edits`, `public_views` | k6 custom check |

---

## 5. Reference deployment results

> The numbers below are the **expected** results on the reference deployment described in §2. They were derived from the V22.1 performance contract (`docs/V22_1_PERFORMANCE_RESULTS.json`), extrapolated to the V54 stack. Actual results will be filled in after the first k6 run on the staging VPS.

### 5.1 RSVP burst (L1) — expected on 2 vCPU / 4 GB RAM / PG 15

| Metric | Expected value | Notes |
|--------|-----------------|-------|
| Total RSVPs submitted in 5 min | 1000 | All VUs complete exactly one iteration |
| Successful RSVPs (HTTP 201) | ≥ 990 | < 1% failure rate |
| p50 response time | ~80 ms | SQLite write is ~5 ms; PG write is ~20 ms; the rest is rate-limit + body parse + audit-event insert |
| p95 response time | ~350 ms | Under the 500 ms target — headroom for the spike |
| p99 response time | ~1.2 s | Under the 2 s informational target |
| HTTP 5xx errors | 0 | The request-slot semaphore (capacity 64) should not saturate at 1000 concurrent VUs because each request completes in < 100 ms |
| HTTP 429 rate-limit | 0 | `EINVITE_LOAD_TEST_MODE=1` relaxes the rate limit |
| CPU usage (avg) | ~70% on vCPU 0, ~30% on vCPU 1 | Single-process; vCPU 0 does the http.server loop, vCPU 1 does the PG writes |
| Memory usage (peak) | ~250 MB | Python process + PG shared buffers |
| PG connections (peak) | 1 | The stdlib http.server is single-threaded; only one DB connection is open at a time (this is the **bottleneck** — see §6) |

### 5.2 AI agent tool calls (L2) — expected

| Metric | Expected value |
|--------|-----------------|
| Total tool calls in 2 min | ~50 (one per VU) |
| p50 response time | ~150 ms |
| p95 response time | ~800 ms |
| p99 response time | ~1.5 s |
| HTTP 5xx errors | 0 |
| HTTP 429 (rate limit) | ~5 (10 calls/min/user × 50 users = 500 expected, but each VU only makes 1 call, so the rate-limit should NOT fire — adjust the per-user AI rate limit to 100/min for the test if it does) |

### 5.3 Collaboration edits (L3) — expected

| Metric | Expected value |
|--------|-----------------|
| Total mutations in 3 min | ~7000 (20 VUs × ~3 mutations/sec/VU × 180 sec) |
| p50 response time | ~60 ms |
| p95 response time | ~250 ms |
| p99 response time | ~800 ms |
| HTTP 5xx errors | 0 |
| HTTP 409 conflicts | ~5% | Expected — 20 editors on the same document will conflict; the k6 script retries |

### 5.4 Public page views (L4) — expected

| Metric | Expected value |
|--------|-----------------|
| Total page views in 1 hr | ~10,000 (200 VUs × 50 iterations each) |
| p50 response time (GET) | ~30 ms |
| p95 response time (GET) | ~120 ms |
| p99 response time (GET) | ~300 ms |
| p95 response time (POST beacon) | ~50 ms |
| HTTP 5xx errors | 0 |

---

## 6. Scaling beyond the reference deployment

The reference deployment (2 vCPU / 4 GB RAM / single-process) handles the burst scenarios above with headroom. For higher throughput:

| Scaling axis | How | Effect |
|--------------|-----|--------|
| Vertical (more CPU) | Upgrade to 4 vCPU / 8 GB RAM | p95 drops by ~30% (single-process benefits from faster single-thread performance) |
| Horizontal (more processes) | Run N copies of `server.py` on ports 8080-808N, with Caddy load-balancing via round-robin | Throughput scales ~linearly with N (up to PG `max_connections`); each process holds 1 PG connection |
| DB replica | Add a PG read-replica for `GET /api/public/{slug}` + `GET /i/{slug}` | Read throughput doubles; writes still hit the primary |
| Redis | Add Redis for rate-limit counters + presence (currently in-process) | Per-VU latency drops by ~5 ms (the in-process dict is faster than Redis for a single process, but Redis enables horizontal scaling) |
| CDN | Put Caddy behind Cloudflare for static asset caching | Static `bundle-*.js` + `bundle-*.css` + WOFF2 fonts are cached at the edge; origin traffic drops by ~80% for `public_views` |

**Phase 3 scope:** the reference deployment only. Scaling beyond it is a Phase 5 (Hosted Tier) concern.

---

## 7. k6 script

The k6 script is at [`tests/load_test_k6.js`](../../tests/load_test_k6.js). It implements all four scenarios behind `export const options = { scenarios: {...} }`. To run a single scenario:

```bash
# Install k6 (one-time).
# Linux:
sudo gpg -k && sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A36442D57A5E7B547C6CAD227 && echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list && sudo apt-get update && sudo apt-get install -y k6

# Set the env vars (point at the staging host).
export EINVITE_LOAD_TEST_BASE_URL=http://127.0.0.1:8080
export EINVITE_LOAD_TEST_SLUG=test-invitation-slug
export EINVITE_LOAD_TEST_HOST_COOKIE=einvite_session=<host-session-token>

# Run only the RSVP burst scenario.
k6 run --scenario rsvp_burst tests/load_test_k6.js

# Run all scenarios.
k6 run tests/load_test_k6.js
```

---

## 8. Load-test report template

> **Bilingual note.** The field labels below are surfaced to the host in the dashboard's "Load test report" view (planned for Phase 5 hosted tier — currently this template is Markdown-only). The Khmer translations are noted for the i18n contract.

```markdown
# Load Test Report — <YYYY-MM-DD>

**Test environment:** 2 vCPU / 4 GB RAM / PG 15 / MinIO / Caddy
**Test host:** <hostname>
**k6 version:** <version>
**Commit:** <git SHA>

## Scenario results

### L1 — RSVP burst (rsvp_burst)

| Metric | Target | Measured | Within budget? | ការវាយតម្លៃ / Khmer label |
|--------|--------|----------|----------------|---------------------------|
| Total RSVPs submitted | 1000 | <value> | ✅ / ❌ | ចំនួន RSVP សរុប |
| p50 response time | — | <value> ms | n/a | ពេលវេលាឆ្លើយតបមធ្យម |
| p95 response time | < 500 ms | <value> ms | ✅ / ❌ | ពេលវេលាឆ្លើយតប 95% |
| p99 response time | < 2 s | <value> ms | ✅ / ❌ | ពេលវេលាឆ្លើយតប 99% |
| HTTP 5xx errors | 0 | <value> | ✅ / ❌ | កំហុស 5xx |
| HTTP 4xx errors (non-429) | < 1% | <value> | ✅ / ❌ | កំហុស 4xx |

### L2 — AI agent tool calls (ai_tool_calls)
(same shape as L1)

### L3 — Concurrent collaboration updates (collab_edits)
(same shape as L1; add an HTTP 409 row)

### L4 — Public page views (public_views)
(same shape as L1)

## Resource usage

| Resource | Peak | Notes |
|----------|------|-------|
| CPU (vCPU 0) | <value>% | http.server loop |
| CPU (vCPU 1) | <value>% | PG writes + MinIO |
| Memory (Python process) | <value> MB | |
| Memory (PostgreSQL) | <value> MB | shared_buffers=1GB |
| PG connections (peak) | <value> | Single-process = 1 |
| Disk write IOPS (peak) | <value> | |

## Gaps encountered

- (e.g., "the per-user AI rate limit fired on VU 35; bumped to 100/min for the test.")
- (e.g., "the request-slot semaphore saturated at 64 concurrent; consider raising to 128 for the next test.")

## Action items

- [ ] <action> — owner <name> — due <date>
- [ ] ...

## Sign-off

- Test operator: <name> — <date>
- Engineering lead: <name> — <date>
```

---

## 9. Acceptance gates

1. The k6 script runs end-to-end against the staging deployment without manual intervention (set `EINVITE_LOAD_TEST_BASE_URL` + `EINVITE_LOAD_TEST_SLUG` + `EINVITE_LOAD_TEST_HOST_COOKIE`).
2. The RSVP burst (L1) meets the p95 < 500 ms target with zero 5xx errors.
3. The AI agent scenario (L2) meets the p95 < 2 s target with zero 5xx errors.
4. The reference deployment numbers in §5 are reproduced within ±20% on a clean 2 vCPU / 4 GB RAM VPS.
5. No HTTP 5xx errors during any scenario; the request-slot semaphore in `server.py::Handler` degrades gracefully to 503 with the standard security headers (ASVS L2 gap `[14.1.12]` — see [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md)).
6. The load-test report is filed under `docs/certification/load-test-reports/<YYYY>-<MM>-<DD>.md`.

---

## 10. Cross-references

- [`CERTIFICATION.md`](./CERTIFICATION.md) §4 — executive summary.
- [`tests/load_test_k6.js`](../../tests/load_test_k6.js) — the k6 script.
- [`docs/PRODUCTION_DEPLOYMENT.md`](../PRODUCTION_DEPLOYMENT.md) — reference deployment topology.
- [`docs/V22_1_PERFORMANCE_RESULTS.json`](../V22_1_PERFORMANCE_RESULTS.json) — V22.1 performance baseline (the precursor to the §5 expected numbers).
- [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) `### P3-F` — the request-slot semaphore security-header gap (relevant to acceptance gate 5).
- [`docs/ROADMAP.md`](../ROADMAP.md) §6 — Phase 3 task definition (load test against burst target).
