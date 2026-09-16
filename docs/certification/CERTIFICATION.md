# Production Certification — eInvite Platform V54.5

> **Phase 3 deliverable.** This is the signed certification checklist required by [`docs/ROADMAP.md`](../ROADMAP.md) §6 (Phase 3 — Production Certification). It aggregates the evidence from five independent work-streams — native platform matrix, browser matrix, penetration test, load test, and the second quarterly DR drill — into a single sign-off page.
>
> **Bilingual note.** All user-facing strings in the platform are bilingual EN + KH per ROADMAP ground rule 5. The report-template field labels in this document are mirrored in both scripts where the platform surfaces them to a host (e.g. the load-test report template and the DR-drill report template).
>
> **Status legend.**
> - **pass** — requirement met; evidence is linked.
> - **fail** — requirement not met; remediation is in flight and tracked below.
> - **pending** — procedure is written but has not yet been executed against the target platform.
> - **na** — requirement does not apply (rationale required in the Evidence column).

---

## §1. Native platform matrix (Windows + Linux 3× each)

Full procedure and per-platform acceptance gates live in [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md). This section is the executive summary.

The matrix covers **clean install + V53.1 → V54 upgrade + V54 → V53.1 rollback** on six operating systems:

| ID | Platform | Install | Upgrade | Rollback | Status | Evidence | Sign-off |
|----|----------|---------|---------|----------|--------|----------|----------|
| N1 | Windows 11 (consumer) | `scripts/setup-einvite-complete.ps1` | V53.1 → V54 | V54 → V53.1 | pending | [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §Windows 11 · `tests/v16_windows_ui_hardening_test.py` | — |
| N2 | Windows Server 2022 | `scripts/setup-einvite-complete.ps1` + `deploy/windows/start-einvite-windows-server.ps1` | V53.1 → V54 | V54 → V53.1 | pending | [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §Windows Server 2022 | — |
| N3 | Windows Server 2025 (or current) | `scripts/setup-einvite-complete.ps1` | V53.1 → V54 | V54 → V53.1 | pending | [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §Windows Server 2025 | — |
| N4 | Ubuntu 22.04 LTS | `deploy/linux/install-einvite-laptop.sh` | V53.1 → V54 | V54 → V53.1 | pending | [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §Ubuntu 22.04 · `tests/v14_live_server_acceptance_test.py` | — |
| N5 | Ubuntu 24.04 LTS | `deploy/linux/install-einvite-laptop.sh` | V53.1 → V54 | V54 → V53.1 | pending | [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §Ubuntu 24.04 | — |
| N6 | Debian 12 | `deploy/linux/install-einvite-laptop.sh` | V53.1 → V54 | V54 → V53.1 | pending | [`NATIVE-PLATFORM-MATRIX.md`](./NATIVE-PLATFORM-MATRIX.md) §Debian 12 | — |

**Acceptance gates per platform (all six must hold):**
1. The server boots and reports `E-invitation-website: http://<host>:<port>` (see `server.py` startup banner).
2. `/api/health/live` returns 200 within 10 seconds of boot.
3. All 16 server-rendered HTML pages return HTTP 200 with `Content-Security-Policy: script-src 'self'` and no `require-trusted-types-for` directive (asserted by `tests/v14_live_server_acceptance_test.py`).
4. The stdlib test suite passes (deterministic subset, no Playwright required): `python3 tests/v16_windows_ui_hardening_test.py` + the security regression suite (`tests/security_regression_test.py`, `tests/v0_52_security_boundary_test.py`).
5. The on-startup fail-closed malware scanner is detected: ClamAV (`clamdscan`/`clamd` on Linux) **or** Microsoft Defender (`MpCmdRun.exe` on Windows). See `src/python/security_scanner_v54.py`.
6. `production_preflight.py --check-dependencies` returns 0.

---

## §2. Browser matrix (4 desktop + 2 mobile)

Full procedure and per-browser acceptance gates live in [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md). This section is the executive summary.

The project is **build-tool-free** (vanilla JS, no transpiler, no bundler). Browser compatibility is therefore primarily a function of (a) CSS feature support, (b) WebCrypto support for ES256 passkeys, and (c) WebGL support for the V22 scene model. See `tests/browser_runtime.py` and `tests/inline_editor_runtime_test.py` for the existing automated coverage (Chromium only — the matrix below extends that to the other browsers).

| ID | Browser | Version target | Status | Evidence | Sign-off |
|----|---------|----------------|--------|----------|----------|
| B1 | Chrome (desktop) | latest stable | pending | [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md) §Chrome · `tests/inline_editor_runtime_test.py` (Chromium baseline) | — |
| B2 | Firefox (desktop) | latest ESR + latest stable | pending | [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md) §Firefox | — |
| B3 | Safari (desktop) | latest stable (macOS 14+) | pending | [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md) §Safari | — |
| B4 | Edge (desktop) | latest stable | pending | [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md) §Edge | — |
| B5 | Safari iOS | latest stable (iOS 17+) | pending | [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md) §Safari iOS | — |
| B6 | Chrome Android | latest stable (Android 13+) | pending | [`BROWSER-MATRIX.md`](./BROWSER-MATRIX.md) §Chrome Android | — |

**Per-browser acceptance gates (all six must hold):**
1. All 16 HTML pages render without `console.error` (excluding third-party favicon/YouTube/SoundCloud origin errors — see `tests/v14_live_server_acceptance_test.py::serious_console`).
2. The editor (`/dashboard.html` → editor route) loads with `document.documentElement.dataset.editorReady === 'true'`.
3. The public RSVP form `POST /api/public/{slug}/rsvps` submits and the host sees the row in `/api/invitations/{id}/rsvps`.
4. The AI agent panel (`src/js/ai-creative-agent-v28.js` + `src/js/ai-assistant-loader-v27.js`) renders without runtime errors; the tool-registry loads.
5. Bilingual EN↔KH toggle works on all bilingual pages; the toggle persists in `localStorage` and re-renders without a full page reload.
6. No CSP violation report in the browser dev-tools console (the CSP is `script-src 'self'` — see `server.py::end_headers`).

---

## §3. Penetration test scope (OWASP ASVS 5.0.0 L2)

Full scope, methodology, and per-chapter test cases live in [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md). The gap analysis the pen test scopes against lives in [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) (Phase 1b deliverable — 14 chapters, 154 requirement rows, prioritized remediation list P1-A through P4-F).

| ID | Scope item | Status | Evidence | Sign-off |
|----|-----------|--------|----------|----------|
| P1 | Pen test targets the ~150 routes in `src/python/server.py` (do_GET/do_POST/do_PUT/do_DELETE dispatch) | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §2.1 | — |
| P2 | Pen test targets the 80 AI agent tools registered in `ai_agent/tools.py` (ASVS L2 + AISVS C9/C10) | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §2.2 · [`docs/ai/AISVS-C9-C10-MAPPING.md`](../ai/AISVS-C9-C10-MAPPING.md) | — |
| P3 | Pen test targets the V32 platform endpoints (workspaces, jobs, observability, backups) | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §2.3 | — |
| P4 | Methodology: black-box (external tester, no source) + grey-box (docs + schemas) + white-box (source access) | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §3 | — |
| P5 | All ASVS L2 chapters covered (1 Encoding → 14 Configuration) — refer to gaps in [`ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §4 · [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) | — |
| P6 | Signed pen test report delivered with findings classified Critical / High / Medium / Low | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §5 | — |
| P7 | All Critical + High findings remediated before sign-off | pending | [`PEN-TEST-SCOPE.md`](./PEN-TEST-SCOPE.md) §6 (acceptance) | — |

**Acceptance gates:**
1. A signed report is filed under `docs/security/pen-test-reports/<YYYY>-<auditor>.md` (or PDF if delivered by an external auditor).
2. Every Critical or High finding has either (a) a remediation commit with a test, or (b) a documented compensating control + risk-acceptance sign-off by the maintainer.
3. Medium/Low findings have an owner and a target remediation quarter; they do not block Phase 3 sign-off.
4. The pen test was scoped against ASVS 5.0.0 L2 (not L1) — the platform handles guest PII, so L1 is insufficient per [`docs/ROADMAP.md`](../ROADMAP.md) §1b.

---

## §4. Load test plan (k6)

Full plan, scenarios, and reference-deployment numbers live in [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md). The k6 script lives at [`tests/load_test_k6.js`](../../tests/load_test_k6.js). The k6 script was chosen over Locust because k6 is JS-based and easier to integrate with a stdlib-only setup (Locust requires `pip install locust` and a separate runner).

| ID | Scenario | Target | Status | Evidence | Sign-off |
|----|----------|--------|--------|----------|----------|
| L1 | Concurrent RSVP submissions — wedding-season burst | 1000 RSVPs in 5 minutes | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §3.1 · `tests/load_test_k6.js` (scenario `rsvp_burst`) | — |
| L2 | Concurrent AI agent tool invocations | 50 parallel tool calls | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §3.2 · `tests/load_test_k6.js` (scenario `ai_tool_calls`) | — |
| L3 | Concurrent collaboration updates | 20 simultaneous editors per invitation | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §3.3 · `tests/load_test_k6.js` (scenario `collab_edits`) | — |
| L4 | Public invitation page views | 10000 views over 1 hour | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §3.4 · `tests/load_test_k6.js` (scenario `public_views`) | — |
| L5 | 95th-percentile response time — RSVP | < 500 ms | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §4 | — |
| L6 | 95th-percentile response time — AI agent | < 2 s | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §4 | — |
| L7 | Zero HTTP 5xx errors during any scenario | 0 | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §4 | — |
| L8 | Reference deployment benchmark | 2 vCPU / 4 GB RAM / PostgreSQL | pending | [`LOAD-TEST-PLAN.md`](./LOAD-TEST-PLAN.md) §5 | — |

**Acceptance gates:**
1. The k6 script runs end-to-end against a staging deployment without manual intervention (set `EINVITE_LOAD_TEST_BASE_URL` + `EINVITE_LOAD_TEST_SLUG`).
2. The reference deployment numbers (§5 of the load-test plan) are reproducible within ±20% on a clean 2 vCPU / 4 GB RAM VPS.
3. No HTTP 5xx errors during the burst scenario; the request-slot semaphore in `server.py::Handler` degrades gracefully to 503 with the standard security headers (ASVS L2 gap `[14.1.12]` — see [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md)).

---

## §5. Disaster recovery drill (second quarterly drill)

The first quarterly DR drill plan and report template live in [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §5 (Phase 1c deliverable). Phase 3 adds the **second quarterly drill** section in [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9 — see the appended section.

| ID | Drill item | Status | Evidence | Sign-off |
|----|-----------|--------|----------|----------|
| D1 | Scenario: simulated primary DB corruption at 02:00 UTC | pending | [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9.2 | — |
| D2 | Declare incident (runbook §1) | pending | [`docs/ops/RESTORE-RUNBOOK.md`](../ops/RESTORE-RUNBOOK.md) §1 | — |
| D3 | Restore from pgBackRest to staging | pending | [`docs/ops/RESTORE-RUNBOOK.md`](../ops/RESTORE-RUNBOOK.md) §2-§5 | — |
| D4 | Validate row counts on Tier-1 tables (rsvps, guests, invitations, audit_events) | pending | [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9.3 | — |
| D5 | Validate `audit_events` hash-chain integrity (0 broken links) | pending | [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9.3 | — |
| D6 | Measured RTO ≤ Tier-1 target (30 min) | pending | [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9.3 | — |
| D7 | Drill report filed under `docs/ops/drill-reports/<YYYY>-Q<n>.md` | pending | [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9.4 | — |
| D8 | Gaps documented as action items with owners + due dates | pending | [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9.4 | — |

**Acceptance gates:**
1. Every step in [`RESTORE-RUNBOOK.md`](../ops/RESTORE-RUNBOOK.md) was executed without the on-call engineer inventing a new procedure (small flag changes are OK; new procedures are not — they must be filed as action items).
2. The measured RTO fits inside the Tier-1 budget of ≤ 30 minutes.
3. The measured RPO fits inside the Tier-1 budget of ≤ 5 minutes.
4. All canaries pass (row counts match production ±0; hash-chain integrity = 0 broken links; object-storage bucket listing matches).
5. This is the **second** drill — the first was Phase 1c (Q1). A drill that surfaces gaps is **more valuable** than one that passes trivially, provided the gaps are filed as action items.

---

## §6. Sign-off

Phase 3 certification is **complete** only when all five sections above (§1–§5) are marked **pass** in the Status column, with evidence linked and acceptance gates verified. A pending or failing item blocks sign-off.

### Maintainer signature

By signing, the maintainer attests that:
- They have personally reviewed the evidence linked in §1–§5.
- All Critical + High pen-test findings (§3) are remediated.
- The load test (§4) was run against the reference deployment and meets the 95th-percentile targets.
- The second quarterly DR drill (§5) was executed and meets the Tier-1 RTO/RPO targets.
- No working code was deleted during Phase 3 — only documentation, the k6 script, and the BACKUP-DR.md extension were added (see `VERSION_HISTORY.md` V54.5 entry).

| Field | Value |
|-------|-------|
| Maintainer name | <name> |
| Role | Project maintainer |
| Date (UTC) | YYYY-MM-DD |
| Signature | `<gpg --clearsign>` or `(signed via commit)` |

### External auditor signature

By signing, the external auditor attests that:
- They are independent of the eInvite Platform development team.
- They performed (or supervised) the penetration test scoped in §3 against ASVS 5.0.0 L2.
- They witnessed (or reviewed the report of) the load test (§4) and the DR drill (§5).
- They have no unresolved objections to certification.

| Field | Value |
|-------|-------|
| Auditor name | <name> |
| Organization | <organization> |
| Date (UTC) | YYYY-MM-DD |
| Signature | `<gpg --clearsign>` or `(signed letterhead)` |

---

## Cross-references

- [`docs/ROADMAP.md`](../ROADMAP.md) §6 — Phase 3 task definition.
- [`docs/ROADMAP.md`](../ROADMAP.md) §1c — Phase 1c DR drill (the **first** drill; this is the second).
- [`docs/security/ASVS-L2-GAP-ANALYSIS.md`](../security/ASVS-L2-GAP-ANALYSIS.md) — Phase 1b gap analysis; basis for §3.
- [`docs/ai/AISVS-C9-C10-MAPPING.md`](../ai/AISVS-C9-C10-MAPPING.md) — Phase 1a AI governance; cross-referenced from §3.
- [`docs/ops/BACKUP-DR.md`](../ops/BACKUP-DR.md) §9 — Phase 3 second DR drill (appended).
- [`docs/ops/RPO-RTO-TARGETS.md`](../ops/RPO-RTO-TARGETS.md) — tier definitions referenced from §4 + §5.
- [`docs/ops/RESTORE-RUNBOOK.md`](../ops/RESTORE-RUNBOOK.md) — the 02:00 on-call procedure.
- [`VERSION_HISTORY.md`](../../VERSION_HISTORY.md) V54.5 — Phase 3 changelog entry.

## Change history

| Date | Change |
|------|--------|
| 2026-09-14 | Initial Phase 3 deliverable. Six-section certification framework (native matrix, browser matrix, pen-test scope, load-test plan, second DR drill, sign-off). Companion files: `NATIVE-PLATFORM-MATRIX.md`, `BROWSER-MATRIX.md`, `PEN-TEST-SCOPE.md`, `LOAD-TEST-PLAN.md`, `tests/load_test_k6.js`, extended `docs/ops/BACKUP-DR.md` §9. |
