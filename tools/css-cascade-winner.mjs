/**
 * css-cascade-winner.mjs — who actually WINS a property for an element, in each
 * state, in cascade order?
 *
 * Why this exists
 * ---------------
 * `tools/important-lift-test.mjs` reports that removing a declaration changes no
 * computed value, which is evidence that a declaration is inert — but "inert" and
 * "safe to demote" are not the same claim, and the difference matters because the
 * lift probe *removes* the declaration while a demotion only drops its
 * `!important`. A demotion cannot change any computed value when the declaration is
 * not the cascade winner: a losing declaration that loses its priority still loses.
 * This tool establishes that, per element and per state, from the browser's own
 * matched-style list (selectors, values, `important` flags in cascade order), so the
 * judgement is attributable rather than inferred from a diff.
 *
 * Measured with it (2026-10-12, index.html): the declaration
 *   `.final-timeline-row:hover, .final-timeline-row.active { background: … !important }`
 * never wins `background` on any `.final-timeline-row` — `body.studio-experience
 * .final-timeline-row { background: var(--app-surface) !important }` overrides it in
 * both states — which is why its demotion produced no change (§6 of the report).
 *
 * Reading the output
 *   `order` is cascade order as Chrome reports it (later entries win when priority
 *   and specificity tie); `IMPORTANT` marks `!important`. The tool prints what the
 *   browser computed alongside, so a winner claim can be checked against the value.
 *
 * Usage
 *   node tools/css-cascade-winner.mjs <url> --selector=.final-timeline-row \
 *        [--property=background] [--states=plain,active,hover] [--index=0]
 *
 * `plain` forces nothing; `active`/`focus-visible`/`checked` are applied as the class
 * the selector names (or forced over CDP when the name is a pseudo-class), the same
 * forcing rules as tools/important-lift-test.mjs and tools/state-style-diff.mjs.
 *
 * Requires: node + puppeteer-core and a running server (tools/serve-gzip.py).
 */
import { launch, newPage } from './lib/browser.mjs';
import { argValue, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const SELECTOR = argValue(argv, 'selector', null);
const PROPERTY = String(argValue(argv, 'property', 'background'));
const STATES = String(argValue(argv, 'states', 'plain,active,hover')).split(',').map((s) => s.trim()).filter(Boolean);
const INDEX = Number(argValue(argv, 'index', 0));
if (!SELECTOR) {
  console.error('css-cascade-winner: --selector=<css selector> is required');
  process.exit(2);
}

const PSEUDO = new Set(['hover', 'focus', 'focus-visible', 'focus-within', 'checked', 'target']);
const CLASS_STATES = ['active'];
const propertyMatcher = new RegExp('^' + PROPERTY.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&') + '(-.*)?$');

const browser = await launch({ kind: 'full' });
const page = await newPage(browser, { width: 1366, height: 900 });
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise((r) => setTimeout(r, 1200));

const cdp = await page.target().createCDPSession();
await cdp.send('DOM.enable');
await cdp.send('CSS.enable');
const { root } = await cdp.send('DOM.getDocument', { depth: -1 });
const matches = await page.evaluate((sel) => document.querySelectorAll(sel).length, SELECTOR);
if (!matches) {
  console.log(`CASCADE_WINNER ${JSON.stringify({ url: URL, selector: SELECTOR, property: PROPERTY, elements: 0 })}`);
  console.log('  (the selector matches nothing on this page — no claim is made)');
  await browser.close();
  process.exit(0);
}

console.log(`CASCADE_WINNER ${JSON.stringify({ url: URL, selector: SELECTOR, property: PROPERTY, elements: matches, index: INDEX, states: STATES })}`);
for (const state of STATES) {
  const useClass = CLASS_STATES.includes(state);
  if (useClass) await page.evaluate((sel, i, cls) => document.querySelectorAll(sel)[i].classList.add(cls), SELECTOR, INDEX, state);
  const { nodeIds } = await cdp.send('DOM.querySelectorAll', { nodeId: root.nodeId, selector: SELECTOR });
  const nodeId = nodeIds[INDEX];
  const forced = PSEUDO.has(state) && state !== 'plain' ? [state] : [];
  if (nodeId && forced.length) await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: forced });
  const matched = nodeId ? await cdp.send('CSS.getMatchedStylesForNode', { nodeId }) : { matchedCSSRules: [] };
  const computed = await page.evaluate((sel, i) => {
    const el = document.querySelectorAll(sel)[i];
    return el ? getComputedStyle(el).getPropertyValue(arguments ? '' : '') || null : null;
  }, SELECTOR, INDEX).catch(() => null);
  const computedValue = await page.evaluate((sel, i, prop) => {
    const el = document.querySelectorAll(sel)[i];
    return el ? getComputedStyle(el).getPropertyValue(prop) : null;
  }, SELECTOR, INDEX, PROPERTY);
  const rows = [];
  matched.matchedCSSRules.forEach((m, order) => {
    const rule = m.rule || {};
    const style = rule.style || {};
    for (const p of style.cssProperties || []) {
      if (!p.range) continue;                      // authored entries only, not longhand fragments
      if (!propertyMatcher.test(p.name)) continue;
      rows.push({
        order,
        important: !!p.important,
        name: p.name,
        value: String(p.value || '').slice(0, 52),
        selector: String((rule.selectorList && rule.selectorList.text) || rule.selectorText || '(inline/unknown)').slice(0, 78),
      });
    }
  });
  if (nodeId && forced.length) await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
  if (useClass) await page.evaluate((sel, i, cls) => document.querySelectorAll(sel)[i].classList.remove(cls), SELECTOR, INDEX, state);

  const importantRows = rows.filter((r) => r.important);
  const winner = importantRows.length ? importantRows[importantRows.length - 1] : (rows.length ? rows[rows.length - 1] : null);
  console.log(`  state=${state.padEnd(13)} computed ${PROPERTY}=${JSON.stringify(computedValue)}${computed ? '' : ''}`);
  for (const r of rows) {
    console.log(`    order=${String(r.order).padStart(2)} ${r.important ? 'IMPORTANT' : '         '} ${r.name.padEnd(18)} ${r.value.padEnd(52)} ${r.selector}`);
  }
  console.log(`    last-important -> ${winner ? winner.selector + '  ' + winner.name + ':' + winner.value : '(none)'}`);
}
await browser.close();
