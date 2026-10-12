/**
 * important-lift-test.mjs — decide, per DECLARATION, whether an `!important` on a
 * `:hover` rule is load-bearing or redundant, and report the shorthand grouping.
 *
 * The defect this version fixes
 * -----------------------------
 * The previous version enumerated candidates with
 *
 *     for (let k = 0; k < rule.style.length; k++) { const p = rule.style[k]; ... }
 *
 * CSSStyleDeclaration's indexed properties are LONGHANDS. On this Chrome, for
 *
 *     .ui-theme-menu button:hover {
 *       background: var(--app-surface-3) !important;
 *       transform: none !important;
 *     }
 *
 * `rule.style.length` is 10 (nine background longhands plus transform) while
 * `rule.style.cssText` is `background: var(--app-surface-3) !important;
 * transform: none !important;` — two authored declarations. The instrument
 * therefore reported one authored `!important` as nine independent candidates,
 * eight of them "inert", and the ninth (background-color) load-bearing. Acting on
 * the eight would have deleted the hover highlight on every page.
 *
 * Enumeration now
 * ---------------
 * Declarations are read from the serialized form (`rule.style.cssText`), which
 * preserves what was authored — measured, not assumed; the evidence is
 * tools/css-declaration-granularity.mjs, and it also shows the alternative,
 * CDP CSS.getMatchedStylesForNode (getMatchedStylesForNode=true,
 * setStyleTexts=true on this Chrome). The CSSOM serialization was chosen because
 * the candidate list is rule-driven while getMatchedStylesForNode is node-driven:
 * the same rule would have to be identified through every element that matches it.
 * Each declaration reports the longhands it expands to, so the grouping is
 * visible rather than lost.
 *
 * Method (leave-one-out, runtime-only, nothing is written to disk)
 *   1. Load the page; collect every `:hover` rule from the CSSOM, deriving each
 *      selector part's TRIGGER (the element that must be hovered) and its SUBJECT
 *      (the element whose style changes). A subject naming a pseudo-element keeps
 *      it: `.studio-panel-resizer:hover:after` is measured on the trigger's
 *      `::after`, which the previous version could not see at all.
 *   1b. (v2) A rule whose selector list mixes `:hover` with another state
 *      (`.final-timeline-row:hover, .final-timeline-row.active`) is now MEASURED on
 *      both paths instead of being written off: the class the selector names is
 *      added to the matching elements and a pseudo-class it names is forced over
 *      CDP. Only a state this harness cannot synthesize leaves a declaration
 *      unmeasured, and the reason is reported per rule. Before this, 19
 *      row-instances across 7 declarations were unmeasurable by construction — the
 *      largest single block of "no evidence" in the sweep — and a declaration whose
 *      only reachable path is `.active` could never be cleared on hover-only
 *      evidence either. Both directions are now measured, and a declaration is
 *      load-bearing if EITHER path changes a computed value.
 *   2. Snapshot the COMPLETE computed style — every property Chrome exposes — of
 *      the trigger, its `::before`/`::after`, and every subject, with hover forced,
 *      AFTER the forced state's motion has settled (v3). The read used to happen
 *      between `CSS.forcePseudoState` and its undo, so it could sample a
 *      mid-transition frame; that made the per-declaration verdict a per-run
 *      observation rather than a property of the tree. Five runs over the same
 *      page and tree split on three declarations (§1.1 of the instrument-repair
 *      report). `lib/motion-settle.mjs` waits — one frame, every finite running
 *      animation on the elements being read, then two frames — before the read.
 *      What is measured is unchanged; only when it is read. The instrument
 *      reports how often it found motion in flight (`settleStats`) so a reader can
 *      tell the fix was exercised rather than merely present.
 *   3. For each `!important` DECLARATION: rebuild the rule's declaration text
 *      without it, re-force hover on every element the rule can reach, and diff the
 *      complete computed style against the snapshot. Restore, and assert the
 *      restore round-trips (a per-declaration invariant; violations fail the run).
 *   4. A declaration whose removal changes nothing, anywhere, is redundant on this
 *      page. "Redundant here" stays a weaker claim than "safe to delete", which is
 *      why the sweep is per-page and every page must agree before source changes.
 *   4b. (v4) ... and only where the elements it reaches are RENDERED. A leave-one-out
 *      diff is an observation of computed values, and for an element with no box
 *      Chrome stops resolving used values: inside a `display:none` subtree
 *      `transform` reads `none` whatever the cascade says, so removal "changes
 *      nothing" in every run — a vacuous verdict, not an inert declaration.
 *      Measured on index.html (2026-10-12): `.ui-theme-menu button:hover`
 *      `transform: none !important` read `none` and reported 0 differences with the
 *      theme menu `[hidden]`, and `matrix(1.012, 0, 0, 1.012, 0, -2)` — a real
 *      change — once the menu was revealed; the unanimous 'demotable' verdict the
 *      expanded sweep produced for it was an artifact of measuring a closed menu.
 *      Such a declaration is now reported as UNMEASURED, with the count of elements
 *      reached and no box, and can never be pooled into a unanimous demotion.
 *      The rule is a precondition on the observation, not a change to what is
 *      measured: every read below is the same complete computed style it was
 *      before, taken at the same moment (v3).
 *
 * Self-check (fails the run, exit 3)
 *   1. Fixture: the rule text is read out of src/css/modern-ui.css — a tracked,
 *      hand-written file — injected into a throwaway stylesheet, and enumerated by
 *      the same code the sweep uses. `.ui-theme-menu button:hover` must report 2
 *      declarations (not 10 longhands), with `background` expanding to 9 longhands,
 *      and `input:hover,textarea:hover,select:hover` must report 1 (not 4).
 *   2. Cross-check: the same fixture rule is located through CDP
 *      getMatchedStylesForNode on a synthesized element, and its authored
 *      `cssProperties` must agree with the serialization on what is important.
 *   3. Per rule, during the sweep: the union of the declarations' longhand
 *      expansions must equal the set of longhands the rule marks important. A
 *      re-grouped or mis-parsed rule shows up here.
 *
 * Scope: rules whose selector list contains `:hover`, including the other state
 * parts of those same rules (v2). Every other `!important` in the tree is out of
 * reach of this method at a sane cost — the leave-one-out needs a computed-style
 * diff of every element a rule can reach, and the non-hover universe is 32,832
 * declarations against 3,911 elements. That boundary is stated in the report
 * rather than implied away.
 *
 * Force mechanism is CDP CSS.forcePseudoState (Chrome-only by design):
 *   https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-forcePseudoState
 *
 * Usage
 *   node tools/important-lift-test.mjs [url] [--json] [--cap=N] [--out=FILE]
 *   node tools/important-lift-test.mjs [url] --self-check-only
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { emulateHoverCapable, freezeMotion, launch, verifyHoverMediaRewrite } from './lib/browser.mjs';
import { MOTION_SETTLE_SOURCE } from './lib/motion-settle.mjs';
import { REPO_ROOT, artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const AS_JSON = hasFlag(argv, 'json');
const SELF_CHECK_ONLY = hasFlag(argv, 'self-check-only');
const CAP = Number((argv.find((a) => a.startsWith('--cap=')) || '--cap=10').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;

/** The fixture: a tracked hand-written file, and the two rules in it that use a shorthand with !important. */
const FIXTURE_FILE = resolve(REPO_ROOT, 'src', 'css', 'modern-ui.css');
const FIXTURE = [
  { selector: '.ui-theme-menu button:hover', declarations: 2, shorthands: { background: 9 } },
  { selector: 'input:hover,textarea:hover,select:hover', declarations: 1, shorthands: { 'border-color': 4 } },
];

