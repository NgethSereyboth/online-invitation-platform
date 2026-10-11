/**
 * style-recalc-attribution.mjs — WHO causes each style recalculation, not just how many.
 *
 * Why this exists
 * ---------------
 * tools/style-layout-trace.mjs answers "how much time went into Recalculate Style
 * and which selectors were expensive". That was not enough to act on for
 * index.html: it reported 8,264 ms of UpdateLayoutTree while the per-selector
 * matching total was only 398 ms, i.e. 95% of the cost was style *resolution*,
 * not selector matching. A selector-level report cannot explain that.
 *
 * This tool answers the next question: each Recalculate Style event sits inside
 * some cause on the same thread — a timer callback, an animation frame, an event
 * dispatch, a HTML parse, a forced synchronous layout from script, or an outer
 * style recalculation. Trace events carry nesting as [ts, ts+dur] intervals, so
 * the enclosing cause is recoverable purely from the trace. Aggregating time by
 * that cause is what turns "style is slow" into "this loop is dirtying the
 * document 60 times a second".
 *
 * Method
 * ------
 *   1. Keep only complete events (ph === 'X') on the main renderer thread (the
 *      tid that emitted UpdateLayoutTree).
 *   2. For each UpdateLayoutTree interval, walk the containment chain outward and
 *      record the ROOT cause (the outermost enclosing event) and the NEAREST
 *      non-style cause (first ancestor whose name is neither UpdateLayoutTree nor
 *      Layout nor a LocalFrameView/FrameView wrapper) — the two different
 *      questions "which task" and "which statement".
 *   3. Report total ms and count per cause, plus a duration histogram so a single
 *      pathological recalc is distinguishable from a long tail.
 *
 * Usage
 *   node tools/style-recalc-attribution.mjs [url] [--wait=2000] [--top=15]
 *                                           [--json] [--out=FILE] [--trace=FILE]
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: a per-cause breakdown on stdout and optionally artifacts/*.json.
 */
import { readFileSync, writeFileSync } from 'node:fs';

import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const WAIT = Number((argv.find((a) => a.startsWith('--wait=')) || '--wait=2000').split('=')[1]);
const TOP = Number((argv.find((a) => a.startsWith('--top=')) || '--top=15').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;
const TRACE_OUT = (argv.find((a) => a.startsWith('--trace=')) || '').split('=')[1] || null;
const AS_JSON = hasFlag(argv, 'json');

let events;
const FROM_TRACE = (argv.find((a) => a.startsWith('--from-trace=')) || '').split('=')[1] || null;
if (FROM_TRACE) {
  // Re-analyse a saved trace instead of capturing a new one. This is how the
  // before/after numbers in the report are produced from the same parser: a
  // parser fix must not require re-running an unrepeatable capture.
  events = JSON.parse(readFileSync(FROM_TRACE, 'utf8'));
} else {
  const browser = await launch({ kind: 'full' });
  const page = await newPage(browser, { width: 1366, height: 900 });
  const cdp = await page.target().createCDPSession();
  events = [];
  cdp.on('Tracing.dataCollected', ({ value }) => events.push(...value));
  const done = new Promise((resolve) => cdp.once('Tracing.tracingComplete', resolve));
  await cdp.send('Tracing.start', {
    transferMode: 'ReportEvents',
    traceConfig: {
      recordMode: 'recordAsMuchAsPossible',
      includedCategories: ['devtools.timeline', 'blink.user_timing', 'loading', 'v8', 'disabled-by-default-blink.debug'],
    },
  });
  await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await new Promise((r) => setTimeout(r, WAIT));
  await cdp.send('Tracing.end');
  await done;
  await browser.close();
  if (TRACE_OUT) writeFileSync(artifactPath(TRACE_OUT), JSON.stringify(events));
}

// --- main renderer thread ----------------------------------------------------
const recalcAll = events.filter((e) => e.name === 'UpdateLayoutTree' && e.ph === 'X');
const mainTid = recalcAll.length ? recalcAll[0].tid : null;
const main = events
  .filter((e) => e.ph === 'X' && e.tid === mainTid && typeof e.dur === 'number')
  .sort((a, b) => a.ts - b.ts);

const start = main.length ? main[0].ts : 0;
const end = main.length ? Math.max(...main.map((e) => e.ts + e.dur)) : 0;
const wallMs = (end - start) / 1000;

// Enclosing-chain lookup. Events are sorted by start; a candidate is an ancestor
// when it starts at or before and ends at or after the child.
function ancestorsOf(ev) {
  const chain = [];
  for (let i = main.length - 1; i >= 0; i--) {
    const a = main[i];
    if (a === ev) continue;
    if (a.ts <= ev.ts && a.ts + a.dur >= ev.ts + ev.dur && a.dur > ev.dur) chain.push(a);
  }
  return chain.sort((a, b) => a.dur - b.dur); // innermost first
}

const STYLE_NAMES = new Set([
  'UpdateLayoutTree', 'Layout', 'LocalFrameView::updateStyleAndLayoutIfNeededRecursive',
  'LocalFrameView::UpdateLifecyclePhasesForPrinting', 'StyleRecalcInvalidationTracking',
]);
// The JS frame a recalculation is caused by is the actionable attribution: the
// enclosing task says "an animation frame", the innermost FunctionCall says
// which function. Same [ts, ts+dur] containment reasoning as above.
const JS_NAMES = new Set(['FunctionCall', 'EvaluateScript']);
const byJsFrame = new Map();
const byRoot = new Map();
const byNearest = new Map();
const buckets = new Map();
const rows = [];
for (const ev of recalcAll) {
  const chain = ancestorsOf(ev);
  const root = chain.length ? chain[chain.length - 1] : null;
  const nearest = chain.find((a) => !STYLE_NAMES.has(a.name)) || null;
  const rootKey = root ? root.name : '(no enclosing event)';
  const nearKey = nearest ? nearest.name : '(no enclosing event)';
  byRoot.set(rootKey, byRoot.get(rootKey) || { name: rootKey, ms: 0, count: 0 });
  byRoot.get(rootKey).ms += ev.dur / 1000;
  byRoot.get(rootKey).count += 1;
  byNearest.set(nearKey, byNearest.get(nearKey) || { name: nearKey, ms: 0, count: 0 });
  byNearest.get(nearKey).ms += ev.dur / 1000;
  byNearest.get(nearKey).count += 1;
  const b = ev.dur < 1000 ? '<1ms' : ev.dur < 5000 ? '1-5ms' : ev.dur < 20000 ? '5-20ms'
    : ev.dur < 50000 ? '20-50ms' : ev.dur < 100000 ? '50-100ms' : '>=100ms';
  buckets.set(b, (buckets.get(b) || 0) + 1);
  const js = chain.filter((a) => JS_NAMES.has(a.name));
  const innermost = js.length ? js[0] : null;
  const jsKey = innermost
    ? `${innermost.name}@${String((innermost.args && innermost.args.data && innermost.args.data.url) || '').replace(/^https?:\/\/[^/]+/, '')}:${(innermost.args && innermost.args.data && innermost.args.data.lineNumber) || 0} ${(innermost.args && innermost.args.data && innermost.args.data.functionName) || ''}`.trim()
    : '(no JS frame)';
  const jsRow = byJsFrame.get(jsKey) || { frame: jsKey, ms: 0, count: 0, maxMs: 0, elements: 0 };
  jsRow.ms += ev.dur / 1000;
  jsRow.count += 1;
  jsRow.maxMs = Math.max(jsRow.maxMs, ev.dur / 1000);
  jsRow.elements += (ev.args && ev.args.elementCount) || 0;
  byJsFrame.set(jsKey, jsRow);
  rows.push({
    durMs: ev.dur / 1000,
    atMs: (ev.ts - start) / 1000,
    elementCount: ev.args ? ev.args.elementCount : null,
    root: rootKey,
    nearest: nearKey,
    jsFrame: jsKey,
    stack: chain.slice(-4).map((a) => a.name),
  });
}
const sortMs = (m) => [...m.values()].sort((a, b) => b.ms - a.ms);
const totalMs = recalcAll.reduce((a, e) => a + e.dur / 1000, 0);

const summary = {
  url: URL,
  mainThreadTid: mainTid,
  traceWallMs: wallMs,
  recalcTotalMs: totalMs,
  recalcCount: recalcAll.length,
  recalcShareOfMainThread: wallMs ? totalMs / wallMs : null,
  byRoot: sortMs(byRoot).slice(0, TOP),
  byNearest: sortMs(byNearest).slice(0, TOP),
  byJsFrame: [...byJsFrame.values()].sort((a, b) => b.ms - a.ms).slice(0, TOP)
    .map((r) => ({ ...r, avgElements: r.count ? Math.round(r.elements / r.count) : 0 })),
  durationHistogram: [...buckets.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ bucket: k, count: v })),
  slowest: rows.sort((a, b) => b.durMs - a.durMs).slice(0, TOP),
};

