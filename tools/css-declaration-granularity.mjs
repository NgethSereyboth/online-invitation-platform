/**
 * css-declaration-granularity.mjs — what does each API say a CSS rule contains?
 *
 * Why this exists
 * ---------------
 * `tools/important-lift-test.mjs` demotes `!important` one candidate at a time.
 * It enumerated its candidates with
 *
 *     for (let k = 0; k < rule.style.length; k++) { const p = rule.style[k]; ... }
 *
 * A CSSStyleDeclaration's indexed properties are LONGHANDS: one authored
 * `background: linear-gradient(...) !important` iterates as `background-image`,
 * `background-position-x`, ... `background-color`. The instrument therefore
 * reported one authored declaration as nine independent candidates — eight of
 * them inert — and the previous pass correctly refused to act on a list whose
 * entries could not be removed independently of each other.
 *
 * Which API preserves the authored form is not a matter of reading the spec: it
 * is a property of this Chrome. This tool prints all of them side by side for a
 * named selector, so the choice is made against output rather than recollection:
 *
 *   CSSOM index           rule.style.length / rule.style[k] / getPropertyPriority
 *   CSSOM serialization   rule.cssText, rule.style.cssText
 *   CDP authored form     CSS.getMatchedStylesForNode -> cssProperties[]
 *                         (name, value, important, implicit, longhandProperties)
 *   CDP edit API          whether CSS.setStyleTexts is present at all
 *
 * Usage
 *   node tools/css-declaration-granularity.mjs [page] --selector='.ui-theme-menu button:hover'
 *   node tools/css-declaration-granularity.mjs index.html --selector='input:hover,textarea:hover,select:hover' --json
 *
 * --selector is matched as a SUBSTRING of a rule's selectorText, so a rule can be
 * inspected even when no element on the page currently matches it (the theme menu
 * is built on first open, but its rule is in the stylesheet from load). The CDP
 * section needs a live element and is skipped, loudly, when there is none.
 *
 * Requirements: a running server (tools/serve-gzip.py), node + puppeteer-core.
 * Writes nothing. Exit 2 if the selector matches no rule anywhere.
 */
import { freezeMotion, launch } from './lib/browser.mjs';
import { hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const pageArg = argv.find((a) => !a.startsWith('--'));
const URL = urlFromArg(pageArg || pageUrl('index.html'));
const SELECTOR = (argv.find((a) => a.startsWith('--selector=')) || '--selector=').split('=').slice(1).join('=')
  || '.ui-theme-menu button:hover';
const AS_JSON = hasFlag(argv, 'json');

const browser = await launch({ kind: 'full' });
const page = await browser.newPage();
await page.setViewport({ width: 1366, height: 900 });
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await freezeMotion(page);

const cdp = await page.target().createCDPSession();
await cdp.send('DOM.enable');
await cdp.send('CSS.enable');

// Capability is a fact about this Chrome, so it is probed by CALLING, not by
// reading the protocol description: Schema.getDomains reports an empty command
// list for CSS here while the method itself answers fine, and a capability
// report that is wrong in the safe direction is still wrong.
const canCall = async (method, params) => {
  try { await cdp.send(method, params); return true; } catch { return false; }
};
const { root: probeRoot } = await cdp.send('DOM.getDocument', { depth: 1 });
const probeNode = (await cdp.send('DOM.querySelector', { nodeId: probeRoot.nodeId, selector: 'body' })).nodeId;
const hasMatchedStyles = probeNode ? await canCall('CSS.getMatchedStylesForNode', { nodeId: probeNode }) : false;
let hasSetStyleTexts = false;
if (probeNode) {
  const matched = hasMatchedStyles ? await cdp.send('CSS.getMatchedStylesForNode', { nodeId: probeNode }) : null;
  const first = matched && (matched.matchedCSSRules || []).map((m) => m.rule).find((r) => r.styleSheetId && r.style && r.style.range);
  if (first) {
    hasSetStyleTexts = await canCall('CSS.setStyleTexts', {
      edits: [{ styleSheetId: first.styleSheetId, range: first.style.range, text: first.style.cssText }],
    });
  }
}

/** The first element matching the selector, and the live rules that match it. */
const inPage = await page.evaluate((sel) => {
  const el = document.querySelector(sel.split(',')[0]);
  const collected = [];
  const wanted = sel.split(',').map((s) => s.trim()).filter(Boolean);
  const walk = (rules, source) => {
    for (const rule of rules) {
      if (rule.cssRules && rule.constructor.name !== 'CSSStyleRule') { walk(rule.cssRules, source); continue; }
      if (!rule.selectorText || !rule.selectorText.includes(':hover')) continue;
      if (!wanted.some((w) => rule.selectorText.includes(w))) continue;
      const parts = [];
      for (let k = 0; k < rule.style.length; k++) {
        const p = rule.style[k];
        parts.push({ name: p, value: rule.style.getPropertyValue(p), priority: rule.style.getPropertyPriority(p) });
      }
      collected.push({
        selectorText: rule.selectorText,
        source,
        indexedLength: rule.style.length,
        indexed: parts,
        styleCssText: rule.style.cssText,
        ruleCssText: rule.cssText,
      });
    }
  };
  [...document.styleSheets].forEach((sheet, i) => {
    let rules;
    try { rules = sheet.cssRules; } catch { return; }
    walk(rules, sheet.href ? sheet.href.split('/').pop() : `inline#${i}`);
  });
  return {
    found: collected.length > 0,
    element: el ? el.tagName + (el.className ? '.' + String(el.className).split(/\s+/)[0] : '') : null,
    rules: collected,
  };
}, SELECTOR);

if (!inPage.found) {
  console.error(`css-declaration-granularity: no :hover rule matches ${SELECTOR} on ${URL}`);
  await browser.close();
  process.exit(2);
}

// DOM.querySelector matches against the DOM as it is, and `:hover` is never true
// there, so a `:hover` selector finds no node. The state is dropped for the
// lookup and then FORCED, which is the only way the browser will report the rule.
const nodeSelector = SELECTOR.split(',')[0].replace(/:hover/g, '').trim();
const { root } = await cdp.send('DOM.getDocument', { depth: 1 });
const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: nodeSelector });

