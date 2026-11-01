# Design system

Two layers, one document:

1. **Application tokens** — the shell's palette, type scale, spacing, radii, elevation, motion and
   geometry. These are CSS custom properties in `src/css/tokens.css`, which every one of the 16 routes
   loads (the source list lives in `docs/route-bundle-sources.json`). Components consume tokens; they
   do not hard-code values.
2. **Khmer event pack rules** — the design contract the 36-template pack follows. Its source is
   `template-pack/`; the app renders the converted native documents, so the rules show up in the
   product rather than in a separate styleguide.

The token layer is normative for the app. The pack layer is normative for pack artwork.

---

## Application tokens

### Palette

One token set with a dark override on `html[data-theme="dark"]`. There is exactly one accent: the
Khmer maroon in `--brand`, re-pointed lighter in dark mode. `--brand-2` is its second tone, not a
second accent — the violet it once was lost the cascade to these tokens and has no interactive
consumer left.

| Role | Light | Dark | Notes |
|---|---|---|---|
| `--surface-0` (page) | `#f5f6f8` | `#111218` | app background |
| `--surface-1` | `#ffffff` | `#191a21` | cards, panels |
| `--surface-2` | `#f8f8fb` | `#202129` | wells, nested panels |
| `--surface-3` | `#eff0f4` | `#292b34` | pressed / selected ground |
| `--text-1` | `#1f2026` | `#f3f4f8` | primary reading colour |
| `--text-2` | `#646773` | `#b2b4be` | secondary text |
| `--text-3` | `#6c707a` | `#90939f` | 4.96:1 light; 5.66:1 dark surface-1, 4.61:1 dark surface-3 — the two values were raised to clear AA-normal |
| `--border-1` / `--border-2` | `#e2e3e8` / `#d3d5dc` | `#2f313b` / `#3c3f4b` | hairlines, dividers |
| `--brand` (accent) | `#8b465b` | `#e18aa5` | the only accent; focus ring and primary button use it |
| `--brand-2` | `#ba6d84` | `#f0a8bb` | accent's second tone |
| `--brand-soft` | `#f5e8ed` | `#38252e` | tinted ground for accent surfaces |
| `--success` / `--warning` / `--danger` | `#2b9b68` / `#c98322` / `#c6404d` | `#69d095` / `#f2b65c` / `#ff7883` | status only |
| `--info` | `#2f6fb5` | `#7fb2ef` | toast/info surfaces (`--app-info`) |

A `--canva-*` reference layer (turquoise, blue, purple, pink, one gradient) exists in the same file
for future Canva-styled surfaces. **Nothing consumes it, and it never replaces `--brand`**; each value
carries its measured contrast in a comment so a future consumer knows whether it may carry text.

### Type scale

Self-hosted families only (CSP `font-src 'self' data:`). Titles are weight **600**, not 700.

| Step | Size / line-height | Tracking | Weight |
|---|---|---|---|
| `--fs-title-lg` | 24 / 1.2 | `--tracking-tight` (-0.01em) | 600 |
| `--fs-title-md` | 20 / 1.25 | `--tracking-tight` | 600 |
| `--fs-title-sm` | 16 / 1.3 | 0 | 600 |
| `--fs-title-xs` | 14 / 1.3 | 0 | 600 |
| `--fs-body-lg` | 16 / 1.5 | 0 | 400 |
| `--fs-body-md` | 14 / 1.5 | 0 | 400 |
| `--fs-body-sm` | 12 / 1.45 | 0 | 400 |
| `--fs-caption` | 11 / 1.4 | 0.02em | 500 |
| `--fs-mono` | 11 / 1.2 | 0.04em | 600 |
| `--fs-display-lg` (local addition) | 64 / 1.1 | `--tracking-tight` | 400 |
| `--fs-hero` (local addition) | 80 / 1.1 | `--tracking-tight` | 400 |

Families: `--font-latin` (Inter first), `--font-khmer` (`EInvite Noto Sans Khmer` first),
`--font-display` (Noto Serif), `--font-display-km` (Noto Serif Khmer), `--font-mono` (system stack).
`:lang(km)` and `.khmer-text` force the Khmer family and `letter-spacing: normal` — a Latin family in
front of a Khmer run can suppress OpenType shaping, and negative tracking breaks clusters. The two
display steps are a local product addition with no consumers yet, not a borrowed scale step.

### Spacing, radii, elevation

- **Spacing** is an 8px grid with a 4px half-unit: 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 64, 96
  (`--space-1…24`). 20, 28 and 40 are local stops kept because existing declarations depend on them;
  they are defined tokens precisely because an undefined one behaves as `unset`, not as a fallback.
- **Radii:** 8 (`--radius-sm`/`-md`), 16 (`--radius-lg`/`-xl`), 9999 (`--radius-pill`), 24
  (`--radius-media`, local addition, no consumers yet).
- **Elevation:** `--app-shadow-sm` is the live card-rest value and `--app-shadow-card-hover` is its
  hover pair (`--shadow-1` / `--shadow-2` are aligned to that pair); `--shadow-3` is the floating
  layer, deliberately larger.

### Motion

