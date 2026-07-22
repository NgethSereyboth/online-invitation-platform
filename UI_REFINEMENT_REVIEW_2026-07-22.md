# UI Refinement Review — 2026-07-22

This build addresses the review screenshots and focuses on responsive, device-aware layout behavior instead of adding new product scope.

## Dashboard
- Reworked the signed-in dashboard into a project-first home screen inspired by modern creative tools.
- Added responsive project navigation, large search, quick create actions, and recent invitation cards.
- Project cards now open the editor only when selected; the editor is not embedded on the home page.
- Improved desktop and mobile dashboard layouts.
- Improved the signed-out login width and desktop/mobile responsiveness.

## Materials
- Fixed the management-page layout bug caused by missing page-mode attributes.
- Added a compact, responsive filter toolbar.
- Collapsed the large upload form behind an Upload files control.
- Reduced card and thumbnail size for a cleaner file-browser-like library.
- Improved cookie-session compatibility by retrying without stale local bearer tokens.

## Editor
- Added explicit content mode and design mode.
- Event and Blocks no longer display ghost canvas controls, selection bars, or the inspector.
- Pages, Uploads, Elements, and Text remain design modes with the canvas visible.
- Added a dedicated Text destination with a Canva-like text workflow.
- Added default text styles, Khmer title preset, font combinations, font search, and Magic Writing entry point.
- Compact element and ornament library cards and category chips.
- Improved responsive editor behavior for desktop, laptop, tablet, and mobile widths.
- Compact-screen inspector is now a floating panel that opens when an object is selected.

## Navigation
- Reduced the workspace-launcher size and spacing.
- Added device-aware dashboard navigation behavior.

## Validation
The deterministic project review suite passes after these changes.
