/**
 * dom-timeline.mjs — what does the page insert AFTER first paint, and when?
 *
 * A layout shift is a symptom. This is the instrument that finds the cause: it
 * records every DOM mutation with its timestamp relative to navigation start,
 * together with a layout-shift entry if one follows, so "the viewport moved down
 * 50px at 1341 ms" can be paired with "a 50px-tall <div class=canvas-header> was
 * appended at 1340 ms".
 *
 * Why not just read the sources: the modules responsible are concatenated into
 * the route bundle and append their markup at parse time, so which module owns
 * which element is not recoverable by grepping. The mutation record is the
 * ground truth.
 *
 * Usage
 *   node tools/dom-timeline.mjs [url] [--wait=4000] [--min-height=8] [--json] [--out=FILE]
 *
 *   --min-height  only report added elements whose rendered box is at least this
 *                 tall (px); the interesting ones reserve vertical space.
 *
 * Requires: node + puppeteer-core, a running server (tools/serve-gzip.py).
 * Produces: an ordered timeline of mutations (with the parent chain), each
 * added element's box, and the layout-shift events interleaved by timestamp.
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const WAIT = Number((argv.find((a) => a.startsWith('--wait=')) || '--wait=4000').split('=')[1]);
const MIN_H = Number((argv.find((a) => a.startsWith('--min-height=')) || '--min-height=8').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;
const AS_JSON = hasFlag(argv, 'json');

const PROBE = `(() => {
  window.__tl = [];
  const rect = (r) => (r ? { x: r.x, y: r.y, w: r.width, h: r.height, top: r.top, left: r.left } : null);
  const name = (n) => {
    if (!n || !n.nodeName) return String(n && n.nodeType);
    const cls = (typeof n.className === 'string' ? n.className : '').trim();
    const id = n.id ? '#' + n.id : '';
    return n.nodeName + id + (cls ? '.' + cls.split(/\\s+/).join('.') : '');
  };
  const chain = (n) => {
    const out = [];
    let cur = n && n.parentElement;
    for (let i = 0; cur && i < 6; i++, cur = cur.parentElement) out.push(name(cur));
    return out.join(' < ');
  };
  const t0 = performance.timeOrigin;
  const now = () => performance.now();
  try {
    new MutationObserver((records) => {
      for (const rec of records) {
        for (const node of rec.addedNodes) {
          if (node.nodeType !== 1) continue;
          const r = node.getBoundingClientRect();
          window.__tl.push({
            kind: 'add', t: Math.round(now() * 10) / 10,
            node: name(node), parent: chain(node),
            rect: rect(r), text: (node.textContent || '').trim().slice(0, 40),
            childCount: node.children ? node.children.length : 0,
          });
          // Note mutations inside the inserted subtree in one line rather than
          // one record per descendant.
          const n2 = node.querySelectorAll ? node.querySelectorAll('*').length : 0;
          if (n2 > 1) window.__tl[window.__tl.length - 1].descendants = n2;
        }
        for (const node of rec.removedNodes) {
          if (node.nodeType !== 1) continue;
          window.__tl.push({ kind: 'remove', t: Math.round(now() * 10) / 10, node: name(node), parent: chain(node) });
        }
      }
      // Observe document, not document.documentElement: this script runs before
      // the parser has created the root element, so observing the documentElement
      // throws "parameter 1 is not of type Node" and the probe silently records
      // nothing at all (0 mutations, and no error unless you look for it).
    }).observe(document, { childList: true, subtree: true });
    window.__shifts = [];
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) if (!e.hadRecentInput) window.__shifts.push({ t: Math.round(e.startTime), value: e.value });
    }).observe({ type: 'layout-shift', buffered: true });
    window.__navT0 = t0;
  } catch (e) { window.__tlError = String(e); }
  window.__tlReady = true;
})()`;

const browser = await launch({ kind: 'full' });
const page = await newPage(browser, { width: 1366, height: 900 });
await page.evaluateOnNewDocument(PROBE);
await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
await new Promise((r) => setTimeout(r, WAIT));
const snap = await page.evaluate(() => ({
  timeline: window.__tl || [],
  shifts: window.__shifts || [],
  err: window.__tlError || null,
  fcp: (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime || null,
  nav: (() => { const n = performance.getEntriesByType('navigation')[0] || {}; return { dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd }; })(),
}));
await browser.close();

// Elements that reserve vertical space are the ones that can move a neighbour.
const containerish = snap.timeline.filter((m) => m.kind === 'add' && m.rect && m.rect.h >= MIN_H);
const summary = {
  url: URL,
  waitMs: WAIT,
  minHeight: MIN_H,
  fcpMs: snap.fcp ? Math.round(snap.fcp) : null,
  domContentLoadedMs: snap.nav.dcl ? Math.round(snap.nav.dcl) : null,
  loadEventMs: snap.nav.load ? Math.round(snap.nav.load) : null,
  mutations: snap.timeline.length,
  adds: snap.timeline.filter((m) => m.kind === 'add').length,
  removes: snap.timeline.filter((m) => m.kind === 'remove').length,
  containersAdded: containerish.length,
  shiftEvents: snap.shifts.length,
  shiftTotal: snap.shifts.reduce((a, s) => a + s.value, 0),
  probeError: snap.err,
};

if (AS_JSON || OUT) {
  const payload = { summary, timeline: snap.timeline, shifts: snap.shifts, containers: containerish };
  if (OUT) {
    const file = artifactPath(OUT);
    writeFileSync(file, JSON.stringify(payload, null, 1));
    console.log(`DOM_TIMELINE ${JSON.stringify(summary)} raw=${file}`);
  } else {
    console.log(JSON.stringify(payload, null, 0));
  }
} else {
  console.log(`URL ${URL}   wait=${WAIT}ms`);
  console.log(`FCP ${summary.fcpMs}ms   DCL ${summary.domContentLoadedMs}ms   load ${summary.loadEventMs}ms`);
  console.log(`mutations ${summary.mutations} (adds ${summary.adds}, removes ${summary.removes})   ` +
    `containers added >=${MIN_H}px: ${summary.containersAdded}   shifts ${summary.shiftEvents} total ${summary.shiftTotal.toFixed(4)}`);
  if (summary.probeError) console.log(`PROBE ERROR: ${summary.probeError}`);
  console.log('\n--- timeline (add/remove with rendered box) ---');
  for (const m of snap.timeline) {
    const box = m.rect ? `h=${m.rect.h} w=${m.rect.w} top=${m.rect.top}` : '';
    const d = m.descendants ? ` +${m.descendants}` : '';
    console.log(`  t=${String(m.t).padStart(7)}ms ${m.kind.padEnd(6)} ${m.node}${d}  ${box}`);
    console.log(`             parent: ${m.parent}`);
  }
  console.log('\n--- layout shifts ---');
  for (const s of snap.shifts) console.log(`  t=${String(s.t).padStart(6)}ms  value=${s.value.toFixed(5)}`);
}
