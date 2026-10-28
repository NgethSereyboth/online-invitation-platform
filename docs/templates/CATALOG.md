# Khmer event template pack — catalogue

The 36 pack templates, served from `/assets/template-pack/` and listed by the
Template Studio under **Khmer events**. Every entry is a native invitation
document (`schemaVersion` 1) built by `tools/build-template-pack.py` from
`template-pack/`; the picker never imports the pack into the editor bundle.

- Source of truth: `template-pack/catalog.json` (copy, palettes, pages) and the
  per-template layer files under `template-pack/templates/`.
- Rebuild: `.venv/bin/python tools/build-template-pack.py`
- Verify: `.venv/bin/python tools/build-template-pack.py --check` and
  `.venv/bin/python -m pytest tests/test_template_pack.py -q`
- Thumbnails: `assets/template-pack/thumbs/<id>.webp`, 420 px wide, rendered in
  the real editor by `tools/render-template-thumbs.py`.
- Acceptance evidence: [ACCEPTANCE-2026-10-25.md](ACCEPTANCE-2026-10-25.md),
  [DESIGN-REVIEW-2026-10-25.md](DESIGN-REVIEW-2026-10-25.md),
  [PUBLIC-PROOF-2026-10-25.md](PUBLIC-PROOF-2026-10-25.md) and the
  [final report](FINAL-REPORT-2026-10-25.md).

Canvas codes: `a5p` = A5 portrait 1000×1414; `story` = 1080×1920 story;
`square` = 1080×1080; `portrait` = 1080×1350; `a4p` = A4 portrait 1240×1754.

## The 36

