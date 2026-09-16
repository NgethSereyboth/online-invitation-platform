# V19.1 Typography Stabilization Changelog

Release date: 2026-07-28  
Baseline: `e-invitation-platform-advanced-typography-v19.zip`  
Invitation compatibility: `schemaVersion: 13`

## Fixed

- Added `justify` to the authoritative server persistence/publication contract.
- Added strict server validation and normalization for every V19 typography field and numeric relationship.
- Replaced stored font-family CSS with trusted stable font IDs and fixed renderer stacks.
- Added deterministic migration for recognized legacy font stacks and rejection for unknown strings.
- Repaired client `NaN`/infinity/null/malformed numeric normalization and JSON serialization.
- Rebuilt responsive auto-fit to preserve configured, minimum, maximum, and computed values separately.
- Added shared editor/public fitting and refit hooks after layout, fonts, ResizeObserver, and window resize.
- Restored vertical alignment for multi-column text using outer flex and inner column flow.
- Made Advanced text layout a full-width accordion on desktop and mobile.
- Unified the 8–200 font-size contract and exposed computed fit separately.
- Kept mobile transform targets at 44×44px with 10–14px visual knobs and tiny-object non-overlap.
- Made page thumbnails reuse normalized typography projection.
- Bundled licensed, subsetted English/Khmer Noto WOFF2 families and font-loading synchronization.

## Security

- Rejects semicolons, CSS comments, `url()`, control characters, unknown font IDs, malformed types, unknown enums, huge font values, and non-finite numbers.
- Published styles are resolved only from the generated trusted font registry.

## Tests

- Added six required V19.1 suites and promoted them to the official gate.
- Final gate: 41 deterministic checks and 23 required browser suites.
- Three consecutive Linux release runs passed; Windows target-machine certification remains pending.
