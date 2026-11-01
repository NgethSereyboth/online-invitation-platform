# Round 3 — live sweep findings

Date: 2026-11-01
Live site: `https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page`
Local production backend: `http://127.0.0.1:4175`
Branch: `chore/cleanup`

## Result

Round 3 re-checked all earlier findings, then ran the full 20-route × 6-viewport
live matrix and the authenticated local flow. **No new product defect was
confirmed.** The public site became unavailable partway through the last
viewport because the hosting plan's daily request allowance was exhausted, so
the final two live 1440 records are external `429` responses rather than app
responses. The same two routes and the valid-invitation control were verified at
1440 against the local production-mode server.

| Measure | Result |
|---|---|
| Live route/viewport records | **120** (20 routes × 6 widths) |
| Live screenshots | **120** |
| Live statuses | 107 × 200, 11 × expected 404, **2 × external 429** |
| Horizontal overflow | **0 records** |
| Page errors | **0** |
| Unlabelled inputs / unnamed buttons / missing alt | **0 / 0 / 0** |
| Authenticated flow | **44 checks, 0 failed, 0 application console errors** |
| Editor interactions | add, drag, resize, rotate, multi-select, undo, redo, save, reload, export — all passed |
| PNG export | **40,937 bytes**, valid PNG signature |
| Gallery form at 390 / 1440 | 220 px / 330 px fields and button; no clipping; overflow 0 |
| Template filter | 36 → 1 on `royal` |
| Khmer digits | present at 360, 390 and 1440 in the public flow |

## Product findings

**None.** There is no new product bug with a route, viewport, reproduction
step, expected result and actual result to record. Consequently there is no
`fix-round-3:` commit; no product source file was changed.

## Environment and tooling findings

| ID | Kind | Route / scope | Repro | Expected | Actual | Severity | Status |
|---|---|---|---|---|---|---|---|
| OBS-R3-1 | Hosting quota | Every route; documents at 1440 | Run the 120-record live matrix against the Sites production origin. | The app responds normally. | Sites pauses the site because daily requests reached **10,755 / 10,000**. The two 1440 documents that had not loaded returned Cloudflare `429` with `retry-after: 60`; seven subrequests also got 429. `sites_inspect` confirms `state: suspended`, reset **2026-11-02T00:00Z**. | External blocker | **Open** — cannot be fixed in the repo; wait for reset or change the hosting plan. |
| OBS-R3-2 | Hosting injection | All live routes | Load any page on the deployed origin. | No CSP violation from application code. | The host injects `static.cloudflareinsights.com/beacon.min.js`; `script-src 'self'` blocks it. This predates round 1 and is not emitted by this repository. | P3 external | Accepted/documented; widening CSP is an owner security decision. |
| OBS-R3-3 | Deployment | Production | `sites_deploy` with `deploy/sites/manifest.json` after the quota was exhausted. | New deployment receipt. | Rejected before a receipt was created: “Your sites have reached a hosting allowance and are paused.” Last successful deploy remains `7265e709-7c1a-4af1-9d20-c60d98b092a5` at 04:15:09Z; `published: true` but serving is suspended. | External blocker | **Open** — retry after the daily reset. |
| OBS-R3-4 | Finder false positives | 112 records | Run the clipping detector over elements with hidden overflow. | Only user-visible clipped text is reported. | Hits are `.sr-only` headings/labels, hidden alternate-language spans, ellipsis in the editor title/refresh labels, and the guest empty-state paragraph whose Khmer translation is hidden. Full-page screenshots at 390 and 1440 show the visible copy intact; document overflow is 0 everywhere. | Not a defect | Triaged, no change. |
| OBS-R3-5 | Finder false positives | 5 records (`/` at 360–1280) | Inspect elements crossing the right edge. | No page-level horizontal scroll. | `#workflowV5Focus` / its animated focus-rail button extends past the viewport while off-canvas; `scrollWidth - clientWidth` remains 0. | Not a defect | Triaged, no change. |
| OBS-R3-6 | Finder false positives | 113 records | Inspect tap targets under 24 px. | Real controls are reachable. | Hits are skip links, the brand menu, hidden/off-canvas focus controls, native checkboxes and the open-cover button. This is pre-existing and not introduced by round 3; no new interaction failure was observed. | Not a new defect | Triaged; WCAG target-size work remains in `docs/NEXT-WORK.md`. |