const browser = await launch({ kind: 'full' });
const page = await browser.newPage();
await page.setViewport({ width: 1366, height: 900 });
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise((r) => setTimeout(r, 1200));
await freezeMotion(page);

// Declared simulation, not decoration: headless Chrome reports (hover:hover) as
// false and CDP cannot override it, so without this every @media(hover:hover)
// rule is switched off while the tool claims to be measuring hover states.
const hoverMedia = await emulateHoverCapable(page);

const cdp = await page.target().createCDPSession();
await cdp.send('DOM.enable');
await cdp.send('CSS.enable');
await cdp.send('DOM.getDocument', { depth: -1, pierce: true });

// Style sheets are identified by id, so the fixture sheet the self-check injects
// can be told apart from the 40 the page already loaded, instead of guessed at
// from a selector match.
const sheetIds = [];
cdp.on('CSS.styleSheetAdded', (e) => sheetIds.push(e.header.styleSheetId));

await page.addScriptTag({ content: readFileSync(resolve(REPO_ROOT, 'tools', 'lib', 'css-decl.js'), 'utf8') });
// (v3) The settle helper every read below goes through. Injected the same way as
// the declaration parser, so one implementation serves the self-check and the
// sweep.
await page.addScriptTag({ content: MOTION_SETTLE_SOURCE });

// ---------------------------------------------------------------------------
// Self-check 1: the fixture, through the same code the sweep uses.
// ---------------------------------------------------------------------------
const fixtureText = readFileSync(FIXTURE_FILE, 'utf8');
/** Lift a rule's declaration block verbatim out of the file text (pure text, no CSSOM). */
function ruleTextFromFile(text, selector) {
  const at = text.indexOf(selector);
  if (at === -1) return null;
  const open = text.indexOf('{', at);
  const close = text.indexOf('}', open);
  if (open === -1 || close === -1) return null;
  return { selector, body: text.slice(open + 1, close).trim() };
}
const fixtureRules = FIXTURE.map((f) => {
  const found = ruleTextFromFile(fixtureText, f.selector);
  if (!found) throw new Error(`self-check: ${f.selector} not found in ${FIXTURE_FILE}`);
  return { ...f, body: found.body };
});
const sheetCountBeforeFixture = sheetIds.length;

// The marker is what identifies the fixture sheet later: the fixture body is copied
// from a file this page also bundles, so the declaration text itself is not unique.
const FIXTURE_MARKER = `decl-fixture-marker-${process.pid}`;
const selfCheck = await page.evaluate((rules, marker) => {
  const { parseDeclarations, declarationsOf, longhandNamesOf } = globalThis.CssDecl;
  // The fixture keeps its real selector: the CDP cross-check below has to find it
  // through a node, and the DOM it needs is synthesized to match.
  const host = document.createElement('style');
  host.textContent = `/* ${marker} */\n` + rules.map((r) => `${r.selector}{${r.body}}`).join('\n');
  (document.head || document.documentElement).appendChild(host);
  const out = [];
  for (let i = 0; i < rules.length; i++) {
    const rule = host.sheet.cssRules[i];
    // 1a — the declaration-level enumeration, on the live rule.
    const { declarations } = declarationsOf(rule);
    // 1b — the same parser against the file text, independent of any serialization.
    const fromFileText = parseDeclarations(rules[i].body);
    // 1c — what the longhand model would have reported: the number the defect produced.
    const longhandModel = longhandNamesOf(rule).length;
    out.push({
      selector: rules[i].selector,
      declarationCount: declarations.length,
      fromFileTextCount: fromFileText.length,
      longhandModelCount: longhandModel,
      ruleCssText: rule.cssText,
      declarations: declarations.map((d) => ({
        name: d.name, value: d.value, important: d.important,
        longhands: d.longhands, isShorthand: d.isShorthand,
      })),
    });
  }
  return out;
}, fixtureRules, FIXTURE_MARKER);

// `CSS.styleSheetAdded` is delivered on a later tick, so the sheet id is waited
// for rather than read straight after the injection. It is then confirmed by its
// TEXT: the fixture body is copied from a file that this page also bundles, so a
// text match alone would find the bundled copy first.
async function resolveFixtureSheet(before, timeoutMs = 3000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const added = sheetIds.slice(before);
    for (let i = added.length - 1; i >= 0; i--) {
      try {
        const { text } = await cdp.send('CSS.getStyleSheetText', { styleSheetId: added[i] });
        if (text && text.includes(FIXTURE_MARKER)) return added[i];
      } catch { /* sheet went away */ }
    }
    await new Promise((r) => setTimeout(r, 50));
  }
  return null;
}
const fixtureSheetId = await resolveFixtureSheet(sheetCountBeforeFixture);

