# Development Phase Update — 2026-07-21

This phase continues the imported project baseline without replacing its architecture.

## Added in this phase

- Khmer/English invitation content fields for couple names and the main invitation message.
- Guest language modes: English only, Khmer only, or switchable Khmer + English.
- Guest-facing EN / ខ្មែរ language switcher.
- Host contact section with validated phone and Telegram actions.
- Gallery manager with persistent ordering, captions, selection, and removal controls.
- Gallery captions and ordering in both local preview and published invitations.
- Layers panel for canvas objects.
- Object locking.
- Bring-forward / send-backward layer controls.
- Undo and redo with keyboard shortcuts.
- Improved drag snapping and movement boundaries.
- Direct text editing from the selected-object properties panel.
- Cross-device server material library listing and server material deletion.
- Client-side image downscaling/compression before storage when useful.
- Server-side file signature checks for JPEG, PNG, WebP, GIF, MP3, and M4A uploads.
- Basic rate limiting for registration, login, uploads, and public RSVP submissions.
- Invitation document size/object-count validation before create, save, and publish.
- Template choice when creating a new invitation from the dashboard.

## Verification performed

- `python -m py_compile server.py`
- `node --check app.js`
- `node --check dashboard.js`
- `node --check guests.js`
- `git diff --check` on changed application files
- API integration test: registration → invitation creation → publish → public fetch → RSVP persistence
- Material API integration test: upload → list → delete
- Upload content validation test: valid PNG accepted, fake PNG rejected
- Browser-runtime component tests using a headless browser with local persistence/API stubs
- Guest rendering test for bilingual switching, gallery captions, contacts, and personalized guest display

## Recommended next phase

1. Add richer fully designed invitation templates rather than theme-only starter variations.
2. Add bilingual schedule, venue, countdown, and custom section content.
3. Add richer canvas alignment guides, multi-select, grouping, rotation, and object-specific image crop controls.
4. Add a reusable section/block library so users can insert new invitation sections visually.
5. Add image thumbnails/derivatives on the backend for production-scale media delivery.
6. Prepare PostgreSQL and R2/S3 deployment adapters while keeping the local SQLite mode for development.
