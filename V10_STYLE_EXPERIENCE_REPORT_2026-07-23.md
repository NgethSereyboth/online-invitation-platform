# E-invitation Platform — Style Experience V10

## Implemented

- Data-driven invitation schema version 10 with backward migration from V9 documents.
- Global Style Kits: Royal Khmer Gold, Modern Cambodian Luxury, and Botanical Blush.
- Style Kit preview/apply, normal editor undo support, later object customization, template-default restoration, persistence in draft and publication documents, and desktop-layout selection.
- Six premium opening scenes: Soft Monogram, Royal Khmer Gate, Silk Curtain, Floral Reveal, Cinematic Photo, and Minimal Editorial.
- Guest-interaction music start remains intact for uploaded audio and YouTube; reduced-motion mode disables nonessential opening and section animation.
- Full Storyboard view built on the existing `sectionOrder`, including page thumbnails, enabled/disabled state, content warnings, edit actions, drag/reorder controls, RSVP optional-state messaging, device selection, and published-flow playback.
- Desktop guest layouts: Ambient Frame, Editorial Split, and Full Width, with mobile collapse and form width protection.
- Dynamic 1200×630 server social-card SVG metadata plus client previews/downloads for Open Graph, square, and story formats.
- Share tools for clean public link, prepared message, Telegram, WhatsApp, Facebook, social card, and branded QR/share graphic. Personalized guest/access credentials are stripped.
- Dashboard first-invitation empty state with templates, checklist, materials link, and example guest preview.
- Editor Focus Mode, remembered browser state, floating Style & Experience launcher, compact quick toolbar, and performance checks.
- Accessibility cleanup for icon labels, drawer state helpers, focus return, Escape behavior, missing image alt text, and reduced motion.
- Public performance improvements: below-fold image lazy loading, async image decoding, section `content-visibility`, and opening-critical content kept visible.

## Invitation document changes

V10 adds these optional top-level fields. Existing V9 documents are migrated at runtime without deleting or rewriting existing content:

- `schemaVersion: 10`
- `styleKit: { id, overrides, templateDefaults }`
- `openingScene: { id, monogram, subtitle, backgroundColor, backgroundImage, decorative, enterText, enterTextKm, duration, textVariant, skipAllowed }`
- `desktopGuestLayout: "ambient-frame" | "editorial-split" | "full-width"`
- `socialCard: { photo, alignment, textVariant, language, monogram }`
- `experience: { focusMode }`

The existing `sectionOrder` remains the only source of truth for public flow ordering. RSVP remains controlled by `settings.rsvpEnabled`.

## Known limitations

- The server social metadata image is generated as SVG. The editor downloads PNG previews from canvas, but the server does not yet persist a pre-rendered PNG/AVIF derivative.
- Social-card photo selection is stored and exposed in the editor, but the lightweight server SVG currently uses colors/text/monogram rather than rasterizing remote photos.
- The branded QR download is a branded share graphic with the clean link text; it does not add a new QR-code dependency to the no-build baseline.
- Full published-flow playback requires a connected backend and at least one published snapshot.
- Image `srcset`, AVIF conversion, blur placeholders, and server-side image resizing require an image-processing provider and are therefore represented by metadata-ready/lazy-loading behavior rather than production transcoding.
- Advanced inspector groups from older editor layers were not structurally rewritten; V10 adds progressive-disclosure entry points without risking V9 control regressions.
