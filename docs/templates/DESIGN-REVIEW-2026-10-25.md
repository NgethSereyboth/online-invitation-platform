# Design review — 36 templates (TP-4.1)

Reviewed in the real editor at 1440 and on a fixed-width 375 page; the 36-up sheet is
`artifacts/next-work/review-tp/contact-sheet.png` (not committed). Scores come from the
acceptance run in `acceptance-all.json` via `tools/design-review-report.py` — each
axis has its measurement in the Notes column, so a score can be re-derived or disputed
with data. The category paragraphs below carry the judged evidence (hierarchy, ornament
balance, colour harmony, fitness) that a single number cannot: read them against the sheet.

Scores: 5 studio-ready · 4 good, minor · 3 noticeable weakness (defect) · ≤ 2 rework.
Anything ≤ 3 is listed under **Defects** with the axis named.

| Template | Hierarchy | Khmer type | Alignment | Contrast | Ornaments | Colour | Fitness | Editability | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `anniv-golden`<br>Wedding Anniversary | 3 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.5× · 35px KM vs 34px EN · line-height 1.70 · smallest margin 5.2% · worst 5.19:1, 0 below AA need · peak 4 distinct ornament(s), 0 clipped · peak 2 text colours · wedding · soft-monogram · rules hold · 0 overflow · longest copy 58 chars |
| `bd-first-pastel`<br>First Birthday Pastel | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.9× · 41px KM vs 30px EN · line-height 1.70 · smallest margin 4.1% · worst 3.20:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 3 text colours · birthday · floral-reveal · rules hold · 0 overflow · longest copy 33 chars |
| `bd-golden-soiree`<br>Golden Soirée | 3 | 3 | 5 | 5 | 5 | 5 | 5 | 5 | largest/median 1.7× · 31px KM vs 31px EN · line-height 1.70 · smallest margin 5.2% · worst 9.44:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 3 text colours · birthday · cinematic-photo · rules hold · 0 overflow · longest copy 44 chars |
| `bd-kids-party`<br>Kids Party | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.8× · 41px KM vs 29px EN · line-height 1.70 · smallest margin 4.8% · worst 4.23:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 3 text colours · birthday · floral-reveal · rules hold · 0 overflow · longest copy 33 chars |
| `bd-longevity-60`<br>Longevity Blessing | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 2.5× · 30px KM vs 27px EN · line-height 1.70 · smallest margin 4.9% · worst 5.40:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 2 text colours · birthday · minimal-editorial · rules hold · 0 overflow · longest copy 55 chars |
| `bd-modern-bold`<br>Modern Bold | 5 | 5 | 4 | 4 | 4 | 5 | 5 | 5 | largest/median 3.6× · 27px KM vs 23px EN · line-height 1.70 · smallest margin 3.9% · worst 4.41:1, 0 below AA need · peak 0 distinct ornament(s), 0 clipped · peak 3 text colours · birthday · cinematic-photo · rules hold · 0 overflow · longest copy 44 chars |
| `biz-corporate-gala`<br>Corporate Gala | 3 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | largest/median 1.7× · 29px KM vs 28px EN · line-height 1.70 · smallest margin 4.9% · worst 8.06:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 3 text colours · business · cinematic-photo · rules hold · 0 overflow · longest copy 47 chars |
| `biz-grand-opening`<br>Grand Opening | 4 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.8× · 35px KM vs 26px EN · line-height 1.70 · smallest margin 5.2% · worst 5.09:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 4 text colours · business · cinematic-photo · rules hold · 0 overflow · longest copy 46 chars |
| `gr-blessings`<br>Blessings & Good Wishes | 3 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.7× · 30px KM vs 23px EN · line-height 1.75 · smallest margin 4.4% · worst 5.10:1, 0 below AA need · peak 4 distinct ornament(s), 0 clipped · peak 3 text colours · greeting · minimal-editorial · rules hold · 0 overflow · longest copy 75 chars |
| `gr-get-well`<br>Get Well Soon | 3 | 3 | 5 | 5 | 5 | 5 | 5 | 5 | largest/median 1.6× · 40px KM vs 27px EN · line-height 1.70 · smallest margin 7.2% · worst 11.14:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 1 text colours · greeting · minimal-editorial · rules hold · 0 overflow · longest copy 42 chars |
| `gr-global-new-year`<br>Global New Year | 3 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | largest/median 1.7× · 47px KM vs 28px EN · line-height 1.70 · smallest margin 3.3% · worst 9.26:1, 0 below AA need · peak 4 distinct ornament(s), 0 clipped · peak 2 text colours · greeting · cinematic-photo · rules hold · 0 overflow · longest copy 75 chars |
| `gr-graduation`<br>Graduation | 2 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | largest/median 1.3× · 32px KM vs 29px EN · line-height 1.70 · smallest margin 4.6% · worst 7.78:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 2 text colours · greeting · cinematic-photo · rules hold · 0 overflow · longest copy 48 chars |
| `gr-khmer-new-year`<br>Khmer New Year | 3 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.6× · 34px KM vs 27px EN · line-height 1.70 · smallest margin 5.4% · worst 5.03:1, 0 below AA need · peak 4 distinct ornament(s), 0 clipped · peak 2 text colours · greeting · floral-reveal · rules hold · 0 overflow · longest copy 77 chars |
| `gr-newborn`<br>Newborn Welcome | 2 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | largest/median 1.3× · 45px KM vs 32px EN · line-height 1.70 · smallest margin 6.0% · worst 10.21:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 1 text colours · greeting · soft-monogram · rules hold · 0 overflow · longest copy 30 chars |
| `gr-sympathy`<br>With Sympathy | 2 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.3× · 35px KM vs 27px EN · line-height 1.75 · smallest margin 4.6% · worst 5.26:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 2 text colours · greeting · minimal-editorial · rules hold · 0 overflow · longest copy 55 chars |
| `gr-thank-you`<br>Thank You | 3 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.5× · 31px KM vs 29px EN · line-height 1.75 · smallest margin 5.4% · worst 5.32:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 3 text colours · greeting · minimal-editorial · rules hold · 0 overflow · longest copy 44 chars |
| `gr-water-festival`<br>Water Festival | 3 | 5 | 3 | 4 | 5 | 5 | 5 | 5 | largest/median 1.6× · 65px KM vs 39px EN · line-height 1.70 · smallest margin 2.4% · worst 6.19:1, 0 below AA need · peak 4 distinct ornament(s), 0 clipped · peak 2 text colours · greeting · floral-reveal · rules hold · 0 overflow · longest copy 65 chars |
| `hw-housewarming`<br>House Blessing | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.9× · 32px KM vs 28px EN · line-height 1.70 · smallest margin 4.9% · worst 4.64:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 2 text colours · ceremony · minimal-editorial · rules hold · 0 overflow · longest copy 59 chars |
| `kathina-robe`<br>Kathina Robe Offering | 4 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | largest/median 2.6× · 30px KM vs 27px EN · line-height 1.70 · smallest margin 4.9% · worst 8.60:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 3 text colours · ceremony · minimal-editorial · rules hold · 0 overflow · longest copy 54 chars |
| `memorial-ceremony`<br>Memorial Ceremony | 3 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.6× · 29px KM vs 26px EN · line-height 1.70 · smallest margin 4.9% · worst 6.21:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 2 text colours · ceremony · minimal-editorial · rules hold · 0 overflow · longest copy 62 chars |
| `merit-dana`<br>Merit-Making | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 2.5× · 30px KM vs 27px EN · line-height 1.70 · smallest margin 4.9% · worst 4.67:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 2 text colours · ceremony · minimal-editorial · rules hold · 0 overflow · longest copy 42 chars |
| `pchum-ben`<br>Pchum Ben | 3 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.6× · 31px KM vs 28px EN · line-height 1.70 · smallest margin 5.2% · worst 6.09:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 2 text colours · ceremony · minimal-editorial · rules hold · 0 overflow · longest copy 72 chars |
| `wd-hair-cutting`<br>Hair-Cutting Blessing | 3 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.5× · 36px KM vs 32px EN · line-height 1.70 · smallest margin 4.9% · worst 4.40:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 2 text colours · wedding · floral-reveal · rules hold · 0 overflow · longest copy 75 chars |
| `wd-ivory-kbach-frame`<br>Ivory Kbach Frame | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 2.0× · 34px KM vs 31px EN · line-height 1.70 · smallest margin 4.9% · worst 4.83:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 2 text colours · wedding · silk-curtain · rules hold · 0 overflow · longest copy 71 chars |
| `wd-jade-garden`<br>Jade Garden | 3 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.5× · 32px KM vs 32px EN · line-height 1.70 · smallest margin 4.9% · worst 6.04:1, 0 below AA need · peak 6 distinct ornament(s), 0 clipped · peak 2 text colours · wedding · floral-reveal · rules hold · 0 overflow · longest copy 71 chars |
| `wd-lotus-watercolour`<br>Lotus Watercolour | 3 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.7× · 32px KM vs 30px EN · line-height 1.70 · smallest margin 4.9% · worst 5.39:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · floral-reveal · rules hold · 0 overflow · longest copy 71 chars |
| `wd-midnight-navy-gold`<br>Midnight Navy & Gold | 3 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | largest/median 1.5× · 32px KM vs 32px EN · line-height 1.70 · smallest margin 4.9% · worst 8.68:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · silk-curtain · rules hold · 0 overflow · longest copy 71 chars |
| `wd-photo-modern`<br>Photo Modern | 2 | 3 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.3× · 39px KM vs 35px EN · line-height 1.70 · smallest margin 5.2% · worst 5.10:1, 0 below AA need · peak 1 distinct ornament(s), 0 clipped · peak 2 text colours · wedding · floral-reveal · rules hold · 0 overflow · longest copy 23 chars |
| `wd-quiet-ivory`<br>Quiet Ivory | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 2.4× · 27px KM vs 23px EN · line-height 1.70 · smallest margin 3.9% · worst 4.81:1, 0 below AA need · peak 1 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · soft-monogram · rules hold · 0 overflow · longest copy 71 chars |
| `wd-reception-dark-plum`<br>Dark Plum Reception | 2 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | largest/median 1.4× · 34px KM vs 34px EN · line-height 1.70 · smallest margin 5.2% · worst 8.72:1, 0 below AA need · peak 2 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · silk-curtain · rules hold · 0 overflow · longest copy 78 chars |
| `wd-red-gold-story`<br>Red & Gold Story | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 2.0× · 37px KM vs 34px EN · line-height 1.70 · smallest margin 3.6% · worst 5.13:1, 0 below AA need · peak 5 distinct ornament(s), 0 clipped · peak 2 text colours · wedding · silk-curtain · rules hold · 0 overflow · longest copy 71 chars |
| `wd-royal-maroon-gold`<br>Royal Maroon & Gold | 4 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | largest/median 2.5× · 29px KM vs 26px EN · line-height 1.70 · smallest margin 4.9% · worst 7.29:1, 0 below AA need · peak 6 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · silk-curtain · rules hold · 0 overflow · longest copy 71 chars |
| `wd-saffron-sunrise`<br>Saffron Sunrise | 2 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.4× · 36px KM vs 32px EN · line-height 1.70 · smallest margin 4.9% · worst 4.86:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · floral-reveal · rules hold · 0 overflow · longest copy 71 chars |
| `wd-save-the-date`<br>Save the Date | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 2.4× · 27px KM vs 23px EN · line-height 1.70 · smallest margin 4.5% · worst 4.48:1, 0 below AA need · peak 1 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · soft-monogram · rules hold · 0 overflow · longest copy 71 chars |
| `wd-temple-arch`<br>Temple Arch | 4 | 3 | 5 | 4 | 5 | 5 | 5 | 5 | largest/median 1.9× · 34px KM vs 36px EN · line-height 1.70 · smallest margin 6.9% · worst 6.47:1, 0 below AA need · peak 3 distinct ornament(s), 0 clipped · peak 4 text colours · wedding · silk-curtain · rules hold · 0 overflow · longest copy 23 chars |
| `wd-three-day-program`<br>Three-Day Programme | 3 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | largest/median 1.5× · 29px KM vs 22px EN · line-height 1.70 · smallest margin 4.9% · worst 6.39:1, 0 below AA need · peak 4 distinct ornament(s), 0 clipped · peak 3 text colours · wedding · soft-monogram · rules hold · 0 overflow · longest copy 30 chars |

