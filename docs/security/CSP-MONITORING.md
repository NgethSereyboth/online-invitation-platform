# CSP Report-Only Monitoring (V54.28 — sec-8 / ROADMAP-V2 §2.8)

> **Goal.** Give the host visibility into what the enforcing Content-Security-Policy
> WOULD block, without breaking anything in production. Reports flow into
> `audit_events` and stdout, where a weekly summary surfaces noisy directives,
> repeat offenders, and unwanted third-party loads.

---

## 1. Header wiring

Every response now carries THREE CSP-related headers (see `end_headers` in
`src/python/server.py`):

| Header | Purpose |
|---|---|
| `Content-Security-Policy` | The enforcing policy. Violations are BLOCKED by the browser. Unchanged since V54.0. |
| `Content-Security-Policy-Report-Only` | A mirror of the enforcing policy + `report-uri /api/csp-report` + `report-to csp`. Violations are REPORTED but NOT blocked. |
| `Report-To` | Reporting API group config — points at the same `/api/csp-report` endpoint with `max_age=10886400` (126 days). |

The report-only policy is the **exact same string** as the enforcing policy,
plus `; report-uri /api/csp-report; report-to csp`. Keep them in lock-step —
the constant `CSP_HEADER` (defined at the top of `server.py`) is the single
source of truth for both.

> ⚠️ **Do not** flip the report-only header into an enforcing header until
> a week of clean reports. The whole point of §2.8 is to observe first,
> enforce later.

---

## 2. The `/api/csp-report` endpoint

- **Method:** `POST`
- **Auth:** None required (CSRF / Origin checks are bypassed for this route
  — browsers cannot attach CSRF tokens to CSP reports, and the Reporting
  API may omit the `Origin` header entirely).
- **Rate limit:** 60 reports / 60 seconds per IP. Returns `429` over the
  limit (the browser will not retry on 4xx).
- **Response:** `204 No Content` on success (per the CSP reporting spec).
  Failures inside the handler are swallowed — the endpoint NEVER returns
  5xx, because a 5xx makes the browser retry the report, amplifying noise.
- **Side effects:**
  1. A structured log line is emitted to stdout:
     ```
     [csp_report] document=<doc_uri> directive=<directive> blocked=<blocked_uri> source=<source_file>:<line> user_agent=<ua>
     ```
     (or, when `EINVITE_JSON_LOGS=1`, a JSON object with the same fields).
     This is emitted UNCONDITIONALLY — even unauthenticated reports are
     logged so guest-page violations are still observable.
  2. If the request carries a valid session cookie / bearer token, an
     `audit_events` row is written with `action='csp.violation'`,
     `target_type='csp'`, and a `metadata_json` blob containing the
     extracted fields. Anonymous reports are logged but NOT audited so
     guest-page noise doesn't pollute the audit trail.

### Accepted report shapes

The endpoint accepts both:

**Legacy `report-uri`** (Content-Type `application/csp-report`):
```json
{
  "csp-report": {
    "document-uri": "https://example.com/i/test",
    "referrer": "",
    "violated-directive": "script-src",
    "effective-directive": "script-src",
    "original-policy": "default-src 'self'; ...",
    "blocked-uri": "https://evil.com/script.js",
    "line-number": 42,
    "column-number": 1,
    "source-file": "https://example.com/i/test"
  }
}
```

**Reporting API `report-to`** (Content-Type `application/reports+json`):
```json
[{
  "type": "csp-violation",
  "url": "https://example.com/i/test",
  "user_agent": "Mozilla/5.0 ...",
  "body": {
    "documentURL": "https://example.com/i/test",
    "referrer": "",
    "blockedURL": "https://evil.com/script.js",
    "effectiveDirective": "script-src",
    "originalPolicy": "default-src 'self'; ...",
    "lineNumber": 42,
    "columnNumber": 1,
    "sourceFile": "https://example.com/i/test"
  }
}]
```

The handler normalises both into the same kebab-case field set internally.

---

## 3. Weekly summary query

The weekly summary is a **documentation-only** SQL query — there is no
cron job wired up (per the §2.8 task scope). An operator runs it ad-hoc
against the production database (SQLite or PostgreSQL — the
`audit_events` schema is identical on both):

