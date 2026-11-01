# Improvement research — existing functions

**Date:** 2026-11-01
**Scope:** public invitation/guest page, RSVP and gallery, editor, export/templates,
check-in service worker, Khmer typography
**Status:** research only — no application source changed

This note records current, source-backed opportunities for improving functions the
platform already has. It is deliberately narrower than a redesign: each item names
the existing surface, the evidence, the smallest safe experiment, and the trade-off.
A second pass adds invitation metadata/privacy, check-in PWA/offline, album-photo
privacy and multi-tab autosave findings (IMP-9–IMP-12).

## Method

Reviewed the current source first, then compared it with authoritative guidance from
web.dev/Chrome for Developers, the W3C/WAI WCAG 2.2 material, the W3C Khmer script
resources, and Noto/MDN. The W3C Khmer documents are Group Note Drafts; line-height
and specific test strings below are practical recommendations, not W3C-published
numbers. The second pass used the installed performance, accessibility and Web
Interface Guidelines skills, then checked the current server/source paths; its four
items are hypotheses to verify where a code anchor is not conclusive.

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

## Second pass — additional opportunities (2026-11-01)

The first pass concentrated on rendering, editor interaction and WCAG 2.2. This pass
looks at the surfaces around the invitation: how it is shared, how check-in survives a
bad venue network, what happens to uploaded-photo metadata, and what a second editor
tab does to unsaved work. None of these is implemented here.

