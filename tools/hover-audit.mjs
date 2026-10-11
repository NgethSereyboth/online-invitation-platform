/**
 * hover-audit.mjs — force every :hover rule in a page and diff the computed style.
 *
 * Model
 *   A selector like `.gallery-photo:hover img` has two roles:
 *     - TRIGGER  the element that must be in the :hover state  -> `.gallery-photo`
 *                (everything left of the first `:hover`, minus a trailing combinator)
 *     - SUBJECT  the element whose computed style should change -> `.gallery-photo img`
 *                (the same selector with `:hover` deleted)
 *   Hovering only the subject would miss the rule entirely, so the audit forces
 *   the state on the trigger and diffs both the trigger and every subject.
 *
 * Mechanism
 *   CDP `CSS.forcePseudoState` is the protocol form of Playwright's page.hover().
 *   Unlike a synthetic mouse move it also reaches off-screen, covered, and
 *   zero-size elements, which is what makes this usable as an automated gate.
 *     https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-forcePseudoState
 *     https://developer.mozilla.org/en-US/docs/Web/CSS/:hover
 *   Chrome-only, by design.
 *
 * Three CDP gotchas, documented so the next pass does not rediscover them:
 *   1. cdp.send('Runtime.evaluate') resolves to the CDP `result` payload, so the
 *      RemoteObject is one level down: `const {result: remote} = await
 *      cdp.send(...)`. Destructuring `{object}` yields undefined for every call.
 *   2. DOM.getDocument must be called after DOM.enable and before node ids can
 *      be resolved, or DOM.requestNode has nothing to resolve against.
 *   3. DOM.requestNode legitimately returns nodeId 0. Treating 0 as falsy
 *      (`if (!nodeId) continue`) discards every element and reports a clean run
 *      of zero tests. Compare against undefined/null instead.
 *
 * Usage
 *   node tools/hover-audit.mjs [url] [--json] [--cap=N] [--out=FILE]
 *
 * Requires: node + puppeteer-core from the repo's package.json, and a running
 * server (tools/serve-gzip.py).
 * Produces: a per-page summary on stdout, and with --out the full per-element
 * JSON under artifacts/.
 */
import { writeFileSync } from 'node:fs';