if (AS_JSON || OUT) {
  if (OUT) {
    const file = artifactPath(OUT);
    writeFileSync(file, JSON.stringify(summary, null, 1));
    console.log(`STYLE_RECALC_ATTRIBUTION ${JSON.stringify({
      url: summary.url, traceWallMs: Math.round(summary.traceWallMs),
      recalcTotalMs: Math.round(summary.recalcTotalMs), recalcCount: summary.recalcCount,
      share: summary.recalcShareOfMainThread == null ? null : Number(summary.recalcShareOfMainThread.toFixed(3)),
      topRoot: summary.byRoot[0] || null,
    })} raw=${file}`);
  } else {
    console.log(JSON.stringify(summary, null, 1));
  }
} else {
  console.log(`URL ${URL}   main renderer tid=${mainTid}   wait=${WAIT}ms`);
  console.log(`main-thread wall clock in trace: ${wallMs.toFixed(0)} ms`);
  console.log(`Recalculate Style total:         ${totalMs.toFixed(0)} ms over ${recalcAll.length} events` +
    `  (${(totalMs / wallMs * 100).toFixed(1)}% of main-thread wall clock)`);
  console.log('\n--- by enclosing TASK (outermost) ---');
  for (const r of summary.byRoot) console.log(`  ${r.ms.toFixed(0).padStart(7)} ms  ${String(r.count).padStart(5)} events  ${r.name}`);
  console.log('\n--- by nearest non-style cause ---');
  for (const r of summary.byNearest) console.log(`  ${r.ms.toFixed(0).padStart(7)} ms  ${String(r.count).padStart(5)} events  ${r.name}`);
  console.log('\n--- by innermost JS frame (the actionable one) ---');
  for (const r of summary.byJsFrame) console.log(`  ${r.ms.toFixed(0).padStart(7)} ms  n=${String(r.count).padStart(4)} max=${r.maxMs.toFixed(0).padStart(4)}ms avgEl=${String(r.avgElements).padStart(4)}  ${r.frame.slice(0, 110)}`);
  console.log('\n--- per-recalc duration histogram ---');
  for (const b of summary.durationHistogram) console.log(`  ${String(b.count).padStart(5)}  ${b.bucket}`);
  console.log('\n--- slowest recalcs ---');
  for (const r of summary.slowest) {
    console.log(`  ${r.durMs.toFixed(1).padStart(8)} ms at +${r.atMs.toFixed(0)}ms  elements=${r.elementCount}  ${r.stack.join(' < ')}`);
  }
}
