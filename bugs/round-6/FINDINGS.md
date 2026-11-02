# Round 6 — six widths, final local pass

- **Build under test:** the local production bundle at `http://127.0.0.1:4180`,
  served from `artifacts/sites-public` with the isolated backend at `:4181`.
  The published origin remains the 2026-11-02T01:46Z deployment; its daily
  hosting allowance is exhausted, so this pass makes **no live claim**.
- **Method:** `bugs/round-6/live_flows.py` at six widths (editor, templates,
  filters, Khmer input, registration, shells, 404, per-state screenshots and
  console/network records). `bugs/round-4/flow_sweep.py` supplies the separate
  six-width guest/editor depth pass (61 checks).
- **Viewports:** 360×800, 390×844, 768×900, 1024×900, 1280×900, 1440×900.

## Findings

| ID | Route | Viewport | Repro | Expected | Actual | Severity | Status |
|---|---|---|---|---|---|---|---|
| — | — | — | — | — | **No product defect confirmed.** | — | — |

The final interaction run passed: **225/225 checks, 0 failures**, with clean
console, page-error and unexpected-request checks at every width. The 15
failures in the first live run were harness assumptions; three 1024 gesture
failures in the first local rerun were a scrolled canvas target, fixed by
scrolling the selected title into the viewport before dragging.

## Per-width execution

| Width | Checks | Failed | Console/page/network |
|---|---|---|---|
| 360 | 38 | 0 | clean |
| 390 | 38 | 0 | clean |
| 768 | 37 | 0 | clean |
| 1024 | 36 | 0 | clean |
| 1280 | 38 | 0 | clean |
| 1440 | 38 | 0 | clean |

Raw record: `live-flows-six.json`; state screenshots: `shots/flows-v2/`.

## Failure triage

| Failure | Cause | Evidence | Harness correction |
|---|---|---|---|
| 360/390/1024 drag, resize, rotate | Selecting the object opens the responsive inspector/Quick Edit drawer above the canvas. At 1024 the canvas was also left scrolled, putting the title above the viewport. | A direct drag on the unselected title moves it; the failure screenshot showed the drag click opening the topbar guest preview. | Close the drawer (Escape/Canvas) after selecting; reset scroll, scroll the title into the canvas, and require its center to be in-view before gesturing. **Passes.** |
| undo/redo, all widths | The check compared exact `state.objects` JSON. Redo re-inserts the undone text object with a fresh id, so the visual result is restored but the bytes differ. | Every width reported `undo changed = true`, `redo restored = false`; the earlier bridge-based 1440 pass used a title transform, not an inserted object. | Compare restored object count/content instead of exact JSON. **Passes.** |
| 360 appearance | The Appearance control is correctly absent at this width. | Check records `skipped: control absent`, not a failure. | None. |
| Expected API 404 | `/i/missing-slug-round-6` also fetches `/api/public/missing-slug-round-6` (404 by design). | Only network hit in each width; page, console and all other requests clean. | Filter both deliberate 404 paths. **Passes.** |

## What passed at six widths (local final)

- Appearance menu (Dark→Light), language switch, rail tabs, Design check,
  command palette, Guest preview and Publish shells (768+).
- Editor add text, save, reload/recover, PNG export (valid signature, no CSP
  error), multi-select; drag/resize/rotate at 768/1280/1440 and by direct
  pointer on mobile/1024.
- Template search 36→15, source and category filters, favorites toggle, refresh,
  Khmer numerals typed into search (Khmer text and Khmer numerals), Khmer/mixed card text,
  `"EInvite Noto Sans Khmer"` computed font.
- Signed-out dashboard shell, invalid registration/sign-in rejected, valid-shaped
  registration fields accepted but **never submitted** (no account created).
- `/designer` auth shell and the missing-invitation 404.
- Console, page errors and unexpected HTTP/request failures: **clean at every
  width**.

## Visual records

The audit recorded clipped `.sr-only`/`.skip-link` text (134), known small
targets (109), the off-canvas `#workflowV5Focus` (5), header popover overlaps
(4), and five low-contrast reports on `#lang-km.active`. The contrast reports are
false positives: the probe parses only `rgb()` backgrounds and falls through to
the page colour for `color(srgb …)`; the active language chip is white on the
accent fill. No new clipping, overlap, misalignment or Khmer glyph defect was
confirmed.

## Live redeploy blocked

At **2026-11-02T03:40Z** the origin returned **HTTP 429 “This site has reached
its hosting allowance.”** `sites_inspect` reports the site **paused**:

- daily requests **10,301 / 10,000**, reset **2026-11-03T00:00Z**
- monthly requests 21,056 / 100,000; data preserved

The single production deploy attempt (`593d9b20-ecfb-4e0d-9d88-799f4c6099ed`)
was refused with the same hosting-allowance error before a receipt was created.
The latest successful deployment remains 2026-11-02T01:46:34Z. The local final
pass is green, but the deployed build predates these app fixes. No live deploy
or live verification is claimed, and no retry was made. The 429 is detected and
recorded instead of cascading into a blank-page failure.

## Coverage limits

- Guest invitation and RSVP were not driven against production: there is no
  published invitation and no credentials. They remain covered by the local
  seeded bundle (61/61 checks).
- The final six-width pass is local. The live origin must be rebuilt, deployed
  and re-tested after the allowance resets.
- No account was created and no production data was written.

## Earlier-round regression checks

| ID | Check | Result |
|---|---|---|
| BUG-R1-1 | Signed-out editor redirect | **Pass** — `/invitations/<id>/editor` → `/dashboard?next=…`. |
| BUG-R1-2 | Missing vs published slug | **Pass** — missing 404 live/local; published 200 locally. |
| BUG-R1-3 | Export / CSP | **Pass** — valid PNG, console clean, all widths. |
| BUG-R1-4 | Manual runners | **Pass** — v17 and v0_52 exit 0 (no code changed). |
| BUG-R2-1/2/3 | Guest features, album reflow, single credit | **Pass** — local 61/61. |
| BUG-R4-1/2/3 | Pages grouping, tablet/drawer recovery | **Pass** — local 61/61. |
| P1 CLS | Editor first paint | **Fixed locally** — desktop **0.0698 / 0.0679 / 0.0810**, mobile **0.0973 / 0.0973 / 0.0943** (three consecutive runs each); all < 0.1. The 220 → 502 → 220 px Pages-group reflow is gone; residual `.ix-groups` movement is ≤ 0.0020. |

## Gates

- `py_compile bugs/round-6/live_flows.py` → pass after the final edits.
- `python3 build.py all` → exit 0 (`BUILD_OK`); `build.py all --check` → `MIRROR_CHECK_PASSED`.
- `python3 -m compileall -q src/python tests tools` → exit 0.
- Full pytest suite: **247 passed, 16 warnings in 1092.83 s (exit 0)**; no failures. The 16
  warnings are all `PytestReturnNotNoneWarning` from the example plugin; the SQLite teardown /
  `PytestUnhandledThreadExceptionWarning` is gone.
- `node --check` on changed JS → pass. The repo has no ESLint or TypeScript toolchain.
