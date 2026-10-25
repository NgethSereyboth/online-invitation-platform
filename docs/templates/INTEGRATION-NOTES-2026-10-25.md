# Template-pack integration notes (TP-0.1)

**Date:** 2026-10-25 · **Base:** `5f78421` · **Author:** Freebuff (read-only discovery; no code changed)
**Scope:** how `template-pack/` maps onto the app's real document model, measured by reading the source,
not by guessing. Every section cites `file:line` or a one-line check.

---

## 1. Document model

An invitation/poster document is a plain JSON object. The editor's own default is `src/js/app.js:193-273`
(`const initial = {...}`), the Template Studio's built-ins are `src/js/builtin-templates.js:2-9`, and a
saved document is normalised by `migrateDocument()` at `src/js/app.js:344-410`. The shape a **populated**
document actually takes is decided by `capture()` (`src/js/app.js:593-856`) which writes the DOM back
into state, so this is the authoritative object model:

| Key | Type | Notes |
|---|---|---|
| `schemaVersion` | number | built-ins write `10` (`src/js/builtin-templates.js:2`); a document read back from a real save also carries `schemaVersion` and is migrated by `migrateDocument` |
| `eventType` | string | `Wedding`, `Birthday`, `Business`, `Poster`, … |
| `templateId` | string | optional provenance |
| `fields` | object | `names`, `namesKm`, `date`, `time`, `venue`, `venueKm`, `message`, `messageKm`, `contactPhone`, `contactTelegram` (`src/js/app.js:344-356`) |
| `settings` | object | `rsvpEnabled`, `wishesEnabled`, `scheduleEnabled`, `venueEnabled`, `galleryEnabled`, `countdownEnabled`, `musicEnabled`, `openingEnabled`, `contactEnabled`, `videoEnabled`, `khmerNumerals` (LT-2.2) |
| `designPages` | array | each `{id, name, preset, enabled, background, backgroundImage, backgroundSize, backgroundOverlay, useMasterBackground, animation{preset,duration}, transition{preset,duration}, objects{}}` — normalised at `src/js/app.js:358-369` |
| `objects` | object | the **hero** page's objects, keyed by id (`src/js/app.js:721`) |
| `sectionOrder` | string array | `page:<id>` tokens interleaved with guest sections; public renderer reads it at `src/js/public-page.js:58` |
| `palette` | object | `{background, surface, text, heading, muted}` (`src/js/app.js:267`, `apply()` at `src/js/app.js:912`) |
| `accent` | hex string | scalar accent, `src/js/app.js:912` |
| `posterCanvas` | `{width,height}` | **this is the canvas size**; `normalizePosterDocument` at `src/js/app.js:326` and `applyPosterCanvasSize` at `src/js/app.js:332` size `#stage` in px |
| `styleKit` | `{id, overrides, templateDefaults}` | built-ins only (`src/js/builtin-templates.js:2`) |
| `openingScene` | object | `{id, monogram, subtitle, backgroundColor, backgroundImage, decorative, enterText, enterTextKm, duration, textVariant, skipAllowed}` (`src/js/builtin-templates.js:2`) |
| `masterPageStyle` | object | page background defaults, `src/js/app.js:371-375` |
| `backgroundEffects` | object | `{mode: none|solid|gradient, start, end, angle, texture: none|paper|dots|grid|soft-grain, textureOpacity}` — **document-wide**, not per page (`src/js/app.js:376-380`) |
| `galleryOrder`, `schedule`, `venues`, `customBlocks`, `sectionLayouts`, `sectionStyles`, `sectionAnimations`, `music`, `video`, `mapUrl`, `rsvpFields` | — | present on every saved document; irrelevant to static templates but must not be dropped |

