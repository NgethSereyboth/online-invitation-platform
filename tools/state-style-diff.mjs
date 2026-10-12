/**
 * state-style-diff.mjs — did a CSS edit change the styles of the states the sweep
 * cannot reach with a hover audit?
 *
 * Why this exists
 * ---------------
 * `tools/important-lift-test.mjs` (v2) now measures a declaration on the non-:hover
 * state path of its rule as well as on `:hover` — so it can propose
 * `.final-timeline-row:hover, .final-timeline-row.active { background: … }` as
 * demotable. The check that decides whether a demotion is safe is a before/after
 * comparison, but the project's row-level comparison
 * (`tools/hover-regression-diff.py`) only forces `:hover`: a declaration whose only
 * reachable path is `.active` would be checked on a state the edit cannot affect.
 *
 * This tool closes that hole. It snapshots the COMPLETE computed style of every
 * element matching a selector in each requested state — `plain`, `active` (the
 * class the rule names is added), `focus-visible` (forced over CDP) and `hover`
 * (forced over CDP) — into a JSON file, and with `--compare` reads two snapshots
 * back and prints whether they are identical, element by element and property by
 * property. Same forcing rules as the lift probe, so the two agree by construction.
 *
 * What it does NOT claim
 * ----------------------
 * It measures the states it is asked for, on the pages it is pointed at. A state the
 * page cannot reach (a row that only exists in an authenticated session) is reported
 * as an element count of 0 rather than silently passing, and the report says which
 * states were measured.
 *
 * Method
 *   The class/attribute a state needs is applied to the element for the duration of
 *   the read and removed afterwards; a pseudo-class is forced with
 *   `CSS.forcePseudoState`
 *   https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-forcePseudoState
 *   (the same mechanism the hover audit uses, because headless Chrome reports
 *   `(hover: hover)` as false and CDP cannot override the media feature — see
 *   tools/lib/browser.mjs).
 *
 * Usage
 *   node tools/state-style-diff.mjs <url> --selector=.final-timeline-row \
 *        [--states=plain,active,hover] [--out=FILE]
 *   node tools/state-style-diff.mjs --compare=before.json,after.json
 *
 * The comparison is by property NAME, not by position: Chrome enumerates registered
 * custom properties in an order that is not stable across two loads of the same
 * page, so a positional diff reports dozens of "changes" that are the same values
 * reordered (measured — the first version of this file did exactly that).
 *
 * Exit status: 0 when the capture ran (and, with --compare, when the snapshots are
 * identical); 1 when they differ; 2 on a harness failure.
 */
import { readFileSync, writeFileSync } from 'node:fs';

import { launch, newPage } from './lib/browser.mjs';
import { artifactPath, argValue, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);

// ---------------------------------------------------------------------------
// Compare mode: read two snapshots, print the verdict, no browser.
// ---------------------------------------------------------------------------
const COMPARE = argValue(argv, 'compare', null);
if (COMPARE) {
  const [beforePath, afterPath] = String(COMPARE).split(',');
  if (!beforePath || !afterPath) {
    console.error('state-style-diff: --compare needs BEFORE.json,AFTER.json');
    process.exit(2);
  }
  const before = JSON.parse(readFileSync(artifactPath(beforePath), 'utf8'));
  const after = JSON.parse(readFileSync(artifactPath(afterPath), 'utf8'));
  const differences = [];
  const keys = new Set([...Object.keys(before.elements), ...Object.keys(after.elements)]);
  for (const key of [...keys].sort()) {
    const b = before.elements[key];
    const a = after.elements[key];
    if (!b || !a) { differences.push({ element: key, change: b ? 'element disappeared' : 'element appeared' }); continue; }
    for (const state of Object.keys(b.states)) {
      const bs = b.states[state];
      const as = a.states && a.states[state];
      if (!as) { differences.push({ element: key, state, change: 'state not captured after' }); continue; }
      if (bs === as) continue;
      // Compare by PROPERTY NAME, not by position: Chrome enumerates registered
      // custom properties in an order that is not stable between two loads of the
      // same page, and a positional diff reports ~30 changes that are all the same
      // values in a different order. Measured — the first version of this tool did
      // exactly that on a change that moved no value.
      const toMap = (text) => {
        const map = new Map();
        for (const part of String(text || '').split(';')) {
          const at = part.indexOf(':');
          if (at === -1) continue;
          map.set(part.slice(0, at).trim(), part.slice(at + 1).trim());
        }
        return map;
      };
      const bMap = toMap(bs);
      const aMap = toMap(as);
      for (const [name, value] of bMap) {
        if (!aMap.has(name)) differences.push({ element: key, state, change: `${name}:${value} removed` });
        else if (aMap.get(name) !== value) differences.push({ element: key, state, change: `${name}: ${value} -> ${aMap.get(name)}` });
        if (differences.length > 20) break;
      }
      for (const [name, value] of aMap) {
        if (!bMap.has(name)) differences.push({ element: key, state, change: `${name}:${value} added` });
        if (differences.length > 20) break;
      }
      // A property-count change is worth reporting even when every shared name agrees.
      if (bMap.size !== aMap.size) {
        differences.push({ element: key, state, change: `property count ${bMap.size} -> ${aMap.size}` });
      }
    }
  }
  const summary = {
    before: { url: before.url, selector: before.selector, states: before.states, elements: Object.keys(before.elements).length },
    after: { url: after.url, selector: after.selector, states: after.states, elements: Object.keys(after.elements).length },
    elementsCompared: keys.size,
    differences: differences.length,
    identical: differences.length === 0,
  };
  console.log('STATE_STYLE_DIFF ' + JSON.stringify(summary));
  for (const d of differences) console.log('  DIFF ' + JSON.stringify(d));
  process.exit(differences.length ? 1 : 0);
}

