# V23.6 Reusable Photo-Style Architecture

## Purpose

V23.6 extends the V23.5 non-destructive photo workflow into a reusable style system. It does not create a second image renderer, duplicate the document model, or add destructive raster processing. A photo style is a sanitized data-only package containing supported visual adjustment fields. Existing image objects remain authoritative, and the shared editor/public rendering path continues to project the resulting fields.

## Runtime placement

`photo-style-library-v23.js` is loaded by `performance-loader-v22.js` immediately after `photo-workflow-v23.js`. The stylesheet is injected only when the module initializes. The module therefore adds no new blocking script or stylesheet tag to the initial editor HTML.

## Authoritative boundaries

1. **Photo-field authority** — `EInvitePhotoWorkflow.normalizeLook`, `applyLookToObject`, and `projectLookToNode` own normalization, mutation, and preview projection.
2. **Document authority** — `EInviteEditorBridge` continues to own the active document, selected IDs, active canvas, transactions, Undo, and Redo.
3. **Command authority** — `EInviteCommandRegistry` owns library opening, saving, and page-scope entry. No global key listener is added.
4. **Rendering authority** — the existing image object fields and shared renderer remain the only saved/published visual representation.
5. **Storage authority** — custom style definitions are browser-profile preferences under `einvite-photo-styles-v23`; they are not invitation-document data.

## Style model

Each style contains:

- bounded ID and display name;
- optional description, category, and tags;
- built-in/custom marker;
- creation/update timestamps;
- one normalized V23.5 photo look.

The style intentionally excludes media URL, asset ID, object ID, size, z-order, crop position, fit, mask/frame geometry, flips, perspective, and warp composition. Applying a style changes treatment rather than replacing or repositioning media.

## Library boundaries

- Maximum custom styles: 36.
- Maximum stored library payload: 900,000 bytes.
- Maximum imported file: 1,000,000 bytes.
- Imported records are normalized, sanitized, capped, assigned new IDs, and given duplicate-safe names.
- Storage failure falls back to an in-memory session library and produces an accessible warning.

## Preview and batch transaction lifecycle

1. Resolve eligible image IDs from the selected-image scope or active-page scope.
2. Capture the current DOM projection for every target.
3. Project the candidate look directly to target nodes without changing the document.
4. Cancel restores the captured projections.
5. Apply cancels preview state, enters one `EInviteEditorBridge.transact` call, and applies the normalized look to every target object.
6. One Undo restores the complete batch; one Redo reapplies it.

## Context integration

- A single selected image exposes Edit photo, Photo styles, Replace, Frame, Position, Duplicate, and Delete.
- An all-image multi-selection exposes Photo styles as the primary batch action.
- The status bar and Photo Editor provide additional visible entry points.
- Quick Actions discovers the same registered commands and shortcut metadata.

## Lifecycle and accessibility

The library uses a native dialog, visible Preview/Apply/Cancel controls, search, scope selection, focus restoration, mobile single-column containment, operation feedback, and lifecycle cleanup. Repeated open/close cycles reuse one dialog and one command registration.
