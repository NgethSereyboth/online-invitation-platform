# E3 — the tool rail floats on top of the page, not beside it

Scope: the editor's floating tool rail (`#canvasViewport > .ei-tool-rail`) on
`index.html`. Measured, the rail painted over the invitation page — 46px of the page at
1200px, 23px at 1280px — because a `position:sticky` box never leaves the flow, so the
rail's static position sat on the viewport's content-box left edge, which is exactly
where the centred `.canvas-frame` starts.

Blocks that need the dev server and a browser carry a `report-verify: measurement`
declaration; the rest are re-runnable with
`node tools/report-verify.mjs docs/reviews/fix-e3-rail-over-canvas.md`.

## 1. Two rules, and only one of them can win

`editor-pro.css` places the rail, and it is the only rail rule that competes, because it
is bundled **unlayered** while every corrective rule in
`organized/workflow-final-audit-v7.css` sits inside `@layer components`. Unlayered
declarations beat all layered ones regardless of specificity, so the audit file's
`position:absolute;margin:0` — written for this exact bug — could never take effect.

```
$ git show HEAD:src/css/editor-pro.css | grep -o '\.ei-tool-rail{position:sticky[^}]*}'
.ei-tool-rail{position:sticky;left:12px;top:18px;z-index:70;width:46px;padding:6px;display:flex;flex-direction:column;gap:5px;border:1px solid var(--app-line);border-radius:15px;background:color-mix(in srgb,var(--app-surface) 93%,transparent);box-shadow:0 16px 44px rgba(0,0,0,.15);backdrop-filter:blur(18px);align-self:flex-start;margin:18px 0 -100%;transform:translateZ(0)}
```

```
$ git show HEAD:src/css/organized/workflow-final-audit-v7.css | grep -o 'body\.studio-experience #canvasViewport.\{0,3\}ei-tool-rail{[^}]*}'
body.studio-experience #canvasViewport>.ei-tool-rail{position:absolute;left:12px;top:18px;margin:0;align-self:auto}
body.studio-experience #canvasViewport>.ei-tool-rail{left:7px;top:7px}
```

The two files differ in exactly one way that decides the cascade: `editor-pro.css`
never opens a layer, while the audit file wraps everything it contains in
`@layer components`:

```
$ grep -o '@layer' src/css/editor-pro.css | wc -l
0
```

```
$ grep -o '@layer' src/css/organized/workflow-final-audit-v7.css | wc -l
1
```

That is why the audit rule loses despite the higher specificity, and it is why the fix
in §3 goes into `editor-pro.css` (inside a plain media query, still unlayered).

<!-- report-verify: measurement needs the dev server and a browser; one run's CSSOM -->

The browser confirmed the same thing from its own matched-rule list before the fix: the
sticky declaration was reported with no layer wrapper and the audit rule inside
`CSSLayerBlockRule[name=components]`, and `getComputedStyle(rail).position` was `sticky`
with all four declarations present in the bundle.

## 2. Why sticky put it on the page

`left:12px` on a sticky box is a scroll-time inset, not a static offset. The rail's flow
position is the viewport's content-box left edge, and the canvas frame is positioned
there too (viewport padding `52px 70px 100px`, i.e. a 70px gutter each side).

<!-- report-verify: measurement needs the dev server and a browser; one run's layout -->

| rail `position` | rail left (px) | frame left (px) |
| --- | --- | --- |
| `sticky` (as shipped) | 413 | 411 |
| `static` + `margin-left:-58px` | 353 | 411 |
| `relative` + `margin-left:-58px` | 365 | 411 |

353 is what `left:12px` was meant to produce: 12px inside the padding box (341) and 12px
clear of the canvas (411). The gutter was right; the rail was not in it.

There is a second trap, and it cost a fix attempt: **Chrome resolves a sticky inset
against the box's margin box.** Shrinking only `margin-left` to −58px changed the
rendered left edge from 413 to … 413:

<!-- report-verify: measurement same run as above -->

| `position` | `margin-left` | rail left (px) |
| --- | --- | --- |
| sticky | 0 | 413 |
| sticky | −58px | 413 |
| sticky | −150px | 413 |
| relative | −58px | 365 |

The inset has to shrink by the same amount for the shift to survive.

## 3. The fix

`src/css/editor-pro.css` keeps the rail sticky (it genuinely follows the canvas —
§4) and moves both the margin and the inset into the gutter, desktop only, with the
gutter value named in `src/css/tokens.css`:

```css
/* src/css/tokens.css */
--editor-rail-inset:12px;
--editor-canvas-gutter:70px;

/* src/css/editor-pro.css */
@media(min-width:1181px){.ei-tool-rail{
  margin-left:calc(var(--editor-rail-inset,12px) - var(--editor-canvas-gutter,70px));
  left:calc(var(--editor-rail-inset,12px) - var(--editor-canvas-gutter,70px))}}
```

1181px is the project's own desktop boundary (`editor-responsive-contract-v27.js`:
`mode() = innerWidth<=820 ? 'mobile' : innerWidth<=1180 ? 'compact' : 'desktop'`). At
≤1180 the contract shrinks the viewport gutter to 12px and centres the canvas, so there
is nothing to offset — a −58px shift there would move the rail out of the viewport and
over the left pane. The new rule lands unlayered, like the declaration it corrects (last
line of the block in §1).

## 4. Verification

<!-- report-verify: measurement needs the dev server plus a browser; layout of one run -->

`artifacts/measure_e3.js` (rail rect and `position`, frame rect, gutter, overlap) through
`agent-browser`, before and after:

| viewport | before rail x | frame x | before overlap | after rail x | after gap |
| --- | --- | --- | --- | --- | --- |
| 1920 | 413 | 756 | none | 393 | 332 |
| 1600 | 413 | 596 | none | 393 | 172 |
| 1440 | 413 | 516 | none | 393 | 92 |
| 1360 | 413 | 476 | none | 393 | 52 |
| 1280 | 413 | 436 | 23px of the page covered | 393 | 12 |
| 1240 | 413 | 416 | 43px | 393 | 12 |
| 1200 | 413 | 411 | 46px | 393 | 12 |
| 1190 | 413 | 411 | 46px | 393 | 12 |
| 1181 | 413 | 411 | 46px | 393 | 12 |
| 1180 | 131 | 414 | none | 131 | 237 |
| 1100 | 131 | 374 | none | 131 | 197 |
| 1024 | 131 | 336 | none | 131 | 159 |
| 900 | 131 | 274 | none | 131 | 97 |
| 820 | 65 | 201 | none | 65 | 90 |
| 780 | 58 | 181 | 1px vertical graze | 58 | 1px graze |
| 700 | 58 | 141 | none | 58 | none |

Sticky following is intact — with the rail in the gutter, scrolling the canvas viewport
300px and 900px leaves the rail pinned at `[353, 271]`:

<!-- report-verify: measurement same run as above -->

| viewport `scrollTop` | rail `[left, top]` |
| --- | --- |
| 0 | `[353, 271]` |
| 300 | `[353, 271]` |
| 900 | `[353, 271]` |

Screenshots, cropped to the canvas viewport at the same rect:
[`before-e3-canvas-1200.png`](before-e3-canvas-1200.png) — the rail's panel covers the
left 46px of the page and clips the "a" of the dek;
[`after-e3-canvas-1200.png`](after-e3-canvas-1200.png) — the rail sits in the gutter and
the page is whole; [`after-e3-canvas-1280.png`](after-e3-canvas-1280.png) — the 1280px
case, 12px gap; [`after-e3-780.png`](after-e3-780.png) — the horizontal mobile rail.

## 5. What was not fixed, and why

- **780px, 1px vertical graze.** Below 781px the rail turns horizontal and sits in the
  top gutter (`position:absolute;left:7px;top:7px`); at exactly 780px its bottom edge
  meets the canvas frame's top edge with a 1px overlap. The screenshot shows no clipping
  — the frame's rounded top-left corner is visible below the rail — and the geometry is
  identical before and after this change, so it is pre-existing. Closing it means
  changing the ≤780 rail height or the mobile viewport's top padding, which is a wider
  mobile-layout change than this defect justifies. Reported, not fixed.
- **≤1180 relies on the centred canvas.** With the gutter at 12px the rail cannot have
  its own column; it does not overlap today because `.canvas-frame` is centred and lands
  well to the right of the rail (97–237px of clearance measured). A page wider than the
  viewport's content box would reduce that clearance; that state was not produced, so it
  is a residual risk rather than a measured defect.
- The audit file's inert `position:absolute` rule for the same element was left in
  place. It agrees with the real layout today (the rail is sticky; the gutter offsets
  keep it clear), but if `editor-pro.css` is ever wrapped in `@layer components` that
  rule will start winning and remove the offset's meaning.
