/**
 * important-lift-test.mjs — decide, per declaration, whether an `!important` on
 * a `:hover` rule is load-bearing or redundant.
 *
 * Method (leave-one-out, runtime-only, nothing is written to disk)
 *   1. Load the page and collect every `:hover` rule from the CSSOM, deriving
 *      for each selector its TRIGGER (the element that must be hovered) and its
 *      SUBJECT (the element whose style changes).
 *   2. Snapshot the COMPLETE computed style of every affected element while the
 *      hover state is forced — every property Chrome exposes, not a hand-picked
 *      subset, so a change in any observable property is caught.
 *   3. For each `!important` declaration on a `:hover` rule: demote that one
 *      declaration to normal priority in the CSSOM, re-force hover on every
 *      element the rule can reach, and compare the full computed style against
 *      the snapshot. Restore the priority immediately afterwards.
 *   4. A declaration whose demotion changes nothing, anywhere, is redundant on
 *      this page: the cascade already produces the same value without it.
 *
 * Rationale: "redundant on the pages tested" is a weaker claim than "safe to
 * delete", which is why the test is per-page and must be re-run on every page
 * a declaration can reach before that declaration is demoted in source.
 *
 * Force mechanism is CDP CSS.forcePseudoState (Chrome-only by design):
 *   https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-forcePseudoState
 *
 * Usage
 *   node tools/important-lift-test.mjs [url] [--json] [--cap=N] [--out=FILE]
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: redundant/load-bearing counts per page, and with --out the full
 * per-declaration JSON under artifacts/.
 */
import { writeFileSync } from 'node:fs';

