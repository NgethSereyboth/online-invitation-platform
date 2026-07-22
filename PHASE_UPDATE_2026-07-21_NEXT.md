# Development Phase Update — Premium Templates and Richer Invitation Content

This phase continues the current portable HTML/CSS/JavaScript + Python/SQLite architecture.

## Added in this phase

### Four genuinely different guest invitation templates

The existing theme choices now change the actual guest-page composition rather than only swapping colors:

- Royal Rose — romantic editorial arches, soft floral background treatment, curved photography.
- Khmer Gold — ceremonial framed composition, geometric gold details, formal card styling.
- Emerald Garden — airy botanical composition, rounded glass-like cards, organic photo presentation.
- Midnight Luxury — cinematic dark presentation, luminous typography, glass panels, star-like background details.

The dashboard creation dialog now shows visual template-choice cards and descriptions.

### Expanded Khmer/English invitation content

The following content now has separate English and Khmer values and switches with the guest language control:

- Main venue name.
- Countdown heading.
- Schedule item titles.
- Additional venue names and addresses.
- Custom section headings and body text.

Existing bilingual names and invitation wording continue to work.

### Reusable custom section/block library

The editor can now add reusable information blocks:

- Our Story.
- Dress Code.
- Important Note.
- Custom Section.

Each block supports:

- English heading.
- Khmer heading.
- English body text.
- Khmer body text.
- Enable/disable.
- Reordering.
- Removal.

The entire custom-block area can also be positioned through the existing section-order system using the `custom` section key.

### Improved schedule and venue presentation

Published invitations now render schedule items and multiple venues as structured, template-aware components rather than plain paragraphs.

### Richer object controls

Selected canvas objects now support:

- Rotation from -180° to 180°.
- Persisted rotation state.
- Image fit: crop-to-fill or show-full-image.
- Horizontal image focal-point control.
- Vertical image focal-point control.
- Persisted image crop/focal settings.
- Gallery rendering that respects image fit and focal point.

### Alignment guides

Dragging objects now shows temporary visual alignment guides when objects snap to common positions such as edges, quarter positions, and center lines.

### Stronger backend document validation

The Python backend now validates:

- Supported section-order values.
- Duplicate section keys.
- Maximum schedule size.
- Maximum venue count.
- Maximum custom-section count.
- Custom-section text length.

Invalid section identifiers are rejected before creating or publishing an invitation.

## Verification performed

- `node --check app.js`
- `node --check dashboard.js`
- `node --check guests.js`
- Extracted and syntax-checked the inline JavaScript in `public.html`
- `python -m py_compile server.py`
- `git diff --check` on changed application files
- Server health check
- Fresh account registration
- Invitation creation with bilingual venue, bilingual schedule, bilingual countdown, and custom blocks
- Publish snapshot creation
- Public invitation API retrieval
- Confirmation that Khmer custom-block and schedule data survive publishing
- Backend rejection test for unsupported section-order values
- Public route HTTP response test

## Recommended next development phase

1. Make the published invitation use selected canvas/artistic objects in one or more dedicated free-form hero sections.
2. Add multi-select, group/ungroup, and stronger alignment/distribution controls.
3. Add image crop previews with an interactive crop frame instead of only focal-point sliders.
4. Add editable gallery alt text and per-photo template treatment.
5. Add section-level animation settings and a visual section library.
6. Add server-side image derivative generation and thumbnail metadata.
7. Prepare PostgreSQL and object-storage adapters while preserving the current SQLite/local-storage development mode.
