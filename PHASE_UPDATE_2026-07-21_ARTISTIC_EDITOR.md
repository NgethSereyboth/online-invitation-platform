# Development Phase Update — Artistic Published Canvas and Advanced Editor Controls

This phase moves the prototype closer to a Canva-style invitation editor while preserving the current dependency-free HTML/CSS/JavaScript + Python/SQLite architecture.

## Added in this phase

### Published artistic hero uses real canvas objects

Canvas objects can now be included directly in the published invitation's artistic hero area.

Supported published object properties include:

- Position.
- Width and height.
- Layer order.
- Rotation.
- Text font and color.
- Per-object animation and duration.
- Image fit and focal point.
- Bilingual synchronization for the main names, invitation message, and event-detail objects.

Each object has a `Show in published artistic hero` control so decorative or working objects can be excluded when required.

### Separate hero and gallery visibility

Image objects now independently control whether they appear:

- In the free-form artistic hero.
- In the structured photo gallery.

This prevents the canvas and gallery from being forced to use exactly the same media set.

### Multi-selection

Users can now select more than one object using Shift/Ctrl/Command-click.

Selected objects can be moved together and are visibly marked on the canvas and in the Layers panel.

### Group and ungroup

Multiple selected objects can be grouped. Grouped objects move together and preserve a group identifier in the invitation document.

Groups can later be ungrouped without deleting or flattening the individual objects.

### Alignment and distribution

Multi-selected objects can now be aligned by:

- Left edge.
- Horizontal center.
- Right edge.
- Top edge.
- Vertical center.
- Bottom edge.

Three or more objects can also be distributed horizontally or vertically.

### Interactive image crop preview

The image property panel now contains an interactive crop preview.

Users can click directly on the preview to choose the image focal point, in addition to using the horizontal and vertical sliders.

The selected focus is used on the canvas, artistic published hero, and gallery.

### Accessible gallery descriptions

Each gallery photo now has a separate editable image-description field in addition to its visible caption.

The description is published as the image `alt` text for accessibility.

### Section-level animation controls

The editor now provides individual animation controls for:

- Artistic hero.
- Gallery.
- Countdown.
- Schedule.
- Custom blocks.
- Venue.
- Contact section.
- RSVP.

Each section can select an animation preset and duration. The `None` animation option was also corrected so it truly disables animation on published content.

### Visual section block library

The custom-section system now has visual quick-add blocks for:

- Our Story.
- Dress Code.
- Important Note.
- Quote.
- Accommodation.
- Gift Note.

All remain bilingual and editable after insertion.

### Stronger backend document validation

The Python backend now validates additional editor data before saving or publishing:

- Canvas object types.
- Position and dimension values.
- Rotation range.
- Image focal-point range.
- Object animation names and durations.
- Group identifier length.
- Section animation names and durations.

Invalid CSS-like position values and unsupported animation names are rejected.

## Verification performed

- `node --check app.js`
- `node --check dashboard.js`
- `node --check guests.js`
- Extracted and syntax-checked the inline JavaScript in `public.html`
- `python -m py_compile server.py`
- `git diff --check` for changed application files
- Server health check
- Fresh account registration
- Valid invitation creation with section-animation and artistic-object metadata
- Publish/public API round trip for `showInHero`, `showInGallery`, and section-animation settings
- Backend rejection test for unsupported section animations
- Backend rejection test for invalid object position/style values
- Public route verification that the artistic-hero renderer is included

## Recommended next phase

1. Add marquee/drag-box selection and keyboard object deletion/duplication.
2. Add true rotate handles and on-canvas group bounding boxes.
3. Add object opacity, border radius, shadow, and text size/alignment controls.
4. Add section templates/layout variants beyond custom information blocks.
5. Add server-generated image thumbnails and derivative metadata.
6. Add PostgreSQL and object-storage adapters behind the existing repository/storage boundaries.
7. Add deployment configuration for a real hosted test environment.
