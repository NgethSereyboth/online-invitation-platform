/**
 * forced-layout-attribution.mjs — name the JS call sites that force synchronous layout.
 *
 * Why this exists
 * ---------------
 * `tools/perf-trace-compare.py` measured that index.html emits 111 `Layout`
 * trace events against Canva's 37, and that 77 of them are nested inside a
 * script event (the forced-layout proxy) against Canva's 6.
 *
 * CORRECTION (this header used to say the opposite). It claimed "Chrome attaches
 * no `args.stackTrace` to Layout events even with
 * `disabled-by-default-devtools.timeline.stack` ... enabled". That was a reader
 * bug, not a capture limitation: the stack is attached to the event's own data
 * dictionary, so it lands at `args.beginData.stackTrace`, and the count of such
 * events on index.html is 79 of 107 — i.e. essentially every Layout event that
 * the nested-in-script proxy calls forced. The trace therefore CAN name the
 * calling function; `tools/layout-stack-attribution.py` does exactly that, and it
 * is the cheaper first question to ask.
 *
 * This tool still answers a question the trace cannot: whether a *read of layout
 * geometry while the DOM is dirty* occurs, including reads that coalesce into an
 * already-pending frame and therefore cost nothing (`--exercise` measures one
 * interaction, not the load). A trace shows where layout time actually went; this
 * shows where a forced read could have gone. Use the trace to rank, this tool to
 * confirm.
 *
 * Chromium sources for the category and the stack attachment:
 *   https://chromium.googlesource.com/chromium/src/+/main/base/trace_event/builtin_categories.h
 *   https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/core/inspector/inspector_trace_events.cc
 *
 * How the detector works (the classic algorithm, stated plainly)
 *   A forced synchronous layout is a *read of layout geometry while the DOM is
 *   dirty*. So this tool instruments both halves:
 *     writes  style/className/innerHTML/textContent/attribute setters,
 *             appendChild/insertBefore/removeChild, classList — set `dirty = true`
 *     reads   getBoundingClientRect, getClientRects, the offset/scroll/client
 *             geometry getters, getComputedStyle, innerText — if `dirty` was
 *             true, that call is a
 *             forced layout: record the call site and clear `dirty`
 *   `dirty` is also cleared when a rAF callback runs, since the engine lays out
 *   at frame time anyway and the next read is then free.
 *
 * The connectivity guard (a correction made because the first measurement was wrong)
 *   The first version flagged every read while dirty, and reported a rich-text
 *   sanitizer (`renderer-core.js` cleanNode/plainText/sanitizeRichText, ~180
 *   "forced" reads) as the worst offender. That was a detector artefact: the
 *   sanitizer builds a *detached* `<template>`/`<div>`, and a detached subtree
 *   never participates in layout, so its `textContent`/`innerHTML` reads are
 *   free. A read now only counts as forced when the receiver is connected to the
 *   document (`this.isConnected`). The artifact keeps the unguarded count too, so
 *   the two numbers can be compared rather than the correction simply asserted.
 *
 * What it is not
 *   It still reports an *upper bound on candidates*, not a trace of real engine
 *   layouts: a read on a connected node while dirty may coalesce with a pending
 *   frame and cost nothing. It finds call sites worth looking at;
 *   `tools/perf-trace-compare.py` is what confirms a change removed real work.
 *   Reads through getters that are not wrapped here are invisible, and the
 *   report says so.
 *
 * Only the first stack frame that belongs to the *page* is recorded. The probe
 * itself is injected with evaluateOnNewDocument, so its own frames are
 * `<anonymous>:line:col`; the first version of this tool reported those and
 * named the probe instead of the caller. Frames are therefore matched against a
 * URL-ish shape, and that filter is the whole point of the `callsite` helper.
 *
 * --exercise: measure an INTERACTION, not just the load
 *   A load-time count only sees the load. The first fix this tool justified was a
 *   per-keystroke search filter that thrashed layout on every input event; the
 *   load-time number did not move, because the load path never types. `--exercise`
 *   zeroes the counters after the page settles, types into a selector one
 *   character at a time (real input events), and reports only the counters that
 *   interaction produced. `--exercise=sq=.studio-panel-search input` sets the text
 *   to type (default `and`).
 *
 * Usage
 *   node tools/forced-layout-attribution.mjs http://127.0.0.1:8124/index.html --top=15
 *   node tools/forced-layout-attribution.mjs [url] --exercise=.studio-panel-search input
 *   node tools/forced-layout-attribution.mjs [url] --settle=4000 --json
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, argValue, hasFlag, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const RAW_URL = argv.find((a) => !a.startsWith('--'));
const TARGET_URL = urlFromArg(RAW_URL || 'index.html');
const TOP = Number(argValue(argv, 'top', 20));
const SETTLE = Number(argValue(argv, 'settle', 4000));
const LABEL = String(argValue(argv, 'label', 'run'));
const AS_JSON = hasFlag(argv, 'json');
// --exercise=<selector>  measure only what an interaction costs: zero the probe,
// type <text> into the selector with real input events, read the deltas.
const EXERCISE = argValue(argv, 'exercise', null);
const EXERCISE_TEXT = String(argValue(argv, 'exercise-text', 'and'));

// NOTE: this whole probe is a template literal, so a backslash inside it would be
// eaten by the template. Newlines are therefore expressed as
// String.fromCharCode(10) rather than an escape sequence.
const PROBE = `(() => {
  const counts = new Map();
  const state = { dirty: false, writes: 0, reads: 0, forced: 0, forcedDetached: 0, wrapErrors: 0 };
  window.__forcedLayoutProbe = { counts, state };
  const NL = String.fromCharCode(10);

  const isPageFrame = (frame) => /\\/\\//.test(frame) || /^[^\\s()]+\\.(js|mjs|html|css)[:(]/.test(frame);

  const callsite = () => {
    try {
      const raw = (new Error().stack || '').split(NL);
      const frames = [];
      for (const line of raw) {
        const f = line.trim().replace(/^at\\s+/, '');
        if (!f || f === 'Error') continue;
        if (f.indexOf('<anonymous>') !== -1) continue;
        frames.push(f);
      }
      for (const f of frames) if (isPageFrame(f)) return f.slice(0, 220);
      return frames.length ? frames[0].slice(0, 220) : '(unknown)';
    } catch (e) { return '(stack unavailable)'; }
  };

  const bump = (site, key) => {
    let row = counts.get(site);
    if (!row) { row = { forced: 0, detached: 0, reads: 0, writes: 0 }; counts.set(site, row); }
    row[key] += 1;
  };

  // A read can only force a layout when its receiver is connected to the
  // document: a detached subtree has no boxes, so its geometry reads are free.
  // The helper is tri-state (true / false / null for "not an element") so a
  // window read is not silently treated as detached.
  const connected = (target) => {
    if (target === window || target === document) return true;
    if (!target || typeof target !== 'object') return true;
    if (!('isConnected' in target)) return null;
    return !!target.isConnected;
  };

  const recordRead = (target) => {
    state.reads += 1;
    const site = callsite();
    bump(site, 'reads');
    if (!state.dirty) return;
    state.dirty = false;
    if (connected(target) === false) {
      state.forcedDetached += 1;
      bump(site, 'detached');
      return;
    }
    state.forced += 1;
    bump(site, 'forced');
  };
  const recordWrite = () => {
    state.writes += 1;
    state.dirty = true;
    bump(callsite(), 'writes');
  };

  const wrapMethod = (holder, name) => {
    if (!holder || typeof holder[name] !== 'function') return;
    const orig = holder[name];
    holder[name] = function () { recordRead(this); return orig.apply(this, arguments); };
  };
  wrapMethod(Element.prototype, 'getBoundingClientRect');
  wrapMethod(Element.prototype, 'getClientRects');
  wrapMethod(Range.prototype, 'getBoundingClientRect');
  wrapMethod(Range.prototype, 'getClientRects');
  wrapMethod(Element.prototype, 'scrollIntoView');
  wrapMethod(Document.prototype, 'elementFromPoint');
  wrapMethod(Document.prototype, 'elementsFromPoint');
  wrapMethod(window, 'getComputedStyle');

  // Only properties whose *read* can require layout. Two corrections, both made
  // after a wrong first measurement: id and className reads are pure attribute
  // lookups, and window's innerWidth/scrollX/scrollY are viewport values — none
  // of them forces a layout. innerText does (it needs rendered text), and the
  // geometry getters do. id/className stay in the write list below.
  const readGetters = [
    [HTMLElement.prototype, ['offsetWidth','offsetHeight','offsetTop','offsetLeft','offsetParent','clientWidth','clientHeight','clientTop','clientLeft','innerText']],
    [Element.prototype, ['scrollWidth','scrollHeight','scrollTop','scrollLeft','clientWidth','clientHeight','innerHTML']],
  ];
  for (const [proto, props] of readGetters) {
    if (!proto) continue;
    for (const prop of props) {
      const desc = Object.getOwnPropertyDescriptor(proto, prop);
      if (!desc || typeof desc.get !== 'function') continue;
      const self = proto;
      const next = {
        configurable: true,
        enumerable: desc.enumerable,
        get() { recordRead(self === window ? window : this); return desc.get.call(this); },
      };
      if (typeof desc.set === 'function') next.set = function (v) { recordWrite(); return desc.set.call(this, v); };
      try { Object.defineProperty(proto, prop, next); } catch (e) { state.wrapErrors += 1; }
    }
  }

  const writeMethods = [
    [Element.prototype, ['setAttribute','removeAttribute','toggleAttribute','insertAdjacentElement','insertAdjacentHTML','insertAdjacentText','scrollTo','scrollBy','append','prepend','replaceChildren','remove','after','before']],
    [Node.prototype, ['appendChild','insertBefore','removeChild','replaceChild']],
    [DOMTokenList.prototype, ['add','remove','toggle','replace']],
    [CSSStyleDeclaration.prototype, ['setProperty','removeProperty']],
  ];
  for (const [proto, methods] of writeMethods) {
    if (!proto) continue;
    for (const m of methods) {
      if (typeof proto[m] !== 'function') continue;
      const orig = proto[m];
      proto[m] = function () { recordWrite(); return orig.apply(this, arguments); };
    }
  }

  // innerHTML/outerHTML write a subtree (a style invalidation); textContent writes
  // text; className/id are attribute writes. All four are writes. Only innerHTML
  // and textContent are also layout-*forcing reads*, so they get a getter; id and
  // className are attribute lookups and must not be counted as reads — wrapping
  // their getter reported a DOM-walking helper as the hottest forced-layout site.
  for (const prop of ['innerHTML','outerHTML','textContent','className','id']) {
    for (const proto of [Element.prototype, Node.prototype]) {
      const desc = Object.getOwnPropertyDescriptor(proto, prop);
      if (!desc || typeof desc.set !== 'function') continue;
      const next = {
        configurable: true,
        enumerable: desc.enumerable,
        set(v) { recordWrite(); return desc.set.call(this, v); },
      };
      if (typeof desc.get === 'function' && (prop === 'innerHTML' || prop === 'outerHTML' || prop === 'textContent')) {
        next.get = function () { recordRead(this); return desc.get.call(this); };
      } else if (typeof desc.get === 'function') {
        next.get = function () { return desc.get.call(this); };
      }
      try { Object.defineProperty(proto, prop, next); } catch (e) { state.wrapErrors += 1; }
    }
  }

  const raf = window.requestAnimationFrame;
  if (typeof raf === 'function') {
    window.requestAnimationFrame = function (cb) {
      return raf.call(this, function (t) { state.dirty = false; return cb(t); });
    };
  }
})();`;

const browser = await launch({ kind: 'full' });
const page = await newPage(browser, { width: 1440, height: 900 });
let navigationError = null;
await page.evaluateOnNewDocument(PROBE);
try {
  await page.goto(TARGET_URL, { waitUntil: 'load', timeout: 60000 });
} catch (e) {
  navigationError = String(e && e.message ? e.message : e);
}
await page.waitForNetworkIdle({ idleTime: 1000, timeout: SETTLE }).catch(() => {});
await new Promise((r) => setTimeout(r, SETTLE));

let exerciseError = null;
if (EXERCISE) {
  // Zero the probe, then type. Everything counted after this point was caused by
  // the interaction, which is the only honest way to measure a per-input fix.
  await page.evaluate(() => {
    const p = window.__forcedLayoutProbe;
    if (p) {
      p.counts.clear();
      Object.assign(p.state, { dirty: false, writes: 0, reads: 0, forced: 0, forcedDetached: 0, wrapErrors: 0 });
    }
  });
  try {
    const handle = await page.$(String(EXERCISE));
    if (!handle) throw new Error(`no element matches ${EXERCISE}`);
    await handle.click({ clickCount: 3 }).catch(() => {});
    await handle.type(EXERCISE_TEXT, { delay: 60 });
    await page.keyboard.press('Backspace');
  } catch (e) {
    exerciseError = String(e && e.message ? e.message : e);
  }
  await new Promise((r) => setTimeout(r, 400));
}

const snapshot = await page.evaluate(() => {
  const p = window.__forcedLayoutProbe;
  if (!p) return null;
  return {
    state: Object.assign({}, p.state),
    sites: Array.from(p.counts.entries()).map(([site, v]) => Object.assign({ site }, v)),
  };
});
await browser.close();

if (!snapshot) {
  console.error('forced-layout-attribution: probe did not install (page may have replaced window).');
  process.exit(2);
}

const sites = snapshot.sites.sort((a, b) => b.forced - a.forced || b.reads - a.reads);
const artifact = {
  label: LABEL,
  url: TARGET_URL,
  capturedAt: new Date().toISOString(),
  navigationError,
  exercise: EXERCISE ? { selector: EXERCISE, text: EXERCISE_TEXT, error: exerciseError } : null,
  state: snapshot.state,
  distinctCallSites: sites.length,
  sites: sites.slice(0, 200),
};
writeFileSync(artifactPath(`forced-layout-attribution-${LABEL}.json`), JSON.stringify(artifact, null, 1));

if (AS_JSON) {
  console.log(JSON.stringify(artifact, null, 1));
} else {
  console.log(
    `FORCED_LAYOUT_ATTRIBUTION ${JSON.stringify(Object.assign({ label: LABEL, url: TARGET_URL, exercise: EXERCISE || null, distinctCallSites: sites.length }, snapshot.state))}`,
  );
  console.log(`  top ${TOP} call sites by forced reads:`);
  for (const s of sites.slice(0, TOP)) {
    console.log(
      `  ${String(s.forced).padStart(5)} forced  ${String(s.reads).padStart(6)} reads  ${String(s.writes).padStart(6)} writes  ${s.site}`,
    );
  }
}