// ---------------------------------------------------------------------------
// Self-check 2: CDP getMatchedStylesForNode must agree with the serialization.
// ---------------------------------------------------------------------------
const fixtureNode = await page.evaluate(() => {
  // Synthesize the DOM the fixture rule targets, so the rule has a node to match.
  // `:hover` is a valid selector but matches nothing un-hovered, so the node is
  // addressed by a plain selector and the state is forced over CDP below.
  const wrap = document.createElement('div');
  wrap.className = 'ui-theme-menu decl-fixture-host';
  const btn = document.createElement('button');
  btn.textContent = 'fixture';
  wrap.appendChild(btn);
  document.body.appendChild(wrap);
  return { selector: '.decl-fixture-host button', ok: !!document.querySelector('.decl-fixture-host button') };
});

let cdpCrossCheck = {
  available: false, agrees: null, authored: [], serialized: [],
  sheetId: fixtureSheetId, sheetsBefore: sheetCountBeforeFixture, sheetsAfter: sheetIds.length,
};
if (fixtureNode.ok && fixtureSheetId) {
  const { root } = await cdp.send('DOM.getDocument', { depth: -1 });
  const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: fixtureNode.selector });
  if (nodeId) {
    try {
      const sheetText = (await cdp.send('CSS.getStyleSheetText', { styleSheetId: fixtureSheetId })).text || '';
      cdpCrossCheck.sheetTextHasFixture = sheetText.includes(FIXTURE[0].selector);
      // A rule whose selector carries :hover is not in matchedCSSRules until the
      // state is forced, so force it on the fixture node.
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
      const matched = await cdp.send('CSS.getMatchedStylesForNode', { nodeId });
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
      cdpCrossCheck.available = true;
      const rulesForNode = (matched.matchedCSSRules || []).map((m) => m.rule)
        .filter((r) => r.styleSheetId === fixtureSheetId);
      // CDP's cssProperties does NOT hand back the authored form directly:
      // measured on this Chrome, one `background: var(...) !important` arrives as
      // 2 authored entries plus 10 fragments (the shorthand, `transform`, then the
      // nine background longhands and `transform` again) with `longhandProperties`
      // empty on all of them. What separates the two is `range`: only an authored
      // declaration carries a source range. `shorthandEntries` is populated but
      // lists shorthands only (it has `background` and not `transform`), so it is
      // recorded rather than used on its own.
      const authored = [];
      let fragmentEntries = 0;
      const shorthandEntries = [];
      for (const r of rulesForNode) {
        const style = r.style || {};
        const props = style.cssProperties || [];
        for (const p of props) {
          if (p.range) { if (p.important) authored.push(p.name); } else fragmentEntries++; }
        for (const s of (style.shorthandEntries || [])) shorthandEntries.push(s.name);
      }
      cdpCrossCheck.fragmentEntries = fragmentEntries;
      cdpCrossCheck.shorthandEntries = shorthandEntries;
      cdpCrossCheck.matchedRules = rulesForNode.length;
      const serialized = selfCheck[0].declarations.filter((d) => d.important).map((d) => d.name);
      cdpCrossCheck.authored = [...new Set(authored)].sort();
      cdpCrossCheck.serialized = [...new Set(serialized)].sort();
      cdpCrossCheck.agrees = cdpCrossCheck.authored.join('|') === cdpCrossCheck.serialized.join('|');
    } catch (err) {
      cdpCrossCheck.error = String(err.message || err);
    }
  }
}

const selfCheckFailures = [];
for (const [i, expected] of FIXTURE.entries()) {
  const got = selfCheck[i];
  if (got.declarationCount !== expected.declarations) {
    selfCheckFailures.push(`${expected.selector}: ${got.declarationCount} declarations, expected ${expected.declarations}`);
  }
  if (got.fromFileTextCount !== expected.declarations) {
    selfCheckFailures.push(`${expected.selector}: file-text parser found ${got.fromFileTextCount} declarations, expected ${expected.declarations}`);
  }
  for (const [name, longhands] of Object.entries(expected.shorthands)) {
    const d = got.declarations.find((x) => x.name === name);
    if (!d) selfCheckFailures.push(`${expected.selector}: no declaration named ${name}`);
    else if (d.longhands.length !== longhands) {
      selfCheckFailures.push(`${expected.selector}: ${name} expands to ${d.longhands.length} longhands, expected ${longhands}`);
    }
  }
  if (got.declarationCount >= got.longhandModelCount) {
    selfCheckFailures.push(`${expected.selector}: declaration count (${got.declarationCount}) must be below the longhand count (${got.longhandModelCount}) — the enumeration did not collapse the shorthand`);
  }
}
if (!cdpCrossCheck.available) {
  selfCheckFailures.push(`CDP cross-check did not run (sheetId=${fixtureSheetId}, node=${fixtureNode.ok})${cdpCrossCheck.error ? ': ' + cdpCrossCheck.error : ''}`);
} else if (cdpCrossCheck.agrees === false) {
  selfCheckFailures.push(
    `CDP authored ${JSON.stringify(cdpCrossCheck.authored)} != serialized ${JSON.stringify(cdpCrossCheck.serialized)}`
    + `\n    CDP entries: ${JSON.stringify(cdpCrossCheck.entries)}`,
  );
}

// Self-check 4: the hover-capable simulation must have taken effect. If the
// rewrite silently failed, every verdict below is measured on a touch-first page.

const mediaRewrite = await verifyHoverMediaRewrite(page, hoverMedia.rewrittenCount);
if (!mediaRewrite.markerCountMatches) {
  selfCheckFailures.push(`hover media simulation rewrote ${hoverMedia.rewrittenCount} rule(s) but only ${mediaRewrite.rewritten.length} carry the rewrite marker`);
}
if (mediaRewrite.stillInactive.length) {
  selfCheckFailures.push(`${mediaRewrite.stillInactive.length} rewritten media rule(s) still report matches=false`);
}

const selfCheckReport = {
  fixtureFile: 'src/css/modern-ui.css',
  rules: selfCheck,
  cdpCrossCheck,
  hoverMedia,
  mediaRewrite,
  failures: selfCheckFailures,
};
console.log('SELF_CHECK ' + JSON.stringify({
  fixture: selfCheck.map((r) => ({
    selector: r.selector, declarations: r.declarationCount,
    fromFileText: r.fromFileTextCount, longhandModelWouldReport: r.longhandModelCount,
  })),
  cdp: { available: cdpCrossCheck.available, agrees: cdpCrossCheck.agrees },
  hoverMedia: {
    hoverCapableByDefault: hoverMedia.mediaHoverCapableBefore,
    clausesFound: hoverMedia.clausesFound,
    rewritten: hoverMedia.rewrittenCount,
    stillInactiveAfter: mediaRewrite.stillInactive.length,
  },
  failures: selfCheckFailures.length,
}));
if (selfCheckFailures.length) {
  for (const f of selfCheckFailures) console.error('  SELF-CHECK FAILURE: ' + f);
  console.error('SELF_CHECK_FAILED — refusing to report verdicts from a broken enumerator.');
  await browser.close();
  process.exit(3);
}

