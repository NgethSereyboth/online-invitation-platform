# Canvas motion

## Status and scope

The P1–P6 source implementation follows the [engineering brief](CANVA-SMOOTHNESS-BRIEF.md). **Interaction, performance, visual and regression acceptance is deferred at the user's request.** Source implementation is not a verified smoothness or performance claim. No phase commits have been made.

This remains a vanilla JavaScript, DOM/CSS editor. No rendering framework, GPU renderer, worker pool or runtime dependency was added. Public renderer code was not changed. The implementation ledger and historical check results are in [the motion ledger](../artifacts/canvas-motion/ledger.md).

## Mechanisms and ownership

| Mechanism | Source and responsibility |
|---|---|
| Frame batching | [`editor-pro.js`](../src/js/editor-pro.js) exposes `EInviteMotion.createFrameBatcher(reduce, commit)`. Wheel deltas sum and retain the latest cursor; pointer/slider batches retain the latest value. `flush()` cancels the scheduled frame before applying the final value. Visibility changes flush pending input. |
| Viewport | [`index.html`](../src/html/index.html) contains `#canvasViewport > #stageTransform > #stage`. `editor-pro.js` owns `view = {x, y, zoom}` and the outer transform writer. Existing percent-positioned objects remain inside the stage. [`editor-pro.css`](../src/css/editor-pro.css) promotes only the outer moving layer. |
| Zoom | `EInviteMotion.viewport` provides `setZoom`, `setView`, `fit`, `clientToWorld`, cached geometry and gesture boundaries. `EInviteCanvasViewController` preserves the existing zoom API. Zoom is clamped to 0.1–5; slider positions 0–40 map through `log2(zoom + 10)`. |
| Drag and undo | [`professional-editor.js`](../src/js/professional-editor.js) owns selection move/resize/rotate; [`direct-manipulation.js`](../src/js/direct-manipulation.js) owns inline/crop interactions and the reusable pointer helper. A 3-screen-pixel dead zone precedes transform transactions. [`app.js`](../src/js/app.js) supplies begin/commit/cancel undo transactions and 500 ms nudge coalescing. |
| Snapping | `EInviteMotion.snap.resolve` is pure world-coordinate math with page, sibling, grid, guide and equal-spacing candidates. Tolerance is `6 / zoom` world pixels; a previous snap has a 1.5× release threshold. Sibling candidates are capped at 100. Alt temporarily bypasses snapping. |
| Measurement chrome | `#canvasMeasurements` is a sibling of the moving layer, outside exported stage content. It renders screen-width hairlines, rulers, guides, margin and distance labels. Guide edits and margin settings use document transactions. New precision controls include English and Khmer strings. |
| Wheel and pan | Ctrl/Cmd-wheel normalizes pixel/line/page units (1/40/800), sums deltas per frame and applies `2 ** (-0.01 * clamp(delta, -25, 25))`. Plain wheel is left to native scrolling. Space/middle/hand-tool pan writes screen-space translation. Touch-background pan can continue with bounded inertia. |
| Reduced motion | The media query disables programmatic tweens and touch inertia without removing zoom or pan controls. Wheel edge-paging remains **off**. |
| Decode-ahead | `editor-pro.js` observes stage images and warms current/next enabled design-page images/backgrounds during idle time. Decode work pauses while hidden or gesturing. See the resource limits below. |
| Collaboration | [`collaboration-studio.js`](../src/js/collaboration-studio.js) owns the existing V31 network lifecycle separately from the editor bundle. Polling is serialized, jittered and backed off; focus/visibility resume drains queued edits before polling. Presence requests are serialized too. |

Other continuous-input integrations remain in [`editor-core.js`](../src/js/editor/editor-core.js), [`canvas-plus.js`](../src/js/canvas-plus.js) and [`photo-editor.js`](../src/js/photo-editor.js). [`editor-command-system.js`](../src/js/editor-command-system.js) routes canonical keyboard commands.

## Coordinate convention

The sole viewport transform is:

```text
translate3d(x, y, 0) scale(zoom)
```

Translation is in screen pixels; stage dimensions and object geometry are world pixels. For a client point:

```text
worldX = (clientX - viewportLeft - borderLeft + scrollLeft - x) / zoom
worldY = (clientY - viewportTop  - borderTop  + scrollTop  - y) / zoom
```

At a cursor-anchored zoom, compute the world point using the old zoom, then compensate translation:

```text
newX = oldX - worldX * (newZoom - oldZoom)
newY = oldY - worldY * (newZoom - oldZoom)
```

Cache viewport rectangles, borders and stage dimensions before gesture writes. Resize observation refreshes idle geometry. The debug guards below identify remaining synchronous geometry reads; they do not prove their absence.

## Motion and resource limits

`EInviteMotion.MOTION` centralizes the adopted time budgets:

| Budget | Milliseconds |
|---|---:|
| Programmatic tween cap | 150 |
| Plain-wheel re-arm indicator | 80 |
| Wheel end | 140 |
| Zoom readout debounce | 200 |
| Flick lock constant (edge paging is off) | 250 |
| Long-press constant | 251 |
| Transition cap constant | 400 |
| Idle scheduling timeout/fallback delay | 100 |
| Nudge coalescing window | 500 |

