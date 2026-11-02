# Round 6 — live origin, six widths, full public surface

- **Origin:** https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page
- **Build:** deployed 2026-11-02T01:46Z; live `bundle-index.css` SHA-256
  `8e323747df19ccf5f34923464a10e5fa12a4cbdcf66e4bf67448b1f2fe01aced`
  matches the local built file.
- **Method:** `bugs/round-6/live_sweep.py` (114 records: 19 routes × 6 widths,
  full-page screenshots, console/page errors, failed requests, non-2xx,
  overflow, right-edge, clipping, labels, alt text, tap targets) and
  `bugs/round-6/live_flows.py` (18 interaction checks at 1440/360, plus the
  live CLS observer). Guest/RSVP/editor-depth coverage ran against the
  byte-identical local bundle via `bugs/round-4/flow_sweep.py` (61 checks).
- **Viewports:** 360×800, 390×844, 768×900, 1024×900, 1280×900, 1440×900.

## Findings

| ID | Route | Viewport | Repro | Expected | Actual | Severity | Status |
|---|---|---|---|---|---|---|---|
| — | — | — | — | — | **No new product defects found.** | — | — |

## Interaction results (live)

| Check | Result |
|---|---|
| Live CLS, `/` demo editor, 1440, load + 7 s | **0.000 (0 shifts)** — recorded, not fixed this round |
| Demo editor boots | 4 objects, stage visible, 0 overflow |
| Drag title | x 8% → 16%, state changed |
| Undo / redo | undo changes, redo restores exactly |
| Multi-select title+subtitle | 2 ids selected, 2 outlines |
| Add text via canvas text tool | 4 → 5 objects |
| Export PNG | 38,853 bytes, valid PNG signature, 0 CSP errors |
| Mobile 360 | 0 overflow, 5 objects, stage visible |
| Templates search "wedding" | 36 → 15 `.pack-card` results |
| Invalid registration | rejected by native validation; still signed out, no account created |
| Privacy language | `lang="km"` at 1440; back to English at 360, 0 overflow |
| Missing invitation | HTTP 404, heading “Invitation unavailable”, 0 overflow |
| Console | clean on all non-404 states |

## Triaged observations (not defects)

| ID | Observation | Why it is not a bug |
|---|---|---|
| OBS-R6-1 | 108 records report clipped `.skip-link` / `.sr-only` text | Screen-reader-only labels are clipped by design; same class triaged in rounds 2–4. |
| OBS-R6-2 | 16×36 `#studioFavorites` / `#selectAllGuests`, 8×20 `.app-brand`, 1×1 `.skip-link` | Same class as round 4: icon/checkbox targets with spacing and the brand mark; not new. |
| OBS-R6-3 | 8 px right-edge buttons at 768/1024/1280 on `/` | The landing demo’s horizontal tool strip; round 4 recorded the same three hits. Document scrollWidth stays 0. |
| OBS-R6-4 | `#workflowV5Focus` crosses the right edge at 360/390 | Off-canvas focus rail; `scrollWidth - clientWidth = 0`, same as rounds 3–4. |
| OBS-R6-5 | 3 console errors + 1 failed request on `/i/missing-slug-round-6` | Deliberate 404 subresources plus Cloudflare’s injected `beacon.min.js` blocked by CSP; no product code involved. |
| OBS-R6-6 | `/designer` shows “Designer Workspace unavailable” | Auth-gated workspace shell. The anonymous demo editor is `/`; its interactions all pass. |
| OBS-R6-7 | No published invitation exists live (all `/i/<slug>` 404) | Production has no invitation data; guest/RSVP six-width coverage runs locally with a seeded published invitation. |

## Earlier-round regression checks

| ID | Check | Result |
|---|---|---|
| BUG-R1-1 | Signed-out editor redirect | **Pass** — `/invitations/<id>/editor` → `/dashboard?next=…`. |
| BUG-R1-2 | Missing vs published slug | **Pass** — missing 404 live and local; published 200 locally. |
| BUG-R1-3 | Export / CSP | **Pass** — live PNG 38,853 B, clean console. |
| BUG-R1-4 | Manual runners | **Pass** — v17 and v0_52 exit 0 (no code changed since). |
| BUG-R2-1/2/3 | Guest features, album reflow, single credit | **Pass** — 0 feature panels, gallery form at 390/1440, 1 credit. |
| BUG-R4-1/2/3 | Pages grouping, tablet/drawer recovery | **Pass** — local flow sweep 61/61, six widths. |
| P1 CLS | Editor first paint | **Open, not addressed** — local 0.3927; live demo 0.000. The ≤0.1 target is not met. |

## Coverage limits

- Live editor/guest interaction is impossible without production credentials or a
  published invitation; both ran against the local bundle whose CSS hash matches
  live. No account was created and no production data was written.
- The live sweep captures every route at six widths but the template picker,
  auth forms and privacy language toggles were interacted with at 1440/360;
  editor functions were exercised live at those two widths and locally at six.
- Screenshots: `shots/` (live 114 + interaction states), workspace-only.
- Raw records: `live-sweep.json`, `live-flows.json`.

## Gates

- `python3 build.py all --check` → `BUILD_OK` / `MIRROR_CHECK_PASSED`
- `python3 -m compileall -q src/python tests tools` → exit 0
- `node --check`: no JS changed this round (N/A)
- Full pytest suite: see `PROGRESS.md` (running at the time of writing).
- The repo has no ESLint or TypeScript toolchain; this is noted here as required.
