# Version History

This project uses **semantic versioning**. `0.x` is pre-1.0; `1.0.0` is the first
production-certified release.

> **Legacy history:** the pre-reset version history (V1 → V54.34) is preserved
> in [`docs/LEGACY-VERSION-HISTORY.md`](docs/LEGACY-VERSION-HISTORY.md).

---

## Version numbering scheme

| Bump | When | Example |
|---|---|---|
| **MAJOR** (`0` → `1`) | Only at production certification. Never before. | `0.99.5` → `1.0.0` |
| **MINOR** (`0.54` → `0.55`) | A completed roadmap part. One minor per part. | `0.54.0` → `0.55.0` |
| **PATCH** (`0.54.0` → `0.54.1`) | A completed task within a part. | `0.54.0` → `0.54.1` → `0.54.2` |

---

## 0.68.1 — Security hardening: SQL injection fix + shared helpers + path/header/ReDoS/logging fixes

- **Triggered by:** GitHub Copilot security scan (Bandit B608 HIGH + pip-audit + Gitleaks).
- **SQL injection (B608 HIGH):** Fixed 2 dynamic `SET` clauses in `server.py` (`update_signup_sheet` + `update_poll`) — column names now filtered through hardcoded `frozenset` whitelist via `safe_set_clause()`; values parameter-bound. No `# nosec B608` suppression retained — the fix is real.
- **Shared helpers:** Created `src/python/core/security_helpers.py` (`safe_set_clause`, `safe_order_by`, `safe_path_under`, `safe_header_value`, `redact`, `redact_mapping`, `escape_html`).
- **Path injection:** Fixed `security_scanner_v54.py::scan_file()` — path containment check.
- **Response splitting:** Fixed 3 dynamic header values — CRLF stripped from `Content-Disposition` filenames + `Location` redirect.
- **Clear-text logging:** Fixed `production_preflight.py` — defensive redaction of messages with sensitive keywords.
- **Bandit MEDIUM suppressions:** Added `# nosec B404` (subprocess import, 2 sites), `# nosec B603` (subprocess calls, 4 sites) with reason comments.
- **Primary files:** `src/python/core/security_helpers.py`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `src/python/production_preflight.py`

---

## 0.68.2 — Phase B: consolidate helpers, replace B110 suppressions with logging, fix B404 placement, verify cryptography pin

- **B1 — Consolidated duplicate SQL helper modules:** Deleted `src/python/core/sql_safety.py` (duplicate of `security_helpers.py`). Updated `server.py` import from `core.sql_safety` to `core.security_helpers`. `security_helpers.py` is the single canonical location.
- **B2 — Removed dead import:** `safe_order_by` was imported but never called (no user-supplied `ORDER BY` columns exist). Removed from import line. Only `safe_set_clause` (which IS used at lines 8163 and 8374) is imported.
- **B3 — Replaced 42 `# nosec B110` suppressions with real logging:** Added module-level `_log = logging.getLogger("einvite.server")` with `StreamHandler`. Every `except OSError:pass` and `except Exception:pass` now reads `except <Type> as exc: _log.debug("cleanup failed: %s", exc)`. Zero `# nosec B110` suppressions remain (down from 42).
- **B4 — Corrected B404 suppression:** `# nosec B404` on `server.py` line 5 IS valid (subprocess IS imported there). Added `# nosec B404` to `security_scanner_v54.py:23` (the other `import subprocess` site) with reason comment.
- **B5 — Verified cryptography pin against PyPI:** `pip index versions cryptography` confirms latest is `50.0.1`. `pip-audit --strict` against `cryptography==44.0.1` reports **7 CVEs** (highest fix version: `50.0.0` for PYSEC-2026-3552). Updated pin from `>=44.0.1,<48` to `>=50.0.0,<51`.
- **B6 — Cleaned up duplicate VERSION_HISTORY entry:** Removed the stale second `0.68.1` entry (at line 110 — claimed `>=43,<48` and `# nosec` comments retained). Kept the accurate first entry.
- **Primary files:** `src/python/core/security_helpers.py`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `docs/requirements-production.txt`, `VERSION_HISTORY.md`

---

## 0.68.3 — Version-free source names + the two guards the mirror was missing

