// k6 load test script for the eInvite Platform.
//
// Phase 3 deliverable. Companion to docs/certification/LOAD-TEST-PLAN.md.
//
// Run:
//   export EINVITE_LOAD_TEST_BASE_URL=http://127.0.0.1:8080
//   export EINVITE_LOAD_TEST_SLUG=test-invitation-slug
//   export EINVITE_LOAD_TEST_HOST_COOKIE=einvite_session=<host-session-token>
//   export EINVITE_LOAD_TEST_INVITATION_ID=<invitation-uuid>
//   k6 run --scenario rsvp_burst tests/load_test_k6.js   # RSVP burst only
//   k6 run tests/load_test_k6.js                          # all scenarios
//
// Env vars:
//   EINVITE_LOAD_TEST_BASE_URL        (required) The base URL of the staging server.
//   EINVITE_LOAD_TEST_SLUG            (required for L1 + L4) The slug of a pre-seeded
//                                     published invitation with rsvpEnabled=true.
//   EINVITE_LOAD_TEST_HOST_COOKIE     (required for L2 + L3) The host session cookie
//                                     (e.g. "einvite_session=abc123").
//   EINVITE_LOAD_TEST_INVITATION_ID   (required for L2 + L3) The invitation UUID
//                                     matching the host cookie.
//
// This script is build-tool-free — it uses k6's built-in modules only, no imports
// from npm or any other package manager. It matches the project's stdlib-only constraint
// (see ROADMAP.md ground rule 4).

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Trend, Rate } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.EINVITE_LOAD_TEST_BASE_URL || 'http://127.0.0.1:8080';
const SLUG = __ENV.EINVITE_LOAD_TEST_SLUG || 'test-invitation-slug';
const HOST_COOKIE = __ENV.EINVITE_LOAD_TEST_HOST_COOKIE || 'einvite_session=dev-host-session';
const INVITATION_ID = __ENV.EINVITE_LOAD_TEST_INVITATION_ID || '00000000-0000-0000-0000-000000000000';

// Custom metrics (visible in the k6 summary at the end of the run).
const rsvpSuccess = new Counter('einvite_rsvp_success');
const rsvpFailures = new Counter('einvite_rsvp_failures');
const rsvpDuration = new Trend('einvite_rsvp_duration', true);
const aiToolSuccess = new Counter('einvite_ai_tool_success');
const aiToolDuration = new Trend('einvite_ai_tool_duration', true);
const collabConflictRate = new Rate('einvite_collab_conflict');
const collabDuration = new Trend('einvite_collab_duration', true);
const publicViewDuration = new Trend('einvite_public_view_duration', true);

// ---------------------------------------------------------------------------
// Scenarios
// ---------------------------------------------------------------------------
// Each scenario is independent. Use `--scenario <name>` to run only one.
// The RSVP burst is the PRIMARY acceptance scenario (L1, see LOAD-TEST-PLAN.md §3.1).
// The other three are required but secondary.
//
// Note on VU count: k6 VUs are goroutines, not real threads. A single VU can
// sustain ~10 req/sec if the response time is 100ms. For the RSVP burst, 1000
// VUs each making ONE request means the burst completes in ~1 second of wall
// time if the server is fast — we use the `stages` executor with ramp-up to
// spread the load over 5 minutes (matching the real wedding-season burst shape).
// ---------------------------------------------------------------------------

