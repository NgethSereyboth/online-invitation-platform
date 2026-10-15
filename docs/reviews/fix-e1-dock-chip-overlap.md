# E1 — the page dock's chips paint over their own controls

Scope: the editor page dock (`#workflowPageDock`) on `index.html`. The reported
symptom was that the dock's page labels "print over each other". Measured, the three
siblings in the dock never overlap; what collides is the *content inside one chip* —
the chip was narrower than its own grid tracks, so the page number ran under the
thumbnail, and the label ran under the `•••` / drag-handle band and wrapped to a
second line inside a 50px-tall box.

Every number is printed next to the command that produced it. Blocks that need the dev
server and a browser carry a `report-verify: measurement` declaration; the rest are
re-runnable with
`node tools/report-verify.mjs docs/reviews/fix-e1-dock-chip-overlap.md`.

## 1. The before state, from the declarations that shipped

The chip's grid asked for more width than the fixed width later rules gave it:

```
$ git show HEAD:src/css/workflow-creation-flow-v4.css | grep -o 'grid-template-columns:22px 40px minmax(40px,1fr)'
grid-template-columns:22px 40px minmax(40px,1fr)
```

```
$ git show HEAD:src/css/workflow-creation-flow-v4.css | grep -o 'padding-right:25px!important'
padding-right:25px!important
```

```
$ git show HEAD:src/css/workflow-pro-editor-v6.css | grep -o 'workflow-page-number{margin-left:19px}'
workflow-page-number{margin-left:19px}
```

```
$ git show HEAD:src/css/organized/workflow-final-audit-v7.css | grep -o 'workflow-page-chip{width:1[0-9]*px!important;min-width:1[0-9]*px!important}'
workflow-page-chip{width:112px!important;min-width:112px!important}
workflow-page-chip{width:118px!important;min-width:118px!important}
```

From those declarations the chip's minimum honest width is
`8 (padding-left) + 22 (number column) + 6 (gap) + 40 (thumbnail) + 6 (gap) +
40 (name column min) + 25 (right band) = 147px`, against a fixed **118px** at
1181–1450px and **112px** at 821–1180px: 29px and 35px short. The overflow lands in
the right-hand band, which is exactly where the two absolutely positioned affordances
live (`page-experience-v22.css`: `.v22-dock-drag-handle{right:25px;width:22px}`;
`workflow-creation-flow-v4.css`: `.workflow-page-more{right:5px;width:20px}`).

Two consequences, both visible in [`before-e1.png`](before-e1.png):

- The number ran under the thumbnail. `.workflow-page-number` is 20px wide with
  `margin-left:19px` inside a 22px column, so its box spans chip-relative 27px → 47px
  while the thumbnail column starts at 8 + 22 + 6 = 36px: **11px of the number sits
  underneath the thumbnail**.
- The label had a 40px column in a content box of 118 − 8 − 25 = 85px, so the grid was
  29px wider than its box, pushing the name under the `•••` band; the `.v54-nav-text`
  wrapping rules in `editor-styles.css` then broke it onto a second line inside a
  50px chip.

## 2. The fix

The chip now states the space it needs as tokens instead of hard-coding a width
(`src/css/tokens.css`):

```css
--editor-dock-chip-gap:6px;
--editor-dock-chip-slot-number:20px; /* .workflow-page-number: width 20px */
--editor-dock-chip-thumb:var(--space-10);
--editor-dock-chip-name-min:var(--space-12);
--editor-dock-chip-name-max:84px;
--editor-dock-chip-tools:47px;      /* v22 drag handle (25+22px) + v4 "•••" (5+20px) */
--editor-dock-chip-min:calc(var(--space-2) + var(--editor-dock-chip-slot-number)
  + var(--editor-dock-chip-gap) + var(--editor-dock-chip-thumb)
  + var(--editor-dock-chip-gap) + var(--editor-dock-chip-name-min)
  + var(--editor-dock-chip-tools));
```

`workflow-creation-flow-v4.css` uses them for the grid, the minimum width and the
right band; `workflow-pro-editor-v6.css` drops the `margin-left:19px` indent, which
existed only to clear the order badge — and the badge is deliberately hidden inside
the dock (`page-experience-v22.css`:
`#workflowPageDock .workflow-v6-order-badge{display:none!important}`). Reserving 40px
for that badge was what pushed the dock's track into a scroll at 1200px; the number's
own 20px is what belongs there.

