# OKID template pack v1 — 100 event templates (designed by Claude)

This folder is **design source material**, not app code. Claude planned and designed it; the Freebuff agent integrates it under
`docs/HISTORY.md`. Everything here is original work (no third-party artwork, no copied templates).

46 designs are Khmer-led with an English companion line; **23** are English-led — **The Olive Letter**, **Amber Arch**, **Cathedral Rose** and the 2026 event additions.

```
template-pack/
  README.md                 this file
  catalog.json              100 entries: id, category, canvas, names (EN/KM), tags, pages, palette, typography, photo slots
  templates/<id>.json       one design spec per template (layer lists, percent coordinates, palette roles)
  ornaments/*.svg           64 original SVG ornaments (lotus, kbach corners/strips, dividers, frames, skyline, confetti ...)
  copy-bank.json            ALL Khmer + English copy (117 keys) + Khmer calendar words/digits. The only Khmer source for the pack.
  KHMER-COPY-MAP.md         the same copy as a table for native review (word-break marks stripped)
  fonts.json                font roles -> Google Fonts OFL families
  schema/template.schema.json   format description
  generator/                Python source that produced everything above (re-run to change a design)
  previews/                 reference renders (QA only - never ship)
```

## Format in one minute

* A template has 1-2 **pages** on one of five **canvases**: `a5p` 1000x1414, `p45` 1080x1350, `sq` 1080x1080, `story` 1080x1920, `land` 1600x900.
* A page is an ordered list of **layers** (bottom to top): `bg`, `shape` (rect/ellipse/line), `svg` (ornament), `pattern` (tiled ornament),
  `photo` (placeholder slot: rect/ellipse), `text`.
* `x y w h` are **percentages of the canvas**. `size`, `strokeWidth`, `radius`, `tile`, `frame.width` are **pixels at the declared canvas width**
  (multiply by `renderWidth / canvas.w`).
* **Colour is never hex.** Layers name palette roles: `bg paper ink soft accent accent2 deep line` (+ optional `sky wash1 wash2`).
  Re-theming = replacing the palette object. Gradient `bg.fill = {gradient:{angle, stops:[[role,0..1],...]}}`.
* **Ornament recolour:** monotone SVGs use `currentColor` (set from layer `color`). `confetti`, `balloons`, `watercolour-wash` are multi-tone and use
  magic fills `#AA0001/#AA0002/#AA0003`; the layer's `recolor {c1,c2,c3}` (roles) replaces them.
* **Text never contains Khmer.** A text layer has `copy` (key in `copy-bank.json`, text = `copy[key][lang]`) or a `literal` for non-Khmer glyphs
  such as `&`. `lang` is `km` or `en`. `font` is a role in `fonts.json`. `slot` marks the owner-editable fields
  (`groom`, `bride`, `name`, `host`, plus `<slot>_en`).
* **Khmer word breaks:** Khmer strings carry U+200B at word boundaries (inserted with ICU `Intl.Segmenter('km')`). Keep them; they are invisible and
  let every renderer wrap Khmer at word boundaries. Khmer `letterSpacing` is always 0 (letter-spacing breaks Khmer clusters).
* `lines` on text layers is the line count measured with the real fonts at design time, a layout hint only.

## Design system

| Role | Ceremonial (Moul / Cinzel / Great Vibes) | Elegant (Moulpali / Playfair / Cormorant) | Modern (Kantumruy Pro / Jost) | Festive (Koulen / Battambang / Montserrat) |
|---|---|---|---|---|
| Khmer title / name | Moul / Moulpali | Moulpali / Noto Serif Khmer | Kantumruy Pro | Koulen |
| Khmer body | Noto Serif Khmer | Noto Serif Khmer | Kantumruy Pro | Battambang |
| English | Cinzel + script names | Playfair Display + Cormorant Garamond | Jost | Montserrat |

Khmer body line-height 1.7 to 1.95, Khmer is always set larger than the English line beside it (Khmer glyphs have a smaller optical size), minimum text
size 1.9 % of canvas width, safe margin 3 % on all sides.

## Pack linter (`generator/lint.py`)

