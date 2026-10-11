/**
 * layout-thrash-probe.mjs — how many forced style recalculations does ONE JS call cause?
 *
 * Why this exists
 * ---------------
 * tools/style-recalc-attribution.mjs found that index.html spends 67.6% of its
 * main-thread wall clock inside Recalculate Style, and that the worst offender is
 * a requestAnimationFrame callback. That narrows it to a function but not to a
 * statement. The remaining question for a read-modify-write loop is always the
 * same: does one invocation force ONE recalculation (batched) or N (thrashing)?
 *
 * This tool answers that directly. It loads the page, settles, starts a trace,
 * calls a single JS expression exactly once, stops the trace, and reports the
 * style recalculation and layout events that occurred inside the measurement
 * window only. Calling the same site before and after a change turns "batched the
 * reads" from a claim into a number.
 *
 * Usage
 *   node tools/layout-thrash-probe.mjs [url] --call="window.EInviteUiComponents.refresh()" \
 *        [--settle=2500] [--wait=500] [--json]
 *
 *   --call   JS expression evaluated once inside the trace window
 *   --settle ms to wait after load before tracing (let the module chain finish)
 *   --wait   ms to wait after --call before stopping the trace
 *   --repeat call the expression N times, to check the loop is idempotent
 *
 * --loop-bench mode
 *   The trace-based mode cannot measure a read-modify-write loop that is
 *   scheduled with requestAnimationFrame and only runs while the document is
 *   still settling, because headless Chrome stops producing frames once the page
 *   goes idle and the callback then never runs. `--loop-bench=SELECTOR` measures
 *   the same loop *synchronously* in one evaluate() call instead, and compares the
 *   two shapes that matter:
 *
 *     interleaved   for (n of nodes) { if (read(n) > 2) write(n) }   ← thrash
 *     batched       read all, then write all                          ← one recalc
 *
 *   Both are run on the same nodes, in the same document, alternating, so the
 *   only difference is the ordering of reads and writes. The reported ratio is
 *   the cost of interleaving on this page.
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: recalculation/layout event counts and milliseconds inside the window,
 * plus a per-selector-cost summary for the same window.
 */
import { hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const CALL = (argv.find((a) => a.startsWith('--call=')) || '--call=void 0').slice('--call='.length);
const SETTLE = Number((argv.find((a) => a.startsWith('--settle=')) || '--settle=2500').split('=')[1]);
const WAIT = Number((argv.find((a) => a.startsWith('--wait=')) || '--wait=500').split('=')[1]);
const REPEAT = Number((argv.find((a) => a.startsWith('--repeat=')) || '--repeat=1').split('=')[1]);
const LOOP_BENCH = (argv.find((a) => a.startsWith('--loop-bench=')) || '').split('=')[1] || null;
const BENCH_ROUNDS = Number((argv.find((a) => a.startsWith('--rounds=')) || '--rounds=7').split('=')[1]);
const AS_JSON = hasFlag(argv, 'json');

const browser = await launch({ kind: 'full' });
const page = await newPage(browser, { width: 1366, height: 900 });
const cdp = await page.target().createCDPSession();

await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
await new Promise((r) => setTimeout(r, SETTLE));

const nodeCounts = await page.evaluate(() => {
  const $$ = (s) => [...document.querySelectorAll(s)];
  return {
    totalElements: document.getElementsByTagName('*').length,
    navText: $$('.v54-nav-text').length,
  };
});

if (LOOP_BENCH) {
  // Synchronous A/B of the read-modify-write shape. Runs in the live page, so the
  // real DOM size and the real stylesheet are part of the measurement.
  const bench = await page.evaluate(async (selector, rounds) => {
    const nodes = [...document.querySelectorAll(selector)];
    const before = nodes.map((n) => n.style.minHeight);
    const results = { nodes: nodes.length, interleaved: [], batched: [] };
    const restore = () => nodes.forEach((n, i) => { n.style.minHeight = before[i]; });

    const interleaved = () => {
      const t = performance.now();
      for (const node of nodes) {
        if (node.scrollHeight - node.clientHeight > 2) node.style.minHeight = `${Math.ceil(node.scrollHeight)}px`;
      }
      return performance.now() - t;
    };
    const batched = () => {
      const t = performance.now();
      const heights = nodes.map((n) => ({ node: n, over: n.scrollHeight - n.clientHeight, target: Math.ceil(n.scrollHeight) }));
      for (const h of heights) if (h.over > 2) h.node.style.minHeight = `${h.target}px`;
      return performance.now() - t;
    };
    for (let i = 0; i < rounds; i++) {
      restore();
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      results.interleaved.push(interleaved());
      restore();
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      results.batched.push(batched());
    }
    restore();
    const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
    return { ...results, interleavedMedian: median(results.interleaved), batchedMedian: median(results.batched) };
  }, LOOP_BENCH, BENCH_ROUNDS);

  console.log(`URL ${URL}`);
  console.log(`loop-bench selector: ${LOOP_BENCH}   nodes: ${bench.nodes}   rounds: ${BENCH_ROUNDS}`);
  console.log(`interleaved read→write : ${bench.interleaved.map((v) => v.toFixed(1)).join(', ')}  → median ${bench.interleavedMedian.toFixed(1)} ms`);
  console.log(`batched read,then write: ${bench.batched.map((v) => v.toFixed(1)).join(', ')}  → median ${bench.batchedMedian.toFixed(1)} ms`);
  console.log(`ratio: ${(bench.interleavedMedian / Math.max(bench.batchedMedian, 0.01)).toFixed(1)}x`);
  if (AS_JSON) console.log(JSON.stringify({ url: URL, ...nodeCounts, bench }, null, 1));
  await browser.close();
  process.exit(0);
}

const events = [];
cdp.on('Tracing.dataCollected', ({ value }) => events.push(...value));
const done = new Promise((resolve) => cdp.once('Tracing.tracingComplete', resolve));
await cdp.send('Tracing.start', {
  transferMode: 'ReportEvents',
  traceConfig: {
    recordMode: 'recordAsMuchAsPossible',
    includedCategories: ['devtools.timeline', 'v8', 'disabled-by-default-blink.debug'],
  },
});
const t0 = Date.now();
for (let i = 0; i < REPEAT; i++) {
  await page.evaluate(CALL);
}
void t0;
await new Promise((r) => setTimeout(r, WAIT));
await cdp.send('Tracing.end');
await done;
await browser.close();

const tid = (events.find((e) => e.name === 'UpdateLayoutTree') || {}).tid;
const recalc = events.filter((e) => e.name === 'UpdateLayoutTree' && e.ph === 'X');
const layout = events.filter((e) => e.name === 'Layout' && e.ph === 'X');
const recalcMs = recalc.reduce((a, e) => a + (e.dur || 0), 0) / 1000;
const layoutMs = layout.reduce((a, e) => a + (e.dur || 0), 0) / 1000;

// Per-selector cost inside the same window: this is where a thrashing loop shows
// up as "the same handful of selectors evaluated hundreds of times".
const rows = [];
for (const e of events) {
  if (e.name !== 'SelectorStats') continue;
  const s = e.args?.selector_stats;
  if (s && Array.isArray(s.selector_timings)) rows.push(...s.selector_timings);
}
const selTotals = new Map();
for (const r of rows) {
  const k = r.selector;
  const cur = selTotals.get(k) || { selector: k, elapsedUs: 0, attempts: 0, matches: 0 };
  cur.elapsedUs += r['elapsed (us)'] || 0;
  cur.attempts += r.match_attempts || 0;
  cur.matches += r.match_count || 0;
  selTotals.set(k, cur);
}

const summary = {
  url: URL,
  call: CALL,
  repeat: REPEAT,
  settleMs: SETTLE,
  waitMs: WAIT,
  ...nodeCounts,
  recalcEvents: recalc.length,
  recalcMs,
  layoutEvents: layout.length,
  layoutMs,
  selectorRows: rows.length,
  topSelectors: [...selTotals.values()].sort((a, b) => b.elapsedUs - a.elapsedUs).slice(0, 12),
};

if (AS_JSON) {
  console.log(JSON.stringify(summary, null, 1));
} else {
  console.log(`URL ${URL}`);
  console.log(`call: ${CALL}   repeat=${REPEAT}   settle=${SETTLE}ms   wait=${WAIT}ms`);
  console.log(`document elements: ${nodeCounts.totalElements}   .v54-nav-text nodes: ${nodeCounts.navText}`);
  console.log(`inside the window: Recalculate Style ${recalcMs.toFixed(1)} ms / ${recalc.length} events` +
    `   Layout ${layoutMs.toFixed(1)} ms / ${layout.length} events`);
  console.log(`forced recalcs per call: ${(recalc.length / REPEAT).toFixed(2)}`);
  console.log('\n--- top selectors in the window ---');
  for (const s of summary.topSelectors) {
    console.log(`  ${(s.elapsedUs / 1000).toFixed(3).padStart(9)} ms  attempts=${String(s.attempts).padStart(7)}  ${s.selector.slice(0, 90)}`);
  }
}