import { freezeMotion, launch } from './lib/browser.mjs';
import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const AS_JSON = hasFlag(argv, 'json');
const CAP = Number((argv.find((a) => a.startsWith('--cap=')) || '--cap=10').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;
const PROPS = ['background-color', 'color', 'box-shadow', 'transform', 'border-color', 'outline-color'];

const browser = await launch({ kind: 'full' });
const page = await browser.newPage();
await page.setViewport({ width: 1366, height: 900 });
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise((r) => setTimeout(r, 1200));
await freezeMotion(page);

const cdp = await page.target().createCDPSession();
await cdp.send('DOM.enable');
await cdp.send('CSS.enable');
await cdp.send('DOM.getDocument', { depth: -1, pierce: true });

const collected = await page.evaluate((cap, props) => {
  const selectors = [];
  const walk = (rules) => {
    for (const rule of rules) {
      if (rule.cssRules && rule.constructor.name !== 'CSSStyleRule') { walk(rule.cssRules); continue; }
      if (!rule.selectorText || !rule.selectorText.includes(':hover')) continue;
      for (const part of rule.selectorText.split(',')) {
        const s = part.trim();
        if (s.includes(':hover')) selectors.push(s);
      }
    }
  };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch { /* opaque */ } }

  const byTrigger = new Map();     // trigger selector -> Set of subject selectors
  let skippedNested = 0;
  for (const s of selectors) {
    // `:hover` nested inside :not()/:is()/:has() means something else; the
    // "delete the token" transform is invalid there, so it is recorded as
    // skipped rather than silently mis-tested.
    if (/:not\(|:is\(|:has\(/.test(s)) { skippedNested++; continue; }
    const idx = s.indexOf(':hover');
    const trigger = s.slice(0, idx).replace(/[>+~]\s*$/, '').trim();
    const subject = s.replace(/:hover/g, '').replace(/\s+/g, ' ').trim();
    if (!trigger || !subject) { skippedNested++; continue; }
    if (!byTrigger.has(trigger)) byTrigger.set(trigger, new Set());
    byTrigger.get(trigger).add(subject);
  }

  const snap = (el) => {
    if (!el || !el.isConnected) return null;
    const cs = getComputedStyle(el);
    const o = {};
    for (const p of props) o[p] = cs.getPropertyValue(p);
    return o;
  };

  const targets = [];
  let invalid = 0, noMatch = 0, capped = 0;
  for (const [trigger, subjects] of byTrigger) {
    let els;
    try { els = [...document.querySelectorAll(trigger)]; } catch { invalid++; continue; }
    if (!els.length) { noMatch++; continue; }
    if (els.length > cap) capped++;
    for (const el of els.slice(0, cap)) {
      const subjectEls = [];
      for (const s of subjects) {
        try { for (const e of document.querySelectorAll(s)) if (!subjectEls.includes(e)) subjectEls.push(e); }
        catch { /* invalid subject */ }
      }
      targets.push({ el, subjectEls, trigger, subjects: [...subjects] });
    }
  }

  const entries = targets.map((t, i) => {
    t.index = i;
    return {
      i, trigger: t.trigger, subjects: t.subjects,
      tag: t.el.tagName, cls: String(t.el.className || '').slice(0, 46),
      subjectCount: t.subjectEls.length,
    };
  });

  // Everything the later reads need lives on `window`, keyed by index, so the
  // reads never have to re-resolve a selector against a possibly re-rendered DOM.
  window.__hoverAudit = {
    targets: targets.map((t) => ({ el: t.el, subjectEls: t.subjectEls })),
    before: targets.map((t) => ({ self: snap(t.el), subjects: t.subjectEls.map(snap) })),
  };

  return {
    triggerSelectors: byTrigger.size,
    hoverSelectors: selectors.length,
    skippedNested,
    invalidSelectors: invalid,
    triggersWithNoMatch: noMatch,
    triggersCapped: capped,
    elements: entries,
  };
}, CAP, PROPS);

const onWindow = await page.evaluate(() => {
  const a = window.__hoverAudit;
  return a ? { targets: a.targets.length, before: a.before.length } : null;
});

const results = [];
let unreadable = 0;
for (const info of collected.elements) {
  const { result: remote } = await cdp.send('Runtime.evaluate', {
    expression: 'window.__hoverAudit.targets[' + info.i + '].el', returnByValue: false,
  });
  let nodeId = null;
  if (remote && remote.objectId) {
    try { ({ nodeId } = await cdp.send('DOM.requestNode', { objectId: remote.objectId })); }
    catch { nodeId = null; }
  }
  // nodeId 0 is a legitimate id here; only undefined/null is a real failure.
  if (nodeId === undefined || nodeId === null) { unreadable++; continue; }
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
  const after = await page.evaluate((i, props) => {
    const t = window.__hoverAudit.targets[i];
    if (!t || !t.el || !t.el.isConnected) return null;
    const snap = (el) => {
      if (!el || !el.isConnected) return null;
      const cs = getComputedStyle(el);
      const o = {};
      for (const p of props) o[p] = cs.getPropertyValue(p);
      return o;
    };
    return { self: snap(t.el), subjects: t.subjectEls.map(snap) };
  }, info.i, PROPS);
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
  if (!after) { unreadable++; continue; }

  const before = await page.evaluate((i) => window.__hoverAudit.before[i], info.i);
  const diffOf = (b, a) => {
    const d = {};
    if (!b || !a) return d;
    for (const p of PROPS) if (b[p] !== a[p]) d[p] = b[p] + ' -> ' + a[p];
    return d;
  };
  const selfDiff = diffOf(before && before.self, after.self);
  const subjectDiffs = (after.subjects || [])
    .map((a, k) => diffOf(before && before.subjects ? before.subjects[k] : null, a))
    .filter((d) => Object.keys(d).length);
  const changed = { ...selfDiff };
  for (const d of subjectDiffs) for (const k of Object.keys(d)) if (!(k in changed)) changed[k] = d[k];
  results.push({ i: info.i, trigger: info.trigger, tag: info.tag, cls: info.cls,
    subjects: info.subjects, selfDiff, subjectDiffs,
    isChange: Object.keys(changed).length > 0 || subjectDiffs.length > 0 });
}

const changed = results.filter((r) => r.isChange);
const unchanged = results.filter((r) => !r.isChange);
const summary = {
  url: URL,
  hoverSelectorsInCssom: collected.hoverSelectors,
  distinctTriggerSelectors: collected.triggerSelectors,
  skippedHoverNestedInNotIsHas: collected.skippedNested,
  invalidSelectors: collected.invalidSelectors,
  triggersMatchingNothing: collected.triggersWithNoMatch,
  triggersCappedAtN: collected.triggersCapped,
  capPerTrigger: CAP,
  elementsOnWindow: onWindow ? onWindow.targets : null,
  elementsTested: results.length,
  elementsUnreadable: unreadable,
  elementsWithVisibleChange: changed.length,
  elementsWithNoVisibleChange: unchanged.length,
};

function text() {
  const out = [];
  out.push('URL ................................ ' + URL);
  out.push('  :hover selectors in the CSSOM .... ' + summary.hoverSelectorsInCssom);
  out.push('  distinct trigger selectors ....... ' + summary.distinctTriggerSelectors);
  out.push('  skipped (hover inside :not/:is/:has) ' + summary.skippedHoverNestedInNotIsHas);
  out.push('  invalid selectors ................ ' + summary.invalidSelectors);
  out.push('  triggers matching no element ..... ' + summary.triggersMatchingNothing);
  out.push('  triggers capped at ' + CAP + ' elements ... ' + summary.triggersCappedAtN);
  out.push('  elements captured on window ...... ' + summary.elementsOnWindow);
  out.push('  elements tested .................. ' + summary.elementsTested + (unreadable ? ' (unreadable: ' + unreadable + ')' : ''));
  out.push('    -> visible change on forced hover ' + summary.elementsWithVisibleChange);
  out.push('    -> NO  visible change ........... ' + summary.elementsWithNoVisibleChange);
  if (unchanged.length) {
    out.push('\n--- no visible change in ' + PROPS.join('/') + ' (first 40) ---');
    for (const r of unchanged.slice(0, 40))
      out.push('  ' + r.tag + '.' + r.cls + '   trigger=' + JSON.stringify(r.trigger).slice(0, 70));
  }
  return out.join('\n');
}

if (OUT) {
  const file = artifactPath(OUT);
  writeFileSync(file, JSON.stringify({ summary, changed, unchanged }, null, 0));
  console.log(text());
  console.log(`HOVER_AUDIT_SUMMARY ${JSON.stringify(summary)} raw=${file}`);
} else if (AS_JSON) {
  console.log(JSON.stringify({ summary, changed, unchanged }, null, 0));
} else {
  console.log(text());
}
await browser.close();
