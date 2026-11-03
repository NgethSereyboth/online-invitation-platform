# Round 7 — PC-hosted route parity and security close-out

**Date:** 2026-11-03
**Origin:** `http://127.0.0.1:4175` (`einvite-app`, direct PC server)
**Build:** `python3 build.py all` → `BUILD_OK`; `MIRROR_CHECK_PASSED (up_to_date=533)`
**Harness:** `bugs/round-6/live_flows.py`, six widths: 360, 390, 768, 1024, 1280, 1440
**Record:** `bugs/round-7/live-flows-six.json`

## Final result

`LIVE_CHECKS=225 FAILED=0 WIDTHS=6` — every width completed with clean page errors,
console (excluding the deliberate missing-invitation 404), and network checks.

The final run covered the editor boot, appearance/language toggles, rail tabs, overflow
menu, design check, command palette, guest preview, selection, drag, resize, rotate,
multi-select, add text, undo/redo, save, reload/recover, PNG export (41,847 B at 1440),
template cards/search/filters/favorites/refresh, Khmer text and numerals, the signed-out
dashboard shell and invalid-form states, designer shell, and the missing-invitation 404.

## Findings

| ID | Page/route | Viewport(s) | Severity | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| BUG-R7-1 | `/templates` (also `/dashboard`, `/designer`) | 360, 390, 768, 1024, 1280, 1440 | P1 | The production-style page URL renders the corresponding PC page | Direct PC server returned **404**; the app's `.html` route worked | **Fixed** |

### BUG-R7-1 — extensionless page routes 404 on the direct PC host

**Reproduction (before fix):** `curl -I http://127.0.0.1:4175/templates` → `404`; the
same request to `/templates.html` → `200`. `/dashboard` and `/designer` behaved the same
way, so the dashboard/designer/template flows could not run at any width.

**Root cause:** Cloudflare Pages resolves extensionless paths to the corresponding
`.html` asset, while `src/python/server.py` only matched an explicit `*.html` path. The
existing harness intentionally uses the production-style URLs, so this was a direct-host
route-parity gap rather than a test-only mistake.

**Fix:** Added an explicit `PAGE_ALIASES` allowlist in `src/python/server.py` for the 15
top-level application pages, resolved only through `serve_html_file`. There is no
directory fallback or arbitrary HTML exposure. Added
`tests/page_route_alias_test.py`, which compares every alias response byte-for-byte with
its canonical `.html` page.

**Verification after fix:** `/templates`, `/dashboard`, and `/designer` return 200 on the
restarted service; the alias test passes; the final six-width sweep has zero failures.

## Security workstream

Captured GitHub feedback: **92 open Dependabot alerts / 49 unique advisories**, **118 open
CodeQL alerts**, **0 secret-scanning alerts**, and failed Security Scan run
`41472118974` (job `125368141539`). The CI failure was the old branch's Pillow `12.3.0`
and Brotli `1.2.0`; current pins are Pillow `13.0.0` and Brotli `1.2.1`.

Local verification after the fixes:

- `bash scripts/security-scan.sh` → **PASS** (bandit 0 HIGH, pip-audit clean, SBOM 10
  components). gitleaks and Trivy were unavailable and skipped.
- `npm ci --ignore-scripts --no-audit` → exit 0; `npm audit --json` → **0 vulnerabilities**
  (`puppeteer-core 25.16.0`, `chromium-bidi 157.0.8090-0`, `zod 4.6.7`).
- `python3 build.py all --check` → **BUILD_OK**, mirror check `up_to_date=533`.
- `python3 -m compileall -q src/python tests` → exit 0; `git diff --check` → clean.

The remote CodeQL ledger is **not claimed cleared**: the snapshot predates these commits
and must be pushed and rescanned. The remaining groups are triaged in
`docs/security/GITHUB-SECURITY-TRIAGE-2026-11-03.md`; generated mirror alerts are expected
to disappear after the rebuild/rescan, while the local-draft storage finding remains an
owner/privacy decision.

## Evidence

- Final JSON: `live-flows-six.json` in this folder.
- Final console log: `/tmp/r7c-sweep.log` (local run artifact).
- Baseline 404 run: `/tmp/r7-sweep.log` (18 failures, three per width, all `/templates`).
- Screenshots from the final harness run are under `bugs/round-6/shots/`; the same harness
  writes all six-width page/state captures there, including the repaired template,
  dashboard, and designer pages.
