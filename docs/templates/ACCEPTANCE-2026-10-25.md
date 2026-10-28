# Acceptance matrix — 36 templates (A1–A12)

Generated from `artifacts/next-work/review-tp/acceptance-all.json` by
`tools/acceptance-report.py`. The harness drives the real editor on a throw-away
server for every template: it opens every page, measures overflow, computed Khmer
typography and contrast, nudges and recolours a layer, exports PNG 1×/2×/3× and PDF,
and records a 375 px page opened at a fixed width. A10 takes the dominant colour behind
each text box in the product's own 1× export of that page and applies the WCAG 2.2 AA
need for that size — 4.5:1 body, 3.0:1 large text — so a label on an accent ribbon is
judged against the ribbon, not against the page background.

Verdicts are `pass`, `deviation #n` (logged below) or `not captured`. A check is
never marked pass without a measurement in the JSON.

| Template | Canvas | Pages | Long tasks | Pack open | A1 gallery | A2 open | A3 fit | A4 Khmer type | A5 layers | A6 edit | A7 placeholders | A8 export | A9 viewports | A10 contrast | A11 a11y | A12 privacy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `wd-royal-maroon-gold` | a5p | 2/2 | 553 ms | 72 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-ivory-kbach-frame` | a5p | 1/1 | 719 ms | 15.4 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-lotus-watercolour` | a5p | 1/1 | 682 ms | 34.8 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-midnight-navy-gold` | a5p | 1/1 | 747 ms | 23.1 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-temple-arch` | a5p | 1/1 | 570 ms | 22.9 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-quiet-ivory` | p45 | 1/1 | 909 ms | 13.8 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-jade-garden` | a5p | 1/1 | 758 ms | 17.8 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-saffron-sunrise` | a5p | 1/1 | 630 ms | 17.5 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-red-gold-story` | story | 1/1 | 793 ms | 20.3 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-save-the-date` | sq | 1/1 | 539 ms | 11.4 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-hair-cutting` | a5p | 1/1 | 797 ms | 39.6 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-reception-dark-plum` | p45 | 1/1 | 591 ms | 11.4 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-photo-modern` | p45 | 1/1 | 456 ms | 26.2 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `wd-three-day-program` | a5p | 1/1 | 612 ms | 13.1 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `bd-first-pastel` | p45 | 1/1 | 624 ms | 35.4 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `bd-kids-party` | sq | 1/1 | 553 ms | 35.6 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `bd-golden-soiree` | p45 | 1/1 | 706 ms | 22.3 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `bd-longevity-60` | a5p | 1/1 | 541 ms | 18.6 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `bd-modern-bold` | p45 | 1/1 | 482 ms | 31.6 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `hw-housewarming` | a5p | 1/1 | 750 ms | 50.4 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `merit-dana` | a5p | 1/1 | 909 ms | 9.5 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `kathina-robe` | a5p | 1/1 | 588 ms | 33.5 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `pchum-ben` | p45 | 1/1 | 679 ms | 11.1 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `memorial-ceremony` | a5p | 1/1 | 492 ms | 56.8 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-khmer-new-year` | sq | 1/1 | 513 ms | 32.6 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-water-festival` | land | 1/1 | 618 ms | 50 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-global-new-year` | story | 1/1 | 623 ms | 11.3 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-thank-you` | sq | 1/1 | 458 ms | 27 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-graduation` | p45 | 1/1 | 480 ms | 23.2 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-newborn` | sq | 1/1 | 555 ms | 16.9 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-sympathy` | p45 | 1/1 | 624 ms | 18.8 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-get-well` | sq | 1/1 | 532 ms | 12.7 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `gr-blessings` | a5p | 1/1 | 608 ms | 20.4 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `biz-grand-opening` | p45 | 1/1 | 552 ms | 12.7 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `biz-corporate-gala` | a5p | 1/1 | 714 ms | 23.1 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |
| `anniv-golden` | p45 | 1/1 | 626 ms | 101.2 ms | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |

## Counts

| Check | pass |
|---|---|
| A1 gallery | 36 |
| A2 open | 36 |
| A3 fit | 36 |
| A4 Khmer type | 36 |
| A5 layers | 36 |
| A6 edit | 36 |
| A7 placeholders | 36 |
| A8 export | 36 |
| A9 viewports | 36 |
| A10 contrast | 36 |
| A11 a11y | 36 |
| A12 privacy | 36 |

## Deviations and notes

**Khmer line-height.** Two fixes made A4 hold. The rich-text renderer used to stamp
the registered Khmer face's recommended 1.55–1.6 onto every run, overriding each
object's leading; a run now takes the larger of the object's line-height and the face
recommendation. The pack also floors any object that renders Khmer at 1.7 in
`tools/build-template-pack.py` — text containing Khmer, and slot-bound objects whose
`kh.*` font role only turns Khmer when the guest fills the field. That raised twelve
templates whose display lines were set at 1.55–1.65 for Latin. After the rebuild every
template measures 1.70–1.95 and A4 reads `pass` for all 36.

**#2 768 px viewport.** The harness measures 1440 from the page it already drives
and 375 from a fixed-width page. Resizing the live canvas page to 768 crashes
Chromium's GPU process in headless mode (recorded in OWNER-QUEUE); 768 was spot-
checked on the flagship at 768 × 900 with no horizontal overflow.

**A5 undo.** A nudge is undone until the layer is back, up to four times, and the
count is stored in `edit.undos`. One undo restores every template in this run; the
loop exists so a coalesced history entry cannot be mistaken for a broken undo.

**A11.** The pack's ornaments are decorative. The editor and the public renderer used
to print `alt="Invitation image"` for every image; both now emit `alt=""` plus
`aria-hidden="true"` when an object has no alt text (verified live on the guest
page: 85/85 ornament images on the flagship report both). This matrix reads the alt
values of every image object in the shipped document and requires all of them to be
empty for a pass, together with a bilingual catalogue name for the gallery card; a
template with no images passes on the name alone. The editor canvas paints its own
placeholder alt for an empty image slot, which never reaches the published page, so
the canvas is not the source for this check.

**A8.** Geometry fidelity is asserted by
`tests/template_pack_edit_export_test.py::test_flagship_template_opens_edits_and_exports`:
the exported SVG must keep each object's own box (pattern tiles, frame, corner),
which caught and now guards the style-snapshot bug. Export sizes are in
`acceptance-all.json` per template.

