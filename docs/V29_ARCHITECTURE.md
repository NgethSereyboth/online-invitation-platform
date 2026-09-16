# V29 Professional Layers and Vector Architecture

Status: implementation complete; certification pending final V32 independent audit.

V29 introduces `professionalScene` version 1 as a normalized hierarchy shared by persistence, editor transactions, public rendering, copy/paste, component references, and future collaboration. Existing `objects`, `designPages`, and `sceneTree` remain compatibility projections; the structured invitation document remains authoritative.

## Bounded modules

- `document-schema-v32.js` / `document_schema_v32.py`: schema-18 migration and validation.
- `scene-graph-v29.js`: hierarchy, stable IDs, order keys, world/local matrices, grouping, frames, masks, component definitions and instances.
- `professional-layers-v29.js`: accessible virtualized tree, selection synchronization, reorder/nesting, filters, rename, visibility/lock and precision actions.
- `vector-model-v29.js`: vector primitives, paths, sanitized SVG import/export, node mutation and bounded boolean/compound operations.
- `advanced-public-renderer-v32.js`: public vector, mask and component fallback rendering.

The hierarchy depth is capped at 24 and the scene at 10,000 nodes. Unsupported boolean operations report an explicit unsupported state rather than flattening or corrupting geometry. Editor overlays never enter public SVG.
