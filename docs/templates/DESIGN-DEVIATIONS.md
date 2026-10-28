# Design deviations — 36-template pack

Binding rule (work order §3.1): the pack's visual design is final. A design may change **only** to
fix a measured defect — overflow, clipping, collision, contrast, unreadable at 375 px, export
mismatch — and every change is logged here with the number that justified it. Taste is not a defect.

The generator (`template-pack/generator/`) needs Pillow+Raqm, cairosvg and Node to rebuild; those
are not installable in this repo's venv (TP-OD-2), so a change is made in the single
`template-pack/templates/<id>.json` layer file, marked **hand-edited**, and a `TODO: regenerate`
line goes to `artifacts/next-work/OWNER-QUEUE.md`.

| # | Template | Layer | Change | Measurement that justified it | Date |
|---|---|---|---|---|---|
| 1 | all 36 | `shape` layers with `fill: null` (9 templates: `anniv-golden`, `bd-golden-soiree`, `biz-corporate-gala`, `kathina-robe`, `memorial-ceremony`, `pchum-ben`, `wd-midnight-navy-gold`, `wd-reception-dark-plum`, `wd-red-gold-story`) | Converter fix, not a design edit: a stroke-only frame now emits `fillColor: "none"` instead of painting the stroke colour as its fill | The flagship and eight framed templates rendered a full-canvas gold rectangle; `wd-royal-maroon-gold` measured 1.03:1 on its title and body (A10). A frame is a border, not a fill. | 2026-10-26 |
| 2 | `biz-grand-opening` | `text-05` ("Grand Opening") | **hand-edited**: moved from `y 37.28` to `y 39.2` and colour `paper` → `deep` | The subtitle straddled the ribbon band's lower edge: upper half on `#B8431A`, lower half on `#FFF8E8`, measured 1.07:1 in the 1× export. It now sits fully on the cream ground at 10.4:1. | 2026-10-26 |

## Not deviations

- **Font substitution.** The pack names 14 families; 12 are not in the registry. Mapping to the
  nearest registered face (TP-OD-1 fallback) changes texture, not layout, and is recorded in
  `FONT-SUBSTITUTIONS.md`, not here.
- **Pattern tiles are images.** A repeated tile is drawn as one image per grid cell by the
  converter; the editor has no tiled-fill primitive (TP-0 gap table). Geometry matches the pack
  exactly at 1×/2×/3× (A8).
- **Style kit / opening scene.** Chosen per Appendix D from the six existing scenes; no new scene
  was created. `gr-newborn` keeps `soft-monogram` because that scene is the fade-only option in the
  quiet group — it is not a flourish.