Built-ins ship with `designPages: []` and `objects: {}` (`src/js/builtin-templates.js:2`) — that is why the
five existing built-ins look empty in the editor. A *populated* page is the `designPages[i]` object above;
its `objects` map is exactly the same shape as the hero `state.objects` map. Live example of a populated
document built in code: `src/js/adaptive-templates.js:53` (`applyFamilyPayload`) writes `designPages` and
`sectionOrder` page tokens into the editor through `EInviteEditorBridge.transact`.

## 2. Object types and the pack-layer mapping

Object types that exist: **text**, **image**, **shape** (`rectangle` | `circle` | `line`, `src/js/bundle-index-2.js:1113`),
and **decoration** (a text object with decoration styling, `src/js/app.js:1946`). There is **no SVG object type**,
no group object (grouping is a `groupId` string on members, `src/js/app.js:754`), no pattern fill and no clip-path
other than the six image masks (`src/js/app.js:1890`).

The persisted object (written at `src/js/app.js:721-850`, rehydrated at `src/js/app.js:939-1075`) carries
`left/top/width/height` as CSS strings, `type`, `html`, `font`, `fontSize`, `color`, `textAlign`, `fontWeight`,
`fontStyle`, `letterSpacing`, `lineHeight`, `textWrap`, `textColumns`, `fillColor`, `shapeKind`, `opacity`,
`borderWidth/Color/Radius`, `shadowBlur/Color`, `backgroundEnabled/Color/Opacity`, `blendMode`,
`fillMode` + `gradientStart/End/Angle`, `textGradient*`, `textStroke*`, `textShadow*`, `textTransform`,
`rotation`, `imageFit/PositionX/PositionY/Mask/Frame/*` (35 image adjustments), `locked`, `visible`,
`zIndex`, `src`, `alt`, `contentBinding`, `smartLayout`, `responsiveConstraints`.

| Pack layer (`template-pack/schema/template.schema.json`) | App object | Mapping | Status |
|---|---|---|---|
| `bg` (fill role or gradient) | `designPages[i].background` (+ `backgroundEffects`) or a full-bleed `shape` | flat colour → page `background`; 2-stop gradient → one `shape` object at 0/0/100/100 with `fillMode:'gradient'` (page background cannot hold a gradient) | flat **exact**, gradient **approximate** (2 stops only; 3-stop = nearest 2) |
| `shape` (rect / ellipse / line, `fill`, `stroke`, `strokeWidth`, `radius`) | `shape` object | `fillColor`, `borderColor`, `borderWidth`, `borderRadius`, `shapeKind` (`rectangle` / `circle` / `line`) | **exact** (per-side border not supported; pack uses uniform strokes) |
| `svg` (ornament, `src`, `color` or `recolor`, `flipX/flipY`, `rot`, `opacity`) | `image` object | `src` = self-hosted recoloured SVG copy; `opacity`; `rotation`; flips → not available on images (only `imageFlipX/Y`, which exist: `src/js/app.js:1917`) | recolour **exact at build time**, flips **exact** via `imageFlipX/Y`, live recolour **unsupported** (by design, baked at build) |
| `pattern` (tiled ornament, `tile` px) | N repeated `image` objects | tile the ornament across the layer box at build time | **approximate** (no repeat fill; a build-time tile grid reproduces it) |
| `photo` (slot, `shape` rect/ellipse/arch, `placeholder`) | `image` object | `imageMask: none|circle|arch`, empty `src`, placeholder panel drawn behind | **exact** for rect/circle/arch, `frame` maps to `imageFrame` |
| `text` (`copy`/`literal`, `lang`, `font`, `size`, `weight`, `color`, `align`, `lineHeight`, `letterSpacing`, `transform`, `slot`) | `text` object | `html` (copy value for `lang`), `font` = registry id, `fontSize`, `fontWeight`, `color`, `textAlign`, `lineHeight`, `letterSpacing`, `textTransform`, `contentBinding` = `fields.<slot>` | **exact**; `rot` → `rotation`; `lines` is a hint only |

