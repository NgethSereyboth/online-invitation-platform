# Security Audit — eInvite / OKID — 2026-11-07

**Repository:** `einvite-platform`
**HEAD:** `3dace26` (branch `main`)
**Audit target:** `http://127.0.0.1:4311` — isolated local instance, data directory `.tools/security-audit/data`
**Scope:** Python stdlib/Waitress backend, static frontend, plugin sandbox, dependency manifests, HTTP configuration, full Git history
**Release handling:** local-only audit; no push, tag, PR or merge (project decision **OD-3**). Nothing was committed.
**Working tree:** this audit changed `.gitleaks.toml`, `src/js/checkin.js`, and the generated check-in bundle/mirror/page-assets outputs. Unrelated pre-existing modifications (notably `assets/template-pack/*`, with mtimes from 2026-11-06) were present before the audit and were left untouched.

---

## 1. Executive summary

- **Confirmed real findings:** 1 — a stored DOM XSS in the host check-in page (`src/js/checkin.js`, mirrored into `src/python/bundle-checkin.js:389`), severity **S2**, fixed and verified with the originating Semgrep ruleset; plus 1 tooling finding — the committed gitleaks config disabled all secret-detection rules, **S2**, fixed and verified with a canary.
- **Triaged:** 98 Bandit hits (0 HIGH), 2,402 ESLint warnings (0 errors), 45 gitleaks historical hits, 28 unverified Trufflehog hits, 3 JavaScript Semgrep warnings, 16 DrHeader route hits, 2 Vamp MEDIUM header findings, and 4 ZAP reconnaissance alerts. None is a confirmed HIGH/CRITICAL vulnerability; the two real items above are closed.
- **Remaining / blocked:** 3 accepted-risk header items (`style-src 'unsafe-inline'`, absent COEP, broad `img-src https:`), 1 secret-scan item needing owner confirmation (Canva `script_key` evidence), 1 partial ZAP active scan (stopped at 37%, no report), and no browser-level execution test of the fixed check-in page.

The audit found **no dependency CVEs** in production or test requirements, and **no verified live secret**.

---

## 2. Tool inventory

| Tool | Version | Status | Notes |
|---|---|---|---|
| Bandit | 1.9.4 | INSTALLED | `.tools/sec-venv/bin/bandit` |
| Semgrep | 1.184.0 | INSTALLED | `.tools/sec-venv/bin/semgrep`; `p/python`, `p/owasp-top-ten`, `p/javascript` |
| pip-audit | 2.10.1 | INSTALLED | `.tools/sec-venv/bin/pip-audit` |
| gitleaks | 8.30.1 | INSTALLED | `.tools/bin/gitleaks` |
| Trufflehog | 3.99.8 | INSTALLED | `.tools/bin/trufflehog` |
| OSV-Scanner | 2.7.0 | INSTALLED | `.tools/bin/osv-scanner` |
| Nuclei | 3.11.1 | INSTALLED | `.tools/bin/nuclei` |
| OWASP ZAP | 2.17.0 | INSTALLED | Native `.tools/zap/zap.sh`; the core tarball does not include `zap-baseline.py`/`zap-full-scan.py` |
| Eclipse Temurin JRE | 21.0.13 | INSTALLED | `.tools/jre`, because Docker and a host Java runtime were absent |
| vamp-http-audit | 1.7.0 | INSTALLED | `.tools/sec-venv/bin/vamp-http-audit`; JSON/TXT output valid, HTML export crashed inside the tool |
| DrHeader | 3.0.4 | INSTALLED | `.tools/sec-venv/bin/drheader`, OWASP ASVS preset |
| ESLint | 9.39.5 | PRESENT | `.tools/eslint-env`; full `src/` run produced `reports/eslint-security.json` |
| eslint-plugin-security | 3.x | PRESENT | `.tools/eslint-env`; version as resolved by the local environment |
| Node.js / npm | 22.23.4 | PRESENT | Used for ESLint, `npm audit`, syntax checks |
| Python | 3.12.3 | PRESENT | `.venv` |
| pytest | 7.4.4 / 9.1.1 environments | PRESENT | Focused tests run with `.venv/bin/python -m pytest` |
| Docker / Podman | — | **INSTALL-FAILED** | Neither runtime is installed; native ZAP + Temurin JRE used instead. No privileged installation attempted. |

