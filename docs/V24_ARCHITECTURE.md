# V24 Canva-Quality Invitation Workflow Architecture

## Purpose

V24 completes the interaction roadmap begun by the V24.0 preview. The release does not attempt to turn the invitation platform into a general Canva clone or a Photoshop raster engine. It applies Canva-quality interaction principles to the existing invitation-first product while preserving Khmer typography, event pages, RSVP, guests, check-in, privacy, publishing, review operations, and self-hosted deployment.

## Runtime ownership

- Invitation document and transactions: `EInviteEditorBridge`
- Scene hierarchy and nested groups: V22 scene model
- Commands and discoverability: V23 command registry
- Global keyboard ownership: V23 shortcut manager
- Review comments, approvals, notifications, tasks, and policies: private server-side review models
- Initial canvas experience: `workspace-experience-v24.js`
- V24.1–V24.6 systems: second-stage modules loaded by `performance-loader-v22.js`

No V24 module installs a competing global keyboard owner or a second document-history system.

## V24.1 — Direct manipulation

`direct-manipulation-v24.js` provides local, transactional editing modes:

- Double-click and command-driven inline text editing
- Floating typography controls positioned near the active text object
- Image crop mode with focal-point dragging
- Crop Fit, Fill, Center, Apply, and Cancel controls
- Scoped Enter/Escape handling only while an inline session is active
- Selection-aware cancellation when the active object changes

Edits remain document transactions. Preview-only interaction does not create history entries.

## V24.2 — Unified content

`content-browser-v24.js` combines invitation content discovery into one lazy dialog:

- Images and uploaded materials
- Text, shapes, dividers, and ceremonial decorations
- Invitation page presets
- Structured event sections
- Local and account reusable groups
- Event style kits
- Registered commands
- Recent and favorite content

The browser reuses the asset workflow, page controls, component records, style history, and command registry rather than duplicating those systems.

## V24.3 — Smart layout

`smart-layout-v24.js` supplies invitation-focused composition tools:

- Vertical and horizontal stacks
- Gap and alignment controls
- Tidy grid
- Equal width/height
- Responsive anchor metadata
- Invitation format presets
- Out-of-bounds, overflow, missing-media, and overlap diagnostics

Layout commits are grouped transactions. Responsive metadata is stored in the invitation document and remains compatible with existing renderers that do not yet consume every constraint.

## V24.4 — Event brand and reusable components

`brand-components-v24.js` builds on the style-kit and object models:

- Built-in Khmer, wedding, government, and formal event brands
- Custom brand capture from the current invitation
- English/Khmer font pairings
- Palette and optional logo/monogram capture
- Whole-document or active-page application
- Reusable selected-object components
- Local persistence with account-server synchronization when available

Component insertion generates new object and group identifiers and uses the current canvas transaction model.

## V24.5 — Collaboration maturity

`collaboration-v24.js` extends the private V23.7/V23.8 review system:

- Page and invitation review summaries
- Comment-linked assignments
- Assignee, priority, status, and due date
- Overdue and high-priority views
- Mention assistance based on invitation participants
- CSV review reporting

The backend adds `review_tasks`, keyed by invitation and root comment. Permissions use invitation owner/collaborator access. Tasks are removed when their invitation or root comment is deleted. This is asynchronous review coordination, not unsafe real-time canvas co-editing.

## V24.6 — Quality, accessibility, and export

`export-quality-v24.js` provides:

- Missing media checks
- Image alternative-text checks and direct repair UI
- Empty-text and text-overflow checks
- Estimated text contrast checks
- Link-format checks
- Canvas-boundary checks
- Invitation title/date checks
- Review-policy blocker projection
- Current-page PNG and SVG export
- All-pages PNG ZIP export
- Current/all-page browser print surfaces for PDF workflows
- Private project JSON backup
- Machine-readable quality report

All-pages PNG uses a bounded renderer, data-URL SVG rasterization with a timeout, a 4096-pixel page limit, and an in-browser ZIP writer. Review records and credentials are not inserted into public rendering.

## Loading and performance

The initial route remains the existing compiled editor bundle. These modules load after the editor is interactive:

1. `workspace-experience-v24.js`
2. `direct-manipulation-v24.js`
3. `content-browser-v24.js`
4. `smart-layout-v24.js`
5. `brand-components-v24.js`
6. `collaboration-v24.js`
7. `export-quality-v24.js`

Their stylesheets are injected when each module initializes. The final initial route is 1,418,592 bytes against the 1,420,000-byte budget.

## Privacy and security boundaries

- Review tasks are private invitation collaboration data.
- Project backup is explicitly private and contains the invitation document, not account credentials.
- Public invitations do not expose comments, review tasks, notifications, approvals, or publish policies.
- Imported/reusable components are normalized before insertion.
- Account component APIs remain subject to authenticated access.
- Export does not execute imported code or fetch arbitrary scripts.

## Strategic boundary

V24 deliberately does not add full raster painting, arbitrary editable PDF import, a global marketplace, general documents/whiteboards, or real-time multiplayer editing. These would require substantially different security, conflict-resolution, and rendering architectures.
