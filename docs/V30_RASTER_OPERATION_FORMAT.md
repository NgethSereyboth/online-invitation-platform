# V30 Raster Operation Format

Each edit document has `id`, `version`, `sourceAssetId`, `sourceAssetVersion`, pixel metadata, `operations`, `adjustments`, `layers`, `masks`, `crop`, `transform`, preview/export asset IDs, status and fingerprint.

Operations are ordered deterministic objects with stable IDs, a declared type, bounded parameters, enabled state and optional mask/layer target. Adjustments are reorderable, toggleable, editable and removable. Pixel bytes remain in the material/object-storage abstraction. Commit creates a new rendition; Cancel discards the editing session and never mutates the invitation or original.

Implemented local operations include crop, resize, rotation, flip, brightness/exposure, contrast, saturation/vibrance, grayscale, sepia, blur and sharpen. Brush, eraser, gradient, bucket, clone, heal, dodge/burn and selection operations are represented non-destructively for the workspace and provider renderer. Advanced generative fill and full Photoshop parity are intentionally not claimed.