if (SELF_CHECK_ONLY) {
  console.log('SELF_CHECK_PASSED');
  await browser.close();
  process.exit(0);
}

// ---------------------------------------------------------------------------
// (v4) Tear the fixture down before the sweep runs.
// ---------------------------------------------------------------------------
// The self-check has to inject its fixture rule and synthesize a DOM for it. That
// synthesized host is `div.ui-theme-menu.decl-fixture-host > button` — a REAL,
// RENDERED element that matches any rule this page already has for
// `.ui-theme-menu button` (and for a bare `button`). Measured on dashboard.html
// (2026-10-12) before this teardown: the candidate `.ui-theme-menu button:hover`
// reported 3 targets, the third being
// `button rects=1 hidden=false parent=div.ui-theme-menu.decl-fixture-host`, i.e. the
// probe was sweeping its own scaffolding, and the fixture sheet's copy of the rule
// was enumerated as a second rule with the same selector. Both are removed here, so
// what the sweep measures is the page's own DOM and the page's own stylesheets.
const fixtureTeardown = await page.evaluate((marker) => {
  const removed = { styleSheets: 0, hosts: 0 };
  for (const el of [...document.querySelectorAll('style')]) {
    if (el.textContent && el.textContent.includes(marker)) { el.remove(); removed.styleSheets++; }
  }
  for (const el of [...document.querySelectorAll('.decl-fixture-host')]) { el.remove(); removed.hosts++; }
  return {
    ...removed,
    fixtureRulesLeft: [...document.styleSheets].flatMap((s) => { try { return [...s.cssRules]; } catch { return []; } })
      .filter((r) => r.selectorText === '.ui-theme-menu button:hover').length,
    fixtureHostsLeft: document.querySelectorAll('.decl-fixture-host').length,
  };
}, FIXTURE_MARKER);
if (fixtureTeardown.styleSheets !== 1 || fixtureTeardown.hosts !== 1 || fixtureTeardown.fixtureHostsLeft !== 0) {
  console.error('SELF_CHECK_FAILED — the fixture the self-check injected is still in the page: ' + JSON.stringify(fixtureTeardown));
  await browser.close();
  process.exit(3);
}
selfCheckReport.fixtureTeardown = fixtureTeardown;
console.log('SELF_CHECK_TEARDOWN ' + JSON.stringify(fixtureTeardown));

