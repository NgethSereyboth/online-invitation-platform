# Phase Update — Professional Template Workflow

This phase turns the growing page-builder system into a reusable template workflow.

## Added

- Complete invitation templates stored per account in SQLite.
- `GET /api/templates`, `GET /api/templates/{id}`, `POST /api/templates`, and `DELETE /api/templates/{id}`.
- Save the entire invitation design as a reusable template from the editor.
- Visual template browser in the dashboard with category filters and search.
- Reuse custom account templates when creating a new invitation.
- Built-in multi-page template blueprints for Royal Rose, Khmer Gold, Emerald Garden, Midnight Luxury, Celebration Pop, and Ivory Executive.
- Built-in templates now carry page structure, section order, palette, section styling, layout and animation rather than acting only as theme colors.
- Material-library picker for master-page, visual-page, and section background images.
- Local browser fallback for full reusable templates when the backend is unavailable.

## Architecture

The invitation document remains the single reusable source of truth. Creating from a template clones the full design document and changes the new invitation's primary title/event metadata without sharing live state with the source template.
