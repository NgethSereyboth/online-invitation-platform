# vendor/noto-khmer — the Khmer face the card renderer draws with

**Why this is in the repository.** `image_font(..., khmer=True)` in
`src/python/server.py` used to resolve a Khmer system font from a list of
absolute paths and silently fall through to DejaVu when none existed
(`docs/reviews/bulk-guest-import-research.md` §5.4, risk 1). The production
manifest (`docs/requirements-production.txt`) installs no font package and the
repository shipped only `.woff2` subsets under `assets/fonts/`, which Pillow
cannot load as a system font — so on Render every Khmer guest name would have
been drawn as empty boxes with no exception raised. Vendoring the face makes the
rendering identical on every machine and survives a base-image change.

## Files

| file | source | sha256 |
|---|---|---|
| `NotoSansKhmer-Regular.ttf` | Google Noto (`fonts-noto-core`, `NotoSansKhmer-Regular.ttf`, 112,372 bytes) | see `INTEGRITY.txt` |
| `NotoSansKhmer-Bold.ttf` | same package, `NotoSansKhmer-Bold.ttf`, 113,376 bytes | see `INTEGRITY.txt` |
| `LICENSE.txt` | the same text as `licenses/fonts/Noto-OFL-1.1.txt` | — |

Licence: **SIL Open Font License 1.1** (Copyright 2013 Google Inc.). The
repository already vendors this licence for the Noto web faces at
`licenses/fonts/Noto-OFL-1.1.txt` and declares `licenseId: "OFL-1.1"` in
`assets/fonts/registry.json`, so no new licence class is introduced.

## How it is used

`khmer_font_candidates()` in `src/python/server.py` returns the vendored paths
first and the previous system paths after them, so a developer machine with
`fonts-noto-core` installed keeps working. `log_khmer_font_status()` is called at
startup (both `create_app()` under waitress and the `__main__` dev server) and
prints `KHMER_FONT_STATUS ok …` or `KHMER_FONT_STATUS WARN …` using the same
`_khmer_font_metadata` (OpenType `pref blwf abvf pstf pres blws abvs psts abvm
blwm dist` and ≥92% modern-Khmer coverage) that uploaded custom fonts are
validated with.

`vendor/` is mirrored into `src/python/vendor/` by `python3 build.py mirror`
(`src/python/build/sync_frontend_assets.py`), so both copies are committed and
the served tree carries the face.
