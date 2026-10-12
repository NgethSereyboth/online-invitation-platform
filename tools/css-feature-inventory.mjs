/**
 * css-feature-inventory.mjs — count modern-CSS layout/containment features in the
 * CSS a URL actually ships, so two sites can be compared on the same axis.
 *
 * Why this exists
 * ---------------
 * Goal 0 of the Canva-analysis pass asks whether Canva's editor uses CSS
 * containment (`content-visibility`, `contain`, `will-change`, `@layer`,
 * `@container`) where this project does not. That question cannot be answered by
 * reading Canva's source — none is published — and it cannot be answered from
 * DevTools' computed-style pane, which shows no rule that did not match. It is a
 * question about the *CSS text*, so this tool collects the CSS text both sides
 * ship and counts the constructs.
 *
 * How the text is obtained (and why not `document.styleSheets`)
 *   `document.styleSheets[i].cssRules` throws SecurityError for a cross-origin
 *   sheet, and Canva's CSS is on static.canva.com — a different origin. Reading
 *   through the CDP Network domain (`Network.getResponseBody` per requestId)
 *   returns the bytes regardless of CORS, which makes one instrument work on both
 *   a remote site and a local server. Inline `<style>` blocks are read from the
 *   DOM, since they are not network requests at all.
 *
 * What it counts (per URL, over the union of every stylesheet + inline block)
 *   containment:  content-visibility, contain, contain-intrinsic-size
 *   hints:        will-change, translateZ/translate3d/backface-visibility, isolation
 *   modern CSS:   @layer, @container/container-type, :is(, :where(, :has(, clamp(
 *   cost markers: !important declarations, @media blocks, custom properties,
 *                 style rules, distinct selectors, total bytes
 *
 * Usage
 *   node tools/css-feature-inventory.mjs https://www.canva.com/ --label=canva
 *   node tools/css-feature-inventory.mjs http://127.0.0.1:8124/index.html --label=project-index
 *   node tools/css-feature-inventory.mjs --pages=index.html,public.html,dashboard.html --label=project
 *
 * Requires a running server for the `--pages` form (`make serve-gzip`).
 * Writes artifacts/css-feature-inventory-<label>.json; prints one row per URL.
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, argValue, hasFlag, pageUrl } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const LABEL = String(argValue(argv, 'label', 'run'));
const WAIT = Number(argValue(argv, 'wait', 4000));
const AS_JSON = hasFlag(argv, 'json');
const pagesFlag = argValue(argv, 'pages', null);
const positional = argv.filter((a) => !a.startsWith('--') && !/^https?:/.test(a) === false);

let TARGETS;
if (pagesFlag) {
  TARGETS = String(pagesFlag)
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => pageUrl(p));
} else {
  TARGETS = argv.filter((a) => /^https?:\/\//.test(a));
}
if (!TARGETS.length) TARGETS = ['https://www.canva.com/'];
void positional;

const UA =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
  'Chrome/154.0.0.0 Safari/537.36';

/**
 * One pass of literal counting. Every pattern is a plain substring or regex over
 * the concatenated CSS text; nothing here is inferred, so the same function run
 * over a different site is a fair comparison.
 */