| Token | Value | Use |
|---|---|---|
| `--motion-1` | 150ms | small state changes |
| `--motion-2` | 200ms | the default; card lift, panels |
| `--motion-3` | 250ms | larger surfaces |
| `--ease-out` | `cubic-bezier(0.2,0,0,1)` | enter / settle |
| `--ease-in` | `cubic-bezier(0.4,0,1,1)` | exit |

Rules:

1. Animate `transform` and `opacity`; never a layout-affecting property. `.card-hover` lifts by
   `transform` only, over `--motion-2` with `--ease-out`.
2. Every hover/scroll motion has a `prefers-reduced-motion: reduce` guard. The guards live with their
   owning component — 46 sheets under `src/css/` carry one, and the shell's are in
   `src/css/app-shell.css`.
3. No animation is load-bearing: content is visible and usable with motion off.
4. The editor canvas is measured by the layout guard, so an animation that changes geometry is a
   gate failure rather than a design choice.

### Focus and geometry

- Focus uses `--app-ring` (two ring layers against the surface) or `--app-ring-inset` on dense
  controls; the accent is always the ring colour. Never remove an outline without replacing it.
- Shell geometry: top bar 56, rail 240 (64 collapsed), inspector 320, status bar 32, content max
  1200, card 280 (`--app-topbar-h`, `--app-rail-w`, `--app-rail-w-collapsed`, `--app-inspector-w`,
  `--app-statusbar-h`, `--app-content-max`, `--app-card-h`). The shell and the editor read the same
  tokens, which is why a change lands in both places or neither.

---

## Khmer event pack (36 templates)

### Pack palette roles

Every template declares eight roles. Layers name a role; the converter is the only
place a role becomes a hex value, which is what makes re-theming a palette swap.
**Colour is never hex in the pack source.**

| Role | What it is | Typical use |
|---|---|---|
| `bg` | page ground | poster background |
| `paper` | the raised surface | invitation card panel |
| `ink` | primary reading colour | names, body copy |
| `soft` | secondary reading colour | captions, venue lines |
| `accent` | the metal/festive colour | titles, rules, ornaments |
| `accent2` | the accent's shadow tone | ornament depth, borders |
| `deep` | the darkest panel tone | header band, footer block |
| `line` | hairlines | dividers, frame strokes |

Contrast is checked at build time against the opaque fill under every text layer:
4.5:1 for body, 3:1 for large text. A role pair that fails is a build defect, not a
design preference.

### Pack type packs

The pack designs in four registers and maps each font role to a registered family:

| Register | Khmer display | Khmer body | English | Used for |
|---|---|---|---|---|
| Ceremonial | Moul (→ Noto Serif Khmer) | Noto Serif Khmer | Cinzel / script (→ Noto Serif) | royal weddings, temple ceremonies |
| Elegant | Moulpali (→ Noto Serif Khmer) | Noto Serif Khmer | Playfair / Cormorant (→ Noto Serif) | modern weddings, anniversaries |
| Modern | Kantumruy Pro (→ Noto Sans Khmer) | Noto Sans Khmer | Jost (→ Noto Sans) | birthdays, business |
| Festive | Koulen (→ Noto Sans Khmer) | Battambang (→ Noto Sans Khmer) | Montserrat (→ Noto Sans) | new year, water festival |

Substitutions are listed in [FONT-SUBSTITUTIONS.md](templates/FONT-SUBSTITUTIONS.md);
the gap is tracked in [FONT-GAP-2026-10-25.md](templates/FONT-GAP-2026-10-25.md).
No design downloads a third-party font at runtime.

### Khmer typesetting rules

- Khmer body line-height 1.7–1.95 at design time. The rich-text renderer lets the
  text object's line-height win and floors it at the registered Khmer face's
  recommendation, so these values are what ships: the acceptance run measures
  1.70–1.95 in every pack template on every page.
- Khmer is always set larger than the English line beside it; Khmer glyphs have a
  smaller optical size at the same point size.
- `letter-spacing` is 0 on Khmer. Tracking breaks clusters.
- Word breaks are U+200B, inserted at ICU word boundaries; they are invisible and let
  every renderer wrap Khmer at a word instead of mid-cluster.
- Minimum text size is 1.9 % of canvas width; the safe margin is 3 % on all sides.

### Pack composition rules

- One dominant element per page (the title, or the names). The reading order is
  title → invitation sentence → names → date/time/venue → programme.
- Ornaments frame; they never cross a text box. Corners are symmetrical on
  ceremonial pages, asymmetric only on modern/festive ones.
- A bilingual pair is laid out as one block: Khmer above, English below, both left
  aligned to the same margin (centred on centred designs).
- Photo slots are rectangles or ellipses with a visible placeholder; the photo is
  always replaceable and never cropped by a fixed mask the user cannot change.
- Colour appears in the ornament, the accent rule and the title. Body copy uses
  `ink` or `soft`, never `accent`.

### Pack canvas set

`a5p` 1000×1414 · `p45` 1080×1350 · `sq` 1080×1080 · `story` 1080×1920.
The pack's 36 templates use `a5p` for every invitation (print-ready A5 at
144 dpi equivalent); the gallery also accepts the other three for custom work.

### Pack editing model

Every page is a normal design page: text objects are rich text, images are
ornament SVGs with alt text, and names/dates are bound placeholders. Nothing about
the pack is special-cased in the editor, so editing, undo, export and the guest
page behave exactly as they do for built-in templates.