| # | Thumbnail | Template | Category | Canvas | Pages | Text objects | Ornaments | Typography | Opening scene | Style kit | Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ![Royal Maroon & Gold](../../assets/template-pack/thumbs/wd-royal-maroon-gold.webp) | **Royal Maroon & Gold**<br>អាពាហ៍ពិពាហ៍ ក្រហមមាស<br>`wd-royal-maroon-gold` | Wedding | A5 portrait (1000×1414) | 2 | 34 | 7 | ceremonial | `silk-curtain` | `royal-khmer-gold` | wedding, traditional, royal, dark, gold |
| 2 | ![Ivory Kbach Frame](../../assets/template-pack/thumbs/wd-ivory-kbach-frame.webp) | **Ivory Kbach Frame**<br>អាពាហ៍ពិពាហ៍ ស៊ុមក្បាច់ខ្មែរ<br>`wd-ivory-kbach-frame` | Wedding | A5 portrait (1000×1414) | 1 | 16 | 5 | ceremonial | `silk-curtain` | `royal-khmer-gold` | wedding, traditional, light, gold |
| 3 | ![Lotus Watercolour](../../assets/template-pack/thumbs/wd-lotus-watercolour.webp) | **Lotus Watercolour**<br>អាពាហ៍ពិពាហ៍ ផ្កាឈូកទន់ភ្លន់<br>`wd-lotus-watercolour` | Wedding | A5 portrait (1000×1414) | 1 | 17 | 4 | elegant | `floral-reveal` | `botanical-blush` | wedding, soft, pink, watercolour, light |
| 4 | ![Midnight Navy & Gold](../../assets/template-pack/thumbs/wd-midnight-navy-gold.webp) | **Midnight Navy & Gold**<br>អាពាហ៍ពិពាហ៍ ខៀវយប់ និងមាស<br>`wd-midnight-navy-gold` | Wedding | A5 portrait (1000×1414) | 1 | 16 | 3 | elegant | `silk-curtain` | `royal-khmer-gold` | wedding, modern, dark, gold, navy |
| 5 | ![Temple Arch](../../assets/template-pack/thumbs/wd-temple-arch.webp) | **Temple Arch**<br>អាពាហ៍ពិពាហ៍ ក្លោងទ្វារប្រាសាទ<br>`wd-temple-arch` | Wedding | A5 portrait (1000×1414) | 1 | 13 | 3 | ceremonial | `silk-curtain` | `royal-khmer-gold` | wedding, traditional, temple, angkor, warm |
| 6 | ![Quiet Ivory](../../assets/template-pack/thumbs/wd-quiet-ivory.webp) | **Quiet Ivory**<br>អាពាហ៍ពិពាហ៍ ស្អាតសាមញ្ញ<br>`wd-quiet-ivory` | Wedding | 4:5 portrait (1080×1350) | 1 | 16 | 1 | modern | `soft-monogram` | `botanical-blush` | wedding, minimal, modern, light |
| 7 | ![Jade Garden](../../assets/template-pack/thumbs/wd-jade-garden.webp) | **Jade Garden**<br>អាពាហ៍ពិពាហ៍ សួនបៃតង<br>`wd-jade-garden` | Wedding | A5 portrait (1000×1414) | 1 | 16 | 6 | elegant | `floral-reveal` | `botanical-blush` | wedding, green, garden, light, elegant |
| 8 | ![Saffron Sunrise](../../assets/template-pack/thumbs/wd-saffron-sunrise.webp) | **Saffron Sunrise**<br>អាពាហ៍ពិពាហ៍ ថ្ងៃរះ<br>`wd-saffron-sunrise` | Wedding | A5 portrait (1000×1414) | 1 | 15 | 3 | elegant | `floral-reveal` | `botanical-blush` | wedding, warm, sunrise, orange, traditional |
| 9 | ![Red & Gold Story](../../assets/template-pack/thumbs/wd-red-gold-story.webp) | **Red & Gold Story**<br>អាពាហ៍ពិពាហ៍ ក្រហម និងមាស<br>`wd-red-gold-story` | Wedding | Story 9:16 (1080×1920) | 1 | 16 | 5 | ceremonial | `silk-curtain` | `royal-khmer-gold` | wedding, red, gold, story, phone, traditional |
| 10 | ![Save the Date](../../assets/template-pack/thumbs/wd-save-the-date.webp) | **Save the Date**<br>កត់ទុកថ្ងៃ ផ្កាឈូកខ្ចី<br>`wd-save-the-date` | Wedding | Square 1:1 (1080×1080) | 1 | 16 | 1 | modern | `soft-monogram` | `botanical-blush` | wedding, save-the-date, minimal, engagement, square |
| 11 | ![Hair-Cutting Blessing](../../assets/template-pack/thumbs/wd-hair-cutting.webp) | **Hair-Cutting Blessing**<br>កាត់សក់ ផ្កាឈូកទន់ភ្លន់<br>`wd-hair-cutting` | Wedding | A5 portrait (1000×1414) | 1 | 15 | 4 | elegant | `floral-reveal` | `botanical-blush` | wedding, hair-cutting, ceremony, gold, soft |
| 12 | ![Dark Plum Reception](../../assets/template-pack/thumbs/wd-reception-dark-plum.webp) | **Dark Plum Reception**<br>ជប់លៀង ខ្មៅស្វាយ និងមាស<br>`wd-reception-dark-plum` | Wedding | 4:5 portrait (1080×1350) | 1 | 16 | 2 | elegant | `silk-curtain` | `royal-khmer-gold` | wedding, reception, dark, gold, evening |
| 13 | ![Photo Modern](../../assets/template-pack/thumbs/wd-photo-modern.webp) | **Photo Modern**<br>អាពាហ៍ពិពាហ៍ ទំនើប<br>`wd-photo-modern` | Wedding | 4:5 portrait (1080×1350) | 1 | 13 | 1 | modern | `floral-reveal` | `botanical-blush` | wedding, photo, modern, light |
| 14 | ![Three-Day Programme](../../assets/template-pack/thumbs/wd-three-day-program.webp) | **Three-Day Programme**<br>កម្មវិធីបីថ្ងៃ បែបប្រពៃណី<br>`wd-three-day-program` | Wedding | A5 portrait (1000×1414) | 1 | 18 | 4 | ceremonial | `soft-monogram` | `botanical-blush` | wedding, programme, schedule, traditional |
| 15 | ![First Birthday Pastel](../../assets/template-pack/thumbs/bd-first-pastel.webp) | **First Birthday Pastel**<br>ខួបកំណើតគម្រប់ ១ ឆ្នាំ ពណ៌ទន់<br>`bd-first-pastel` | Birthday | 4:5 portrait (1080×1350) | 1 | 12 | 2 | festive | `floral-reveal` | `botanical-blush` | birthday, first, kids, pastel |
| 16 | ![Kids Party](../../assets/template-pack/thumbs/bd-kids-party.webp) | **Kids Party**<br>ជប់លៀងកុមារ ពណ៌ដិតដាស់<br>`bd-kids-party` | Birthday | Square 1:1 (1080×1080) | 1 | 12 | 2 | festive | `floral-reveal` | `botanical-blush` | birthday, kids, party, bold |
| 17 | ![Golden Soirée](../../assets/template-pack/thumbs/bd-golden-soiree.webp) | **Golden Soirée**<br>ខួបកំណើត ខ្មៅ និងមាស<br>`bd-golden-soiree` | Birthday | 4:5 portrait (1080×1350) | 1 | 13 | 2 | elegant | `cinematic-photo` | `modern-cambodian-luxury` | birthday, adult, dark, gold, elegant |
| 18 | ![Longevity Blessing](../../assets/template-pack/thumbs/bd-longevity-60.webp) | **Longevity Blessing**<br>ចម្រើនអាយុ មាសព្រះអាទិត្យ<br>`bd-longevity-60` | Birthday | A5 portrait (1000×1414) | 1 | 13 | 5 | ceremonial | `minimal-editorial` | `modern-cambodian-luxury` | birthday, longevity, elder, respectful, traditional |
| 19 | ![Modern Bold](../../assets/template-pack/thumbs/bd-modern-bold.webp) | **Modern Bold**<br>ខួបកំណើត ពណ៌ដិតដាស់<br>`bd-modern-bold` | Birthday | 4:5 portrait (1080×1350) | 1 | 13 | 0 | modern | `cinematic-photo` | `modern-cambodian-luxury` | birthday, modern, minimal, adult |
| 20 | ![House Blessing](../../assets/template-pack/thumbs/hw-housewarming.webp) | **House Blessing**<br>ឡើងផ្ទះថ្មី ផ្កាឈូកទន់ភ្លន់<br>`hw-housewarming` | Ceremony | A5 portrait (1000×1414) | 1 | 12 | 4 | elegant | `minimal-editorial` | `modern-cambodian-luxury` | housewarming, blessing, ceremony, warm |
| 21 | ![Merit-Making](../../assets/template-pack/thumbs/merit-dana.webp) | **Merit-Making**<br>បុណ្យទាន បែបប្រពៃណី<br>`merit-dana` | Ceremony | A5 portrait (1000×1414) | 1 | 13 | 5 | ceremonial | `minimal-editorial` | `modern-cambodian-luxury` | merit, dana, buddhist, respectful, traditional |
| 22 | ![Kathina Robe Offering](../../assets/template-pack/thumbs/kathina-robe.webp) | **Kathina Robe Offering**<br>កឋិនទាន ពណ៌ទឹកក្រូច<br>`kathina-robe` | Ceremony | A5 portrait (1000×1414) | 1 | 13 | 2 | ceremonial | `minimal-editorial` | `modern-cambodian-luxury` | kathina, buddhist, saffron, dark, respectful |
| 23 | ![Pchum Ben](../../assets/template-pack/thumbs/pchum-ben.webp) | **Pchum Ben**<br>ភ្ជុំបិណ្ឌ បែបប្រពៃណី<br>`pchum-ben` | Ceremony | 4:5 portrait (1080×1350) | 1 | 14 | 3 | elegant | `minimal-editorial` | `modern-cambodian-luxury` | pchum-ben, ancestors, buddhist, sober, respectful |
| 24 | ![Memorial Ceremony](../../assets/template-pack/thumbs/memorial-ceremony.webp) | **Memorial Ceremony**<br>បុណ្យខួប ស្ងប់ស្ងាត់<br>`memorial-ceremony` | Ceremony | A5 portrait (1000×1414) | 1 | 14 | 2 | elegant | `minimal-editorial` | `modern-cambodian-luxury` | memorial, sober, respectful, monochrome |
| 25 | ![Khmer New Year](../../assets/template-pack/thumbs/gr-khmer-new-year.webp) | **Khmer New Year**<br>ចូលឆ្នាំថ្មី ភ្លឺថ្លា<br>`gr-khmer-new-year` | Greetings | Square 1:1 (1080×1080) | 1 | 6 | 4 | festive | `floral-reveal` | `botanical-blush` | greeting, khmer-new-year, festive, warm |
| 26 | ![Water Festival](../../assets/template-pack/thumbs/gr-water-festival.webp) | **Water Festival**<br>បុណ្យអុំទូក ទន្លេខៀវ<br>`gr-water-festival` | Greetings | Banner 16:9 (1600×900) | 1 | 4 | 4 | festive | `floral-reveal` | `botanical-blush` | greeting, water-festival, festive, blue, landscape |
| 27 | ![Global New Year](../../assets/template-pack/thumbs/gr-global-new-year.webp) | **Global New Year**<br>ឆ្នាំសកល ខៀវចាស់ និងមាស<br>`gr-global-new-year` | Greetings | Story 9:16 (1080×1920) | 1 | 4 | 4 | festive | `cinematic-photo` | `modern-cambodian-luxury` | greeting, new-year, story, dark, gold |
| 28 | ![Thank You](../../assets/template-pack/thumbs/gr-thank-you.webp) | **Thank You**<br>សូមអរគុណ បែបប្រពៃណី<br>`gr-thank-you` | Greetings | Square 1:1 (1080×1080) | 1 | 6 | 3 | elegant | `minimal-editorial` | `modern-cambodian-luxury` | greeting, thank-you, elegant, warm |
| 29 | ![Graduation](../../assets/template-pack/thumbs/gr-graduation.webp) | **Graduation**<br>បញ្ចប់ការសិក្សា ខៀវចាស់ និងមាស<br>`gr-graduation` | Greetings | 4:5 portrait (1080×1350) | 1 | 6 | 2 | elegant | `cinematic-photo` | `modern-cambodian-luxury` | greeting, graduation, congratulations, navy, gold |
| 30 | ![Newborn Welcome](../../assets/template-pack/thumbs/gr-newborn.webp) | **Newborn Welcome**<br>កូនកើតថ្មី ពណ៌ទន់<br>`gr-newborn` | Greetings | Square 1:1 (1080×1080) | 1 | 6 | 4 | elegant | `soft-monogram` | `botanical-blush` | greeting, newborn, baby, pastel, soft |
| 31 | ![With Sympathy](../../assets/template-pack/thumbs/gr-sympathy.webp) | **With Sympathy**<br>រំលែកទុក្ខ ស្ងប់ស្ងាត់<br>`gr-sympathy` | Greetings | 4:5 portrait (1080×1350) | 1 | 4 | 3 | elegant | `minimal-editorial` | `modern-cambodian-luxury` | greeting, sympathy, sober, respectful, monochrome |
| 32 | ![Get Well Soon](../../assets/template-pack/thumbs/gr-get-well.webp) | **Get Well Soon**<br>ឆាប់ជាសះស្បើយ បៃតងខ្ចី<br>`gr-get-well` | Greetings | Square 1:1 (1080×1080) | 1 | 4 | 4 | modern | `minimal-editorial` | `modern-cambodian-luxury` | greeting, get-well, green, soft |
| 33 | ![Blessings & Good Wishes](../../assets/template-pack/thumbs/gr-blessings.webp) | **Blessings & Good Wishes**<br>ជូនពរ បែបប្រពៃណី<br>`gr-blessings` | Greetings | A5 portrait (1000×1414) | 1 | 6 | 4 | ceremonial | `minimal-editorial` | `modern-cambodian-luxury` | greeting, blessing, respectful, elder, gold |
| 34 | ![Grand Opening](../../assets/template-pack/thumbs/biz-grand-opening.webp) | **Grand Opening**<br>សម្ពោធ ខ្សែបូ<br>`biz-grand-opening` | Business | 4:5 portrait (1080×1350) | 1 | 12 | 3 | modern | `cinematic-photo` | `modern-cambodian-luxury` | business, opening, ribbon, bright |
| 35 | ![Corporate Gala](../../assets/template-pack/thumbs/biz-corporate-gala.webp) | **Corporate Gala**<br>ជប់លៀងប្រចាំឆ្នាំ ព្រលប់<br>`biz-corporate-gala` | Business | A5 portrait (1000×1414) | 1 | 13 | 2 | elegant | `cinematic-photo` | `modern-cambodian-luxury` | business, gala, corporate, dark, gold |
| 36 | ![Wedding Anniversary](../../assets/template-pack/thumbs/anniv-golden.webp) | **Wedding Anniversary**<br>ខួបអាពាហ៍ពិពាហ៍ មាសផ្កាឈូក<br>`anniv-golden` | Wedding | 4:5 portrait (1080×1350) | 1 | 16 | 4 | elegant | `soft-monogram` | `botanical-blush` | anniversary, wedding, gold, elegant |

## Categories

| Category | Templates | Picker filter |
|---|---|---|
| Wedding | 15 | Wedding |
| Birthday | 5 | Birthday |
| Ceremony (housewarming, merit, Kathina, Pchum Ben, memorial) | 5 | Ceremony |
| Greetings | 9 | Greetings |
| Business | 2 | Business |

## Intended event

Each template is a complete multi-page invitation: page 1 is the formal
invitation (title, invitation sentence, names, date, time, venue); later pages
carry the programme, the venue and the RSVP/wishes copy. All copy is Khmer with
an English companion line; names, dates, times and venue are bracketed
placeholders that the editor binds to invitation fields.

## Ornaments

The pack draws on 27 procedural SVG ornaments (`assets/template-pack/ornaments/`),
served with a content hash and cache headers. Each built template references
between four and eight of them; none is a third-party image. See
[`docs/ASSETS.md`](../ASSETS.md) for the SHA-256 of every file.
