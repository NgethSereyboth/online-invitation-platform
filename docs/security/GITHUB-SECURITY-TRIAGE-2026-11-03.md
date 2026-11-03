# GitHub security feedback — 2026-11-03 triage

**Repository:** `NgethSereyboth/online-invitation-platform`
**Local branch:** `main` (218 commits ahead of `origin/main` at triage time)
**Verification origin:** `http://127.0.0.1:4175` (PC-hosted, not Sites)
**Raw evidence (gitignored):** `artifacts/security/2026-11-03/`

## Captured feedback

| Source | Result |
|---|---|
| `GET /repos/.../dependabot/alerts?state=open` | **92 open alerts / 49 unique advisories** |
| `GET /repos/.../code-scanning/alerts?state=open` | **118 open CodeQL alerts** |
| `GET /repos/.../secret-scanning/alerts?state=open` | **0 alerts** |
| Security Scan run [41472118974](https://github.com/NgethSereyboth/online-invitation-platform/actions/runs/41472118974) | **failure** at `Run security scan` (2026-11-02T15:29Z) |

The failed job log is saved as `security-job-125368141539.log`. It fails in
`pip-audit`, not bandit or gitleaks:

- Pillow **12.3.0** is affected by the reported advisories; the current tree pins **13.0.0**.
- Brotli **1.2.0** is affected by `CVE-2026-111497`; the current tree pins **1.2.1**.
- Bandit: PASS (no HIGH findings).
- Gitleaks: PASS (no secrets detected).
- Trivy: skipped because the Docker build was unavailable.

The 92 Dependabot alerts are computed against GitHub's old default branch. They are
not 92 independent current-tree defects: the large Pillow block is duplicated across
`requirements.txt` and `docs/requirements-production.txt`, and the old npm/browser
chain is likewise historical.

## Current-tree action taken

| Finding | Fix | Verification |
|---|---|---|
| Workflow token over-permission (`actions/missing-workflow-permissions`) | Added `permissions: contents: read` to `security.yml` and `lighthouse.yml` | `tests/security_workflow_permissions_test.py` |
| `py/clear-text-logging-sensitive-data` in preflight | Central redaction helper used by JSON and text output | `tests/security_preflight_redaction_test.py` |
| `py/path-injection` via the malware scanner temp filename | Replaced upload-derived suffix with a fixed `.bin` temp file created by `mkstemp` | `tests/security_scanner_temp_path_test.py` |
| `js/prototype-polluting-assignment` in timeline tracks | Reject `__proto__`/`prototype`/`constructor` IDs and write via `Object.defineProperty` | `node --check`; existing motion contract |
| npm high findings (`zod` → `chromium-bidi` → `puppeteer-core`) | Upgraded dev dependency to `puppeteer-core@25.16.0`; lockfile now resolves chromium-bidi `157.0.8090-0`, zod `4.6.7` | `npm audit --package-lock-only` → **0 vulnerabilities** |
| Python runtime advisories | Current pins already at Pillow `13.0.0` and Brotli `1.2.1` | `pip-audit` on the current requirements file (run after installing the scanner) |
| HTTP response headers | Added `safe_header_value()` for CR/LF-bearing `Location` values and reused `_safe_inline_filename()` for backup downloads; media disposition remains `inline|attachment` | `tests/security_media_headers_test.py` |
| Rich-text regex cost / unsafe fallback | Replaced the mailto regex with delimiter checks and the legacy-markup regex with a bounded tag check; the no-DOM renderer fallback now strips tags with a small state machine instead of incomplete regexes | `tests/v21_0_rich_text_model_test.py`, `tests/v21_0_migration_roundtrip_test.py` |
| Generated JavaScript mirrors | Rebuilt with `python3 build.py all`; do not edit `src/python/bundle-*.js` or `src/python/build/*` by hand | `BUILD_OK`, `MIRROR_CHECK_PASSED` |

## CodeQL triage notes

- 32 of the 118 alerts are generated `src/python/bundle-*.js` mirrors of `src/js`
  sources. Fix the source and regenerate; do not edit generated mirrors.
- The remaining high-confidence code changes are the four above. The following
  reported patterns are being reviewed rather than mechanically changed:
  - `py/http-response-splitting`: server header construction is already passed through
    `safe_request_id`, `_safe_inline_filename`, or a CR/LF-stripping expression; the
    media `disposition` query parameter needs an explicit `inline|attachment` allowlist.
  - `py/path-injection`: the scanner temp path is fixed above; server media paths are
    basenamed/allowlisted before use.
  - `js/clear-text-storage-of-sensitive-data`: the dashboard's local mode intentionally
    stores an invitation draft for offline recovery. It contains user content, not
    credentials; changing that persistence is a product/privacy decision, not a
    mechanical security patch.
  - `js/xss-through-dom` and `js/incomplete-multi-character-sanitization`: many alerts
    point at static template strings or the DOM-rebuilding `cleanNode` sanitizer. Each
    location must be traced to a user-controlled sink before a change; no blanket
    `innerHTML` rewrite is safe in this editor.
- CodeQL alert counts will only fall on GitHub after the corrected commits are pushed
  and rescanned. This local pass does not claim the remote alert ledger is already clear.

## Verification — current tree (2026-11-03)

- `npm ci --ignore-scripts --no-audit`: **exit 0**; installed `puppeteer-core 25.16.0`, `chromium-bidi 157.0.8090-0`, `zod 4.6.7`.
- `npm audit --json`: **exit 0**, **0 vulnerabilities** at every severity.
- `bash scripts/security-scan.sh`: **exit 0** — bandit PASS (0 HIGH), pip-audit PASS, SBOM PASS (10 components).
  - gitleaks and Trivy were not available and were skipped; the previous GitHub Gitleaks job passed.
- `python3 build.py all`: **BUILD_OK**, `MIRROR_CHECK_PASSED`; `python3 -m compileall -q src/python tests`: exit 0.
- `node --check src/js/renderer-core.js`: exit 0; `git diff --check`: exit 0.
- PC route parity: `/`, `/templates`, `/dashboard`, and `/designer` all return 200 on `127.0.0.1:4175`; `tests/page_route_alias_test.py` compares every alias with its canonical `.html` response.
- Six-width Playwright sweep: **225/225 checks, 0 failures, 6/6 widths** after the rebuilt service restart; clean page/console/network checks. Record: `bugs/round-7/live-flows-six.json`; findings: `bugs/round-7/FINDINGS.md`.

## Remaining CodeQL disposition

The 118-alert snapshot was taken before this working tree. It cannot be used as a
current-tree count until these commits are pushed and CodeQL rescans them. The
groups below are intentionally not suppressed in code.

| Family | Count in snapshot | Disposition |
|---|---:|---|
| `js/xss-through-dom` | 58 | Mostly generated `bundle-*.js` mirrors plus static template strings; traced sinks in `renderer-core.js` use an allowlist DOM rebuild. Rebuild removes mirror drift. No untrusted HTML sink was found in the newly reviewed paths; rescan is required to shrink the hosted ledger. |
| `js/incomplete-multi-character-sanitization` / `js/bad-tag-filter` | 21 | The no-DOM fallback used incomplete tag regexes. It now uses `stripTags()`; generated mirrors were rebuilt. Remaining `src/js` hits are static markup, not user input. |
| `js/clear-text-storage-of-sensitive-data` | 7 | The editor deliberately persists a local invitation draft for offline recovery. It contains event content, not credentials; changing persistence is a product/privacy decision and is not silently rewritten here. |
| `py/bad-tag-filter` | 8 | Test-only HTML-inlining regexes. They do not ship in the server or browser bundle; they are test-fixture hygiene, not a runtime parser. |
| `py/http-response-splitting` | 6 | Header values now pass through `safe_header_value` or `_safe_inline_filename`, and the media disposition is allowlisted. |
| `py/polynomial-redos` | 5 | `rich_text_document_model.py` mailto and legacy-markup expressions are replaced. The three server locations in the snapshot no longer contain the referenced `0.`/`!` expressions at their mapped lines; this is a stale line map until rescan. |
| `py/path-injection` | 4 | The scanner temp path is fixed (`.bin`, `mkstemp`); server asset/media paths are basenamed and resolved under the intended root. |
| `js/prototype-polluting-assignment` | 3 | Fixed in `src/js/timeline.js` with reserved-id rejection and `Object.defineProperty`; mirrors rebuilt. |
| `actions/missing-workflow-permissions` | 2 | Fixed with `permissions: contents: read` in both workflows. |
| `py/clear-text-logging-sensitive-data` | 2 | Fixed at the call site with `redact_preflight_message()`; the static analyzer does not model the custom helper, so a rescan is the only way to confirm its ledger. |
| `py/incomplete-url-substring-sanitization` | 2 | Test-only assertions over literal fixture URLs, not runtime URL validation. |

## HEAD reconciliation — 2026-11-03

The source commit (`ebb96d4`, at evidence HEAD `286080e`) was re-audited against **fresh, fully paginated**
GitHub lists: **92 Dependabot alerts / 49 unique advisories**, **118 CodeQL alerts**,
**0 secret-scanning alerts**. The complete Dependabot per-advisory table (package,
affected range, committed pin, result, alert IDs) and every non-generated CodeQL
disposition are in `docs/security/HEAD-RECONCILIATION-2026-11-03.md`.

Result: **0 current vulnerable packages** — 42 Python advisory rows resolve to
Pillow `13.0.0` / Brotli `1.2.1`; all seven npm advisories name packages absent from
the committed lock. Of 118 CodeQL alerts, 86 are generated bundle/build mirrors; all
32 non-generated locations are either fixed in source or explicitly justified in the
reconciliation table. The hosted ledger remains owner-held until a push and rescan.

## Acceptance for this pass

1. `npm audit --package-lock-only` reports zero findings.
2. The new security regression tests pass.
3. `python3 build.py all --check` passes after generated mirrors are rebuilt.
4. The local six-width Playwright sweep is clean against `http://127.0.0.1:4175`.
5. No `@ts-ignore`, `eslint-disable`, CodeQL suppression, deleted test, or lowered
   threshold is introduced.
