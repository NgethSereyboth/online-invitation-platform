# Template pack — run to 100 designs

**Started:** 2026-11-06 · **Owner:** pack owner · **Status:** complete

This is the working progress file for the pack-100 run. The durable record is in `docs/HISTORY.md`
under the same date.

## Outcome

- Pack grew from **69 to 100** designs: wedding **34**, ceremony **17**, greeting **25**,
  birthday **15**, business **9**; **54 English-led**, **46 Khmer-led**.
- **31 new designs** across seven layouts (`classic`, `panel`, `poster`, `split`, `programme`,
  `kbach`, `band`) and **10 new computed ornaments** (`kbach-frame`, `naga-arch`,
  `lotus-medallion`, `peacock-fan`, `silk-band`, `betel-tray`, `moon-water`, `chevron-rule`,
  `palm-frond`, `diamond-lattice`).
- Eight new Khmer-idiom weddings follow the conventions found online (kbach corner frames, gold on
  oxblood/ivory/teal, lotus/naga/peacock/betel motifs, three-day programme, modern monogram).
  Every motif is original computed geometry; nothing was traced, downloaded or copied.

## Working constraints

- **No agent-written Khmer.** Every new rendered text layer is English. Khmer catalogue labels are
  reused verbatim from `template-pack/copy-bank.json` and are metadata only; a Khmer proofreader
  should replace them with design-specific labels (see Open items).
- Local only: no commit, push, PR or deployment unless the owner asks.

## Research inputs

- [vectorkhmer — Khmer wedding invitation frames](https://www.vectorkhmer.com/2019/04/khmer-wedding-invitation-card-frame.html)
- [Behance — Kbach Khmer border collections](https://www.behance.net/search/projects/kbach%20khmer)
- [The Knot — traditional Cambodian weddings](https://www.theknot.com/content/traditional-cambodian-wedding)
- [Paperlust — 2026 invitation trends](https://paperlust.co/blog/2026-wedding-invitation-trends/)
- [The Knot — 2026 invitation trends](https://www.theknot.com/content/wedding-invitation-trends)
- [Paperless Post — 2026 trends](https://www.paperlesspost.com/blog/wedding-invitation-design-trends)

## Phase table

| Phase | State | Evidence |
|---|---|---|
| Research (Khmer wedding + 2026 event directions) | done | sources above |
| Author 31 designs + 10 ornaments | done | `artifacts/next-work/add-pack-100.py`, catalogue **100** |
| Wire scene map and build | done | `wire-pack-100-scenes.py`; `TEMPLATE_PACK_BUILT files=292 written=100` |
| Render 100 thumbnails | done | **100** thumbs, **1,146,720 bytes** |
| Docs, counts, gallery copy, tests | done | docs updater; **14 passed** |
| UX/UI review and fixes | done | table below |
| Verification | done | server validator **100 invalid 0**, `build.py all --check` |

## UX/UI findings

| # | Finding | Fix | State |
|---|---|---|---|
| 1 | Gallery hint still said "Sixty-nine" at 100 designs | copy updated to "One hundred" (en + km spans) | done |
| 2 | 57 skeleton cards reserved the wrong gallery height | skeleton grid now holds 100 cards | done |
| 3 | Every keystroke rebuilt all cards | filter renders coalesce into one `requestAnimationFrame` | done |
| 4 | 11–12 px labels failed server typography normalization (`textAutoFitMax` below the 12 px body floor) | builder clamps auto-fit max to 12 and never lets the minimum exceed the designed size | done |
| 5 | Poster body copy printed over the pinned motif (`Moon Engagement`, `Sixteen`) | copy cursor clears the ornament band instead of advancing by its height | done |
| 6 | Panel kicker collided with tall ornaments (`Modern Monogram`, `Gold Night`, `One Year`) | kicker position follows the ornament box | done |
| 7 | `naga-arch` read as two loose hooks; split layout was a floating rail; lattice was too faint | symmetrical double-naga torana, ruled two-column split, heavier lattice | done |

## Verification

- `pytest tests/test_template_pack.py tests/template_pack_gallery_test.py tests/template_pack_loader_test.py -q`
  → **14 passed** (pack 12, gallery 1, loader 1).
- Server validator over every built document → **TOTAL 100 INVALID 0**.
- `python3 build.py all --check` → `BUILD_OK`; mirror `up_to_date=730`.
- Thumbnails rendered through the fit-and-freeze capture; the eight Khmer weddings and one design
  per new layout were inspected at thumbnail size.

## Open items

- Khmer catalogue labels for the new designs are category-generic reused strings, pending a Khmer
  proofreader; they are not rendered.
- The gallery was exercised through its automated page test; no manual browser session was recorded
  in this file.
- No commit, push or deployment has been made.