export const options = {
  scenarios: {
    // L1 — RSVP burst (wedding-season spike).
    // 1000 VUs over 5 minutes; each VU submits exactly one RSVP.
    rsvp_burst: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 1000 },  // spike ramp-up
        { duration: '4m', target: 1000 },   // steady state
        { duration: '30s', target: 0 },     // ramp-down
      ],
      gracefulRampDown: '10s',
      exec: 'rsvpBurst',
    },

    // L2 — Concurrent AI agent tool invocations.
    // 50 VUs over 2 minutes; each VU makes one tool call per iteration.
    ai_tool_calls: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5s', target: 50 },
        { duration: '2m', target: 50 },
        { duration: '5s', target: 0 },
      ],
      gracefulRampDown: '5s',
      exec: 'aiToolCall',
    },

    // L3 — Concurrent collaboration updates.
    // 20 VUs over 3 minutes; each VU sends a mutation every 200-500ms.
    collab_edits: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2s', target: 20 },
        { duration: '3m', target: 20 },
        { duration: '2s', target: 0 },
      ],
      gracefulRampDown: '5s',
      exec: 'collabEdit',
    },

    // L4 — Public invitation page views.
    // 200 VUs over 1 hour; each VU loads the page + fires the view beacon.
    public_views: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 200 },
        { duration: '58m', target: 200 },
        { duration: '1m', target: 0 },
      ],
      gracefulRampDown: '30s',
      exec: 'publicView',
    },
  },

  // Thresholds — these gate the exit code. k6 exits non-zero if any threshold
  // is breached. See LOAD-TEST-PLAN.md §4 for the acceptance targets.
  thresholds: {
    // L1 — RSVP burst.
    'http_req_duration{scenario:rsvp_burst}': ['p(95)<500'],  // < 500 ms p95
    'http_req_failed{scenario:rsvp_burst}': ['rate==0'],       // zero 5xx

    // L2 — AI agent tool calls.
    'http_req_duration{scenario:ai_tool_calls}': ['p(95)<2000'],  // < 2 s p95
    'http_req_failed{scenario:ai_tool_calls}': ['rate==0'],

    // L3 — Collaboration edits.
    'http_req_duration{scenario:collab_edits}': ['p(95)<500'],
    'http_req_failed{scenario:collab_edits}': ['rate==0'],

    // L4 — Public page views (GET only — the POST beacon is checked separately).
    'http_req_duration{scenario:public_views,expected_response:200}': ['p(95)<200'],
    'http_req_failed{scenario:public_views}': ['rate==0'],
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Random integer in [min, max] inclusive.
function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Pick a random RSVP name (Khmer + Latin to exercise the i18n path).
const RSVP_NAMES = [
  'Sophea', 'Serey', 'Dara', 'Chanthou', 'Rithy',
  'សុភា', 'សិរី', 'ដារា', 'ច័ន្ធួ', 'ឫទ្ធី',
];

function randomName(vuId) {
  // Mix Latin + Khmer names so the load test exercises both code paths.
  const name = RSVP_NAMES[vuId % RSVP_NAMES.length];
  return `${name} ${vuId}`;
}

// ---------------------------------------------------------------------------
// Scenario L1 — RSVP burst
// ---------------------------------------------------------------------------
// Endpoint: POST /api/public/{slug}/rsvps
// Body: {"name":"...","status":"Yes, joyfully","count":1}
// Expected: 201 with {"id":"...","saved":true,"updated":false}
// Notes:
//   - The honeypot "website" field is NOT sent (an empty value is fine; a
//     non-empty value would return 400 — see server.py:5272).
//   - The bot protection check returns True if BOT_PROTECTION_ENDPOINT is not
//     set (the staging default) — so an empty botToken is accepted.
//   - Rate limits are bypassed by setting EINVITE_LOAD_TEST_MODE=1 in the
//     staging environment's .env (see LOAD-TEST-PLAN.md §2).
// ---------------------------------------------------------------------------

export function rsvpBurst() {
  const vuId = __VU;  // k6 virtual user ID (1-based, unique per VU)
  const url = `${BASE_URL}/api/public/${encodeURIComponent(SLUG)}/rsvps`;
  const payload = JSON.stringify({
    name: randomName(vuId),
    status: 'Yes, joyfully',
    count: 1,
    note: `Load test VU ${vuId}`,
  });
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    tags: { scenario: 'rsvp_burst' },
  };

  const start = Date.now();
  const res = http.post(url, payload, params);
  const duration = Date.now() - start;

  rsvpDuration.add(duration);

  const ok = check(res, {
    'status is 201 or 200': (r) => r.status === 201 || r.status === 200,
    'response has saved=true': (r) => {
      try {
        const body = r.json();
        return body && body.saved === true;
      } catch (e) {
        return false;
      }
    },
    'response time < 500ms (p95 gate)': (r) => r.timings.duration < 500,
  });

  if (ok) {
    rsvpSuccess.add(1);
  } else {
    rsvpFailures.add(1);
    // Log the failure for the post-run report (k6 prints these to stderr).
    if (__VU < 5) {  // only log first 5 VUs to avoid spam
      console.warn(`RSVP failure VU=${__VU} status=${res.status} body=${res.body}`);
    }
  }

  // Each VU submits exactly one RSVP, then exits the iteration.
  // k6 will re-run the iteration if the scenario is still in steady-state,
  // but for the burst we want ONE request per VU — so sleep for the rest of
  // the iteration.
  sleep(5);
}

