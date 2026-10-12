/**
 * demotion-recheck.mjs — is a declaration safe to demote in the state a USER can
 * reach, when the sweep could only see it in a state where nothing is observable?
 *
 * Why this exists
 * ---------------
 * `tools/important-lift-test.mjs` proposes an `!important` declaration for demotion
 * when removing it changes no computed value it can read. That is an observation of
 * computed values, and for an element with NO BOX Chrome stops resolving used values:
 * inside a `display:none` subtree `transform` reads `none` whatever the cascade says,
 * so the leave-one-out returns an identical snapshot in every run. Measured on
 * index.html (2026-10-12), `transform: none !important` in
 * `.ui-theme-menu button:hover`: with the theme menu `[hidden]` the value read `none`
 * and removal changed nothing (48/48 page-runs in the expanded sweep, which is why
 * the sweep called it unanimously demotable); with the menu REVEALED the same removal
 * moved the element to `matrix(1.012, 0, 0, 1.012, 0, -2)` — a real, visible change.
 * The sweep now reports such a declaration as UNMEASURED rather than redundant, and
 * this tool is what answers the question that leaves open.
 *
 * What it does
 * ------------
 * For one rule (`--selector`) and one property (`--property`):
 *   1. load the page, freeze motion, re-enable `@media(hover:hover)` (lib/browser.mjs)
 *      and VERIFY the rewrite took effect;
 *   2. with `--reveal`, remove the `hidden` attribute from every ancestor of every
 *      matched element first — the state a user is in when they can hover the thing at
 *      all (a closed popover cannot be hovered). Without it, the rule is measured in
 *      the page's default state, which is what the sweep does;
 *   3. read every matched element's computed `--property` with `:hover` forced over
 *      `CSS.forcePseudoState`
 *      https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-forcePseudoState
 *      after `MotionSettle.settleAll` — the same settle the lift probe now uses, so a
 *      running transition cannot be read mid-interpolation (a `transform` transition
 *      samples as the identity matrix at t=0, which looks exactly like "no change");
 *   4. re-read after the declaration loses its `!important` (DEMOTION — what a source
 *      edit does) and after it is removed entirely (DELETION — what the leave-one-out
 *      does), then report each as LOSSY or NO-CHANGE per element.
 *
 * Reading the verdict
 *   `rendered=false` marks an element with no box: nothing about it is observable, so
 *   its row cannot support a verdict either way. A verdict is READ on rendered
 *   elements only, and `elementsReadable` is printed so a run that observed nothing
 *   says so instead of implying agreement.
 *
 * Usage
 *   node tools/demotion-recheck.mjs <url> --selector='.ui-theme-menu button:hover' \
 *        --property=transform [--reveal] [--out=FILE]
 *
 * Requires: node + puppeteer-core and a running server (tools/serve-gzip.py).
 */
import { writeFileSync } from 'node:fs';