Checks per template: WCAG contrast (4.5 body, 3.0 large) against the opaque fill under every text layer, text boxes inside the safe area, text-over-text
overlap, stack overflow at design time, every `copy` key exists, every ornament file exists, Khmer line-height, minimum size, no literal Khmer in layers,
no Khmer in the generator source outside `copybank.py`, at least 30 templates, no Latin letters in any Khmer string (placeholders in `[ ]` aside).
Last run: **0 errors / 0 warnings on the generated templates**; the hand-authored designs are validated by the app converter and the pack tests.

To rebuild after a change: `PACK_FONTS=<dir of the 14 TTFs named in generator/engine.py FONTS> python3 generator/build_pack.py --write && python3 generator/lint.py`
(needs Pillow with raqm, cairosvg and Node for the Khmer word breaker). `--preview` writes PNG renders to `_preview/`.

## The 100 templates

| # | id | category | canvas | pages | EN name | Khmer name | photo slots |
|---|---|---|---|---|---|---|---|
| 1 | `wd-royal-maroon-gold` | wedding | a5p | 2 | Royal Maroon & Gold | អាពាហ៍ពិពាហ៍ ក្រហមមាស | — |
| 2 | `wd-ivory-kbach-frame` | wedding | a5p | 1 | Ivory Kbach Frame | អាពាហ៍ពិពាហ៍ ស៊ុមក្បាច់ខ្មែរ | — |
| 3 | `wd-lotus-watercolour` | wedding | a5p | 1 | Lotus Watercolour | អាពាហ៍ពិពាហ៍ ផ្កាឈូកទន់ភ្លន់ | — |
| 4 | `wd-midnight-navy-gold` | wedding | a5p | 1 | Midnight Navy & Gold | អាពាហ៍ពិពាហ៍ ខៀវយប់ និងមាស | — |
| 5 | `wd-temple-arch` | wedding | a5p | 1 | Temple Arch | អាពាហ៍ពិពាហ៍ ក្លោងទ្វារប្រាសាទ | — |
| 6 | `wd-quiet-ivory` | wedding | p45 | 1 | Quiet Ivory | អាពាហ៍ពិពាហ៍ ស្អាតសាមញ្ញ | — |
| 7 | `wd-jade-garden` | wedding | a5p | 1 | Jade Garden | អាពាហ៍ពិពាហ៍ សួនបៃតង | — |
| 8 | `wd-saffron-sunrise` | wedding | a5p | 1 | Saffron Sunrise | អាពាហ៍ពិពាហ៍ ថ្ងៃរះ | — |
| 9 | `wd-red-gold-story` | wedding | story | 1 | Red & Gold Story | អាពាហ៍ពិពាហ៍ ក្រហម និងមាស | — |
| 10 | `wd-save-the-date` | wedding | sq | 1 | Save the Date | កត់ទុកថ្ងៃ ផ្កាឈូកខ្ចី | — |
| 11 | `wd-hair-cutting` | wedding | a5p | 1 | Hair-Cutting Blessing | កាត់សក់ ផ្កាឈូកទន់ភ្លន់ | — |
| 12 | `wd-reception-dark-plum` | wedding | p45 | 1 | Dark Plum Reception | ជប់លៀង ខ្មៅស្វាយ និងមាស | — |
| 13 | `wd-photo-modern` | wedding | p45 | 1 | Photo Modern | អាពាហ៍ពិពាហ៍ ទំនើប | couple |
| 14 | `wd-three-day-program` | wedding | a5p | 1 | Three-Day Programme | កម្មវិធីបីថ្ងៃ បែបប្រពៃណី | — |
| 15 | `bd-first-pastel` | birthday | p45 | 1 | First Birthday Pastel | ខួបកំណើតគម្រប់ ១ ឆ្នាំ ពណ៌ទន់ | — |
| 16 | `bd-kids-party` | birthday | sq | 1 | Kids Party | ជប់លៀងកុមារ ពណ៌ដិតដាស់ | — |
| 17 | `bd-golden-soiree` | birthday | p45 | 1 | Golden Soirée | ខួបកំណើត ខ្មៅ និងមាស | — |
| 18 | `bd-longevity-60` | birthday | a5p | 1 | Longevity Blessing | ចម្រើនអាយុ មាសព្រះអាទិត្យ | — |
| 19 | `bd-modern-bold` | birthday | p45 | 1 | Modern Bold | ខួបកំណើត ពណ៌ដិតដាស់ | — |
| 20 | `hw-housewarming` | ceremony | a5p | 1 | House Blessing | ឡើងផ្ទះថ្មី ផ្កាឈូកទន់ភ្លន់ | — |
| 21 | `merit-dana` | ceremony | a5p | 1 | Merit-Making | បុណ្យទាន បែបប្រពៃណី | — |
| 22 | `kathina-robe` | ceremony | a5p | 1 | Kathina Robe Offering | កឋិនទាន ពណ៌ទឹកក្រូច | — |
| 23 | `pchum-ben` | ceremony | p45 | 1 | Pchum Ben | ភ្ជុំបិណ្ឌ បែបប្រពៃណី | — |
| 24 | `memorial-ceremony` | ceremony | a5p | 1 | Memorial Ceremony | បុណ្យខួប ស្ងប់ស្ងាត់ | portrait |
| 25 | `gr-khmer-new-year` | greeting | sq | 1 | Khmer New Year | ចូលឆ្នាំថ្មី ភ្លឺថ្លា | — |
| 26 | `gr-water-festival` | greeting | land | 1 | Water Festival | បុណ្យអុំទូក ទន្លេខៀវ | — |
| 27 | `gr-global-new-year` | greeting | story | 1 | Global New Year | ឆ្នាំសកល ខៀវចាស់ និងមាស | — |
| 28 | `gr-thank-you` | greeting | sq | 1 | Thank You | សូមអរគុណ បែបប្រពៃណី | — |
| 29 | `gr-graduation` | greeting | p45 | 1 | Graduation | បញ្ចប់ការសិក្សា ខៀវចាស់ និងមាស | — |
| 30 | `gr-newborn` | greeting | sq | 1 | Newborn Welcome | កូនកើតថ្មី ពណ៌ទន់ | — |
| 31 | `gr-sympathy` | greeting | p45 | 1 | With Sympathy | រំលែកទុក្ខ ស្ងប់ស្ងាត់ | — |
| 32 | `gr-get-well` | greeting | sq | 1 | Get Well Soon | ឆាប់ជាសះស្បើយ បៃតងខ្ចី | — |
| 33 | `gr-blessings` | greeting | a5p | 1 | Blessings & Good Wishes | ជូនពរ បែបប្រពៃណី | — |
| 34 | `biz-grand-opening` | business | p45 | 1 | Grand Opening | សម្ពោធ ខ្សែបូ | — |
| 35 | `biz-corporate-gala` | business | a5p | 1 | Corporate Gala | ជប់លៀងប្រចាំឆ្នាំ ព្រលប់ | — |
| 36 | `anniv-golden` | wedding | p45 | 1 | Wedding Anniversary | ខួបអាពាហ៍ពិពាហ៍ មាសផ្កាឈូក | — |
| 37 | `wd-olive-letter` | wedding | a5p | 1 | The Olive Letter | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 38 | `en-garden-sun` | wedding | a5p | 1 | Garden Sun | អាពាហ៍ពិពាហ៍ សួនថ្ងៃរះ | — |
| 39 | `en-coastal-vows` | wedding | p45 | 1 | Coastal Vows | អាពាហ៍ពិពាហ៍ ឆ្នេរសមុទ្រ | couple |
| 40 | `en-afterglow-disco` | birthday | sq | 1 | Afterglow Disco | ខួបកំណើត រាំពេលយប់ | — |
| 41 | `en-cloud-nine-baby` | birthday | p45 | 1 | Cloud Nine Baby | ស្វាគមន៍កូនថ្មី ពណ៌ទន់ | portrait |
| 42 | `en-noir-graduate` | greeting | p45 | 1 | Noir Graduate | បញ្ចប់ការសិក្សា ខ្មៅ និងមាស | — |
| 43 | `en-summit-26` | business | land | 1 | Summit 26 | សន្និសីទ ឆ្នាំ ២០២៦ | — |
| 44 | `en-terracotta-home` | ceremony | a5p | 1 | Terracotta Home | ឡើងផ្ទះថ្មី ដីឥដ្ឋ | — |
| 45 | `en-deco-anniversary` | wedding | story | 1 | Deco Anniversary | ខួបអាពាហ៍ពិពាហ៍ ស្ថាបត្យកម្ម | — |
| 46 | `en-moonlit-halloween` | birthday | sq | 1 | Moonlit Halloween | ជប់លៀងហាឡូវីន | — |
| 47 | `en-midnight-new-year` | greeting | story | 1 | Midnight New Year | ឆ្នាំថ្មី ពាក់កណ្តាលអធ្រាត្រ | — |
| 48 | `km-bokor-vows` | wedding | a5p | 1 | Bokor Vows | អាពាហ៍ពិពាហ៍ បូកគោ | — |
| 49 | `km-silk-engagement` | wedding | p45 | 1 | Silk Engagement | ពិធីភ្ជាប់ពាក្យ សូត្រខ្មែរ | — |
| 50 | `km-neon-birthday` | birthday | sq | 1 | Neon Birthday | ខួបកំណើត ពន្លឺពណ៌ | — |
| 51 | `km-baby-blessing` | greeting | p45 | 1 | Baby Blessing | ពរជ័យកូនថ្មី | — |
| 52 | `km-wood-earth-home` | ceremony | a5p | 1 | Wood & Earth Home | ឡើងផ្ទះថ្មី ឈើ និងដី | — |
| 53 | `km-lotus-merit` | ceremony | story | 1 | Lotus Merit | បុណ្យទាន ផ្កាឈូកស | — |
| 54 | `km-sra-sor-new-year` | greeting | land | 1 | Sra Sor New Year | ចូលឆ្នាំថ្មី ស្រស់ស្រាយ | — |
| 55 | `km-modern-graduate` | greeting | p45 | 1 | Modern Graduate | បញ្ចប់ការសិក្សា ទំនើប | — |
| 56 | `km-golden-anniversary` | wedding | story | 1 | Golden Anniversary | ខួបអាពាហ៍ពិពាហ៍ មាសក្រហម | — |
| 57 | `km-river-night` | greeting | land | 1 | River Night | បុណ្យអុំទូក យប់ទន្លេ | — |
| 58 | `en-amber-arch` | wedding | a5p | 1 | Amber Arch | ទ្វារធ្នូមាស | — |
| 59 | `en-cathedral-rose` | wedding | a5p | 1 | Cathedral Rose | មង្គលការផ្កាកុលាប | — |
| 60 | `en-riso-thirty` | birthday | sq | 1 | Riso Thirty | ខួប​កំណើត​៣០​ឆ្នាំ | — |
| 61 | `en-chrome-gala` | business | land | 1 | Chrome Gala | ពិធី​ប្រគល់​រង្វាន់​ក្រូម | — |
| 62 | `en-kraft-hearth` | ceremony | a5p | 1 | Kraft Hearth | ពិធី​ប្រទានពរ​ផ្ទះ​ថ្មី | — |
| 63 | `en-ticket-anniv` | wedding | land | 1 | Silver Stub | ខួប​អាពាហ៍ពិពាហ៍​២៥​ឆ្នាំ | — |
| 64 | `en-confetti-shower` | ceremony | sq | 1 | Confetti Shower | ពិធី​សែន​ទារក | — |
| 65 | `en-award-noir` | business | p45 | 1 | Award Noir | ពិធី​រង្វាន់​រាត្រី​ខ្មៅ | — |
| 66 | `en-folk-grad` | greeting | a5p | 1 | Folk Cap | ពិធី​បញ្ចប់​ការសិក្សា | — |
| 67 | `en-museum-engage` | wedding | p45 | 1 | Quiet Museum | ពិធី​ភ្ជាប់ពាក្យ​បែប​សារមន្ទីរ | — |
| 68 | `en-festival-lineup` | greeting | story | 1 | After Hours | ពិធីបុណ្យ​តន្ត្រី​ពេលយប់ | — |
| 69 | `en-watercolour-christen` | ceremony | a5p | 1 | Washed in Light | ពិធី​ជ្រមុជទឹក​ទារក | — |
| 70 | `km-royal-kbach` | wedding | a5p | 1 | Royal Kbach | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 71 | `km-naga-blessing` | wedding | a5p | 1 | Naga Blessing | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 72 | `km-lotus-vow` | wedding | p45 | 1 | Lotus Vow | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 73 | `km-peacock-silk` | wedding | a5p | 1 | Peacock Silk | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 74 | `km-betel-promise` | wedding | p45 | 1 | Betel Promise | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 75 | `km-moon-engagement` | wedding | story | 1 | Moon Engagement | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 76 | `km-silk-programme` | wedding | a5p | 1 | Silk Programme | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 77 | `km-modern-monogram` | wedding | p45 | 1 | Modern Monogram | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ | — |
| 78 | `en-ordination-saffron` | ceremony | a5p | 1 | Saffron Ordination | សូមជូនពរ | — |
| 79 | `en-house-blessing` | ceremony | p45 | 1 | Threshold Blessing | សូមជូនពរ | — |
| 80 | `en-memorial-light` | ceremony | a5p | 1 | In Quiet Light | សូមជូនពរ | — |
| 81 | `en-baby-blessing` | ceremony | sq | 1 | Little Blessing | សូមជូនពរ | — |
| 82 | `en-merit-gold` | ceremony | p45 | 1 | Merit of Gold | សូមជូនពរ | — |
| 83 | `en-longevity-ninety` | ceremony | a5p | 1 | Ninety Years | សូមជូនពរ | — |
| 84 | `en-khmer-new-year` | greeting | sq | 1 | Sok Sabay | សូមជូនពរ | — |
| 85 | `en-pchum-ben` | greeting | p45 | 1 | Pchum Ben | សូមជូនពរ | — |
| 86 | `en-water-festival` | greeting | land | 1 | Water Festival | សូមជូនពរ | — |
| 87 | `en-kathina` | greeting | a5p | 1 | Kathina Offering | សូមជូនពរ | — |
| 88 | `en-vesak-moon` | greeting | p45 | 1 | Vesak Moon | សូមជូនពរ | — |
| 89 | `en-womens-day` | greeting | sq | 1 | For Her | សូមជូនពរ | — |
| 90 | `en-christmas-gold` | greeting | p45 | 1 | Gold Night | សូមជូនពរ | — |
| 91 | `en-with-thanks` | greeting | sq | 1 | With Thanks | សូមជូនពរ | — |
| 92 | `en-first-birthday` | birthday | sq | 1 | One Year | ពិធី​អបអរសាទរ​ខួបកំណើត | — |
| 93 | `en-sweet-sixteen` | birthday | story | 1 | Sixteen | ពិធី​អបអរសាទរ​ខួបកំណើត | — |
| 94 | `en-sixty-years` | birthday | a5p | 1 | Sixty Years | ពិធី​អបអរសាទរ​ខួបកំណើត | — |
| 95 | `en-carnival-day` | birthday | land | 1 | Carnival Day | ពិធី​អបអរសាទរ​ខួបកំណើត | — |
| 96 | `en-thirty-gold` | birthday | sq | 1 | Thirty, Golden | ពិធី​អបអរសាទរ​ខួបកំណើត | — |
| 97 | `en-foundry-opening` | business | land | 1 | Foundry Opening | ពិធីជប់លៀង​អាហារ​ពេលល្ងាច​ប្រចាំឆ្នាំ | — |
| 98 | `en-annual-gala` | business | p45 | 1 | Annual Gala | ពិធីជប់លៀង​អាហារ​ពេលល្ងាច​ប្រចាំឆ្នាំ | — |
| 99 | `en-summit-2027` | business | land | 1 | Summit 2027 | ពិធីជប់លៀង​អាហារ​ពេលល្ងាច​ប្រចាំឆ្នាំ | — |
| 100 | `en-launch-noir` | business | story | 1 | Launch Noir | ពិធីជប់លៀង​អាហារ​ពេលល្ងាច​ប្រចាំឆ្នាំ | — |

## Known limits (honest list)

* Khmer copy is **Claude-drafted**; 48 of 117 strings are flagged `med` risk. Native review is non-blocking; every string goes to `KHMER-REVIEW-QUEUE.md`.
* Previews were rendered with Pillow + cairosvg, not the app. Final pixel judgement happens in the editor (work order TP-4).
* Photo slots are placeholders; no stock photography ships. The designs work with an empty slot.
* Lunar dates are owner-entered; nothing here computes them.