The decode warmup uses `requestIdleCallback` with a 100 ms timeout, or a timer followed by rAF. The timeout is a scheduling deadline, **not** a guarantee that decoding finishes within 100 ms. No new decodes start during gestures or inertia. Already-running browser decodes cannot be cancelled.

- At most two simultaneous decode calls and eight queued sources.
- The retained LRU cache holds at most eight images and an estimated 24 MiB (`naturalWidth * naturalHeight * 4`). This bounds retained entries, not browser process memory or transient decoder allocations.
- Images larger than that estimate are not retained. Existing `img` nodes use `decoding="async"`; detached preload images use low fetch priority.
- `IntersectionObserver` uses a 240 px look-ahead margin and a 0.9 threshold. Current/next-page document sources are also queued directly, including backgrounds.
- Cached `Image` references retain the decoded resource for the DOM image path; no redundant `ImageBitmap` copies or new blob URLs are created. The browser ultimately controls decoded-resource residency.
- Visibility and lifecycle cleanup cancel scheduled warmups, disconnect observers and release cache references. Speculative decode failures increment debug counters only; they do not replace the normal image loading path.

Collaboration polling uses an 800 ms base with ±10% jitter, exponential failure backoff and a 30 s maximum. Success resets the failure count. The next poll is scheduled after the previous request and queued upload work settle. Snapshot failures retry the snapshot; epoch mismatches stop automatic retries for explicit recovery. Hidden tabs stop scheduling polls/presence; already-issued requests may settle. Focus/visible resume is single-flight. Pending uploads use batches of at most 500 operations and retain the existing durable offline queue. Presence uses a five-second idle heartbeat and an 80 ms pointer throttle, with at most one presence request in flight.

## Debug diagnostics

Open the editor with `?_perfdebug=1` (or append `&_perfdebug=1` to an existing query). This opts into local diagnostics only; it adds no analytics service.

- `window.__einvitePerf`: commit count, total/maximum commit duration, layout-read count, successful decode count and decode-failure count.
- `performance.getEntriesByName('einvite:commit')`: frame-batcher commit durations.
- `performance.getEntriesByName('einvite:gesture')`: viewport gesture durations.
- Gesture-time guards warn on bounding/client rect methods, computed style, offset dimensions/positions, client dimensions/borders and scroll dimensions. They restore the original methods/getters at lifecycle cleanup. Warnings are capped at 20; the counter continues.
- Marks are cleared after spans; measure buffers clear after 200 entries per name. Counters remain cumulative.
- `EInviteMotion.images` exposes retained image count, estimated bytes, queued count and active decode count.

These wrappers deliberately perturb execution and detect reads that might cause layout, not whether a particular read actually forced layout. Use an ordinary non-debug page for final performance measurements. A generic commit counter includes all batchers and is not a per-gesture attribution metric.

## Deferred verification handoff

Regenerate source bundles and runtime mirrors through the supported entry point:

```bash
python3 build.py all
```

The final generation run returned exit 0 and the affected source/generated JavaScript passed `node --check`. The served `bundle-index.js`, its CSS, collaboration module and editor HTML match their source artifacts; the running local server returns the updated route. This is generation/syntax/served-byte evidence only, not an interaction test.

**Known pre-existing generator issue:** `build_editor_bundle.py` and `build_page_manifests.py` calculate their server destination as `src/python/build/`, not `src/python/`. After generation the server's standalone `editor-suite.js`/CSS remain stale and its `page-assets.json` is missing. The active editor route uses the correctly generated `bundle-index.js`/CSS; this does not make the other outputs correct. The artifact audit caught this despite the successful build exit. No baseline generator repair was made under the no-unrelated-fixes constraint. Details: [delivery inspection](../artifacts/canvas-motion/P6/delivery-inspection.json).

When testing resumes, resolve that build-output blocker with authorization, then run the ordered build/static gates from the brief, followed by interaction, performance and visual checks. Compare pytest failures against the recorded initial identities, not an old roadmap total. Do not repair unrelated baseline failures or regenerate visual baselines just to make checks green.

Existing tooling:

- [`canvas_motion_contract_test.py`](../tests/canvas_motion_contract_test.py): initial P1 built-symbol and deterministic batcher checks.
- [`canvas_motion_playwright.py`](../tests/canvas_motion_playwright.py): initial P1 burst check; it still requires expansion/adaptation for P2–P6.
- [`canvas-motion-perf.mjs`](../tools/canvas-motion-perf.mjs): three-run wheel/pan/snap/crop harness; audit its stage-transform instrumentation before accepting P2–P6 results.
- [`canvas-motion-visual.py`](../tools/canvas-motion-visual.py): P1 comparison against initial source; later phase coverage is pending.
- [`visual_regression.py`](../tests/visual_regression.py): existing application-wide visual runner.

Still required: cursor invariance ≤1 px; ≤one commit per elapsed frame plus boundary allowance; dead-zone/one-step undo/capture/Escape behavior; zoom-scaled snap tolerance; no gesture layout shifts; keyboard parity; reduced motion; hidden/focus/retry/upload races; decode/cache cleanup; Khmer IME; route/script/byte budgets; three saved representative perf runs and visual evidence. No acceptance result for those checks is asserted here.
