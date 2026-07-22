# Phase Update — Page Navigation, Clipboard, Master Backgrounds & Account Materials

This phase adds:

- visual page thumbnails and a horizontal page navigator
- drag-and-drop reordering for visual pages
- cross-page object copy/paste, including Ctrl/Cmd+C and Ctrl/Cmd+V
- global master page backgrounds with per-page inheritance
- per-page transition styles and durations
- four additional prebuilt page layouts: Photo Collage, Split Feature, Ceremony Page, Thank You Page
- a searchable/filterable material library
- an authenticated account-level `/api/assets` endpoint so stored materials can be reused across invitations
- support for selecting stored audio as invitation music
- backend validation for master page styles and page transitions

The account material library is still backed by the local development server's SQLite metadata and `data/uploads/`. Production deployment should later move file bytes to R2/S3 and retain the same API-level ownership model.