**DAST tooling caveat:** the ZAP 2.17 core tarball lacks the Python scan wrappers. ZAP was driven with `zap.sh -cmd -zapit` for quick reconnaissance and `zap.sh -cmd -quickurl` for the attempted active scan. The `-quickout` report file was not produced by the reconnaissance run; the raw `.tools/security-audit/zap-recon.log` is the evidence for those alerts.

---

## 3. Findings table

| ID | Layer | Severity | Location / rule | Triage | Evidence |
|---|---|---|---|---|---|
| SEC-01 | SAST (Semgrep) | **S2** | `src/js/checkin.js:13` (mirrored to `src/python/bundle-checkin.js:389`), `javascript.browser.security.raw-html-concat.raw-html-concat` | **REAL — FIXED / VERIFIED** | `reports/semgrep-python.json`; post-fix `reports/semgrep-checkin-after.json` |
| SEC-02 | SAST (Semgrep) | Info | `src/js/album.js:156`, `src/python/album.js:156`, `typescript.react.security.audit.react-unsanitized-method` | **FALSE-POSITIVE** — every dynamic value passes through `esc()`; copies are byte-identical (`cmp` 0) | `reports/semgrep-js.json`, `reports/semgrep-python.json` |
| SEC-03 | SAST (Semgrep) | Info | `src/js/plugin_sandbox_host.js:196`, `src/js/plugins/sandbox-host.js:196`, `src/python/plugin_sandbox_host.js:196`, `javascript.browser.security.wildcard-postmessage-configuration` | **FALSE-POSITIVE / hardening follow-up** — iframe is `sandbox="allow-scripts"` without `allow-same-origin`; `srcdoc` has an opaque origin, so `'*'` is required; init payload contains only the plugin's own manifest/permissions | `reports/semgrep-js.json`, `reports/semgrep-python.json` |
| SEC-04 | Secret scan tooling | **S2** | `.gitleaks.toml` had only `[allowlist]`, no `[extend]`; `gitleaks --config .gitleaks.toml` therefore ran with zero rules | **REAL — FIXED / VERIFIED** with a synthetic AWS canary (0 detections before, 1 after) | `reports/gitleaks.json`, `reports/gitleaks-fixed.json`, `reports/gitleaks-final.json` |
| SEC-05 | Secret scan (gitleaks) | **NEEDS-VERIFICATION** (potential S1) | `tools/evidence/rea-canva-bundle.json`, 39 `generic-api-key` hits, commit `5bb5ac7331de`, line 1 | **NEEDS-VERIFICATION** — 8 unique 68-character `script_key` values captured from a Canva page; no live credential confirmed. Owner must confirm whether these are public script identifiers; if not, rotate and purge the evidence file/history | `reports/gitleaks-final.json` |
| SEC-06 | Secret scan (gitleaks) | Info | 6 historical hits: `app.js:2` (`295db02c77b0`), `docs/reviews/deploy-03-render.md:213` (`18133f61a0d6`), `docs/reviews/v54-commit.md:167` (`dd1b97a8e75c`), `tests.bak/v0_52_final_ux_refinement_browser_test.py:98` and `tests.bak/v53_1_ai_project_operator_backend_test.py:135` (`019e521a856d`), `tools/evidence/instrument-repair-flag-branch.txt:158` (`fd3ffa0d93a9`) | **FALSE-POSITIVE** — feature flag, placeholder/test fixture, localStorage key constants, docs test password | `reports/gitleaks-final.json` |
| SEC-07 | Secret scan (Trufflehog) | Info | 28 unverified hits, 27 Postgres detectors, 1 PhraseAccessToken; 0 verified | **FALSE-POSITIVE / UNVERIFIED** — sampled contexts are placeholders and test fixtures; no live credential | `reports/trufflehog.json` |
| SEC-08 | Headers (DrHeader) | MEDIUM | `Content-Security-Policy: style-src 'self' 'unsafe-inline'` on 16/16 routes | **WONTFIX — accepted risk**, expiry 2027-05-07; migration already tracked as ASVS 3.1.7 / P3-J; owner sign-off required | `reports/drheader/*.json` |
| SEC-09 | Headers (Vamp) | MEDIUM | `Cross-Origin-Embedder-Policy` absent; `style-src 'unsafe-inline'` | **WONTFIX — accepted risk**, expiry 2027-05-07; adding COEP `require-corp` without a CORP migration would break cross-origin invitation media; no SharedArrayBuffer use | `reports/vamp-headers.json`, `reports/vamp-headers.txt` |
| SEC-10 | DAST (ZAP recon) | MEDIUM | CSP Wildcard Directive: `img-src 'self' data: blob: https:` | **WONTFIX — accepted risk**, expiry 2027-05-07; `https:` is intentionally broad for user-supplied invitation images; no script execution, but external-image tracking remains possible | `.tools/security-audit/zap-recon.log` |
| SEC-11 | DAST (ZAP recon) | Info | CSP Report-Only header found | **FALSE-POSITIVE** — intentional monitoring mirror with `report-uri /api/csp-report` | `.tools/security-audit/zap-recon.log` |
| SEC-12 | DAST (ZAP recon) | Info | Information Disclosure — Suspicious Comments: `"from"` | **FALSE-POSITIVE** — ordinary source text; no secret or version disclosure | `.tools/security-audit/zap-recon.log` |
| SEC-13 | SAST (Bandit) | 39 MEDIUM + 59 LOW, 0 HIGH | 98 hits; rule counts below | **FALSE-POSITIVE / accepted non-security use** | `reports/bandit.json`, `reports/bandit.txt` |
| SEC-14 | SAST (ESLint) | 2,402 warnings, 0 errors | 224 files; class counts below | **FALSE-POSITIVE / broad-rule noise**; no exploitable sink confirmed | `reports/eslint-security.json` |
| SEC-15 | SCA | None | pip-audit production/test, npm audit, OSV production/test | **CLEAN** — 0 vulnerabilities | `reports/pip-audit-2026-11-07.json`, `reports/pip-audit-test-2026-11-07.json`, `reports/npm-audit-2026-11-07.json`, `reports/osv.json`, `reports/osv-test.json` |
| SEC-16 | DAST (Nuclei) | None | `http://127.0.0.1:4311`, critical/high/medium templates | **CLEAN** — 0 findings, exit 0 | `reports/nuclei.json` |
| SEC-17 | DAST (ZAP active) | Unknown | Same isolated target | **PARTIAL** — stopped at 37%, no report; not a clean result | `.tools/security-audit/zap-quick.log` |