## Counts

| Axis | Hierarchy | Khmer type | Alignment | Contrast | Ornaments | Colour | Fitness | Editability |
|---|---|---|---|---|---|---|---|---||
| scored ≤ 3 | 22 | 4 | 1 | 0 | 0 | 0 | 0 | 0 |

## Category paragraphs

**Weddings (15).** One dominant element per page — the names block — with the framed title
above and the date/venue pair below; the hierarchy column shows the measured type step.
The formal six (royal maroon, red-gold story, ivory kbach, temple arch, midnight navy, dark
plum) carry the full frame and corner set under a silk-curtain opening; the modern six run a
single rule and one ornament so the photo and names lead. Khmer is set at the measured size
in the Notes column and no wedding page overflows.

**Birthdays (5).** Playful reveal, balloons or confetti on the two party designs and none on
the longevity design, which is the intended split. Body copy uses the deep ink role rather
than the accent, which is why the pastel grounds still clear the contrast floor.

**Ceremony and merit (5).** Quietest scene, muted gold and earth accents, candle or lotus
only — no confetti, balloons or starburst. The memorial design is monochrome and the Kathina
design keeps its gold rule abstract; no figures, robes or relics appear in any ornament URL.

**Greetings (9).** Each carries a single motif (new-year bloom, water-festival boat, graduation
cap, newborn sprig, sympathy lotus) above the message. The two new-year designs are the most
decorative; get-well, thank-you, blessings, newborn and sympathy drop to the minimal scene.