Pack layer counts over the 36 templates: 453 `text`, 167 `svg`, 37 `bg`, 29 `shape`, 5 `pattern`, 2 `photo`
(measured with a one-line JSON walk of `template-pack/templates/*.json`).

## 3. Units and canvases

- Geometry is **percent of the artboard** (`left: '20%'`, `top: '40%'`); height may be percent or px. The pack's
  `x/y/w/h` are percentages too, so they copy straight across; the pack's `size`, `strokeWidth`, `radius`, `tile`
  and `frame.width` are **px at the declared canvas width** and must be multiplied by `canvas.w / 1000`… no —
  by `renderWidth / canvas.w` at render time; because our artboard *is* the canvas, they are copied 1:1
  (`template-pack/README.md` "Format in one minute").
- Canvas: `posterCanvas {width,height}` sizes the stage in px (`src/js/app.js:332-341`, clamped 200–4000 by
  `clampPosterSize` at `src/js/app.js:322`). The five pack canvases therefore all exist **without any new
  page-size code**: `a5p` 1000×1414, `p45` 1080×1350, `sq` 1080×1080, `story` 1080×1920, `land` 1600×900.
  Three of them (`p45`, `sq`, `story`) are also poster presets in `src/js/templates.js:36`; `a5p` and `land`
  are inside the custom-size range.
- Export: PNG/PDF export uses the stage size, so the exported page is the pack canvas; bleed is not part of the
  pack format and is not added (recorded as a gap in §9).

## 4. Text

- Per-object typography is complete: `font`, `fontSize`, `fontWeight`, `fontStyle`, `color`/`colorToken`,
  `textAlign`, `lineHeight` (number), `letterSpacing` (number), `textTransform`, `rotation`, `textWrap`
  (`normal|balance|pretty`), `textColumns`, `opacity`, plus rich text (`RichTextDocumentModel`,
  `src/js/app.js:839-847`).
- Two text objects (Khmer over English) can be linked to editable data with `contentBinding`
  (`fields.names` / `fields.namesKm`), resolved by `src/js/template-bindings.js:12`; grouping is a shared
  `groupId` (`src/js/app.js:754`). The pack's `slot` marker therefore maps to `contentBinding: 'fields.<slot>'`.
- **Khmer line-height ≥ 1.7 is expressible**: `lineHeight` is a free number and the registry's
  `normalizeTypography` does not clamp it (`src/js/typography-contract.js:6`). Khmer `letterSpacing` stays `0`
  (`template-pack/README.md`, rule already enforced by the pack linter).

## 5. Colours and recolouring

- There is no CSS-variable or `currentColor` object fill: an object's colour is read from its own dataset and
  written inline by `applyObjectVisualStyle` (`src/js/app.js:1854-1908`). An SVG is an `<img src>`; the browser
  cannot recolour its internals and no live recolour API exists.
- Therefore ornament colour is **baked at build time** by the converter, exactly as the work order says:
  monotone ornaments (pack uses `currentColor`) get a fill injected; multi-tone (`#AA0001/#AA0002/#AA0003`
  magic fills) get role hexes substituted. The built copy is a separate file under the served path, so two
  templates with the same ornament in different colours never share a file.
- The editor's own SVG upload path sanitises uploads (`asset-workflow.js`); pack ornaments never go through it —
  they are already-authored files in the repo and are additionally checked by the TP-1.2 test (no `<script>`,
  no `on*=`, no external URL).

## 6. Fonts

The font registry is `src/js/typography-contract.js:2` (`EInviteFontRegistry` / `EInviteTypography`, exposed at
`src/js/bundle-index.js:764`). It has **8 ids**, of which 4 are real faces and 4 are system fallbacks:

| Registry id | Family | Bundled |
|---|---|---|
| `noto-sans` | EInvite Noto Sans | yes (2 woff2) |
| `noto-serif` | EInvite Noto Serif | yes (2 woff2) |
| `noto-sans-khmer` | EInvite Noto Sans Khmer | yes (2 woff2) |
| `noto-serif-khmer` | EInvite Noto Serif Khmer | yes (2 woff2) |
| `serif-georgia`, `sans-arial`, `sans-trebuchet` | OS system faces | no (legacy only) |
| Inter | (bundled separately, `assets/fonts/inter-*.woff2`) | yes |