```
$ grep -o 'grid-template-columns:var(--editor-dock-chip-slot-number) var(--editor-dock-chip-thumb) minmax(0,1fr)!important' src/css/workflow-creation-flow-v4.css | wc -l
2
```

```
$ grep -o 'min-width:var(--editor-dock-chip-min)!important' src/css/workflow-creation-flow-v4.css | wc -l
2
```

`--editor-dock-chip-tools` is the two-affordance band; the label column abuts it, so a
truncated name ends exactly at the drag handle's left edge. That is the original 25px
band's behaviour (the label met the `•••` band there too), kept deliberately. If the
dock's badge suppression is ever lifted, the number slot must grow to ≥36px — the
token comment says so.

## 3. Verification

<!-- report-verify: measurement needs the dev server plus a browser; the numbers are the layout of one run -->

Chips measured with `artifacts/measure_chips.js` (child rects plus pairwise
intersections) through `agent-browser` against
`http://127.0.0.1:4175/index.html` at 1280×900 with a second page added, so both chips
exist: chip width **175px**, grid `20px 40px 46px`, padding `5px 47px 5px 8px`,
**0 child pairs intersect, 0 children escape the chip**.

| viewport | chip w | track (scroll / client) | overlap pairs | escapes |
| --- | --- | --- | --- | --- |
| 900 | 175 | 625 / 625 fits | 0 | 0 |
| 1024 | 175 | 651 / 651 fits | 0 | 0 |
| 1100 | 175 | 651 / 651 fits | 0 | 0 |
| 1180 | 175 | 651 / 651 fits | 0 | 0 |
| 1200 | 175 | 421 / 421 fits | 0 | 0 |
| 1280 | 175 | 501 / 501 fits | 0 | 0 |
| 1440 | 175 | 651 / 651 fits | 0 | 0 |
| 1600 | 175 | 651 / 651 fits | 0 | 0 |
| 1920 | 175 | 651 / 651 fits | 0 | 0 |
| 700 | 149 | 499 / 499 fits | 0 | 0 |
| 390 | 182 / 149 | 369 / 182 scrolls | 0 | 0 |

The `•••` and drag-handle band was measured with `artifacts/measure_chips_more.js`,
which appends the exact element the v4 add-page path appends — those affordances are
only in the DOM for chips created through that path:

```
$ grep -n "workflow-page-more" src/js/workflow-creation-flow-v4.js | cut -c1-120
158:      const more=document.createElement('span');more.className='workflow-page-more';more.textContent='•••';mor
```

<!-- report-verify: measurement same run as above: browser plus server -->

With the affordance appended, at 900 / 1200 / 1280 / 1600 / 700 the label box ends
**22px** before the `•••` at every width, with no intersecting pairs and no escapes.
The drag-handle band (right 25px → 47px) abuts the label column, as described in §2.

Screenshots, all 4× the dock region with the same crop:
[`before-e1.png`](before-e1.png) — "Main hero" wrapped onto two lines, the number
hidden under the thumbnail, the `•••` glyph printed over "Title Page";
[`after-e1.png`](after-e1.png) and [`after-e1-1600.png`](after-e1-1600.png) — each
chip reads `1 | thumbnail | Main hero`, and the 1280px track fits with no scroll. The
1200px dock is also visible in
[`after-e3-canvas-1200.png`](after-e3-canvas-1200.png): both chips plus `Flow` and `+`
inside a 530px dock.

## 4. What was not verified

- The chips were measured in design mode on a fresh invitation. A page name longer
  than `--editor-dock-chip-name-max` truncates (84px, 64px at ≤1180, 48px at ≤700); a
  very long single word was measured to grow the label column and scroll the track
  rather than escape the chip, but the ellipsis itself was not captured.
- Below 640px the dock is a horizontally scrolling strip by design
  (`.workflow-page-dock-track{overflow-x:auto}` plus the v7 scroll-margin), so the
  390px row above scrolls; that is intended phone behaviour, not a fixed defect.
- Content mode hides the dock entirely
  (`.studio-content-mode .workflow-page-dock{display:none!important}`) and was not
  exercised.
