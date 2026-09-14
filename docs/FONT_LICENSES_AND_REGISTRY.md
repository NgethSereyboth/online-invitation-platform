# Font Licenses and Registry

## Purpose

V20 treats fonts as trusted application resources, not document-supplied CSS. Invitation documents persist stable font IDs and English/Khmer pairing IDs. The renderer resolves those IDs through generated, fixed stacks.

The editable registry source is `typography-contract.json`. Do not hand-edit generated `typography-contract.js`, `typography_contract.py`, or `typography-fonts.css`; regenerate them with:

```text
python generate_typography_contract.py
```

## Bundled license

The bundled Noto assets are distributed under the **SIL Open Font License 1.1**. The included license text is:

- `licenses/fonts/Noto-OFL-1.1.txt`

The registry records copyright metadata for each bundled family. The OFL permits bundling, embedding, redistribution, and modification subject to its terms. This document is an engineering inventory, not a substitute for legal review.

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
| `noto-sans` | 400 | `assets/fonts/noto-sans-latin-400.woff2` | `6932db6a846e5f3eedd70862935d1e382ffa25da0851563c3e7b82129ebefe23` |
| `noto-sans` | 700 | `assets/fonts/noto-sans-latin-700.woff2` | `a9885073a1b8fcde1b37ac0c4497914e598cc9057344a552217b32e4c89f0866` |
| `noto-serif` | 400 | `assets/fonts/noto-serif-latin-400.woff2` | `3c94a973daf5e7fd05cb205eab2171b0af0ba42496202d54e6cdd55e45a82221` |
| `noto-serif` | 700 | `assets/fonts/noto-serif-latin-700.woff2` | `d7e6e94e00d65d77273e033e0eca185d9ab37d44d4505225f364ff1453cb7039` |
| `noto-sans-khmer` | 400 | `assets/fonts/noto-sans-khmer-400.woff2` | `53229761be85cb21c727d19ff81e959f3a35c32925d42f02829acf53dbdbf625` |
| `noto-sans-khmer` | 700 | `assets/fonts/noto-sans-khmer-700.woff2` | `0eb1923fffc493ed3af0e5cb4bc467ec1c7921ce9f845888ebd3b5755b86aecd` |
| `noto-serif-khmer` | 400 | `assets/fonts/noto-serif-khmer-400.woff2` | `db80eb1479b0cb726e5fd224ba2cde7b6f92825988f4ec1e89575d851011e625` |
| `noto-serif-khmer` | 700 | `assets/fonts/noto-serif-khmer-700.woff2` | `fe903cee1be19a931d38a575948897f7c0d0159a8c2c028af596ec928d7976ce` |

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
4. Record stable ID, family, scripts, weights, assets, license metadata, copyright, and SHA-256 values in `typography-contract.json`.
5. Add an English/Khmer pairing only when both language paths have reliable shaping and fallback.
6. Regenerate the contract.
7. Run model, hostile-input, WOFF2 metadata, real-browser loading, offline, Khmer shaping, visual geometry, public rendering, and CSP tests.
8. Never migrate an unknown historical CSS string by heuristic resemblance.