`@font-face` is declared in `typography-fonts.css` per route bundle with `font-display: swap` + `unicode-range`
(LT-2.4), `font-src 'self' data:` in the CSP (`src/python/server.py:343-346`), nothing remote.
Against `template-pack/fonts.json` (14 roles):

- **present** — `Noto Serif Khmer` (`noto-serif-khmer`), `Noto Sans Khmer` (`noto-sans-khmer`).
- **missing** — Moul, Moulpali, Koulen, Bokor, Battambang, Kantumruy Pro (Khmer display/body) and Cormorant
  Garamond, Playfair Display, Great Vibes, Cinzel, Montserrat, Jost (Latin).
- Capture of the gap: TP-2.2. TP-OD-1 allows a self-hosted OFL `.woff2` per missing family, lazily loaded;
  otherwise the nearest registry family and a row in `docs/templates/FONT-SUBSTITUTIONS.md`.

## 7. Serving

- The server serves a **deny-by-default** static whitelist: `public_static_path()` at
  `src/python/server.py:3694-3719`. Root files: only `.js .css .webmanifest .png .jpg .jpeg .webp .gif .svg .ico
  .woff .woff2 .ttf .otf .wasm`; nested files only under `assets/`, `vendor/`, `licenses/`, `core/`, with `.txt`
  added. **`.json` is not served at all** (a deliberate disclosure fix, same docstring).
- `build.py all` builds/mirrors `src/js`, `src/css`, `src/html` into `src/python/` (`SYNC_FRONTEND_ASSETS_DONE`,
  `MIRROR_CHECK_PASSED`) — `assets/` is already a served directory and is copied 1:1.
- CSP: `img-src 'self' data: blob: https:` and `font-src 'self' data:` (`src/python/server.py:343-346`), so
  self-hosted ornament SVGs, thumbnails and fonts are covered without touching the policy.
- **Decision (recorded in `artifacts/next-work/DECISIONS.md`):** the pack's browser-facing files live under
  `assets/template-pack/` (already inside the whitelist for `.svg/.webp/.woff2/.js`). The two JSON artefacts the
  gallery needs (`catalog`, one built document) are published as **ES modules** —
  `assets/template-pack/catalog.js` and `assets/template-pack/built/<id>.js`, each a single
  `export default {…}` — because `.json` is denied by the static whitelist and adding a new API route would add
  a new server surface (and a rate-limit row) for a read-only, cacheable asset. The loader uses dynamic
  `import()`; nothing is inlined into any bundle, so the editor bundle cannot grow (TP-OD-4, proved at TP-1.5).

## 8. Gallery

- The template gallery is `templates.html` → `src/js/templates.js` (`load()` at `:16`, `filtered()` at `:14`,
  `render()` at `:15`, `useTemplate()` at `:33`). It lists `EInviteBuiltinTemplates` (`builtin-templates.js`)
  plus the user's templates and the marketplace, filters by free-text, `#studioCategory`, `#studioSource` and
  favourites, and renders a `.studio-thumb` placeholder from the document palette (`templates.js:13`).
  "Use" creates an invitation (`POST /api/invitations`) from `t.document` and navigates to
  `/invitations/<id>/editor` (`templates.js:33`).
- Categories offered by the picker today: `Wedding`, `Birthday`, `Business`, `Other` (`templates.js` meta form).
  The pack's five categories are `wedding | birthday | ceremony | greeting | business`; `Ceremony` and
  `Greetings` are new option values, and the pack group also needs its own filter row (TP-1.4).
- Bilingual names: the picker prints a single `t.name`. Pack templates carry `name.en` + `name.km` in
  `catalog.json`; TP-1.4 renders both with the existing `.i18n-en` / `.i18n-km` convention.
