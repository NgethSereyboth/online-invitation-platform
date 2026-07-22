# Development Phase Update — Advanced Editor Controls

This phase extends the invitation canvas and guest renderer toward a more capable visual-design workflow.

## Added in this phase

### Drag-box multi-selection
- Drag across empty canvas space to select multiple objects.
- Shift/Ctrl/Command can add marquee-selected objects to the existing selection.
- Objects intersecting the selection rectangle are highlighted before selection completes.

### Selection and group bounding boxes
- Multi-selected objects show a shared bounding outline and selection count.
- Grouped objects show a shared `Group` bounding label.
- Clicking a grouped object selects the complete group.
- Shift/Ctrl-click toggles the complete group consistently.

### Real rotation handle
- Selected objects now show a dedicated rotation handle above the object.
- Drag the handle around the object to rotate it.
- Hold Shift while rotating to snap rotation changes to 15-degree steps.
- Group/multi-selection rotation applies the same rotation delta to selected objects.

### Keyboard editing shortcuts
- `Ctrl/Cmd + D`: duplicate the current selection.
- `Delete` / `Backspace`: delete removable selected objects.
- Arrow keys: nudge selected objects.
- `Shift + Arrow`: larger nudge.
- `Escape`: clear selection.
- Existing undo/redo shortcuts remain available.

### Multi-object duplication
- Multiple selected objects can be duplicated together.
- Duplicated groups receive a new independent group ID.
- Image gallery membership is retained for duplicated image objects.

### Typography controls
Text objects now support:
- Font size.
- Left, center, and right alignment.
- Existing font family and text color controls can apply across a multi-selection of text objects.

### Object appearance controls
Canvas objects now support:
- Opacity.
- Border width.
- Border color.
- Corner radius.
- Shadow blur.
- Shadow color.

These properties are stored in draft/publish data and rendered on the public invitation hero.

### Richer section layout templates
Four major invitation areas now have layout choices:

- Countdown: number cards, minimal, compact pills.
- Schedule: elegant timeline, event cards, minimal list.
- Venue: venue cards, stacked details, split layout.
- Custom blocks: elegant cards, editorial, alternating.

Layout selections are saved into the invitation document and used by both editor-generated guest previews and server-published invitation pages.

### Backend validation and robustness
- New object appearance values are validated before save/publish.
- Section layout names are validated against supported choices.
- Invalid opacity, dimensions, appearance values, and section layouts are rejected.
- PUT and DELETE API requests now return clean 400 responses for validation errors instead of terminating the HTTP request unexpectedly.

## Verification completed

- `node --check app.js`: passed.
- `node --check` on the inline `public.html` script: passed.
- `python -m py_compile server.py`: passed.
- `git diff --check` for changed application files: passed.
- Backend register → create → publish → public-read round trip with new layout/style fields: passed.
- Invalid opacity validation: returned HTTP 400 as expected.
- Invalid section-layout validation: returned HTTP 400 as expected.

## Recommended next development phase

1. Add copy/paste between invitations and object clipboard shortcuts.
2. Add object snapping to other objects, not only canvas guide positions.
3. Add a true page/section design mode so more than the opening hero can be visually composed.
4. Add richer text styling: bold, italic, letter spacing, line height, and Khmer font packs.
5. Add shape/decorative element insertion and an element library.
6. Add background controls per artistic section.
7. Add image filters and basic brightness/contrast controls.
8. Improve mobile editor panels while keeping desktop as the main authoring experience.
