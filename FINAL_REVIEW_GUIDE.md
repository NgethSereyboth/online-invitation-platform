# E-invitation-website — Final Review Candidate Guide

This build is the provider-independent review candidate. It is intended to be reviewed locally before choosing deployment, payment, email, object-storage, or AI providers.

## Start the full application

```powershell
cd "<project-folder>"
python -u server.py --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

Keep the PowerShell window open while reviewing.

## Suggested review flow

### 1. Account and dashboard

1. Create an account.
2. Review Light, Dark, and System appearance modes.
3. Create one invitation from each major template family.
4. Search/filter dashboard invitations.
5. Duplicate and archive one test invitation.

### 2. Creation Studio

Review the editor primarily on desktop.

Check:

- Resizable/collapsible creation and inspector panels.
- `Ctrl/Cmd + K` Quick Actions.
- `?` keyboard-shortcut guide.
- `F` focus mode.
- Canvas zoom, pan, rulers, grid, and safe margins.
- Single and multi-object selection.
- Marquee selection, group/ungroup, layers, locking, alignment, distribution, and tidy.
- Right-click context menu.
- Copy/paste and Copy Style/Paste Style.
- Drag uploaded media and library elements onto the canvas.

### 3. Rich design tools

In the Elements workspace, review:

- Search and categories.
- Favorites and Recent items.
- Wedding, botanical, ceremonial, editorial, and shape elements.
- Ready-made text styles.

With an object selected, review:

- Fonts, Khmer font stacks, size, bold, italic, line height, letter spacing, and alignment.
- Text gradients, outlines, shadows, and text transformation.
- Object background color and opacity.
- Blend modes.
- Borders, radii, shadows, and opacity.
- Shape gradients.
- Image crop/focal point, masks, frames, and photo adjustments.

### 4. Motion

Review:

- Object animation preset and duration.
- Animation delay.
- Preview Selected.
- Preview Page.
- Stagger Selected.
- Motion Timeline.
- Section animations.
- Page animations and transitions.

### 5. Page and section builder

Review:

- Main hero canvas.
- Visual page templates.
- Page thumbnails and drag ordering.
- Cross-page copy/paste.
- Master backgrounds.
- Page-specific backgrounds and transitions.
- Section ordering.
- Structured section layouts and appearance.
- Reusable pages, content blocks, and design groups.

### 6. Materials

Review:

- Image, audio, and video uploads.
- Search, filters, folders, tags, favorites, rename, and delete.
- Reuse media across projects.
- Gallery ordering, captions, and alt text.
- Featured video and invitation music.

### 7. Invitation-specific workflow

Review:

- Khmer + English content.
- Khmer lunar dates.
- Countdown.
- Schedule.
- Multiple venues and map links.
- Contact buttons.
- Optional RSVP.
- Custom RSVP questions.
- Guest wishes.
- Design Check score and fix actions.

### 8. Publishing and guest experience

1. Publish a snapshot.
2. Open `/i/{slug}` in another browser tab.
3. Verify that later draft edits do not alter the published version until republished.
4. Review Tap to Open, music, animations, pages, gallery, event sections, language switcher, Add to Calendar, Share, RSVP, and Wishes.
5. Test password-protected mode.
6. Restore an earlier published version as a draft.

### 9. Guest operations

Review:

- Guest CSV import/export.
- Personalized links.
- QR codes.
- RSVP filtering and owner edits.
- Check-in and undo check-in.
- Analytics.

### 10. Professional workflows

Review:

- Save complete design as a template.
- Template Studio preview, duplication, editing, versioning, favorites, and marketplace visibility.
- Designer Workspace.
- Account-level materials and reusable components.

## Automated checks

```powershell
python tests/smoke_test.py
python tests/plan_limit_test.py
python tests/final_features_test.py
```

Expected results:

```text
SMOKE_TEST_PASSED
PLAN_LIMIT_TEST_PASSED
FINAL_FEATURES_TEST_PASSED
```

## Intentionally not considered complete until providers are chosen

The review candidate deliberately does not pretend the following are fully production-complete without real provider accounts and deployment decisions:

- Automated subscription/payment processing.
- Production payment webhooks, invoicing, refunds, and creator payouts.
- A live PostgreSQL runtime migration and production database topology.
- Production Cloudflare R2/S3 credentials and CDN/domain setup.
- Production SMTP credentials and deliverability configuration.
- Public hosting, HTTPS, monitoring, alerting, and operational backups.
- AI writing, translation, image generation, or design assistance provider integration.
- Large-scale real-time multi-user collaborative editing.

Those items should be selected only after the local product review confirms the desired workflow and visual direction.

## Final professional-editor review additions

Before approving this build, also test the following interaction pass:

### Photoshop-style interaction

- Hold `Alt` and drag an object; confirm a duplicate is created and moved.
- Hold `Shift` while dragging; confirm movement is constrained to one axis.
- Hold `Shift` while resizing; confirm the aspect ratio stays fixed.
- Hold `Shift` while rotating; confirm rotation snaps.
- Test `V`, `T`, `H`, `R`, `O`, and `L` tool shortcuts.
- Test `Ctrl/Cmd + J`, `Ctrl/Cmd + A`, grouping/ungrouping, layer order shortcuts, zoom, and fit.
- Double-click a text object and edit directly on the canvas.
- Use precise X/Y/W/H/rotation controls, quick placement, vertical text alignment, and text-box padding.

### Layers and structure

- Search layers by name.
- Rename a layer by double-clicking its name.
- Hide/show a layer and confirm it is excluded from the published artistic canvas when hidden.
- Lock/unlock objects.
- Verify selection, grouping, ordering, alignment, and smart-layout tools.

### Smart tools and photo editing

- Generate invitation wording in several tones.
- Generate formal Khmer wording.
- Try palette suggestion and Auto Polish Hero.
- Upload a photo and test Auto bg cut on a simple background.
- Restore the original image.
- Test Magic Enhance, Portrait Soften, hue, horizontal/vertical flip, and Reset edits.
- Replace the selected image from the Material Library.

### Background and atmosphere

- Test solid, gradient, and textured invitation backgrounds.
- Confirm the artboard stays readable when the application switches between Light and Dark mode.
- Confirm background effects survive publish and reopen correctly in the guest invitation.

### Material Library

- Select multiple files and upload them in one action.
- Drag files onto the upload area.
- Paste an image file from the clipboard while the Material Library is open.
- Search, tag, favorite, move into folders, and reuse materials across invitations.
