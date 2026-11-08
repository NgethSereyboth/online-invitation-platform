# Security audit remediation — 2026-11-07

**Repository:** `einvite-platform`
**HEAD at audit:** `3dace26` (`main`)
**Scope:** isolated local audit origin on `127.0.0.1:4311` (secure mode) and `127.0.0.1:4310` (non-secure E2E fixture), fixture data only.
**Status:** remediation complete for all in-repo issues that can be safely resolved without production access; human-owned items are listed below.

No commit, push, tag, merge, history rewrite, credential rotation, or production deployment was performed.

## Executive summary

- **SEC-01 stored DOM XSS is fixed and now browser-verified.** `src/js/checkin.js` builds the event name with `replaceChildren()` and `textContent`; the generated bundles and Python mirror were rebuilt. The new Playwright regression injects an `<img onerror>` payload through `invitation.document.fields.names` and passes with no script execution or unsafe element.
- **The gitleaks configuration is fixed.** `.gitleaks.toml` now extends the default ruleset. A synthetic `script_key` canary was detected by `generic-api-key`; the tracked pre-commit hook uses that config.
- **A real WSGI/header bug was found and fixed.** The waitress adapter de-duplicated response headers by name, dropping the second `Set-Cookie` (the CSRF cookie). Login therefore delivered the session cookie but not the double-submit cookie under production-style waitress. The adapter now preserves duplicate `Set-Cookie` headers; both cookies are verified on secure and non-secure origins.
- **HSTS is consistent.** HSTS is emitted only when `EINVITE_COOKIE_SECURE=1`; non-secure mode sends none. Secure-mode cookies carry `HttpOnly`, `SameSite=Lax`, and `Secure`.
- **Secret scans:** 45 gitleaks hits and 28 Trufflehog hits are fully triaged. No live secret was confirmed. The 39 Canva `script_key` hits are captured evidence and remain **NEEDS_HUMAN_ACTION** (8 unique values, 68 characters each). The suspected 25-character Postgres hit is absent; the current Postgres values are 24, 36, 42, 55, 57, and 60 characters and are placeholders/test data.
- **SAST/DAST:** Bandit 79 findings (0 HIGH, 33 MEDIUM, 46 LOW) triaged to 66 false positives and 13 accepted risks. Targeted Semgrep on the changed check-in files is clean. The full-tree Python Semgrep run was stopped after failing to complete; this is recorded as a limitation, not a pass. Scoped ZAP and the manual DAST probes pass the security controls; a full authenticated active scan remains outstanding.
- **Dependencies:** `pip-audit` and `npm audit` report zero vulnerabilities.
- **No new HIGH/CRITICAL issue is known from this remediation pass.**

## Findings and final status

