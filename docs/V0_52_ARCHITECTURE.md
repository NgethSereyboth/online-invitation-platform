# V0.52 Architecture Note

V0.52 is a release-label correction and hardening pass over the cumulative V34–V52 implementation. It does not restart the product or introduce a new framework.

## Compatibility identifiers

The following names intentionally remain unchanged because they are already persistence or caller contracts:

- `/api/platform/v52/*`
- `future_platform_v52/`
- `future-studio-loader-v52.js`
- `eventEcosystemV52`
- `event_*_v52` database tables
- V52 document feature keys and migration records

They describe the internal milestone family. The externally presented cumulative product version is **V0.52**.

## Deferred-loading boundary

`editor-deferred-tools-bootstrap-v0_52.js` is the only canonical launcher for the large AI, advanced-editor, and font-browser entry points. Vector, raster, collaboration, V32 operations, and V34–V0.52 platform modules remain lazy-loaded. Generated route bundles are produced from `route-bundle-sources-v15.json`; generated bundles are never the source of truth.

## UI and CSP boundary

`future-ui-v0_52.js` provides element creation, text assignment, accessible native dialogs, form-value collection, and lifecycle cleanup without `innerHTML`, `insertAdjacentHTML`, runtime `<style>` text, `eval`, or `new Function`. Mobile platform UI is modal and desktop UI is complementary.

## Security and data boundaries

- AI provider credentials remain server-side and are excluded from saved routing policy documents.
- Marketplace moderation is separated from author submission.
- Production domain verification is provider-backed.
- Plugin manifests remain declarative and permission allow-listed.
- Animation execution is property and resource bounded.
- Bulk generation retains only declared/mapped fields and token hashes.
- Schema 27 and all previous migration paths remain unchanged.