// ---------------------------------------------------------------------------
// Enumerate every `!important` DECLARATION in a `:hover` rule, and the targets.
// ---------------------------------------------------------------------------
const setup = await page.evaluate((cap) => {
  const { declarationsOf } = globalThis.CssDecl;
  // (v4) Does this element have a box at all? A leave-one-out diff can only
  // observe a change on an element that is RENDERED: for an element inside a
  // `display:none` subtree Chrome resolves `transform` to `none` (and, more
  // generally, stops resolving used values), so a declaration that governs it can
  // look inert on every run. Measured on index.html (2026-10-12): removing
  // `transform: none !important` from `.ui-theme-menu button:hover` left the value
  // reading `none` while the menu was `[hidden]`, and produced
  // `matrix(1.012, 0, 0, 1.012, 0, -2)` once the menu was revealed — same page,
  // same declaration, opposite verdicts. `getClientRects().length > 0` is the
  // predicate: an element with no box cannot be hovered by a user either, so
  // nothing about it is observable in this harness.
  const isRendered = (el) => { try { return el.getClientRects().length > 0; } catch { return false; } };
  const hoverRules = [];
  const walk = (rules) => {
    for (const rule of rules) {
      if (rule.cssRules && rule.constructor.name !== 'CSSStyleRule') { walk(rule.cssRules); continue; }
      if (rule.selectorText && rule.selectorText.includes(':hover')) hoverRules.push(rule);
    }
  };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch { /* opaque */ } }

  // A subject may name a pseudo-element; keep it, so the measurement lands on the
  // box the rule actually paints (`.x:hover:after` is invisible otherwise).
  const PSEUDO = /::?(before|after|marker|placeholder|first-line|first-letter|selection|backdrop)$/i;
  // (v2) A NON-:hover state part: the class or pseudo-class the selector names,
  // which this harness can force on the elements the part matches. `base` is the
  // rest of the part, and is what gets queried.
  const STATE_PSEUDO = /:(focus-visible|focus-within|focus|active|checked|target)$/;
  const parseStatePart = (s) => {
    const pm = STATE_PSEUDO.exec(s);
    if (pm) {
      const base = s.slice(0, pm.index).trim();
      return base ? { base, cls: null, pseudo: pm[1], raw: s } : null;
    }
    const cm = /\.([A-Za-z_][\w-]*)$/.exec(s);
    if (cm) {
      const base = s.slice(0, cm.index).trim();
      return base ? { base, cls: cm[1], pseudo: null, raw: s } : null;
    }
    return null;
  };
  const stateSpecs = new Map(); // spec key -> {base, cls, pseudo} to apply
  const stateKeyOf = (p) => `${p.base}|${p.cls || ''}|${p.pseudo || ''}`;
  const byTrigger = new Map();
  const candidates = [];
  let skippedNested = 0;
  let pseudoSubjects = 0;
  const groupingMismatches = [];
  let declarationsEnumerated = 0;
  let longhandsEnumerated = 0;
  let declarationsShared = 0;
  for (const rule of hoverRules) {
    const triggers = new Set();
    const subjects = new Map(); // base selector -> Set(pseudo|null)
    for (const part of rule.selectorText.split(',')) {
      const s = part.trim();
      if (!s.includes(':hover')) continue;
      if (/:not\(|:is\(|:has\(/.test(s)) { skippedNested++; continue; }
      const idx = s.indexOf(':hover');
      const trig = s.slice(0, idx).replace(/[>+~]\s*$/, '').trim();
      if (!trig) { skippedNested++; continue; }
      const raw = s.replace(/:hover/g, '').replace(/\s+/g, ' ').trim();
      const m = PSEUDO.exec(raw);
      const base = m ? raw.slice(0, m.index).trim() : raw;
      const pseudo = m ? '::' + m[1].toLowerCase() : null;
      if (!base) { skippedNested++; continue; }
      triggers.add(trig);
      if (!subjects.has(base)) subjects.set(base, new Set());
      subjects.get(base).add(pseudo);
      if (pseudo) pseudoSubjects++;
    }
    // A trigger is shared across rules: every subject any rule reaches through it
    // belongs to that trigger's target set, so a removal re-measures all of them.
    for (const trig of triggers) {
      if (!byTrigger.has(trig)) byTrigger.set(trig, new Map());
      const acc = byTrigger.get(trig);
      for (const [base, pseudos] of subjects) {
        if (!acc.has(base)) acc.set(base, new Set());
        for (const p of pseudos) acc.get(base).add(p);
      }
    }
    // (v2) A rule may also target a NON-:hover state — `.row:hover, .row.active` is
    // one declaration governing both. Both paths are now forced and measured; the
    // declaration is unmeasured only when a state part cannot be synthesized (the
    // reason is carried out with the row).
    const selectorParts = rule.selectorText.split(',').map((s) => s.trim()).filter(Boolean);
    const stateKeys = [];
    let unsupportedStatePart = null;
    for (const part of selectorParts) {
      if (part.includes(':hover')) continue;
      const spec = parseStatePart(part);
      if (!spec) { unsupportedStatePart = part; continue; }
      const key = stateKeyOf(spec);
      if (!stateSpecs.has(key)) stateSpecs.set(key, spec);
      if (!stateKeys.includes(key)) stateKeys.push(key);
    }
    const sharedWithNonHover = unsupportedStatePart !== null;
    const unsupportedReason = unsupportedStatePart
      ? `the rule also targets \`${unsupportedStatePart.slice(0, 60)}\`, a state this harness cannot synthesize`
      : null;
    const { declarations } = declarationsOf(rule);
    const important = declarations.filter((d) => d.important);
    // 3 — per-rule invariant: the important longhands the declarations cover must be
    // exactly the longhands the rule marks important.
    const covered = new Set();
    for (const d of important) for (const l of d.longhands) covered.add(l);
    const actual = new Set();
    for (let k = 0; k < rule.style.length; k++) {
      const p = rule.style[k];
      if (rule.style.getPropertyPriority(p) === 'important') actual.add(p);
    }
    const missing = [...actual].filter((n) => !covered.has(n));
    const extra = [...covered].filter((n) => !actual.has(n));
    if (missing.length || extra.length) {
      groupingMismatches.push({
        selector: rule.selectorText.slice(0, 120),
        declarations: important.map((d) => d.name),
        missing, extra,
      });
    }
    declarationsEnumerated += important.length;
    for (const d of important) longhandsEnumerated += d.longhands.length;
    if (sharedWithNonHover) declarationsShared += important.length;
    if (important.length && triggers.size) {
      candidates.push({
        rule, declarations: important, triggers: [...triggers], sharedWithNonHover,
        stateKeys, unsupportedReason,
        subjects: [...subjects].map(([base, pseudos]) => ({ base, pseudos: [...pseudos] })),
      });
    }
  }

  const targets = [];
  let triggersWithNoMatch = 0, triggersCapped = 0, invalid = 0;
  for (const [trigger, subjectMap] of byTrigger) {
    let els;
    try { els = [...document.querySelectorAll(trigger)]; } catch { invalid++; continue; }
    if (!els.length) { triggersWithNoMatch++; continue; }
    if (els.length > cap) triggersCapped++;
    for (const el of els.slice(0, cap)) {
      const subjectEls = [];
      for (const [base, pseudos] of subjectMap) {
        let found;
        try { found = [...document.querySelectorAll(base)]; } catch { continue; }
        for (const e of found) {
          for (const p of pseudos) {
            if (!subjectEls.some((s) => s.el === e && s.pseudo === p)) subjectEls.push({ el: e, pseudo: p });
          }
        }
      }
      // (v4) `rendered` is about the TRIGGER — the element whose state is forced. A
      // subject without a box cannot produce a diff either, so it cannot turn an
      // unobservable read into an observable one; and a subject that IS rendered while
      // its trigger is not is a *different* element's style, which this rule's `:hover`
      // cannot reach. (Measured on index.html: counting subjects as rendering the target
      // reported 28 rendered targets for `input:hover, textarea:hover, select:hover`
      // where the page has 340 form controls and 3 with a box.)
      targets.push({ el, subjectEls, trigger, rendered: isRendered(el) });
    }
  }

  const byTriggerIdx = new Map();
  targets.forEach((t, i) => {
    if (!byTriggerIdx.has(t.trigger)) byTriggerIdx.set(t.trigger, []);
    byTriggerIdx.get(t.trigger).push(i);
  });

  // (v2) Resolve the state parts to elements: one entry per element that must have
  // the class added / the pseudo-class forced while the leave-one-out runs.
  const stateTargets = [];
  let stateUnresolved = 0;
  for (const [key, spec] of stateSpecs) {
    let els;
    try { els = [...document.querySelectorAll(spec.base)]; } catch { stateUnresolved++; continue; }
    if (!els.length) { stateUnresolved++; continue; }
    for (const el of els.slice(0, cap)) stateTargets.push({ el, key, cls: spec.cls, pseudo: spec.pseudo, rendered: isRendered(el) });
  }
  const stateIdxByKey = new Map();
  stateTargets.forEach((t, i) => {
    if (!stateIdxByKey.has(t.key)) stateIdxByKey.set(t.key, []);
    stateIdxByKey.get(t.key).push(i);
  });

  window.__lift = {
    targets: targets.map((t) => ({ el: t.el, subjectEls: t.subjectEls, rendered: t.rendered })),
    stateTargets: stateTargets.map((t) => ({ el: t.el, cls: t.cls, pseudo: t.pseudo, rendered: t.rendered })),
    candidates: candidates.map((c) => ({
      declarations: c.declarations.map((d) => ({ name: d.name, longhands: d.longhands })),
      rule: c.rule,
      sharedWithNonHover: c.sharedWithNonHover,
      unsupportedReason: c.unsupportedReason,
      stateIndices: [...new Set(c.stateKeys.flatMap((k) => stateIdxByKey.get(k) || []))],
      indices: [...new Set(c.triggers.flatMap((t) => byTriggerIdx.get(t) || []))],
    })),
  };

  return {
    hoverRulesTotal: hoverRules.length,
    skippedNested,
    pseudoSubjects,
    stateTargetCount: stateTargets.length,
    stateSpecsUnresolved: stateUnresolved,
    distinctTriggers: byTrigger.size,
    invalidSelectors: invalid,
    triggersWithNoMatch,
    triggersCapped,
    targetCount: targets.length,
    // (v4) How many of those targets can carry an observation at all.
    targetsRendered: targets.filter((t) => t.rendered).length,
    targetsNotRendered: targets.filter((t) => !t.rendered).length,
    stateTargetsRendered: stateTargets.filter((t) => t.rendered).length,
    candidateRules: candidates.length,
    candidateDeclarations: declarationsEnumerated,
    candidateLonghands: longhandsEnumerated,
    declarationsSharedWithNonHover: declarationsShared,
    groupingMismatches,
    candidatePreview: candidates.slice(0, 200).map((c) => ({
      sel: c.rule.selectorText.slice(0, 74),
      declarations: c.declarations.map((d) => d.name),
      longhands: c.declarations.reduce((n, d) => n + d.longhands.length, 0),
      targets: [...new Set(c.triggers.flatMap((t) => byTriggerIdx.get(t) || []))].length,
    })),
  };
}, CAP);

const groupingMismatches = setup.groupingMismatches.length;
if (groupingMismatches) {
  console.error(`LIFT_GROUPING_FAILED — ${groupingMismatches} rule(s) where the declarations do not cover the important longhands:`);
  for (const g of setup.groupingMismatches.slice(0, 10)) console.error('  ' + JSON.stringify(g));
}

async function nodeIdFor(i) {
  const { result: remote } = await cdp.send('Runtime.evaluate', {
    expression: 'window.__lift.targets[' + i + '].el', returnByValue: false,
  });
  if (!remote || !remote.objectId) return null;
  try { const { nodeId } = await cdp.send('DOM.requestNode', { objectId: remote.objectId }); return nodeId; }
  catch { return null; }
}

/**
 * Capture the complete computed style of the trigger, its pseudo-elements, and
 * every subject (on its declared pseudo-element when it names one).
 */
const CAPTURE = async (idx) => {
  const t = window.__lift.targets[idx];
  // (v3) WHEN the read happens: after the forced state's motion settles, not
  // between the force and its undo. Every element about to be read is settled,
  // including the subjects on their declared pseudo-element.
  await globalThis.MotionSettle.settleAll([t.el, ...t.subjectEls.map((s) => s.el)]);
  const styleOf = (el, pseudo) => {
    if (!el || !el.isConnected) return null;
    const cs = getComputedStyle(el, pseudo);
    let s = '';
    for (let k = 0; k < cs.length; k++) { const p = cs[k]; s += p + ':' + cs.getPropertyValue(p) + ';'; }
    return s;
  };
  return {
    self: styleOf(t.el, null),
    selfBefore: styleOf(t.el, '::before'),
    selfAfter: styleOf(t.el, '::after'),
    subjects: t.subjectEls.map((s) => styleOf(s.el, s.pseudo)),
  };
};

/**
 * (v2) The same capture for an element reached through a rule's NON-:hover state
 * part. The class the selector names is already added (or the pseudo-class forced)
 * when this runs, so this is the state's own computed style.
 */
const CAPTURE_STATE = async (idx) => {
  const t = window.__lift.stateTargets[idx];
  // (v3) Same settle as CAPTURE: the class was just added / the pseudo-class just
  // forced, so a transition on the state path is exactly as sampleable mid-flight.
  await globalThis.MotionSettle.settleAll([t.el]);
  const styleOf = (el, pseudo) => {
    if (!el || !el.isConnected) return null;
    const cs = getComputedStyle(el, pseudo);
    let s = '';
    for (let k = 0; k < cs.length; k++) { const p = cs[k]; s += p + ':' + cs.getPropertyValue(p) + ';'; }
    return s;
  };
  return { self: styleOf(t.el, null), selfBefore: styleOf(t.el, '::before'), selfAfter: styleOf(t.el, '::after') };
};

// ---------------------------------------------------------------------------
// 2 — baseline: complete computed style with hover forced.
// ---------------------------------------------------------------------------
const t0 = Date.now();
const matched = [];
const baseline = new Map();
for (let i = 0; i < setup.targetCount; i++) {
  const nodeId = await nodeIdFor(i);
  if (nodeId === null) continue;
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
  const snap = await page.evaluate(CAPTURE, i);
  await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
  if (!snap) continue;
  baseline.set(i, snap);
  matched.push({ i, nodeId });
}

// ---------------------------------------------------------------------------
// 3 — leave-one-out: remove ONE DECLARATION, re-measure, restore.
// ---------------------------------------------------------------------------
function diffSnapshots(base, snap) {
  const changes = [];
  const keys = ['self', 'selfBefore', 'selfAfter'];
  for (const k of keys) {
    if (snap[k] !== base[k]) changes.push({ where: k, from: base[k], to: snap[k] });
  }
  for (let s = 0; s < (snap.subjects || []).length; s++) {
    if (snap.subjects[s] !== (base.subjects || [])[s]) {
      changes.push({ where: `subject[${s}]`, from: (base.subjects || [])[s], to: snap.subjects[s] });
    }
  }
  return changes;
}

function firstDifference(from, to) {
  const a = String(from || '').split(';');
  const b = String(to || '').split(';');
  const out = [];
  for (let k = 0; k < Math.min(a.length, b.length); k++) if (a[k] !== b[k]) out.push(a[k] + ' -> ' + b[k]);
  return out.slice(0, 4);
}

const nodeIdByIndex = new Map(matched.map((m) => [m.i, m.nodeId]));

// (v2) Baseline for the non-:hover state paths: the same complete-style capture,
// taken with the state applied (class added, or pseudo-class forced over CDP) and
// WITHOUT :hover, because these are the elements a `X:hover, X.active` rule reaches
// through its other selector part.
async function stateNodeIdFor(i) {
  const { result: remote } = await cdp.send('Runtime.evaluate', {
    expression: 'window.__lift.stateTargets[' + i + '].el', returnByValue: false,
  });
  if (!remote || !remote.objectId) return null;
  try { const { nodeId } = await cdp.send('DOM.requestNode', { objectId: remote.objectId }); return nodeId; }
  catch { return null; }
}
const applyState = async (i, on) => page.evaluate((k, add) => {
  const t = window.__lift.stateTargets[k];
  if (t.cls) { if (add) t.el.classList.add(t.cls); else t.el.classList.remove(t.cls); }
  return { pseudo: t.pseudo, cls: t.cls };
}, i, on);

const stateBaseline = new Map();
const stateMatched = [];
const stateNodeIds = new Map();
for (let i = 0; i < setup.stateTargetCount; i++) {
  const meta = await applyState(i, true);
  let nodeId = stateNodeIds.get(i) ?? null;
  if (nodeId === null) { nodeId = await stateNodeIdFor(i); if (nodeId !== null) stateNodeIds.set(i, nodeId); }
  if (nodeId !== null && meta.pseudo) await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [meta.pseudo] });
  const snap = await page.evaluate(CAPTURE_STATE, i);
  if (nodeId !== null && meta.pseudo) await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
  await applyState(i, false);
  if (!snap) continue;
  stateBaseline.set(i, snap);
  stateMatched.push(i);
}
const results = [];
let restoreFailures = 0;
for (let ci = 0; ci < setup.candidateRules; ci++) {
  const cand = await page.evaluate((k) => {
    const c = window.__lift.candidates[k];
    return {
      declarations: c.declarations,
      indices: c.indices,
      stateIndices: c.stateIndices,
      unsupportedReason: c.unsupportedReason || null,
      sharedWithNonHover: c.sharedWithNonHover === true,
      sel: c.rule.selectorText.slice(0, 90),
      originalCssText: c.rule.style.cssText,
      // (v4) Which of this rule's reachable elements have a box, and so can carry
      // an observation. Empty means the leave-one-out below would be vacuous.
      renderedIndices: c.indices.filter((i) => window.__lift.targets[i] && window.__lift.targets[i].rendered),
      renderedStateIndices: (c.stateIndices || []).filter((i) => window.__lift.stateTargets[i] && window.__lift.stateTargets[i].rendered),
    };
  }, ci);
  const rows = [];
  for (const decl of cand.declarations) {
    const affected = cand.indices.filter((i) => nodeIdByIndex.has(i) && baseline.has(i));
    const stateAffected = (cand.stateIndices || []).filter((i) => stateBaseline.has(i));
    const renderedAffected = cand.renderedIndices.filter((i) => nodeIdByIndex.has(i) && baseline.has(i));
    const renderedStateAffected = cand.renderedStateIndices.filter((i) => stateBaseline.has(i));
    if (cand.sharedWithNonHover) {
      rows.push({
        name: decl.name, longhands: decl.longhands, diffs: 0, affected: affected.length, unmeasured: true,
        note: cand.unsupportedReason || 'the rule also targets a non-:hover selector, which this harness does not measure',
        sample: [],
      });
      continue;
    }
    if (!affected.length && !stateAffected.length) {
      // Not "redundant": unmeasured. A declaration no element on this page reaches —
      // through :hover or through the rule's other state parts — cannot be cleared
      // here, and it must not be counted as demotable anywhere.
      rows.push({ name: decl.name, longhands: decl.longhands, diffs: 0, affected: 0, unmeasured: true, note: 'no element on this page reaches this rule', sample: [] });
      continue;
    }
    if (!renderedAffected.length && !renderedStateAffected.length) {
      // (v4) Reached, but not observable: every element this rule reaches exists in
      // the DOM without a box (a `display:none` subtree — a closed popover, a hidden
      // panel). Chrome does not resolve used values for such an element, so the
      // leave-one-out below returns the identical snapshot no matter what the
      // declaration says, in every run: a vacuous verdict, not an inert declaration.
      // It is reported as unmeasured with the reason, so it can never be pooled into
      // a unanimous demotion. `tools/demotion-recheck.mjs` is the instrument that
      // answers the question this page state cannot (`--reveal`).
      rows.push({
        name: decl.name, longhands: decl.longhands, diffs: 0, affected: affected.length + stateAffected.length,
        stateAffected: stateAffected.length, stateDiffs: 0, sample: [], unmeasured: true, notRendered: true,
        note: `${affected.length + stateAffected.length} element(s) reached, none rendered (no box: a display:none subtree), so no computed value can be observed here`,
      });
      continue;
    }
    // Remove this ONE declaration by rebuilding the rule's declaration text.
    const removed = await page.evaluate((k, name) => {
      const rule = window.__lift.candidates[k].rule;
      const all = globalThis.CssDecl.parseDeclarations(rule.style.cssText);
      const keep = all.filter((d) => d.name !== name).map((d) => d.text).join('; ');
      rule.style.cssText = keep;
      return { applied: rule.style.cssText, removedAny: keep !== all.map((d) => d.text).join('; ') };
    }, ci, decl.name);
    let diffs = 0;
    const sample = [];
    for (const i of affected) {
      const nodeId = nodeIdByIndex.get(i);
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover'] });
      const snap = await page.evaluate(CAPTURE, i);
      await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
      const base = baseline.get(i);
      if (!snap) continue;
      const changes = diffSnapshots(base, snap);
      if (changes.length) {
        diffs += changes.length;
        if (sample.length < 3) {
          sample.push({ element: i, where: changes[0].where, changed: firstDifference(changes[0].from, changes[0].to) });
        }
      }
    }
    // (v2) The same leave-one-out along the rule's non-:hover state path. A
    // declaration that changes a computed value in EITHER state is load-bearing.
    let stateDiffs = 0;
    for (const i of stateAffected) {
      const meta = await applyState(i, true);
      const nodeId = stateNodeIds.get(i) ?? null;
      if (nodeId !== null && meta.pseudo) await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [meta.pseudo] });
      const snap = await page.evaluate(CAPTURE_STATE, i);
      if (nodeId !== null && meta.pseudo) await cdp.send('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
      await applyState(i, false);
      if (!snap) continue;
      const changes = diffSnapshots(stateBaseline.get(i), snap);
      if (changes.length) {
        diffs += changes.length;
        stateDiffs += changes.length;
        if (sample.length < 3) {
          sample.push({ element: i, where: `state:${changes[0].where}`, changed: firstDifference(changes[0].from, changes[0].to) });
        }
      }
    }
    const restored = await page.evaluate((k, original) => {
      const rule = window.__lift.candidates[k].rule;
      rule.style.cssText = original;
      return rule.style.cssText;
    }, ci, cand.originalCssText);
    if (restored !== cand.originalCssText) restoreFailures++;
    rows.push({
      name: decl.name, longhands: decl.longhands, diffs, affected: affected.length + stateAffected.length,
      stateAffected: stateAffected.length, stateDiffs, sample, removedAny: removed.removedAny,
      rendered: renderedAffected.length + renderedStateAffected.length,
    });
  }
  results.push({ i: ci, selector: cand.sel, declarations: rows });
}

