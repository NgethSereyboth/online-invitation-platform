# Improvement research — existing functions

**Date:** 2026-11-01
**Scope:** public invitation/guest page, RSVP and gallery, editor, export/templates,
check-in service worker, Khmer typography
**Status:** research only — no application source changed

This note records current, source-backed opportunities for improving functions the
platform already has. It is deliberately narrower than a redesign: each item names
the existing surface, the evidence, the smallest safe experiment, and the trade-off.

## Method

Reviewed the current source first, then compared it with authoritative guidance from
web.dev/Chrome for Developers, the W3C/WAI WCAG 2.2 material, the W3C Khmer script
resources, and Noto/MDN. The W3C Khmer documents are Group Note Drafts; line-height
and specific test strings below are practical recommendations, not W3C-published
numbers.

## Findings, ordered by value and risk

| ID | Existing surface | Finding and first action | Evidence | Risk / trade-off |
|---|---|---|---|---|
| IMP-1 | Public invitation hero / LCP | The shared renderer adds `loading="lazy"` to **every** image object (`src/js/renderer-core.js`, image branch; used by `public-page.js`). If the hero or first-viewport image is rendered through that path, the browser defers the LCP fetch until layout. Measure the actual LCP element and make the first-viewport image eager with `fetchpriority="high"`; do **not** combine lazy + high. | web.dev: [Optimize LCP](https://web.dev/articles/optimize-lcp), [Browser-level lazy loading](https://web.dev/articles/browser-level-image-lazy-loading), [Fetch Priority](https://web.dev/articles/fetch-priority) | Easy to test; must verify the LCP element rather than assuming, and limit `fetchpriority="high"` to one or two resources. |
| IMP-2 | Editor / INP | The editor route remains the large bundle (`NEXT-WORK` #9, 1.52 MB before images). Measure field INP and use the Long Animation Frames API before changing code; the likely wins are splitting editor-only modules, deferring non-visual work after a drag/resize, and yielding long loops. OffscreenCanvas is a possible progressive enhancement, not a first move. | web.dev: [Optimize INP](https://web.dev/articles/optimize-inp), [Optimize long tasks](https://web.dev/articles/optimize-long-tasks), [Long Animation Frames](https://developer.chrome.com/docs/web-platform/long-animation-frames), [OffscreenCanvas](https://web.dev/articles/offscreen-canvas) | Larger change; measure interaction-level INP, because Lighthouse/TBT cannot identify the slow interaction. |
| IMP-3 | Editor chrome and gallery controls / WCAG 2.5.8 | The live sweep found many sub-24 px controls; some are skip links or essential/hidden controls, but the dense editor chrome needs a deliberate audit. Use invisible hit-area padding to reach **24×24 CSS px** for non-canvas controls; the canvas itself may invoke the Essential exception, but toolbar buttons, menus and gallery actions do not. | W3C WAI: [Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html); existing `tools/a11y-target-size.py` | Inflating hit areas can overlap handles near small objects; test z-order and pointer hit-testing. Do not simply enlarge every visual icon. |
| IMP-4 | Editor / WCAG 2.5.7 | Dragging must be achievable with a **single pointer without dragging**, not only with a keyboard. Provide click-only equivalents for move/resize/rotate/marquee: numeric X/Y/W/H/rotation fields, nudge buttons, or click-first/click-second placement. Announce the changed value through a polite live region. | W3C WAI: [Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html); [APG dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) | Numeric fields already fit the existing inspector model; a second click-to-place mode adds state and needs Esc/announcement design. |
| IMP-5 | Khmer display and body text | The Khmer family and `letter-spacing: normal` are already correct (`src/css/tokens.css`). The public guest bundle sets `.guest-hero h1` to `line-height:1.08`, and the rendered hero title uses `.hero-object-title` at `1.05`; both are tight for stacked Khmer marks. Set a Khmer-specific display/body line-height (roughly 1.6–1.75 for body; at least the equivalent of 1.35+ for display), avoid fixed heights/`overflow:hidden` on Khmer text, and never apply tracking or `break-all`. Test the W3C stress strings in Chrome, Safari and Firefox. | W3C: [Khmer script resources](https://www.w3.org/TR/khmr-lreq/), [Khmer gap analysis](https://www.w3.org/TR/khmr-gap/), [language declarations](https://www.w3.org/International/questions/qa-html-language-declarations); [Noto use](https://notofonts.github.io/noto-docs/website/use/); [MDN line-height](https://developer.mozilla.org/en-US/docs/Web/CSS/line-height) | A slightly taller hero is a visual change; verify against the existing six-width matrix and do not add a fixed height. |
| IMP-6 | Gallery / public images | Responsive `srcset`/`sizes` and WebP are already shipped. Evaluate AVIF through `<picture>` only after measuring hero/gallery bytes; keep WebP/JPEG fallbacks and make `sizes` match the rendered slot. Do not replace the current pipeline blindly. | web.dev: [Serve responsive images](https://web.dev/articles/serve-responsive-images); Chrome: [Improve image delivery](https://developer.chrome.com/docs/performance/insights/image-delivery) | New server variants increase storage/processing; the measured load delay may be more important than format bytes. |
| IMP-7 | RSVP/gallery forms | The RSVP markup has visible labels and native `required`/`maxlength`; the gallery unlock has a label and error paragraph. For WCAG 2.2, add a text error summary, `aria-invalid`/`aria-describedby`, and a polite status/error live region, then move focus to the summary or first invalid field. Do not add `autocomplete` to a guest-name field without deciding whether the submitter is the guest or a host acting for someone else. | W3C: [Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html), [Identify Input Purpose](https://www.w3.org/WAI/WCAG22/Understanding/identify-input-purpose.html); [APG names/descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) | Native validation still works; custom validation adds maintenance and must preserve entered values. |
| IMP-8 | Check-in service worker | The service worker intentionally covers only check-in and uses network-first for its unversioned assets. That is a sound narrow scope; do not extend cache-first behaviour to the editor or RSVP APIs. If a PWA/offline mode is added, cache only content-hashed static assets and keep draft/RSVP writes network-first with explicit conflict handling. | Chrome: [Service worker deployment](https://developer.chrome.com/docs/workbox/service-worker-deployment); current `src/js/service-worker.js` | Expanding offline caching can serve stale editor code or hide failed writes; no change is recommended now. |

## Recommended sequence

1. **Measure first:** capture LCP subparts and interaction INP on the deployed origin
   (or a production-mode local server) before changing code. Confirm which element is
   the LCP and which editor interactions are slowest.
2. **Low-risk, high-confidence fixes:** make the confirmed LCP image eager/priority,
   correct Khmer display line-height/clipping, and add 24 px hit areas to non-canvas
   controls. These are small, testable changes against the existing six-width matrix.
3. **Accessibility interaction work:** audit the editor's numeric/click-only
   alternatives and error/live-region behaviour; use the existing target-size and
   keyboard harnesses.
4. **Larger performance work:** editor code splitting/INP work and AVIF variants only
   after measurements show they are the bottleneck.

## Do not do

- Do not apply `loading="lazy"` to the confirmed hero/LCP image, and do not combine
  it with `fetchpriority="high"`.
- Do not apply `letter-spacing`, `text-align: justify`, `word-break: break-all`, or
  fixed-height overflow clipping to Khmer text.
- Do not widen the production CSP for the host-injected Cloudflare beacon without an
  explicit owner/security decision; it remains an external observation from rounds
  1–3.
- Do not cache RSVP/editor writes or unversioned editor code in a service worker.
- Do not add `@ts-ignore`, `eslint-disable`, weaken tests or lower thresholds to make
  any of these experiments pass.

## Sources

- web.dev: [Optimize LCP](https://web.dev/articles/optimize-lcp),
  [Common LCP misconceptions](https://web.dev/blog/common-misconceptions-lcp),
  [Optimize INP](https://web.dev/articles/optimize-inp),
  [Optimize long tasks](https://web.dev/articles/optimize-long-tasks),
  [Browser-level lazy loading](https://web.dev/articles/browser-level-image-lazy-loading),
  [Responsive images](https://web.dev/articles/serve-responsive-images),
  [Fetch Priority](https://web.dev/articles/fetch-priority),
  [Resource hints](https://web.dev/learn/performance/resource-hints),
  [Code splitting](https://web.dev/learn/performance/code-split-javascript)
- Chrome for Developers: [Improve image delivery](https://developer.chrome.com/docs/performance/insights/image-delivery),
  [Long Animation Frames](https://developer.chrome.com/docs/web-platform/long-animation-frames),
  [Service worker deployment](https://developer.chrome.com/docs/workbox/service-worker-deployment)
- W3C/WAI: [WCAG 2.2 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html),
  [Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html),
  [Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html),
  [Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html),
  [Identify Input Purpose](https://www.w3.org/WAI/WCAG22/Understanding/identify-input-purpose.html),
  [APG Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/),
  [Declaring language](https://www.w3.org/International/questions/qa-html-language-declarations)
- Khmer: [W3C Khmer script resources](https://www.w3.org/TR/khmr-lreq/),
  [W3C Khmer gap analysis](https://www.w3.org/TR/khmr-gap/),
  [Khmer orthography notes](https://r12a.github.io/scripts/khmr/km.html),
  [Noto font use](https://notofonts.github.io/noto-docs/website/use/)
- MDN: [line-height](https://developer.mozilla.org/en-US/docs/Web/CSS/line-height),
  [lang](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/lang),
  [dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)

## Repository anchors checked

- `src/js/renderer-core.js` — shared image rendering, responsive attributes, `loading="lazy"`.
- `src/js/public-page.js` — guest composition, RSVP/gallery markup, renderer call with `heroTitle`.
- `src/css/tokens.css` — Khmer family/tracking rules and typography tokens.
- `src/css/typography-fonts.css` — self-hosted, subset Noto fonts with `font-display:swap`.
- `src/js/service-worker.js` — check-in-only network-first cache.
- `tools/a11y-target-size.py` — existing 24 px handle/target measurement.
- `docs/NEXT-WORK.md` — open CLS, LCP, bundle and WCAG 2.2 items.