- The editor itself has **no template picker**; its closest surface is the adaptive-family dialog
  (`src/js/adaptive-templates.js:55-57`, four families). The pack is therefore integrated at `templates.html`,
  not inside the editor.
- `styleKit` ids that exist (from `builtin-templates.js`): `royal-khmer-gold`, `modern-cambodian-luxury`,
  `botanical-blush`. `openingScene` ids that exist, all six from `#openingStyle` (`src/html/index.html:245`):
  `soft-monogram`, `royal-khmer-gate`, `silk-curtain`, `floral-reveal`, `cinematic-photo`,
  `minimal-editorial` (built-ins pick among three at `builtin-templates.js:2`); the guest renderer accepts any
  id and falls back (`public-page.js`).

## 9. Gaps and blockers

| Pack feature | App support | Plan |
|---|---|---|
| Percent geometry | `left/top/width/height` percent | use as-is (exact) |
| Canvas sizes (5) | `posterCanvas` custom px | use as-is (exact) |
| Flat `bg` role | `designPages[i].background` | use as-is (exact) |
| Gradient `bg` | page background is flat; `backgroundEffects` is document-wide | approximate: full-bleed gradient `shape` object |
| `shape` rect/ellipse/line | `shapeKind` rectangle/circle/line | exact |
| `svg` ornament, recolour | image object + build-time recolour | exact at build time; no live recolour |
| `svg` flip | `imageFlipX` / `imageFlipY` | exact |
| `pattern` (tiled SVG) | none | approximate: build-time tile grid of image objects |
| `photo` slot rect/ellipse/arch | image object + `imageMask` | exact (empty `src` + placeholder panel) |
| `text` with `font` roles | registry has 4 of 14 families | TP-2.2: add missing OFL faces or substitute |
| `text` `size` px at canvas width | `fontSize` px on the artboard | exact |
| `slot` editable field | `contentBinding: fields.<name>` | exact |
| Bleed / crop marks | not in the pack format | none needed |
| Multi-stop gradient | 2 stops only | approximate |
| Page-level gradient | no | approximate (shape) |

No gap is **blocking**: every pack template can be built with existing object types. Nothing in this list
requires a new editor feature.

## 10. Existing templates

- **Built-ins (5)**: `builtin-royal-khmer` "Royal Khmer Gold", `builtin-modern-luxury` "Modern Cambodian Luxury",
  `builtin-botanical-blush` "Botanical Blush", `builtin-birthday-editorial` "Editorial Birthday",
  `builtin-business-minimal` "Modern Event" (`src/js/builtin-templates.js:4-8`).
- **Adaptive families (4)**: `khmer-royal-wedding`, `modern-wedding`, `government-delegation`,
  `conference-formal` (`src/js/adaptive-templates.js:36-52`).
- **Pack (36)**: ids `wd-*`, `bd-*`, `hw-*`, `merit-*`, `kathina-*`, `pchum-*`, `memorial-*`, `gr-*`,
  `biz-*`, `anniv-*` (`template-pack/catalog.json`, `count: 36`).
- **Collision check** (one-line comparison of all three id sets): **0 collisions**. The pack ids are unique
  and contain no `builtin-` prefix; the gallery will badge them as its own source.

---

### Decisions taken in this item (copied to DECISIONS.md)

1. Pack browser assets live under `assets/template-pack/` (inside the static whitelist).
2. Pack JSON is published as ES modules (`catalog.js`, `built/<id>.js`) because the server denies `.json`;
   no new API route is added.
3. The pack is integrated in the Template Studio (`templates.html`), not inside the editor bundle.
4. Every pack template uses `posterCanvas` for its canvas — no new page-size code.
5. Gradient backgrounds become a full-bleed gradient `shape`; tiled patterns become a build-time image grid.
6. No pack gap is `blocking`; no new editor feature is built for this order.