### Bandit rule breakdown

| Rule | Count | Triage |
|---|---:|---|
| B110 (`try/except/pass`) | 31 | FALSE-POSITIVE — intentional best-effort cleanup/telemetry paths; no security decision is swallowed |
| B608 (SQL string construction) | 26 | FALSE-POSITIVE — parameterized statements or fixed allowlists (`safe_set_clause`, `_METRIC_TABLES`, fixed table/column tuples) |
| B603 (subprocess) | 16 | FALSE-POSITIVE — argument arrays, no `shell=True`; callers use fixed commands |
| B310 (`urllib` URL open) | 11 | FALSE-POSITIVE — config/admin-controlled endpoints or guarded by `validate_destination` (private/loopback/link-local/reserved blocked) |
| B404 (subprocess import) | 5 | FALSE-POSITIVE — import alone is not a vulnerability |
| B112 (`try/except/continue`) | 3 | FALSE-POSITIVE — intentional per-item failure isolation |
| B104 (bind all interfaces) | 2 | FALSE-POSITIVE — intentional container/deployment bind; network access is controlled outside the process |
| B105/B107 (hardcoded password) | 1 each | FALSE-POSITIVE — test fixtures / documentation examples |
| B311 (non-cryptographic random) | 1 | FALSE-POSITIVE — not used for tokens, keys or security decisions |
| B607 (partial executable path) | 1 | FALSE-POSITIVE — resolved by the deployment environment; no user-controlled executable name |

### ESLint rule breakdown

