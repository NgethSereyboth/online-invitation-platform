# Structure-Migration Pilot Audit — Read-only

Status line: `git` IS AVAILABLE; repo is inside a git work tree (`main`); working tree has 4 pre-existing modifications in `docs/` and `scripts/`; `src/` is clean (`git status --porcelain src/` empty); audit creates exactly one new file (`?? docs/STRUCTURE-PILOT-AUDIT.md`); nothing else modified, deleted, renamed, or staged.

---

## 1. Git State

- `git rev-parse --abbrev-ref HEAD`: `main`
- `git status --porcelain` (whole repo):
  - ` M docs/STRUCTURE-MAPPING.json`
  - ` M docs/STRUCTURE-MAPPING.md`
  - ` M scripts/build_structure_mapping.py`
  - ` M scripts/migrate_structure.py`
  (4 modified files; all outside `src/`; the pilot directory itself is unmodified)
- `git status --porcelain src/`: **(no output)** — `src/` is clean in git
- `git log --oneline -n 10`: `6b60370 structure: pre-migration checkpoint (2A complete)` through `e126eaa Merge pull request #12 ...`
- `git diff --stat`: 4 files changed, 333 insertions(+), 208 deletions(-)
- Pre-existing modifications include `docs/STRUCTURE-MAPPING.json` and `docs/STRUCTURE-MAPPING.md` which the state file (`docs/.structure-migration-state.json`) references; this is consistent with the pilot being committed at `6b60370`.

---

## 2. Pilot Inventory

Source: `docs/.structure-migration-state.json` (16 `applied_moves` entries of `move:src→dst`, 25 `created_dirs`). The table below records both paths for each claimed move.

**Hashing method:** Python `hashlib.sha256` on raw bytes; normalized hash = `CRLF→LF` + `rstrip()` per line; `bash/sha256sum` not used (absent / unreliable on Windows).

| # | Source | Destination | src_ex | src_b | dst_ex | dst_b | sha_src | sha_dst | byte_id | norm_id | git_src | git_dst | src_trk | dst_trk | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| -1 | `src/python/security_v13.py` | `src/python/core/auth.py` | F | - | T | 14486 | - | `64325...c82` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -2 | `src/python/production_preflight.py` | `src/python/core/preflight.py` | F | - | T | 13979 | - | `e0297...146` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -3 | `src/python/dependency_preflight.py` | `src/python/core/deps.py` | F | - | T | 4408 | - | `371e8...3d2` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -4 | `src/python/security_scanner_v54.py` | `src/python/features/malware_scanner.py` | T | 18782 | T | 18763 | `d64d0...304` | `b3973...403` | F | F | (clean) | (clean) | T | T | DIVERGED |
| -5 | `src/python/secrets_v54.py` | `src/python/features/secrets.py` | F | - | T | 7016 | - | `3ccd2...460` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -6 | `src/python/plugin_marketplace_ca.py` | `src/python/features/plugin_marketplace_ca.py` | T | 8284 | T | 8284 | `229b8...fa5` | `229b8...fa5` | T | T | (clean) | (clean) | T | T | COPIED_LEFT_BEHIND |
| -7 | `src/python/backup_restore.py` | `src/python/features/backup.py` | F | - | T | 5864 | - | `77df4...7c3` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -8 | `src/python/build_route_bundles.py` | `src/python/build/build_route_bundles.py` | F | - | T | 9657 | - | `e4f62...4cd` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -9 | `src/python/build_editor_bundle.py` | `src/python/build/build_editor_bundle.py` | F | - | T | 6323 | - | `2b232...bf2` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -10 | `src/python/build_page_manifests.py` | `src/python/build/build_page_manifests.py` | F | - | T | 7637 | - | `ff0cb...1b3` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -11 | `src/python/sync_frontend_assets.py` | `src/python/build/sync_frontend_assets.py` | F | - | T | 7350 | - | `3ea10...5b1` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -12 | `src/python/prepare_production_env.py` | `src/python/build/prepare_production_env.py` | F | - | T | 5386 | - | `fb855...2f1` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -13 | `src/js/toast.js` | `src/js/components/toast.js` | T | 7545 | T | 7545 | `27b80...d1` | `27b80...d1` | T | T | (clean) | (clean) | T | T | COPIED_LEFT_BEHIND |
| -14 | `src/js/plugin_sandbox_host.js` | `src/js/plugins/sandbox-host.js` | T | 9998 | T | 9998 | `5a4c5...3a7` | `5a4c5...3a7` | T | T | (clean) | (clean) | T | T | COPIED_LEFT_BEHIND |
| -15 | `src/js/theme-init.js` | `src/js/core/theme.js` | F | - | T | 1799 | - | `3b49c...67` | F | F | (clean) | (clean) | F | T | MOVED_OK |
| -16 | `src/css/toast.css` | `src/css/components/toast.css` | T | 5445 | T | 5445 | `ef709...84` | `ef709...84` | T | T | (clean) | (clean) | T | T | COPIED_LEFT_BEHIND |

