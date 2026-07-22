# Development Phase — Visual Page & Section Builder

This phase introduces independently editable free-form visual pages in addition to the main artistic hero.

## Added
- Visual page library with Title, Photo Feature, Quote, Story, and Details page presets.
- Each visual page has its own object canvas, background color/image, overlay, entrance animation, and visibility.
- Main hero and visual pages can be switched in the same editor canvas.
- Visual pages can be duplicated, removed, moved within the invitation sequence, and saved as reusable local page templates.
- Dynamic `page:<id>` entries are supported inside `sectionOrder`, so visual pages can be interleaved with Gallery, Countdown, Schedule, Venue, Contact, and RSVP sections.
- Published preview and server public invitation render all visual pages with their free-form text, image, shape, decoration, mask, frame, animation, rotation, and styling data.
- Backend validation now validates visual page IDs, backgrounds, background URLs, overlays, animation settings, page objects, and dynamic section order tokens.

## Architecture
The invitation now supports two visual-canvas levels:
1. Main artistic hero (`document.objects`)
2. Independent visual pages (`document.designPages[].objects`)

This keeps existing invitations compatible while providing a path toward a full page-based invitation builder.

## Additional section reuse tools
- Custom information blocks can now be duplicated.
- Custom information blocks can be saved as reusable local content-block templates and inserted into future invitations.
- Hero-only gallery/public-hero controls are hidden while editing an independent visual page to reduce editing confusion.