| ID | Existing surface | Finding and first action | Evidence | Risk / trade-off |
|---|---|---|---|---|
| IMP-9 | Public invitation sharing / search | The template has OG/Twitter title, description, image, dimensions and a versioned absolute image URL. It lacks `og:image:alt` and `twitter:image:alt`; the canonical is relative (`/i/...`); a published page has no robots directive — the only `X-Robots-Tag: noindex` is for a missing/unpublished slug (`server.py:11101`). Add a generic social-image alt with no guest/venue data, render an absolute self-canonical, and decide whether a published invitation is public or link-only. For link-only, send `noindex, nofollow` by header and meta; do not put `Disallow` in `robots.txt` because crawlers then never see the noindex. Google's Event rich result excludes invitation-only events, so do not add Event JSON-LD just for SEO. | Google: [Event structured data](https://developers.google.com/search/docs/appearance/structured-data/event), [noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing), [canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [shareable pages](https://developers.google.com/search/docs/monitor-debug/prevent-abuse); [ogp.me](https://ogp.me/); [Meta link images](https://developers.facebook.com/documentation/sharing/webmasters/images) | This is an owner policy decision, not a blind SEO change. `noindex` does not make a page private; keep the unguessable token/password and `no-referrer` for that. Social previews are cached by third parties and can expose names or venue data; keep the card generic. |
| IMP-10 | Check-in PWA / offline | `manifest.webmanifest` has `icons:[]`, no `id`/`scope`, and `start_url` is the dashboard while `short_name` says “OKID Check-in”. Chromium installability needs 192 px and 512 px icons. The worker precaches the check-in shell, but `/api/` data is not cached; `checkin.js` stores unsynced changes in `localStorage` with no mutation id, cross-tab leader, dead-letter state or pre-event readiness check. Add icons, `id`/`scope` and a valid install target first, then an IndexedDB outbox (`clientId` + `mutationId`), a Web Locks leader and a visible pending/failed count. Keep POSTs and attendee PII out of caches. | MDN: [installability](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable), [manifest icons](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/icons), [Background Sync](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API); web.dev: [web app manifest](https://web.dev/learn/pwa/web-app-manifest), [offline cookbook](https://web.dev/articles/offline-cookbook) | Do not flip the whole app to cache-first. Shell cache-first plus queue replay is safe only after idempotent server mutations and a no-cache path for 401s. `navigator.onLine` is a hint, never a gate; test with real network-off, not just DevTools. |
| IMP-11 | Album photos / EXIF privacy | Album upload validates the image and stores the **raw** byte stream (`server.py:10736–10754`). The responsive derivative path does transpose and strip metadata (`server.py:2637–2651`, `STRIP_EXIF_DERIVATIVES` default on), so derivatives are safe; the original object keeps GPS/device/thumbnail metadata unless a separate scrub layer exists. Decide whether originals are retained; if not, re-encode or strip them server-side on ingest and verify the stored bytes with `exiftool`. On the client, `createImageBitmap(file, {imageOrientation:'from-image'})` + `OffscreenCanvas` can decode/resize/encode without a full-res DOM canvas, but it must never be the only privacy control. | MDN: [createImageBitmap](https://developer.mozilla.org/en-US/docs/Web/API/Window/createImageBitmap), [convertToBlob](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas/convertToBlob), [image formats](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Image_types) | Re-encoding originals changes quality/colour and costs CPU; an original may be needed for future print. Make retention explicit per album. iOS canvas memory is the hard limit: cap area/concurrency and release canvases; a silent blank preview is worse than a visible per-file error. |
| IMP-12 | Editor autosave / second tab | The open D-3 defect (second tab renders four objects and never sets `editorReady`) is consistent with a stale draft-lock/init-order failure. Collaboration queue and editor tab state are kept in `localStorage` (`collaboration-studio.js:23`, `workflow-continuity.js`); there is no Web Locks leader. Reproduce with two tabs, then separate “local draft” from “server-confirmed save”, gate initialization on a BroadcastChannel/Yjs sync step, use `navigator.locks` for the single writer, flush on `visibilitychange → hidden`, and use `If-Match`/412 for server saves. | MDN: [Web Locks](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API), [Page Lifecycle](https://developer.chrome.com/docs/web-platform/page-lifecycle-api), [BroadcastChannel](https://developer.mozilla.org/en-US/docs/Web/API/Broadcast_Channel_API), [beforeunload](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event); Yjs: [y-indexeddb](https://docs.yjs.dev/ecosystem/database-provider/y-indexeddb), [UndoManager](https://docs.yjs.dev/api/undo-manager) | This is a substantial correctness change, not a CSS fix. Do not “take over” by discarding the other tab’s draft; do not treat a successful local IDB write as a server save. Keep `beforeunload` as a warning only and remove it once the server confirms. |

### Web Interface Guidelines quick pass

Checked against the current Vercel Web Interface Guidelines (fetched 2026-11-01). This
is not a full UI audit; it records only findings that map to this pass.

| Finding | File | Action |
|---|---|---|
| Social image has no alternative text | `src/html/public.html:14–21` | Add `og:image:alt` and `twitter:image:alt` with a generic “Wedding invitation for [names]” string; keep venue/guest details out. |
| Canonical URL is relative | `src/html/public.html:22` | Render an absolute self-canonical with `absolute_url()`; keep one canonical method. |
| Install target and manifest identity are underspecified | `src/html/manifest.webmanifest` | Add 192/512 (and maskable) icons, an explicit `id`, a `scope`, and a `start_url` that matches the check-in workflow or rename the app. |
| Queue state is browser-storage only and unversioned | `src/js/checkin.js:8` | Move the outbox to IndexedDB with a schema/version, mutation id, retry/dead-letter state, and a visible pending count; keep `localStorage` only for non-critical UI preferences. |
| RSVP labels and errors already pass the basic guideline check | `src/js/public-page.js` | Do not add `autocomplete` to the guest-name field without deciding whether the submitter is the guest; preserve the existing visible label and error paragraph. |

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
- Do not add `Event` JSON-LD to an invitation-only page or treat `noindex` as access
  control; decide the public/link-only policy first.
- Do not promise client-side EXIF removal while uploading raw originals, and do not
  use `localStorage` as the only durable check-in outbox when offline correctness is
  required.

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

### Second-pass sources

- Google Search Central: [Event structured data](https://developers.google.com/search/docs/appearance/structured-data/event),
  [block indexing](https://developers.google.com/search/docs/crawling-indexing/block-indexing),
  [canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls),
  [prevent abuse / shareable pages](https://developers.google.com/search/docs/monitor-debug/prevent-abuse);
  [Schema.org Event](https://schema.org/Event)
- Open Graph: [ogp.me](https://ogp.me/); [Meta link-image requirements](https://developers.facebook.com/documentation/sharing/webmasters/images)
- MDN: [PWA installability](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable),
  [manifest icons](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/icons),
  [Background Synchronization](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API),
  [createImageBitmap](https://developer.mozilla.org/en-US/docs/Web/API/Window/createImageBitmap),
  [convertToBlob](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas/convertToBlob),
  [Web Locks](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API),
  [Page Lifecycle](https://developer.chrome.com/docs/web-platform/page-lifecycle-api),
  [BroadcastChannel](https://developer.mozilla.org/en-US/docs/Web/API/Broadcast_Channel_API)
- web.dev: [web app manifest](https://web.dev/learn/pwa/web-app-manifest),
  [offline cookbook](https://web.dev/articles/offline-cookbook),
  [IndexedDB app state](https://web.dev/articles/indexeddb-best-practices-app-state)
- Yjs: [y-indexeddb](https://docs.yjs.dev/ecosystem/database-provider/y-indexeddb),
  [UndoManager](https://docs.yjs.dev/api/undo-manager)
- Vercel: [Web Interface Guidelines source](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)

## Repository anchors checked

- `src/js/renderer-core.js` — shared image rendering, responsive attributes, `loading="lazy"`.
- `src/js/public-page.js` — guest composition, RSVP/gallery markup, renderer call with `heroTitle`.
- `src/css/tokens.css` — Khmer family/tracking rules and typography tokens.
- `src/css/typography-fonts.css` — self-hosted, subset Noto fonts with `font-display:swap`.
- `src/js/service-worker.js` — check-in-only network-first cache.
- `tools/a11y-target-size.py` — existing 24 px handle/target measurement.
- `src/html/public.html` — OG/Twitter metadata, relative canonical, no image alt tags.
- `src/html/manifest.webmanifest` — empty icon list and dashboard/check-in naming mismatch.
- `src/js/checkin.js` — localStorage queue, `navigator.onLine` gate, no cross-tab leader.
- `src/js/photo-worker.js` — pixel filtering only; no decode/encode or metadata handling.
- `src/js/collaboration-studio.js`, `src/js/workflow-continuity.js` — localStorage queue and tab state.
- `src/python/server.py` — noindex only for missing slugs; raw album storage; derivative EXIF strip.
- `docs/NEXT-WORK.md` — open CLS, LCP, bundle and WCAG 2.2 items, including D-3 second-tab failure.
