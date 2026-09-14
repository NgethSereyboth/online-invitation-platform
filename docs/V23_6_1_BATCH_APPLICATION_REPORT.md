# V23.6.1 Batch Application Report

V23.6.1 adds previewable, transaction-safe style application at two scopes:

1. **Selected images** — every selected image on the active canvas.
2. **Current page** — every image object on the active hero canvas or design page.

Preview updates DOM projections only. The document and history remain unchanged until Apply. Apply uses one named `EInviteEditorBridge.transact` operation regardless of target count, so one Undo restores the complete batch and one Redo reapplies it.

Selection changes cancel an active preview to prevent a temporary projection from remaining attached to stale targets. Non-image objects are ignored safely. Empty scopes are disabled or return accessible feedback rather than creating empty history entries.