| Rule | Count | Triage |
|---|---:|---|
| `security/detect-object-injection` | 2,349 | FALSE-POSITIVE — the rule fires on every bracket access, including fixed lookup maps and internally generated keys. Sampled instances (`account-security.js:6`, `adaptive-gpu-quality.js:6`, `adaptive-templates.js:10`) are internal maps; no user-controlled key reaches a prototype or sensitive store |
| `security/detect-unsafe-regex` | 27 | FALSE-POSITIVE — static, anchored regexes over bounded fields (colors, dimensions, clipboard transforms, typography values). No catastrophic-backtracking input path was demonstrated |
| `security/detect-possible-timing-attacks` | 19 | FALSE-POSITIVE — comparisons of non-secret UI state, tokens used for render ordering, and public values; no password/API-key comparison |
| `security/detect-non-literal-regexp` | 6 | FALSE-POSITIVE — 2 in the plugin host (approved manifest grants), 3 in generated bundles, 1 in `core/khmer-format.js` (internal locale/format pattern); no untrusted remote input |
| Unused `eslint-disable` directive | 1 | Housekeeping only — `src/js/editor/editor-core.js:245`; not a security finding |

No scanner rule was deleted, no blanket suppression was added, and no test was removed or weakened. False positives remain visible in the reports; if CI requires a zero-warning gate, add targeted, justified annotations rather than a repository-wide suppression.

---

## 4. Fix log

### SEC-01 — stored DOM XSS in the host check-in page

**Finding (raw):** Semgrep `javascript.browser.security.raw-html-concat.raw-html-concat` at `src/python/bundle-checkin.js:389`:

> “User controlled data in a HTML string may result in XSS”

The generated line mirrored `src/js/checkin.js:13`, which did:

```js
$('#eventName').innerHTML =
  '<span class="i18n i18n-en">' + invitation.document.fields.names + '</span>' +
  '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + invitation.document.fields.names + '</span>';
```

The same pattern appeared in the offline/demo branch. `invitation.document.fields.names` is invitation data controlled by the invitation owner, so a crafted name could execute script in the authenticated host's check-in page.

**Fix:** added `_eventName(name)` in `src/js/checkin.js`. It calls `host.replaceChildren()` and appends two `<span>` elements whose `textContent` is the invitation name. No HTML parsing is involved. Both branches now call `_eventName(...)`; the unescaped `innerHTML` concatenation is gone.

**Rebuild:** `python3 build.py all` regenerated `src/js/bundle-checkin.js`, `src/python/bundle-checkin.js`, the `src/python` mirror, and page-assets. `python3 build.py all --check` printed:

```
MIRROR_CHECK_PASSED (up_to_date=730)
BUILD_OK editor bundles manifests mirror (check)
```

**Tests and syntax:**

- `node --check src/js/checkin.js` → 0
- `node --check src/js/bundle-checkin.js` → 0
- `node --check src/python/bundle-checkin.js` → 0
- `pytest -q tests/served_asset_resolution_test.py tests/v14_static_server_test.py` → **32 passed in 51.07s**
- ESLint on the changed file → **0 errors**, 1 pre-existing `detect-object-injection` warning on the existing `esc()` character map.

**Re-scan (same ruleset, changed files):**

```
.tools/sec-venv/bin/semgrep scan --config p/python --config p/owasp-top-ten \
  --json --output reports/semgrep-checkin-after.json --quiet \
  src/js/checkin.js src/js/bundle-checkin.js src/python/bundle-checkin.js
```

Result: `semgrep-checkin-results 0`. The originating raw-html-concat finding is gone from the source and both generated copies.

### SEC-04 — gitleaks config disabled every rule

**Finding:** `.gitleaks.toml` contained only an `[allowlist]`. A gitleaks config without `[extend] useDefault = true` replaces the built-in ruleset, so the pre-commit hook (`gitleaks --config .gitleaks.toml`) scanned with zero rules. The full-history run returned **0** findings for that reason, not because the history was clean.

**Fix:** added:

```toml
[extend]
useDefault = true
```

plus a comment explaining why the extension is load-bearing.

**Proof:** a synthetic AWS access-key canary was scanned with the project config. Before the fix it produced **0** hits; after the fix it produced **1** hit. The same full-history scan then reported **45** findings (all triaged in this report), and 417 commits / 137.8 MB were scanned. This is a stricter scan, not a regression.

---

## 5. Blocked fixes

