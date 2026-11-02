# Round 5 — deployed-origin verification

- **Origin:** https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page
- **Deployment:** `sites_deploy` `state: succeeded`, 2026-11-02T01:46:34Z;
  `sites_inspect` `published: true`; daily requests 0 / 10,000 after the reset.
- **Method:** `artifacts/verify/live_round5.py` — Playwright Chromium, each of the
  16 shipped routes at 1440×900 and 360×800, `waitUntil: load`, 1.8 s settle,
  collecting console errors, page errors, failed requests, horizontal overflow
  and document title. Key pages saved under `shots/`.

## Result

**32/32 route loads clean: 0 console errors, 0 page errors, 0 failed requests,
0 horizontal overflow.** HTTP 200 everywhere except `public.html`, which returns
307 (expected: it needs an invitation slug).

| Route | 1440 | 360 | Notes |
|---|---|---|---|
| index.html | 200 | 200 | landing renders, no overflow |
| dashboard.html | 200 | 200 | |
| public.html | 307 | 307 | redirects to the invitation resolver without a slug |
| admin.html | 200 | 200 | |
| account.html | 200 | 200 | |
| billing.html | 200 | 200 | |
| verify.html | 200 | 200 | |
| reset.html | 200 | 200 | |
| privacy.html | 200 | 200 | |
| guests.html | 200 | 200 | |
| responses.html | 200 | 200 | |
| analytics.html | 200 | 200 | |
| materials.html | 200 | 200 | |
| checkin.html | 200 | 200 | |
| templates.html | 200 | 200 | |
| designer.html | 200 | 200 | editor mounts |

## Bugs found

None at this scope. No new P0/P1/P2 findings.

## Regression checks

- BUG-R1-4 manual runners: both pass locally (`v17`, `v0_52`); the refreshed
  expectations are recorded in `bugs/round-4/FINDINGS.md`.
- BUG-R1-1 signed-out editor, BUG-R1-2 slug routing, BUG-R1-3 export/CSP were
  re-verified locally by the unchanged suite; the live origin serves the same
  bundle hash as the deployed worker.
- CLS: 0.3927 at 1440×900 (was 0.4959 phase 10); not re-measured live this round.

## Scope limits

- Two widths on the live origin (1440, 360), not the full six; the six-width
  editor interaction matrix is covered locally by the phase-10/round-4 sweeps.
- Screenshots are viewport captures of index, dashboard, public and designer at
  both widths; they are workspace-only (not committed, matching rounds 1–4).
