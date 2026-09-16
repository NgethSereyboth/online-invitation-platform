# V23.6 Migration and Rollback Report

## Migration

No database, server API, invitation schema, page schema, image-object schema, or publishing migration is required.

On first use:

- the second-stage loader initializes `photo-style-library-v23.js` after the V23.5 photo workflow;
- built-in styles are generated from the existing V23.5 presets;
- the custom library reads `einvite-photo-styles-v23` when available;
- missing or invalid storage data falls back safely to an empty custom library;
- existing images continue to use their current normalized adjustment fields.

## Compatibility

- Existing V23.5 copied-look behavior remains available.
- Existing invitations and image objects require no rewrite.
- Existing asset, frame, crop, mask, style-kit, checkpoint, page, publishing, RSVP, guest, privacy, and analytics workflows are unchanged.
- The old advanced photo controls remain available for compatibility.

## Rollback

A code rollback can remove `photo-style-library-v23.js` from `performance-loader-v22.js` and remove its contextual/status/photo-editor entry points. Saved invitation documents remain valid because applied styles are ordinary existing image-adjustment fields. The browser-profile custom library may remain in localStorage without affecting older releases.
