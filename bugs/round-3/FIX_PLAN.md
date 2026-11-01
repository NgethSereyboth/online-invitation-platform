# Round 3 — fix plan

Date: 2026-11-01
Status: **no product code fixes**; one dependency follow-up completed; live
re-verification and deployment are blocked by the hosting daily quota.

## Ordered tasks

| # | Task | Suspected cause | Files likely to change | Commit | Status |
|---|---|---|---|---|---|
| 1 | Bump Brotli 1.2.0 → 1.2.1 in production and tools requirements, then prove the resolved environments install consistently. | Dependabot follow-up from the 2026-11-01 inventory; no code defect. | `docs/requirements-production.txt`, `tools/requirements.txt` | `940a799` | **Done** — both pins are 1.2.1; temporary venv reports module/dist 1.2.1 and `pip check` is clean; runtime `.venv` upgraded and `einvite-app` restarted (`/api/health` 200); build/bundle checks pass. |
| 2 | Record the round-3 matrix and triage every finder hit. | None — no product defect was confirmed. | `bugs/round-3/*` | docs commit | **Done** — 120 records, 120 screenshots; 118 accessible live records verify; false-positive classes documented. |
| 3 | Re-run the interrupted live 1440 routes and the authenticated flow. | Sites paused after **10,755 / 10,000 daily requests**; Cloudflare returns 429 before the Worker. | none (external) | — | **Blocked** until **2026-11-02T00:00Z**. Local production-mode 1440 fallback is green: valid invitation 200, missing slug 404, missing route 404, signed-out editor 200 → dashboard, overflow 0. |
| 4 | Redeploy current HEAD and verify the served hashes/publication. | Sites refuses deploys while the quota is suspended. | `deploy/sites/manifest.json` (already built) | — | **Blocked** — `sites_deploy` was rejected before creating a receipt; last successful deploy remains `7265e709`. The current static build is unchanged, but a fresh publication is not confirmed. |
| 5 | Resolve the remaining host-injected beacon CSP message. | Cloudflare injects `beacon.min.js`; production CSP is `script-src 'self'`. | `src/python/...` CSP policy, only if the owner approves a third-party origin | — | **Owner decision**, not a round-3 regression; unchanged from rounds 1–2. |

## Product-fix scope

No source file changes were justified by round 3. The editor, RSVP, gallery,
template picker, export, error/empty states and Khmer/mixed-text paths all
passed. The only failures were the external 429 responses after the hosting
allowance was exhausted.

## Verification for this round

- `python3 build.py all` → `BUILD_OK` / `MIRROR_CHECK_PASSED`.
- `python3 tools/build-sites-bundle.py --out artifacts/sites-public` → 224
  files, 9.48 MiB; local hashes match the last deployed bundle.
- Authenticated flow → `44` checks, `0` failed, `0` console errors; PNG
  40,937 bytes.
- Live matrix → `120` records, `0` horizontal overflow, `0` page errors,
  `0` unlabelled inputs, `0` unnamed buttons, `0` missing alt text.
- Local 1440 fallback → four routes as tabulated in `FINDINGS.md`.

## Not touched

No `@ts-ignore`, `eslint-disable`, deleted tests, weakened assertions or
lowered thresholds. No placeholder text was replaced with real personal data
and no secret was committed.

## Remaining external action

After the **2026-11-02T00:00Z** reset, redeploy once and repeat the two live
1440 records (`/missing-route-round-3`, signed-out editor) plus the valid
invitation. That is the only step preventing round 3 from being marked fully
closed; it requires no code change.
