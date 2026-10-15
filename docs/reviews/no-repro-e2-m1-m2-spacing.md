# The three written symptoms that did not reproduce — and what the measurement found instead

Three of the five reported symptoms could not be reproduced as written. This file keeps
the measurements that say so, because "we looked and it is not there" is a result too,
and it records one *new* defect the same measurements turned up: it is measured, it is
real, and it is **not fixed** (§4).

Method: the dev server (`python3 src/python/server.py --host 127.0.0.1 --port 4175`)
plus `./node_modules/.bin/agent-browser` — the same app, same URLs, DOM and computed
geometry read from the live page. Scripts: `artifacts/measure_overlays.js`,
`artifacts/measure_library.js`. Every block in this file is
`<!-- report-verify: measurement ... -->`: it needs the server and a browser, and the
numbers are one run's layout.

## 1. E2 — the status strip, the HUD and "Graphics diagnostics"

**Does not reproduce.** The written symptom was the HUD, the graphics diagnostics
panel and the status strip printing over one another. Measured at 1440/1100/900 with
an object selected on the canvas:

<!-- report-verify: measurement needs the dev server plus a browser -->

    1440  #workflowV5Status 641,164 167x28  .workflow-quick-strip: absent
          .ei-graphics-diagnostics: in aside.right.studio-inspector at 1183,790
    1100  #workflowV5Status 537,130 147x28  .workflow-quick-strip: absent
          .ei-graphics-diagnostics: 1137,819 (drawer closed, off-screen)
     900  #workflowV5Status 437,130 147x28  .workflow-quick-strip: absent
          .ei-graphics-diagnostics: 937,819 (drawer closed, off-screen)

- `#workflowV5Status` is a lone top-centre pill; the sweeping probe that compares
  every floating overlay (`artifacts/measure_overlays.js`) reports no intersection
  involving it that is not one of the two known non-overlaps below.
- `.workflow-quick-strip` is **not in the DOM** on this build at all, so it cannot
  collide with anything.
- "Graphics diagnostics" is not a floating HUD: `adaptive-gpu-quality-v22.js` appends
  a `<details class="ei-graphics-diagnostics">` into `aside.right` (the inspector
  pane). At ≤1180 that pane is a closed drawer translated off-screen, so it is not
  painting over the canvas either.

Two intersections the probe does report are correct behaviour, not defects: the
`+ Add` quick-add trigger sits over the page dock's rounded corner
(36×10px at 1440, 42×42px at 900 — a floating action button above a floating strip,
both with transparent corners), and the tool rail's box intersected the diagnostics
panel only while the rail was still mis-positioned (§2 of
[`fix-e3-rail-over-canvas.md`](fix-e3-rail-over-canvas.md)); after that fix the rail
sits in the gutter.

## 2. M1 and M2 — the materials toolbar "printing over itself"

**Does not reproduce as spacing.** `.library-toolbar` is a wrapping flex row with real
gaps; there are no overlapping controls at any width tested:

<!-- report-verify: measurement needs the dev server plus a browser -->

    1440  bar 1116x56   display=flex wrap=wrap gap=8px rows=2
          search 654x38 flex=1 1 360px minW=160px | #typeFilter 125px | #folderFilter 150px | #sort 145px
    1024  bar  899x102  rows=3   search 484x38 | #typeFilter 388px | #folderFilter 436px | #sort 436px
     768  bar  482x102  rows=3   search 464x38 | #typeFilter 149px | #folderFilter 149px | #sort 149px
     390  bar  126x192  rows=5   search 160x38 | #typeFilter 110px | #folderFilter 110px | #sort 110px

Overlap pairs between the four controls: **zero at every width**. The only pairs the
probe reports are between the four `.sr-only` `<label>`s, which are 1×1px clipped
boxes stacked at the same coordinate by design — not visible text.

What the toolbar *did* show was a content defect in the same region: every option
label rendered twice ("All typesAll types"). Cause and fix are in
[`fix-m2-doubled-filter-labels.md`](fix-m2-doubled-filter-labels.md); the before/after
crops are [`before-m1.png`](before-m1.png) / [`after-m1.png`](after-m1.png).

## 3. Why no spacing remedy was applied

The prescribed remedies for these three symptoms were spacing changes — margins,
gaps, widths. The measurements above say the spacing is already correct: the toolbar
wraps with an 8px gap and no control intersects another, and the top-centre overlays
are stacked with clear space between them. Applying those remedies anyway would have
moved layout that measures correctly, so nothing was changed for them.

## 4. New defect found in the same pass: the materials page is a 150px column on phones

**Measured, real, reproducible on a fresh load.** At 390px the app shell kept a desktop
three-column grid and confined the page to its first column:

<!-- report-verify: measurement needs the dev server plus a browser at 390x900 -->

    browser, materials.html at 390x900
    body.final-page-entered.ui-ready   grid-template-columns: 150px 0px 240px
    main.library-page   0,56   150x1041   (viewport is 390x900)
    .library-toolbar   12,357  126x192
    #search            20,365  160x38    <- 34px wider than its own 126px panel
    #typeFilter        20,411  110x38

`localStorage` was cleared (`einvite-v54-sidebar-collapsed`, `einvite-left-width`
removed) and the page reloaded at 390px before measuring, so this is not stale
persisted state. [`after-m1-390.png`](after-m1-390.png) is what it looks like: the
"Library" heading, its description and the `Refresh` button wrapped into a ~126px
strip with the rest of the viewport empty, and the search field (`min-width:160px`
from `final-polish.css`, `!important`) sticking 34px out of its panel.

At the time this was recorded, the shell's grid template at phone width was left alone on
purpose: it reaches every non-editor page, so it belonged in its own pass with its own
before/after rather than in a bug-fix pass over three named symptoms.

**Fixed in that next pass** — [`fix-shell-mobile-rail-drawer.md`](fix-shell-mobile-rail-drawer.md)
reports the four defects behind the one symptom: a duplicate `position: sticky` rule at
(0,2,1) that kept the rail in the flow, so its `grid-area: rail` closed over two implicit
columns (`0px` and `240px`) and starved the single `minmax(0, 1fr)` column down to 150px;
a persisted `rail-collapsed` that shrank the phone drawer to 64px; a ☰ drawer control whose
desktop hide lost to `body:not(.guest) > header button`; and a « collapse control offered on
phones, where it could only do the second of those. After that pass `body` resolves `390px`
at 390px and the topbar and `main` are 390px wide, so the toolbar-scoped half needed no
change of its own: at 390px the search field now sits inside its panel (measured, and the
`min-width:160px` in `final-polish.css` is untouched).

## 5. Limits

- Every number in this file is one browser run at one viewport height (900px, 844px
  for the 390px crops); no device or DPR emulation was used beyond the viewport.
- The E2 probe exercised the editor with an object selected on the canvas. States
  that need a live collaboration session, a raster workspace, or the AI drawer were
  not entered, so an overlay collision confined to those states would not have been
  seen.
- The 390px shell measurement was taken on `materials.html` only. The same body grid
  would affect other non-editor pages, but that was not measured here, so it is not
  claimed in this file; the follow-up pass swept all 16 routes at 390px plus six rail
  pages at 390/768/1024/1366 and reports the result per page
  ([`fix-shell-mobile-rail-drawer.md`](fix-shell-mobile-rail-drawer.md)).