**Verdict counts:** `MOVED_OK` = 11; `COPIED_LEFT_BEHIND` = **4** (`-6`, `-13`, `-14`, `-16`); `DIVERGED` = 1 (`-4`); `TARGET_MISSING` = 0; `BOTH_MISSING` = 0; `PRE_EXISTING_TARGET` = 0.

Note on `-4` (`security_scanner_v54.py` → `features/malware_scanner.py`): both files exist in git (tracked, clean), raw bytes differ (18782 vs 18763) and normalized hashes differ (`597406...` vs `65a3d7...`). This is not a pure copy; content diverged after (or during) the move.

Note on source-tracked vs target-tracked: for the `COPIED_LEFT_BEHIND` rows, both source and destination are tracked by `git ls-files`; the source file remains at the old path (not deleted) and is committed, confirming the pilot performed a copy, not a move.

---

## 3. Duplicate Scan

- Under `src/js/`, `src/css/`, `src/python/`: no untracked files per `git status --porcelain` (other than 4 ignored files: `src/.env`, `src/python/data/.guest-token-secret`, `.media-signing-secret`, `.upload-signing-secret`).
- `src/js/components/chart.js`: **TRACKED** (`git ls-files` non-empty), exists (file present), `git status --porcelain src/js/components/chart.js` empty (clean). It is **not** in `docs/.structure-migration-state.json`; origin is unknown (pre-existing, not part of pilot).
- True duplicate groups (`.js`/`.css`/`.py`, identical normalized content, within `src/`): **38 groups**. Key groups:
  - `src/css/toast.css` ↔ `src/css/components/toast.css` (`SHA` `3e49d8...`) — pilot duplicate
  - `src/js/toast.js` ↔ `src/js/components/toast.js` (`SHA` `9dcf57...`) — pilot duplicate
  - `src/js/plugin_sandbox_host.js` ↔ `src/js/plugins/sandbox-host.js` (`SHA` `1626a6...`) — pilot duplicate
  - `src/python/plugin_marketplace_ca.py` ↔ `src/python/features/plugin_marketplace_ca.py` (`SHA` `077a49...`) — pilot duplicate
  - `src/css/bundle-*.css` (16 groups) duplicated between `src/css/` and `src/python/build/`
  - `src/js/bundle-*.js` (16 groups) duplicated between `src/js/` and `src/python/build/`
  - `src/css/editor-suite.css` ↔ `src/python/build/editor-suite.css`
  - `src/js/editor-suite.js` ↔ `src/python/build/editor-suite.js`
  (Many `bundle-*` duplicates are build artifacts copied by the pilot into `src/python/build/`; they are identical to the source bundles.)

---

## 4. Reference Audit

Search scope: `src/html/**/*.html`, `src/js/**/*.js`, `*.json` (repo root + `docs/`), `scripts/**/*.py`, root-level `*.py`. References to **old** path vs **new** path are distinguished; hard breakages (script/link tag pointing at missing file) flagged explicitly.

### Hard breakages (tag points to missing / wrong path)

- `<script src="theme-init.js">` in 12 HTML files (`account.html`, `admin.html`, `analytics.html`, `billing.html`, `checkin.html`, `dashboard.html`, `designer.html`, `guests.html`, `reset.html`, `responses.html`, `templates.html`, `verify.html`). Source `src/js/theme-init.js` moved to `src/js/core/theme.js`; old tag is broken. Corrected references exist in `index.html`, `materials.html`, `privacy.html` pointing at `core/theme.js`.
- `<link rel="stylesheet" href="toast.css">` in `dashboard.html`. Source `src/css/toast.css` moved to `src/css/components/toast.css`; old link broken.
- `docs/route-bundle-sources-v15.json`: `"earlyScripts": ["core/safe-dom.js","backend-mode-v14.js","theme-init.js"]` — references old path.
- `docs/page-assets-v15.json`: `"scripts":["theme-init.js",..."bundle-account-v15.js"]` (repeated for every page) — references old path.
- `docs/route-bundles-v15.json`: uses `bundle-account-v15.js` etc., not the moved module paths; not a direct breakage on moved files but confirms build artifacts still reference pre-migration names.

### Reference table (old path → files)

