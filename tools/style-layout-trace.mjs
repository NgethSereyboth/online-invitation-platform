/**
 * style-layout-trace.mjs — where does "Style & Layout" main-thread time actually go?
 *
 * Lighthouse reports one opaque bucket ("mainthread-work-breakdown →
 * Style & Layout: N ms"). This captures a real CDP trace around a page load and
 * answers three separate questions that the bucket hides:
 *
 *   1. Recalculate Style vs Layout — two different engines, two different fixes.
 *   2. Which DOM subtrees the expensive passes touched (trace event beginData:
 *      dirtyObjects / totalObjects / frame), so the cost is attributable.
 *   3. Which SELECTORS are expensive — per-selector match attempts, matches and
 *      elapsed time — so a reduction is aimed at a named rule, not at "the CSS".
 *
 * A correction to the brief that specified this tool
 * --------------------------------------------------
 * The brief asked for `CSS.enableSelectorStats`. There is no such method: the
 * CDP CSS domain in Chrome 155 (queried from the running browser's own
 * /json/protocol) has no selector-stats command, and the current protocol
 * definition does not either.
 *   https://chromedevtools.github.io/devtools-protocol/tot/CSS/
 * DevTools enables selector stats through TRACING — the Performance panel adds
 * the `disabled-by-default-blink.debug` category and reads the resulting
 * `SelectorStats` trace event, associating it with the selected Recalculate
 * Style event.
 *   https://developer.chrome.com/docs/devtools/performance/selector-stats
 *   https://microsoftedge.github.io/DevTools/explainers/StyleTracing/explainer.html
 * So this tool traces with the debug category enabled and parses `SelectorStats`.
 *
 * Trace event names (Chrome's internal names differ from the panel's labels):
 *   UpdateLayoutTree  ->  panel shows "Recalculate Style"
 *   Layout            ->  panel shows "Layout"
 *   SelectorStats     ->  the per-selector rows
 *
 * Usage
 *   node tools/style-layout-trace.mjs [url] [--top=10] [--wait=2000] [--label=before]
 *                                     [--json] [--out=FILE] [--no-selector-stats]
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: totals for UpdateLayoutTree and Layout, the longest individual
 * events with their beginData, and the top-N selectors by elapsed time
 * (microseconds as emitted; milliseconds shown alongside).
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const TOP = Number((argv.find((a) => a.startsWith('--top=')) || '--top=10').split('=')[1]);
const WAIT = Number((argv.find((a) => a.startsWith('--wait=')) || '--wait=2000').split('=')[1]);
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;
const LABEL = (argv.find((a) => a.startsWith('--label=')) || '--label=run').split('=')[1];
const AS_JSON = hasFlag(argv, 'json');
const SELECTOR_STATS = !hasFlag(argv, 'no-selector-stats');

const browser = await launch({ kind: 'full' });
const page = await newPage(browser, { width: 1366, height: 900 });
const cdp = await page.target().createCDPSession();

const events = [];
cdp.on('Tracing.dataCollected', ({ value }) => events.push(...value));
const done = new Promise((resolve) => cdp.once('Tracing.tracingComplete', resolve));

const categories = ['devtools.timeline', 'blink.user_timing', 'loading', 'v8'];
if (SELECTOR_STATS) categories.push('disabled-by-default-blink.debug');

await cdp.send('Tracing.start', {
  transferMode: 'ReportEvents',
  traceConfig: { recordMode: 'recordAsMuchAsPossible', includedCategories: categories },
});

await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
await new Promise((r) => setTimeout(r, WAIT));
await cdp.send('Tracing.end');
await done;
await browser.close();

const ms = (us) => us / 1000;
const totals = { UpdateLayoutTree: 0, Layout: 0 };
const perEvent = { UpdateLayoutTree: [], Layout: [] };
for (const e of events) {
  if (e.ph !== 'X') continue; // complete events only: 'B' has no dur and would double-count
  if (!(e.name in totals)) continue;
  const dur = e.dur || 0;
  totals[e.name] += dur;
  perEvent[e.name].push({
    durMs: ms(dur),
    startMs: ms(e.ts || 0),
    beginData: e.args ? (e.args.beginData || e.args.data || null) : null,
  });
}
for (const k of Object.keys(perEvent)) perEvent[k].sort((a, b) => b.durMs - a.durMs);

// Recalculate Style events NEST: a top-level style recalc that triggers a
// second recalc inside it emits both, and summing durations then counts the
// inner one twice. The non-overlapping union of the event intervals is the
// honest "main thread was inside style recalc for this long" figure. Both are
// reported so the difference between them is visible rather than assumed away.
const mainThreadTid = perEvent.UpdateLayoutTree.length
  ? events.find((e) => e.name === 'UpdateLayoutTree').tid
  : null;
function unionMs(name, tid) {
  const iv = events
    .filter((e) => e.name === name && e.ph === 'X' && (tid == null || e.tid === tid))
    .map((e) => [e.ts, e.ts + (e.dur || 0)])
    .sort((a, b) => a[0] - b[0]);
  let total = 0;
  let curStart = null;
  let curEnd = null;
  for (const [s, e] of iv) {
    if (curStart === null) { curStart = s; curEnd = e; continue; }
    if (s <= curEnd) curEnd = Math.max(curEnd, e);
    else { total += curEnd - curStart; curStart = s; curEnd = e; }
  }
  if (curStart !== null) total += curEnd - curStart;
  return { ms: ms(total), intervals: iv.length };
}
const recalcUnion = unionMs('UpdateLayoutTree', mainThreadTid);
const layoutUnion = unionMs('Layout', mainThreadTid);

// --- selector stats ---------------------------------------------------------
// The payload path is not part of the CDP CSS schema (it is a trace event), so
// this reads every plausible shape instead of assuming one, and reports which
// key it actually found. A future Chrome that renames the field fails loudly
// (empty top list plus the observed keys) rather than silently reporting zero.
//
// Shape actually emitted by Chrome 155 (verified against a raw trace dump, see
// docs/reviews/reproducibility-and-performance-report.md §3):
//
//   { name: "SelectorStats", args: { selector_stats: { selector_timings: [
//       { "selector": "html", "style_sheet_id": "ua-style-sheet",
//         "elapsed (us)": 1, "match_attempts": 3, "match_count": 1,
//         "fast_reject_count": 0 }, ... ] } } }
//
// Note `selector_stats` is an OBJECT wrapping the array, and the timing key is
// the literal string `"elapsed (us)"` — with a space and parentheses. The first
// version of this parser only accepted an array directly under `args`, so it
// reported 264 events and 0 rows. That retraction is recorded in the report.
const selectorStatsEvents = events.filter((e) => e.name === 'SelectorStats');
const observedKeys = new Set();
let selectorRows = [];
for (const e of selectorStatsEvents) {
  const args = e.args || {};
  for (const k of Object.keys(args)) observedKeys.add(k);
  let rows = args.selector_stats || args.selectorStats || args.data || args.stats || null;
  if (rows && !Array.isArray(rows) && Array.isArray(rows.selector_timings)) rows = rows.selector_timings;
  if (Array.isArray(rows)) selectorRows = selectorRows.concat(rows);
}
const selectorTotals = new Map();
for (const row of selectorRows) {
  const selector = row.selector ?? row.selectorText ?? '(unknown)';
  const elapsed = row['elapsed (us)'] ?? row.elapsed ?? row.elapsed_us ?? row.elapsedUs ?? row.time ?? 0;
  const attempts = row.match_attempts ?? row.matchAttempts ?? 0;
  const matches = row.match_count ?? row.matchCount ?? row.matches ?? 0;
  const key = selector;
  const cur = selectorTotals.get(key) || { selector: key, elapsedUs: 0, attempts: 0, matches: 0, rows: 0 };
  cur.elapsedUs += elapsed;
  cur.attempts += attempts;
  cur.matches += matches;
  cur.rows += 1;
  selectorTotals.set(key, cur);
}
const topSelectors = [...selectorTotals.values()]
  .sort((a, b) => b.elapsedUs - a.elapsedUs)
  .slice(0, TOP)
  .map((s) => ({ ...s, elapsedMs: ms(s.elapsedUs) }));

const summary = {
  label: LABEL,
  url: URL,
  selectorStatsRequested: SELECTOR_STATS,
  traceEvents: events.length,
  recalcStyleTotalMs: ms(totals.UpdateLayoutTree),
  recalcStyleEventCount: perEvent.UpdateLayoutTree.length,
  recalcStyleUnionMs: recalcUnion.ms,
  recalcStyleUnionIntervals: recalcUnion.intervals,
  layoutTotalMs: ms(totals.Layout),
  layoutEventCount: perEvent.Layout.length,
  layoutUnionMs: layoutUnion.ms,
  layoutUnionIntervals: layoutUnion.intervals,
  selectorStatsEvents: selectorStatsEvents.length,
  selectorStatsKeysObserved: [...observedKeys],
  selectorRows: selectorRows.length,
  selectorStatsTotalMs: ms([...selectorTotals.values()].reduce((a, s) => a + s.elapsedUs, 0)),
  topSelectors,
  longestRecalc: perEvent.UpdateLayoutTree.slice(0, TOP),
  longestLayout: perEvent.Layout.slice(0, TOP),
};

if (AS_JSON || OUT) {
  if (OUT) {
    const file = artifactPath(OUT);
    writeFileSync(file, JSON.stringify(summary, null, 1));
    console.log(`STYLE_LAYOUT_TRACE ${JSON.stringify({
      label: summary.label, recalcStyleTotalMs: summary.recalcStyleTotalMs,
      layoutTotalMs: summary.layoutTotalMs, selectorStatsEvents: summary.selectorStatsEvents,
      selectorRows: summary.selectorRows, selectorStatsTotalMs: summary.selectorStatsTotalMs,
    })} raw=${file}`);
  } else {
    console.log(JSON.stringify(summary, null, 1));
  }
} else {
  console.log(`URL ${URL}   label=${LABEL}   wait=${WAIT}ms   trace events=${summary.traceEvents}`);
  console.log(`Recalculate Style (UpdateLayoutTree): ${summary.recalcStyleTotalMs.toFixed(1)} ms summed over ${summary.recalcStyleEventCount} events`);
  console.log(`                              union:  ${summary.recalcStyleUnionMs.toFixed(1)} ms of non-overlapping main-thread time`);
  console.log(`Layout:                               ${summary.layoutTotalMs.toFixed(1)} ms summed over ${summary.layoutEventCount} events`);
  console.log(`                              union:  ${summary.layoutUnionMs.toFixed(1)} ms`);
  console.log(`Selector stats: ${summary.selectorStatsEvents} events, ${summary.selectorRows} rows, ` +
    `keys observed=${JSON.stringify(summary.selectorStatsKeysObserved)}, total ${summary.selectorStatsTotalMs.toFixed(1)} ms`);
  console.log(`\n--- top ${TOP} selectors by elapsed time ---`);
  for (const s of summary.topSelectors) {
    console.log(`  ${s.elapsedMs.toFixed(3).padStart(9)} ms  attempts=${String(s.attempts).padStart(7)} matches=${String(s.matches).padStart(7)}  ${s.selector.slice(0, 90)}`);
  }
  if (!summary.topSelectors.length) console.log('  (none — selector stats not emitted)');
  console.log(`\n--- longest individual Recalculate Style events ---`);
  for (const e of summary.longestRecalc) {
    console.log(`  ${e.durMs.toFixed(2).padStart(8)} ms  ${JSON.stringify(e.beginData).slice(0, 150)}`);
  }
  console.log(`\n--- longest individual Layout events ---`);
  for (const e of summary.longestLayout) {
    console.log(`  ${e.durMs.toFixed(2).padStart(8)} ms  ${JSON.stringify(e.beginData).slice(0, 150)}`);
  }
}
