# PROGRESS — autonomous mission log

## Current status
- **Branch:** `chore/cleanup`, local commits only (OD-3). Nothing pushed.
- **Queue of record:** `docs/NEXT-WORK.md` — 18 open defects, **0 untriaged suite failures**, 36
  work-order tasks, 18 owner decisions, 12 verification debts. History: `docs/HISTORY.md`.
- **Step 1 (finish leftover work):** the two pre-existing suite fixes and the three editor
  baseline failures are closed. Remaining Step 1 work is the product backlog in `NEXT-WORK.md`
  (P0/P1/P2), not test triage.
- **Round 1 (live sweep):** 114 live route/viewport records + 31 authenticated local checks,
  **0 failed checks**; final full suite **223 passed, 2 warnings in 883.42 s (exit 0)**; one P1
  fixed (BUG-R1-1) and proven live, two P2s logged (soft 404, CSP console), one stale
  manual-runner fixture marked stuck. Findings: `bugs/round-1/FINDINGS.md`. The two P2s were
  fixed in round 2.
- **Round 2 (live sweep):** 120 live route/viewport records + 42 authenticated local checks,
  **0 failed checks / 0 application console errors**; the three new P2s are fixed and live:
  empty guest-feature panels removed, album upload row reflowed, duplicate platform credit
  removed. PNG export remains valid (39,023 B); findings and evidence are in
  `bugs/round-2/`. Retested live 200/404 contract, signed-out redirect, Khmer digits and all
  six widths.
- **Round 0 (baseline close-out):** `lt_4_3`, `lt_4_4` and `lt_2_2` pass — `4 passed in 51.59 s`.
  Verdicts and evidence: `bugs/round-0/FINDINGS.md`; plan: `FIX_PLAN.md`.
- **Live site:** production redeployed 2026-11-01 04:15 UTC at
  `https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page` and `published: true` (deploy
  `7265e709-7c1a-4af1-9d20-c60d98b092a5`). Served `bundle-public.js` SHA-256 is
  `c44ae93b…858899cc` and served `bundle-public.css` is `32c7f20a…4448d87c`; both match
  `artifacts/sites-public`. `/i/qa-ui-sweep-wedding` returns 200, `/i/<missing>` returns 404 and
  `/api/health` returns 200 through the Worker. `einvite-app` and `einvite-tunnel` are active;
  preview remains on its 2026-10-31 build.
- **Baseline already measured:** build/bundles/smoke green; layout grazed 600 ms once and passed on a
  quiet rerun; pytest profile before the fixes was **5 failed / 218 passed** (15:01). Full log under
  `artifacts/next-work/gates/`.

## Log

### 2026-11-01 — Dependabot inventory
- Documented all **92 open alerts** (49 unique advisories; 13/49/29/1 alerts by severity;
  6/26/16/1 unique) in `docs/security/DEPENDABOT-ALERTS-2026-11-01.md`, including every alert ID,
  manifest, version, fix and advisory link.
- The default branch is the source of the count. The current branch already has Pillow 13.0.0
  (82 alerts fixed once merged); Brotli 1.2.0 remains in three manifests; the seven old npm alerts
  are no longer in this lockfile. Current `npm audit` separately reports three high dev-only
  `zod`/`puppeteer-core` chain findings.
- No dependency pins were changed in this pass.

### 2026-11-01 — round 2: guest-page P2s fixed, deployed and re-swept
- Live matrix: 20 routes × 6 widths = **120 records**, screenshots per state; **0 horizontal
  overflow**, no unexpected statuses. Expected 404s account for the 18 non-beacon console errors
  (missing-slug document + API, missing route). The host-injected Cloudflare beacon remains the
  only third-party CSP violation.
- Authenticated flow: **42 checks, 0 failed, 0 application console errors** — RSVP, Khmer digits,
  template filter, editor add/drag/resize/rotate/multi-select/undo/redo/save/reload, signed-out
  redirect, wrong-password error, and a 39,023 B PNG export with the PNG signature.
- **BUG-R2-1 (P2, fixed `0604f2c`):** every guest page mounted sign-up, poll and album panels
  before knowing whether the host had data. Empty sheets/polls now remove themselves; the album
  is gated by the gallery setting; the branded credit is reordered after the mounted panels.
- **BUG-R2-2 (P2, fixed `ef2f52a` + `33b43eb`):** the album form's fixed grid clipped “Choose
  photo” and collapsed the caption. Auto-fit columns stack the fields in the narrow card, the
  button owns a full row, and `Load more[hidden]` is actually hidden. Gallery-enabled fixture
  proves both fields are usable at 390 and 1440.
- **BUG-R2-3 (P2, fixed `ef78d67`):** `public.html` shipped a static credit while the renderer
  appended another. The static duplicate is gone; the live page has exactly one credit.
- **Not kept:** the apparent blank design pages are deferred reveal animations; scrolling each
  page into view shows all text at opacity 1. The renderer was left unchanged.
- Gates: `build.py all --check` → `MIRROR_CHECK_PASSED`; `build.py bundles --check` →
  `ROUTE_BUNDLE_CHECK_PASSED`; `compileall` exit 0. Production deploy `7265e709` published
  04:15:09Z; served JS/CSS hashes match the local bundle.
- Final full suite: **223 passed, 2 warnings in 1033.18 s (exit 0)**. The warnings are the known
  teardown-time `sqlite3.OperationalError` on a worker thread; no test failed.