// ---------------------------------------------------------------------------
// Scenario L2 — AI agent tool call
// ---------------------------------------------------------------------------
// Endpoint: POST /api/invitations/{id}/ai/execute
// Body: {"tool":"invitation.list_assets","args":{"limit":20}}
// Auth: EINVITE_LOAD_TEST_HOST_COOKIE as a Cookie header.
// Expected: 200 with {"ok":true,"result":[...]}
// Notes:
//   - We use the read-only `invitation.list_assets` tool because it is
//     deterministic, has no side effects, and exercises the AI tool
//     authorization path (the JIT elevation is not required for read tools).
//   - The per-user AI rate limit defaults to 10 calls/min. Each VU makes
//     one call per iteration; with 50 VUs over 2 minutes, the limit should
//     not fire. If it does, set the test-only env var to bump the limit.
// ---------------------------------------------------------------------------

export function aiToolCall() {
  const url = `${BASE_URL}/api/invitations/${encodeURIComponent(INVITATION_ID)}/ai/execute`;
  const payload = JSON.stringify({
    tool: 'invitation.list_assets',
    args: { limit: 20 },
    context: { source: 'load_test_k6', vu: __VU },
  });
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Cookie': HOST_COOKIE,
    },
    tags: { scenario: 'ai_tool_calls' },
  };

  const start = Date.now();
  const res = http.post(url, payload, params);
  const duration = Date.now() - start;

  aiToolDuration.add(duration);

  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has ok=true': (r) => {
      try {
        const body = r.json();
        return body && body.ok === true;
      } catch (e) {
        return false;
      }
    },
    'response time < 2s (p95 gate)': (r) => r.timings.duration < 2000,
  });

  if (ok) {
    aiToolSuccess.add(1);
  } else if (__VU < 5) {
    console.warn(`AI tool failure VU=${__VU} status=${res.status} body=${res.body}`);
  }

  // Pace: one tool call per 2 seconds per VU.
  sleep(2);
}

// ---------------------------------------------------------------------------
// Scenario L3 — Concurrent collaboration edit
// ---------------------------------------------------------------------------
// Endpoint: PUT /api/invitations/{id}/collab/mutations
// Body: {"mutation":{"type":"text-insert","path":"fields.title","position":N,"text":"x"},
//        "client_id":"<vu>","revision":<current>}
// Auth: EINVITE_LOAD_TEST_HOST_COOKIE as a Cookie header.
// Expected: 200 with {"revision":<n+1>,"applied":true}
//   OR      409 with {"error":"conflict","current_revision":<n>} (retry)
// Notes:
//   - The mutation requires the current revision. We GET the invitation first
//     to fetch it, then PUT the mutation. On 409, we re-GET and retry up to 3
//     times.
//   - 20 VUs editing the SAME invitation — worst-case contention.
// ---------------------------------------------------------------------------

const COLLAB_MAX_RETRIES = 3;

function fetchCurrentRevision() {
  const url = `${BASE_URL}/api/invitations/${encodeURIComponent(INVITATION_ID)}`;
  const res = http.get(url, {
    headers: { 'Cookie': HOST_COOKIE, 'Accept': 'application/json' },
    tags: { scenario: 'collab_edits' },
  });
  if (res.status !== 200) return null;
  try {
    const body = res.json();
    return body && body.revision ? body.revision : 0;
  } catch (e) {
    return null;
  }
}

