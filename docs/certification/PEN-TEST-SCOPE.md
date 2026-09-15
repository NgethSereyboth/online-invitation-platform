# Penetration Test Scope — OWASP ASVS 5.0.0 Level 2

> **Phase 3 deliverable.** Companion file to [`CERTIFICATION.md`](./CERTIFICATION.md) §3. This document defines the scope, methodology, and per-chapter test cases for the Phase 3 penetration test.
>
> **Standard.** OWASP Application Security Verification Standard (ASVS) 5.0.0 — **Level 2** (system handling personal data — guest PII and RSVPs). Level 1 alone is insufficient per [`docs/ROADMAP.md`](../ROADMAP.md) §1b.
>
> **Gap analysis.** The internal self-assessment is in [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) (Phase 1b deliverable — 14 chapters, 154 requirement rows, prioritized remediation list P1-A through P4-F). That document is the **input** to this penetration test: the pen tester verifies the gaps the self-assessment identified and looks for new findings the self-assessment missed.
>
> **AI agent security.** The 80 AI agent tools are also scoped against OWASP AISVS 1.0 Chapters C9 (Orchestration & Agentic Security) and C10 (MCP Security). The AISVS mapping is in [`docs/ai/AISVS-C9-C10-MAPPING.md`](../ai/AISVS-C9-C10-MAPPING.md) (Phase 1a deliverable). The 12 high-blast-radius attack stories are in [`docs/ai/attack-stories/`](../ai/attack-stories/) — the pen tester should use these as **grey-box** test cases for the AI agent scope (§2.2 below).

---

## 1. Scope

### 1.1 In scope

| Target | Surface | How to reach |
|--------|---------|--------------|
| The ~150 HTTP routes in `src/python/server.py` | `do_GET`, `do_POST`, `do_PUT`, `do_DELETE` dispatch tables (lines 3091, 3290, 3209, 3255) | The base URL: `https://<host>/api/...` + the 16 server-rendered HTML pages |
| The 80 AI agent tools in `ai_agent/tools.py` | `POST /api/invitations/{id}/ai/plan` + `POST /api/invitations/{id}/ai/execute` + `POST /api/invitations/{id}/ai/cancel` | The dashboard editor's AI agent panel |
| The V32 platform endpoints in `platform_v32/service.py` + `platform_v32/storage.py` | Workspaces, jobs, observability, backups, schema migrations | `POST /api/platform/workspaces`, `POST /api/platform/jobs`, `GET /api/platform/health`, `GET /api/platform/metrics` |
| The V52 future platform endpoints in `future_platform_v52/service.py` | Event ecosystem, automation runs, data-merge jobs, animation export jobs, marketplace packages | `POST /api/platform/event-ecosystem/...`, `POST /api/platform/data-merge/...`, `POST /api/platform/animation/...`, `POST /api/platform/marketplace/...` |
| The auth/session subsystem | Registration, login, MFA, passkeys, password reset, email verification, session revocation | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/mfa/...`, `POST /api/auth/passkey/...`, `POST /api/auth/password-reset/...` |
| The public invitation subsystem (unauthenticated) | Public invitation view, RSVP, wish submission, view tracking, gallery unlock, check-in | `GET /i/{slug}`, `POST /api/public/{slug}/rsvps`, `POST /api/public/{slug}/wishes`, `POST /api/public/{slug}/view`, `POST /api/public/{slug}/unlock`, `POST /api/public/{slug}/gallery/unlock` |
| The collaboration subsystem | SSE collaboration stream, optimistic-locking mutation endpoint, presence | `GET /api/invitations/{id}/collab/stream` (SSE), `PUT /api/invitations/{id}/collab/mutations`, `POST /api/invitations/{id}/collab/presence` |
| The file upload + asset pipeline | Material upload, album upload, asset listing, asset delete | `POST /api/invitations/{id}/assets` (multipart), `POST /api/invitations/{id}/album` (multipart), `DELETE /api/invitations/{id}/assets/{asset_id}` |
| The V54 malware scanner gate | ClamAV INSTREAM (Linux) + MpCmdRun.exe (Windows) fail-closed path | Triggered by every upload route; the EICAR test signature (b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE") should return HTTP 422 with `code=malware_detected` |

### 1.2 Out of scope

| Out-of-scope item | Rationale |
|-------------------|-----------|
| The host operating system (Linux kernel, Windows Defender, firewall rules) | The OS is in scope for the native platform matrix ([`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md)), NOT for the pen test. The pen test scopes the **application**, not the OS. |
| The PostgreSQL database engine itself | CVE-2022-* and similar PG bugs are out of scope; the application's **use** of PG (SQL injection, parameter binding) is in scope. |
| Third-party SaaS dependencies (Stripe, SendGrid, OpenAI) | Their security is their own; the application's **integration** with them (webhook signature verification, outbound HTTPS only — see ASVS gap `[9.1.4]`) is in scope. |
| The browser extension model (Phase 4 plugin marketplace — not yet implemented) | Out of scope until Phase 4 lands. |

