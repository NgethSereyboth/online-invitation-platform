# Load-test result — template

> **Template, not evidence.** No load test has been run against this tree. Do not fill numbers in this
> file: copy it to `docs/certification/LOAD-TEST-RESULT-<YYYY-MM-DD>.md`, run the plan, and record the
> real output there. `docs/certification/CERTIFICATION.md` §4 stays unsigned until such a file exists.
>
> Plan and scenarios: [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md). Metrics tables: its §8. This file is
> the surrounding record — who ran it, against what, with which artifacts, and who signed it.

## 1. Run metadata

| Field | Value |
|---|---|
| Date / window | `<YYYY-MM-DD HH:MM–HH:MM TZ>` |
| Operator | `<name>` |
| Commit | `<git SHA>` (working tree clean? `<yes/no>`) |
| k6 version | `<version>` |
| Environment | `<e.g. 2 vCPU / 4 GB RAM / PG 15 / MinIO / Caddy>` |
| Database | `<PostgreSQL <version>, shared_buffers=<…>>` |
| Dataset | `<invitations / guests / RSVPs seeded>` |
| Rate limits relaxed for the run | `<none / list exactly what was changed and where>` |
| Artifacts | `<path to k6 JSON/summary, server logs, dashboards>` |

## 2. Acceptance targets being tested

These are the plan's §4 thresholds; do not restate them differently in the result.

| Metric | Target | Scenario |
|---|---|---|
| p95 — RSVP | < 500 ms | `rsvp_burst` |
| p95 — AI agent tool call | < 2 s | `ai_tool_calls` |
| p95 — collaboration edit | < 500 ms | `collab_edits` |
| p95 — public page GET | < 200 ms | `public_views` |
| HTTP 5xx | 0 | all scenarios |
| HTTP 4xx | < 1 %, excluding 429 and 409 | all scenarios |

## 3. Result summary

| Scenario | Peak VUs | p95 | 5xx | 4xx (non-429/409) | Verdict |
|---|---:|---:|---:|---:|---|
| L1 `rsvp_burst` | `<n>` | `<ms>` | `<n>` | `<%>` | `<PASS/FAIL>` |
| L2 `ai_tool_calls` | `<n>` | `<ms>` | `<n>` | `<%>` | `<PASS/FAIL>` |
| L3 `collab_edits` | `<n>` | `<ms>` | `<n>` | `<%>` | `<PASS/FAIL>` |
| L4 `public_views` | `<n>` | `<ms>` | `<n>` | `<%>` | `<PASS/FAIL>` |

Full per-metric tables: paste the filled §8 tables from the plan, or link the result section.

## 4. Resource ceilings observed

Peak CPU per vCPU, Python RSS, PostgreSQL RSS, connection count and disk write IOPS at peak — copy the
plan's §8 resource table with measured values. A run that stays inside the latency targets while
saturating a resource is a **capacity finding**, not a pass.

## 5. Gaps and changes during the run

- `<what was changed mid-run, why, and whether the run was restarted>`
- `<what the run could not exercise (e.g. CDN, multi-region, real WAN latency)>`

## 6. Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Maintainer | `<name>` | `<date>` | `<signature>` |

Verdict: `<all scenarios within budget / list the failing ones>`.

## 7. What this does not prove

A single-host k6 run validates throughput and tail latency on a known reference deployment. It does not
prove behaviour behind a CDN, across regions, under a real traffic mix, or past the seeded dataset size.
Those remain roadmap §8.3 external items until separately exercised.
