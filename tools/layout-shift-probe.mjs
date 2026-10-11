/**
 * layout-shift-probe.mjs — attribute Cumulative Layout Shift to the elements that
 * caused it, over N loads.
 *
 * CLS is the one index.html metric that compression, the loader chain and gzip
 * cannot touch: it is a layout defect, and fixing it requires knowing WHICH node
 * moved and by how much. This collects `layout-shift` entries via the Layout
 * Instability API (buffered, so entries emitted before the observer attached are
 * still reported), keeps `hadRecentInput: false` entries only — the metric
 * definition excludes shifts within 500 ms of user input — and reports the top
 * contributors with the node name, its class, and the previous/current rect.
 *
 *   https://web.dev/articles/debug-layout-shifts
 *   https://developer.mozilla.org/en-US/docs/Web/API/LayoutShift
 *
 * It also records the CLS distribution across loads, because a single load of a
 * page that swaps a font or reveals a late resource is not a measurement: one
 * load can land below the threshold and the next above it.
 *
 * Usage
 *   node tools/layout-shift-probe.mjs [url] [--n=5] [--wait=10000] [--top=10]
 *                                    [--json] [--out=FILE] [--label=before|after]
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: per-load CLS, the mean/min/max, and the top-N shift contributors by
 * total value; with --out, full JSON under artifacts/.
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const N = Number((argv.find((a) => a.startsWith('--n=')) || '--n=5').split('=')[1]);
const WAIT = Number((argv.find((a) => a.startsWith('--wait=')) || '--wait=10000').split('=')[1]);
const TOP = Number((argv.find((a) => a.startsWith('--top=')) || '--top=10').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;
const LABEL = (argv.find((a) => a.startsWith('--label=')) || '--label=run').split('=')[1];
const AS_JSON = hasFlag(argv, 'json');

const OBSERVER = `(() => {
  window.__shifts = [];
  window.__cls = 0;
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.hadRecentInput) continue;
        window.__cls += entry.value;
        window.__shifts.push({
          value: entry.value,
          startTime: entry.startTime,
          sources: entry.sources.map((s) => ({
            node: s.node ? s.node.nodeName + '.' + (typeof s.node.className === 'string' ? s.node.className : '') : null,
            previousRect: s.previousRect,
            currentRect: s.currentRect,
          })),
        });
      }
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) {
    window.__cls = null;
  }
})()`;

const browser = await launch({ kind: 'full' });
const loads = [];
for (let i = 0; i < N; i++) {
  const page = await newPage(browser, { width: 1366, height: 900 });
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e).slice(0, 140)));
  // Attach before any document script runs so nothing is missed, and use
  // buffered:true as a second net for entries emitted before the observer.
  await page.evaluateOnNewDocument(OBSERVER);
  await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await new Promise((r) => setTimeout(r, WAIT));
  const snap = await page.evaluate(() => ({
    cls: window.__cls,
    shifts: window.__shifts,
    resourceCount: performance.getEntriesByType('resource').length,
    domElements: document.querySelectorAll('*').length,
    // Which faces actually rendered, and whether the font load settled.
    fonts: (document.fonts ? [...document.fonts].map((f) => f.family + '/' + f.weight + '/' + f.status) : []),
  }));
  loads.push({ load: i + 1, ...snap, pageErrors });
  await page.close();
}
await browser.close();

// Aggregate the contributors across loads: a shift that happens on every load is
// a real layout defect; one that happens once is a race and needs more captures.
const agg = new Map();
for (const load of loads) {
  for (const s of load.shifts) {
    for (const src of s.sources) {
      const key = src.node || '(no node)';
      const cur = agg.get(key) || { node: key, totalValue: 0, count: 0, loads: new Set(), example: null };
      cur.totalValue += s.value;
      cur.count += 1;
      cur.loads.add(load.load);
      if (!cur.example) cur.example = { value: s.value, startTime: s.startTime, previousRect: src.previousRect, currentRect: src.currentRect };
      agg.set(key, cur);
    }
  }
}
const contributors = [...agg.values()]
  .map((c) => ({ ...c, loads: c.loads.size }))
  .sort((a, b) => b.totalValue - a.totalValue);

const clsValues = loads.map((l) => l.cls);
const finite = clsValues.filter((v) => typeof v === 'number');
const summary = {
  label: LABEL,
  url: URL,
  loads: N,
  waitMs: WAIT,
  clsValues,
  clsMin: finite.length ? Math.min(...finite) : null,
  clsMax: finite.length ? Math.max(...finite) : null,
  clsMean: finite.length ? finite.reduce((a, b) => a + b, 0) / finite.length : null,
  clsAllBelow010: finite.length === N && finite.every((v) => v < 0.1),
  totalShifts: loads.reduce((a, l) => a + l.shifts.length, 0),
  pageErrors: loads.reduce((a, l) => a + l.pageErrors.length, 0),
  topContributors: contributors.slice(0, TOP),
};

if (AS_JSON || OUT) {
  if (OUT) {
    const file = artifactPath(OUT);
    writeFileSync(file, JSON.stringify({ summary, loads }, null, 1));
    console.log(`CLS_PROBE ${JSON.stringify(summary)} raw=${file}`);
  } else {
    console.log(JSON.stringify({ summary, loads }, null, 0));
  }
} else {
  console.log(`URL ${URL}   label=${LABEL}   loads=${N}   wait=${WAIT}ms`);
  console.log(`CLS per load: ${clsValues.map((v) => v.toFixed(4)).join(', ')}`);
  console.log(`CLS min=${summary.clsMin?.toFixed(4)} mean=${summary.clsMean?.toFixed(4)} max=${summary.clsMax?.toFixed(4)}  ` +
    `all<0.10=${summary.clsAllBelow010}`);
  console.log(`layout-shift entries: ${summary.totalShifts}   page errors: ${summary.pageErrors}`);
  console.log(`\n--- top ${TOP} contributors by total shift value ---`);
  for (const c of summary.topContributors) {
    console.log(`  ${c.totalValue.toFixed(4)}  x${c.count} on ${c.loads}/${N} loads  ${c.node}`);
    if (c.example) {
      const p = c.example.previousRect, n = c.example.currentRect;
      console.log(`      prev ${JSON.stringify(p)}`);
      console.log(`      curr ${JSON.stringify(n)}`);
    }
  }
  if (!contributors.length) console.log('  (no non-input layout shifts recorded)');
}
