# Font substitutions for the template pack

Every role in `template-pack/fonts.json` maps to a font id the app already ships. The map is
`FONT_ROLES` in `tools/build-template-pack.py`; this table is the human-readable record required by TP-2.2.

| pack role | requested family | shipped as | what changes |
|---|---|---|---|
| `kh.moul` | Moul | `noto-serif-khmer` | Loses Moul's heavy ceremonial strokes; keeps Khmer shaping and the larger-than-English size relation. |
| `kh.moulpali` | Moulpali | `noto-serif-khmer` | Serif Khmer instead of Moulpali; names stay one line (auto-fit only if a substituted line would clip). |
| `kh.koulen` | Koulen | `noto-sans-khmer` | Sans Khmer replaces the condensed display face used on festive titles. |
| `kh.bokor` | Bokor | `noto-serif-khmer` | Declared in the pack but not used by a shipped layer; mapped for completeness. |
| `kh.serif` | Noto Serif Khmer | `noto-serif-khmer` | Exact. |
| `kh.sans` | Noto Sans Khmer | `noto-sans-khmer` | Exact. |
| `kh.battambang` | Battambang | `noto-sans-khmer` | Slightly narrower; body line-height unchanged (≥1.7). |
| `kh.kantumruy` | Kantumruy Pro | `noto-sans-khmer` | Modern sans instead of Kantumruy Pro. |
| `lat.cormorant` | Cormorant Garamond | `noto-serif` | Wider body face; the converter fits text inside the designed box. |
| `lat.playfair` | Playfair Display | `noto-serif` | High-contrast serif replaced by Noto Serif. |
| `lat.script` | Great Vibes | `noto-serif` | Script names render upright; this is the most visible substitution. |
| `lat.cinzel` | Cinzel | `noto-serif` | Roman capitals replaced by Noto Serif; `text-transform` is preserved. |
| `lat.montserrat` | Montserrat | `noto-sans` | Geometric sans replaced by Noto Sans. |
| `lat.jost` | Jost | `noto-sans` | Modern sans replaced by Noto Sans. |

## Rules that keep the substitution safe

1. **No retyping.** The converter copies strings from `copy-bank.json`; it never edits a Khmer value.
2. **Fit, not overflow.** Each text box is at least the measured line height (×1.06 + 18 px). `textAutoFit: fit`
   with the designed size as the max shrinks a line only if the wider substituted face would clip. The acceptance
   scan over all 36 templates reports zero overflowing text objects.
3. **Khmer is always larger than its English companion**, as designed, and Khmer `letterSpacing` is 0 (checked in
   `tests/test_template_pack.py` and again in the acceptance harness).
4. **No runtime font request.** Both substituted faces are in the editor bundle; no CDN and no third-party origin is
   used (proof: `artifacts/next-work/review-tp/tp-2-2-network.json`).

## Replacing a substitution later

The substitution is one line in `FONT_ROLES`. To use a real family, first add it to the typography contract under
TP-OD-1 (WOFF2 + SHA-256 + licence + `@font-face`), then point the role at the new id, run
`python3 tools/build-template-pack.py`, and re-run the acceptance harness. No template JSON changes.
