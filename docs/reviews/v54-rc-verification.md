# V54-RC — Independent verification of the v54 changeset

**Dispatch:** V54-RC, issued 2026-10-05 · **Report:** 2026-10-05 · **Role:** verifying agent (falsification, not agreement). No commit, stash, checkout, reset, or clean was executed. No scratch files were created in the repo (all helper scripts and dumps live in `%TEMP%\einvite-platform\`).

---

## 1. Decision summary

**Verdict: CONDITIONALLY commit-ready.** The changeset is technically sound and internally consistent: HEAD is pinned at `133d3647…`; every one of the 16 regenerated JS bundles (and all 16 CSS bundles) is byte-exactly the manifest concatenation of the current working-tree sources (independent reconstruction `ALL_BUNDLES_CONSISTENT` plus `build_route_bundles.py --check` → `ROUTE_BUNDLE_CHECK_PASSED`); **no bundle hunk is unexplained** — every diff decomposes into (a) the `core/i18n.js` prepend on all 16 pages, (b) the admin page module split (`admin.js` → 9× `pages/admin/*.js`, admin only), and (c) per-page source edits that are all tracked-and-modified entries of this changeset (i18n sweep, v54 editor work, Inter font faces). The G1 fix (`#restoreFile` at `src/html/index.html:99`) is present, and the insertBefore regression fix is present in `src/js/studio-experience.js`, its mirror, and the rebuilt index bundle (applied fix = candidate A ∪ B hybrid, argued in §4 of this report). All 17 HTML mirrors are byte-identical. `src/js/core/i18n.js` is untracked but its build-requirement is a **FACT** (every bundle begins with its chunk; the builder hard-fails without it); its session-of-origin is **UNKNOWN** from git.

Conditions the user must satisfy before `git commit` (details in §9, item 4):

1. Accept staging of bucket F (351 untracked `src/python/` mirror entries) — that is a large addition the prior report treated as part of the changeset.
2. Accept `src/js/core/i18n.js` (bucket D) with UNKNOWN session-of-origin (content is in-scope and build-required; provenance is a prior i18n session, 2026-09-28).
3. Confirm the bucket-G exclusions (prior-session artifacts: backend feature-flag workstream in `server.py`/`features/settings.py`, sbom dependency bumps, 4 stale `src/python/build/` artifacts, scratch/audit files).
4. Acknowledge the Khmer gate: all 11 strings are copy-pasted verbatim from diff output and all 11 are present in `docs/i18n/TRANSLATIONS.csv` (`status=translated`), but their linguistic correctness is **UNKNOWN** (machine-generated; several look wrong, e.g. `Publish snapshot → ច្រើម`). `docs/reviews/v54-khmer-gate.md` carries the blank `khmer_proposed` column for the user.

Nothing in this verification falsifies the "commit-ready" claim. The prior session's numbers (16 bundles, 17/17 HTML, 497-line baseline) were independently re-derived; the only numeric drift is the porcelain count 497 → 498 (+1, explained: one tracked file gained a stat-dirty entry between sessions — see §2.3).

---

## 2. Ground (§0 of dispatch)

### 2.1 Mandated commands, raw output

```
PS> Get-Location
Path
----
F:\eInvite\einvite-platform
PS> git rev-parse --show-toplevel
F:/eInvite/einvite-platform
PS> git rev-parse HEAD
133d3647eb4a095337b7492e864c9acba94e1b35
PS> (git status --porcelain | Measure-Object -Line).Lines
498
```

**FACT.** HEAD matches the required pin `133d3647…` exactly.

### 2.2 Status dump

Full `git status --porcelain` dumped to `%TEMP%\einvite-platform\v54rc-status.txt`
(`$env:TEMP` resolved to `C:\Users\NGETHS~1\AppData\Local\Temp\dsh-Ak5Wmo`).
First 50 lines and last 20 lines of the 498-line dump:

```
 M .gitignore
 M docs/FONT_LICENSES_AND_REGISTRY.md
 M docs/page-assets-v15.json
 M docs/route-bundle-sources-v15.json
 M docs/route-bundles-v15.json
 M sbom.cdx.json
 M scripts/check-bilingual-consistency.py
 M scripts/security-scan.sh
 M src/css/account-page-v13.css
 M src/css/ai-assistant-pro.css
 M src/css/bundle-account-v15.css
 M src/css/bundle-admin-v15.css
 M src/css/bundle-analytics-v15.css
 M src/css/bundle-billing-v15.css
 M src/css/bundle-checkin-v15.css
 M src/css/bundle-dashboard-v15.css
 M src/css/bundle-designer-v15.css
 M src/css/bundle-guests-v15.css
 M src/css/bundle-index-v15.css
 M src/css/bundle-materials-v15.css
 M src/css/bundle-privacy-v15.css
 M src/css/bundle-public-v15.css
 M src/css/bundle-reset-v15.css
 M src/css/bundle-responses-v15.css
 M src/css/bundle-templates-v15.css
 M src/css/bundle-verify-v15.css
 M src/css/canvas-plus.css
 M src/css/compact-theme-v0_52.css
 M src/css/dashboard-page-v13.css
 M src/css/editor-suite.css
 M src/css/editor-ux-refinement-v0_52.css
 M src/css/editor/editor-styles.css
 M src/css/final-experience.css
 M src/css/final-polish.css
 M src/css/organized/styles.css
 M src/css/professional-layers-v29.css
 M src/css/studio-experience.css
 M src/css/ux-refine.css
 M src/html/account.html
 M src/html/admin.html
 M src/html/analytics.html
 M src/html/billing.html
 M src/html/checkin.html
 M src/html/dashboard.html
 M src/html/designer.html
 M src/html/guests.html
 M src/html/index.html
 M src/html/materials.html
 M src/html/privacy.html
 M src/html/public.html
```
… (middle 428 lines: remaining M entries + all 372 untracked entries) …
```
?? src/python/webgl-scene-backend-v22.js
?? src/python/workflow-continuity.css
?? src/python/workflow-continuity.js
?? src/python/workflow-creation-flow-v3.css
?? src/python/workflow-creation-flow-v3.js
?? src/python/workflow-creation-flow-v4.css
?? src/python/workflow-creation-flow-v4.js
?? src/python/workflow-final-audit-v7.css
?? src/python/workflow-final-audit-v7.js
?? src/python/workflow-pro-editor-v6.css
?? src/python/workflow-pro-editor-v6.js
?? src/python/workflow-refine.css
?? src/python/workflow-refine.js
?? src/python/workflow-ux-v5.css
?? src/python/workflow-ux-v5.js
?? src/python/workspace-v21.css
?? src/python/workspace-v21.js
?? src/python/zoom-layout-pages-v22.css
?? src/python/zoom-layout-v22.css
?? tests/ac4_2d_audit_test.py
```

### 2.3 Baseline delta: 498 vs the prior session's 497

**FACT.** Count is 498 (126 ` M` + 372 `??`); the G1 report recorded 497 (125 ` M` + 372 `??`).
Not materially different (Δ = 1). Reconciliation: `git diff --name-only` (index vs
worktree) lists **125** files; `git status` flags **126**. The extra one is:

```
PS> # in status-M but not in git diff
scripts/security-scan.sh
```

`scripts/security-scan.sh` is stat-dirty with **no content diff** (pure line-ending /
stat-cache artifact under `core.autocrlf`; `git diff` shows nothing for it).
**INFERENCE:** the +1 is this entry appearing (or being re-flagged) after the G1
session; it carries no content. It is classified H (§3) and excluded from the commit.
All CRLF stderr warnings observed during diff runs were stale stat-cache noise on
files that are content-clean (verified: none of the warned paths appear in status).

---

## 3. Inventory (§1 of dispatch)

Full table, one row per porcelain entry (498/498), machine-classified;
`size-delta if M` is `git diff --numstat` (insertions/deletions):

| path | bucket | tracked | size-delta if M |
|---|---|---|---|
| .gitignore | G | yes | +13/-1 |
| docs/FONT_LICENSES_AND_REGISTRY.md | A | yes | +36/-0 |
| docs/page-assets-v15.json | E | yes | +37/-34 |
| docs/route-bundle-sources-v15.json | E | yes | +30/-5 |
| docs/route-bundles-v15.json | E | yes | +91/-66 |
| sbom.cdx.json | G | yes | +21/-21 |
| scripts/check-bilingual-consistency.py | A | yes | +254/-52 |
| scripts/security-scan.sh | H | yes | - |
| src/css/account-page-v13.css | A | yes | +1/-1 |
| src/css/ai-assistant-pro.css | A | yes | +1/-1 |
| src/css/bundle-account-v15.css | E | yes | +17/-8 |
| src/css/bundle-admin-v15.css | E | yes | +17/-8 |
| src/css/bundle-analytics-v15.css | E | yes | +17/-8 |
| src/css/bundle-billing-v15.css | E | yes | +17/-8 |
| src/css/bundle-checkin-v15.css | E | yes | +5/-2 |
| src/css/bundle-dashboard-v15.css | E | yes | +37/-9 |
| src/css/bundle-designer-v15.css | E | yes | +17/-8 |
| src/css/bundle-guests-v15.css | E | yes | +17/-8 |
| src/css/bundle-index-v15.css | E | yes | +287/-13 |
| src/css/bundle-materials-v15.css | E | yes | +17/-8 |
| src/css/bundle-privacy-v15.css | E | yes | +7/-2 |
| src/css/bundle-public-v15.css | E | yes | +5/-2 |
| src/css/bundle-reset-v15.css | E | yes | +17/-8 |
| src/css/bundle-responses-v15.css | E | yes | +17/-8 |
| src/css/bundle-templates-v15.css | E | yes | +17/-8 |
| src/css/bundle-verify-v15.css | E | yes | +17/-8 |
| src/css/canvas-plus.css | A | yes | +10/-4 |
| src/css/compact-theme-v0_52.css | A | yes | +2/-0 |
| src/css/dashboard-page-v13.css | A | yes | +19/-0 |
| src/css/editor-suite.css | A | yes | +10/-4 |
| src/css/editor-ux-refinement-v0_52.css | A | yes | +3/-2 |
| src/css/editor/editor-styles.css | A | yes | +273/-3 |
| src/css/final-experience.css | A | yes | +1/-1 |
| src/css/final-polish.css | A | yes | +1/-1 |
| src/css/organized/styles.css | A | yes | +4/-1 |
| src/css/professional-layers-v29.css | A | yes | +2/-2 |
| src/css/studio-experience.css | A | yes | +1/-1 |
| src/css/ux-refine.css | A | yes | +1/-1 |
| src/html/account.html | A | yes | +10/-10 |
| src/html/admin.html | A | yes | +2/-2 |
| src/html/analytics.html | A | yes | +2/-2 |
| src/html/billing.html | A | yes | +6/-6 |
| src/html/checkin.html | A | yes | +2/-2 |
| src/html/dashboard.html | A | yes | +18/-18 |
| src/html/designer.html | A | yes | +3/-3 |
| src/html/guests.html | A | yes | +2/-2 |
| src/html/index.html | A | yes | +48/-12 |
| src/html/materials.html | A | yes | +10/-10 |
| src/html/privacy.html | A | yes | +52/-47 |
| src/html/public.html | A | yes | +1/-1 |
| src/html/reset.html | A | yes | +9/-9 |
| src/html/responses.html | A | yes | +2/-2 |
| src/html/templates.html | A | yes | +2/-2 |
| src/html/verify.html | A | yes | +4/-9 |
| src/js/account.js | A | yes | +11/-6 |
| src/js/album.js | A | yes | +5/-5 |
| src/js/analytics.js | A | yes | +8/-2 |
| src/js/billing.js | A | yes | +21/-15 |
| src/js/bundle-account-v15.js | E | yes | +270/-7 |
| src/js/bundle-admin-v15.js | E | yes | +1372/-29 |
| src/js/bundle-analytics-v15.js | E | yes | +267/-3 |
| src/js/bundle-billing-v15.js | E | yes | +280/-16 |
| src/js/bundle-checkin-v15.js | E | yes | +269/-7 |
| src/js/bundle-dashboard-v15.js | E | yes | +291/-26 |
| src/js/bundle-designer-v15.js | E | yes | +268/-2 |
| src/js/bundle-guests-v15.js | E | yes | +289/-13 |
| src/js/bundle-index-v15.js | E | yes | +456/-27 |
| src/js/bundle-materials-v15.js | E | yes | +269/-6 |
| src/js/bundle-privacy-v15.js | E | yes | +259/-0 |
| src/js/bundle-public-v15.js | E | yes | +278/-20 |
| src/js/bundle-reset-v15.js | E | yes | +266/-3 |
| src/js/bundle-responses-v15.js | E | yes | +271/-9 |
| src/js/bundle-templates-v15.js | E | yes | +275/-13 |
| src/js/bundle-verify-v15.js | E | yes | +263/-2 |
| src/js/checkin-v13.js | A | yes | +10/-6 |
| src/js/collaboration-presence-v52.js | A | yes | +6/-4 |
| src/js/components/chart.js | A | yes | +5/-2 |
| src/js/crdt-yjs-indexeddb.js | A | yes | +6/-4 |
| src/js/crdt-yjs-rich-media.js | A | yes | +6/-4 |
| src/js/crdt-yjs-undo.js | A | yes | +6/-5 |
| src/js/dashboard.js | A | yes | +10/-6 |
| src/js/delivery-dialog.js | A | yes | +6/-5 |
| src/js/designer.js | A | yes | +9/-1 |
| src/js/editor/chrome/command-palette.js | A | yes | +5/-2 |
| src/js/editor/chrome/layers.js | A | yes | +5/-2 |
| src/js/editor/chrome/pages.js | A | yes | +4/-2 |
| src/js/editor/chrome/shortcuts.js | A | yes | +5/-2 |
| src/js/editor/collab/comments.js | A | yes | +4/-2 |
| src/js/editor/collab/presence.js | A | yes | +5/-2 |
| src/js/editor/editor-core.js | A | yes | +157/-10 |
| src/js/editor/history/timeline.js | A | yes | +5/-4 |
| src/js/editor/ui-layout.js | A | yes | +9/-1 |
| src/js/guest-journey.js | A | yes | +1/-1 |
| src/js/guests.js | A | yes | +29/-11 |
| src/js/host-polls.js | A | yes | +6/-5 |
| src/js/host-signup-sheets.js | A | yes | +6/-5 |
| src/js/invitation-edit-history.js | A | yes | +4/-4 |
| src/js/materials.js | A | yes | +9/-4 |
| src/js/monitoring.js | A | yes | +83/-5 |
| src/js/pages/admin/admin.js | A | yes | +24/-8 |
| src/js/pages/admin/audit-log.js | A | yes | +6/-1 |
| src/js/pages/admin/bulk-operations.js | A | yes | +6/-1 |
| src/js/pages/admin/feature-flags.js | A | yes | +100/-14 |
| src/js/pages/admin/impersonate.js | A | yes | +6/-1 |
| src/js/pages/admin/invitations.js | A | yes | +6/-1 |
| src/js/pages/admin/reports.js | A | yes | +6/-1 |
| src/js/pages/admin/system-health.js | A | yes | +6/-1 |
| src/js/pages/admin/users.js | A | yes | +11/-1 |
| src/js/pages/auth/sessions.js | A | yes | +5/-5 |
| src/js/pages/dashboard/analytics.js | A | yes | +6/-1 |
| src/js/polls.js | A | yes | +4/-4 |
| src/js/public-page.js | A | yes | +1/-1 |
| src/js/reset.js | A | yes | +7/-2 |
| src/js/responses.js | A | yes | +11/-7 |
| src/js/service-worker.js | A | yes | +2/-2 |
| src/js/signup-sheets.js | A | yes | +4/-4 |
| src/js/studio-experience.js | C | yes | +31/-15 |
| src/js/templates.js | A | yes | +15/-11 |
| src/js/verify.js | A | yes | +4/-1 |
| src/python/build/build_route_bundles.py | A | yes | +8/-7 |
| src/python/build/bundle-admin-v15.js | G | yes | +958/-23 |
| src/python/build/editor-suite.css | G | yes | +10/-4 |
| src/python/build/page-assets-v15.json | G | yes | +37/-34 |
| src/python/build/route-bundles-v15.json | G | yes | +11/-3 |
| src/python/build/sync_frontend_assets.py | A | yes | +2/-1 |
| src/python/server.py | G | yes | +168/-3 |
| .cache/ | G | no | - |
| .pw-browsers/ | G | no | - |
| _i18n_all_result.json | G | no | - |
| assets/fonts/inter-latin-400.woff2 | A | no | - |
| assets/fonts/inter-latin-700.woff2 | A | no | - |
| assets/fonts/inter-latin-800.woff2 | A | no | - |
| deliverables/ | G | no | - |
| docs/SESSION-LOG-2026-09-26.md | G | no | - |
| docs/STRUCTURE-PILOT-AUDIT.md | G | no | - |
| docs/UX-AUDIT-2026-09-26.md | G | no | - |
| docs/i18n/LANGUAGE-GAP-REPORT.md | A | no | - |
| docs/i18n/TRANSLATIONS.csv | A | no | - |
| docs/reviews/ | G | no | - |
| licenses/fonts/Inter-OFL-1.1.txt | A | no | - |
| screenshots/ | G | no | - |
| scripts/audit_bidi.js | G | no | - |
| scripts/fix_structure_references.py | G | no | - |
| src/html/test-i18n-beacon.html | G | no | - |
| src/js/core/i18n.js | D | no | - |
| src/python/accessibility-polish.js | F | no | - |
| src/python/accessibility-v12.css | F | no | - |
| src/python/account-page-v13.css | F | no | - |
| src/python/account-security-v13.css | F | no | - |
| src/python/account-security-v13.js | F | no | - |
| src/python/account.html | F | no | - |
| src/python/account.js | F | no | - |
| src/python/adaptive-gpu-quality-v22.js | F | no | - |
| src/python/adaptive-templates-v25.css | F | no | - |
| src/python/adaptive-templates-v25.js | F | no | - |
| src/python/admin-page-v13.css | F | no | - |
| src/python/admin.html | F | no | - |
| src/python/admin.js | F | no | - |
| src/python/advanced-animation-v44.js | F | no | - |
| src/python/advanced-editor-loader-v32.js | F | no | - |
| src/python/advanced-motion-runtime-v44.js | F | no | - |
| src/python/advanced-public-loader-v32.js | F | no | - |
| src/python/advanced-public-renderer-v32.css | F | no | - |
| src/python/advanced-public-renderer-v32.js | F | no | - |
| src/python/ai-agent-tool-registry-v28.js | F | no | - |
| src/python/ai-assistant-loader-v27.css | F | no | - |
| src/python/ai-assistant-loader-v27.js | F | no | - |
| src/python/ai-assistant-pro.css | F | no | - |
| src/python/ai-assistant-pro.js | F | no | - |
| src/python/ai-creative-agent-v28.css | F | no | - |
| src/python/ai-creative-agent-v28.js | F | no | - |
| src/python/ai-editor-action-extension-v53.js | F | no | - |
| src/python/ai-editor-action-service-v27.js | F | no | - |
| src/python/ai-production-v35.js | F | no | - |
| src/python/album.js | F | no | - |
| src/python/analytics-page-v13.css | F | no | - |
| src/python/analytics.html | F | no | - |
| src/python/analytics.js | F | no | - |
| src/python/app.js | F | no | - |
| src/python/asset-workflow-v23.css | F | no | - |
| src/python/asset-workflow-v23.js | F | no | - |
| src/python/assets/ | F | no | - |
| src/python/backend-mode-v14.js | F | no | - |
| src/python/billing-page-v13.css | F | no | - |
| src/python/billing.html | F | no | - |
| src/python/billing.js | F | no | - |
| src/python/brand-components-v24.css | F | no | - |
| src/python/brand-components-v24.js | F | no | - |
| src/python/builtin-templates.js | F | no | - |
| src/python/bundle-account-v15.css | F | no | - |
| src/python/bundle-account-v15.js | F | no | - |
| src/python/bundle-admin-v15.css | F | no | - |
| src/python/bundle-admin-v15.js | F | no | - |
| src/python/bundle-analytics-v15.css | F | no | - |
| src/python/bundle-analytics-v15.js | F | no | - |
| src/python/bundle-billing-v15.css | F | no | - |
| src/python/bundle-billing-v15.js | F | no | - |
| src/python/bundle-checkin-v15.css | F | no | - |
| src/python/bundle-checkin-v15.js | F | no | - |
| src/python/bundle-dashboard-v15.css | F | no | - |
| src/python/bundle-dashboard-v15.js | F | no | - |
| src/python/bundle-designer-v15.css | F | no | - |
| src/python/bundle-designer-v15.js | F | no | - |
| src/python/bundle-guests-v15.css | F | no | - |
| src/python/bundle-guests-v15.js | F | no | - |
| src/python/bundle-index-v15.css | F | no | - |
| src/python/bundle-index-v15.js | F | no | - |
| src/python/bundle-materials-v15.css | F | no | - |
| src/python/bundle-materials-v15.js | F | no | - |
| src/python/bundle-privacy-v15.css | F | no | - |
| src/python/bundle-privacy-v15.js | F | no | - |
| src/python/bundle-public-v15.css | F | no | - |
| src/python/bundle-public-v15.js | F | no | - |
| src/python/bundle-reset-v15.css | F | no | - |
| src/python/bundle-reset-v15.js | F | no | - |
| src/python/bundle-responses-v15.css | F | no | - |
| src/python/bundle-responses-v15.js | F | no | - |
| src/python/bundle-templates-v15.css | F | no | - |
| src/python/bundle-templates-v15.js | F | no | - |
| src/python/bundle-verify-v15.css | F | no | - |
| src/python/bundle-verify-v15.js | F | no | - |
| src/python/canva-scale-v31.js | F | no | - |
| src/python/canvas-plus.css | F | no | - |
| src/python/canvas-plus.js | F | no | - |
| src/python/checkin-v13.css | F | no | - |
| src/python/checkin-v13.js | F | no | - |
| src/python/checkin.html | F | no | - |
| src/python/collaboration-live.css | F | no | - |
| src/python/collaboration-live.js | F | no | - |
| src/python/collaboration-presence-v52.js | F | no | - |
| src/python/collaboration-studio-v31.css | F | no | - |
| src/python/collaboration-studio-v31.js | F | no | - |
| src/python/collaboration-v24.css | F | no | - |
| src/python/collaboration-v24.js | F | no | - |
| src/python/collaboration.css | F | no | - |
| src/python/collaboration.js | F | no | - |
| src/python/command-palette-v23.css | F | no | - |
| src/python/command-palette-v23.js | F | no | - |
| src/python/compact-theme-v0_52.css | F | no | - |
| src/python/content-browser-v24.css | F | no | - |
| src/python/content-browser-v24.js | F | no | - |
| src/python/core/i18n.js | F | no | - |
| src/python/core/safe-dom.js | F | no | - |
| src/python/core/theme.js | F | no | - |
| src/python/crdt-adapter-v31.js | F | no | - |
| src/python/crdt-yjs-indexeddb.js | F | no | - |
| src/python/crdt-yjs-rich-media.js | F | no | - |
| src/python/crdt-yjs-undo.js | F | no | - |
| src/python/creative-packs.css | F | no | - |
| src/python/creative-packs.js | F | no | - |
| src/python/custom-font-core-v22.js | F | no | - |
| src/python/custom-fonts-v22.css | F | no | - |
| src/python/custom-fonts-v22.js | F | no | - |
| src/python/dashboard-css-km.html | F | no | - |
| src/python/dashboard-empty-state.css | F | no | - |
| src/python/dashboard-empty-state.js | F | no | - |
| src/python/dashboard-enhancements.js | F | no | - |
| src/python/dashboard-page-v13.css | F | no | - |
| src/python/dashboard-polish.js | F | no | - |
| src/python/dashboard.html | F | no | - |
| src/python/dashboard.js | F | no | - |
| src/python/data-merge-v47.js | F | no | - |
| src/python/delivery-dialog.js | F | no | - |
| src/python/designer-page-v13.css | F | no | - |
| src/python/designer.html | F | no | - |
| src/python/designer.js | F | no | - |
| src/python/direct-manipulation-v24.css | F | no | - |
| src/python/direct-manipulation-v24.js | F | no | - |
| src/python/document-schema-v32.js | F | no | - |
| src/python/editor-builders.css | F | no | - |
| src/python/editor-builders.js | F | no | - |
| src/python/editor-canva-v13.css | F | no | - |
| src/python/editor-canva-v13.js | F | no | - |
| src/python/editor-canvas-core.css | F | no | - |
| src/python/editor-command-system-v23.js | F | no | - |
| src/python/editor-commands-v13.js | F | no | - |
| src/python/editor-deferred-tools-bootstrap-v0_52.js | F | no | - |
| src/python/editor-layout-stability.css | F | no | - |
| src/python/editor-layout-stability.js | F | no | - |
| src/python/editor-pro.css | F | no | - |
| src/python/editor-pro.js | F | no | - |
| src/python/editor-responsive-contract-v27.css | F | no | - |
| src/python/editor-responsive-contract-v27.js | F | no | - |
| src/python/editor-schema-v13.js | F | no | - |
| src/python/editor-shared-styles-v13.css | F | no | - |
| src/python/editor-shared-styles-v13.js | F | no | - |
| src/python/editor-suite.css | F | no | - |
| src/python/editor-suite.js | F | no | - |
| src/python/editor-ui-layout.css | F | no | - |
| src/python/editor-ux-refinement-v0_52.css | F | no | - |
| src/python/enterprise-government-v42.js | F | no | - |
| src/python/event-ecosystem-v52.js | F | no | - |
| src/python/experience-schema.js | F | no | - |
| src/python/export-quality-v24.css | F | no | - |
| src/python/export-quality-v24.js | F | no | - |
| src/python/features/settings.py | G | no | - |
| src/python/final-experience.css | F | no | - |
| src/python/final-experience.js | F | no | - |
| src/python/final-polish.css | F | no | - |
| src/python/final-polish.js | F | no | - |
| src/python/font-browser-loader-v22.js | F | no | - |
| src/python/font-browser.css | F | no | - |
| src/python/font-browser.js | F | no | - |
| src/python/future-public-renderer-v52.css | F | no | - |
| src/python/future-public-renderer-v52.js | F | no | - |
| src/python/future-studio-loader-v52.js | F | no | - |
| src/python/future-studio-v52.css | F | no | - |
| src/python/future-ui-v0_52.js | F | no | - |
| src/python/gpu-loader-v22.js | F | no | - |
| src/python/gpu-projection-v22.js | F | no | - |
| src/python/gpu-texture-cache-v22.js | F | no | - |
| src/python/graphics-runtime-v22.css | F | no | - |
| src/python/guest-features-v54_1.css | F | no | - |
| src/python/guest-journey.css | F | no | - |
| src/python/guest-journey.js | F | no | - |
| src/python/guest-layouts.css | F | no | - |
| src/python/guest-layouts.js | F | no | - |
| src/python/guests-page-v13.css | F | no | - |
| src/python/guests-test-en.html | F | no | - |
| src/python/guests-test-km.html | F | no | - |
| src/python/guests.html | F | no | - |
| src/python/guests.js | F | no | - |
| src/python/host-polls.js | F | no | - |
| src/python/host-signup-sheets.js | F | no | - |
| src/python/i18n-css-en.html | F | no | - |
| src/python/i18n-css-km.html | F | no | - |
| src/python/i18n-css-test.html | F | no | - |
| src/python/i18n-inject-test.html | F | no | - |
| src/python/incremental-scene-renderer-v22.js | F | no | - |
| src/python/index-test-en.html | F | no | - |
| src/python/index-test-km.html | F | no | - |
| src/python/index.html | F | no | - |
| src/python/interaction-scheduler-v22.js | F | no | - |
| src/python/invitation-context.js | F | no | - |
| src/python/invitation-edit-history.js | F | no | - |
| src/python/lang-km.html.bak | F | no | - |
| src/python/licenses/ | F | no | - |
| src/python/manifest.webmanifest | F | no | - |
| src/python/materials-page-v13.css | F | no | - |
| src/python/materials.html | F | no | - |
| src/python/materials.js | F | no | - |
| src/python/mobile-editor-v14.js | F | no | - |
| src/python/modern-ui.css | F | no | - |
| src/python/modern-ui.js | F | no | - |
| src/python/monitoring.css | F | no | - |
| src/python/monitoring.js | F | no | - |
| src/python/navigation-history-v23.css | F | no | - |
| src/python/navigation-history-v23.js | F | no | - |
| src/python/opening-scenes.css | F | no | - |
| src/python/opening-scenes.js | F | no | - |
| src/python/package-lock.json | F | no | - |
| src/python/package.json | F | no | - |
| src/python/page-experience-v22.css | F | no | - |
| src/python/page-experience-v22.js | F | no | - |
| src/python/performance-loader-v22.js | F | no | - |
| src/python/performance-observability-v22.js | F | no | - |
| src/python/photo-editor-v13.css | F | no | - |
| src/python/photo-editor-v13.js | F | no | - |
| src/python/photo-editor.css | F | no | - |
| src/python/photo-editor.js | F | no | - |
| src/python/photo-retouch-v13.css | F | no | - |
| src/python/photo-retouch-v13.js | F | no | - |
| src/python/photo-style-library-v23.css | F | no | - |
| src/python/photo-style-library-v23.js | F | no | - |
| src/python/photo-worker-v13.js | F | no | - |
| src/python/photo-workflow-v23.css | F | no | - |
| src/python/photo-workflow-v23.js | F | no | - |
| src/python/plugin-platform-v48.js | F | no | - |
| src/python/plugin-runtime-v48.js | F | no | - |
| src/python/plugin_sandbox_host.js | F | no | - |
| src/python/polls.js | F | no | - |
| src/python/print-readiness-v25.css | F | no | - |
| src/python/print-readiness-v25.js | F | no | - |
| src/python/privacy-v13.css | F | no | - |
| src/python/privacy.html | F | no | - |
| src/python/product-operations-v13.css | F | no | - |
| src/python/product-operations-v13.js | F | no | - |
| src/python/production-readiness-v32.css | F | no | - |
| src/python/production-readiness-v32.js | F | no | - |
| src/python/professional-editor-v17.css | F | no | - |
| src/python/professional-editor-v17.js | F | no | - |
| src/python/professional-layers-v29.css | F | no | - |
| src/python/professional-layers-v29.js | F | no | - |
| src/python/professional-workflow-loader-v23.js | F | no | - |
| src/python/professional-workflow-v23.css | F | no | - |
| src/python/professional-workflow-v23.js | F | no | - |
| src/python/public-page.js | F | no | - |
| src/python/public-share-panel.js | F | no | - |
| src/python/public.html | F | no | - |
| src/python/publishing-domains-v45.js | F | no | - |
| src/python/pw_verify.js | F | no | - |
| src/python/pw_verify2.js | F | no | - |
| src/python/pw_verify3.js | F | no | - |
| src/python/raster-model-v30.js | F | no | - |
| src/python/raster-worker-v30.js | F | no | - |
| src/python/raster-workspace-v30.css | F | no | - |
| src/python/raster-workspace-v30.js | F | no | - |
| src/python/render-worker-bridge-v22.js | F | no | - |
| src/python/renderer-core.js | F | no | - |
| src/python/reset-page-v13.css | F | no | - |
| src/python/reset.html | F | no | - |
| src/python/reset.js | F | no | - |
| src/python/responses-page-v13.css | F | no | - |
| src/python/responses.html | F | no | - |
| src/python/responses.js | F | no | - |
| src/python/review-v23.css | F | no | - |
| src/python/review-v23.js | F | no | - |
| src/python/rich-text-contract.js | F | no | - |
| src/python/rich-text-document-model.js | F | no | - |
| src/python/rich-text-editing-v21.css | F | no | - |
| src/python/rich-text-editing-v21.js | F | no | - |
| src/python/rich-text-renderer-v21.css | F | no | - |
| src/python/rich-text-renderer-v21.js | F | no | - |
| src/python/route-bundles-v15.json | F | no | - |
| src/python/runtime-lifecycle-v15.js | F | no | - |
| src/python/scene-graph-v29.js | F | no | - |
| src/python/scene-model-v22.js | F | no | - |
| src/python/scene-render-worker-v22.js | F | no | - |
| src/python/service-worker.js | F | no | - |
| src/python/signup-sheets.js | F | no | - |
| src/python/smart-layout-v24.css | F | no | - |
| src/python/smart-layout-v24.js | F | no | - |
| src/python/social-card.css | F | no | - |
| src/python/social-card.js | F | no | - |
| src/python/stabilized-v14.css | F | no | - |
| src/python/storage.js | F | no | - |
| src/python/storyboard.css | F | no | - |
| src/python/storyboard.js | F | no | - |
| src/python/studio-automation-v27.css | F | no | - |
| src/python/studio-automation-v27.js | F | no | - |
| src/python/studio-experience.css | F | no | - |
| src/python/studio-experience.js | F | no | - |
| src/python/studio-governance-v25.css | F | no | - |
| src/python/studio-governance-v25.js | F | no | - |
| src/python/studio-operations-v26.css | F | no | - |
| src/python/studio-operations-v26.js | F | no | - |
| src/python/style-history-v23.css | F | no | - |
| src/python/style-history-v23.js | F | no | - |
| src/python/style-kits.css | F | no | - |
| src/python/style-kits.js | F | no | - |
| src/python/styles.css | F | no | - |
| src/python/template-bindings-v25.css | F | no | - |
| src/python/template-bindings-v25.js | F | no | - |
| src/python/template-marketplace-v36.js | F | no | - |
| src/python/templates-page-v13.css | F | no | - |
| src/python/templates.html | F | no | - |
| src/python/templates.js | F | no | - |
| src/python/test-a.html | F | no | - |
| src/python/test-b.html | F | no | - |
| src/python/test-c.html | F | no | - |
| src/python/test-d.html | F | no | - |
| src/python/test-i18n-beacon.html | F | no | - |
| src/python/test-i18n-click.html | F | no | - |
| src/python/theme-hardening.css | F | no | - |
| src/python/timeline-runtime-v13.js | F | no | - |
| src/python/timeline-v13.css | F | no | - |
| src/python/timeline-v13.js | F | no | - |
| src/python/toast.css | F | no | - |
| src/python/toast.js | F | no | - |
| src/python/tokens.css | F | no | - |
| src/python/typography-contract.js | F | no | - |
| src/python/typography-document-model.js | F | no | - |
| src/python/typography-editor-v20.js | F | no | - |
| src/python/typography-fonts.css | F | no | - |
| src/python/typography-layout-service.js | F | no | - |
| src/python/typography-system-v20.css | F | no | - |
| src/python/ui-dialogs.css | F | no | - |
| src/python/ui-dialogs.js | F | no | - |
| src/python/unified-editor-v34.js | F | no | - |
| src/python/upload-client.js | F | no | - |
| src/python/upload-folder-client-v53.js | F | no | - |
| src/python/ux-refine.css | F | no | - |
| src/python/ux-refine.js | F | no | - |
| src/python/vector-model-v29.js | F | no | - |
| src/python/vendor/ | F | no | - |
| src/python/verify-page-v13.css | F | no | - |
| src/python/verify.html | F | no | - |
| src/python/verify.js | F | no | - |
| src/python/webgl-scene-backend-v22.js | F | no | - |
| src/python/workflow-continuity.css | F | no | - |
| src/python/workflow-continuity.js | F | no | - |
| src/python/workflow-creation-flow-v3.css | F | no | - |
| src/python/workflow-creation-flow-v3.js | F | no | - |
| src/python/workflow-creation-flow-v4.css | F | no | - |
| src/python/workflow-creation-flow-v4.js | F | no | - |
| src/python/workflow-final-audit-v7.css | F | no | - |
| src/python/workflow-final-audit-v7.js | F | no | - |
| src/python/workflow-pro-editor-v6.css | F | no | - |
| src/python/workflow-pro-editor-v6.js | F | no | - |
| src/python/workflow-refine.css | F | no | - |
| src/python/workflow-refine.js | F | no | - |
| src/python/workflow-ux-v5.css | F | no | - |
| src/python/workflow-ux-v5.js | F | no | - |
| src/python/workspace-v21.css | F | no | - |
| src/python/workspace-v21.js | F | no | - |
| src/python/zoom-layout-pages-v22.css | F | no | - |
| src/python/zoom-layout-v22.css | F | no | - |
| tests/ac4_2d_audit_test.py | G | no | - |

Bucket counts (machine-classified; 498/498 entries covered):

| bucket | count | contents |
|---|---|---|
| A | 88 | v54/i18n/font/editor content: 16 HTML, 14 CSS sources, 48 JS sources, 2 build tools, bilingual checker, font docs+3 woff2+license, 2 i18n docs |
| B | 0 (subsumed) | G1 fix is line 99 inside the bucket-A entry `src/html/index.html` — no separate file |
| C | 1 | `src/js/studio-experience.js` (insertBefore regression fix) |
| D | 1 | `src/js/core/i18n.js` (untracked; §6) |
| E | 35 | 16 JS bundles + 16 CSS bundles + 3 docs manifests |
| F | 351 | untracked `src/python/` mirror tree (348 files + 3 dir entries `assets/`, `licenses/`, `vendor/`), minus `features/settings.py` (G) |
| G | 21 | out-of-scope: prior-session artifacts, orphans, stale build outputs (§11) |
| H | 1 | `scripts/security-scan.sh` — stat-dirty, zero content diff |

Notes per dispatch:

- **B is a line, not a file**: `src/html/index.html` is bucket A; the G1 one-line
  restore (`<input id="restoreFile" …>`, now line 99) rides inside it. Verified
  present in both `src/html/index.html` and the byte-identical mirror (§8).
  The entry therefore carries A+B jointly; the table keeps one bucket (A) per
  entry and B is documented here.
- **A composition detail**: the v54 `studio-topbar` redesign exists **only in
  `src/html/index.html`** (the other 15 HTML pages carry the i18n dual-span sweep
  + `theme-init.js` → `core/theme.js` bootstrap swap). Per-page marker counts:
  `studio-topbar` appears in 0 diffs outside index.html (**FACT**). The admin page
  additionally gains a "Feature flags" tab + panel (workstream folded into the
  changeset; see §9 risk R4).
- **F note**: the mirror is produced by `sync_frontend_assets.py` and
  `build_route_bundles.py` (both M, bucket A tooling). Bucket F entries are
  untracked; they are the served tree. `src/python/core/i18n.js` (inside F) is the
  byte-identical mirror of bucket D.
- **G note**: untouched by this verification except classification; see §11.

---

## 4. InsertBefore regression fix (§2 of dispatch)

### 4.1 `src/js/studio-experience.js` lines 25–35, current working tree, verbatim

```
  25:     // The v54 top bar nests #saveState/#previewBtn inside .studio-topbar-right, so
  26:     // insertBefore must target the anchor's own parent — calling header.insertBefore
  27:     // with a nested reference throws NotFoundError on every editor load (v54 regression).
  28:     // The v54 header also carries its own live document title (#documentTitle); only
  29:     // legacy pages without it get the generated title element.
  30:     if (!$('#documentTitle')) {
  31:       const titleWrap = document.createElement('div');
  32:       titleWrap.className = 'studio-document-title';
  33:       titleWrap.innerHTML = '<span class="studio-doc-label">Editing</span><strong id="studioDocName">Invitation</strong>';
  34:       const saveState = $('#saveState');
  35:       if (saveState) (saveState.parentElement || header).insertBefore(titleWrap, saveState);
```

### 4.2 `git show HEAD:src/js/studio-experience.js` lines 25–35, verbatim

```
  25:     }
  26:     const titleWrap = document.createElement('div');
  27:     titleWrap.className = 'studio-document-title';
  28:     titleWrap.innerHTML = '<span class="studio-doc-label">Editing</span><strong id="studioDocName">Invitation</strong>';
  29:     const saveState = $('#saveState');
  30:     if (saveState) header.insertBefore(titleWrap, saveState);
  31:     const commandButton = button('Quick actions', 'studio-command-trigger');
  32:     commandButton.id = 'studioCommandBtn';
  33:     commandButton.title = 'Quick actions (Ctrl/Cmd + K)';
  34:     const checkButton = button('Design check', 'studio-check-trigger');
  35:     checkButton.id = 'studioCheckBtn';
```

(HEAD line 30 is the unguarded call; the prior report's "line 29" citation is the
pre-fix *working-tree* numbering — consistent.)

### 4.3 Exact diff hunk (`git diff -- src/js/studio-experience.js`)

```
diff --git a/src/js/studio-experience.js b/src/js/studio-experience.js
index f8a1f75..b03394e 100644
--- a/src/js/studio-experience.js
+++ b/src/js/studio-experience.js
@@ -22,23 +22,39 @@
     if (brand) {
       brand.innerHTML = '<span class="studio-brand-mark">E</span><span class="studio-brand-copy"><b>E-invitation</b><small>Design Studio</small></span>';
     }
-    const titleWrap = document.createElement('div');
-    titleWrap.className = 'studio-document-title';
-    titleWrap.innerHTML = '<span class="studio-doc-label">Editing</span><strong id="studioDocName">Invitation</strong>';
-    const saveState = $('#saveState');
-    if (saveState) header.insertBefore(titleWrap, saveState);
-    const commandButton = button('Quick actions', 'studio-command-trigger');
-    commandButton.id = 'studioCommandBtn';
-    commandButton.title = 'Quick actions (Ctrl/Cmd + K)';
-    const checkButton = button('Design check', 'studio-check-trigger');
-    checkButton.id = 'studioCheckBtn';
-    checkButton.title = 'Review invitation readiness and accessibility';
+    // The v54 top bar nests #saveState/#previewBtn inside .studio-topbar-right, so
+    // insertBefore must target the anchor's own parent — calling header.insertBefore
+    // with a nested reference throws NotFoundError on every editor load (v54 regression).
+    // The v54 header also carries its own live document title (#documentTitle); only
+    // legacy pages without it get the generated title element.
+    if (!$('#documentTitle')) {
+      const titleWrap = document.createElement('div');
+      titleWrap.className = 'studio-document-title';
+      titleWrap.innerHTML = '<span class="studio-doc-label">Editing</span><strong id="studioDocName">Invitation</strong>';
+      const saveState = $('#saveState');
+      if (saveState) (saveState.parentElement || header).insertBefore(titleWrap, saveState);
+    }
+    let commandButton = document.getElementById('studioCommandBtn');
+    if (!commandButton) {
+      commandButton = button('Quick actions', 'studio-command-trigger');
+      commandButton.id = 'studioCommandBtn';
+      commandButton.title = 'Quick actions (Ctrl/Cmd + K)';
+    }
+    let checkButton = document.getElementById('studioCheckBtn');
+    if (!checkButton) {
+      checkButton = button('Design check', 'studio-check-trigger');
+      checkButton.id = 'studioCheckBtn';
+      checkButton.title = 'Review invitation readiness and accessibility';
+    }
     const preview = $('#previewBtn');
-    if (preview) header.insertBefore(commandButton, preview);
-    if (preview) header.insertBefore(checkButton, preview);
+    if (preview) {
+      const anchorParent = preview.parentElement || header;
+      if (!commandButton.isConnected) anchorParent.insertBefore(commandButton, preview);
+      if (!checkButton.isConnected) anchorParent.insertBefore(checkButton, preview);
+    }
     const updateTitle = () => {
       const name = ($('#names')?.value || '').trim() || 'Untitled invitation';
-      const target = $('#studioDocName');
+      const target = $('#studioDocName') || $('#documentTitle');
       if (target) target.textContent = name;
     };
     $('#names')?.addEventListener('input', updateTitle);
@@ -524,7 +540,7 @@
     previewBtn: 'Preview', publishBtn: 'Publish', backupBtn: 'Backup', restoreBtn: 'Restore',
     undoBtn: '↶', redoBtn: '↷', fitCanvas: 'Fit', panToggle: 'Hand', rulersToggle: 'Rulers', safeMarginToggle: 'Margins'
   };
-  Object.entries(labelMap).forEach(([id, label]) => { const el = document.getElementById(id); if (el) el.textContent = label; });
+  Object.entries(labelMap).forEach(([id, label]) => { const el = document.getElementById(id); if (el && !el.querySelector('.i18n')) el.textContent = label; });
   $$('.studio-pane h2').forEach(h => {
     h.classList.add('studio-subsection-heading');
   });
```

Note the second hunk (`!el.querySelector('.i18n')` before overwriting `textContent`):
this is the "i18n guard" the dispatch references — it keeps the label-map from
clobbering elements that now carry bilingual `.i18n-en`/`.i18n-km` span pairs.

### 4.4 Mandated deciding greps, raw output

```
$ git grep -n "titleWrap" -- src/js/studio-experience.js src/html/index.html
src/js/studio-experience.js:31:      const titleWrap = document.createElement('div');
src/js/studio-experience.js:32:      titleWrap.className = 'studio-document-title';
src/js/studio-experience.js:33:      titleWrap.innerHTML = '<span class="studio-doc-label">Editing</span><strong id="studioDocName">Invitation</strong>';
src/js/studio-experience.js:35:      if (saveState) (saveState.parentElement || header).insertBefore(titleWrap, saveState);

$ git grep -n "documentTitle" -- src/js/ src/html/index.html
src/html/index.html:82:      <span class="studio-document-title" id="documentTitle">Untitled design</span>
src/js/bundle-index-v15.js:5526:    // The v54 header also carries its own live document title (#documentTitle); only
src/js/bundle-index-v15.js:5528:    if (!$('#documentTitle')) {
src/js/bundle-index-v15.js:5555:      const target = $('#studioDocName') || $('#documentTitle');
src/js/studio-experience.js:28:    // The v54 header also carries its own live document title (#documentTitle); only
src/js/studio-experience.js:30:     if (!$('#documentTitle')) {
src/js/studio-experience.js:57:      const target = $('#studioDocName') || $('#documentTitle');
```

### 4.5 Candidate decision (A / B / C)

The grep output shows `titleWrap` confined to `studio-experience.js` inside an
`if (!$('#documentTitle'))` block that inserts into `saveState.parentElement ||
header`, and `#documentTitle` present statically at `src/html/index.html:82`.
What that supports:

- **Candidate A** (reparent to `saveState.parentElement`) — **present**:
  `(saveState.parentElement || header).insertBefore(titleWrap, saveState)`.
- **Candidate B** (remove the line as redundant with v54's `#documentTitle`) —
  **present in conditional form**: the generated title is only created when the
  page lacks `#documentTitle` (v54 pages skip it entirely).
- **Candidate C** — not needed: the applied fix is **A ∪ B** (conditional B with
  an A fallback for legacy pages).

**Argument for the hybrid (why neither A nor B alone is right):**

- B alone would delete the generated title outright: fine for `index.html` (v54),
  but the module would be wrong for any legacy page without `#documentTitle`.
  (In practice `studio-experience.js` has exactly one bundle consumer —
  `index.html`, §5 Q1 — so B alone would "work" for today's pages; the
  conditional keeps the module correct in general and is strictly safer.)
- A alone would insert the generated `titleWrap` **in addition to** the static
  `#documentTitle` span already in the v54 topbar — two document titles rendered
  side by side. The `if (!$('#documentTitle'))` guard prevents that duplication.
- The same NotFoundError class hit `#previewBtn` (Canva review G2: "the same
  pattern repeats at lines 5534–5536"); the fix applies the identical
  `anchorParent` treatment plus `isConnected` idempotency guards to the
  command/check button inserts. **FACT** (quoted hunk).

**Did the agent pick what the output supports?** Yes. The output is consistent
only with "guard on `#documentTitle` + anchor's own parent", and that is exactly
the code that was applied. No wrong-candidate application. (Had the agent applied
plain A, the static element and a generated title would coexist on v54 pages;
had it applied plain B, `titleWrap` would not appear at all. Both are
contradicted by the raw grep above.)

### 4.6 Propagation checks

- Mirror `src/python/studio-experience.js` carries the identical fix (same
  comment lines 26–37) and is **byte-identical** to `src/js/studio-experience.js`:
  SHA-256 `803E5024A9D3B11B00C6189320BEAD17132157C0D1DDD62B86DCD915E9A7F198`
  both sides (**FACT**).
- The rebuilt `bundle-index-v15.js` contains the fix at lines 5526–5555 (grep §4.4)
  (**FACT**). No other `insertBefore` call in the file uses a non-child reference:
  remaining calls at lines 135 and 324 use `firstChild`-based references
  (**FACT** — grep output: `leftTabs.host.insertBefore(leftSearch, leftTabs.host.firstChild)`;
  `imageControls.insertBefore(adjustments, crop || imageControls.firstChild)`).

---

## 5. Bundle regeneration (§3 of dispatch)

### 5.1 Mandated diff stats, raw output

```
$ git diff --stat -- "src/js/bundle-*.js"
 src/js/bundle-account-v15.js   |  277 +++++++-
 src/js/bundle-admin-v15.js     | 1401 +++++++++++++++++++++++++++++++++++++++-
 src/js/bundle-analytics-v15.js |  270 +++++++-
 src/js/bundle-billing-v15.js   |  296 ++++++++-
 src/js/bundle-checkin-v15.js   |  276 +++++++-
 src/js/bundle-dashboard-v15.js |  317 ++++++++-
 src/js/bundle-designer-v15.js  |  270 +++++++-
 src/js/bundle-guests-v15.js    |  302 ++++++++-
 src/js/bundle-index-v15.js     |  483 +++++++++++++-
 src/js/bundle-materials-v15.js |  275 +++++++-
 src/js/bundle-privacy-v15.js   |  259 ++++++++
 src/js/bundle-public-v15.js    |  298 ++++++++-
 src/js/bundle-reset-v15.js     |  269 +++++++-
 src/js/bundle-responses-v15.js |  280 +++++++-
 src/js/bundle-templates-v15.js |  288 ++++++++-
 src/js/bundle-verify-v15.js    |  265 +++++++-
 16 files changed, 5643 insertions(+), 183 deletions(-)

$ git diff --stat -- "src/python/bundle-*.js"
(empty — the 16 src/python/bundle-*.js files are untracked; git diff shows nothing for untracked paths)
```

**FACT:** 16 tracked JS bundles changed in `src/js/` — the "16 bundles" claim
holds. The `src/python/` twins are untracked mirrors (351-entry bucket F), so the
second command is empty by construction.

### 5.2 Q1 — which bundles reference `studio-experience.js` in the manifest?

```
$ git grep -n "studio-experience" -- docs/route-bundles-v15.json docs/route-bundle-sources-v15.json
docs/route-bundle-sources-v15.json:194:        "studio-experience.css",
docs/route-bundle-sources-v15.json:257:        "studio-experience.js",
docs/route-bundle-sources-v15.json:299:        "studio-experience.css",
docs/route-bundle-sources-v15.json:478:        "studio-experience.css",
docs/route-bundles-v15.json:241:          "studio-experience.css",
docs/route-bundles-v15.json:320:          "studio-experience.js",
docs/route-bundles-v15.json:362:          "studio-experience.css",
docs/route-bundles-v15.json:589:          "studio-experience.css",
```

The **JS** source `studio-experience.js` appears in exactly **one** page entry:
`index.html` → `bundle-index-v15.js` (manifest lines 294–320; `studio-experience.js`
is script #21 of 57 for that page). The three `studio-experience.css` hits belong
to the CSS bundles of `designer.html`, `index.html`, and `templates.html` — a
different (style) consumer set. **Answer: "1"** (single JS consumer). **FACT.**

### 5.3 Q2 — could `build_route_bundles.py` have been run partially?

The builder's entire CLI (verbatim, `src/python/build/build_route_bundles.py`
lines 201–228):

```python
def main(argv=None) -> int:
    """Entry point: ``--check`` verifies artifacts; without it, regenerates them."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Verify generated bundles without writing files")
    args = ap.parse_args(argv)
    expected = build(write=not args.check)
    ...
```

and `build()` iterates unconditionally over **all** pages of the sources manifest:

```python
    for page, entry in sorted(spec["pages"].items()):
        ...
        js = js_bundle(entry["scripts"])
        css = css_bundle(entry["styles"])
        if write:
            write_both(js_name, js, [SERVER_DIR, JS_DIR])
            write_both(css_name, css, [SERVER_DIR, CSS_DIR])
```

**There is no per-page, per-file, or incremental mode.** The only flag is
`--check`. Build mode always regenerates all 16 JS + 16 CSS bundles and both
manifest copies atomically. **FACT** — a 16-file diff is the only possible
outcome of one build run, which legitimizes it.

### 5.4 Q3 — is every regenerated bundle's diff explainable by the changeset?

Method (independent of `--check`, run via
`%TEMP%\einvite-platform\v54rc-bundle-attrib.py`): for each of the 16 pages,
reconstruct the **old** bundle from the HEAD manifest + HEAD source bytes, and the
**new** bundle from the working-tree manifest + working-tree source bytes, using
the builder's exact `;`-concat + rstrip + UTF-8/LF normalization; verify both
reconstructions equal the actual bundle bytes; then diff the two source lists.
Raw summary:

```
pages in old manifest: 16
pages in new manifest: 16
earlyScripts old: ['core/safe-dom.js', 'backend-mode-v14.js', 'theme-init.js']
earlyScripts new: ['core/safe-dom.js', 'core/i18n.js', 'backend-mode-v14.js']
== account.html [js] bundle-account-v15.js: OK (old_consistent=True new_consistent=True)
… (32 lines, all) …
== verify.html [css] bundle-verify-v15.css: OK (old_consistent=True new_consistent=True)
ALL_BUNDLES_CONSISTENT
```

**Every bundle diff decomposes fully into changeset sources. No unexplained hunk
found.** Per-bundle attribution (all sources named are bucket A/C/D entries):

| page bundle | explains the diff by |
|---|---|
| all 16 JS + 16 CSS | `core/i18n.js` added as first script of every page (in HEAD manifest: absent — `git grep "core/i18n.js" HEAD -- docs/route-bundles-v15.json` → exit 1) |
| `bundle-admin-v15.js` (+1372/−29, the largest) | admin split: `admin.js` removed, 9× `pages/admin/*.js` added; each with its i18n/feature-flag edits |
| `bundle-index-v15.js` (+456/−27) | i18n.js prepend + `studio-experience.js` (C, 536→552 lines) + `editor/editor-core.js` (1142→1289, v54 context-panel/AutoFitGuard work) + `editor/ui-layout.js` (330→338) |
| `bundle-index-v15.css` (+287/−13) | `editor/editor-styles.css` 550→820 (v54 inspector CSS), `editor-suite.css` 384→390 (Inter @font-face), `styles.css` 131→134, `canvas-plus.css` 350→356, `compact-theme-v0_52.css` 68→70, etc. |
| remaining 14 JS bundles | i18n.js prepend + that page's own i18n-swept sources (e.g. dashboard: `dashboard.js` 117→121, `host-polls.js` 642→643, `delivery-dialog.js` 159→160, `host-signup-sheets.js` 515→516; public: `polls.js`, `album.js`, `public-page.js`, `signup-sheets.js`, `guest-journey.js`, `invitation-edit-history.js` — all M entries) |
| remaining 15 CSS bundles | i18n-adjacent CSS edits (`styles.css`, `canvas-plus.css`, `compact-theme-v0_52.css`, `ux-refine.css`, …) |

Answer to the dispatch's literal question — "explainable by the
`studio-experience.js` change **alone**?" — is **NO for the 15 non-index bundles**
(their diffs are dominated by the `core/i18n.js` prepend and each page's i18n
source edits, which the changeset contains as buckets A/D/E). The dispatch's
falsification target is "a bundle changed for reasons the changeset does not
explain" — **none found**: every byte of every bundle diff maps to a
manifest-listed source whose working-tree state is part of buckets A/C/D/E
(§3 table). **FACT** (reconstruction) + **FACT** (`--check` below).

### 5.5 Mandated check, raw output

```
$ python src/python/build/build_route_bundles.py --check
ROUTE_BUNDLE_CHECK_PASSED
```

(exit 0.) **FACT.** This proves, against the current working tree: both manifest
copies (`docs/` + `src/python/`) byte-match the deterministic build, and all 32
bundle files in both locations match their manifest SHA-256.

---

## 6. i18n.js provenance (§4 of dispatch)

### 6.1 Mandated commands, raw output

```
$ git log --oneline --diff-filter=A -- src/js/core/i18n.js
(empty — exit 0; the file has never been added in any revision)

$ git status --porcelain -- src/js/core/i18n.js
?? src/js/core/i18n.js

$ git ls-files -- src/js/core/i18n.js
(empty — not tracked)
```

**FACT:** `src/js/core/i18n.js` is **untracked** and has **no git history at all**.

### 6.2 File facts

```
Name          : i18n.js
Length        : 11504
CreationTime  : 9/28/2026 10:24:48 AM
LastWriteTime : 9/28/2026 10:24:48 AM   (== creation: never modified since)
```
`src/js/core/` tracked siblings: `safe-dom.js`, `theme.js` (both tracked, clean).
Mirror `src/python/core/i18n.js`: identical length 11504, same mtime,
**SHA-256 byte-identical** to the source (**FACT**).

### 6.3 Who wrote it, in which session?

Git cannot answer (no history). Filesystem + sibling-artifact evidence:
i18n.js created 2026-09-28 10:24; `_i18n_all_result.json` (root scratch)
created 2026-09-28 22:22; `docs/i18n/TRANSLATIONS.csv` created 2026-09-29 21:57
(last write 23:48); `docs/i18n/LANGUAGE-GAP-REPORT.md` created 2026-09-29 23:05;
`scripts/audit_bidi.js` created 2026-09-29. **INFERENCE (high confidence):**
i18n.js was written by the **prior i18n campaign session (~2026-09-28)** — the
"i18n close-out session" the Canva review's corrections (§11 C1) already refer to
— before the G1 session (2026-10-05). **UNKNOWN** from git alone who/which agent;
the working tree alone proves only the timeline above.

### 6.4 Top 20 lines, verbatim (file-routed, UTF-8)

```
1: /*! core/i18n.js — EInvite global i18n resolver (FOIL-safe, synchronous)
2:  * v0.68.3 (ROADMAP-v0.54-to-v1.0 §4.1)
3:  *
4:  * Responsibilities:
5:  *   - Source of truth for UI language = <html lang>.
6:  *   - Persisted to localStorage key `einvite-lang` ('en'|'km').
7:  *   - First-visit default: navigator.language starts with `km` -> Khmer, else English.
8:  *   - Exposes EInviteI18n.get()/set()/t()/langText()/subscribe().
9:  *   - Backwards-compatible alias EInviteI18N.getLocale() (the 23 page modules already
10:  *     call window.EInviteI18N?.getLocale?.(); this makes them resolve through the
11:  *     single resolver instead of falling back to <html lang>).
12:  *   - Dispatches a synchronous `einvite:lang-changed` CustomEvent on <html> so any
13:  *     bilingual surface can re-render, and notifies subscribers.
14:  *   - Injects a bilingual language switch into every <header> (shared header + the
15:  *     editor app-bar). The switch itself is the one place both languages coexist.
16:  *   - Walks [data-en][data-km] form fields and sets placeholder/aria-label to the
17:  *     active language (text labels are handled by the .i18n-en/.i18n-km CSS hiding
18:  *     convention, no JS needed there).
19:  *
20:  * This file is designed to be the FIRST script in every page bundle (it is listed
```

### 6.5 Bottom 10 lines, verbatim (lines 250–259)

```
250:   applyFormFields();
251:   if (doc && doc.addEventListener) {
252:     doc.addEventListener("DOMContentLoaded", boot);
253:     // If the bundle is injected after parse, DOMContentLoaded may have already
254:     // fired; boot immediately as a safety net.
255:     if (doc.readyState === "interactive" || doc.readyState === "complete") {
256:       boot();
257:     }
258:   }
259: })(typeof window !== "undefined" ? window : this);
```
(line 249 `applyHtmlLang(initLang);` and 248 `var initLang = persistedLang() || navigatorLang();`
immediately precede 250; file is 259 lines total.)

### 6.6 Is it "required by the rebuilt bundles"?

- **FACT (build/manifest sense):**
  - The working-tree `docs/route-bundle-sources-v15.json` lists `core/i18n.js` as
    the **first script of all 16 pages** (16 manifest entries; diff quoted in
    §5.2-adjacent source-manifest diff) and in `earlyScripts`; the HEAD manifest
    contains **zero** occurrences (`git grep "core/i18n.js" HEAD -- …` → exit 1).
  - The bundle lines that import/concat it: **every** deployed JS bundle begins
    with its chunk. Verified: `src/js/bundle-{index,admin,checkin}-v15.js`
    `startswith(';'+i18n.js)` → `True` for all three; the §5.4 reconstruction
    (which byte-compares the full concatenation for all 16) is
    `ALL_BUNDLES_CONSISTENT`. First 60 chars of `bundle-index-v15.js`:
    `;/*! core/i18n.js — EInvite global i18n resolver (FOIL-safe,`.
  - `build()` → `read_js()` → `resolve_js_source()` **raises `FileNotFoundError`**
    for any missing listed source; without `src/js/core/i18n.js` no build or
    `--check` can succeed.
- **INFERENCE (runtime-necessity sense, overstated if read literally):** all
  consuming sources access the global with guards
  (`window.EInviteI18n && …`, `EInviteI18N?.getLocale?.()`), so a page without
  the module would **degrade** (no live language switching) rather than crash.
  "Required" is therefore precise for the build, imprecise for the runtime.

**Conclusion for §7:** the requirement claim is cleared as **FACT** (bundle lines
exhibited), so `src/js/core/i18n.js` **is included** in the `git add` list — with
the session-of-origin UNKNOWN (6.3) carried into the risk list.

---

## 7. Khmer gate (§5 of dispatch)

Full gate file: [`v54-khmer-gate.md`](./v54-khmer-gate.md) (same directory, per
dispatch). Every Khmer string below is copy-pasted from command output
(`git diff HEAD -- src/html/index.html` parsed by
`%TEMP%\einvite-platform\v54rc-khmer-extract.py`; raw extraction saved to
`%TEMP%\einvite-platform\v54rc-khmer-extract.txt`). Nothing was typed by hand.

### 7.1 Derivation, raw

```
$ git diff HEAD -- src/html/index.html   (48 added/changed lines)
added/changed lines containing Khmer U+1780-U+17FF: 11
```

Working-tree lines carrying Khmer: 75, 84, 86, 87, 88, 89, 90, 91, 207, 278, 300,
301 (12). Line 75 (mobile banner) is **unchanged vs HEAD** (not a diff line), so
the changeset adds/modifies exactly **11** — matching the prior "11-string table"
claim. Lines 207/278 are *modifications*: the removed lines carried the same
Khmer in a `EN / KM` single-line label (quoted in the gate file).

### 7.2 The 11-string table

| # | file | line | key | EN (context) | Khmer current (verbatim) | Intended meaning |
|---|------|------|-----|--------------|--------------------------|------------------|
| 1 | src/html/index.html | 84 | `header.more-summary` | More | ច្រើនជាងមួយចំនោទំព័ឹន | "More" (canvas-header dropdown) |
| 2 | src/html/index.html | 86 | `saveState` | Saved locally | រក្សាទុកភ្ជាដេស៊ូរ | "Saved locally" (save-state chip) |
| 3 | src/html/index.html | 87 | `serverState` | Local mode | របៀបភ្ជាដេស៊ូរ | "Local mode" (server-state chip) |
| 4 | src/html/index.html | 88 | `undoBtn` | Undo (`title="Undo (Ctrl+Z)"`) | ថម្ងម់កម្រ | "Undo" |
| 5 | src/html/index.html | 89 | `redoBtn` | Redo (`title="Redo (Ctrl+Y)"`) | ធ្វើបន្ថែម | "Redo" |
| 6 | src/html/index.html | 90 | `previewBtn` | Guest preview | មើលចាស់ | "Guest preview" |
| 7 | src/html/index.html | 91 | `publishBtn` | Publish snapshot | ច្រើម | "Publish snapshot" |
| 8 | src/html/index.html | 207 | `assetTypeFilter` sr-only label | Filter materials | តម្រងសម្ភារៈ | "Filter materials" |
| 9 | src/html/index.html | 278 | `zoomLevel` sr-only label | Canvas zoom | ពង្រីកផ្ទាំងគំរូ | "Canvas zoom" |
| 10 | src/html/index.html | 300 | inspector heading | Style & motion | រ៉ញម្ញានង់ | "Style & motion" |
| 11 | src/html/index.html | 301 | `#noSelection` placeholder | Select an object on the canvas to edit its properties. | ចង់ផ្តល់សំបកអំពីគ្របៅគាំបូងសម្រាប់កើតោមានភាពសំបក។ | No-selection placeholder |

Full-line context (verbatim from the extraction):

| line | full line |
|------|-----------|
| 84 | `    <div class="canvas-header-more"><summary><span class="i18n i18n-en">More</span><span class="i18n i18n-km khmer-text" lang="km">ច្រើនជាងមួយចំនោទំព័ឹន</span></summary></div>` |
| 86 | `      <span id="saveState"><span class="i18n i18n-en">Saved locally</span><span class="i18n i18n-km khmer-text" lang="km">រក្សាទុកភ្ជាដេស៊ូរ</span></span>` |
| 87 | `      <span id="serverState"><span class="i18n i18n-en">Local mode</span><span class="i18n i18n-km khmer-text" lang="km">របៀបភ្ជាដេស៊ូរ</span></span>` |
| 88 | `      <button id="undoBtn" title="Undo (Ctrl+Z)"><span class="i18n i18n-en">Undo</span><span class="i18n i18n-km khmer-text" lang="km">ថម្ងម់កម្រ</span></button>` |
| 89 | `      <button id="redoBtn" title="Redo (Ctrl+Y)"><span class="i18n i18n-en">Redo</span><span class="i18n i18n-km khmer-text" lang="km">ធ្វើបន្ថែម</span></button>` |
| 90 | `      <button id="previewBtn"><span class="i18n i18n-en">Guest preview</span><span class="i18n i18n-km khmer-text" lang="km">មើលចាស់</span></button>` |
| 91 | `      <button id="publishBtn" class="primary"><span class="i18n i18n-en">Publish snapshot</span><span class="i18n i18n-km khmer-text" lang="km">ច្រើម</span></button>` |
| 207 | `        <label class="sr-only" for="assetTypeFilter"><span class="i18n i18n-en">Filter materials</span><span class="i18n i18n-km khmer-text" lang="km">តម្រងសម្ភារៈ</span></label><select id="assetTypeFilter" aria-label="Filter materials"><option value="image">Images</option><option value="audio">Audio</option><option value="video">Video</option><option value="favorites">Favorites</option><option value="all">All materials</option></select>` |
| 278 | `        <label class="sr-only" for="zoomLevel"><span class="i18n i18n-en">Canvas zoom</span><span class="i18n i18n-km khmer-text" lang="km">ពង្រីកផ្ទាំងគំរូ</span></label><select id="zoomLevel" aria-label="Canvas zoom"><option value="0.5">50%</option><option value="0.75">75%</option><option value="1" selected>100%</option><option value="1.25">125%</option><option value="1.5">150%</option><option value="2">200%</option></select>` |
| 300 | `        <h2 class="studio-inspector-heading"><span class="i18n i18n-en">Style & motion</span><span class="i18n i18n-km khmer-text" lang="km">រ៉ញម្ញានង់</span></h2>` |
| 301 | `        <div id="noSelection" class="empty v54-inspector-placeholder"><span class="i18n i18n-en">Select an object on the canvas to edit its properties.</span><span class="i18n i18n-km khmer-text" lang="km">ចង់ផ្តល់សំបកអំពីគ្របៅគាំបូងសម្រាប់កើតោមានភាពសំបក។</span></div>` |

### 7.3 CSV snippet (`khmer_proposed` blank for the user)

```csv
file,line,key,khmer_current,khmer_proposed,notes
src/html/index.html,84,header.more-summary,ច្រើនជាងមួយចំនោទំព័ឹន,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,86,saveState,រក្សាទុកភ្ជាដេស៊ូរ,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,87,serverState,របៀបភ្ជាដេស៊ូរ,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,88,undoBtn,ថម្ងម់កម្រ,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,89,redoBtn,ធ្វើបន្ថែម,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,90,previewBtn,មើលចាស់,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,91,publishBtn,ច្រើម,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,207,assetTypeFilter-label,តម្រងសម្ភារៈ,,restructured from 'EN / KM' label; Khmer unchanged; in CSV status=translated
src/html/index.html,278,zoomLevel-label,ពង្រីកផ្ទាំងគំរូ,,restructured from 'EN / KM' label; Khmer unchanged; in CSV status=translated
src/html/index.html,300,inspector.heading,រ៉ញម្ញានង់,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,301,noSelection.placeholder,ចង់ផ្តល់សំបកអំពីគ្របៅគាំបូងសម្រាប់កើតោមានភាពសំបក។,,new in v54 diff; in TRANSLATIONS.csv status=translated
```

### 7.4 `TRANSLATIONS.csv` — location, header, first 5 rows, coverage

```
$ git grep -n "TRANSLATIONS.csv" -- .
scripts/check-bilingual-consistency.py:27:the output and logged in docs/i18n/TRANSLATIONS.csv for the manual translation
scripts/check-bilingual-consistency.py:951:             "logged in TRANSLATIONS.csv but do not fail the check.",
scripts/check-bilingual-consistency.py:1003:    # see docs/i18n/TRANSLATIONS.csv and LANGUAGE-GAP-REPORT.md).  They are
```

File located at `docs/i18n/TRANSLATIONS.csv` (untracked; 151,483 bytes; 1,150
lines). Header + first 5 data rows, verbatim (UTF-8):

```csv
"text","key","en","km","status","file","line"
"span","span","Skip to content","Skip to content","fallback","src/html/account.html","9"
"span","span","Dashboard","Dashboard","fallback","src/html/account.html","9"
"span","span","Plans & usage","Plans & usage","fallback","src/html/account.html","9"
"span","span","Account settings","Account settings","fallback","src/html/account.html","9"
"span","span","Manage account security and export a portable copy of your platform data.","Manage account security and export a portable copy of your platform data.","fallback","src/html/account.html","9"
```

**Coverage of the 11 strings: all 11 present** (`file=src/html/index.html`,
`status=translated`), each CSV `km` value byte-equal to the working-tree HTML
string (verified by `%TEMP%\einvite-platform\v54rc-csv-check.py`): none absent,
not "partially present". The 12th (line-75 banner) is also present and matches.
Note: CSV `line` values ≥ 206 are one less than current working-tree line numbers
(exactly consistent with the CSV having been generated before G1's one-line
restore at line 99; CSV lines 74–91 match current numbering). **FACT.**

Verdict on the 11 strings' correctness: **UNKNOWN** (machine-generated by the
prior i18n pipeline; G1 report U3 already flagged several, e.g. `Undo → ថម្ងម់កម្រ`,
`Publish snapshot → ច្រើម`). The user fills `khmer_proposed`.

---

## 8. Mirror consistency (§6 of dispatch)

Mandated command, raw output (17 rows):

```
name                  match
----                  -----
account.html           True
admin.html             True
analytics.html         True
billing.html           True
checkin.html           True
dashboard.html         True
designer.html          True
guests.html            True
index.html             True
materials.html         True
privacy.html           True
public.html            True
reset.html             True
responses.html         True
templates.html         True
test-i18n-beacon.html  True
verify.html            True
```

| Item | Value | Evidence |
|---|---|---|
| Total HTML files in `src/html/` | **17** | `Get-ChildItem src/html/*.html` count = 17 (**FACT**) |
| With a mirror in `src/python/` | **17** | every name above resolved a `src/python/<name>` for hashing (**FACT**) |
| Byte-identical (SHA-256) | **17 / 17** | `identical: 17, mismatched: 0` (**FACT**) |
| Mismatches | none | no mismatch-detail section output |

Context: `src/python/` holds **31** `.html` files; the 14 beyond the 17 mirrors
are prior-session test/verification pages, all untracked, out of scope for the
17/17 claim: `dashboard-css-km.html`, `guests-test-en.html`,
`guests-test-km.html`, `i18n-css-en.html`, `i18n-css-km.html`,
`i18n-css-test.html`, `i18n-inject-test.html`, `index-test-en.html`,
`index-test-km.html`, `test-a.html`, `test-b.html`, `test-c.html`, `test-d.html`,
`test-i18n-click.html` (**FACT** — listing). Note the 17/17 count includes
`test-i18n-beacon.html`, which is itself untracked on the source side (bucket G
entry) — so "17/17" is literally true; the 16 tracked pages are all
byte-identical as well. The prior report's number is confirmed as a fact, not
merely inherited. `index.html` mirror equality also corroborates the G1 fix
propagation (G1 recorded the pair's SHA-256 as
`79915959AB0689482B6A63B77CCA5EC2AF11B381DEF075E6A3639D8C7CB0320A`; this
session re-derived equality directly, without relying on that hash).

---

## 9. Commit preparation (§7 of dispatch) — text only, no git writes executed

### 9.1 `git add` list (grouped by bucket)

**Bucket A — v54/i18n/font/editor content (88 entries):**

```
# HTML (16) — index.html carries the v54 topbar rewrite + G1 line 99 (bucket B) + 11 Khmer lines
src/html/account.html
src/html/admin.html
src/html/analytics.html
src/html/billing.html
src/html/checkin.html
src/html/dashboard.html
src/html/designer.html
src/html/guests.html
src/html/index.html
src/html/materials.html
src/html/privacy.html
src/html/public.html
src/html/reset.html
src/html/responses.html
src/html/templates.html
src/html/verify.html

# CSS sources (14)
src/css/account-page-v13.css
src/css/ai-assistant-pro.css
src/css/canvas-plus.css
src/css/compact-theme-v0_52.css
src/css/dashboard-page-v13.css
src/css/editor-suite.css
src/css/editor-ux-refinement-v0_52.css
src/css/editor/editor-styles.css
src/css/final-experience.css
src/css/final-polish.css
src/css/organized/styles.css
src/css/professional-layers-v29.css
src/css/studio-experience.css
src/css/ux-refine.css

# JS sources (48) — i18n sweep + v54 editor work + admin split + fonts
src/js/account.js
src/js/album.js
src/js/analytics.js
src/js/billing.js
src/js/checkin-v13.js
src/js/collaboration-presence-v52.js
src/js/components/chart.js
src/js/crdt-yjs-indexeddb.js
src/js/crdt-yjs-rich-media.js
src/js/crdt-yjs-undo.js
src/js/dashboard.js
src/js/delivery-dialog.js
src/js/designer.js
src/js/editor/chrome/command-palette.js
src/js/editor/chrome/layers.js
src/js/editor/chrome/pages.js
src/js/editor/chrome/shortcuts.js
src/js/editor/collab/comments.js
src/js/editor/collab/presence.js
src/js/editor/editor-core.js
src/js/editor/history/timeline.js
src/js/editor/ui-layout.js
src/js/guest-journey.js
src/js/guests.js
src/js/host-polls.js
src/js/host-signup-sheets.js
src/js/invitation-edit-history.js
src/js/materials.js
src/js/monitoring.js
src/js/pages/admin/admin.js
src/js/pages/admin/audit-log.js
src/js/pages/admin/bulk-operations.js
src/js/pages/admin/feature-flags.js
src/js/pages/admin/impersonate.js
src/js/pages/admin/invitations.js
src/js/pages/admin/reports.js
src/js/pages/admin/system-health.js
src/js/pages/admin/users.js
src/js/pages/auth/sessions.js
src/js/pages/dashboard/analytics.js
src/js/polls.js
src/js/public-page.js
src/js/reset.js
src/js/responses.js
src/js/service-worker.js
src/js/signup-sheets.js
src/js/templates.js
src/js/verify.js

# build tooling (2)
src/python/build/build_route_bundles.py
src/python/build/sync_frontend_assets.py

# i18n tooling + docs (3)
scripts/check-bilingual-consistency.py
docs/i18n/LANGUAGE-GAP-REPORT.md
docs/i18n/TRANSLATIONS.csv

# font work (5)
docs/FONT_LICENSES_AND_REGISTRY.md
assets/fonts/inter-latin-400.woff2
assets/fonts/inter-latin-700.woff2
assets/fonts/inter-latin-800.woff2
licenses/fonts/Inter-OFL-1.1.txt
```

**Bucket B** — no separate path: the G1 one-liner is inside `src/html/index.html` (listed above).

**Bucket C (1):**

```
src/js/studio-experience.js
```

**Bucket D (1)** — included because §6 cleared the build-requirement as FACT:

```
src/js/core/i18n.js
```

**Bucket E (35) — regenerated bundles + manifests:**

```
src/js/bundle-account-v15.js
src/js/bundle-admin-v15.js
src/js/bundle-analytics-v15.js
src/js/bundle-billing-v15.js
src/js/bundle-checkin-v15.js
src/js/bundle-dashboard-v15.js
src/js/bundle-designer-v15.js
src/js/bundle-guests-v15.js
src/js/bundle-index-v15.js
src/js/bundle-materials-v15.js
src/js/bundle-privacy-v15.js
src/js/bundle-public-v15.js
src/js/bundle-reset-v15.js
src/js/bundle-responses-v15.js
src/js/bundle-templates-v15.js
src/js/bundle-verify-v15.js
src/css/bundle-account-v15.css
src/css/bundle-admin-v15.css
src/css/bundle-analytics-v15.css
src/css/bundle-billing-v15.css
src/css/bundle-checkin-v15.css
src/css/bundle-dashboard-v15.css
src/css/bundle-designer-v15.css
src/css/bundle-guests-v15.css
src/css/bundle-index-v15.css
src/css/bundle-materials-v15.css
src/css/bundle-privacy-v15.css
src/css/bundle-public-v15.css
src/css/bundle-reset-v15.css
src/css/bundle-responses-v15.css
src/css/bundle-templates-v15.css
src/css/bundle-verify-v15.css
docs/route-bundles-v15.json
docs/route-bundle-sources-v15.json
docs/page-assets-v15.json
```

**Bucket F (351) — served mirror tree** (all untracked `src/python/` entries from
the §3 table **except** `src/python/features/settings.py`, which is G): i.e.
`git add src/python/` minus the exclusion in §9.2. Includes the mirrors of C
(`src/python/studio-experience.js`, byte-identical, §4.6), D
(`src/python/core/i18n.js`, byte-identical, §6.2), E (32 bundles + manifest), and
all 17 HTML (§8). **Condition R1 applies**: this is the largest single decision
in the commit; if the user prefers the mirror to stay untracked, drop this group
entirely (the server keeps working from the working tree; a fresh clone would
then need `sync_frontend_assets.py` + a bundle build to reproduce the served tree).

### 9.2 `git add` exclusions (bucket G + H — explicit, no "and the rest")

```
# tracked, out-of-scope (7)
.gitignore
sbom.cdx.json
src/python/server.py
src/python/build/bundle-admin-v15.js
src/python/build/editor-suite.css
src/python/build/page-assets-v15.json
src/python/build/route-bundles-v15.json

# untracked, out-of-scope (14)
.cache/
.pw-browsers/
_i18n_all_result.json
deliverables/
docs/SESSION-LOG-2026-09-26.md
docs/STRUCTURE-PILOT-AUDIT.md
docs/UX-AUDIT-2026-09-26.md
docs/reviews/
screenshots/
scripts/audit_bidi.js
scripts/fix_structure_references.py
src/html/test-i18n-beacon.html
src/python/features/settings.py
tests/ac4_2d_audit_test.py
```
plus **H**:
```
scripts/security-scan.sh   # stat-dirty only, zero content diff — do not stage
```

### 9.3 Commit message draft

```
v54: studio topbar redesign + i18n Khmer sweep, with G1 #restoreFile and insertBefore fixes

Primary change: the v54 header rewrite. index.html gains the studio-topbar
(document title, save/server state chips, undo/redo/preview/publish actions,
Project/Editor header menu); the other 15 pages gain the bilingual i18n dual-span
sweep and the core/theme.js + lang-bootstrap swap; the Inter app-chrome font faces
land in editor-suite.css/canvas-plus.css with license + SBOM-adjacent docs; the
admin page adds a Feature flags tab. The 16 route bundles (JS+CSS) are regenerated
via build_route_bundles.py: core/i18n.js is now the first script of every page,
the admin page splits from admin.js into pages/admin/*.js, and
build_route_bundles.py now writes to src/python/ instead of src/python/build/.

The G1 #restoreFile fix travels in this commit because the v54 header rewrite is
what dropped the hidden input (restored at src/html/index.html:99, byte-exact
against all 50 committed ancestors); without it the index bundle throws at load.

The insertBefore regression was introduced by the same v54 header nesting
(#saveState/#previewBtn are no longer direct children of <header>) and is fixed
in this commit: studio-experience.js now skips the generated title when the v54
#documentTitle exists and anchors insertBefore to the element's own parent
(saveState.parentElement || header), with matching treatment for #previewBtn and
an i18n guard so the label map never clobbers bilingual .i18n span elements.

Note: src/js/core/i18n.js is new/untracked; its session-of-origin is a prior
i18n session (2026-09-28, no git history) — content verified in-scope and
build-required (all 16 bundles begin with its chunk; ROUTE_BUNDLE_CHECK_PASSED).
The 11 Khmer strings in the v54 header are recorded in
docs/reviews/v54-khmer-gate.md (TRANSLATIONS.csv, status=translated); their
linguistic correctness awaits user review.
```

No trailer, sign-off, co-author line, or emoji.

### 9.4 Outstanding risks — user decisions before `git commit`

- **R1 — `src/python/` mirror staging (351 untracked files, bucket F):** the
  prior report treated the mirror as part of the changeset; staging it makes the
  served tree reproducible from git but adds ~350 files (including 14 test HTML
  pages and `package.json`/`package-lock.json` in the mirror). Decide: stage
  all of F, or keep the mirror untracked (and document the two-step restore).
- **R2 — `src/python/build/*` tracked stale build artifacts:** the 4 M entries
  (`bundle-admin-v15.js` +958/−23, `editor-suite.css` +10/−4,
  `page-assets-v15.json` +37/−34, `route-bundles-v15.json` +11/−3) sit in the
  builder's **old** write location; the builder was moved to `src/python/` in
  this changeset and no longer writes there. They are now mutually inconsistent
  (build/route-bundles-v15.json lacks `core/i18n.js` and still lists the old
  admin bundle hash; 15 of 16 build/ bundles are at HEAD state). Excluded here
  (G). Decide: commit as-is (inconsistent state), exclude (recommended), or
  delete the 32 tracked `src/python/build/bundle-*` leftovers in a separate
  cleanup commit.
- **R3 — `src/js/core/i18n.js` (bucket D):** requirement = FACT (§6.6),
  session-of-origin = UNKNOWN (prior i18n session, 2026-09-28). Included in the
  add list; user confirmation requested. If rejected, the commit breaks
  (`--check` and every build fail without it).
- **R4 — backend workstream exclusion:** `src/python/server.py` (+168/−3,
  feature-flags/settings/admin-session-idle, ROADMAP §4.2b) and untracked
  `src/python/features/settings.py` are excluded (G). Note the interlock: the
  bucket-A admin work (feature-flags tab in `admin.html`,
  `pages/admin/feature-flags.js`, `monitoring.js` system tab) calls APIs that
  only the modified `server.py` implements; committing A without G-server leaves
  the admin feature-flags tab 404-ing on a clean checkout. Decide: accept the
  partial feature in this commit, or defer the admin feature-flag UI edits (they
  are intermixed in the same files — cannot be split without new edits).
- **R5 — `sbom.cdx.json` (G):** dependency bumps (boto3 1.43.94→1.43.103,
  psycopg 3.3.5→3.3.6, timestamp 2026-09-28) — prior-session housekeeping,
  excluded. Decide: commit with the changeset or separately.
- **R6 — 15 orphan `src/js` sources (A):** i18n-swept but not consumed by any
  bundle or HTML (verified by consumer map + reference grep):
  `collaboration-presence-v52.js`, `components/chart.js`,
  `crdt-yjs-{indexeddb,rich-media,undo}.js`, `editor/chrome/*.js` (4),
  `editor/collab/*.js` (2), `editor/history/timeline.js`,
  `pages/auth/sessions.js`, `pages/dashboard/analytics.js`,
  `service-worker.js` (registered at runtime via checkin-v13.js). Harmless;
  included; user may defer.
- **R7 — Khmer correctness (UNKNOWN):** 11 strings recorded; user fills
  `khmer_proposed` in `docs/reviews/v54-khmer-gate.md` (before or after commit).
- **R8 — `.gitignore` (G):** adds `node_modules/` + `.ff_screenshots/`
  housekeeping; excluded. Trivial; may fold into any commit.
- **R9 — `scripts/security-scan.sh` (H):** stat-dirty, zero content diff; not
  staged.

---

## 10. Uncertainty register

| # | Item | Label |
|---|---|---|
| U1 | Session/agent-of-origin of `src/js/core/i18n.js` (no git history; mtime 2026-09-28 10:24, creation==last-write; sibling i18n artifacts 9/28–9/29) | **UNKNOWN** (origin); **INFERENCE, high confidence** (prior i18n campaign session ~2026-09-28) |
| U2 | Linguistic correctness of the 11 Khmer strings (machine-generated; several look wrong, e.g. `Undo → ថម្ងម់កម្រ`, `Publish snapshot → ច្រើម`) | **UNKNOWN** — user fills `khmer_proposed` (§7.3) |
| U3 | The 12th Khmer line (line 75, mobile banner) — pre-existing vs HEAD, not part of the 11; correctness also unverified | **UNKNOWN** (out of diff scope) |
| U4 | Whether the 15 orphan `src/js` sources are dynamically loaded at runtime by some bundle (static reference grep found none; they are not in any manifest) | **UNKNOWN** (runtime behavior not executed this session); static non-consumption is **FACT** |
| U5 | Admin feature-flag workstream completeness: UI (bucket A) committed without backend (G) → 404s on clean checkout | **INFERENCE** (from quoted server.py diff + admin.html diff); user decision R4 |
| U6 | `earlyScripts` key in `route-bundle-sources-v15.json` is declarative only — the builder reads only `spec["pages"]`, and HTML pages load `core/theme.js` + inline bootstrap + bundle directly; docs already record this drift | **FACT** (builder source) / **INFERENCE** (intent of the key) |
| U7 | `scripts/security-scan.sh` — why it became stat-dirty (line-ending flip by some prior tool) | **UNKNOWN** (mechanism); zero content diff is **FACT** |
| U8 | The +1 porcelain line vs the G1 baseline (497→498) — attributed to the U7 entry appearing after G1; the G1 snapshot file is not accessible from this session to diff against | **INFERENCE** |
| U9 | Identity of the listener occupying port 8000 (inherited from G1 U1; no server/browser runs performed this session) | **UNKNOWN** |
| U10 | Inter WOFF2 asset integrity (3 new woff2 files; hashes not compared against an upstream Inter release) | **UNKNOWN** (license docs committed alongside; OFL text present) |
| U11 | `src/python/build/bundle-admin-v15.js` (+958/−23) — who/what wrote the new admin bundle into the *old* location (old builder run, or manual sync) | **UNKNOWN** (method); its inconsistency with `build/route-bundles-v15.json` is **FACT** (hash comparison §5/§9) |

Confidence labels: every FACT above is tied to a command whose output is pasted
in this report or in `docs/reviews/v54-khmer-gate.md`.

## 11. Not checked (explicit)

1. **No browser/runtime verification this session** — no Puppeteer/Edge runs, no
   console capture. The G1/Canva browser evidence (5386 TypeError before/after,
   5527 NotFoundError) is inherited from the predecessor reports, not re-executed.
   The insertBefore fix is verified at the code+bundle+mirror level (§4), not by
   observed page load.
2. No functional test of backup/restore (file choose → parse → write ×4 → reload)
   — inherited from G1 "not checked" #2.
3. No content review of the `src/python/features/` backend modules
   (`feature_flags.py`, `settings.py`, etc.) beyond `server.py`'s import lines
   and the untracked-status fact of `settings.py`.
4. No per-hunk eyeball of the ~30 remaining small A-bucket JS/CSS diffs beyond
   the mechanical i18n-token-ratio sweep (§5.4 method note) and the full bundle
   reconstruction — the reconstruction proves bundle↔source consistency, and the
   sampled diffs (8 of 15 orphans, plus editor-core, monitoring, admin, polls,
   verify, public-page, sessions, crdt-yjs-undo, service-worker,
   delivery-dialog, host-polls, host-signup-sheets) establish the i18n-sweep
   pattern.
5. No verification that `src/python/features/settings.py` content matches what
   `server.py` expects at import time (not executed; no Python import test run).
6. No audit of the 14 extra `src/python/*.html` test pages' content.
7. No re-derivation of Canva-review numbers (M1–M13, G3–G8, D1–D6, OOS-1..4) —
   out of scope for a commit-readiness check.
8. No check of `.ff_screenshots/` (gitignored in the new .gitignore draft,
   untracked) or `deliverables/`, `screenshots/` contents.
9. No WOFF2 integrity check against upstream Inter release hashes (U10).
10. No service-worker cache-behavior observation (inherited from G1 "not
    checked" #10; the `CACHE` bump v15→v16 in `service-worker.js` was noted, not
    exercised).

## 12. Acceptance-criteria self-check

- [x] Tree pinned; HEAD = `133d3647eb4a095337b7492e864c9acba94e1b35`; porcelain count 498 stated (§2.1)
- [x] Full inventory table, one bucket per entry (498/498) (§3)
- [x] InsertBefore diff hunk quoted; candidate A/B/C decided and argued — applied fix = A∪B (§4.3–4.5)
- [x] Both grep commands from §2 of dispatch run, raw output pasted (§4.4)
- [x] Bundle manifest consulted; # of JS consumers of `studio-experience.js` = **1**, source quoted (§5.2)
- [x] Unexplained bundle diffs: **none found** — full attribution via reconstruction + `--check` (§5.4–5.5)
- [x] `build_route_bundles.py --check` output pasted → `ROUTE_BUNDLE_CHECK_PASSED` (§5.5)
- [x] `i18n.js` provenance labeled: build-requirement **FACT**; session-of-origin **UNKNOWN** (§6.3, §6.6)
- [x] Khmer gate table written to `docs/reviews/v54-khmer-gate.md` (new file, only location)
- [x] Every Khmer string copy-pasted from command output (diff extraction routed through file; none typed)
- [x] `TRANSLATIONS.csv` located; header + first 5 rows quoted; 11/11 present (§7.4)
- [x] Mirror consistency table for all 17 HTML files; 17/17 byte-identical (§8)
- [x] Commit prep produced as text only (§9); **no** `git commit`/`stash`/`checkout`/`reset`/`clean` executed, no index or `.git/` write attempted
- [x] Report at exactly `docs/reviews/v54-rc-verification.md`
- [x] Final `git status --porcelain` vs initial: identical 498 lines — the two new report files live inside the already-collapsed untracked `docs/reviews/` directory entry, so no new porcelain line appears; the only change is the directory's content (now 4 files: 2 predecessor reports + the two new ones)

---

*Every number in this report was produced by a command whose output is pasted here
or saved to `%TEMP%\einvite-platform\` (paths listed inline). Prior-report numbers
(16 bundles, 17/17 HTML, 497 baseline, 5386/5527 line citations) were
independently re-derived where this dispatch required; none were inherited on
trust.*