| Finding | Why it is blocked | Human action required |
|---|---|---|
| SEC-08 / SEC-09 / SEC-10 — CSP `style-src 'unsafe-inline'`, COEP absent, broad `img-src https:` | Removing `'unsafe-inline'` needs a nonce/hash migration across server-rendered inline styles; COEP `require-corp` needs CORP on every cross-origin image/video/plugin resource; narrowing `img-src` would break user-supplied external invitation images. These are accepted-risk decisions with a 2027-05-07 expiry, not code-only fixes | Owner sign-off on the accepted risk or a scheduled UI/CSP migration; track under ASVS 3.1.7 / P3-J |
| SEC-05 — Canva `script_key` values | 39 gitleaks hits in `tools/evidence/rea-canva-bundle.json` are 8 unique 68-character values. No live credential was verified. Rewriting history is a force-push decision and is prohibited without explicit instruction | Confirm with Canva whether `script_key` is a public page identifier. If it is a credential, rotate it and purge the evidence file from history; do not force-push until the owner authorizes it |
| SEC-17 — ZAP active scan | The quick active scan reached 37% after more than 20 minutes, produced no report, and was stopped. Running it against anything other than the isolated local instance is prohibited | Run a context-limited active scan (selected auth/API routes) with a longer budget, or accept the partial DAST limitation for this release |
| Full-tree Semgrep Python re-scan | The targeted re-scan of the changed check-in files is clean, but a full-tree post-fix run was not repeated because the full `p/python + p/owasp-top-ten` scan is slow on this repository | Run the full ruleset in CI or a dedicated scan window; expected remaining results are the two documented false positives (`album.js`, `plugin_sandbox_host.js`) |
| SEC-01 browser verification | The fix is proven at the source, generated-bundle and Semgrep-rule levels, but no real browser session was driven through the malicious-name path | Manually open the host check-in page for an invitation whose `names` field contains HTML, confirm it renders as text and no script executes; add a Playwright regression if the browser harness is available |
| Bandit / ESLint false positives | Suppressing them would weaken or hide the scan output. They are recorded as false positives with justifications; no blanket `# nosec` or rule deletion was added | If CI requires zero findings, add targeted annotations with a reason and a review date, and keep the raw reports |

---

## 6. Secrets found

**No verified live secret was found.** No secret value is printed in full below; gitleaks was run with `--redact`.

| File / line | Commit | Detector | Redacted value | Triage / rotation |
|---|---|---|---|---|
| `tools/evidence/rea-canva-bundle.json:1` (39 hits) | `5bb5ac7331de` | `generic-api-key` | 8 unique 68-character `script_key` values; prefix/suffix withheld | **NEEDS-VERIFICATION** — captured Canva page evidence, adjacent to `"url": "https://www.canva.com/"`; no API-secret field or verified use found. Owner must confirm whether these are public script identifiers. If live, rotate in Canva and purge the evidence file from history; force-push only with explicit instruction |
| `docs/reviews/deploy-03-render.md:213` | `18133f61a0d6` | `generic-api-key` | 15-character value, `te…23` | **FALSE-POSITIVE** — deploy example/test placeholder. If this value was ever used as a real `EINVITE_SECRET_KEY`, rotate it |
| `docs/reviews/v54-commit.md:167` | `dd1b97a8e75c` | `generic-api-key` | 19-character value, `St…23` | **FALSE-POSITIVE** — documented test password (`tests/v0_52…` context), not a live credential |
| `tests.bak/v0_52_final_ux_refinement_browser_test.py:98` | `019e521a856d` | `generic-api-key` | `[redacted]` | **FALSE-POSITIVE** — throwaway test fixture |
| `tests.bak/v53_1_ai_project_operator_backend_test.py:135` | `019e521a856d` | `generic-api-key` | `[redacted]` | **FALSE-POSITIVE** — throwaway test fixture |
| `app.js:2` | `295db02c77b0` | `generic-api-key` | `[redacted]` | **FALSE-POSITIVE** — `publishKey`/localStorage key constant, not a credential |
| `tools/evidence/instrument-repair-flag-branch.txt:158` | `fd3ffa0d93a9` | `generic-api-key` | `"key":"ai_agent_enabled"` | **FALSE-POSITIVE** — feature flag |
| Trufflehog: 28 unverified hits (27 Postgres, 1 PhraseAccessToken) | n/a | Postgres / PhraseAccessToken | `[redacted]` | **FALSE-POSITIVE / UNVERIFIED** — placeholders and test fixtures; 0 verified |