function inventory(cssText) {
  const text = cssText || '';
  const count = (re) => (text.match(re) || []).length;
  const bytes = Buffer.byteLength(text, 'utf8');
  return {
    bytes,
    // containment / culling
    contentVisibility: count(/content-visibility\s*:/g),
    contain: count(/(?:^|[;{\s])contain\s*:/g),
    containIntrinsicSize: count(/contain-intrinsic-size\s*:/g),
    // compositing hints
    willChange: count(/will-change\s*:/g),
    translateZ: count(/translateZ\(|translate3d\(/g),
    backfaceVisibility: count(/backface-visibility\s*:/g),
    isolation: count(/(?:^|[;{\s])isolation\s*:/g),
    // modern cascade / query features
    layers: count(/@layer\b/g),
    containerQueries: count(/@container\b/g),
    containerType: count(/container-type\s*:/g),
    isSelector: count(/:is\(/g),
    whereSelector: count(/:where\(/g),
    hasSelector: count(/:has\(/g),
    clamp: count(/clamp\(/g),
    colorMix: count(/color-mix\(/g),
    nesting: count(/(?:^|\})\s*(?:&|@nest)\b/gm),
    // cost markers
    important: count(/!important/g),
    mediaBlocks: count(/@media\b/g),
    keyframes: count(/@keyframes\b/g),
    customPropertyDecls: count(/--[a-z0-9-]+\s*:/gi),
    styleRules: count(/\{/g),
    selectors: count(/[^{}]+(?=\{)/g),
    aspectRatio: count(/aspect-ratio\s*:/g),
    contentVisibilityAuto: count(/content-visibility\s*:\s*auto/g),
    virtualScrollish: count(/overflow-(?:y|)\s*:\s*(?:auto|scroll)/g),
  };
}

const browser = await launch({ kind: 'full', extraArgs: ['--disable-blink-features=AutomationControlled'] });
const results = [];

for (const url of TARGETS) {
  const page = await newPage(browser, { width: 1440, height: 900 });
  await page.setUserAgent(UA);
  const cdp = await page.target().createCDPSession();
  await cdp.send('Network.enable', {});

  /** requestId -> {url, mimeType, status} for every stylesheet-shaped response. */
  const cssResponses = new Map();
  cdp.on('Network.responseReceived', (e) => {
    const mime = e.response.mimeType || '';
    const isCss = mime.includes('css') || e.type === 'Stylesheet';
    if (isCss && !e.response.url.startsWith('data:')) {
      cssResponses.set(e.requestId, { url: e.response.url, mimeType: mime, status: e.response.status });
    }
  });
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});

  let status = null;
  let error = null;
  try {
    const resp = await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    status = resp ? resp.status() : null;
  } catch (e) {
    error = String(e && e.message ? e.message : e);
  }
  await page.waitForNetworkIdle({ idleTime: 800, timeout: WAIT }).catch(() => {});
  await new Promise((r) => setTimeout(r, Math.min(WAIT, 2000)));

  const sheets = [];
  const failures = [];
  for (const [requestId, meta] of cssResponses) {
    try {
      const { body, base64Encoded } = await cdp.send('Network.getResponseBody', { requestId });
      sheets.push({
        url: meta.url,
        status: meta.status,
        bytes: base64Encoded ? Buffer.from(body, 'base64').length : Buffer.byteLength(body, 'utf8'),
        text: base64Encoded ? Buffer.from(body, 'base64').toString('utf8') : body,
      });
    } catch (e) {
      failures.push({ url: meta.url, reason: String(e && e.message ? e.message : e) });
    }
  }

  let inline = '';
  let inlineBlocks = 0;
  let ruleCount = null;
  try {
    const dom = await page.evaluate(() => {
      let text = '';
      let blocks = 0;
      for (const el of document.querySelectorAll('style')) {
        text += (el.textContent || '') + '\n';
        blocks += 1;
      }
      let rules = 0;
      let inaccessible = 0;
      for (const sheet of document.styleSheets) {
        try { rules += sheet.cssRules ? sheet.cssRules.length : 0; } catch { inaccessible += 1; }
      }
      return { text, blocks, rules, inaccessible };
    });
    inline = dom.text;
    inlineBlocks = dom.blocks;
    ruleCount = { total: dom.rules, inaccessibleSheets: dom.inaccessible };
  } catch (e) {
    failures.push({ url: '(inline styles)', reason: String(e && e.message ? e.message : e) });
  }

  const externalCss = sheets.map((s) => s.text).join('\n');
  const combined = externalCss + '\n' + inline;
  const row = {
    url,
    status,
    error,
    stylesheetFiles: sheets.length,
    inlineStyleBlocks: inlineBlocks,
    inaccessibleSheets: ruleCount ? ruleCount.inaccessibleSheets : null,
    domRuleCount: ruleCount ? ruleCount.total : null,
    fetchFailures: failures.length,
    externalBytes: sheets.reduce((n, s) => n + s.bytes, 0),
    inlineBytes: Buffer.byteLength(inline, 'utf8'),
    inventory: inventory(combined),
    topSheets: sheets
      .map((s) => ({ url: s.url, bytes: s.bytes }))
      .sort((a, b) => b.bytes - a.bytes)
      .slice(0, 8),
    failures,
  };
  results.push(row);
  await page.close().catch(() => {});
}

await browser.close();

const out = {
  label: LABEL,
  capturedAt: new Date().toISOString(),
  chrome: '/usr/bin/google-chrome via tools/lib/browser.mjs',
  targets: results,
};
writeFileSync(artifactPath(`css-feature-inventory-${LABEL}.json`), JSON.stringify(out, null, 1));

const KEYS = [
  'bytes', 'contentVisibility', 'contentVisibilityAuto', 'contain', 'containIntrinsicSize',
  'willChange', 'translateZ', 'backfaceVisibility', 'isolation',
  'layers', 'containerQueries', 'containerType', 'isSelector', 'whereSelector', 'hasSelector',
  'clamp', 'colorMix', 'important', 'mediaBlocks', 'keyframes', 'customPropertyDecls',
  'styleRules', 'selectors', 'aspectRatio', 'virtualScrollish',
];
if (AS_JSON) {
  console.log(JSON.stringify(out, null, 1));
} else {
  console.log(`CSS_FEATURE_INVENTORY label=${LABEL} targets=${results.length}`);
  for (const r of results) {
    console.log(
      `\n  ${r.status ?? 'ERR'} ${r.url}\n    stylesheets=${r.stylesheetFiles} inlineBlocks=${r.inlineStyleBlocks} domRules=${r.domRuleCount} inaccessibleSheets=${r.inaccessibleSheets} externalBytes=${r.externalBytes} inlineBytes=${r.inlineBytes}${r.error ? ` error=${r.error}` : ''}`,
    );
    console.log('    ' + KEYS.filter((k) => k !== 'bytes').map((k) => `${k}=${r.inventory[k]}`).join('  '));
  }
}