| ID | Finding | Final status | Evidence / note |
|---|---|---|---|
| SEC-01 | Stored DOM XSS via `invitation.document.fields.names` in `src/js/checkin.js` | **FIXED** | `_eventName()` uses `replaceChildren()` + `textContent`; generated bundles/mirror rebuilt; targeted Semgrep 0; Playwright check-in regression passed. |
| SEC-04 | `.gitleaks.toml` had no default rules, so the hook scanned nothing | **FIXED** | `[extend] useDefault = true`; synthetic canary detected by `generic-api-key`; `.githooks/pre-commit` uses the config. |
| New | WSGI adapter dropped duplicate `Set-Cookie`; CSRF cookie missing | **FIXED** | `src/python/server.py` preserves duplicate `Set-Cookie`; both cookies observed on :4310 and :4311. |
| HSTS | WSGI emitted HSTS unconditionally while handler gated on `COOKIE_SECURE` | **FIXED** | HSTS only on secure origin; `reports/headers-final-2026-11-07.*.txt`. |
| Secrets | 39 Canva `script_key` hits in `tools/evidence/rea-canva-bundle.json` | **NEEDS_HUMAN_ACTION** | 8 unique 68-character values; determine whether captured from live Canva integrations; rotate/redact if live. |
| Secrets | Remaining 6 gitleaks hits | **VERIFIED_FALSE_POSITIVE** | 2 feature flags, 1 placeholder, 3 test fixtures; see `reports/secret-triage-2026-11-07.json`. |
| Secrets | 28 Trufflehog hits | **VERIFIED_FALSE_POSITIVE** | 0 verified; 11 placeholder, 12 documentation example, 5 test fixture. No 25-character Postgres value exists. |
| Bandit | 79 findings (0 HIGH, 33 MEDIUM, 46 LOW) | **TRIAGED** | 66 false positives, 13 risk-accepted; `reports/bandit-triage-2026-11-07.json`. B608 is allowlisted/parameterized SQL; B603 is list-argument subprocess; B310 is operator-config URL use. |
| ESLint | 2,402 warnings, 0 errors | **TRIAGED_WARNINGS** | Broad `detect-object-injection` noise and regex/timing warnings; targeted changed files: 0 errors, 3 warnings. |
| Semgrep JS | album renderer, plugin-host wildcard postMessage | **VERIFIED_FALSE_POSITIVE / RISK_ACCEPTED** | Album interpolations use `esc()`; wildcard postMessage is required for an opaque-origin sandboxed `srcdoc` iframe and carries only the plugin manifest/permissions. |
| Semgrep Python | Generated-bundle duplicate of the fixed check-in sink | **FIXED / TARGETED_CLEAN** | `reports/semgrep-checkin-after.json` has 0 results after rebuild. |
| Semgrep Python full tree | Post-fix full-tree run | **BLOCKED_WITH_REASON** | The run scanned 55 Python files with 151 rules but did not complete within the audit window; log retained at `.tools/security-audit/semgrep-python-full-after.log`. Targeted changed-file scan is clean. |
| ZAP | Prior active scan stalled at 37% | **REPLACED / LIMITATION** | Scoped ZAP quick scan completed on `/api/health` (exit 0); 0 application alerts, 2 environment findings (HTTP-only local target, UA fuzzer). Manual DAST probes cover auth/CORS/CSRF/redirect/cookies. Full authenticated active scan remains outstanding. |
| CSP | `style-src 'unsafe-inline'`, broad `img-src https:`, absent COEP | **RISK_ACCEPTED_WITH_REQUIREMENTS** | Inline styles and external invitation media are functional requirements; no `unsafe-inline`/`unsafe-eval` in `script-src`; COOP/CORP present. Owner sign-off and expiry 2027-05-07. |
| Browser | No browser-level check-in execution test previously | **FIXED** | New `e2e/specs/13-security.spec.ts` test passed 1/1. |
| Plugin permissions | Wildcard/prefix/suffix/regex matcher behavior untested | **VERIFIED_FALSE_POSITIVE / TESTED** | `tests/plugin_permission_regex_test.py`: 9/9 cases passed; wildcard is colon-boundary anchored. |
| Dependencies | Python/JS dependency audit | **CLEAN** | `pip-audit`: 22 packages, 0 vulns; `npm audit`: 0 vulnerabilities. |
| Headers | HSTS, XFO, nosniff, Referrer-Policy, Permissions-Policy, COOP, CORP | **PASS** | `reports/headers-final-2026-11-07.secure.txt`; CSP has no script `unsafe-inline`/`unsafe-eval`. |

## DAST results

All probes are in `reports/dast-manual-probes-2026-11-07.json`; no secret values are stored there.

| Probe | Result |
|---|---|
| `GET /api/invitations` unauthenticated | 401 Authentication required |
| `POST /api/invitations` with `Origin: https://evil.example` | 403 `csrf_rejected` |
| `GET /api/health` with evil Origin | 200; no `Access-Control-Allow-Origin` |
| `OPTIONS /api/invitations` cross-origin | 501; no CORS allow header |
| `GET /?next=https://evil.example/steal` | 200; no `Location` (no open redirect) |
| Auth cookie flags, non-secure :4310 | session `HttpOnly; SameSite=Lax`; CSRF `SameSite=Lax`; no Secure |
| Auth cookie flags, secure :4311 | both cookies add `Secure`; HSTS present |
| Authenticated same-origin POST without CSRF header | 403 `csrf_required` |
| Authenticated same-origin POST with CSRF header | 201 Created |
| HSTS, non-secure :4310 | absent |
| HSTS, secure :4311 | `max-age=31536000; includeSubDomains` |

ZAP 2.17.0 completed with `ZAP_EXIT:0`; `reports/zap-active-health.json` contains two findings, both environmental: “HTTP Only Site” for the local HTTP target and “User Agent Fuzzer.” The full authenticated active scan was not completed and is not represented as a pass.

## Tests and build verification

| Check | Result |
|---|---|
| `python3 build.py all --check` | **PASS** — editor bundles, route bundles, page assets, 730-file mirror all up to date |
| `python3 -m py_compile src/python/server.py` | **PASS** |
| `pytest tests/build_integrity_test.py tests/health_version_disclosure_test.py` | **2 passed** |
| `tests/plugin_permission_regex_test.py` | **PASS** — 9/9 matcher cases |
| Playwright check-in XSS regression | **1 passed** (chromium) |
| Targeted Semgrep check-in scan | **0 results** (`reports/semgrep-checkin-after.json`) |
| ESLint changed files (local ESLint 9.39.5) | **0 errors, 3 warnings** (`reports/eslint-remediation-changed.json`) |
| gitleaks synthetic canary | **DETECTED** — `generic-api-key`, exit 1 (`reports/gitleaks-canary-2026-11-07.json`) |
| pip-audit | **0 vulnerabilities** |
| npm audit | **0 vulnerabilities** |

