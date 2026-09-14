# V30 Non-Destructive Raster Workspace Architecture

Status: implementation complete; full-resolution performance and native GPU certification pending final V32 independent audit.

Raster edits are serialized operation documents that reference immutable source assets. Invitation JSON stores IDs, dimensions, operations, adjustments, layers, masks, crop/transform state and result references—not original image bytes or base64 payloads.

`raster-model-v30.js` defines the edit format. `raster-workspace-v30.js` provides recoverable sessions, crop/transform, selections, brush/eraser/clone/heal operation records, adjustment layers, before/after preview and safe Apply/Save-as-new/Cancel boundaries. `raster-worker-v30.js` provides bounded tile planning and cancellation. `platform_v32` persists edit documents and runs idempotent raster jobs. The local Pillow adapter renders bounded images; production storage and queue adapters retain immutable originals and private full-resolution outputs.