- **Triggered by:** the version-labeling audit plan, rewritten as a rename plan after measuring that no user-visible release label existed and that the audit had no end state. See `docs/superpowers/plans/2026-10-16-version-free-source-names.md`.
- **Latent defect found and fixed:** `src/python/route-deferred-loader-v15.js` was missing from the served mirror while `src/python/route-bundles-v15.json` listed it as a startup script for five routes. Because `src/python/` is the server `ROOT`, that is a silent 404. `python3 build.py all --check` was red (exit 1, `MIRROR_CHECK_FAILED`) while the entire pytest suite was green — nothing read the mirror.
- **Guard 1 — served-asset resolution:** new `tests/served_asset_resolution_test.py` asserts that every script/stylesheet/manifest/icon a served page declares resolves inside `src/python/`, that every manifest-declared bundle and deferred chunk exists, and that the mirror is byte-faithful. It calls the syncer's own `mirror_drift()` (extracted from `sync_frontend_assets.main --check`) so the gate and the test cannot disagree.
- **Guard 2 — naming ratchet:** new `tests/version_free_source_names_test.py` plus `tests/versioned_name_allowlist.json` fail on a new version-shaped file name under `src/js`/`src/css`, and on an allowlist entry with no file behind it. The list can only shrink.
- **Generated bundle family renamed:** `bundle-<page>-v15.{js,css}` → `bundle-<page>.{js,css}`, deferred chunks likewise, `route-deferred-loader-v15.js` → `route-deferred-loader.js`, and the three manifests (`route-bundles`, `page-assets`, `route-bundle-sources`) dropped their `-v15`. Generators, the mirror's `GENERATED` allowlist, the runtime loader's stem regex, the service-worker precache list and 33 HTML references moved together.
- **136 hand-authored modules renamed** with references updated across sources, manifests, tests, tools and live docs. The renamer refuses unsafe renames: occupied target, collision in the flattened served namespace (`src/css/organized/` flattens onto `src/css/`), or two batch entries sharing a target.
- **7 names deliberately left** for a human decision — each would collide with a different live file of the name it would take: `collaboration-v24.{js,css}`, `photo-editor-v13.{js,css}`, `workflow-creation-flow-v3.js`, `workflow-creation-flow-v4.js`, `organized/admin-page-v13.css`, `organized/photo-editor-v13.css`.
- **Verification:** `python3 build.py all --check` exit 0; the two new guards 35 passed; the 27-file targeted suite 42 passed with 1 pre-existing failure; the served routes fetched over HTTP (16 pages, 37 distinct assets, 10 deferred chunks) all 200; every route-bundle source entry resolves; the loader stem regex verified under node for both the startup and deferred forms.
- **Not done:** version-prefixed CSS class names and JS namespace segments (448 class names) — deferred as highest-risk and least user-visible.
- **Note:** `tests/v27_3_5_release_evidence_test.py::test_release_evidence` remains red on its `digest(README.md)` assertion. It was already red (README.md carries uncommitted edits) and was left un-rebaselined rather than baking unrelated pending edits into a V0.52 release-evidence assertion.
- **Primary files:** `tests/served_asset_resolution_test.py`, `tests/version_free_source_names_test.py`, `tests/versioned_name_allowlist.json`, `src/python/build/{build_route_bundles,build_page_manifests,sync_frontend_assets}.py`, `src/js/route-deferred-loader.js`, `src/js/service-worker.js`, `CONTRIBUTING.md`

---

## 0.68.4 — Phase 1 close: Khmer header surfaces and the visible review-set defects

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 1 (LT-1.1…LT-1.11, commits FB-68…FB-77), executed locally on `fix/2026-10-22-open-issues`.
- **i18n:** both Khmer addenda, ADDENDUM-2 and the shared terminology replacement applied by script (`VERIFIED 88/88`); the remaining English-on-KM strings are inventoried in `docs/i18n/KHMER-GAP-ROUND5-2026-10-24.md` with English as the accepted fallback. Khmer fallback pin moved 305 → 1 in the same commit.
- **Visible defects closed:** public Gregorian date follows the guest's chosen language and CTA pills stay on one line; dashboard cards size to their content with a readable bilingual status chip, a viewport-tall rail and an equal-height 375 tile row with no drawer smear; every route paints the bundled Khmer face; the 375 editor toolbar/chip/palette/zoom HUD fit; desktop editor has one search, one inspector title, an unclipped brand and no floating status pill; a signed-in non-admin gets the shared access-state card at 375/1440 light and dark.
- **Editor first paint:** `studio-design-mode` and the design section ship in the served markup and `core/theme.js` corrects them from storage before paint. Median probe CLS 0.5526 → 0.1438; LHCI index median 0.1415 against the ≤ 0.1 target — target not met, best number recorded.
- **CSP:** `tools/csp-violation-check.py` now drives `designer.html` signed in and out; `CSP_CHECK_PASSED`, no violation, CSP unchanged.
- **Budget regression caught at the phase close and fixed at the owning layer:** FB-70's dashboard-only rules moved from the universal `app-shell.css` to `canva-ui.css`, and two shipped JS comment blocks were dropped. `bundle-materials.js` 139,092 B (budget 147,456) and `bundle-public.css` 134,128 B (budget 134,144); no budget or threshold changed. Dashboard metrics match the FB-70 baseline with zero mismatches.
- **Verification:** full matrix `GATES_PASSED` — build, bundles, smoke 16 pages/0 errors, layout 1533 checks/0 failed, pytest 157 passed, budgets 6/6, LHCI 16/16 with a11y 1.00, CSP, canvas 22 pass/0 fail/2 skipped, `!important` 3816 ≤ 3823. Evidence in `artifacts/next-work/gates/20261025-121010/` and `artifacts/next-work/review-lt1/after/`.
- **Not done:** LT-1.9's ≤ 0.1 CLS target; the two P2 findings recorded in `artifacts/next-work/lt-1-8/FINDINGS.md` (320/375 topbar cluster clipping on five routes, editor Fit under the mobile Advanced bar at 320).
- **Primary files:** `src/css/app-shell.css`, `src/css/canva-ui.css`, `src/js/final-polish.js`, `src/js/editor/first-selection-prewarm.js`, `src/js/pages/admin/admin.js`, `src/js/public-page.js`, `tools/csp-violation-check.py`, `docs/i18n/*`, `docs/STATUS-INDEX.md`, `VERSION_HISTORY.md`

