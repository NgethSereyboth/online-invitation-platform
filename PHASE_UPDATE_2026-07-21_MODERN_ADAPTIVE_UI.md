# Modern Adaptive UI & Creative Workspace Phase

This phase focuses on visual polish, interaction quality, adaptive appearance, and a more professional creation workflow.

## Added

- Light, Dark, and System appearance modes across authenticated/application pages.
- Appearance preference persists in local storage and reacts to system-theme changes.
- Appearance selector in application headers plus Alt+T shortcut.
- Dark-mode styling for editor panels, dialogs, cards, forms, dashboards, management screens, Template Studio, Material Library, and account pages.
- Shared modern design tokens for surfaces, text, borders, shadows, motion, and accent treatment.
- Smooth page entrance/exit transitions for internal navigation.
- Spring-like hover and press feedback for buttons and interactive cards.
- Pointer ripple feedback on buttons.
- Spotlight hover treatment on cards, templates, quick inserts, blocks, and navigation tiles.
- Adaptive tooltips for compact editor controls.
- Toast notification system used by appearance changes and available to future features as `window.einviteToast`.
- Current-page navigation indicator in application headers.

## Creation Studio improvements

- Resizable left Creation panel and right Inspector panel on desktop.
- Panel sizes persist between sessions.
- Creation and Inspector panels can be collapsed independently.
- Alt+1 through Alt+5 switch the five creation areas.
- Alt+I toggles the Inspector.
- Alt+[ toggles the Creation panel.
- Existing Focus Mode continues to provide a full-canvas editing environment.
- Canvas workspace, controls, panels, tabs, command palette, design check, page navigator, element library and selection toolbar now adapt to Light/Dark appearance.
- Improved canvas depth, hover lift and modern dotted workspace treatment.

## Accessibility and motion

- Focus-visible rings are consistent across buttons, links and form controls.
- `prefers-reduced-motion` is respected and disables decorative motion where appropriate.
- Theme selection exposes accessible labels and menu semantics.

## Architecture

The visual system is isolated in:

- `theme-init.js` — applies appearance before first paint to reduce theme flash.
- `modern-ui.css` — adaptive tokens, Dark/Light styling, micro-interactions and editor layout polish.
- `modern-ui.js` — appearance controls, panel resizing, ripple/spotlight effects, tooltips, toast system and navigation transitions.

The existing invitation data model, editor object model, backend, publishing, RSVP, guest tools, templates and storage remain unchanged.
