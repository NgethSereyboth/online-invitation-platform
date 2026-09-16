# Khmer Typography — W3C Khmer Script Resources Implementation

> Phase 2b deliverable of `docs/ROADMAP.md`. Documents how the eInvite platform
> implements the [W3C Khmer Script Resources](https://www.w3.org/International/sealreq/khmer/)
> guidelines for self-hosted Khmer typography. Companion to:
> - `docs/a11y/WCAG-AA-AUDIT.md` — per-page WCAG 2.1 AA audit.
> - `docs/FONT_LICENSES_AND_REGISTRY.md` — V20 font registry and OFL inventory.
> - `docs/typography-contract.json` — generated font contract (source of truth for `window.EInviteFontRegistry`).
> - `assets/fonts/registry.json` — contributor-facing manifest of vetted Khmer-safe fonts (Phase 2b).
> - `src/css/typography-fonts.css` — generated `@font-face` declarations.
> - `licenses/fonts/Noto-OFL-1.1.txt` — full SIL Open Font License 1.1 text.

---

## 1. Why a Khmer-specific typography doc?

Khmer (ខ្មែរ, Unicode block `U+1780–17FF` with lunar-space `U+19E0–19FF`) is an **abugida**, not an alphabet. It uses:

- **Consonants with inherent vowels** that change with diacritics.
- **Subscript consonants** (Coeng form, `U+17D2` JNJ) — stacked below base consonants.
- **Above- and below-base marks** (vowels, signs, numerals).
- **Reordering** — the inherent-vowel `U+17C6` (AA dependent vowel sign) renders *before* the base consonant even though it follows it in logical order.
- **Complex stacking** that yields **tall ascenders and deep descenders**.

Latin CSS defaults break Khmer: line-height of `1.4` clips subscripts; `letter-spacing` wider than `0` opens abugida clusters; `font-feature-settings: "liga" off` strips contextual shaping. This doc tells contributors *exactly* which values are safe and why.

---

## 2. W3C Khmer Script Resources — implementation mapping

Source: <https://www.w3.org/International/sealreq/khmer/> (W3C Internationalization sealreq, March 2026).

| W3C guidance | eInvite implementation | File / value |
|---|---|---|
| Khmer requires **software shaping** (HarfBuzz / DirectWrite / CoreText). Browsers ship shapers; do **not** disable OpenType features. | `font-feature-settings` left at defaults for Khmer blocks; `font-variant-ligatures: common-ligatures contextual` for `.preview[lang="km"]` in the font browser card preview. Never `font-feature-settings: "liga" off` on Khmer text. | `src/css/custom-fonts-v22.css:6` |
| Khmer needs **taller line-height than Latin** — do not inherit the Latin value. | Latin default `line-height: 1.4–1.5`; Khmer default **`line-height: 1.6`** for body, `1.5` for headings. Set per-script via `:lang(km)` selector — see §4. | `src/css/typography-fonts.css` (declaration block) + per-page CSS |
| **Vertical metrics**: Khmer has tall ascenders + descenders — `unitsPerEm` up to 2048; ascender ~1700, descender ~−700 typical in Noto Khmer. | Each font registry entry records `recommendedLineHeight` (Khmer = `1.42–1.6`; Latin = `1.3`); the font browser applies `preview.style.lineHeight = Math.max(1.2, recommendedLineHeight)` | `src/js/custom-fonts-v22.js:16` (`recommendedLineHeight: finite(...scripts.includes('Khmer')?1.42:1.3, 1.15, 1.8)`) |
| **Font-size floor**: Khmer body text below 16px loses subscript legibility. | The V20 typography contract clamps `fontSize` to `[8, 200]`; the editor UX default is 32px. Document 16px floor for Khmer body text in `font-browser.js` preview. | `src/js/typography-contract.js:13` |
| **Letter-spacing**: Khmer **must** be `normal` — positive letter-spacing breaks abugida clusters. | `.preview[lang="km"]` rule sets `letter-spacing: normal` (default) and `word-break: normal; overflow-wrap: normal; line-break: strict`. | `src/css/custom-fonts-v22.css:6` |
| **OpenType features**: 13 features in Noto Sans Khmer (`ccmp`, `liga`, `clig`, `kern`, `mark`, `mkmk`, `locl`, `ccmp`, `akhn`, `pref`, `pstf`, `blwf`, `abvs`/`blws` — the Khmer-specific shaping features). | We do NOT disable any of these for bundled Noto. We DO surface `khmerFeatures[]` in the per-font metadata for uploaded custom fonts so the registry can flag fonts missing shaping tables. | `src/js/custom-fonts-v22.js:16` (`khmerFeatures` field) + `assets/fonts/registry.json` `opentype_features` field |
| **Numbers**: Khmer has its own digit set `U+17E0–17E9`. Do not force Latin digits in Khmer content. | Editor surfaces a `languageMode` selector (`en` / `km` / `both`) at `src/html/index.html:66`. The Khmer lunar-date preview uses Khmer digits where `dateFormat` is `both` or `khmer`. | `src/html/index.html:66–72` |
| **Font fallback**: pair Khmer primary with a Khmer fallback (not Latin). | Each font registry entry's `stack` lists a Khmer family before/after the primary, never a Latin-only fallback for Khmer content. See `assets/fonts/registry.json` `stack` field per entry. | `docs/typography-contract.json` `fonts.*.stack` |
| **ZWNJ / ZWJ**: Khmer uses `U+200D` ZWJ rarely and `U+200C` ZWNJ essentially never; document that the editor must not strip these. | The V13 rich-text sanitizer allow-lists both characters. | `src/python/server.py:729-799` (`_RichTextSanitizer`) |

---

## 3. Self-hosted Noto Khmer — verification + variable-font plan

### 3.1 What is currently self-hosted

`assets/fonts/` contains **8 static-weight WOFF2 files**:

| File | Family | Weight | Size (bytes) | Type |
|---|---|---|---|---|
| `noto-sans-khmer-400.woff2` | Noto Sans Khmer | 400 | 15 236 | Static WOFF2 (single weight) |
| `noto-sans-khmer-700.woff2` | Noto Sans Khmer | 700 | 16 692 | Static WOFF2 (single weight) |
| `noto-serif-khmer-400.woff2` | Noto Serif Khmer | 400 | 20 336 | Static WOFF2 (single weight) |
| `noto-serif-khmer-700.woff2` | Noto Serif Khmer | 700 | 22 732 | Static WOFF2 (single weight) |
| `noto-sans-latin-400.woff2` | Noto Sans (Latin) | 400 | 35 712 | Static WOFF2 |
| `noto-sans-latin-700.woff2` | Noto Sans (Latin) | 700 | 35 152 | Static WOFF2 |
| `noto-serif-latin-400.woff2` | Noto Serif (Latin) | 400 | 36 252 | Static WOFF2 |
| `noto-serif-latin-700.woff2` | Noto Serif (Latin) | 700 | 37 052 | Static WOFF2 |

All four Khmer assets are **single-weight WOFF2**, ~15–23 KB each. A genuine Khmer variable WOFF2
(weight axis 100–900) is typically 70–150 KB. Sizes confirm the current files are static instances.

### 3.2 Why we do NOT use `npm install @fontsource-variable/noto-sans-khmer`

ROADMAP ground rule 4 forbids build steps (no bundlers, no transpilers, no `npm install`). The
`@fontsource-variable/noto-sans-khmer` package is the right font — it ships the Google Fonts
variable WOFF2 — but installing it via npm would introduce a `node_modules/` tree and a packaging
step the project deliberately avoids.

Instead, contributors self-host the variable WOFF2 **directly**, by downloading the file once and
committing it to `assets/fonts/`.

### 3.3 Maintainer procedure — adding the variable Khmer font

> Replace the two static files `noto-sans-khmer-400.woff2` and `noto-sans-khmer-700.woff2`
> with a single variable WOFF2 once a maintainer can run the fetch step below. This is **not
> blocking** — the two static weights already cover the AA requirement.

1. **Download the variable WOFF2** from one of these OFL-1.1 sources (in priority order):
   - **notofonts.github.io**: <https://github.com/notofonts/khmer/releases> → `NotoSansKhmer\[wght\].woff2` (variable, weight axis 100–900).
   - **Google Fonts API**: `https://fonts.gstatic.com/s/notosanskhmer/v30/<hash>.woff2` — fragment obtained from `https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@100..900&display=swap` (look at the `@font-face` `src: url(...)`).
   - **Fontsource CDN** (download only — do not hotlink in production): `https://cdn.jsdelivr.net/fontsource/fonts/noto-sans-khmer:vf@latest/latin-ext-wght-normal.woff2`.
2. **Place the file** at `assets/fonts/noto-sans-khmer-variable.woff2`.
3. **Verify OFL-1.1** — open the font in `fontTools` (`ttx -t name noto-sans-khmer-variable.woff2`)
   and confirm `nameID 0` (Copyright) and `nameID 13` (License Description) match the OFL-1.1 text
   at `licenses/fonts/Noto-OFL-1.1.txt`.
4. **Add a `@font-face` rule** to `src/css/typography-fonts.css` with the variable-weight descriptor:

   ```css
   @font-face{
     font-family:'EInvite Noto Sans Khmer';
     src:url('assets/fonts/noto-sans-khmer-variable.woff2') format('woff2-variations');
     font-weight:100 900;
     font-style:normal;
     font-display:swap;
     unicode-range:U+1780-17FF,U+19E0-19FF;
   }
   ```

   Place it BEFORE the two static-weight declarations so browsers that support `format('woff2-variations')`
   pick the variable file; older browsers fall through to the static weights.
5. **Re-run the bundle builder**:

   ```bash
   python3 src/python/build_route_bundles.py
   python3 src/python/sync_frontend_assets.py
   ```

6. **Update `docs/typography-contract.json`** `fonts["noto-sans-khmer"].assets` to point at the
   variable file and list `"weights":[100,200,300,400,500,600,700,800,900]`. Re-run:

   ```bash
   python3 src/python/generate_typography_contract.py
   ```

   The generator will rewrite `typography-contract.js`, `typography_contract.py`, and
   `typography-fonts.css` from the JSON. Keep the test assertion in
   `tests/v20_font_registry_loading_test.py:18` happy: 4 Khmer `unicode-range` occurrences + 4 Latin.

7. **Update `assets/fonts/registry.json`** (this Phase 2b manifest) — set
   `noto-sans-khmer.weights` to `[100,200,300,400,500,600,700,800,900]` and `file_path` to
   the variable file.

8. **Verify SHA-256** with `sha256sum assets/fonts/noto-sans-khmer-variable.woff2` and
   record the digest in both `assets/fonts/registry.json` (`sha256` field) and
   `docs/typography-contract.json` (`assetSha256` block).

### 3.4 `@font-face` declarations — current state

The current `src/css/typography-fonts.css` (10 lines, generated by
`generate_typography_contract.py:39-40`) declares **8 static @font-face rules**:

```css
/* Generated trusted typography font faces. Bundled Noto assets use SIL OFL 1.1. */
@font-face{font-family:'EInvite Noto Sans';src:url('assets/fonts/noto-sans-latin-400.woff2') format('woff2');font-style:normal;font-weight:400;font-display:swap;unicode-range:U+0000-024F,U+1E00-1EFF,U+2000-206F;}
@font-face{font-family:'EInvite Noto Sans';src:url('assets/fonts/noto-sans-latin-700.woff2') format('woff2');font-style:normal;font-weight:700;font-display:swap;unicode-range:U+0000-024F,U+1E00-1EFF,U+2000-206F;}
@font-face{font-family:'EInvite Noto Serif';src:url('assets/fonts/noto-serif-latin-400.woff2') format('woff2');font-style:normal;font-weight:400;font-display:swap;unicode-range:U+0000-024F,U+1E00-1EFF,U+2000-206F;}
@font-face{font-family:'EInvite Noto Serif';src:url('assets/fonts/noto-serif-latin-700.woff2') format('woff2');font-style:normal;font-weight:700;font-display:swap;unicode-range:U+0000-024F,U+1E00-1EFF,U+2000-206F;}
@font-face{font-family:'EInvite Noto Sans Khmer';src:url('assets/fonts/noto-sans-khmer-400.woff2') format('woff2');font-style:normal;font-weight:400;font-display:swap;unicode-range:U+1780-17FF,U+19E0-19FF;}
@font-face{font-family:'EInvite Noto Sans Khmer';src:url('assets/fonts/noto-sans-khmer-700.woff2') format('woff2');font-style:normal;font-weight:700;font-display:swap;unicode-range:U+1780-17FF,U+19E0-19FF;}
@font-face{font-family:'EInvite Noto Serif Khmer';src:url('assets/fonts/noto-serif-khmer-400.woff2') format('woff2');font-style:normal;font-weight:400;font-display:swap;unicode-range:U+1780-17FF,U+19E0-19FF;}
@font-face{font-family:'EInvite Noto Serif Khmer';src:url('assets/fonts/noto-serif-khmer-700.woff2') format('woff2');font-style:normal;font-weight:700;font-display:swap;unicode-range:U+1780-17FF,U+19E0-19FF;}
```

Each rule uses **`unicode-range`** to scope the Khmer (`U+1780-17FF, U+19E0-19FF`) and Latin
(`U+0000-024F, U+1E00-1EFF, U+2000-206F`) blocks, so a single font-family stack renders mixed
Khmer+Latin text by pulling only the glyphs each script needs. `font-display: swap` ensures the
invitation text paints immediately in a system fallback and re-renders once Noto Khmer arrives —
critical for slow mobile networks in Cambodia.

A new contributor can verify the declarations are correctly generated by running:

```bash
python3 src/python/generate_typography_contract.py
# prints: TYPOGRAPHY_CONTRACT_GENERATED
diff src/css/typography-fonts.css src/python/typography-fonts.css  # must be identical
```

### 3.5 License

All Noto fonts are **SIL Open Font License 1.1**. The full license text is at
`licenses/fonts/Noto-OFL-1.1.txt`. OFL-1.1 permits bundling, embedding, redistribution, and
modification (including renaming — hence `EInvite Noto Sans Khmer` as the embedded family name).
See `docs/FONT_LICENSES_AND_REGISTRY.md` for the V20 license inventory.

---

## 4. CSS recipe — Khmer-safe typography defaults

The platform does NOT yet ship a global `:lang(km)` override (tracked as follow-up `WCAG-AA-AUDIT.md`
§6 — Khmer-specific issues). When adding one, the **only** correct values are:

```css
/* Safe defaults for Khmer body text. Do NOT inherit Latin values. */
:lang(km), [lang="km"] {
  font-family: 'EInvite Noto Sans Khmer', 'Noto Sans Khmer', 'Khmer UI', Arial, sans-serif;
  font-size: 16px;            /* Khmer floor — below this, subscripts become illegible */
  line-height: 1.6;          /* W3C: Khmer needs taller line-height than Latin */
  letter-spacing: normal;    /* NEVER apply letter-spacing to Khmer — breaks abugida clusters */
  word-break: normal;        /* Khmer words do not use spaces; rely on ZWJ + breaking rules */
  overflow-wrap: normal;
  line-break: strict;
  font-feature-settings: normal;   /* enable all 13 Noto Khmer shaping features */
  font-variant-ligatures: common-ligatures contextual;
  font-kerning: normal;
  font-synthesis: none;      /* never synthesize bold/italic for Khmer — use real weights */
}

:lang(km) h1, :lang(km) h2, :lang(km) h3 {
  line-height: 1.5;           /* headings can be tighter but still ≥1.5 */
  font-weight: 700;
}

/* Latin counterpart for comparison */
:lang(en), [lang="en"] {
  font-size: 16px;
  line-height: 1.5;
  letter-spacing: normal;
}
```

The font browser preview at `src/js/font-browser.js:23` already applies `preview.lang = 'km'`
and `preview.style.lineHeight = Math.max(1.2, f.recommendedLineHeight)` for Khmer entries, so
the preview card shows Khmer at the correct line-height even before a global `:lang(km)` rule
exists.

---

## 5. OpenType features in Noto Sans Khmer

Noto Sans Khmer ships **13 OpenType features** (subset of the GSUB/GPOS tables). The W3C guidance
is "do not disable any of these for Khmer text". This table documents each so contributors know
what is at stake:

| Feature tag | Purpose | Why it matters for Khmer |
|---|---|---|
| `ccmp` | Glyph composition / decomposition | Builds complex conjuncts (Coeng stacks). Without `ccmp`, the renderer cannot combine `U+1780` (ក) + `U+17D2` (Coeng) + `U+1781` (ខ) into the correct subscript stack. |
| `akhn` | Akhand (mandatory ligatures) | Required for historical/orthographic ligatures that cannot be decomposed. |
| `pref` | Pre-base form | Reorders `U+17C6` (AA dependent vowel) to render BEFORE the base consonant. Without `pref`, the vowel appears after the consonant visually, which is wrong. |
| `blwf` | Below-base form | Stacks subscript consonants below the base. |
| `pstf` | Post-base form | Reorders vowels that follow but render after the consonant cluster. |
| `abvs` | Above-base substitutions | Shapes above-base vowel marks and signs (e.g. `U+17B6` AA). |
| `blws` | Below-base substitutions | Shapes below-base vowel marks and signs. |
| `psts` | Post-base substitutions | Shapes post-base marks. |
| `haln` | Halant form | Used when explicit halant (virama) shapes appear. |
| `liga` | Standard ligatures | Contextual Khmer ligatures; mostly off-by-default in Latin but mandatory for Khmer. |
| `clig` | Contextual ligatures | Picks the correct glyph form based on surrounding context. |
| `kern` | Kerning | Adjusts spacing between specific glyph pairs; Khmer kerns are subtle but non-zero. |
| `mark` / `mkmk` | Mark-to-base / mark-to-mark positioning | Positions vowel signs and other marks relative to the base consonant and to each other (essential for stacked marks). |

The font registry at `assets/fonts/registry.json` records which of these features each bundled
font exposes (`opentype_features` field). Uploaded custom fonts are probed for `khmerFeatures[]`
at `src/js/custom-fonts-v22.js:16`.

---

## 6. Browser support notes

| Browser | Shaper | Variable font | `woff2-variations` |
|---|---|---|---|
| Chrome / Edge ≥ 113 | HarfBuzz | Yes | Yes |
| Firefox ≥ 116 | HarfBuzz | Yes | Yes |
| Safari ≥ 16 | CoreText | Yes | Yes (via `woff2` with `font-weight: 100 900`) |
| Older Android WebView | HarfBuzz | Partial (some 4.4–7.0 lack variable support) | Falls back to nearest static weight |
| IE 11 | Uniscribe | No | No — falls back to system Khmer UI font |

The `font-display: swap` directive in every `@font-face` rule ensures Khmer text paints
immediately in the system fallback (`Khmer UI` on Windows, `Suon Panhassey` on older macOS,
`Nokora` on Linux) and re-renders once Noto arrives. We deliberately do not use `font-display:
optional` because the visual jump between system Khmer and Noto Khmer is jarring on invitation
hero text.

---

## 7. Follow-up work tracked elsewhere

- `docs/a11y/WCAG-AA-AUDIT.md` §6 (Khmer-specific) — pages that need `:lang(km)` overrides, dynamic
  `lang` switching on `public.html` (currently hardcoded `lang="en"`).
- `docs/FONT_LICENSES_AND_REGISTRY.md` — V20 license inventory and stable-ID registry (source of
  truth for the generated contract).
- `assets/fonts/registry.json` — Phase 2b contributor-facing manifest of vetted Khmer-safe fonts.
- P1-B worklog entry — `src/python/server.py:6553` reflected-HTML-injection gap on
  `__INVITATION_SLUG__` (CSP script-src 'self' blocks script execution, but defense-in-depth
  violated). When that is fixed, dynamic `<html lang>` switching becomes safe on `public.html`.

---

## 8. Change history

| Date | Version | Change |
|---|---|---|
| 2026-09-14 | V54.2 | Phase 2b — initial document. W3C Khmer Script Resources mapping, self-host variable-font plan, @font-face declaration inventory, OpenType feature table, Khmer-safe CSS recipe. |

*Cross-references: `docs/a11y/WCAG-AA-AUDIT.md`, `docs/FONT_LICENSES_AND_REGISTRY.md`,
`docs/typography-contract.json`, `assets/fonts/registry.json`, `src/css/typography-fonts.css`,
`src/css/custom-fonts-v22.css`, `src/js/custom-fonts-v22.js`, `src/js/font-browser.js`,
`licenses/fonts/Noto-OFL-1.1.txt`.*