// ---------------------------------------------------------------------------
// Capture mode.
// ---------------------------------------------------------------------------
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const SELECTOR = argValue(argv, 'selector', null);
const STATES = String(argValue(argv, 'states', 'plain,active,hover')).split(',').map((s) => s.trim()).filter(Boolean);
const OUT = argValue(argv, 'out', null);
if (!SELECTOR) {
  console.error('state-style-diff: --selector=<css selector> is required');
  process.exit(2);
}

// A state is either a pseudo-class CDP can force, or a class the tool adds.
const PSEUDO = new Set(['hover', 'active', 'focus', 'focus-visible', 'focus-within', 'checked', 'target']);
const CLASS_STATES = ['active'];   // ambiguous names the project uses as a class, not a pseudo

const browser = await launch({ kind: 'full' });
const page = await newPage(browser, { width: 1366, height: 900 });
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise((r) => setTimeout(r, 1200));

const cdp = await page.target().createCDPSession();
await cdp.send('DOM.enable');
await cdp.send('CSS.enable');
const { root } = await cdp.send('DOM.getDocument', { depth: -1 });

const elementKeys = await page.evaluate((sel) => [...document.querySelectorAll(sel)].map((el, i) => {
  const id = el.id ? '#' + el.id : `${el.tagName.toLowerCase()}${i}`;
  return { key: `${id}[${i}]`, tag: el.tagName.toLowerCase(), cls: el.className };
}), SELECTOR);

const elements = {};
let forcedStates = 0;
let classStates = 0;
for (const { key } of elementKeys) {
  const states = {};
  for (const state of STATES) {
    // The element is addressed by index: the snapshot key carries it, and the
    // forced state is applied to the same element each time.
    const idx = elementKeys.findIndex((e) => e.key === key);
    const useClass = CLASS_STATES.includes(state);
    const { nodeId } = await cdp.send('DOM.querySelectorAll', { nodeId: root.nodeId, selector: SELECTOR }).then(async (all) => ({ nodeId: all.nodeIds[idx] }));
    if (!nodeId) { states[state] = null; continue; }
    if (useClass) {
      await page.evaluate((sel, i, cls) => document.querySelectorAll(sel)[i].classList.add(cls), SELECTOR, idx, state);
      classStates++;
    } else if (PSEUDO.has(state) && state !== 'plain') {
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [state] });
      forcedStates++;
    }
    states[state] = await page.evaluate((sel, i) => {
      const el = document.querySelectorAll(sel)[i];
      if (!el) return null;
      const cs = getComputedStyle(el);
      let s = '';
      for (let k = 0; k < cs.length; k++) { const p = cs[k]; s += p + ':' + cs.getPropertyValue(p) + ';'; }
      return s;
    }, SELECTOR, idx);
    if (useClass) {
      await page.evaluate((sel, i, cls) => document.querySelectorAll(sel)[i].classList.remove(cls), SELECTOR, idx, state);
    } else if (PSEUDO.has(state) && state !== 'plain') {
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
    }
  }
  elements[key] = { states };
}

const payload = {
  url: URL,
  selector: SELECTOR,
  states: STATES,
  elements,
  counts: { elements: elementKeys.length, forcedStates, classStates },
};
if (OUT) {
  const file = artifactPath(OUT);
  writeFileSync(file, JSON.stringify(payload, null, 1));
  console.log(`STATE_STYLE_SNAPSHOT ${JSON.stringify({ url: URL, selector: SELECTOR, states: STATES, ...payload.counts })} file=${file}`);
} else {
  console.log(JSON.stringify(payload, null, 1));
}
await browser.close();