const measureMs = Date.now() - t0;
const measurements = nodeIdByIndex.size;
// (v3) How often a read found motion in flight and waited for it. Non-zero means
// the fix was exercised on this page, not merely present in the source.
const settleStats = await page.evaluate(() => globalThis.MotionSettle.stats);
const redundant = [], needed = [], unmeasured = [];
for (const r of results) for (const d of r.declarations) {
  const row = {
    selector: r.selector, declaration: d.name, longhands: d.longhands.length,
    diffs: d.diffs, affected: d.affected ?? 0, sample: d.sample,
    stateDiffs: d.stateDiffs ?? 0, stateAffected: d.stateAffected ?? 0,
    rendered: d.rendered ?? 0,
  };
  if (d.note) row.note = d.note;
  if (d.notRendered) row.notRendered = true;
  if (d.unmeasured) unmeasured.push(row);
  else if (!d.diffs) redundant.push(row);
  else needed.push(row);
}

const summary = {
  url: URL,
  hoverRulesInCssom: setup.hoverRulesTotal,
  distinctTriggerSelectors: setup.distinctTriggers,
  triggersMatchingNothing: setup.triggersWithNoMatch,
  skippedHoverInsideNotIsHas: setup.skippedNested,
  pseudoElementSubjects: setup.pseudoSubjects,
  elementsMeasured: matched.length,
  // (v4) A target without a box cannot carry an observation. Reported so a reader
  // can see how much of the sweep's evidence came from rendered elements.
  targetsInScope: setup.targetCount,
  targetsRendered: setup.targetsRendered,
  targetsNotRendered: setup.targetsNotRendered,
  stateTargetsRendered: setup.stateTargetsRendered,
  candidateRules: setup.candidateRules,
  // `candidateDeclarations` is the count that matters: authored declarations, not longhands.
  candidateDeclarations: setup.candidateDeclarations,
  candidateLonghands: setup.candidateLonghands,
  // (v2) elements reached through a rule's non-:hover state part, and the state
  // parts that could not be synthesized (each one keeps its declaration unmeasured).
  stateTargetsMeasured: stateMatched.length,
  stateSpecsUnresolved: setup.stateSpecsUnresolved,
  declarationsMeasuredOnStatePath: needed.concat(redundant).filter((r) => r.stateAffected > 0).length,
  // What the defective enumerator would have reported for the same rules.
  longhandModelWouldReport: setup.candidateLonghands,
  groupingMismatches,
  restoreFailures,
  hoverMediaSimulation: hoverMedia,
  declarationsRedundantHere: redundant.length,
  declarationsLoadBearingHere: needed.length,
  declarationsUnmeasuredHere: unmeasured.length,
  declarationsUnmeasuredSharedWithNonHover: unmeasured.filter((u) => u.note && u.note.includes('non-:hover')).length,
  declarationsUnmeasuredNotRendered: unmeasured.filter((u) => u.notRendered).length,
  // (v3) The sampling moment, made observable: settles performed, elements
  // settled, and elements found mid-motion.
  settleStats,
  measureMs,
  measureCostPerTarget: measurements ? Math.round(measureMs / measurements) : null,
};