### 2026-11-01 — round 1: live sweep and P1 fix
- Live production matrix: 19 routes × 6 widths, 114 screenshots, **zero horizontal overflow**,
  no unlabelled inputs, no unnamed buttons, no missing alt text. Only the deliberate 404 and the two
  route-level findings produced console/network errors.
- Authenticated local flow (same source, production cannot exercise writes): **31 checks, 0 failed** —
  RSVP, Khmer digits, template filter 36→1, editor Pages pane, save/reload, 1× PNG export (41,042 B),
  390 editor with no overflow, wrong-password error, signed-out redirect.
- **BUG-R1-1 (P1, fixed):** signed-out editor navigations showed raw JSON. HTML `Accept` now gets a
  302 to `/dashboard.html?next=…`; API clients still get 401 (`v12` passes).
- **BUG-R1-2 (P2, open):** missing slug renders "Invitation unavailable" but returns HTTP 200.
- **BUG-R1-3 (P2, open):** CSP blocks a generated `data:image/svg+xml` fetch (two console errors;
  export still valid).
- **BUG-R1-4 (tooling, stuck):** `v0_52_free_canvas_drag_test` times out because the inline fixture
  no longer loads the bundle defining `EInviteProfessionalEditor`; real editor boots in the flow.
- Known defect #6 (second concurrent editor session) reproduced and is not re-scored.
- First full re-run failed only on the Khmer source guard because the sweep fixture carried Khmer
  literals; they were escaped to ASCII (rendered data unchanged), the guard passes, and the fixture
  is committed. The green re-run above is from that tree.
- **Production proof:** deployment `31aca594` succeeded (`published: true`,
  `deployed_at 2026-11-01T02:57:05.865Z`). Live signed-out editor with `Accept: text/html` returns
  **302** to `/dashboard.html?next=…`, with `Accept: application/json` returns **401**, `/api/health`
  returns 200, and the served `bundle-index-2.js` SHA-256 equals the local build
  (`2207b4a8…d021fd04`).

### 2026-11-01 — verification and production deploy
- Full suite: **223 passed, 2 warnings in 866.15 s** (`artifacts/verify/pytest-full.log`), exit 0.
  The warnings are a teardown-time `sqlite3.OperationalError` on a worker thread, not failures.
- Gates: `build.py all --check` → `MIRROR_CHECK_PASSED`; `bundles --check` →
  `ROUTE_BUNDLE_CHECK_PASSED`; `compileall` clean. This repo configures no ESLint, tsc or ruff; those
  build gates are its lint/type-check equivalent.
- Deployed production with the existing `deploy/sites/manifest.json`. Before: live bundle had
  `reorgBody=0`; after: `reorgBody=1` and byte-identical SHA-256 to `artifacts/sites-public`.
- Restarted `einvite-app`; `/api/health` through the Site returns 200. Round 1 not started, per order.

### 2026-11-01 — round 0: the three editor baseline failures
- **BUG-R0-1 (product, P1):** `typography-editor.js` installs after `inspector-reorg.js` and rebuilt
  its shell inside the legacy `#typographyControls`, which the reorg had already hidden after filing
  the controls into the visible Text group. Colour, digit-conversion and run controls were dragged
  back into a hidden container. The shell now mounts into the Text group when the reorg is present;
  the superseded `#advancedTextLayout` is removed so the id stays unique.
- **BUG-R0-2 (stale test):** the shared harness hunted a button labelled `Event details`; the rail is
  rebuilt with the label `Event` and the stable `data-studio-tab="event"` attribute. `open_studio_tab`
  now clicks that attribute (opening the tools drawer at narrow widths).
- **BUG-R0-3 (stale test):** `lt_4_4` waited for `#typographyControls` to be visible, but the
  2026-10-30 reorganisation deliberately hides it. `reveal_inspector_control` opens the real closed
  `<details>` ancestors and the test waits for `#v20RunFont`, the control it drives.
- **No assertion was weakened or removed.** `lt_2_2`'s public-render leg had already passed; the
  public page was never the failure.

### 2026-11-01 — phase-1: platform_jobs table in the SQLite bootstrap
- **Why:** `platform_v32/jobs.py` queries `platform_jobs`, but only `docs/postgres_schema.sql` created
  it. The worker raised `no such table: platform_jobs`, which surfaced as `RemoteDisconnected` in
  `ai_resource_scopes_test`.
- **Change:** the three DDL statements added to `_P2A_SCHEMA_STATEMENTS` (portable SQLite/PostgreSQL),
  so `connect_sqlite()` creates the table and both indexes on the first connection.
- **Verify:** `tests/ai_resource_scopes_test.py`; `build.py all` mirror check.

### 2026-11-01 — phase-1: guest-row actions + public 401 blocks (already shipped)
- `12087a8` delegated row actions on the stable guest-list container; `bbd3b9d` removes the signup /
  poll / album sections on a `401` instead of printing "HTTP 401" on a public invitation.

### 2026-11-01 — phase-1: gallery test aligned with the shared studio filter
- PW-7 removed the per-gallery filter chips so one toolbar filters both lists; the gallery follows
  `einvite:studio-filter`. The test still clicked the removed chips, so it timed out *after* the 36
  cards had rendered. It now drives `#studioCategory` / `#studioSearch` and asserts the same counts
  (15 wedding, 5 ceremony, 36 all, 1 on "maroon") — no assertion removed or weakened.

## Open questions
- **Inspector disclosures:** the 2026-10-30 reorganisation files text controls one disclosure deep.
  Round 1 should judge whether that is acceptable interaction cost for colour/digit conversion, or
  whether the Text group should open its first sub-section by default. No change made in round 0.
