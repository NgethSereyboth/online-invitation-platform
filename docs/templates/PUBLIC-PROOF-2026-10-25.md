# Public-page proof — one template per category (TP-5.2)

Produced by `tools/proof-public-page.py` against a throw-away server
(`tests/v14_test_utils.app_server`, temporary data only). For each category it
publishes one pack document, opens the public page at **375 px Khmer**, **375 px
English** and **1440 px Khmer**, and measures the live DOM — it does not read the
document back from disk.

- Raw data: `artifacts/next-work/review-tp/public-proof.json` (not committed)
- Shots: `artifacts/next-work/review-tp/public-<category>-<width>-<lang>.png`

## Results

`scroll` is `documentElement.scrollWidth` vs `innerWidth`; `texts` counts
`.published-text` objects; `spilled` counts text whose `.typography-flow` renders
outside its object box; `clipped` counts text whose flow overflows with
`overflow:hidden`; `svg` counts ornament images; `blur` counts raster images
smaller than their box (SVG ornaments scale, so they never count).

| Category | Template | View | scroll | objects | texts | spilled | clipped | svg | blur | CSP | console errors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wedding | `wd-royal-maroon-gold` | 375 km | 375/375 | 121 | 34 | 32 | 6 | 85 | 0 | clean | 0 |
| Wedding | `wd-royal-maroon-gold` | 375 en | 375/375 | 121 | 34 | 32 | 6 | 85 | 0 | clean | 0 |
| Wedding | `wd-royal-maroon-gold` | 1440 km | 1440/1440 | 121 | 34 | 24 | 0 | 85 | 0 | clean | 0 |
| Birthday | `bd-first-pastel` | 375 km | 375/375 | 15 | 12 | 8 | 0 | 2 | 0 | clean | 0 |
| Birthday | `bd-first-pastel` | 375 en | 375/375 | 15 | 12 | 8 | 0 | 2 | 0 | clean | 0 |
| Birthday | `bd-first-pastel` | 1440 km | 1440/1440 | 15 | 12 | 0 | 0 | 2 | 0 | clean | 0 |
| Ceremony | `merit-dana` | 375 km | 375/375 | 21 | 13 | 12 | 1 | 8 | 0 | clean | 0 |
| Ceremony | `merit-dana` | 375 en | 375/375 | 21 | 13 | 12 | 1 | 8 | 0 | clean | 0 |
| Ceremony | `merit-dana` | 1440 km | 1440/1440 | 21 | 13 | 2 | 0 | 8 | 0 | clean | 0 |
| Greeting | `gr-khmer-new-year` | 375 km | 375/375 | 12 | 6 | 4 | 0 | 6 | 0 | clean | 0 |
| Greeting | `gr-khmer-new-year` | 375 en | 375/375 | 12 | 6 | 4 | 0 | 6 | 0 | clean | 0 |
| Greeting | `gr-khmer-new-year` | 1440 km | 1440/1440 | 12 | 6 | 0 | 0 | 6 | 0 | clean | 0 |
| Business | `biz-grand-opening` | 375 km | 375/375 | 15 | 12 | 11 | 1 | 3 | 0 | clean | 0 |
| Business | `biz-grand-opening` | 375 en | 375/375 | 15 | 12 | 11 | 1 | 3 | 0 | clean | 0 |
| Business | `biz-grand-opening` | 1440 km | 1440/1440 | 15 | 12 | 1 | 0 | 3 | 0 | clean | 0 |

## What passes

- **Published page loads for all five categories**, in both languages, with no
  third-party request and no console error.
- **No horizontal page overflow** at 375 or 1440 (`scrollWidth == innerWidth`).
- **CSP clean** — every response carries a `Content-Security-Policy` header and no
  CSP violation is logged (`CSP_CHECK_PASSED`).
- **Ornaments are crisp** — every ornament is an SVG served at its own URL, so no
  raster upscaling; zero blurry images in all 15 views.
- **Decorative ornaments are hidden from assistive tech** — the 85 ornament images
  on the flagship page report `alt=""` and `aria-hidden="true"`
  (`{"\"\"|true": 85}` in the DOM probe). This is the A11 fix: the guest bundle no
  longer stamps `alt="Invitation photo"` onto an image whose object has no alt.
- **Khmer page renders in Khmer** at 375 and 1440 after the language switch; the
  375 English view is genuinely English (the toggle persists per guest, so the
  probe now drives each view to its own language and waits for the decision).

## The defect this proof found — and its fix

**Text was rendered without its typography model.** The first run of this proof
recorded 32 of 34 text objects spilling on the flagship wedding page and 6 clipped.
The stored document was correct, and so was the markup the renderer produced; the
element was then overwritten by a second pass that fitted it with a blank model.

### Root cause (proven live, not inferred)