import { emulateHoverCapable, freezeMotion, launch, newPage, verifyHoverMediaRewrite } from './lib/browser.mjs';
import { MOTION_SETTLE_SOURCE } from './lib/motion-settle.mjs';
import { argValue, artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const SELECTOR = argValue(argv, 'selector', null);
const PROPERTY = String(argValue(argv, 'property', 'transform'));
const REVEAL = hasFlag(argv, 'reveal');
const OUT = argValue(argv, 'out', null);
if (!SELECTOR) {
  console.error('demotion-recheck: --selector=<the rule\'s selector text> is required');
  process.exit(2);
}

/** Find every stylesheet rule whose selector text is exactly `sel` (a page may carry
 *  the same rule twice — the bundle and an individual file), and read `prop` from it.
 *
 *  The selectorText test comes FIRST and the descent second, deliberately: on this
 *  Chrome a `CSSStyleRule` has its own (usually empty) `cssRules` because of CSS
 *  nesting, so a walk that descends first and `continue`s never inspects the rule
 *  itself. Measured while writing this file: the descend-first form found 0 rules
 *  where the shipped `important-lift-test.mjs` walk — which guards with
 *  `rule.constructor.name !== 'CSSStyleRule'` — finds the same rule. */
const FIND = `(sel, prop) => {
  const rules = [];
  const walk = (list) => {
    for (const r of list) {
      if (r.selectorText === sel) { rules.push(r); continue; }
      if (r.cssRules) walk(r.cssRules);
    }
  };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch { /* opaque */ } }
  return rules.map((r) => ({ value: r.style.getPropertyValue(prop), priority: r.style.getPropertyPriority(prop) }));
}`;

const browser = await launch({ kind: 'full' });
const page = await newPage(browser);
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise((r) => setTimeout(r, 1200));
await freezeMotion(page);
const hoverMedia = await emulateHoverCapable(page);
const mediaCheck = await verifyHoverMediaRewrite(page, hoverMedia.rewrittenCount);
if (mediaCheck.stillInactive.length) {
  console.error(`demotion-recheck: ${mediaCheck.stillInactive.length} rewritten media rule(s) still report matches=false — refusing to report a hover measurement from a touch-first page.`);
  await browser.close();
  process.exit(3);
}
await page.addScriptTag({ content: MOTION_SETTLE_SOURCE });

const found = await page.evaluate(new Function('sel', 'prop', `const f=${FIND}; return f(sel, prop);`), SELECTOR, PROPERTY);
console.log('DEMOTION_RECHECK ' + JSON.stringify({
  url: URL, selector: SELECTOR, property: PROPERTY, reveal: REVEAL,
  hoverMedia: { rewritten: hoverMedia.rewrittenCount, stillInactive: mediaCheck.stillInactive.length },
  ruleInstances: found.length,
  declarationBefore: found.map((f) => `${f.value}${f.priority ? ' !' + f.priority : ''}`),
}));
if (!found.length) {
  console.error('demotion-recheck: no rule with that exact selector text on this page.');
  await browser.close();
  process.exit(2);
}

const revealReport = REVEAL
  ? await page.evaluate((sel) => {
    const done = [];
    for (const el of document.querySelectorAll(sel)) {
      let node = el.parentElement;
      while (node && node !== document.documentElement) {
        if (node.hasAttribute && node.hasAttribute('hidden')) { node.removeAttribute('hidden'); done.push(`${node.tagName.toLowerCase()}.${String(node.className).split(' ')[0]}`); }
        node = node.parentElement;
      }
    }
    return done;
  }, SELECTOR.replace(/:hover\s*$/, ''))
  : [];
if (REVEAL) console.log('REVEALED ' + JSON.stringify([...new Set(revealReport)]));

const cdp = await page.target().createCDPSession();
await cdp.send('DOM.enable');
await cdp.send('CSS.enable');
const { root } = await cdp.send('DOM.getDocument', { depth: -1 });
const BASE_SEL = SELECTOR.replace(/:hover\s*$/, '');
const { nodeIds } = await cdp.send('DOM.querySelectorAll', { nodeId: root.nodeId, selector: BASE_SEL });

/** Read `prop` on every matched element, hover forced, after its motion settled. */
async function read(label) {
  const rows = [];
  for (let i = 0; i < nodeIds.length; i++) {
    await cdp.send('CSS.forcePseudoState', { nodeId: nodeIds[i], forcedPseudoClasses: ['hover'] });
    const row = await page.evaluate(async (sel, idx, prop) => {
      const el = document.querySelectorAll(sel)[idx];
      if (!el) return null;
      await globalThis.MotionSettle.settleAll([el]);
      const cs = getComputedStyle(el);
      return { value: cs.getPropertyValue(prop), rendered: el.getClientRects().length > 0 };
    }, BASE_SEL, i, PROPERTY);
    await cdp.send('CSS.forcePseudoState', { nodeId: nodeIds[i], forcedPseudoClasses: [] });
    if (row) rows.push({ element: i, ...row });
  }
  console.log(label + ' ' + JSON.stringify(rows));
  return rows;
}

const baseline = await read('VALUES_BASELINE');

// DEMOTION: drop the priority, keep the declaration. This is the source edit.
const afterDemotion = await page.evaluate(new Function('sel', 'prop', `
  const f=${FIND};
  const collect=(s)=>{const out=[];const walk=(list)=>{for(const r of list){if(r.selectorText===s){out.push(r);continue;} if(r.cssRules) walk(r.cssRules);}};for(const sh of document.styleSheets){try{walk(sh.cssRules);}catch{}}return out;};
  const before=f(sel, prop);
  for(const r of collect(sel)) r.style.setProperty(prop, r.style.getPropertyValue(prop), '');
  const f2=${FIND}; return {before, after: f2(sel, prop)};`), SELECTOR, PROPERTY);
console.log('DEMOTION_APPLIED ' + JSON.stringify(afterDemotion));
const demoted = await read('VALUES_AFTER_DEMOTION');

// DELETION: the leave-one-out the lift probe performs.
await page.evaluate(new Function('sel', 'prop', `
  for(const sh of document.styleSheets){let list;try{list=sh.cssRules;}catch{continue;}
    const walk=(rules)=>{for(const r of rules){if(r.selectorText===sel){r.style.removeProperty(prop);continue;} if(r.cssRules) walk(r.cssRules);}};
    walk(list);}`), SELECTOR, PROPERTY);
const deleted = await read('VALUES_AFTER_DELETION');

const byElement = new Map(baseline.map((r) => [r.element, r]));
const report = { url: URL, selector: SELECTOR, property: PROPERTY, reveal: REVEAL, elements: baseline.length, elementsReadable: baseline.filter((r) => r.rendered).length, demotion: [], deletion: [] };
for (const r of demoted) {
  const b = byElement.get(r.element);
  if (!b || !b.rendered) continue;
  if (r.value !== b.value) report.demotion.push({ element: r.element, from: b.value, to: r.value });
}
for (const r of deleted) {
  const b = byElement.get(r.element);
  if (!b || !b.rendered) continue;
  if (r.value !== b.value) report.deletion.push({ element: r.element, from: b.value, to: r.value });
}
// A change means the declaration was load-bearing on an element the user can hover.
report.verdict = report.deletion.length || report.demotion.length ? 'LOAD-BEARING' : 'NO-CHANGE';
console.log('DEMOTION_VERDICT ' + JSON.stringify(report));
if (OUT) writeFileSync(artifactPath(OUT), JSON.stringify(report, null, 2));
await browser.close();
process.exit(report.verdict === 'LOAD-BEARING' ? 1 : 0);