---

## 2. Methodology

The pen test is conducted in three passes, each with a different knowledge level for the tester.

### 2.1 Black-box (external tester, no source access)

**Knowledge:** The tester receives only the base URL (`https://staging.einvite.example.com`) and a single host account credential.

**Goal:** Find vulnerabilities that an external attacker would find. This pass catches issues that the self-assessment missed because the self-assessment was reading source code (the self-assessment "knew" the code, so it didn't test what an outsider would discover).

**Method:**
- Network reconnaissance (nmap, dnsenum).
- Web crawling (Burp Suite, OWASP ZAP) to enumerate the ~150 routes.
- Authenticated fuzzing of every discovered endpoint.
- Unauthenticated fuzzing of the public invitation routes (RSVP, wish, view, unlock).
- Parameter injection (SQL, OS command, LDAP, XPath, NoSQL).
- Business-logic testing (RSVP count negative values, RSVP `count` > `max_guests`, RSVP after `rsvpCloseDate`, RSVP with a faked `guestToken`).
- Session testing (cookie tampering, session fixation, JWT forgery if the platform used JWTs — it does not; the platform uses signed HttpOnly cookies).
- CSP evaluation (can a reflected XSS bypass the `script-src 'self'` CSP? The Phase 1b gap `[1.1.1]` was remediated — see [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) `### P1-A`).

### 2.2 Grey-box (tester has docs + schemas)

**Knowledge:** The tester receives everything in §1.1 above PLUS:
- This document ([`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md)).
- The Phase 1b gap analysis ([`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md)).
- The Phase 1a AISVS C9/C10 mapping ([`docs/ai/AISVS-C9-C10-MAPPING.md`](../ai/AISVS-C9-C10-MAPPING.md)).
- The 12 high-blast-radius AI agent attack stories ([`docs/ai/attack-stories/`](../ai/attack-stories/)).
- The Postgres schema ([`docs/postgres_schema.sql`](../postgres_schema.sql)).
- The API surface inventory (route-bundles-v15.json — generated by `build_route_bundles.py`).

**Goal:** Find vulnerabilities that require knowing the application's data model and route inventory. The tester targets the specific gaps the self-assessment identified, plus the attack stories for the AI agent.

**Method:**
- For each prioritized remediation item (P1-A through P4-F in [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md)), verify the remediation is actually in effect (the self-assessment may claim "pass" but the implementation may be incomplete).
- For each of the 12 attack stories in [`docs/ai/attack-stories/`](../ai/attack-stories/), attempt the documented worst-case scenario and confirm the containment actually triggers.
- For every endpoint enumerated in the route bundles, attempt ASVS-chapter-appropriate test cases (see §4 below).

### 2.3 White-box (tester has source access)

**Knowledge:** Everything in §2.2 PLUS full source code access (`git clone`).

**Goal:** Find vulnerabilities that require reading the code. This pass catches issues that the black-box + grey-box passes miss because they require understanding the control flow.

**Method:**
- Manual source review of the security-critical paths:
  - `server.py::Handler.guard_request_boundary` (lines 2397-2641) — the host allowlist, HTTPS 308 redirect, AI tool authorization, CSRF guard.
  - `server.py::Handler.guard_cookie_origin` — the `Origin` + `Sec-Fetch-Site` + double-submit CSRF check.
  - `server.py::connect` — the SQLite/PostgreSQL switch + parameterized query audit (every `db.execute` call uses `?` placeholders, not f-strings).
  - `security_v13.py` — the password hashing (Argon2id), TOTP, ES256 passkey registration.
  - `security_scanner_v54.py` — the ClamAV INSTREAM + MpCmdRun.exe fail-closed path.
  - `secrets_v54.py` — the auto-secret bootstrap.
  - `production_preflight.py` — the startup gate that refuses to boot if `EINVITE_ALLOW_NO_SCANNER=1` is set in a production environment.
  - `ai_agent/service.py::authorize_tool_call` — the resource-scoped permission check + JIT elevation (5-minute TTL).
  - `ai_agent/capabilities.py` — the role-permission binding.
- Static analysis: `bandit -r src/python/` + `semgrep --config p/owasp-top-ten src/python/` (Phase 1b gap `[10.1.3]` — see [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) `### P4-C`).
- Dependency analysis: `pip-audit -r requirements-production.txt` (gap `[10.1.1]`) + `trivy fs .` (gap `[10.1.2]`).

---

## 3. Per-ASVS-chapter test cases

The Phase 1b gap analysis ([`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md)) is organized into 14 chapters. Each chapter has a table of requirement rows with Status (`pass`/`partial`/`fail`) and Evidence (file:line). The pen tester's job is to **verify** each `pass` claim and **attempt exploitation** for each `partial`/`fail` claim.

| ASVS chapter | Title | Gap-analysis rows | Pen-test focus |
|--------------|-------|--------------------|-----------------|
| 1 | Encoding and Sanitization (Injection / XSS) | Reflected HTML injection in `serve_public` (gap `[1.1.1]`, remediated as P1-A). Content-Disposition filename escaping (gap `[1.1.8]`, P2-E). | Verify the `serve_public` reflected-XSS fix. Test every `Content-Disposition` header for filename injection. |
| 2 | Validation and Business Logic | Per-user rate limits on invitation/template/draft mutations (gap `[2.1.4]`, P2-A). Free-form text Unicode normalization (gap `[2.1.1]`, P3-K). | Test RSVP `count` boundary (1..max_guests). Test `rsvpCloseDate` enforcement (HTTP 410 with `code=rsvp_closed`). Test rate limits: 13th RSVP within 60s from same IP returns 429. |
| 3 | Web Frontend Security | `style-src 'unsafe-inline'` migration (gap `[3.1.7]`, P3-J — currently `style-src 'unsafe-inline'` because the editor uses inline `<style>` blocks for theme tokens). | Verify whether a malicious inline `<style>` can inject a `background:url()` data exfil. Note: `style-src 'unsafe-inline'` is a documented Phase 3 follow-up; the pen test should confirm the risk is bounded (no inline event handlers, no `javascript:` URLs in CSS). |
| 4 | API and Web Service (Overview) | (Overview chapter — no direct test cases.) | — |
| 5 | File Handling | Upload MIME allow-list, magic-byte verification, malware scan (V54 fail-closed). | Upload the EICAR test signature as a PNG (the upload route accepts `image/png` MIME; the scanner gate fires after the magic-byte check — verify the 422 path). Upload a polyglot JPEG/ZIP that the magic-byte check accepts but ClamAV flags. |
| 6 | Authentication | Account lockout for repeated password failures (gap `[6.1.13]`, P1-B — implemented in `security_v13.py`). MFA recovery codes (gap `[6.1.5]`, P1-C). Security notification on MFA enable/disable (gap `[6.1.11]`, P1-D). | Verify lockout triggers after N failed attempts. Verify MFA recovery codes are single-use + logged. Verify the security-notification email fires on MFA enable/disable. |
| 7 | Session Management | Idle session timeout (gap `[7.1.4]`, P2-B). | Verify a session idle for >T minutes is rejected with 401. |
| 8 | Authorization | Multi-tenant data-isolation lint test (gap `[8.1.7]`, P2-C). Invitation role checks (`can_read_invitation`, `can_edit_invitation`, `can_manage_invitation`). | Attempt to access another tenant's invitation by ID (should return 403). Attempt to perform a `manage` action with `edit` role (should return 403). Attempt the AI agent's `publish` tool without the JIT 5-minute elevation (should return 403). |
| 9 | Communication Security | HTTPS-only outbound webhook calls (gap `[9.1.4]`, P3-C). Postgres `sslmode=require` enforcement (gap `[9.1.6]`, P3-D). | Verify the `EINVITE_DATABASE_URL` env var, when set without `sslmode=require`, is rejected at startup by `production_preflight.py`. Verify outbound webhook calls (delivery_channels email/SMS/WhatsApp/Telegram) refuse `http://` URLs. |
| 10 | Malicious Code Search | `pip-audit` / `safety` in CI (gap `[10.1.1]`, P4-A). Trivy image scan in CI (gap `[10.1.2]`, P4-B). Bandit + Semgrep SAST (gap `[10.1.3]`, P4-C). SBOM generation (gap `[10.1.4]`, P4-D). CODEOWNERS + PR template (gap `[10.1.6]`, P4-E). | Run each tool against the current `src/python/` tree; report any high-severity findings. |
| 11 | Business Logic / Data Integrity | Audit retention enforcement job (gap `[11.1.3]`, P3-E). | Verify the `audit_events` hash chain — every row's `prev_hash` = SHA-256 of the previous row's `hash` + `event_type` + `actor` + `created_at`. Test by inserting a row out-of-order (should fail the BEFORE INSERT trigger). |
| 12 | Files and Resources | (Overlaps with Chapter 5.) | — |
| 13 | API and Web Service (Detailed) | Retry-After header on 429 responses (gap `[13.1.2]`, P2-D). Generic exception handler for `do_GET/PUT/POST/DELETE` (gap `[13.1.8]`, P3-A). Per-user SSE connection limit (gap `[13.1.7]`, P3-B). Pagination caps on list endpoints (gap `[13.1.3]`, P3-I). OpenAPI spec (gap `[13.1.10]`, P3-M). | Verify 429 responses include `Retry-After: <seconds>`. Verify a generic 500 response does not leak the Python traceback. Verify per-user SSE connections are capped (default 5). Verify `?limit=` cannot exceed the cap (default 100). |
| 14 | Configuration and Deployment | Container runs as non-root (gap `[14.1.8]`, P3-G). Restrictive permissions on `DATA` directory (gap `[14.1.7]`, P3-H). Security headers on 503 from request-slot semaphore (gap `[14.1.12]`, P3-F). Generic 500 error handler + structured logging (gap `[14.1.13]`, P3-L). | Verify the Dockerfile's `USER` directive is not root. Verify `data/` is mode 0750. Verify a 503 response (sent when the request-slot semaphore is exhausted) includes the standard security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy). |

The full requirement-by-requirement matrix is in [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) — the pen tester is expected to walk every row in that document and re-verify the Status column independently.

---

## 4. Deliverable

The pen tester delivers a **signed report** with the following sections:

| Section | Contents |
|---------|----------|
| Executive summary | 1-page summary: number of findings by severity, overall risk posture, recommendation. |
| Methodology | Confirm the black-box + grey-box + white-box passes were executed. Document the tools used. |
| Findings | One entry per finding, classified Critical / High / Medium / Low. Each entry has: Title, ASVS chapter + requirement ID, severity, description, proof-of-concept (HTTP request/response), remediation recommendation, status (open / remediated / accepted-risk). |
| Remediation verification | For every finding that was remediated during the pen test engagement, the tester re-tests and confirms the fix. |
| Sign-off | Tester name + organization + date + signature. |

**Filing location:** `docs/security/pen-test-reports/<YYYY>-<auditor>.md` (Markdown) or `docs/security/pen-test-reports/<YYYY>-<auditor>.pdf` (PDF, if delivered by an external auditor on letterhead).

---

## 5. Severity classification

| Severity | Definition | SLA for remediation |
|----------|------------|---------------------|
| **Critical** | Remote code execution, SQL injection with auth bypass, full account takeover, breach of guest PII at scale. | Blocks Phase 3 sign-off. Must be remediated + re-tested before sign-off. |
| **High** | Authenticated SQL injection, IDOR across tenants, privilege escalation, MFA bypass, CSRF on a state-changing endpoint. | Blocks Phase 3 sign-off. Must be remediated + re-tested before sign-off. |
| **Medium** | Reflected XSS (no auth bypass), information disclosure (stack trace, internal IP), missing rate limit on a low-impact endpoint. | Owner + target remediation quarter. Does not block Phase 3 sign-off. |
| **Low** | Missing security header on a non-sensitive response, verbose error message, cookie without `Secure` flag on an HTTP-only dev path. | Owner + target remediation quarter. Does not block Phase 3 sign-off. |

---

## 6. Acceptance gates

1. A signed pen test report is filed under `docs/security/pen-test-reports/`.
2. Every Critical or High finding has either:
   - A remediation commit with a regression test (preferred), OR
   - A documented compensating control + a risk-acceptance sign-off by the maintainer (acceptable only when remediation is not technically possible without a major architectural change — e.g. migrating away from stdlib `http.server`).
3. Every Medium / Low finding has an owner and a target remediation quarter. Tracked in `docs/security/remediation-backlog.md`.
4. The pen test was scoped against ASVS 5.0.0 **Level 2** (not Level 1).
5. The pen tester is independent of the eInvite Platform development team (no commits to the main branch in the prior 12 months).

---

## 7. Cross-references

- [`CERTIFICATION.md`](./CERTIFICATION.md) §3 — executive summary.
- [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) — Phase 1b self-assessment; the input to this pen test.
- [`docs/ai/AISVS-C9-C10-MAPPING.md`](../ai/AISVS-C9-C10-MAPPING.md) — Phase 1a AI agent governance.
- [`docs/ai/attack-stories/`](../ai/attack-stories/) — 12 high-blast-radius attack stories (grey-box test cases).
- [`docs/SECURITY.md`](../SECURITY.md) — high-level security overview.
- [`docs/SECURITY_HARDENING_REPORT_2026-08-10.md`](../SECURITY_HARDENING_REPORT_2026-08-10.md) — V54 hardening report (the "remaining production work" list at the end of this document is the precursor to the Phase 3 pen-test scope).
- [`docs/ROADMAP.md`](../ROADMAP.md) §1b + §10 Step 7 — the ASVS research that grounded Phase 1b.