**Rotation instruction:** the only item that could require rotation is the Canva `script_key` set. Rotate through the Canva account/admin that issued those keys, then remove the captured evidence from the working tree and, if the owner decides it is sensitive, from history. The historical test/doc values should be checked once against the production environment; if any was ever reused outside tests, rotate `EINVITE_SECRET_KEY` and any matching database credential.

---

## 7. Dependency upgrades

**No dependency upgrades were made and none are required by this audit.**

| Ecosystem | Command | Result |
|---|---|---|
| Python production | `pip-audit -r requirements.txt` | 0 vulnerabilities — `reports/pip-audit-2026-11-07.json` |
| Python test | `pip-audit -r` test requirements | 0 vulnerabilities — `reports/pip-audit-test-2026-11-07.json` |
| npm | `npm audit --audit-level=moderate --json` | 0 info/low/moderate/high/critical — `reports/npm-audit-2026-11-07.json` |
| OSV production | `osv-scanner scan source -r .` | 0 results — `reports/osv.json` |
| OSV test | test requirements | 0 results — `reports/osv-test.json` |

Direct/transitive classification and version jumps are not applicable: there is no CVE to upgrade for. The Python backend is standard-library/Waitress based; the Node tree contains only build/test tooling.

---

## 8. DAST scope

**Exact target:** `http://127.0.0.1:4311`
**Instance:** isolated local server, `EINVITE_DATA_DIR=$PWD/.tools/security-audit/data`, started with `EINVITE_ALLOW_NO_SCANNER=1`, `EINVITE_DEV_AUTH_TOKENS=1`, `EINVITE_REQUIRE_EMAIL_VERIFICATION=0`, `PYTHONPATH=$PWD/src/python:$PWD`. This was a disposable local database, not staging or production.

| Scan | Type | Timestamp / evidence | Result |
|---|---|---|---|
| ZAP quick reconnaissance | `zap.sh -cmd -zapit` | 2026-11-07 13:20 +07:00; `.tools/security-audit/zap-recon.log` | 4 alerts: 2 MEDIUM CSP (wildcard `img-src https:`, `style-src 'unsafe-inline'`), 2 informational (CSP Report-Only, suspicious comment “from”) |
| ZAP quick active | `zap.sh -cmd -quickurl` | Attempted 2026-11-07; `.tools/security-audit/zap-quick.log` | **PARTIAL** — reached 37% after more than 20 minutes, no report produced, stopped. Not a clean result |
| Nuclei | critical/high/medium templates | 2026-11-07; `reports/nuclei.json` | 0 findings, exit 0; report file 0 bytes |

**ZAP reconnaissance alert detail (raw log):**

```
Number of alerts: 4
	Medium: CSP: Wildcard Directive : "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src..."
	Medium: CSP: style-src unsafe-inline : "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src..."
	Informational: Content Security Policy (CSP) Report-Only Header Found : ""
	Informational: Information Disclosure - Suspicious Comments : "from"
```

**Manual HTTP checks (isolated instance):**

- Signed-out `GET /api/invitations` → **401**.
- Cross-origin `POST` with `Origin: https://evil.example` → **403** `csrf_rejected`.
- `OPTIONS` → **501**; no permissive preflight response.
- Registration → **201**, `Set-Cookie` session is `HttpOnly; SameSite=Lax`; CSRF cookie is intentionally readable for the double-submit check.
- `EINVITE_COOKIE_SECURE` is required by production preflight (`src/python/core/preflight.py:136`) and appends `Secure` to the session/CSRF cookies when enabled (`src/python/server.py:5990`). It is intentionally off on the local HTTP instance, so localhost cookies lack `Secure`.
- No open-redirect parameter was found by Vamp’s 16-parameter probe (`open_redirect_params: []`); CORS origin reflection, credential reflection and null-origin acceptance were all false.
- Headers on the live root: CSP (no `unsafe-inline`/`unsafe-eval` in `script-src`; `object-src 'none'`; `base-uri 'self'`; `frame-ancestors 'self'`; `form-action 'self'`), HSTS `max-age=31536000; includeSubDomains`, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, COOP `same-origin`, CORP `same-site`, and `Server: EInvite` with no version.

---

## 9. Human-only gaps

Scanners cannot prove the following; a clean result must not be read as coverage of them.