let cdpRules = [];
if (!nodeId) {
  console.error(`css-declaration-granularity: no element matches "${nodeSelector}" — CDP section skipped`);
} else if (hasMatchedStyles) {
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
}
if (hasMatchedStyles && nodeId) {
  const matched = await cdp.send('CSS.getMatchedStylesForNode', { nodeId });
  const push = (list, origin) => {
    for (const m of list || []) {
      const rule = m.rule;
      if (!rule.selectorList || !rule.selectorList.text.includes(':hover')) continue;
      cdpRules.push({
        origin,
        selectorText: rule.selectorList.text,
        styleSheetId: rule.styleSheetId || null,
        range: rule.style ? rule.style.range || null : null,
        cssProperties: (rule.style ? rule.style.cssProperties : []).map((p) => ({
          name: p.name,
          value: p.value,
          important: p.important,
          implicit: p.implicit === true,
          longhands: (p.longhandProperties || []).map((l) => l.name),
        })),
      });
    }
  };
  push(matched.matchedCSSRules, 'matched');
  push(matched.pseudoElements, 'pseudo');
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
}

const authored = cdpRules.map((r) => ({
  selectorText: r.selectorText,
  origin: r.origin,
  importantDeclarations: r.cssProperties.filter((p) => p.important && !p.implicit).map((p) => ({
    name: p.name,
    value: p.value,
    expandsTo: p.longhands,
  })),
  importantNames: r.cssProperties.filter((p) => p.important && !p.implicit).map((p) => p.name),
}));

const out = {
  url: URL,
  selector: SELECTOR,
  element: inPage.element,
  cdp: { getMatchedStylesForNode: hasMatchedStyles, setStyleTexts: hasSetStyleTexts, rules: cdpRules },
  cssom: inPage.rules,
  authoredDeclarationsPerCdp: authored,
};

if (AS_JSON) {
  console.log(JSON.stringify(out, null, 2));
} else {
  console.log(`URL ................... ${URL}`);
  console.log(`selector .............. ${SELECTOR}   (first live match: ${inPage.element || 'none'})\n`);
  console.log(`CDP capability ........ getMatchedStylesForNode=${hasMatchedStyles}  setStyleTexts=${hasSetStyleTexts}\n`);
  for (const r of inPage.rules) {
    console.log(`--- CSSOM  ${r.source}  ${r.selectorText}`);
    console.log(`    style.length = ${r.indexedLength}   (indexed names are longhands unless noted)`);
    for (const p of r.indexed) {
      console.log(`      [${p.priority || 'normal'}] ${p.name}: ${p.value}`);
    }
    console.log(`    style.cssText = ${r.styleCssText}`);
  }
  for (const r of cdpRules) {
    console.log(`\n--- CDP (${r.origin})  ${r.selectorText}`);
    for (const p of r.cssProperties) {
      const lh = p.longhands.length ? `  expands-to=[${p.longhands.join(', ')}]` : '';
      console.log(`      [${p.important ? 'important' : 'normal'}${p.implicit ? ', implicit' : ''}] ${p.name}: ${p.value}${lh}`);
    }
  }
  console.log('\n--- authored !important declarations (CDP) ---');
  for (const a of authored) {
    console.log(`  ${a.selectorText}`);
    for (const d of a.importantDeclarations) {
      console.log(`    ${d.name}: ${d.value}   (${d.expandsTo.length} longhands)`);
    }
    if (!a.importantDeclarations.length) console.log('    (none)');
  }
}
await browser.close();
