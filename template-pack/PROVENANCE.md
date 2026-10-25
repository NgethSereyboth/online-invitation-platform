# Provenance — OKID template pack v1

- **Author of the designs, Khmer copy and generator:** Claude (the owner's assistant in chat).
- **Date:** 2026-10-25.
- **Owner:** the owner of this repository. Original work, made for this project; no third-party artwork,
  template, photograph or invitation design was copied.
- **What this directory is:** design *source material* in a neutral format (percent geometry, palette roles,
  copy keys). It is not served to browsers. The app consumes a converted, recoloured copy built by
  `tools/build-template-pack.py` into `assets/template-pack/`; nothing here is loaded at runtime.
- **How it was produced:** `python3 template-pack/generator/build_pack.py --write` then
  `python3 template-pack/generator/lint.py` (pack linter: 0 errors / 0 warnings on 36 templates). The
  generator needs Pillow-with-raqm, cairosvg and Node for the Khmer word breaker; **those are not part of this
  repository's toolchain** (TP-OD-2), so the generator is source-of-record only and is not run by the app's
  build. A design fix is made by editing the generator (or, when it cannot run, the single template's numbers,
  logged as `hand-edited` in `docs/templates/DESIGN-DEVIATIONS.md` with a `TODO: regenerate` line for the
  owner), never by editing `generator/copybank.py`, which is the only Khmer source for the pack.
- **Khmer copy:** drafted by Claude; native review is non-blocking (OD-18). `copy-bank.json` is a Khmer map
  file under the standing "never write Khmer" rule — the repository's scripts copy strings out of it and never
  retype them.
- **Licences:** no font files and no downloaded artwork are stored here. Ornaments are original SVG produced by
  `generator/ornaments.py`. Families named in `fonts.json` are SIL OFL 1.1; if a face is self-hosted later, its
  licence row goes into `docs/FONT_LICENSES_AND_REGISTRY.md` and `docs/ASSETS.md` in the same commit (TP-OD-1).
- **Not tracked:** `previews/` and `_preview/` are QA renders only and are git-ignored (never shipped).
