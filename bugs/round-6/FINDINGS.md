# Round 6 — live origin, six widths, full public surface

- **Origin:** https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page
- **Build:** deployed 2026-11-02T01:46Z; live `bundle-index.css` SHA-256
  `8e323747df19ccf5f34923464a10e5fa12a4cbdcf66e4bf67448b1f2fe01aced`
  matches the local built file. **No app source changed in this pass.**
- **Method:** `bugs/round-6/live_sweep.py` (114 records: 19 routes × 6 widths) plus
  the extended `bugs/round-6/live_flows.py` (six widths: editor, templates,
  filters, Khmer input, registration, shells, 404, per-state screenshots and
  console/network records), and the six-width local guest/editor sweep
  `bugs/round-4/flow_sweep.py` (61 checks).
- **Viewports:** 360×800, 390×844, 768×900, 1024×900, 1280×900, 1440×900.

## Findings

| ID | Route | Viewport | Repro | Expected | Actual | Severity | Status |
|---|---|---|---|---|---|---|---|
| — | — | — | — | — | **No product defect confirmed.** | — | — |

The interaction run completed once at all six widths: **219 checks, 204 passed,
15 failed**. All 15 failures were traced to four harness assumptions and are
listed below; none is confirmed as an application defect. The corrected harness
could not be rerun because the site hit its daily hosting allowance.

## Per-width execution

| Width | Checks | Failed | Failing checks | Console/page/network |
|---|---|---|---|---|
| 360 | 37 | 4 | drag, resize, rotate, undo/redo | clean |
| 390 | 37 | 4 | drag, resize, rotate, undo/redo | clean |
| 768 | 36 | 1 | undo/redo | clean |
| 1024 | 35 | 4 | drag, resize, rotate, undo/redo | clean |
| 1280 | 37 | 1 | undo/redo | clean |
| 1440 | 37 | 1 | undo/redo | clean |

Raw record: `live-flows-six.json`; **202 state screenshots**: `shots/flows-v2/`.

## Failure triage

| Failure | Cause | Evidence | Harness correction |
|---|---|---|---|
| 360/390/1024 drag, resize, rotate | Selecting the object opens the responsive inspector/Quick Edit drawer above the canvas. The suite selected programmatically and then drove pointer gestures under the open drawer. | A direct drag on the unselected title moves it; after `Escape`/Canvas the selected title also drags (manual probe, 360 and 1024). 768/1280/1440 drag, resize and rotate pass in the same run. | Close the drawer (Escape/Canvas) after selecting and before gestures; keep selection. Applied, not yet rerun live. |
| undo/redo, all widths | The check compared exact `state.objects` JSON. Redo re-inserts the undone text object with a fresh id, so the visual result is restored but the bytes differ. | Every width reports `undo changed = true`, `redo restored = false`; the earlier bridge-based 1440 pass used a title transform, not an inserted object. | Compare restored object count/content instead of exact JSON. Applied, not yet rerun live. |
| 360 appearance | The Appearance control is correctly absent at this width. | Check recorded `skipped: control absent`, not a failure. | None. |
| Expected API 404 | `/i/missing-slug-round-6` also fetches `/api/public/missing-slug-round-6` (404 by design). | Only network hit in each width; page, console and all other requests clean. | Filter both deliberate 404 paths. |

## What passed live at six widths

- Appearance menu (Dark→Light), language switch, rail tabs, Design check,
  command palette, Guest preview and Publish shells (768+).
- Editor add text, save, reload/recover, PNG export (valid signature, no CSP
  error), multi-select; drag/resize/rotate at 768/1280/1440 and by direct
  pointer on mobile/1024.
- Template search 36→15, source and category filters, favorites toggle, refresh,
  Khmer numerals typed into search (`ខ្មែរ ១២៣`), Khmer/mixed card text,
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

## Blocked clean rerun

At **2026-11-02T03:40Z** the origin returned **HTTP 429 “This site has reached
its hosting allowance.”** `sites_inspect` reports the site **paused**:

- daily requests **10,301 / 10,000**, reset **2026-11-03T00:00Z**
- monthly requests 21,056 / 100,000; data preserved

The next run must happen after the reset. The 429 is now detected and recorded
instead of cascading into a blank-page failure. No app source was changed and no
deploy/verification is claimed.

## Coverage limits

- Guest invitation and RSVP were not driven against production: there is no
  published invitation and no credentials. They remain covered only by the
  local seeded bundle (61/61 checks).
- The live editor interactions ran at 360/390/768/1024/1280/1440, but the clean
  pass after the harness corrections is the blocked item above.
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
| P1 CLS | Editor first paint | **Open, untouched** — live `/` demo 0.000; workspace 0.3927, target ≤0.1 not met. |

## Gates

- `py_compile bugs/round-6/live_flows.py` → pass after the final edits.
- `python3 build.py all --check` → `BUILD_OK` / `MIRROR_CHECK_PASSED` (no app source changed).
- `python3 -m compileall -q src/python tests tools` → exit 0.
- Full pytest suite: **231 passed, 1 warning in 1210.03 s (exit 0)** (run before this test-only edit).
- `node --check`: no JS changed (N/A). The repo has no ESLint or TypeScript toolchain.