## Earlier-round regression checks

| ID | Check | Result |
|---|---|---|
| BUG-R1-1 | Signed-out editor navigation | **Pass** — 1440 local lands on `/dashboard.html?next=…` with 0 overflow and 0 console errors; all five accessible live widths returned the dashboard. |
| BUG-R1-2 | Published vs missing slug status | **Pass** — live `/i/qa-ui-sweep-wedding` 200; `/i/missing-slug-round-3` 404 at all six widths; local 1440 repeats 200/404 with 0 overflow. |
| BUG-R1-3 | Export/CSP regression | **Pass** — export flow downloaded a valid 40,937-byte PNG with 0 CSP/console errors. The live beacons remain the external host injection described above. |
| BUG-R1-4 | Manual-runner fixture | Still **stuck**, unchanged: the inline fixture does not load the bundle defining `EInviteProfessionalEditor`; the real editor boots and all round-3 editor checks pass. |
| BUG-R2-1 | Empty guest features | **Pass** — 0 unconfigured sign-up/poll/album panels; exactly 1 platform credit. |
| BUG-R2-2 | Album form reflow | **Pass** — 390: file/caption/button 220 px, form 270 px; 1440: 330 px, form 380 px; label not clipped; load-more hidden; overflow 0. |
| BUG-R2-3 | Duplicate credit | **Pass** — exactly one credit in the flow and screenshots. |

## Live 1440 fallback

The last live width was interrupted by OBS-R3-1. The two affected documents
and the valid-invitation control were checked at 1440 against the same source
on the local production-mode backend:

| Route | Status | Final URL | Overflow | Console |
|---|---|---|---|---|
| `/i/qa-ui-sweep-wedding` | 200 | same | 0 | 0 |
| `/i/missing-slug-round-3` | 404 | same | 0 | 2 expected resource 404s |
| `/missing-route-round-3` | 404 | same | 0 | 1 expected resource 404 |
| `/invitations/00000000-0000-0000-0000-000000000000/editor` | 200 | `/dashboard.html?next=…` | 0 | 0 |

Log: `artifacts/verify/round3-local-1440.log`.

## Console/network triage

All **35** captured console errors are one of three expected categories:

- 404s for the deliberately missing slug and missing route (document + API);
- 404/429 resource failures caused by the Sites quota pause;
- the host-injected Cloudflare beacon CSP message (OBS-R3-2).

No application `pageerror` occurred. The 15 `requestfailed` events are aborted
assets/API calls from the 429 pause and the deliberate 404 routes, not app code.
The application console was clean in the 44-check authenticated flow.

## Evidence

- `live-sweep.json` — all 120 records and the per-record audit.
- `flow-sweep.json` — 44 checks, 0 failures, 0 console errors.
- `shots/` — 120 live screenshots plus the flow screenshots (workspace, not all
  committed because of size).
- `evidence/r3-live-public-390.png` — live invitation, 390.
- `evidence/r3-live-guests-390.png`, `-1440.png` — empty guest-list state.
- `evidence/r3-gallery-390.png`, `-1440.png` — reflowed gallery form.
- `evidence/r3-editor-390.png` — editor at 390.
- `evidence/r3-rsvp-submit.png`, `r3-export-png.png`, `r3-khmer-digits-390.png`.
- `evidence/r3-live-429-missing-route.png`, `r3-live-429-editor.png` — the
  external quota response, not a layout screenshot.
- `evidence/r3-local-1440-missing-route.png`, `r3-local-1440-signed-out-editor.png`
  — local fallback for the interrupted live width.
- `artifacts/verify/round3-live-summary.log`, `round3-local-1440.log`,
  `round3-sites-quota.txt`.

## Deployment status

The round-3 rebuild is byte-identical to the last deployed static build:
`bundle-public.js` `c44ae93b…858899cc`, `bundle-public.css`
`32c7f20a…4448d87c`. The attempted redeploy was rejected by the Sites quota
before a receipt was created. The live site therefore still serves deploy
`7265e709-7c1a-4af1-9d20-c60d98b092a5` and is paused until the daily reset.
This round is **not** a fully closed live verification until a post-reset
redeploy and the two 1440 live records are repeated; that remains external.