---

## 0.68.5 — Phase 2 close: the Khmer text engine, dates and export fidelity

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 2 (LT-2.1…LT-2.7, commits FB-78…FB-82), executed locally on `fix/2026-10-22-open-issues`.
- **Khmer numerals and dates (LT-2.2):** `core/khmer-format.js` converts digits from code points (`0x17E0 + n`), formats through `Intl.DateTimeFormat` with `-u-nu-khmr` and an optional Buddhist-era year, and falls back to English month names when the runtime has filtered ICU. The per-invitation `settings.khmerNumerals` switch defaults **off** and round-trips through the editor draft; the editor command only changes selected text.
- **Wrap audit (LT-2.1):** 3 long map paragraphs × 2 surfaces × 4 widths produced 67 line breaks, 0 inside a grapheme cluster and 67/67 on a word boundary; OD-30's fix condition was not met, so no helper or ZWSP was added.
- **Bilingual block audit (LT-2.3):** one object held an EN serif 28 px line and a KM sans 20 px line with independent line heights, identical left edges on editor and public at 375/1440 and no overflow; per-run authoring remains a documented `partial` for the LT-3.1 matrix.
- **Font self-hosting (LT-2.4):** 11 bundled WOFF2 / 2 licence files have rows; 232 `@font-face` blocks across 19 files all carry `font-display` and `unicode-range`, with 0 remote sources. Four fresh-context route loads made only loopback font requests and 0 console errors.
- **IME and paste (LT-2.5):** a map string survives three progressive composition chunks and a second pasted map string through the real editor, save and reload; 24/24 code points match in the model, stored object and reloaded DOM.
- **Export fidelity (LT-2.6):** SVG export now walks nested CSS rule lists, so the faces inside `@layer` are embedded instead of silently skipped (0 → 7 `@font-face` blocks). PNG at 1× is pixel-identical to the editor; 2×/3× stay within MAE 1.03/0.89 after downsampling. Print surfaces reset the inherited body `translateY(2px)` and use the exact page height: one-page PDF, embedded Noto Sans Khmer, text-box placement within 5 px on the loaded matrix (stated tolerance 8 px), MAE 2.0–3.6 at 96 dpi. The export dialog exposes 1×/2×/3× PNG.
- **Verification:** full matrix `GATES_PASSED` — build, bundles, smoke 16 pages/0 errors, layout 160.6 s with `UI_LAYOUT_GUARD_PASSED`, pytest **161 passed**, budgets 6/6, LHCI 16/16 minA11y 1.00, CSP, canvas 22 pass/0 fail/2 skipped, `!important` 3816 ≤ 3823. Phase 2 after set: 17 shots + 6 previews in `artifacts/next-work/review-lt2/after/`; 13/17 pixel-identical to Phase 1, four dynamic shots ≤ 0.35 MAE.
- **Not done:** per-run font/size authoring UI remains `partial` for LT-3.1; PDF text-box tolerance is 8 px because a loaded CI host shifted a long Khmer line by 5 px; the standalone `tests/v24_export_quality_browser_test.py` still cannot start under the current Chromium opaque-origin `set_content` (the real-server LT-2.6 test covers the same path).
- **Primary files:** `src/js/core/khmer-format.js`, `src/js/public-page.js`, `src/js/app.js`, `src/js/export-quality.js`, `src/python/export-quality.js`, `tests/lt_2_2_khmer_format_test.py`, `tests/lt_2_5_khmer_input_test.py`, `tests/lt_2_6_export_fidelity_test.py`, `docs/qa/khmer-text-sheet/`, `docs/STATUS-INDEX.md`, `VERSION_HISTORY.md`
