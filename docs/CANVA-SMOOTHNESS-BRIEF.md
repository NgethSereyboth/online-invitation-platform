# Replicating Canva-class Canvas Smoothness in eInvite — Engineering Brief

**Audience:** the long-running Freebuff agent (GPT, max effort) implementing this in `F:\Project\eInvite\online-invitation-platform`.
**Author:** REA evidence pack, compiled 2026-10-17. Target studied: Canva desktop app 1.126.1 (Electron / Chromium 150), live editor session, 45 s instrumented interaction window.
**Status:** DRAFT v1 — independent review pending (see §7.D).

---

## 0. How to use this document

You are executing a long-running implementation. Read this whole document once, then work **phase by phase** (P1…P6, §4). Do not skip the verification gates; do not batch two phases into one commit.

**Hard constraints of the target repo (from `_rea-canva/einvite-recon.md`):**

- Vanilla JavaScript only. No React/Vue/Svelte, no bundlers, no npm runtime deps. "Build-tool-free" is an enforced project ground rule (`README.md`, `docs/ROADMAP.md` rule #4).
- The only supported build entrypoint is `python3 build.py all` (editor bundle → route bundles → manifests → mirror). `python3 build.py bundles --check` must stay byte-identical when you did not intend to change outputs.
- The design surface is **DOM/CSS-positioned** (`#stage` / `#canvasViewport`, percent-based left/top/width/height), **not** an HTML5 canvas renderer. All replication below targets DOM/CSS.
- Route bundles have script-count and weight budgets (route sources in `docs/route-bundle-sources.json`; the 3-script cap is documented in `plans/003-triage-results.md` and enforced by budget tests incl. `tests/v55_route_weight_budget_test.py`). Any new JS file must be wired through `src/python/build/build_editor_bundle.py` **and** route sources, then budgets re-verified.
- CSP: no `innerHTML`/`eval` in editor JS (see `docs/V0_52_ARCHITECTURE.md`). Bilingual EN+KH strings (rule #5). Playwright tooling exists (`tests/visual_regression.py`, `tests/browser_runtime.py`).

**Evidence convention used below.** Claims cite an evidence alias like `[E-EXEC]`; Appendix §7.A maps every alias to the full REA evidence hash. Status tags on every mechanism:

| Tag | Meaning |
|---|---|
| `LIVE` | Runtime-confirmed in the 45 s instrumented capture (V8 coverage counts + requests). |
| `STATIC` | Read from shipped bundle source; **not** observed executing in the capture window. |
| `CSS` | Read from the shipped stylesheet (fetched from the public CDN; REA does not retain CSS bodies). |
| `INFER` | Explicit inference/recommendation by this brief — not a Canva fact. |

**Never promote a STATIC mechanism to a runtime claim.** The capture's own limitations (§2.2) apply to everything marked LIVE too.

---

## 1. Executive summary — what actually makes it feel smooth

Ten mechanisms, ranked by leverage for eInvite. Each maps to a phase in §4.

1. **One composited transform layer.** The entire canvas content lives under a single element that only ever changes `transform` (origin `0 0`, `will-change: transform`, `position: fixed` parent, `pointer-events: none`, children `pointer-events: none !important`). Nothing inside re-layouts during pan/zoom. `CSS` → P2.
2. **Frame-aligned input batching.** Wheel and pointer deltas are *merged* into one pending value and committed exactly once per `requestAnimationFrame` — 31 wheel events produced 28 zoom applications in the live window. `LIVE` → P1.
3. **Wheel semantics with explicit clamps.** Ctrl/Cmd+wheel = zoom, factor `2^(-0.01 · clamp(ΣΔ, ±25))` per rAF batch `LIVE`; plain wheel = scroll/pan; `deltaMode` normalized with LINE=40 / PAGE=800 px `STATIC`; ~80–140 ms settle debounces separate "gesture" from "idle". → P5.
4. **Zoom-to-cursor math done symbolically.** Zoom is normalized (relative factor → absolute zoom clamped to `[0.1, 5]`) and the translation is compensated by `(newZoom − 1) · currentZoom · cursorOffset` so the point under the cursor is invariant — no iterative fudge. `STATIC` → P2.
5. **A drag pipeline with a 3 px dead zone.** Drag state only starts after the pointer leaves a 3 px box; then `setPointerCapture` (non-touch) + `preventDefault`; drags are wrapped in an **undo transaction** (`undo.startBuffering()`) so a 2-second drag is one undo step. Drags ran live (counts 14/2/2 on `onDragStart` entries). → P3.
6. **Flick / page-wheel behavior with a lock.** When a scrollable surface hits its edge, accumulated wheel delta > 75 px (1000 after manual scroll) switches page, then a 250 ms lock ignores new wheel input, and `prev` restores scroll position in the next frame. `LIVE` → P5.
7. **Feature-module snap system.** Snapping, guides, rulers, distance-measuring, margins are separate installable modules (`install_snapping`, `install_guides`, `install_rulers`, `install_distance_measuring`, `install_margins`) — i.e., a snap engine with pluggable providers, always-on measurement overlays. `STATIC` → P4.
8. **Bounded animation budgets everywhere.** Positional tweens cap at 150 ms; wheel re-attach at 80 ms; wheel-end at 140 ms; zoom commit at 200 ms; transitions ≤ 400 ms. Motion is *short and damped*, never springy-long. `STATIC` (150 ms quote verified) → P1/P5.
9. **Steady-state networking that backs off.** Session heartbeat = `fetch(url?Date.now())` on an async loop with `min(max, initial·factorⁿ) · jitter` backoff `LIVE` (2 `/_online` requests in 45 s). Maps directly onto eInvite's CRDT poller (800 ms) → add jitter + backoff + pause-when-hidden. → P6.
10. **Rendering: don't copy the GPU stack.** Canva ships WebGL/Skia renderers (`useSkiaRenderer`, `bitmaprenderer` blits) because it draws arbitrary design content. eInvite's stage is DOM; the transferable part is **layer discipline + decode-ahead + never read layout inside the gesture loop**. `STATIC` → P6.

What eInvite should *not* take: the WebGL/Skia renderer, the Virtuoso-style virtualized page list, React-style state stores, WebRTC stack. They solve problems eInvite doesn't have at its current scale.

---

## 2. Evidence base

### 2.1 Method and coverage

- **Shell is not the editor.** The desktop app's `app.asar` (23,258,934 B) is a thin Electron shell — the editor is served from `canva.com`. Static asar analysis `[E-ASAR]` (CLI session) + fuse inspection `[E-FUSES]`; Node inspector disabled → passive CDP route.
- **Runtime capture** (passive, user-approved): Canva relaunched with `--remote-debugging-port=9222`; editor target `6B4EB14015EDB5F4122EB2A4AFEB7EF1` = `https://www.canva.com/design/DAHGsoc9tlw/…/edit` ("Website"-type design), Chrome/150.0.7871.250, Electron 43.5.1, `canvadesktopapp-prod/1.126.1` `[E-TARGETS]`.
- **Page/DOM/resources:** three web-page inspections `[E-PAGE1]` `[E-PAGE2]` `[E-PAGE3]` (34 script sources / 46 resources after origin filter incl. the `static.canva.com` CDN; export `[E-SCRIPTS]` = **33 file-backed `.js` bundles + 1 anonymous inline script** — the manifest also indexes the Skia wasm and the GTM container URL); bundle-level analysis `[E-BUNDLE]`.
- **Scripts:** 33 flat JS bundles in `web-scripts-js/` (incl. `c54bf1746175520c.js` 6.3 MB main, `4c07d09cf641607a.js` 4.1 MB interaction/render core, `43bea72bf7ab0b7f.js` 1.96 MB, `57f6584876569505.js` 1.47 MB, webpack runtime `2d34fe8a8200f57e.runtime.js`). Semantic JS-app analyses: run1 all-files `[E-RUN1]`, run2 big-four static-complete (4.66 M AST nodes, 558 findings, 0 parse failures) `[E-RUN2]`; both heap-capped at 4 GiB in the semantic phase (documented limitation).
- **Listeners:** five inventories (`html` 4 listeners `[E-LIST-H]`, canvas 0 `[E-LIST-C]`, layer-marker `[E-LIST-M]`, body 191 = Sentry instrumentation `[E-LIST-B1]` `[E-LIST-B2]`). Sentry wraps `addEventListener`, masking source locations — recorded limitation.
- **Live interaction window (the newest evidence):** 45,000 ms `observe_web_execution` `[E-EXEC]`, 2026-10-17 04:25:40.601Z → 04:26:25.602Z, `end_reason: window_elapsed`; 146 scripts with UTF-16 execution ranges/counts; 7 in-window requests (330 outside window excluded); start/end screenshots `[E-SHOT1]` `[E-SHOT2]` (both 1920×1154) + an earlier editor screenshot `[E-SHOT0]`.
- **Coverage aggregation used throughout this brief (reproducible):** activity counts = Σ `range.count` over ranges with `count>0` **excluding `is_block_coverage` entries** (nested ranges included ⇒ activity indicator, not additive — consistent with E-EXEC limitation #3); unit coverage = union of executed `[start,end)` intervals in UTF-16 code units. Reproduced exactly for the two quoted bundles via `corr-exec.mjs` (4c07: 7,079,994 counts / 311,159 units of 4,186,502 bytes = 7.4 %; c54bf: 1,867,919 / 314,379 of 6,466,068 = 4.9 %).
- **CSS complement:** 8 public `.ltr.css` stylesheets fetched from `static.canva.com` (`css/` folder); main `feb52ee2f9d8fe7a.ltr.css` (272 KB). Not REA-retained (documented limitation).

### 2.2 Runtime-capture limitations (quote these wherever you make LIVE claims)

1. Precise coverage **resets counters and disables optimized execution** — timings during the window are pessimistic; counts are lower bounds on "what code paths exist", not production rates.
2. Counts are per-range; **nested ranges must not be summed**. Zero counts mean "not observed in this window", not "dead code".
3. No chronological trace — only aggregates.
4. Main-frame, main execution world only: **workers, WASM, child frames excluded**.
5. Request `callsites` are producer-reported initiators, not UI causality proof.
6. Budgets: 8 MiB metadata / 8 MiB requests / 32 MiB retained sources; scripts parsed after cutoff excluded.
7. Local-arm clock ≠ backend coverage clock (counts may bleed into command intervals).
8. Source maps are published by Canva but **empty** — all offsets refer to shipped minified sources (in `web-scripts-js/`, matching `static.canva.com` bytes).
9. REA does not retain CSS bodies; stylesheet claims come from the separately fetched files.

---

## 3. Mechanism catalog

Each mechanism: what Canva does → evidence → status → **replication recipe for eInvite (vanilla JS)** → acceptance test → pitfalls.

### M1. Frame-aligned input batching — `LIVE`

**What.** Wheel/pointer/scroll inputs are not applied per event. They are reduced into a single pending value and committed **once per animation frame**. The utility (minified `n4e`) is:

```js
var n4e=class{
  accumulate(a){
    this.pending
      ? this.pending.value = this.cHm(this.pending.value, a)   // reducer merge
      : this.pending = {
          Qgg: window.requestAnimationFrame(()=>{              // flush on next frame
            var {value:b} = n(this.pending);
            this.pending = void 0;
            this.qCt(b);                                       // commit
          }),
          value: a
        };
  }
  flush(){…}
  constructor(a,b){ this.cHm=a; this.qCt=b }
}
```

- Zoom usage: reducer `(d,e)=>({delta:d.delta+e.delta, center:e.center})` — **deltas sum, cursor center takes the latest**; commit = `lMh` (the zoom application). `STATIC` quote, `LIVE` counts.
- Live counts in one 45 s window: `accumulate` called **31×** → `lMh` (commit) **28×** → the app applied zoom at most once per frame while 31 wheel events arrived. Two other live instances of the same utility: 9× (a `flush`-style commit) and **5,514×** on a pointer/drag pipeline (most plausibly pointer-move batching during the two drags observed). `[E-EXEC]`
- Also used as the pan accumulator in the classic canvas handler (`this.nWt = new n4e(...)` around `this.nWt.accumulate(b)` in `onWheel`). `STATIC`

**Why it matters.** It decouples input frequency (150+ Hz trackpads/mice) from render frequency (60 Hz), removes redundant intermediate states, and makes the interaction loop *bounded*: at most one state commit + one paint per frame regardless of event storm.

**eInvite recipe (P1).** Add to the editor runtime (extend `src/js/editor-pro.js` or the shared suite):

```js
function createFrameBatcher(reduce, commit) {
  let pending = null;
  return {
    accumulate(v) {
      if (pending) { pending.value = reduce(pending.value, v); return; }
      pending = { value: v };
      requestAnimationFrame(() => {
        if (!pending) return;
        const v = pending.value; pending = null;
        commit(v);
      });
    },
    flush() { if (pending) { const v = pending.value; pending = null; commit(v); } }
  };
}
// zoom:   reduce = (a,b) => ({ delta: a.delta + b.delta, cx: b.cx, cy: b.cy });
// moves:  reduce = (a,b) => b;            // pointer: latest wins
```

Route **all** continuous inputs through batchers: wheel-zoom, pan drag, crop-drag, slider scrub, resize handles. One commit = one DOM write + one state sync.

**Acceptance test.** Playwright script (pattern of `tests/browser_runtime.py`): dispatch a synthetic burst of ≥30 `wheel` events within one frame (`page.mouse.wheel` × N), record transform-matrix mutations via `MutationObserver` on style attr / rAF sampling; assert **applied commits ≤ frames elapsed + 1** and final zoom equals the accumulated expectation. Add a static contract test (repo style: `tests/canvas_motion_contract_test.py`) asserting the batcher symbol exists in the built `editor-suite.js`.

**Pitfalls.** Don't batch *discrete* actions (click, keypress). Always `flush()` on gesture end (`pointerup`, `wheel` settle) so the last delta can't be lost when rAF is throttled (tab switch — combine with `visibilitychange` → flush).

### M2. The single transform layer — `CSS` (+ `STATIC` wiring)

**What.** Canvas content is composed as exactly three stacked responsibilities:

```css
._2_17VA{cursor:move}                                   /* drag-handle affordance */
._8F7d0w{pointer-events:none;will-change:transform;position:fixed;top:0;left:0}
.I9M93w{transform-origin:0 0;will-change:transform;transition:transform .1s linear}
.I9M93w *{pointer-events:none!important}                /* content never eats gestures */
.G0knkQ{touch-action:none;background-color:#0f101500}    /* gesture surface */
vALUZQ{touch-action:none}                                /* another gesture surface */
```

- Outer `_8F7d0w`: **fixed**, never transformed by the loop, isolates the surface from page layout.
- Inner `I9M93w`: the only element whose `transform` changes; origin `0 0` (so translate/scale composition is trivial); `will-change: transform` is permanent on this one layer; `transition: transform .1s linear` — programmatic (non-gesture) moves get a 100 ms linear tween; during direct gestures the code writes transforms per frame (gesture loop in `4c07` schedules its style application through a rAF-driven reaction — `STATIC`).
- Budget hygiene: the whole 272 KB stylesheet uses `will-change` only **11×**, `touch-action` 9×, `contain` 13×, `transition:transform` 31×. Layer promotion is deliberate, not sprayed.

**eInvite recipe (P2).** Restructure `#stage` into:

```html
<div id="canvasViewport">                     <!-- fixed size, overflow hidden, contain: layout paint -->
  <div id="stageTransform">                   <!-- transform-origin:0 0; will-change:transform -->
    <div id="stage"> … existing % positioned elements … </div>
  </div>
</div>
```

- Single source of truth `view = { x, y, zoom }`; one `applyView()` that writes `stageTransform.style.transform = 'translate3d(x,y,0) scale(zoom)'` and updates `#zoomLevel` (do **not** write per-element).
- Hit-testing/creation math (`canvasPoint()`, `objectAtPoint()`) converts client→world via the inverse matrix — keep the existing percent coordinate system inside `#stage` untouched.
- Gesture sessions add `will-change`; idle sessions leave the 100 ms `transition` for programmatic zooms (zoom buttons, “Fit”) and **remove it during gestures** (`transition:none` is implicit because you write transform per frame anyway — but explicitly toggle a `.gesture` class to avoid the 100 ms easing fighting the direct manipulation).
- Event ownership: viewport listens; children keep `pointer-events` normal for hit-testing **except** pure-visual overlays (guides, marquee) which get `pointer-events:none`.

**Acceptance test.** After `build.py all`: Playwright — perform pan+zoom; assert (a) only `#stageTransform` style changes in the mutation log during the gesture, (b) zero layout thrash: `performance.getEntriesByType('layout-shift')` empty / CLS 0, (c) element bounding boxes preserve world-relative geometry within 0.5 px across random zoom steps (round-trip matrix test).

**Pitfalls.** Don't set `will-change` on every element (memory blowup); one layer. Don't use percentage `transform`; keep `origin 0 0` and order `translate→scale` consistently (`scale` after `translate` in the string means visually `translate(scale)` — pick one convention and document it: **`translate(x, y) scale(z)`**, matrix `(z·x, z·y)`).

### M3. Zoom semantics — `LIVE` (new engine) + `STATIC` (classic path)

**What (new engine, the one exercised in the capture).** Ctrl/Cmd+wheel is captured by a zoom-controller class (`__c.a5e`, `4c07…` @≈3,027,500–3,030,600) mounted on the canvas container:

```js
// attach / detach
eBj(){ this.container?.addEventListener("wheel", this.Mik, {passive:false}) }
// plain wheel with no ctrl/meta → hand back to native scroll, debounce re-attach:
egk = d => { if(!d.ctrlKey && !d.metaKey || this.Ykf){
    this.N.cbt?.get() || this.Xtj();      // detach zoom controller
    this.N.ceh?.(d);                       // notify (UI hint)
    this.Ykf = true; this.SNp(); }}
SNp = dc(() => { this.Ykf = false; this.N.cbt?.get() || this.eBj(); this.N.aNt?.() }, 80)
// ctrl/meta wheel → batch → apply:
Mik = d => { if(d.ctrlKey||d.metaKey){ …preventDefault…
    { delta: d.deltaY, center: new Vd(d.clientX, d.clientY) } → qms.accumulate(…) } }
lMh({delta:a, center:b}){
    a = this.aco() * o4e ** -wk(a, -25, 25);        // per-batch clamp ±25
    c.call(this, wk(a, this.N.minZoom.get(), this.N.maxZoom), b);  // absolute clamp
    this.Nik(); }                                     // dc(…, 200) settle
```

- `o4e = 2**.01` (`4c07…` @≈2,989,845) → per-batch factor `2^(-0.01 · clamp(ΣΔ, ±25))`, i.e. **±19 % max per frame** (25 dx → ×0.84/×1.19); accumulated ΣΔ merged by M1.
- `wk = (a,b,c) => Math.min(c, Math.max(b,a))` (`4c07…` @≈636,421) — the clamp used everywhere (as a function: reuse pattern, don't inline).
- Live counts: `Mik` 31, `accumulate` 31, `lMh` 28; the resulting zoom was applied by the scene transform controller `setTransform` **28×** (`c54bf…` @≈4,156,944 — the live branch set the *absolute* zoom, clamp `Math.max(Math.min(b.zoom, 5), .1)`; the multiplicative branch `Math.max(Math.min(a.zoom*b.Kgn,5),.1)` @≈4,157,994 exists but was not the live branch). `[E-EXEC]`

**What (classic canvas path, present but not run in this capture).** `STATIC` — still worth copying for structure:

```js
// wheel dispatch (canvas mount):
Q = sa => { sa.preventDefault();
  if(sa.ctrlKey) O({ Kgn: 2 ** (-sa.deltaY/200) });              // zoom: ±dx/200 powers of two
  else { let vertical = (sa.shiftKey||sa.altKey) && sa.deltaX===0;
         let dx = vertical ? sa.deltaY : sa.deltaX;
         let dy = vertical ? 0 : sa.deltaY;
         O({ translation: { x: current.x - dx, y: current.y - dy } }); } }
// zoom handler normalizes relative→absolute then compensates translation:
O = ({translation, Kgn, zoom}) => { … if(Kgn){ if(Kgn<1){var c=.1/v(); Kgn<c&&(Kgn=c)} else {c=5/v(); Kgn>c&&(Kgn=c)}
   var adjust = de((Kgn-1)*v(), cursorLocalPoint);               // zoom-to-cursor
   translation = Yd(translation, adjust) } commit({translation, Kgn}) }
```

Zoom-to-cursor math, plainly: `newTranslation = oldTranslation + (newZoom − oldZoom)/oldZoom × (cursor − oldTranslation)` — i.e. keep the world point under the cursor invariant. **Zoom slider mapping** (classic UI): position ∈ 0..40 ←→ zoom via `t1j = (min,max) => { c = log2(min+10); d = log2(max+10)−c; pos = (log2(zoom+10)−c)/d·40; zoom = 2^(pos/40·d+c)−10 }` — a log scale with +10 offset so `0.1 ↔ 0` and `5 ↔ 40`. **Animated zoom** (programmatic): `duration = a8g(|log2(new)−log2(old)|)`, progress easing `f≤0.2 ? 25f³ : 1 + 0.8·(1.25(f−1))³` (fast attack, long tail), applied on `log2` scale. All of the above is `STATIC` (byte-exact quotes; classic-path quotes live in `c54bf…` = main bundle / classic canvas engine, zoom-controller/new-engine quotes in `4c07…` = interaction core).

**Wheel normalization hook** (`STATIC`, not executed in window, `4c07…` @≈405,768): `deltaY * (Map{DOM_DELTA_LINE:40, DOM_DELTA_PAGE:800}.get(deltaMode) ?? 1)`; `preventDefault` only if the consumer didn't `update(g)` and event `cancelable`; end-of-wheel debounce **140 ms**; the update fan-out is rAF-scheduled once per frame.

**eInvite recipe (P2 + P5).**

- `wheel` listener on `#canvasViewport`, `{passive:false}`; normalize `deltaMode` (40/800); branch:
  - `ctrlKey||metaKey` → `zoomBatcher.accumulate({delta, cx, cy})` with reducer summing `delta` (M1); commit applies factor `2^(-0.01·clamp(ΣΔ,±25))`, clamps absolute zoom to `[0.1, 5]`, updates translation by the invariant formula above.
  - otherwise → pan: shift/alt swap axes (horizontal-only wheels pan X), translate by `-delta` in screen px (world px = Δ/zoom).
- Keep eInvite's existing `#zoomLevel` / `currentZoom()` public surface; add `setZoom(z, {cursor})` + `applyView()`.
- Settle constants to adopt: **80 ms** re-arm, **140 ms** wheel-end, **200 ms** zoom commit UI, all via one `debounce(fn, ms)` helper.
- Programmatic zoom (buttons/Fit): use the animated form, but cap duration **150 ms** (M8) and ease `f≤0.2?25f³:…` is optional — a simple `easeOutCubic` ≤150 ms matches the feel.

**Acceptance test.** Playwright: (1) ctrl+wheel ×10 over a fixed world point → that point's screen position invariant within 1 px after each step (zoom-to-cursor property); (2) absolute zoom never < 0.1 or > 5 across stress loop; (3) per-frame factor bounded ≤1.20.

**Pitfalls.** Don't `preventDefault()` plain (non-ctrl) wheel unless you handle scrolling — that breaks trackpad users' expectation. Guard `ctrlKey` only. And do not zoom on pinch-hijack (browser pinch should be ignored/rejected via the pattern in M4 note).

### M4. Panning & page scrolling — `LIVE` (scroll surface) + `STATIC` (pan states)

**What (scroll-based canvas, the live path).** The capture shows the design's canvas is a native scroll container that also *pages*: class `Nmb` (`4c07…` @≈3,137,000–3,141,200; verbatim core, comments added):

```js
this.onWheel = (c, d) => {
  var e = Gkb(c.target, 0, 20);                    // "is there a scrollable ancestor (≤20 levels)?"
  if (c.ctrlKey || c.metaKey || Math.abs(c.deltaY) < Math.abs(c.deltaX) || e) return;   // horizontal or nested-scroll → ignore
  this.r0o || (d.addEventListener("scroll", this.onScroll), this.r0o = true);
  e = Math.sign(c.deltaY) === Math.sign(this.mji);        // same direction as previous
  var f = Math.abs(c.deltaY) < Math.abs(this.mji),        // decelerating?
      g = Math.abs(this.mji) - Math.abs(c.deltaY),        // magnitude drop
      h = this.mji !== 0;                                  // not first event
  this.mji = c.deltaY;
  this.dZl || (e && f && g < 20 && h) || (                 // not a natural decay → user is pushing
    (Math.sign(this.NDf) !== Math.sign(c.deltaY) && this.NDf !== 0
        ? (this.NDf = c.deltaY, this.dZl = false)          // direction change → restart accumulator
        : this.NDf += c.deltaY,                            // else accumulate
     e = d.scrollTop, f = d.scrollHeight, g = d.clientHeight,
     f = c.deltaY > 0 && e < f - g - 1,                    // can scroll further down
     (c.deltaY < 0 && e > 0 || f)
        ? d.scrollBy(0, c.deltaY)                          // normal scroll while scrollable
        : this.bkl() ? Math.abs(this.NDf) <= (this.TZo ? 1000 : 75) ||
            (this.TZo = false, c = this.NDf > 0 ? "next" : "prev",
             this.mji = this.NDf = 0,
             this.wTw(c) && (this.dZl = true,
               window.setTimeout(() => this.dZl = false, 250),   // 250 ms flick lock
               c === "prev" && requestAnimationFrame(() => { d && (d.scrollTop = d.scrollHeight - d.clientHeight) }),
               this.r0o = false, d.removeEventListener("scroll", this.onScroll)))
          : this.NDf = 0));
};
```

Reading: while the surface can scroll natively, wheel deltas go to `scrollBy`. At the edge, a *pushing* gesture (not the natural ±20 decay tail, not during the 250 ms lock) accumulates; once |ΣΔ| exceeds **75 px** (or **1000 px** if the user already scrolled this gesture), it triggers page `next`/`prev`; after switching to `prev`, scroll position is restored to the bottom **inside the next rAF** so reading flows naturally. Live count: 9 wheel events handled. `[E-EXEC]`

**What (free-form pan states).** Classic canvas drag-pan arms states: `pointerdown` with `button===0 && ctrlKey` → "zoom drag", `pointerType==="touch"` → `touchscreen`, space held → `space_pan`, `button===1` → `middle_click_pan`, button 2 → `right_click_pan`; middle-click default is prevented; contextmenu suppressed. Interaction telemetry names the modes (`this.znf("scrollwheel")`, `hFf("scroll")`, `hFf("zoom","scroll")`). `STATIC` (`c54bf…`, canvas-mount block ≈4,980,000–4,988,200) — none of these pan states executed in the capture window (the user never drag-panned).

**Pinch note.** A gesture filter (`WSa`, `4c07…` @≈400,585, executed 782× live) blocks native pinch when ≥2 pointers: `a = gestureSet.has("pinch-zoom")||gestureSet.has("auto"); if(c.size>=2 && !a) event.preventDefault()` — i.e. **opt-in** pinch-zoom; otherwise the browser's pinch is suppressed. `LIVE` count, `STATIC` body.

**eInvite recipe (P5).** Two modes, both small:
- Page-flow designs (invitations are page-like): keep native scroll as the base; add the *edge-accumulator page switch* only if product wants wheel-paging — constants 75/1000/250 ms, `scrollBy` otherwise, `rAF` scroll restore on backward switch. `INFER`: start without page-switching; it surprises users unless the surface is visually paginated.
- Space/middle-drag pan for the editing canvas: implement `space_pan` + `middle_click_pan` exactly as above (armed state machine, 3 px dead zone from M5 applies to mouse pan too, `preventDefault` on middle-click, no context menu while panning).
- Explicitly ignore ctrl+wheel that's meant as browser pinch-zoom (`ctrlKey` + `pinch` cursor) — eInvite should treat ctrl+wheel as zoom (same as Canva), that's settled.

**Acceptance test.** Playwright: hold space + drag → view translates 1:1 with pointer (≤1 px error), cursor is `grab/grabbing`; middle-drag does nothing but pan (no autoscroll widget); wheel at edge does not trigger page changes unless the feature flag is on.

### M5. Drag pipeline with 3 px dead zone + undo coalescing — `LIVE` (drag ran) + `STATIC` (wiring)

**What.** The universal drag hook (pointer path), verbatim:

```js
v = kv(x => {                                   // pointermove
  if (e.current) {
    var y = { x: x.clientX - f.current.x, y: x.clientY - f.current.y };  // delta from press
    if (g) b?.(x, y);                           // live "move" callback (already dragging)
    else {
      if (Math.abs(y.x) < 3 && Math.abs(y.y) < 3) return;   // ← 3 px dead zone = still a click
      a?.(x);                                   // onDragStart
      x.pointerType !== "touch" && d.current?.setPointerCapture(x.pointerId);
    }
    x.preventDefault(); h(!0); l(y);            // suppress text selection; dragging=true; track
  }}, [g, b, a])
```

- **3 px dead zone**: below it, `pointerup` remains a click (no drag state, no undo entry, no jitter). Verified in `c54bf1746175520c.js` @≈1,507,169 — the minified source has a **line break** between `abs(y.x)<` and `3` (semantically `< 3`); the block above is reformatted for readability.
- `setPointerCapture` on mouse/pen (10 occurrences across the bundles); touch handled by touch events separately.
- **Undo transaction around the whole drag**: the editor element drag handler begins with `var k = this.undo.startBuffering(); try{ … }` (hot region: `onDragStart(a,b,c,…,h){ if(this.store.Eo==="background"){ if(!this.Rh.A6a){ var k=this.undo.startBuffering(); try{…`). `LIVE` counts: three `onDragStart` entries executed (14/2/2) in 45 s; `get Eo` (drag-state getter) 511×; an `accumulate` instance ran 5,514× on the pointer pipeline (batched pointer moves).
- Cursor affordance comes from CSS class `_2_17VA{cursor:move}` applied to drag handles only.
- A separate long-press recognizer exists (`onPointerDown` → `setTimeout(…, N.nAa ?? 251)` → cancel/menu, `N9d.onPointerMove` cancels if moved) — 251 ms default hold. `STATIC`

**eInvite recipe (P3).** In `src/js/direct-manipulation.js` (it already has `setPointerCapture` and `beginCropDrag/moveCropDrag/endCropDrag`):

1. Centralize a `beginPointerGesture(el, { onStart, onMove, onEnd, threshold = 3 })` helper: pointerdown stores `{x,y}`, listen `pointermove/pointerup` on `window` (or capture on the element), apply dead zone, `setPointerCapture` on non-touch, `touch-action:none` on gesture surfaces.
2. Wrap *every* drag (move, resize, crop, rotate, text-handle, multi-select move) in `beginUndoTransaction(label)` / `commit()`: push **one** undo entry on first actual move (post-dead-zone), update the label with the final delta; cancel with `Escape` (pointercancel) → restore snapshot.
3. Route pointermove through the M1 batcher (latest-wins) so a 120 Hz pen doesn't re-render at 120 Hz.
4. Cursor set via classes (`.drag-handle{cursor:move}`, `.canvas.space-held{cursor:grab}` etc.), never inline per-frame style writes.
5. Keyboard parity: arrows nudge (1 px; Shift = 10 px) inside the same undo transaction coalescing window (e.g. 500 ms); `Escape` aborts an in-flight drag.

**Acceptance test.** Playwright: press on an element, move 2 px, release → treated as **click** (no transform change, no undo entry); move 30 px → drag; `Ctrl+Z` once reverts the whole drag; during drag with pointer capture, moving outside the viewport keeps the drag alive; `Escape` mid-drag restores the start position.

**Pitfalls.** Don't start undo transactions on pointerdown (pollutes history with cancelled clicks). Don't `preventDefault` pointerdown — you kill focus/IME. Keep the dead zone in *screen* px (zoom-independent feel), while the resulting world delta is divided by zoom.

### M6. Momentum, flick, velocity — `LIVE` (flick lock) + `STATIC` (velocity) + `INFER` (decay)

**What.** Pointer velocity is computed from event timestamps, not frame counts: `velocityX = dx/Δms, velocityY = dy/Δms, velocity = dist/Δms` (`STATIC`, `4c07` @≈401 k, verified quote). The wheel-flick path locks input for **250 ms** after a page switch (M4) and treats a delta stream as "still decaying" while the magnitude drop per event is `< 20` in the same direction (`g < 20` guard, M4 quote). Canva's capture window did not contain a free-form inertial pan (classic pan states never executed), so no inertia-decay constant was observed — treat decay as a design choice below (`INFER`). `[E-EXEC]`

**eInvite recipe (P5, touch-first).** `INFER`: implement flick pan explicitly and simply:

```
on pointerup: take samples from the last 100 ms → v0 (px/ms, clamp |v0| ≤ 3)
each frame:  pos += v · dt;  v *= Math.pow(0.94, dt/16.7)   // ~6 % loss per 60 Hz frame
stop when |v| < 0.05 px/ms or dt > 32 ms (frame stall); cancel on pointerdown.
```

Rules: run it inside the M1 rAF loop (one commit/frame); cap total travel distance (e.g. 1.5 × viewport); never re-enter momentum after a momentum-cancelling tap (trackpad gesture discipline from `N9d.onPointerCancel` pattern — second tap stops motion, first tap just stops without other side effects).

**Acceptance test.** Playwright: synthetic swipe with timestamps produces monotonic decaying displacement; a tap during motion stops within one frame; two consecutive swipes compose without jitter; `prefers-reduced-motion` disables inertia (see §6).

### M7. Snapping, guides, rulers, distance-measuring, margins — `STATIC`

**What.** These are **feature modules registered by name** into the editor runtime and composed from each other:

```
install_snapping        → factory v6h({canvas, pageState, …})
install_guides          → OZ({controller, canvas, …})
install_guides_ui       → S3({ guides: ZX, rulers: cSa, … })
install_rulers          → xn({canvas, pointer, selection, …})
install_margins         → lW({document, undo, …})       ← margin edits are undoable document ops
install_distance_measuring → xS({canvas, selection, …})
install_layout_ui       → HN({session, viewport, selection, …})
install_editing_surfaces→ lci({selection, skeleton, canvas, resources, …})
```

(Quote sample, byte-exact: `ua("install_distance_measuring",()=>xS({canvas:b.canvas.pj,Ta:b.tc.Ta,selection:$a.selection,qP:Wf,EF:Ea.EF,V8f:ah.V8f,No:pb.No,rz:Ib.rz,Tc:ab.Tc,Kb:Eb.Kb}))`.) `ua(name, factory)` = the runtime's feature-install registry; every capability is opt-in, gets explicit dependencies (canvas, selection, undo), and nothing reaches into globals.

**eInvite recipe (P4).**

- Build a **snap engine** as a pure function module (works in world px, tolerance converted from screen px: `tol = 6 / zoom`):
  - Candidate providers (keep additive): page edges & center; element edges/centers for all *visible* siblings; equal-spacing candidates (element between two others); grid/guides if user enabled; rulers-origin.
  - Each candidate: `{axis, kind: 'start'|'center'|'end'|'spacing', value, source}` — score by |distance|, pick best per axis, apply **sticky hysteresis** (release threshold 1.5× tolerance) so lines don't flicker.
  - Snap during drag via the M1 batcher (compute snap from *world* delta; commit snapped position once per frame).
- **Guides**: manual guides are document objects (undoable — mirror `install_margins` receiving `undo`): drag from ruler, delete by dragging back to ruler, lock toggle.
- **Rulers**: top/left, world units, tick density adapts by zoom (px-per-tick = smallest of 1/5/10/50/100 × zoom ≥ ~8 px), highlight selection extent; hide when stage < threshold size (`INFER`).
- **Distance-measuring**: while dragging (and on modifier-hold), render distance badges between the dragged element and nearest edges/nearby elements — text in px or page units; badges are `pointer-events:none` overlays (M2 rule).
- **Margins**: a page-level margin/safe-area setting stored in the document (undoable), rendered as dashed overlay.
- All overlays drawn as **absolutely positioned elements inside the transform layer’s sibling overlay layer** (never inside `#stage` itself), so hit-testing and export are unaffected.

**Acceptance test.** Playwright: drag an element near a sibling edge → it settles flush (0 px gap, within tolerance math), release → position locked; zoom to 400 % → tolerances shrink proportionally (still 6 screen px); toggling guides does not shift element geometry; margin overlay is not exported/rendered in the public renderer path (`renderer-core.js` untouched by overlays).

**Pitfalls.** Snap must be **excluded** from free rotation and text-caret drags; space-pan and zoom-gestures never snap. Keep candidates capped (e.g. nearest 100 elements) or snapping becomes the frame cost — measure with the §5 perf harness.

### M8. Scheduling & motion budgets — `STATIC` (all quotes verified)

**What.** A consistent fleet of time budgets instead of ad-hoc timers:

| Budget | Where | Value |
|---|---|---|
| Positional tween cap | `Qs.ygb(a,b,progress,150)` runner: `f=Math.min(150,f-d); …; f<150&&requestAnimationFrame(e)` | **150 ms** |
| Wheel re-arm | `SNp = dc(…, 80)` (M3) | **80 ms** |
| Wheel-end settle | `dc(…, 140)` (M3) | **140 ms** |
| Zoom commit | `Nik = dc(cc(…), 200)` (M3) | **200 ms** |
| Flick lock | `setTimeout(…, 250)` (M4) | **250 ms** |
| Long-press | `setTimeout(this.timeout, N.nAa ?? 251)` | **251 ms** |
| Page transition caps | `Math.min(400, …)` transitions | ≤ **400 ms** |
| Non-urgent work | `E4f = a => requestIdleCallback ? requestIdleCallback(a, {timeout:100}) : D4f(a); D4f = a => setTimeout(()=>requestAnimationFrame(a), 100)` | **100 ms timeout cap** |
| Render workers | worker pool `Math.min(navigator.hardwareConcurrency, 2)` (STATIC, bundle mining) | ≤ **2** |

- The 150 ms runner is the single most reusable piece: *never animate positional changes longer than 150 ms*, and drive it with `requestAnimationFrame` self-scheduling, not `setInterval`.
- **Double-rAF readiness**: heavy subtree mount signals "ready" only after two frames (`dispatch("init")` → `rAF` → `rAF` → `dispatch("ready")`, verified at `c54bf` @≈3,770,930). This makes "ready" mean *painted*, not *scheduled* — use it before measuring/animating anything right after a view change.
- Observers: `ResizeObserver` (wrapper class) for size-driven fits — no `resize`-event polling; `IntersectionObserver` with a high visibility ratio (≥ .9 observed) gates "visible enough to do work" decisions (decode, prefetch).

**eInvite recipe (P1 + P6).** Create one `editor-motion.js`-style constant block (inside an existing bundled file to respect bundle wiring):

```js
var MOTION = {
  TWEEN_MAX_MS: 150,       // positional tweens
  WHEEL_REARM_MS: 80,      // after plain wheel, re-arm ctrl-wheel zoom
  WHEEL_SETTLE_MS: 140,    // wheel gesture end
  ZOOM_COMMIT_MS: 200,     // write zoom UI state (zoom slider label) after gesture
  FLICK_LOCK_MS: 250,
  LONG_PRESS_MS: 251,
  TRANSITION_MAX_MS: 400
};
```

**Acceptance test.** Static contract test asserts the constants exist and no other file hard-codes `setTimeout` values for gestures (grep gate in the test itself). Playwright: programmatic zoom of 10× completes in ≤ 150 ms ± 1 frame.

### M9. Rendering strategy — `STATIC` (do **not** port Canva's GPU stack)

**What Canva does.** The bundle ships a full drawing stack: `getContext("webgl2"|"webgl"|"2d"|"bitmaprenderer")`, `OffscreenCanvas`, `createImageBitmap({resizeWidth, resizeHeight})` + `transferFromImageBitmap` blits for sharp live zoom of heavy media, a Skia wasm module (`web/wasm/31eefa65….wasm`), and A/B renderer flags (`useSkiaRenderer`, `useNveRenderer`, `optOutNativePdf`). A dedicated worker pool (≤2 workers) frustrates long tasks off the main thread.

**The transferable principles (eInvite recipe, P6):**

1. **Bitmap decode ahead of need.** For heavy images (photos, backgrounds): `img.decoding="async"`, call `img.decode()` for the *next* page/most-likely assets inside `requestIdleCallback(…, {timeout:100})`, and keep a decoded `ImageBitmap`/blob URL cache for zoom previews. `INFER` — matches Canva's decode/blit behavior in effect, implemented with plain DOM APIs.
2. **Never read layout inside the gesture loop.** At `pointerdown`/gesture start, cache `getBoundingClientRect()` for the active element(s) and the viewport; invalidate on gesture end / `ResizeObserver` callbacks. All per-frame math uses cached numbers.
3. **One write zone per frame.** All style writes happen in the batcher commit (M1); reads (`getComputedStyle`, `offsetWidth`) never interleave with writes. Add a dev-mode assertion: during an active gesture, any layout read triggers a `console.warn` (guarded by a `?_perfdebug=1` flag) — this catches regressions cheaply.
4. **Containment.** `#canvasViewport { contain: layout paint; }` and `contain: content` on preview tiles; keep `filter`/`backdrop-filter`/box-shadows **off** the moving transform layer; put them on static overlays only.
5. **Lazy render tiles.** For many-element pages, render offscreen (out of viewport) elements with `content-visibility: auto` (`INFER`, test thoroughly with Playwright visual diffs before keeping).
6. **Workers only if measured.** eInvite is build-tool-free and modest in scale — don't add workers preemptively; if a heavy export/adjust step appears, a single worker is enough (Canva caps at 2).

**Acceptance test.** Perf harness (§5.4): during a recorded 5 s zoom+pan gesture on a 30-element page, p95 frame time ≤ 20 ms on the CI machine and zero ≥ 50 ms frames; DevTools-style long-task observer (`PerformanceObserver('longtask')`) reports no task > 100 ms attributable to gesture code.

### M10. Telemetry & perf marks — `STATIC` (optional for eInvite)

Canva emits structured trace spans per interaction (`tracer.startRootSpan("canvas.zoom"|"canvas.scroll", headline "editor.canvas.*")`, plus a renderer perf-metrics broadcast (`c_perfMetrics.broadcastComplete`) signalled after the double-rAF ready. `INFER` for eInvite: keep it featherweight — behind a `?_perfdebug=1` flag, emit `performance.mark("einvite:zoom:start/end")` and `performance.measure` around gesture commits; expose totals on `window.__einvitePerf`. This gives the Freebuff agent (and future regression runs) a way to detect drift without shipping analytics.

### M11. Steady-state networking (heartbeat/collab) — `LIVE`

**What.** The editor keeps a session heartbeat `/…/_online?<timestamp>` driven by:

```js
HWa = function(a /*sleep*/, b /*task*/, c = qa /*clock*/){        // async while-loop
  var d = false;
  (async()=>{ for(; !d;) await c(b()), d || await a() })();
  return { cancel: ()=>{ d = true } };
};
IWa = function({initial, max, factor, jitter}){                    // backoff generator
  var g = 0;
  return () => Math.min(max, initial * Math.pow(factor, g++)) *
               (1 + (jitter - 1) * Math.random()); };
JWa = async function(url){ try{ await (await fetch(`${url}?${Date.now()}`)).text(); return true }
                           catch(b){ return false } };
```

Live: two `/_online` requests ~22–30 s apart in the 45 s window; the payload path is a plain `fetch` with a cache-busting `Date.now()` suffix; failures do **not** emit errors (fire-and-forget with boolean result feeding the backoff).

**eInvite recipe (P6).** The repo already polls CRDT updates every 800 ms (`collaboration-studio.js`: `schedulePoll(800)`; `GET /api/invitations/{id}/collaboration/v31/updates?since={lastRevision}`; a 3000 ms retry path exists). Keep the cadence, add:

1. **Jitter**: `interval = 800 * (1 + 0.1 * (Math.random()*2 - 1))` to de-synchronize multiple editors.
2. **Backoff on failure**: `min(30000, 800 * 2^failures)` with immediate retry reset on success (mirror `IWa` shape).
3. **Visibility**: `document.visibilityState` — pause polling when hidden, fire one immediate poll on `visibilitychange` → visible (users return to fresh state without a burst).
4. **Flush-then-poll on focus** if local edits are pending.

These three are architecture-aligned (the existing poller keeps durable checkpoints) and cheap to test: `tests/v52_yjs_wiring_test.py`-style wiring assertion + a timing unit test.

### M12. CSS hygiene checklist — `CSS`

Observed budgeting in the shipped stylesheet (272 KB): `will-change` ×11, `touch-action` ×9, `contain` ×13, `transition:transform` ×31, `overscroll-behavior` ×10, backdrop-filter ×10 (kept off the moving layer). Adopt:

- Gesture surfaces get `touch-action:none` **only** where a custom gesture truly owns the area (stage, crop box); everything else stays scrollable.
- Motion uses `transform` and `opacity` only; positional changes capped by M8 budgets; `transition: transform .1s linear` for programmatic hops (M2), never for gesture-driven frames.
- `overscroll-behavior: contain` on editor scroll panes to kill scroll-chaining wobble.
- `cursor` communicates mode: `move` (drag handle), `grab/grabbing` (pan), `crosshair` (creation tools), `ew/ns-resize` (handles) — never set cursor inline per-frame.

---

## 4. The eInvite implementation plan (phases P1–P6)

Work strictly in order; each phase ends with **build → tests → evidence capture → commit**. Never bundle two phases in one commit. If a phase regresses budgets/tests, fix forward or revert to the last green checkpoint.

### P1. Input core: frame batcher + motion budgets

| | |
|---|---|
| **Files** | `src/js/editor-pro.js` (primary home), `src/css/editor-pro.css` (only if needed), `tests/canvas_motion_contract_test.py` (new, mirrors repo contract-test style) |
| **Steps** | 1. Add `createFrameBatcher(reduce, commit)` (M1) + `MOTION` constants + `debounce(fn, ms)`. 2. Route existing wheel-zoom handling and any pointer-move handlers (drag preview, crop) through batchers — behavior-neutral refactor first. 3. `visibilitychange` → `flush()`. |
| **DoD** | `python3 build.py all` then `python3 build.py bundles --check` byte-stable relative to intended change; existing pytest suite count unchanged; new contract test asserts batcher + constants in the built `editor-suite.js`. |
| **Evidence** | Playwright burst test (30 wheel events → ≤ frames commits); attach output to `artifacts/`. |
| **Commit** | `editor: frame-aligned input batching + motion budgets (P1)` |

### P2. Transform viewport: single composited layer + zoom model

| | |
|---|---|
| **Files** | `src/html/index.html` — the designer workspace page (`#stage`, `#canvasViewport`, `#zoomLevel` live there; wrap `#stage` in `#stageTransform`), `src/js/editor-pro.js` (`view` state, `applyView()`, `setZoom`, `zoomToPoint`, slider mapping), `src/css/editor-pro.css` (layer rules per M2), `src/js/canvas-plus.js` (mount points adapting to the new wrapper) |
| **Steps** | 1. Layer split per M2 with exact discipline (origin 0 0, one transform writer, overlay layer as sibling for guides/marquee). 2. `view = {x,y,zoom}` + `applyView()` writing `translate3d(x,y,0) scale(z)`; clamp `[0.1,5]`. 3. Zoom-to-cursor invariant math (M3). 4. Slider ↔ zoom log mapping (`log2(z+10)` scale) keeping `#zoomLevel` and `currentZoom()` API intact. 5. Buttons/keys: `+`, `-`, `Ctrl+0` (100 %), `Shift+F`/`F` (fit) via the 150 ms tween. 6. Cache rects at gesture start (M9.2). |
| **DoD** | Hit-testing (`objectAtPoint`), creation tools, and selection stay accurate at 10 %/100 %/400 %; keyboard operable; visual regression (`tests/visual_regression.py`) green; zoom-to-cursor invariant test green. |
| **Commit** | `editor: composited transform viewport + zoom model (P2)` |

### P3. Drag pipeline: dead zone, capture, undo coalescing

| | |
|---|---|
| **Files** | `src/js/direct-manipulation.js` (gesture helper + migrate move/crop/text-handle drags), `src/js/app.js` (undo transaction API on the document model), `src/js/editor-pro.js` (multi-select move) |
| **Steps** | M5 recipe: `beginPointerGesture(el, {onStart,onMove,onEnd,threshold:3})`; `setPointerCapture` non-touch; moves via batcher; `beginUndoTransaction`/`commit` around every object mutation; `Escape`/`pointercancel` abort; keyboard nudge in same transaction window; cursor classes. |
| **DoD** | 2 px move = click (no undo entry); 30 px move = one undo step; capture keeps drag outside viewport; Escape restores; all existing direct-manipulation tests pass. |
| **Commit** | `editor: dead-zone drag pipeline with undo transactions (P3)` |

### P4. Snapping engine + guides/margins/measurement overlays

| | |
|---|---|
| **Files** | `src/js/editor-pro.js` (engine + overlays), `src/css/editor-pro.css` (overlay styles), `src/js/editor-builders.js` only if schedule/venue builders share snapping needs |
| **Steps** | M7 recipe: pure snap module; page/sibling/spacing candidates; 6 px screen tolerance + hysteresis; guide objects (undoable) + rulers; distance badges during drags; margins as document property with overlay. |
| **DoD** | Snap flush-to-edge test; tolerance scales with zoom; overlays never intercept pointer events nor appear in exports; drag perf harness still p95 ≤ 20 ms with snapping on. |
| **Commit** | `editor: snapping engine + guide/margins overlays (P4)` |

### P5. Wheel semantics + pan + flick

| | |
|---|---|
| **Files** | `src/js/editor-pro.js` (wheel branch), `src/js/direct-manipulation.js` (space/middle pan), `src/css/editor-pro.css` (cursors) |
| **Steps** | M3+M4+M6 recipes: deltaMode normalization; ctrl/cmd-wheel batched zoom with ±25/event cap; plain wheel = scroll; 80/140/200 ms settle constants; space-held + middle-click pan, contextmenu suppressed while panning; touch flick with explicit decay + cancel-on-tap; `prefers-reduced-motion` → no inertia, no 150 ms tweens. |
| **DoD** | Zoom-to-cursor invariant (≤1 px); no accidental page scroll while zooming; pan is 1:1 (≤1 px error); wheel never triggers navigation unless the edge-paging feature flag is explicitly enabled (default OFF). |
| **Commit** | `editor: wheel/pan/flick interaction semantics (P5)` |

### P6. Perf hygiene + steady-state networking + budgets

| | |
|---|---|
| **Files** | `src/js/collaboration-studio.js` (poller), `src/js/editor-pro.js` (perf marks under `?_perfdebug=1`), docs (short `docs/CANVAS-MOTION.md` summarizing the adopted mechanisms and where they live) |
| **Steps** | M9 decode-ahead warmup; M11 jitter/backoff/visibility for the CRDT poller; perf marks; run route budgets (`v55_route_weight_budget_test.py`) and weight audit (`tools/`); final pass over the M12 checklist. |
| **DoD** | Full `pytest tests/` (no new failures beyond the repo’s known-failing baseline recorded in `plans/003`), budget tests green, visual regression green, perf harness numbers recorded to `artifacts/`, docs file added. |
| **Commit** | `perf: decode-ahead + resilient collab poller + budgets (P6)` |

### Things you must NOT do

- No frameworks, bundlers, transpilers, or new runtime dependencies; no CSS-in-JS; no TypeScript.
- No `innerHTML`/`eval` in editor code; CSP stays strict.
- Do not port Canva's WebGL/Skia renderer, virtualized filmstrip, or its React state architecture.
- Do not add timers with magic numbers outside `MOTION` (the contract test enforces this for gesture paths).
- Do not touch public renderer output (`renderer-core.js` / `advanced-public-renderer.js`) in a way that changes exports — editor chrome and public rendering must stay in sync (same source of truth).
- Never commit with `build.py bundles --check` failing unless the bundle change is intended — then regenerate mirror + manifests in the same commit.

---

## 5. Verification protocol (run before every commit)

### 5.1 Build & static gates (repo root, always)

```bash
python3 build.py all                 # regenerate editor bundle, route bundles, manifests, mirror
python3 build.py bundles --check     # byte-identity gate — must pass with intended outputs
pytest tests/ -q                     # full suite; compare against the known-failing baseline
                                     # (plans/003: 236 scripts, 170 pass, 58 remain failing — do not
                                     #  introduce NEW failures; never "fix" by deleting/loosening)
node tools/page-errors.mjs --all     # console/page-error smoke (as configured in the repo)
```

If your change is intended to alter bundle bytes, regenerate **editor bundle + route bundles + manifests + mirror in the same commit** and update any byte-pinned contract test deliberately, noting why in the commit message.

### 5.2 Interaction correctness (Playwright, per phase)

Follow the existing pattern (`tests/browser_runtime.py` launches Chromium and exposes geometry; `tests/visual_regression.py` diffs screenshots). Add `tests/canvas_motion_playwright.py` (or extend the visual-regression runner) with at minimum:

1. **Zoom-to-cursor invariant** (P2/P5): pick a world point, record its client rect, ctrl+wheel 10 steps at that pixel, assert the rect returns to the same client position ±1 px after each commit.
2. **Batching bound** (P1): dispatch 30 wheel events within ~2 frames; count transform commits via MutationObserver; assert commits ≤ frames + 1.
3. **Click-vs-drag** (P3): 2 px move → no undo entry; 30 px → exactly one undo entry; `Ctrl+Z` restores.
4. **Snap** (P4): drag near a sibling edge → final gap 0 ± rounding; zoom 400 % → still snapping at ~6 screen px.
5. **No layout shift** (P2/P6): `PerformanceObserver('layout-shift')` empty during gestures; CLS contribution 0.
6. **Keyboard parity** (P2/P3/P5): `+`/`-`/`Ctrl+0`/fit keys, arrow nudges, `Escape` abort — all reachable without a pointer.
7. **Reduced motion** (P5/P6): emulate `prefers-reduced-motion` → no inertia, tween duration 0.

### 5.3 Visual regression

Any change that alters editor chrome or geometry runs the repo's visual regression flow and attaches before/after screenshots to `artifacts/canvas-motion/<phase>/`. Treat diffs > threshold as failures unless the phase intentionally changes the look — then regenerate baselines in a dedicated commit.

### 5.4 Perf harness (new, once, reused by every phase)

Write `tools/canvas-motion-perf.mjs` (node + Playwright, pattern of existing `tools/` scripts; output JSON to `artifacts/`):

- Records rAF delta times while scripting: (a) 60 ctrl+wheel events, (b) 2 s pan drag, (c) element drag with snapping on a 30-element page, (d) crop drag on a large image.
- Emits: frame count, p50/p95/p99 frame ms, long tasks (`PerformanceObserver('longtask')`), commit count per gesture, and a simple "input→first painted transform" latency proxy.
- **Budget**: p95 ≤ 20 ms, no task > 100 ms, commits ≤ 1.2 × frames. CI variance: run 3×, use best-median; store all three runs.

### 5.5 Evidence discipline

Every phase commit message includes: phase id, files, and the measured numbers (perf JSON path + regression result). The Freebuff agent keeps a running ledger `artifacts/canvas-motion/ledger.md` (what is done, numbers, screenshots, open issues) so a fresh session can recover state without re-discovery.

---

## 6. Instructions for the Freebuff agent (design & execution protocol)

You are acting as the studio’s design lead **and** the implementer. The product already has an identity; your job is to make the canvas feel inevitable — precise, calm, physical — and to keep the implementation honest to the evidence in this brief.

### 6.1 Design direction — “drafting-table calm”

Ground everything in the subject: an eInvite invitation is a piece of paper someone will keep. The editor should feel like a **bookbinder’s drafting table**: quiet surfaces, precise instruments, and one expressive layer (the invitation itself).

- **Palette (editor chrome only — invitation content keeps its own themes):** paper `#FAF9F6`, ink `#17181C`, instrument gray `#6E7278`, verdigris accent `#3E7C6B` (selection/active tool), wax red `#B23A48` (destructive/errors only), guide blue `#3B6FB6` (measured overlays: guides, distance badges, margins). Do **not** drift into the cream+serif+terracotta template look; keep chrome neutral so the user’s design carries the color. Map these onto the repo's existing CSS custom properties/classes first (`src/css/`) — the hexes above are accent targets only where no token exists.
- **Type:** keep the existing bilingual typography architecture. Chrome/UI text uses the project’s UI sans at a clear 3-step scale (12/14/16); numbers in rulers and distance badges use the utility face with tabular figures (`font-variant-numeric: tabular-nums`) — they must not jitter while changing.
- **Signature element:** the **measurement layer** — distance badges and guides rendered like drafting instruments (thin lines, small tabular numbers, no shadows, 1 px hairlines that stay 1 px at any zoom by counter-scaling). This is the one memorable thing; keep everything around it quiet. It is also functionally the piece users will screenshot when they show off precision.
- **Structure encodes truth:** tool rail stays iconic + labeled on hover; the zoom control uses the log-scale slider (M3) so *equal slider travel = equal visual change* — that is information, not decoration. No decorative numbering, no ornamental dividers.
- **Motion:** only where it explains causality — selection outline settles in 120 ms, zoom commit badge in ≤150 ms, no bounces, no spring overshoot in chrome. The canvas itself moves only 1:1 with the user’s input (or the explicit 150 ms tween). Respect `prefers-reduced-motion` by removing inertia and tween durations, not by removing functionality.

### 6.2 Interaction language (canonical behaviors — implement exactly; rows tagged `INFER` are this brief's design calls, not Canva observations)

| Input | Behavior |
|---|---|
| Ctrl/Cmd + wheel | Zoom, cursor-anchored, per-frame factor ≤ ±19 %, absolute clamp `[0.1, 5]`, 200 ms commit of UI readouts |
| Plain wheel / trackpad | Scroll/pan as the platform expects; never hijacked |
| Space + drag, middle-drag | Pan (grab/grabbing cursors); context menu suppressed only while panning |
| Drag element | 3 px dead zone → drag; capture pointer; one undo step per gesture; `Escape` aborts |
| Arrow keys (element selected) | Nudge 1 px; Shift = 10 px; coalesced into one undo step within 500 ms |
| `+` / `-` / `Ctrl+0` / `F` | Zoom in / out / 100 % / fit |
| Hold `Alt` during drag | Temporarily disable snapping `INFER` (escape hatch users expect from design tools) |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo — one entry per transaction (drag, nudge burst, guide move, margin change) |

Focus is always visible (2 px verdigris ring, 2 px offset, never removed for aesthetics); every pointer gesture has a keyboard equivalent; hit targets ≥ 24 px in chrome.

### 6.3 Copy rules (interface voice)

Sentence case; verbs first (“Zoom in”, “Fit to screen”, “Add guide”). One name per concept everywhere (the thing is a “guide”, in the ruler, the tooltip, and the docs). Errors say what happened and how to fix it, in the interface’s voice: “Couldn’t save that change — check your connection, then try again.” Empties are invitations: the canvas empty state says what to do, with the first action focused. All new strings delivered in EN and KH (rule #5).

### 6.4 Long-running execution protocol

1. **Start** by reading this brief end-to-end, then the recon (`_rea-canva/einvite-recon.md`), then the repo’s `docs/ARCHITECTURE.md`. Confirm the current test baseline before touching code (`pytest tests/ -q`, record count).
2. Execute **P1 → P6 in order**. Never start phase N+1 with phase N’s gates red.
3. **Per phase loop:** implement → `build.py all` → static gates (§5.1) → interaction tests (§5.2) that exist for that phase → perf harness (§5.4) → visual regression (§5.3) → update `artifacts/canvas-motion/ledger.md` → single commit with the phase id. If a gate fails: fix forward up to 3 attempts, else revert to the last green state and open an issue note in the ledger.
4. **Stop conditions (ask the human, don’t guess):** a product decision that changes user-visible defaults (e.g., enabling wheel edge-paging), a budget conflict that requires dropping a feature, any change to public rendering output, or two consecutive failed attempts at the same gate.
5. **Checkpointing:** every commit must leave the repo green (baseline-equal). The ledger is the recovery point for a new session: it states the current phase, last green commit, open issues, and measured numbers.
6. **Definition of done (whole brief):** all six phases committed; §5 gates green vs baseline; perf budget met in `artifacts/`; zoom-to-cursor, batching-bound, click-vs-drag, snap, no-layout-shift, keyboard-parity, and reduced-motion tests exist and pass; `docs/CANVA-MOTION.md` (short) explains where each mechanism lives and how to measure it.
7. **When uncertain, prefer the smallest mechanism that satisfies the evidence.** The smoothness comes from discipline (one layer, one commit per frame, bounded timers), not from machinery.

---

## 7. Appendix

### 7.A Evidence index (alias → full REA evidence id)

| Alias | Evidence id | What it is |
|---|---|---|
| E-ASAR | `ev_5823753095644af23c60030f9592093f3b0831428f0f0d479b858394c1ee836e` | app.asar static analysis result (T1; shell-only finding) |
| E-RUN1 | `ev_29e401e1f6025ff2822ce4d97821e6228ca14f526a6daa066476d6fe152c23e6` (parent `ev_c65a1c05208aaba4bd3b55ed5e541662c098b162ace0e7a99033a08d5d69a0c7`) | JS application analysis, all 33 web scripts |
| E-RUN2 | `ev_ac27017de8f32b8d7eab85f4d8c92f58f8f771688055805f62dcfe45311ab528` (parent `ev_facb5083b69470bf1fb0c642ff597620c9b247bc443366de3ca4b7e092c09ac4`) | JS application analysis, 4 big bundles, static-complete |
| E-TARGETS | `ev_61cedf53195bfccd38b7689b923ed7e4e13e4015756e0b71dbaa8aad5224747d` | CDP target inventory (editor target id) |
| E-PAGE1 | `ev_ee0b7485d3442ac5445d38d683fe5354068736b925f62a08296738ebfde24060` | web page inspection #1 (1,694 DOM nodes; origin-filter lesson) |
| E-PAGE2 | `ev_9bf3083f5454fea0abb30f62262f927d47662f6d05c230a504023f9d42eec47e` | web page inspection #2 (34 scripts, 46 resources) |
| E-PAGE3 | `ev_5e7f5182509b9d76de2f69f96ee93e593f8b1989f835379e950aac9665914ee9` | web page inspection #3 with script sources (input to script export) |
| E-BUNDLE | `ev_eb89dfeb3d45dc3d8d32feb3e3c5a07e1d6ba95c49f5759591b4c3e8b12e014b` | bundle-level web analysis |
| E-SCRIPTS | `ev_0ab4e07085561baa52dc4878cc5a1b44c04f94d651e7cd6d74c1b6a6e5df2760` | `export_web_scripts` — 34 script sources retained |
| E-EXEC | `ev_3d6d3a69705da0268df8b7111ab7c967dbb0e0a9f68cc87ad86bbd21fbae90c5` | **45 s live execution observation** (coverage ranges/counts, requests) |
| E-SHOT0 | `ev_e3d4ca19b2f3358a1d31746cf775c67637f27d45b2eb86a477bbd39d4832198b` | editor screenshot 999×757 (early session) |
| E-SHOT1 | `ev_4f9fb2c1ef7258ccbc61bb91a7fb37788830c871d34a08529cd48937e4570f06` | live window start screenshot 1920×1154 |
| E-SHOT2 | `ev_2cf36e1cfe0d53d62e90dd6f92b687c15c2f531001539ca756d1828f98f4dcf5` | live window end screenshot 1920×1154 |
| E-LIST-C | `ev_41974af72722c688d04e99dd9ffb6ca70a447925aa7daf2bb8fd1eee47442c7e` | event listeners on canvas (0) |
| E-LIST-H | `ev_7964d2c56ea28826edb84c94170bcb065a467edc15870d3f46a71e0d8bea668e` | event listeners on `<html>` (4) |
| E-LIST-M | `ev_e6906bb9d05e0d1f1c76fbaa728242ceaff920cd566fd142f1daff960115c27c` | event listeners on layer marker element |
| E-LIST-B1 | `ev_369de62bec7f0b55aba247396f2dac05e7472525d4895a15a61546a32b699cad` | listener inventory (body surface; Sentry-wrapped) |
| E-LIST-B2 | `ev_63f0f6e99e879d4b135aac1e2a4cb07a093e33f683a0563629136cf6c77075bf` | listener inventory (body surface; Sentry-wrapped) |
| E-FUSES | `ev_07407462cf4a63727f7cb8bcf461aae0f09a4c550cb3733f739aaafb1fd5d48d` | Electron fuse inspection |

Session bundle: `rea-web-bundle.json` (64 records, 394,766,456 B) holds every record above; the alias→id mapping was extracted programmatically from those records (`E-RUN1`/`E-RUN2` ids are the analysis results referenced by their parent records; see `progress.md`). Evidence for every LIVE count in this brief: `captures/exec-observation-0.json` (32 MB); counts reproduced by `corr-exec.mjs` / `probe-values.mjs` with the documented filter (non-block ranges, `count>0`), union of executed intervals for unit coverage. Full artifact list: §7.C.

### 7.B Minified-symbol glossary (for re-mining the sources)

| Symbol | Meaning (verified) |
|---|---|
| `o4e` | `2**.01` — zoom step base (factor `o4e ** -clamp(Δ, ±25)`) |
| `wk(a,b,c)` | `Math.min(c, Math.max(b,a))` — clamp |
| `dc(fn, ms)` | debounce (wheel 140, re-arm 80, zoom commit 200) |
| `cc` | bound-method / wrapped callback helper |
| `n4e` | frame batcher (accumulate → `requestAnimationFrame` → commit) |
| `a5e` | ctrl-wheel zoom controller (`eBj` attach, `Mik` handler, `lMh` apply, `Nik` 200 ms commit, `SNp` 80 ms re-arm, `egk` passive pass-through) |
| `Nmb` | page-scroll wheel handler (native `scrollBy`, 75/1000 accum thresholds, 250 ms flick lock `dZl`, rAF scroll-restore on `prev`) |
| `Gkb(el, level, cap)` | scrollable-ancestor finder (overflowY auto/scroll + scrollHeight check) |
| `HWa/IWa/JWa` | heartbeat loop / backoff curve / `fetch(url?Date.now())` |
| `t1j` | zoom ↔ slider log mapping (`log2(z+10)`, 0..40) |
| `Qs.ygb` | timeline tween evaluation used by the 150 ms cap runner |
| `mxh` | classic canvas mount (wheel `Q`, pan/pinch handlers, touch set) |
| `L9d`/`M9d` | drag/pan controller classes (`onStart/onMove/onEnd`) |
| `WSa` | pinch/gesture filter (allow native pinch only for `pinch-zoom`/`auto` gesture sets) |
| `ZYa`/`S0` | pan-state arming (`space_pan`, `middle_click_pan`, `right_click_pan`, `touchscreen`) |
| `$Sa` | event-velocity factory (`velocityX/velocityY/velocity` per ms) |
| `ua(name, factory)` | feature-module registry (`install_snapping`, `install_guides`, `install_guides_ui`, `install_rulers`, `install_margins`, `install_distance_measuring`, `install_layout_ui`, `install_editing_surfaces`) |
| CSS: `_8F7d0w`, `I9M93w`, `G0knkQ`, `vALUZQ`, `_2_17VA` | fixed layer / transform layer / gesture surface / gesture surface / drag cursor (see M2) |

### 7.C Local artifact inventory (`F:\Project\eInvite\_rea-canva\`)

- `progress.md` — execution ledger; `plan.md` — task plan; `einvite-recon.md` — repo recon.
- `web-scripts-js/` — 33 file-backed editor JS bundles (byte-identical to `static.canva.com`); `web-scripts/manifest.json` — export manifest (34 script sources incl. 1 anonymous inline script; also indexes the Skia wasm and GTM container URL).
- `css/` — 8 fetched `.ltr.css` (incl. main `feb52ee2f9d8fe7a.ltr.css`).
- `captures/` — `exec-observation-0.json` (E-EXEC full), `exec-intervals.json` (executed interval map), `live-wheel-paths.txt` (annotated quotes), `editor-viewport.png`, `shot-4f9fb2c1.png`, `shot-2cf36e1c.png`, plus earlier capture extracts.
- `contexts-dump.txt` — mined minified-code contexts; probe scripts: `mine-keywords.mjs`, `mine-contexts.mjs`, `events-probe.mjs`, `mining2.mjs`, `ws3.mjs`, `backend-probe.mjs`, `classify-sources.mjs`, `dom-mine.mjs`, `extract-web-capture.mjs`, `extract-exec.mjs`, `corr-exec.mjs`, `corr2-exec.mjs`, `extract-snips.mjs`, `probe-values.mjs`, `probe2-values.mjs`, `verify-quotes.mjs`, `verify-quotes2.mjs`.
- `rea-web-bundle.json` — full 64-record session evidence bundle.
- `canva-smoothness-brief.md` — this document.

### 7.D Limitations and open questions

**Limitations you must keep honest when citing this brief:** see §2.2 (nine items) — JIT-disabled window, non-summable nested counts, main-frame/world only, no chronology, budget cutoffs, clock skew, empty source maps, CSS fetched outside REA, semantic heap cap (4 GiB) on the four largest bundles. Additionally: the classic canvas wheel/pan/pinch paths (`mxh` mount and its pan-state machine) were **not exercised** in the capture window — they stay STATIC; Sentry masks listener source locations; the 45 s window represents one "Website"-type design session (editor chrome mechanisms generalize, design-type specifics may not).

**Open questions (resolve in-phase, don't guess):**

1. Should wheel edge-paging (M4) ship in eInvite? Default recommendation: **OFF** until the product is visually paginated.
2. Nudge-undo coalescing window (proposed 500 ms) — confirm against eInvite UX.
3. `content-visibility: auto` for offscreen elements (M9.5) — keep only if visual regression stays exact.
4. KH IME composition + batcher flush interplay: ensure `compositionstart/end` flush correctly during text editing (test with a Khmer IME path).
5. Does eInvite want the log-scale zoom slider (M3) replacing any existing linear control? (recommended: yes, matches equal-travel-equal-change)

*End of brief — v1 DRAFT for independent review.*