const payload = {
  summary, redundant, needed, unmeasured,
  candidatePreview: setup.candidatePreview,
  selfCheck: selfCheckReport,
};

if (OUT) {
  const file = artifactPath(OUT);
  writeFileSync(file, JSON.stringify(payload, null, 0));
  console.log(`LIFT_SUMMARY ${JSON.stringify(summary)} raw=${file}`);
  for (const r of needed) console.log('  LOAD-BEARING ' + r.declaration.padEnd(22) + ' longhands=' + r.longhands + ' diffs=' + r.diffs + '  ' + r.selector);
} else if (AS_JSON) {
  console.log(JSON.stringify(payload, null, 0));
} else {
  console.log('URL ..................................... ' + URL);
  console.log('  :hover rules in CSSOM ................ ' + summary.hoverRulesInCssom);
  console.log('  @media(hover:hover) rules re-enabled .. ' + summary.hoverMediaSimulation.rewrittenCount + '   (headless reports hover:none; see lib/browser.mjs)');
  console.log('  elements measured (full computed style) ' + summary.elementsMeasured
    + '   of ' + summary.targetsInScope + ' in scope (' + summary.targetsNotRendered + ' have no box and can carry no observation)');
  console.log('  candidate rules (hover + !important) .. ' + summary.candidateRules);
  console.log('  candidate DECLARATIONS ................ ' + summary.candidateDeclarations);
  console.log('  longhands those declarations cover .... ' + summary.candidateLonghands + '   <- what the longhand model reported');
  console.log('  -> removal changed NOTHING (redundant)   ' + summary.declarationsRedundantHere);
  console.log('  -> removal CHANGED a computed value ...  ' + summary.declarationsLoadBearingHere);
  console.log('  -> no element on this page reaches it ..  ' + summary.declarationsUnmeasuredHere
    + '   (of which reached-but-not-rendered: ' + summary.declarationsUnmeasuredNotRendered + ')');
  console.log('  state-path elements measured (non-:hover) ' + summary.stateTargetsMeasured
    + '   (declarations also measured on that path: ' + summary.declarationsMeasuredOnStatePath + ')');
  console.log('\n--- load-bearing (must keep) ---');
  for (const r of needed) console.log('  ' + r.declaration.padEnd(22) + ' longhands=' + r.longhands + ' diffs=' + r.diffs + '  ' + r.selector);
}
await browser.close();
process.exit(groupingMismatches || restoreFailures ? 3 : 0);
