# Round 8 — independent committed-HEAD verification

**Date:** 2026-11-03
**Commit audited:** `ebb96d4` (`main`)
**Origin:** `http://127.0.0.1:4175` (`einvite-app`, loopback only)
**Harness:** `bugs/round-6/live_flows.py`, widths 360, 390, 768, 1024, 1280, 1440
**Record:** `bugs/round-8/live-flows-six.json`

## Result

`LIVE_CHECKS=225 FAILED=0 WIDTHS=6`.

The sweep started after a fresh `python3 build.py all` and `systemctl --user restart
einvite-app`. The clean result covers:

- editor boot, Pages/Elements/Text/Uploads/Event/Blocks tabs, appearance, language,
  overflow menu, command palette, guest preview;
- selection, drag, resize, rotate, multi-select, add text, undo/redo, save,
  reload/recover, PNG export;
- template cards, search/filter/favorites/refresh, Khmer text and numerals;
- signed-out dashboard shell, invalid registration/sign-in, designer shell;
- missing-invitation 404; clean page errors, console (excluding the deliberate
  missing-invitation 404), and network.

## Artifact proof

Fresh build output:

- `python3 build.py all` → `BUILD_OK`, `MIRROR_CHECK_PASSED`.
- Served `bundle-index.js` SHA-256:
  `94570322281650015cd8ea4bc4672fe6649de5f9a08865f8421ea1d31ce2c06a`.
- `src/python/bundle-index.js` and `src/js/bundle-index.js` have the same SHA-256.
- `/api/health` returned 200 after restart; `/`, `/templates`, `/dashboard`, and
  `/designer` return 200.

## Security gate

- `bash scripts/security-scan.sh` → **PASS** (bandit 0 HIGH, pip-audit clean, SBOM
  10 components).
- `npm audit` → **0 vulnerabilities** at every severity.
- Fresh paginated ledger: **92 Dependabot / 49 unique advisories**, **118 CodeQL**,
  **0 secret-scanning**. Per-advisory reconciliation:
  `docs/security/HEAD-RECONCILIATION-2026-11-03.md`; **0 current vulnerable packages**.
- `build.py all --check` → `BUILD_OK`; `compileall` → exit 0; every `src/js/*.js`
  passes `node --check`; `git diff --check` clean.
- gitleaks/Trivy unavailable locally and skipped; the prior GitHub Gitleaks job passed.

## Findings

None. No new product bug and no regression was found. The two test-only regex and URL
assertion groups in CodeQL remain test fixtures, not shipped runtime code; the hosted
ledger is owner-held for push/rescan.
