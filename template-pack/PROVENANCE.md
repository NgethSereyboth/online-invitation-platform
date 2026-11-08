# Provenance — OKID template pack v1

- **Author of the designs, Khmer copy and generator:** Claude (the owner's assistant in chat).
- **Date:** 2026-10-25.
- **Owner:** the owner of this repository. Original work, made for this project; no third-party artwork,
  template, photograph or invitation design was copied.
- **The Olive Letter (37th design):** added 2026-11-06; an English-led editorial invitation with original
  copy and `olive-branch.svg`; no third-party artwork. Its `name.km` is copied from `copy-bank.json` for
  gallery metadata; its 14 visible text layers are English only.
- **2026 event additions (designs 38–57):** ten English-led and ten Khmer-led designs, released
  2026-11-06. Each has original copy and an original motif; no third-party artwork or photography.
  The Khmer-led designs reuse the existing `copy-bank.json`; `name.km` remains gallery metadata.
- **Amber Arch (58th design):** added 2026-11-06; an English-led wedding invitation with original
  copy and `olive-arch.svg` (computed geometry). The composition follows the 2026 stationery
  direction researched online — a hairline arch, oversized centred serif names, a letterpress
  detail grid and a wax seal on a deep band — but no third-party artwork, photograph, layout or
  typeface was copied. `name.km` is gallery metadata; every rendered text layer is English.
- **Cathedral Rose (69th design):** added 2026-11-06; an English-led wedding invitation built on a
  deep forest stock with ivory ink and antique-gold hairlines. The top-cropped rose window
  (`rose-window.svg`, `rose-glass.svg`) is computed geometry — sixteen lancets, a bead ring and an
  eight-petal hub — not a traced or downloaded illustration. The composition follows the 2026
  research: coloured stock over coloured ink, white-ink printing on dark paper, a high-contrast
  serif for the names and a quiet three-column detail row.
- **What this directory is:** design *source material* in a neutral format (percent geometry, palette roles,
  copy keys). It is not served to browsers. The app consumes a converted, recoloured copy built by
  `tools/build-template-pack.py` into `assets/template-pack/`; nothing here is loaded at runtime.
- **How it was produced:** `python3 template-pack/generator/build_pack.py --write` then
  `python3 template-pack/generator/lint.py` (pack linter: 0 errors / 0 warnings on the 36 generated templates; the 21
  hand-authored additions were validated as a single source file and validated by the app converter and pack tests, not the
  generator linter). The
  generator needs Pillow-with-raqm, cairosvg and Node for the Khmer word breaker; **those are not part of this
  repository's toolchain** (TP-OD-2), so the generator is source-of-record only and is not run by the app's
  build. A design fix is made by editing the generator (or, when it cannot run, the single template's numbers,
  logged as `hand-edited` in `docs/templates/DESIGN-DEVIATIONS.md` with a `TODO: regenerate` line for the
  owner), never by editing `generator/copybank.py`, which is the only Khmer source for the pack.
- **Khmer copy:** drafted by Claude; native review is non-blocking (OD-18). `copy-bank.json` is a Khmer map
  file under the standing "never write Khmer" rule — the repository's scripts copy strings out of it and never
  retype them.
- **Licences:** no font files and no downloaded artwork are stored here. Ornaments are original SVG: 27 were
  produced by `generator/ornaments.py`; `olive-branch.svg` was authored for The Olive Letter,  the 12 event motifs for the 2026 additions, and `olive-arch.svg` for Amber Arch; `olive-branch.svg` was authored for The Olive Letter,  the 12 event motifs for the 2026 additions, and `olive-arch.svg` for Amber Arch; `olive-branch.svg` was authored for The Olive Letter,  the 12 event motifs for the 2026 additions, and `olive-arch.svg` for Amber Arch; `olive-branch.svg` was authored for The Olive Letter,  the 12 event motifs for the 2026 additions, and `olive-arch.svg` for Amber Arch; `olive-branch.svg` was authored for The Olive Letter,  the 12 event motifs for the 2026 additions, and `olive-arch.svg` for Amber Arch; `olive-branch.svg` was authored for The Olive Letter,  the 12 event motifs for the 2026 additions, and `olive-arch.svg` for Amber Arch; `olive-branch.svg` was authored for The Olive Letter, and the
  12 event motifs (`sun-arch` through `lantern-string`) were authored for the 2026 additions. Families
  named in `fonts.json` are SIL OFL 1.1; if a face is self-hosted later, its
  licence row goes into `docs/FONT_LICENSES_AND_REGISTRY.md` and `docs/ASSETS.md` in the same commit (TP-OD-1).
- **Not tracked:** `previews/` and `_preview/` are QA renders only and are git-ignored (never shipped).