1. **Business-logic authorisation flaws.** No scanner finds a missing permission check on a valid endpoint. The audit confirmed signed-out 401s, CSRF 403s and tenant-isolation tests, but did not exhaustively enumerate every object-level authorization path (IDOR, cross-tenant reads, role escalation on every admin action).
2. **Chained exploits.** A medium CSP weakness plus a medium injection point can combine into a critical chain. Each scanner checks one pattern at a time; the accepted header risks and the escaped-sink false positives should be re-evaluated together if new HTML sinks are added.
3. **Client-side runtime behaviour.** The check-in fix was verified statically and with Semgrep/build/tests, but no real browser was driven through a malicious invitation name. A Playwright test should load the host check-in page, inject `<img src=x onerror=...>` into `names`, and assert that it renders as text with no script execution.
4. **Cryptographic design.** Scanners flag `md5`/`sha1` patterns, but they cannot judge key management, token entropy, rotation, or the security of the plugin signing/CRL flow. The audit read the code paths but did not perform a cryptographic design review.
5. **Supply-chain compromise without a CVE.** pip-audit/OSV/npm audit know published advisories only. A compromised but not-yet-assigned package, a malicious maintainer, or a tampered build artifact would not appear in these results.
6. **Insider threat and social engineering.** Nothing here tests a malicious admin, a stolen session, a phishing flow, or a support-desk impersonation path.
7. **Header migration completeness.** The accepted `style-src 'unsafe-inline'`, absent COEP and broad `img-src https:` need an owner decision and a UI/media migration plan; the scan cannot decide the business trade-off.
8. **Canva evidence ownership.** Only the Canva account owner can confirm whether the 8 `script_key` values are public identifiers or credentials.

---

## 10. CVE response SLA

No CVE was found in this audit. If a future scan reports one, use this standard:

| Severity | Response target |
|---|---|
| Critical | Patch or mitigate within **24 hours**; block release; incident review |
| High | Patch **before the next release**; block production promotion until fixed or explicitly accepted with an expiry |
| Moderate | Patch within **14 days** |
| Low | Address in the **next maintenance window** |

Every exception must record the CVE, package, installed and fixed versions, direct/transitive status, reachability, the accepting owner, and an expiry date. A permanent suppression without a justification and a date is prohibited.

---

## Evidence index

| Path | Contents |
|---|---|
| `reports/security-rescan.json` | Machine-readable before/after ledger for every scanner |
| `reports/bandit.json`, `reports/bandit.txt` | Bandit 98 hits, 0 HIGH |
| `reports/semgrep-python.json` | Pre-fix Python/JS ruleset output (3 warnings) |
| `reports/semgrep-js.json` | JavaScript ruleset output (3 warnings) |
| `reports/semgrep-checkin-after.json` | Post-fix targeted re-scan (0 results) |
| `reports/eslint-security.json` | Full ESLint run, 0 errors / 2,402 warnings |
| `reports/eslint-checkin-after.json` | Changed-file ESLint re-scan, 0 errors / 1 warning |
| `reports/pip-audit-2026-11-07.json`, `reports/pip-audit-test-2026-11-07.json` | Python dependency audit |
| `reports/npm-audit-2026-11-07.json` | npm audit |
| `reports/osv.json`, `reports/osv-test.json` | OSV production/test |
| `reports/gitleaks.json` | Pre-fix project-config history run (0 because `.gitleaks.toml` declared no rules) |
| `reports/gitleaks-fixed.json`, `reports/gitleaks-final.json` | Full history with `[extend] useDefault = true` (45 hits) |
| `reports/trufflehog.json` | 28 unverified, 0 verified |
| `reports/drheader/*.json` | 16 route header scans |
| `reports/vamp-headers.json`, `reports/vamp-headers.txt` | Header/CORS/open-redirect audit, grade B |
| `reports/nuclei.json` | Nuclei, 0 findings |
| `.tools/security-audit/zap-recon.log` | ZAP reconnaissance raw output |
| `.tools/security-audit/zap-quick.log` | Partial active scan, stopped at 37% |
| `.tools/security-audit/semgrep-checkin-after.json` | Targeted Semgrep re-scan log |

**Working-tree note:** the audit changes are uncommitted. `.gitleaks.toml` and `src/js/checkin.js` are the intentional edits; the check-in bundles, `src/python` mirror and page-assets are build outputs. The large pre-existing `assets/template-pack/*` modifications were not created or reverted by this audit.