export function collabEdit() {
  const url = `${BASE_URL}/api/invitations/${encodeURIComponent(INVITATION_ID)}/collab/mutations`;
  const clientId = `k6-vu-${__VU}`;

  for (let attempt = 0; attempt < COLLAB_MAX_RETRIES; attempt++) {
    const revision = fetchCurrentRevision();
    if (revision === null) {
      if (__VU < 5) console.warn(`Collab: could not fetch revision VU=${__VU}`);
      sleep(0.2);
      continue;
    }

    const payload = JSON.stringify({
      mutation: {
        type: 'text-insert',
        path: 'fields.title',
        position: randInt(0, 20),
        text: 'x',
      },
      client_id: clientId,
      revision: revision,
    });

    const start = Date.now();
    const res = http.put(url, payload, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Cookie': HOST_COOKIE,
      },
      tags: { scenario: 'collab_edits' },
    });
    const duration = Date.now() - start;
    collabDuration.add(duration);

    if (res.status === 200) {
      collabConflictRate.add(false);
      check(res, {
        'status is 200': (r) => r.status === 200,
        'response has applied=true': (r) => {
          try { return r.json().applied === true; } catch (e) { return false; }
        },
      });
      break;  // success — exit the retry loop
    } else if (res.status === 409) {
      collabConflictRate.add(true);
      // conflict — retry with the new revision (re-fetch on next loop iteration)
      sleep(randInt(50, 200) / 1000);  // back off 50-200 ms
      continue;
    } else {
      if (__VU < 5) console.warn(`Collab failure VU=${__VU} status=${res.status} body=${res.body}`);
      break;  // unexpected error — give up
    }
  }

  // Pace: one mutation attempt every 200-500 ms per VU.
  sleep(randInt(200, 500) / 1000);
}

// ---------------------------------------------------------------------------
// Scenario L4 — Public page view
// ---------------------------------------------------------------------------
// Endpoints: GET /i/{slug} (HTML page) + POST /api/public/{slug}/view (beacon)
// Auth: none (public)
// Expected: 200 for both
// Notes:
//   - Each VU loads the public page, waits 1-5 seconds (simulates reading),
//     then fires the view-beacon POST, then exits the iteration.
//   - The view-beacon is idempotent (the `idempotency_records` table dedupes
//     within 24 hours — see server.py:idempotency_records schema).
// ---------------------------------------------------------------------------

export function publicView() {
  // 1. Load the public HTML page.
  const pageUrl = `${BASE_URL}/i/${encodeURIComponent(SLUG)}`;
  const start1 = Date.now();
  const pageRes = http.get(pageUrl, {
    tags: { scenario: 'public_views', expected_response: '200' },
  });
  publicViewDuration.add(Date.now() - start1);

  check(pageRes, {
    'page status is 200': (r) => r.status === 200,
    'page has CSP header': (r) => {
      const csp = r.headers['Content-Security-Policy'] || '';
      return csp.includes("script-src 'self'");
    },
    'page contains publicRoot': (r) => r.body && r.body.includes('publicRoot'),
  });

  // 2. Simulate reading the page (1-5 seconds).
  sleep(randInt(1, 5));

  // 3. Fire the view-beacon POST.
  const beaconUrl = `${BASE_URL}/api/public/${encodeURIComponent(SLUG)}/view`;
  const beaconRes = http.post(beaconUrl, JSON.stringify({ source: 'load_test_k6' }), {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'public_views' },
  });

  check(beaconRes, {
    'beacon status is 200': (r) => r.status === 200,
  });
}

// ---------------------------------------------------------------------------
// Setup / teardown (runs once per scenario, not per VU)
// ---------------------------------------------------------------------------
// k6 calls `setup()` once at the start of the test run. We use it to verify
// the env vars are set and the server is reachable — failing fast saves the
// operator from running a 5-minute burst against the wrong host.
// ---------------------------------------------------------------------------

export function setup() {
  if (!BASE_URL) {
    throw new Error('EINVITE_LOAD_TEST_BASE_URL is required');
  }

  // Smoke-test the health endpoint before starting the scenario.
  const healthRes = http.get(`${BASE_URL}/api/health/live`, { tags: { scenario: 'setup' } });
  if (healthRes.status !== 200) {
    throw new Error(`Health check failed: expected 200, got ${healthRes.status}. Is the staging server running at ${BASE_URL}?`);
  }

  console.log(`k6 load test starting. base_url=${BASE_URL} slug=${SLUG} invitation_id=${INVITATION_ID}`);
  return { baseUrl: BASE_URL, slug: SLUG };
}

export function teardown(data) {
  console.log('k6 load test complete. See docs/certification/LOAD-TEST-PLAN.md §5 for expected numbers.');
}

// ---------------------------------------------------------------------------
// Default function (used if no `--scenario` flag is passed AND no `exec` is
// specified in the scenario — k6 falls back to `default`).
// Since every scenario above specifies `exec`, this function is never called
// by the multi-scenario run. We keep it as a smoke test for the `k6 run` with
// no scenarios (e.g. `k6 run tests/load_test_k6.js` with the scenarios block
// stripped — useful for ad-hoc testing).
// ---------------------------------------------------------------------------

export default function () {
  rsvpBurst();
}