import { freezeMotion, launch } from './lib/browser.mjs';
import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const AS_JSON = hasFlag(argv, 'json');
const CAP = Number((argv.find((a) => a.startsWith('--cap=')) || '--cap=10').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;

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

const setup = await page.evaluate((cap) => {
  const hoverRules = [];
  const walk = (rules) => {
    for (const rule of rules) {
      if (rule.cssRules && rule.constructor.name !== 'CSSStyleRule') { walk(rule.cssRules); continue; }
      if (rule.selectorText && rule.selectorText.includes(':hover')) hoverRules.push(rule);
    }
  };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch { /* opaque */ } }

  const byTrigger = new Map();
  const candidates = [];
  let skippedNested = 0;
  for (const rule of hoverRules) {
    const triggers = new Set();
    for (const part of rule.selectorText.split(',')) {
      const s = part.trim();
      if (!s.includes(':hover')) continue;
      if (/:not\(|:is\(|:has\(/.test(s)) { skippedNested++; continue; }
      const idx = s.indexOf(':hover');
      const trig = s.slice(0, idx).replace(/[>+~]\s*$/, '').trim();
      const subj = s.replace(/:hover/g, '').replace(/\s+/g, ' ').trim();
      if (!trig || !subj) { skippedNested++; continue; }
      triggers.add(trig);
      if (!byTrigger.has(trig)) byTrigger.set(trig, new Set());
      byTrigger.get(trig).add(subj);
    }
    const importants = [];
    for (let k = 0; k < rule.style.length; k++) {
      const p = rule.style[k];
      if (rule.style.getPropertyPriority(p) === 'important') importants.push(p);
    }
    if (importants.length && triggers.size) candidates.push({ rule, props: importants, triggers: [...triggers] });
  }

  const targets = [];
  let triggersWithNoMatch = 0, triggersCapped = 0, invalid = 0;
  for (const [trigger, subjects] of byTrigger) {
    let els;
    try { els = [...document.querySelectorAll(trigger)]; } catch { invalid++; continue; }
    if (!els.length) { triggersWithNoMatch++; continue; }
    if (els.length > cap) triggersCapped++;
    for (const el of els.slice(0, cap)) {
      const subjectEls = [];
      for (const s of subjects) {
        try { for (const e of document.querySelectorAll(s)) if (!subjectEls.includes(e)) subjectEls.push(e); }
        catch { /* invalid subject */ }
      }
      targets.push({ el, subjectEls, trigger });
    }
  }

  const byTriggerIdx = new Map();
  targets.forEach((t, i) => {
    if (!byTriggerIdx.has(t.trigger)) byTriggerIdx.set(t.trigger, []);
    byTriggerIdx.get(t.trigger).push(i);
  });

  window.__lift = {
    targets: targets.map((t) => ({ el: t.el, subjectEls: t.subjectEls })),
    candidates: candidates.map((c) => ({
      rule: c.rule, props: c.props,
      indices: [...new Set(c.triggers.flatMap((t) => byTriggerIdx.get(t) || []))],
    })),
  };

  return {
    hoverRulesTotal: hoverRules.length,
    skippedNested,
    distinctTriggers: byTrigger.size,
    invalidSelectors: invalid,
    triggersWithNoMatch,
    triggersCapped,
    targetCount: targets.length,
    candidateRules: candidates.length,
    candidateDeclarations: candidates.reduce((n, c) => n + c.props.length, 0),
    candidatePreview: candidates.slice(0, 200).map((c) => ({
      sel: c.rule.selectorText.slice(0, 74), props: c.props,
      targets: [...new Set(c.triggers.flatMap((t) => byTriggerIdx.get(t) || []))].length,
    })),
  };
}, CAP);

async function nodeIdFor(i) {
  const { result: remote } = await cdp.send('Runtime.evaluate', {
    expression: 'window.__lift.targets[' + i + '].el', returnByValue: false,
  });
  if (!remote || !remote.objectId) return null;
  try { const { nodeId } = await cdp.send('DOM.requestNode', { objectId: remote.objectId }); return nodeId; }
  catch { return null; }
}

// 2 — baseline: full computed style of self and subjects while hover is forced.
const matched = [];
const baseline = new Map();
for (let i = 0; i < setup.targetCount; i++) {
  const nodeId = await nodeIdFor(i);
  if (nodeId === null) continue;
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
  const snap = await page.evaluate((idx) => {
    const t = window.__lift.targets[idx];
    const cap = (el) => { if (!el || !el.isConnected) return null; const cs = getComputedStyle(el); let s = '';
      for (let k = 0; k < cs.length; k++) { const p = cs[k]; s += p + ':' + cs.getPropertyValue(p) + ';'; } return s; };
    return { self: cap(t.el), subjects: t.subjectEls.map(cap) };
  }, i);
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
  if (!snap) continue;
  baseline.set(i, snap);
  matched.push({ i, nodeId });
}

// 3 — leave-one-out: demote one declaration, re-measure, restore.
const nodeIdByIndex = new Map(matched.map((m) => [m.i, m.nodeId]));
const results = [];
for (let ci = 0; ci < setup.candidateRules; ci++) {
  const cand = await page.evaluate((k) => {
    const c = window.__lift.candidates[k];
    return { props: c.props, indices: c.indices, sel: c.rule.selectorText.slice(0, 90) };
  }, ci);
  const loadBearing = [];
  for (const prop of cand.props) {
    const affected = cand.indices.filter((i) => nodeIdByIndex.has(i) && baseline.has(i));
    if (!affected.length) { loadBearing.push({ prop, note: 'no measured element', diffs: 0, sample: [] }); continue; }
    await page.evaluate((k, p) => {
      const st = window.__lift.candidates[k].rule.style;
      st.setProperty(p, st.getPropertyValue(p), '');
    }, ci, prop);
    let diffs = 0; const sample = [];
    for (const i of affected) {
      const nodeId = nodeIdByIndex.get(i);
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
      const snap = await page.evaluate((idx) => {
        const t = window.__lift.targets[idx];
        const cap = (el) => { if (!el || !el.isConnected) return null; const cs = getComputedStyle(el); let s = '';
          for (let k = 0; k < cs.length; k++) { const p = cs[k]; s += p + ':' + cs.getPropertyValue(p) + ';'; } return s; };
        return { self: cap(t.el), subjects: t.subjectEls.map(cap) };
      }, i);
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
      const base = baseline.get(i);
      if (!snap) continue;
      if (snap.self !== base.self) {
        diffs++;
        if (sample.length < 3) {
          const a = (base.self || '').split(';'), b = (snap.self || '').split(';');
          const ch = [];
          for (let k = 0; k < Math.min(a.length, b.length); k++) if (a[k] !== b[k]) ch.push(a[k] + ' -> ' + b[k]);
          sample.push({ element: i, changed: ch.slice(0, 4) });
        }
      }
      for (let s = 0; s < (snap.subjects || []).length; s++) {
        if (snap.subjects[s] !== (base.subjects || [])[s]) diffs++;
      }
    }
    await page.evaluate((k, p) => {
      const st = window.__lift.candidates[k].rule.style;
      st.setProperty(p, st.getPropertyValue(p), 'important');
    }, ci, prop);
    loadBearing.push({ prop, diffs, affected: affected.length, sample });
  }
  results.push({ i: ci, selector: cand.sel, props: loadBearing });
}

const redundant = [], needed = [];
for (const r of results) for (const p of r.props) {
  const row = { selector: r.selector, prop: p.prop, diffs: p.diffs, affected: p.affected ?? 0, sample: p.sample };
  if (p.note === 'no measured element') row.note = p.note;
  if (!p.diffs) redundant.push(row); else needed.push(row);
}
const summary = {
  url: URL,
  hoverRulesInCssom: setup.hoverRulesTotal,
  distinctTriggerSelectors: setup.distinctTriggers,
  triggersMatchingNothing: setup.triggersWithNoMatch,
  skippedHoverInsideNotIsHas: setup.skippedNested,
  elementsMeasured: matched.length,
  candidateRules: setup.candidateRules,
  candidateDeclarations: setup.candidateDeclarations,
  declarationsRedundantHere: redundant.length,
  declarationsLoadBearingHere: needed.length,
};

if (OUT) {
  const file = artifactPath(OUT);
  writeFileSync(file, JSON.stringify({ summary, redundant, needed, candidatePreview: setup.candidatePreview }, null, 0));
  console.log(`LIFT_SUMMARY ${JSON.stringify(summary)} raw=${file}`);
  for (const r of needed) console.log('  LOAD-BEARING ' + r.prop.padEnd(22) + ' diffs=' + r.diffs + '  ' + r.selector);
} else if (AS_JSON) {
  console.log(JSON.stringify({ summary, redundant, needed, candidatePreview: setup.candidatePreview }, null, 0));
} else {
  console.log('URL ..................................... ' + URL);
  console.log('  :hover rules in CSSOM ................ ' + summary.hoverRulesInCssom);
  console.log('  elements measured (full computed style) ' + summary.elementsMeasured);
  console.log('  candidate rules (hover + !important) .. ' + summary.candidateRules);
  console.log('  candidate declarations ................ ' + summary.candidateDeclarations);
  console.log('  -> demotion changed NOTHING (redundant)  ' + summary.declarationsRedundantHere);
  console.log('  -> demotion CHANGED a computed value ...  ' + summary.declarationsLoadBearingHere);
  console.log('\n--- load-bearing (must keep) ---');
  for (const r of needed) console.log('  ' + r.prop.padEnd(22) + ' diffs=' + r.diffs + '  ' + r.selector);
}
await browser.close();