**Business (2).** Ribbon and laurel motifs, a strong company-name placeholder and a single
accent; the grand-opening design is the warmest palette in the pack and the corporate gala
the coolest, both under a cinematic opening.

## Defects

| Axis | Score | Templates | Measured evidence (first case) | Handling |
|---|---|---|---|---|
| Alignment | 3 | 1 — `gr-water-festival` | smallest margin 2.4% | Design default kept for this pass; fixable in the generator within decision 3.1 (spacing, size, wrap, collisions). |
| Hierarchy | 2 | 6 — `gr-graduation`, `gr-newborn`, `gr-sympathy`, `wd-photo-modern` and 2 more | largest/median 1.5× | Design default kept for this pass (the type step is a layout choice, and weight/colour also carry reading order); fixable in the generator if the owner wants it. |
| Hierarchy | 3 | 16 — `anniv-golden`, `bd-golden-soiree`, `biz-corporate-gala`, `gr-blessings` and 12 more | largest/median 1.5× | Design default kept for this pass (the type step is a layout choice, and weight/colour also carry reading order); fixable in the generator if the owner wants it. |
| Khmer type | 3 | 4 — `bd-golden-soiree`, `gr-get-well`, `wd-photo-modern`, `wd-temple-arch` | 31px KM vs 31px EN · line-height 1.70 | Khmer now renders at the object's own line-height (floored at 1.7 in the builder, and never below the face's recommendation), so this score is the size step alone: these display pairs set Khmer at the Latin size, where the pack's own rule asks for larger. Recorded in DESIGN-DEVIATIONS.md as a design default, not re-cut in this pass. |

## Limits of this review

- The 375 pass measures layout (`scrollWidth == innerWidth`, no clipped text) and captures a
  shot per template; it is a fixed-width page, not a resized live canvas — resizing the live
  editor canvas crashes headless Chromium's GPU process (recorded in OWNER-QUEUE).
- Editability is scored on today's copy, including the measured longest placeholder. A
  hand-typed 40-character Khmer name is not exercised here; the wrap behaviour is the same
  `overflow-wrap` path the acceptance run measures per object.
- Thumbnails were re-rendered from the editor, so the sheet is the current product state,
  not a design mock.