- `src/python/security_v13.py` → `docs/.structure-migration-state.json`, `docs/ARCHITECTURE.md`, `docs/LEGACY-VERSION-HISTORY.md`, `docs/ROADMAP-V2.md`, `docs/STRUCTURE-MAPPING.json`, `docs/STRUCTURE-MAPPING.md`, `docs/STRUCTURE-MAPPING.source.md`, `docs/security/ASVS-L2-GAP-ANALYSIS.md`
- `src/python/production_preflight.py` → `VERSION_HISTORY.md`, same docs set, `docs/certification/NATIVE-PLATFORM-MATRIX.md`, `docs/security/ASVS-L2-GAP-ANALYSIS.md`
- `src/python/dependency_preflight.py` → docs set
- `src/python/security_scanner_v54.py` → `VERSION_HISTORY.md`, docs set, `docs/ai/attack-stories/*.md`, `docs/certification/CERTIFICATION.md`, `docs/plugins/MODERATION-PIPELINE.md`, `docs/plugins/PLUGIN-SANDBOX.md`, `docs/security/ASVS-L2-GAP-ANALYSIS.md`
- `src/python/secrets_v54.py` → docs set, `docs/plugins/MODERATION-PIPELINE.md`, `docs/security/ASVS-L2-GAP-ANALYSIS.md`, `src/python/features/secrets.py`
- `src/python/plugin_marketplace_ca.py` → `ROADMAP-AUDIT.md`, docs set, `docs/plugins/PLUGIN-SIGNING.md`, `plugins/sdk/validate_manifest.py`
- `src/python/backup_restore.py` → `docs/ROADMAP-IMPLEMENTATION-REPORT.md`, docs set, `docs/certification/NATIVE-PLATFORM-MATRIX.md`, `docs/ops/BACKUP-DR.md`
- `src/python/build_route_bundles.py` → `src/html/index.html`, `README.md`, `assets/fonts/registry.json`, docs set, `docs/a11y/RESPONSIVE-AUDIT.md`, `docs/i18n/KHMER-TYPOGRAPHY.md`, `docs/security/SECURITY-FIX-GUIDE.md`, `scripts/check-bilingual-consistency.py`
- `src/python/build_editor_bundle.py` → `README.md`, docs set, `docs/security/SECURITY-FIX-GUIDE.md`
- `src/python/build_page_manifests.py` → docs set, `docs/security/SECURITY-FIX-GUIDE.md`
- `src/python/sync_frontend_assets.py` → `README.md`, `assets/fonts/registry.json`, docs set, `tests/v52_yjs_wiring_test.py`, `vendor/yjs/README.md`
- `src/python/prepare_production_env.py` → `README.md`, docs set
- `src/js/toast.js` → `ROADMAP-AUDIT.md`, docs set, `docs/a11y/RESPONSIVE-AUDIT.md`
- `src/js/plugin_sandbox_host.js` → `ROADMAP-AUDIT.md`, docs set, `docs/plugins/PLUGIN-SANDBOX.md`
- `src/js/theme-init.js` → docs set, `docs/ai/AGENT-SECURITY-DASHBOARD.md`
- `src/css/toast.css` → docs set, `docs/a11y/RESPONSIVE-AUDIT.md`

### New-path references found

- `src/python/core/auth.py` → `audit_roadmap.py`, `ROADMAP-AUDIT.md`, docs set
- `src/python/features/malware_scanner.py` → docs set, `docs/security/SECURITY-FIX-GUIDE.md`
- `src/python/features/secrets.py` → docs set
- `src/python/features/plugin_marketplace_ca.py` → `ROADMAP-AUDIT.md`, docs set
- `src/python/features/backup.py` → docs set, `docs/STRUCTURE-OVERRIDES.json`
- `src/python/build/*.py` (all 5) → docs set (not referenced in HTML/JS; pointed to by root wrapper only for `build_editor_bundle.py`)
- `src/js/components/toast.js` → `ROADMAP-AUDIT.md`, docs set
- `src/js/plugins/sandbox-host.js` → `ROADMAP-AUDIT.md`, docs set
- `src/js/core/theme.js` → `docs/STRUCTURE-MAPPING.json`, `docs/STRUCTURE-MAPPING.md`, `docs/STRUCTURE-MAPPING.source.md`
- `src/css/components/toast.css` → docs set

### Python import audit (old names still imported)

- `src/python/server.py` (9718 lines): `from security_scanner_v54 import ...` (L15), `from plugin_marketplace_ca import ...` (L17, L9323), `from production_preflight import validate_production_environment` (L9646). All three are old names; targets exist at new paths (`features/malware_scanner.py`, `features/plugin_marketplace_ca.py`, `core/preflight.py`) but `server.py` was not updated.
- `tests/security_mfa_recovery_test.py` (L116): `from core import auth as security_v13`
- `tests/security_notification_emails_test.py` (L219): `from core import auth as security_v13` (`# noqa: E402`)
- `tests/v13_backup_restore_test.py` (L7): `import backup_restore`
- `tests/v14_performance_budget_test.py` (L7): `import build_page_manifests as manifests`
- `scripts/check-bilingual-consistency.py`: references `build_route_bundles.py`

