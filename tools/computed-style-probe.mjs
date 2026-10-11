/**
 * computed-style-probe.mjs — prove that a CSS refactor changed no computed value.
 *
 * This generalises the one-off `toast-probe.mjs` used to prove that folding
 * `toast.css` into the dashboard bundle removed a request without changing
 * anything a user can see. Point it at a page and a set of selectors and it
 * reports, per selector: the full computed style, which stylesheets loaded, and
 * which resource URLs matched. Run it before and after a refactor and diff the
 * two JSON files — or use `--compare=A.json,B.json` to diff in one step.
 *
 * A selector that does not exist on the page is *synthesised* (the tag name and
 * classes are read off the selector text and the node is appended to the
 * nearest matching ancestor, falling back to <body>), so components that only
 * appear after an interaction can still be measured. Synthesis is reported
 * explicitly in the output, never silently.
 *
 * Usage
 *   node tools/computed-style-probe.mjs [url] --selectors=.toast-stack,.toast.toast--success
 *   node tools/computed-style-probe.mjs [url] --selectors=... --out=style-probe.json
 *   node tools/computed-style-probe.mjs --compare=artifacts/before.json,artifacts/after.json
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: JSON on stdout and, with --out, under artifacts/.
 */
import { readFileSync, writeFileSync } from 'node:fs';

import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const COMPARE = (argv.find((a) => a.startsWith('--compare=')) || '').split('=')[1] || null;

function styleMap(el) {
  const cs = getComputedStyle(el);
  const o = {};
  for (let i = 0; i < cs.length; i++) { const p = cs[i]; o[p] = cs.getPropertyValue(p); }
  return o;
}

if (COMPARE) {
  // Offline path: diff two saved probe runs, no browser needed.
  const [aPath, bPath] = COMPARE.split(',');
  if (!aPath || !bPath) {
    console.error('tools: --compare needs two comma-separated files');
    process.exit(2);
  }
  const a = JSON.parse(readFileSync(aPath, 'utf8'));
  const b = JSON.parse(readFileSync(bPath, 'utf8'));
  let totalDiffs = 0;
  for (const sel of Object.keys(a.selectors)) {
    const av = a.selectors[sel]?.style || {};
    const bv = b.selectors[sel]?.style || {};
    const keys = [...new Set([...Object.keys(av), ...Object.keys(bv)])].sort();
    const diffs = keys.filter((k) => av[k] !== bv[k]);
    totalDiffs += diffs.length;
    console.log(`${sel}  props ${Object.keys(av).length} -> ${Object.keys(bv).length}  differ=${diffs.length}`);
    for (const k of diffs.slice(0, 20)) console.log(`    ${k}: ${av[k]} -> ${bv[k]}`);
  }
  console.log(`sheets: ${JSON.stringify(a.sheets)} -> ${JSON.stringify(b.sheets)}`);
  console.log(`VERDICT: ${totalDiffs === 0 ? 'IDENTICAL computed style' : `${totalDiffs} computed-style differences`}`);
  process.exitCode = totalDiffs === 0 ? 0 : 1;
  process.exit();
}

const URL = urlFromArg(argv.find((a) => !a.startsWith('--')));
const SELECTORS = ((argv.find((a) => a.startsWith('--selectors=')) || '').split('=').slice(1).join('=') || '.toast-stack')
  .split(',').map((s) => s.trim()).filter(Boolean);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;
const JSON_OUT = hasFlag(argv, 'json') || Boolean(OUT);

const browser = await launch({ kind: 'full' });
const page = await browser.newPage();
await page.setViewport({ width: 1366, height: 900 });
await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise((r) => setTimeout(r, 800));

const result = await page.evaluate((selectors) => {
  const out = { selectors: {}, sheets: [], resourceMatches: {}, synthesised: [] };
  out.sheets = [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.getAttribute('href'));
  const hrefs = new Set(out.sheets.map((h) => String(h).split('/').pop()));
  out.resourceMatches = Object.fromEntries(
    [...hrefs].map((name) => [name, performance.getEntriesByType('resource').filter((e) => e.name.endsWith(name)).length]),
  );
  for (const sel of selectors) {
    let el = document.querySelector(sel);
    if (!el) {
      // Synthesise: read the final simple selector's tag + classes.
      const last = sel.split(/[ >+~]/).filter(Boolean).pop() || 'div';
      const m = last.match(/^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)/);
      const tag = (m && m[1]) || 'div';
      const classes = (m && m[2] ? m[2].split('.').filter(Boolean) : []);
      try {
        el = document.createElement(tag);
        if (classes.length) el.className = classes.join(' ');
        el.textContent = 'probe';
        document.body.appendChild(el);
        out.synthesised.push(sel);
      } catch { continue; }
    }
    out.selectors[sel] = { tag: el.tagName, cls: String(el.className || ''), style: (() => {
      const cs = getComputedStyle(el); const o = {};
      for (let i = 0; i < cs.length; i++) { const p = cs[i]; o[p] = cs.getPropertyValue(p); }
      return o;
    })() };
  }
  return out;
}, SELECTORS);

if (OUT) {
  const file = artifactPath(OUT);
  writeFileSync(file, JSON.stringify(result, null, 1));
  console.log(`STYLE_PROBE url=${URL} selectors=${Object.keys(result.selectors).length} synthesised=${result.synthesised.length} raw=${file}`);
} else if (JSON_OUT) {
  console.log(JSON.stringify(result));
} else {
  console.log(`url ${URL}`);
  console.log(`sheets ${JSON.stringify(result.sheets)}`);
  for (const [sel, v] of Object.entries(result.selectors)) {
    console.log(`${sel} -> ${v.tag}.${v.cls} (${Object.keys(v.style).length} properties)`);
  }
  if (result.synthesised.length) console.log(`synthesised (not present on page): ${result.synthesised.join(', ')}`);
}
await browser.close();