## Human-only actions, in urgency order

1. **Canva script_key ownership verification (urgent).** Inspect the 39 captured hits in `tools/evidence/rea-canva-bundle.json` (8 unique 68-character values). Determine whether they are live Canva integration keys. If any are live, rotate them in Canva and then redact the evidence file after owner approval. If inert, mark the 8 values as `CAPTURED_EVIDENCE / VERIFIED_INERT` in `reports/secret-triage-2026-11-07.json`. Do not rewrite history before this decision.
2. **CSP sign-off.** Approve or schedule removal of `style-src 'unsafe-inline'` and narrowing of `img-src https:`; approve or reject COEP. Until then the accepted-risk expiry is **2027-05-07**.
3. **Full authenticated ZAP active scan.** Run against an isolated fixture origin with an active-scan policy limited to safe endpoints; do not run destructive traffic against production. Preserve the report as new evidence.
4. **Complete the full-tree Semgrep Python run** in CI or a machine with sufficient time. The targeted changed-file scan is clean; the full run remains a limitation.
5. **Production verification.** Confirm `EINVITE_COOKIE_SECURE=1`, trusted-proxy handling, HSTS at the edge, and both cookies arriving at the browser after the WSGI fix.
6. **ESLint maintenance.** The repository-pinned `.tools/eslint-env` uses ESLint 9.39.5; a global `npx` ESLint 10 run is incompatible with the installed `eslint-plugin-security`. Pin the CI invocation to the local toolchain and keep the 3 targeted warnings documented.

## Evidence files created or refreshed

- `reports/security-rescan.json` — updated scanner ledger (prior copy preserved as `reports/security-rescan-2026-11-07.prior.json`)
- `reports/secret-triage-2026-11-07.json`
- `reports/bandit-remediation.json`, `reports/bandit-triage-2026-11-07.json`
- `reports/semgrep-checkin-after.json`, `reports/semgrep-js.json`, `reports/semgrep-python.json`
- `reports/semgrep-python-full-after.json` (if the run produced one; otherwise the retained log is the evidence)
- `reports/eslint-security.json`, `reports/eslint-remediation-changed.json`
- `reports/dast-manual-probes-2026-11-07.json`
- `reports/zap-active-health.json`
- `reports/headers-final-2026-11-07.secure.txt`, `reports/headers-final-2026-11-07.nonsecure.txt`
- `reports/gitleaks-canary-2026-11-07.json`
- `reports/pip-audit-final-2026-11-07.json`, `reports/pip-audit-final.stderr`
- `reports/npm-audit-final-2026-11-07.json`, `reports/npm-audit-final.stderr`
- `reports/human-action-packet-2026-11-07.md`

## Working-tree summary

Intentional security edits:

- `.gitleaks.toml` — restore default ruleset.
- `.githooks/pre-commit`, `scripts/install-git-hooks.sh` — tracked pre-commit secret scan.
- `src/js/checkin.js`, `src/js/bundle-checkin.js`, `src/python/bundle-checkin.js` — SEC-01 fix and generated mirrors.
- `docs/page-assets.json`, `src/python/build/page-assets.json`, `src/python/page-assets.json` — build-generated manifest updates from the check-in fix.
- `src/python/server.py` — secure HSTS gating and WSGI duplicate `Set-Cookie` preservation.
- `e2e/specs/13-security.spec.ts`, `e2e/support/global-setup.ts` — browser regression and CSRF seed fix (test harness).
- `tests/plugin_permission_regex_test.py` — permission matcher regression.
- New evidence under `reports/` and this document.

Unrelated pre-existing modifications (including `assets/template-pack/*`, template-pack catalogs, CSS/JS generated files, and documentation) were left untouched. They remain in the working tree and are not part of this remediation.

## Residual risk

- Canva `script_key` values are unverified and may be live. This is the highest residual secret risk until the owner checks them.
- CSP inline styles and broad HTTPS image sources remain accepted risks; COEP is absent.
- Full-tree Python Semgrep and a full authenticated ZAP active scan are incomplete.
- The lint evidence relies on the repository-local ESLint 9 toolchain because the global ESLint 10 toolchain is incompatible with the installed security plugin.
- No production deployment or production runtime verification was performed.

**Recommended next review:** after Canva owner verification and before the next production release; re-run all scanners and the browser regression at that time.
