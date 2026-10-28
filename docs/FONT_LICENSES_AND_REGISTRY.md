# Font Licenses and Registry

## Purpose

V20 treats fonts as trusted application resources, not document-supplied CSS. Invitation documents persist stable font IDs and English/Khmer pairing IDs. The renderer resolves those IDs through generated, fixed stacks.

The editable registry source is `docs/typography-contract.json`. Do not hand-edit the generated
`typography-contract.js`, `typography_contract.py`, or `typography-fonts.css`; regenerate them from the
repo root with:

```text
python3 src/python/generate_typography_contract.py
```

## Bundled license

The bundled Noto assets are distributed under the **SIL Open Font License 1.1**. The included license text is:

- `licenses/fonts/Noto-OFL-1.1.txt`
- `licenses/fonts/Inter-OFL-1.1.txt` (app-chrome Inter, see [App-chrome fonts](#app-chrome-fonts))

The registry records copyright metadata for each bundled family. The OFL permits bundling, embedding, redistribution, and modification subject to its terms. This document is an engineering inventory, not a substitute for legal review.

## App-chrome fonts

The app's own chrome (headings, body, buttons, panels on the dashboard, admin,
materials, templates, analytics, responses, billing, account, reset, verify,
designer, and index pages) uses the CSS variable stacks

```text
--canvas-font:    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
--canvas-display: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

defined in `src/css/canvas-plus.css` (and its `editor-suite.css` source twin).
`Inter` is **self-hosted** as WOFF2 so headings never depend on a host-installed
font: on a host without Inter the stack would degrade to the OS generic, and some
Linux/fontconfig configurations resolve that generic to a cursive face, which is
exactly the "cursive headings" symptom observed on machines lacking Inter.

Inter is **not** part of the invitation-document font registry above (it never
shapes invitation content), so it has no stable ID / pairing and is declared
directly by `src/css/canvas-plus.css` via `@font-face` rather than through
`typography-contract.json`.

| Family | Source | License | Weights | Asset (SHA-256) |
|---|---|---|---:|---|
| `Inter` | Bundled WOFF2 (Inter v4.1 static, subset to Latin `U+0000-024F,U+1E00-1EFF,U+2000-206F`) | SIL OFL 1.1 — `licenses/fonts/Inter-OFL-1.1.txt` | 400 | `assets/fonts/inter-latin-400.woff2` (`09ff6647afcf600eed2fd4e2e8a7cca6a275d9ff97f6d06b74fbfd5e795775fc`) |
| `Inter` | same | same | 700 | `assets/fonts/inter-latin-700.woff2` (`ec43bf5290c66996f99f947107681b5940abc578ac8e6d1135d2a79eb5e45d39`) |
| `Inter` | same | same | 800 | `assets/fonts/inter-latin-800.woff2` (`ef3b7c9d5d14a43607498b1ec74f4f251e35d7b57b381c12b3f32b4f13fc9a30`) |

The `@font-face` rules use `font-display:swap` and the same `unicode-range` as the
bundled Noto Latin faces, so Inter is only requested for Latin script; Khmer
rendering continues to come from the bundled Noto Khmer faces. These assets are
synced into the served mirror `src/python/assets/fonts/` by
`src/python/build/sync_frontend_assets.py` and into each route bundle that loads
`canvas-plus.css` by `src/python/build/build_route_bundles.py`.

## Stable font registry

| Stable ID | Display label | Source | Scripts | Weights | Document-safe |
|---|---|---|---|---|---|
| `noto-sans` | Noto Sans | Bundled WOFF2 | Latin; Khmer fallback | 400, 700 | Yes |
| `noto-serif` | Noto Serif | Bundled WOFF2 | Latin; Khmer fallback | 400, 700 | Yes |
| `noto-sans-khmer` | Noto Sans Khmer | Bundled WOFF2 | Khmer; Latin fallback | 400, 700 | Yes |
| `noto-serif-khmer` | Noto Serif Khmer | Bundled WOFF2 | Khmer; Latin fallback | 400, 700 | Yes |
| `serif-georgia` | Classic Serif (system) | OS font plus bundled Noto fallbacks | Latin; Khmer fallback | 400, 700 | Legacy/system option |
| `sans-arial` | Modern Sans (system) | OS font plus bundled Noto fallbacks | Latin; Khmer fallback | 400, 700 | Legacy/system option |
| `sans-trebuchet` | Friendly (system) | OS font plus bundled Noto fallbacks | Latin; Khmer fallback | 400, 700 | Legacy/system option |

`legacyOnly` system entries are retained to preserve V19.1 and older invitations. New recommended semantic styles use bundled Noto pairings.

## Bundled asset inventory and SHA-256

| Font ID | Weight | Asset | SHA-256 |
|---|---:|---|---|
| `noto-sans` | 400 | `assets/fonts/noto-sans-latin-400.woff2` | `f54a80e0d925f4e82d0cf52b3249a4b1320137363e98018a6f65377d3390aa8c` |
| `noto-sans` | 700 | `assets/fonts/noto-sans-latin-700.woff2` | `5fce99c92e68803bf3bf4f2c4a26ab0a649ddea0f11eaba28124d010183b69e5` |
| `noto-serif` | 400 | `assets/fonts/noto-serif-latin-400.woff2` | `0415cee63cb9ba43d5094caddd6d903d447cbc025dbe1c2a621f7855ffa1a99e` |
| `noto-serif` | 700 | `assets/fonts/noto-serif-latin-700.woff2` | `f66ce4961c2ca74153ccf8be0e112ba679575b6aacc3155371483b019155d1b7` |
| `noto-sans-khmer` | 400 | `assets/fonts/noto-sans-khmer-400.woff2` | `4edee25cbc3ad5877820db657b57cf7df5fae06ae7ecc0513209d3617efe99a3` |
| `noto-sans-khmer` | 700 | `assets/fonts/noto-sans-khmer-700.woff2` | `8bb47df185665c501e5d264547b0f7eb235b4fba6063a48d4b721f48474d72e3` |
| `noto-serif-khmer` | 400 | `assets/fonts/noto-serif-khmer-400.woff2` | `980724e3fd5f924c86df268bf5cd5a4b1f500e3446ae579e741ba3df9d0e1b9f` |
| `noto-serif-khmer` | 700 | `assets/fonts/noto-serif-khmer-700.woff2` | `89d8d06b2425e7bc67292401d475d6f047706a13c462f24e291121a64b8f24c2` |

### Bundled UI font (outside the invitation registry)

| Family | Weights | Assets | Licence | Licence file |
|---|---|---|---|---|
| Inter | 400, 700, 800 | `assets/fonts/inter-latin-400.woff2`, `inter-latin-700.woff2`, `inter-latin-800.woff2` | SIL Open Font License 1.1 | `licenses/fonts/Inter-OFL-1.1.txt` |

Inter is the application-shell face. It is bundled and self-hosted the same way as the invitation faces; it is not a document font choice and therefore has no registry entry.

`tests/v20_font_registry_loading_test.py` validates every file, digest, OpenType table presence, `FontFaceSet` load state, and measurable English/Khmer rendering in real Chromium.

## English/Khmer pairings

| Pairing ID | Label | English font | Khmer font | Status |
|---|---|---|---|---|
| `serif-formal` | Formal Serif | `noto-serif` | `noto-serif-khmer` | Recommended |
| `sans-modern` | Modern Sans | `noto-sans` | `noto-sans-khmer` | Recommended |
| `ceremonial-khmer` | Khmer Ceremonial | `noto-serif` | `noto-serif-khmer` | Recommended |
| `modern-system` | Modern System Sans | `sans-arial` | `noto-sans-khmer` | Legacy/system |
| `classic-system` | Classic System Serif | `serif-georgia` | `noto-serif-khmer` | Legacy/system |
| `friendly-system` | Friendly System Sans | `sans-trebuchet` | `noto-sans-khmer` | Legacy/system |

Locale detection is automatic for mixed invitation content and can be explicitly overridden by a supported locale. Pairing resolution chooses the English or Khmer member without changing the document’s pairing ID.

## Fixed fallback stacks

Fallback stacks are registry metadata and generated code. Examples:

```text
noto-serif:
'EInvite Noto Serif','Noto Serif','EInvite Noto Serif Khmer','Noto Serif Khmer','Khmer UI',Georgia,serif

noto-sans-khmer:
'EInvite Noto Sans Khmer','Noto Sans Khmer','Khmer UI','EInvite Noto Sans','Noto Sans',Arial,sans-serif
```

Documents never store these strings. They are resolved after validation.

## Exact legacy migrations

The registry accepts only exact known historical values and maps them to stable IDs. Representative mappings:

| Historical value | Stable ID |
|---|---|
| `Georgia,serif` / `Georgia, serif` | `serif-georgia` |
| `Arial,sans-serif` / `Arial, sans-serif` | `sans-arial` |
| `'Trebuchet MS',sans-serif` variants | `sans-trebuchet` |
| known Noto Serif Khmer / Khmer OS Battambang stacks | `noto-serif-khmer` |
| known Noto Sans Khmer / Khmer OS Battambang stacks | `noto-sans-khmer` |
| known Khmer OS Muol Light / Noto Serif stack | `noto-serif-khmer` |
| `Noto Serif Khmer` | `noto-serif-khmer` |
| `Noto Sans Khmer` | `noto-sans-khmer` |
| `Georgia` | `serif-georgia` |
| `Arial` | `sans-arial` |
| `inherit` or empty browser value | safe default `noto-serif` |

Unknown strings are not guessed. Strict server normalization rejects values such as `Papyrus, fantasy`, CSS declarations, `url()`, semicolons, braces, comments, controls, or oversized identifiers.

## Registry security rules

1. Stable IDs must match `[a-z0-9][a-z0-9-]{0,63}`.
2. Pairing IDs must be present in the generated pairing registry.
3. A bundled entry must name WOFF2 assets that exist and match recorded hashes.
4. A bundled entry must identify its license and license file.
5. Documents persist an ID or pairing ID only.
6. Renderer code may use only a registry-resolved fixed stack.
7. Unknown raw font strings are rejected at the strict server boundary.
8. Adding a font must not weaken CSP, asset-origin, or upload-validation rules.

## Adding a future licensed font

A future release should use this process:

1. Confirm embedding and redistribution rights.
2. Add the license text under `licenses/fonts/`.
3. Add optimized WOFF2 files under `assets/fonts/`.
4. Record stable ID, family, scripts, weights, assets, license metadata, copyright, and SHA-256 values in `docs/typography-contract.json`.
5. Add an English/Khmer pairing only when both language paths have reliable shaping and fallback.
6. Regenerate the contract.
7. Run model, hostile-input, WOFF2 metadata, real-browser loading, offline, Khmer shaping, visual geometry, public rendering, and CSP tests.
8. Never migrate an unknown historical CSS string by heuristic resemblance.

## Template pack (2026-10-25) — no new font file

The 36-template Khmer event pack requests 14 families; the registry ships the four Noto faces above.
Twelve families are substituted with the nearest registered face rather than added, so this order changes
no `@font-face` rule, no licence file and no `assetSha256`. **No new font file ships with this phase.**
The display-font item proposed as D-4 in `FREEBUFF-NEXT-STEPS-2026-10-27.md` (Moul, Moulpali, Kantumruy
Pro, Koulen, Battambang and seven others) was **not executed**; the pack substitutes registered faces,
and adding a real face is the registry process below — a licence file, WOFF2 assets, registry metadata
and a new digest — not a documentation change. The role-by-role map and the owner action that
would replace each substitution are in `docs/templates/FONT-GAP-2026-10-25.md` and
`docs/templates/FONT-SUBSTITUTIONS.md`. The pack's documents persist registry ids only, so a future
TP-OD-1 addition is a registry change plus one line in the converter, never a document migration.