```sql
-- ────────────────────────────────────────────────────────────────────────
-- Weekly CSP-violation summary — run Monday morning against audit_events.
-- Generated for the 7-day window ending at the moment the query runs.
-- ────────────────────────────────────────────────────────────────────────

-- (a) Violations by directive — what is the browser most-often blocking?
--     A spike here is a candidate for either tightening enforcement (after
--     a clean week) or relaxing the policy if the blocked resource is
--     legitimate.
SELECT
    json_extract(metadata_json, '$.violated_directive') AS directive,
    COUNT(*) AS violation_count
FROM audit_events
WHERE action = 'csp.violation'
  AND created_at >= (strftime('%s','now') - 7*24*3600) * 1000
GROUP BY directive
ORDER BY violation_count DESC;

-- (b) Unique blocked-URIs — which third-party resources are being loaded
--     (and blocked)? This is the list to triage: each entry is either a
--     bug (a same-origin script the policy should permit) or an
--     unwanted third-party load (a candidate for a CSP exception or
--     removal from the page).
SELECT
    json_extract(metadata_json, '$.blocked_uri') AS blocked_uri,
    COUNT(*) AS violation_count,
    MIN(created_at) AS first_seen_ms,
    MAX(created_at) AS last_seen_ms
FROM audit_events
WHERE action = 'csp.violation'
  AND created_at >= (strftime('%s','now') - 7*24*3600) * 1000
  AND json_extract(metadata_json, '$.blocked_uri') IS NOT NULL
  AND json_extract(metadata_json, '$.blocked_uri') != ''
GROUP BY blocked_uri
ORDER BY violation_count DESC
LIMIT 200;

-- (c) Repeat offenders — source files generating >10 violations/week.
--     These are the highest-priority fix targets: a single page emitting
--     dozens of CSP violations is almost always a bug (a missing
--     nonce/hash, an inline script that should be externalised, or a
--     third-party widget that should be self-hosted).
SELECT
    json_extract(metadata_json, '$.source_file') AS source_file,
    json_extract(metadata_json, '$.violated_directive') AS directive,
    COUNT(*) AS violation_count
FROM audit_events
WHERE action = 'csp.violation'
  AND created_at >= (strftime('%s','now') - 7*24*3600) * 1000
  AND json_extract(metadata_json, '$.source_file') IS NOT NULL
  AND json_extract(metadata_json, '$.source_file') != ''
GROUP BY source_file, directive
HAVING violation_count > 10
ORDER BY violation_count DESC;

-- (d) Optional — per-user correlation. Join against `users` to surface
--     which accounts are hitting CSP violations (useful for support /
--     on-call triage when a host reports "the editor is broken").
SELECT
    u.email,
    COUNT(*) AS violation_count,
    json_extract(a.metadata_json, '$.violated_directive') AS top_directive
FROM audit_events a
LEFT JOIN users u ON u.id = a.user_id
WHERE a.action = 'csp.violation'
  AND a.created_at >= (strftime('%s','now') - 7*24*3600) * 1000
GROUP BY u.email, top_directive
ORDER BY violation_count DESC
LIMIT 50;
```

### PostgreSQL variant

For PostgreSQL deployments, replace `strftime('%s','now') * 1000` with
`(EXTRACT(EPOCH FROM NOW()) * 1000)::bigint`, and `json_extract(...)` with
`metadata_json::json->>'...'`. The structure is otherwise identical.

### Runbook

1. **Monday morning:** run queries (a)–(c) above.
2. **If (a) shows a directive with >0 violations for two consecutive
   weeks:** investigate. Either tighten enforcement (after a clean week)
   or relax the policy if the blocked resource is legitimate.
3. **If (c) shows a source file with >10 violations:** file a bug against
   the owning team. A clean week requires (c) to be empty.
4. **After a clean week (zero violations across (a)–(c)):** the §2.8
   acceptance criterion "do not switch CSP from report-only to enforce
   until a week of clean reports" is satisfied. At that point, consider
   promoting any tightened directives from the report-only mirror into
   the enforcing header (currently they're identical, so this is a no-op
   unless someone tightens the mirror first).

---

## 4. Rate-limit & failure-mode notes

- **Rate limit (60/min/IP):** enforced via the same `rate_limit()` helper
  used by login/register. Uses Redis if available, else an in-process
  sliding-window dict. Over the limit → `429` (the browser will NOT
  retry on 4xx).
- **DB outage:** the handler wraps the audit write in `try/except`. A DB
  failure is logged at `warning` level but the endpoint still returns
  `204` so the browser doesn't retry.
- **Malformed body:** if `json.loads` fails, the endpoint logs
  `csp_report_body_invalid` at `warning` level and returns `204` (never
  `400` — same retry-avoidance reasoning).
- **Body size limit:** 50KB (CSP reports are typically <2KB; a hostile
  client streaming megabytes is rejected at the `body()` call).

---

## 5. Test coverage

See `tests/security_csp_report_test.py` for the integration test that
exercises:

1. POST a legacy `csp-report` body → `204` + structured log line + (when
   authenticated) an `audit_events` row tagged `csp.violation`.
2. Unauthenticated POST → `204` + log line + NO audit row (guest-page
   noise must not pollute the audit trail).
3. Reporting-API shape (array body) → `204` + same downstream effects.
4. Rate limit: 60 requests succeed, 61st returns `429`.
5. Enforcement policy unchanged: the `Content-Security-Policy` header
   is byte-identical to its pre-V54.28 value.
