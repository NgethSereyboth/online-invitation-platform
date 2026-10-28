# Penetration-test intake — template

> **Template, not evidence.** No penetration test has been commissioned against this tree. Copy it to
> `docs/certification/PEN-TEST-INTAKE-<YYYY>-<auditor>.md` when an engagement starts, fill it with the
> terms actually agreed, and file the tester's report under `docs/security/pen-test-reports/`. Until a
> signed report and a remediation register exist, roadmap §8.3's pen-test item and
> `CERTIFICATION.md` §3 stay open.
>
> Scope, methodology and per-chapter cases: [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md). Severity and
> acceptance gates: its §5–§6.

## 1. Engagement

| Field | Value |
|---|---|
| Tester / firm | `<name>` |
| Independence attestation | `<no commits to this repository in the prior 12 months — evidence>` |
| Contract / NDA reference | `<id, date>` |
| Window | `<YYYY-MM-DD … YYYY-MM-DD>` |
| Standard | ASVS **5.0.0 Level 2** (not Level 1) |
| Primary contact | `<name, channel>` |
| Emergency contact | `<name, channel>` |

## 2. Scope

- **In scope:** `<copy the final list from PEN-TEST-SCOPE.md §1.1; name the environment hostnames>`
- **Out of scope:** `<copy §1.2; add anything agreed for this engagement>`
- **Environment(s) provided:** `<staging URL(s), isolated from production guest data? yes/no>`
- **Test accounts:** `<count and roles — admin, host, guest; MFA enabled/disabled per account>`
- **Secrets/keys provided:** `<what, how delivered, rotation date after the test>`
- **Production-like settings:** `<rate limits, CSP, malware scanner, HTTPS/HSTS — what is live>`
- **Deliberate deviations from production:** `<anything disabled or relaxed, and why the finding still
  applies>`

## 3. Rules of engagement

- No destructive action against production; staging only unless a specific test is agreed in writing.
- No social engineering, no physical access, no third-party provider attacks.
- Denial-of-service only inside `<agreed window>, with <agreed ceiling>`; the load test is a separate
  engagement.
- Guest data: use seeded accounts only; if a real record is exposed, stop and report immediately.
- Test data and copies destroyed by `<date>`; evidence retained per the NDA.
- Disclosure: findings to the maintainer first, public disclosure only after remediation or
  `<N>` days, whichever is later.
- Re-test included for Critical/High findings: `<yes/no>`.

## 4. Deliverable

- One report, filed as `docs/security/pen-test-reports/<YYYY>-<auditor>.md` (PDF acceptable when the
  firm delivers one; link it from the Markdown record).
- Per finding: `id`, title, severity, CVSS vector, affected endpoint/component, reproduction steps,
  evidence (request/response or screenshot), impact, remediation guidance.
- Executive summary, methodology, and a scope-vs-tested matrix against the ASVS L2 chapters.
- A separate machine-readable findings list if the firm provides one: `<format>`.

## 5. Severity and remediation SLA

| Severity | Blocks sign-off? | SLA |
|---|---|---|
| Critical | Yes | Remediated + re-tested before sign-off |
| High | Yes | Remediated + re-tested before sign-off |
| Medium | No | Owner + target quarter |
| Low | No | Owner + target quarter |

## 6. Findings register

| ID | Severity | Title | Status | Remediation commit / control | Re-test |
|---|---|---|---|---|---|
| `<PT-001>` | `<Critical/High/Medium/Low>` | `<title>` | `<open/fixed/accepted>` | `<commit or compensating control>` | `<date / n/a>` |

## 7. Remediation sign-off

For every Critical/High: either a remediation commit **with a regression test**, or a documented
compensating control plus a maintainer risk-acceptance sign-off (allowed only when remediation needs an
architectural change, e.g. moving off stdlib `http.server`).

| Role | Name | Date | Signature |
|---|---|---|---|
| Maintainer | `<name>` | `<date>` | `<signature>` |
| Tester (re-test verdict) | `<name>` | `<date>` | `<signature>` |

## 8. Handover checklist

- [ ] Report filed under `docs/security/pen-test-reports/`.
- [ ] Every Critical/High fixed and re-tested, or risk-accepted in writing.
- [ ] Medium/Low in `docs/security/remediation-backlog.md` with owners and quarters.
- [ ] Test accounts disabled and their secrets rotated.
- [ ] `CERTIFICATION.md` §3 updated with the report reference and the re-test date.
- [ ] Any deliberate production deviation restored and verified.