---

## 5. Build-Tooling Duplication

Triple for each tool: root file, old claimed `src/python/` path, new `src/python/build/` path.

| Root file | Exists | Size | Old `src/python/` | Exists | Size | New `src/python/build/` | Exists | Size | Root vs src | Evidence / import line |
|---|---|---|---|---|---|---|---|---|---|---|
| `build_editor_bundle.py` | T | 433 | `build_editor_bundle.py` | F | - | `build/build_editor_bundle.py` | T | 6323 | **NOT identical** (sha `54bed...` vs `2b232...`) | Thin wrapper: `sys.argv[0]=_target` then `runpy.run_path(_target,run_name='__main__')`; `_target` points at new path (`src/python/build/build_editor_bundle.py`) |
| `build_page_manifests.py` | T | 76 | `build_page_manifests.py` | F | - | `build/build_page_manifests.py` | T | 7637 | **NOT identical** (sha `cf82f...` vs `ff0cb...`) | **Broken stub / unrelated** — single line `_target=os.path.join(...)`; no `import os`, no execution logic |
| `build_route_bundles.py` | T | 75 | `build_route_bundles.py` | F | - | `build/build_route_bundles.py` | T | 9657 | **NOT identical** (sha `9e930...` vs `e4f62...`) | **Broken stub / unrelated** — identical broken pattern, no wrapper logic |

Conclusion: only `build_editor_bundle.py` is a legitimate wrapper; the other two root files are truncated stubs (not wrappers, not duplicates, not related to the moved modules beyond the variable assignment).

---

## 6. Migration Preview

Command: `python scripts/migrate_structure.py --dry-run`

- `loaded 353 rows from docs\STRUCTURE-MAPPING.json`
- `PLAN: moves=241 merge_sources=53 merge_targets=19 skipped=59 total_ops=260`
- `PLAN INVALID:` block: **none** (validation passed)
- Final line: `DRY RUN: no files were changed.`
- Exit code: `0` (successful)
- Stderr: empty
- Confirmed: **no file modifications** by this invocation (dry-run branch only; `--execute` was never invoked; state persistence is inside the execute branch only).

The preview reveals the planned migration is 241 moves + 53 merges + 19 merge targets + 59 skipped = 260 ops, mostly over `src/css/`, `src/js/`, `src/python/` — significantly larger than the 16-file pilot. The 16 pilot rows marked `done` in `docs/STRUCTURE-MAPPING.json` correspond to the 16 pairs audited above.

---

## 7. Blockers & Recommended Next Action

- **4 `COPIED_LEFT_BEHIND` duplicates remain at old paths** (`plugin_marketplace_ca.py`, `toast.js`, `plugin_sandbox_host.js`, `toast.css`) — each has a byte-identical copy at the new path; `git status --porcelain src/` is clean because both copies are tracked, so an `execute` run would treat them as already applied (`done`) and neither remove the old copy nor merge contents.
- **1 `DIVERGED` pair** (`security_scanner_v54.py` vs `features/malware_scanner.py`: 18782 vs 18763 bytes, different hashes) — old source still exists with different content from the destination; the larger migration would inherit this two-source state.
- **Hard reference breakages**: 12 HTML pages reference `theme-init.js` (moved → `core/theme.js`); `dashboard.html` references `toast.css` (moved → `components/toast.css`); `docs/route-bundle-sources-v15.json` and `docs/page-assets-v15.json` reference `theme-init.js`; `src/python/server.py` imports `security_scanner_v54`, `plugin_marketplace_ca`, `production_preflight` (all old names); `tests/` import `security_v13` alias, `backup_restore`, `build_page_manifests`.
- `scripts/migrate_structure.py --execute` refuses when `git status --porcelain src/` is non-empty; `src/` is currently clean, but the 4 duplicates and 1 divergence mean the pilot is not actually finished — running the 294-op migration on top of this state risks propagating duplicates into `src/python/build/`, `src/js/components/`, and new directories.

**Recommended next action:** Resolve the 4 `COPIED_LEFT_BEHIND` and 1 `DIVERGED` pilot pairs (delete/merge old sources, align `security_scanner_v54.py` with `malware_scanner.py`) and fix the `theme-init.js` / `toast.css` HTML references and `server.py` imports before invoking `scripts/migrate_structure.py --execute`.