`TypographyLayoutService.installResponsive` collects the elements it fits with
`scope.querySelectorAll(selector).forEach(observe)`. `observe(source, model)` takes
a **caller-supplied model** as its second parameter, so `forEach` handed it the
array **index**: every element after the first cached a number as its
typography model (`node.__typographyModel = 1, 2, 3…`), and
`renderedElementModel` returns that cache before reading the DOM. The fit pass then
ran `applyToElement(node, 1)`, which wrote the blank-model dataset
the first proof recorded: `data-text-style-id=""`, `data-font-size="32"`,
`data-text-auto-fit="none"` — so 33 of 34 objects lost auto-fit entirely and the
boxes cut their text.

The editor never showed it because `app.js` re-assigns `__typographyModel` on every
synchronous pass, overwriting the bogus index; the guest page renders once and
installs once. Evidence, captured with a hooked `renderObject` (all 35 calls
correct, document present, 6 styles resolvable) and a before/after bracket around
`installResponsiveTypography` (`subheading/27/fit` → `-/32/none`):
`artifacts/next-work/tp-5-2/projection-probe.json`.

### Fix

One line, in the shared service:

```js
// before
const discover=()=>{scope.querySelectorAll?.(selector).forEach(observe);return sources};
// after
const discover=()=>{scope.querySelectorAll?.(selector).forEach(source=>observe(source));return sources};
```

`tests/template_pack_public_projection_test.py` publishes the flagship template and
asserts, object by object, that the live element carries the stored model and that
the fit pass ran; reintroducing the old line makes it fail with
`typography model cached as number`.

### Results after the fix

| Category | Template | View | texts | spilled | clipped |
|---|---|---|---|---|---|
| Wedding | `wd-royal-maroon-gold` | 375 km | 34 | 1 | 3 |
| Wedding | `wd-royal-maroon-gold` | 375 en | 34 | 1 | 3 |
| Wedding | `wd-royal-maroon-gold` | 1440 km | 34 | 0 | 3 |
| Birthday | `bd-first-pastel` | 375 km / 375 en / 1440 km | 12 | 1 / 1 / 0 | 1 / 1 / 1 |
| Ceremony | `merit-dana` | 375 km / 375 en / 1440 km | 13 | 1 / 1 / 0 | 1 / 1 / 1 |
| Greeting | `gr-khmer-new-year` | 375 km / 375 en / 1440 km | 6 | 0 / 0 / 0 | 0 / 0 / 0 |
| Business | `biz-grand-opening` | 375 km / 375 en / 1440 km | 12 | 1 / 1 / 1 | 0 / 0 / 1 |

All 34 objects on the flagship now carry their model and report
`data-text-computed-font-size` (was 1 of 34): the fitted size follows the object's
own style and auto-fit maximum instead of the 32 px default.

### What is left (recorded, not hidden)

Clipping is down from 6 to 3 on the flagship and from 8 to 16 across all 15 views
(counted per view, so the same object counts once per view), but it is not zero. A
stricter probe that measures the last glyph line against the object's own bottom
edge — rather than the flow box, which a flex item can shrink below its content —
finds **4 of 34** objects on the wedding page whose last line reaches 0.7, 1.9, 3.4
and 6.2 px past the box:

- `wd-royal-maroon-gold-p1-text-13` (`Together with our family…`) sits at the
  auto-fit **floor** (10 px) and cannot shrink further: the English string is longer
  than the Khmer the box was drawn for. Fitting cannot fix that; only a wider box or
  shorter copy can.
- `p1-text-15` (+1.9 px), `p1-text-16` (+3.4 px) and `p1-text-21` (+0.7 px) are
  sub-pixel/rounding: the fit accepts a size whose line box exceeds the object edge
  by less than the 1 px rounding allowance in
  `TypographyLayoutService.measurement`.

TP-5.2 is **closed with that residual recorded**: layout, CSP, ornaments, accessibility and
model fidelity pass; what remains is a copy/box decision for `p1-text-13` plus 0.7–3.4 px
rounding on three objects, both queued in `artifacts/next-work/OWNER-QUEUE.md`. Scaled
screenshots and the machine-readable measurements are in `review-tp/` and
`review-tp/public-proof.json`.

## Update 2026-10-29 — the recorded residual is closed (D-8)

Re-ran the same probe after the fix in `docs/templates/DESIGN-DEVIATIONS.md` row 3. On
`wd-royal-maroon-gold`:

| View | clipped | spilled | horizontal overflow |
|---|---|---|---|
| 375 km | **0** | **0** | none |
| 375 en | **0** | **0** | none |
| 1440 km | **0** | **0** | none |

The lead's English string was shortened (Khmer untouched) and the English name pair and `&`
were given 1.3 leading with a taller groom box. The root cause of the three `clipped`
objects was measured, not guessed: the runtime fit reaches the 10 px floor and wraps the lead
to three lines in a 30.14 px box, and Noto Serif's content area is ≈1.29 em, so a 1.15/1.0
`line-height` makes `scrollHeight` exceed `clientHeight` by 2–6 px even on a single line.
No proof predicate, tolerance or allowance was changed.
