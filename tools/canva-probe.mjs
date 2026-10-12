/**
 * canva-probe.mjs — capture a performance trace and a JS asset inventory from
 * Canva's *public* pages, for comparison with this project's own numbers.
 *
 * Why this exists
 * ---------------
 * Goal 0 of the Canva-analysis pass asks how a mature design editor solves the
 * same class of problems this project solves — canvas rendering, panel layout,
 * large stylesheets, long style-recalc passes. Canva publishes no editor source
 * (no public Easel source tree, no dev bundle on npm), so the only honest input
 * is the live site observed through a browser. This tool is that observation,
 * and it is deliberately read-only: it loads pages, records what the network
 * delivered and what the main thread did, and writes two artifacts.
 *
 * What it produces (under artifacts/, never /tmp — see tools/README.md)
 *   <prefix>-trace.json         the raw CDP trace event list for the primary target
 *   <prefix>-scripts.json       every script/stylesheet the page fetched, with sizes
 *   <prefix>-probe-summary.json per-target status, title, final URL, counts
 *
 * `--prefix` (default `canva`) names those three files, so the same instrument
 * traces a Canva page and this project's own served pages and the two traces are
 * then compared by one analyzer. The default keeps the names the pass brief
 * names: artifacts/canva-trace.json and artifacts/canva-scripts.json.
 *
 * What it deliberately does NOT do
 *   * It never logs in. Canva's editor requires an account; the probe visits
 *     only the public marketing / template pages and records the HTTP status so
 *     a login wall is visible in the artifact rather than silently skipped.
 *   * It never evaluates page-supplied strings as commands and never posts
 *     anything. The page text is data.
 *
 * Usage
 *   node tools/canva-probe.mjs
 *   node tools/canva-probe.mjs https://www.canva.com/templates/ --wait=9000
 *   node tools/canva-probe.mjs --targets=https://www.canva.com/,https://www.canva.com/templates/
 *
 * Browser: the repo's puppeteer-core + resolved Chrome (tools/lib/browser.mjs).
 * The brief for this pass named Playwright; the repo's hard rule is that
 * package.json is not edited, and puppeteer-core 25.12.0 is already declared
 * there and is what every other instrument in tools/ measures with. Using the
 * same browser keeps the Canva numbers comparable with the project's own.
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, argValue, hasFlag } from './lib/repo.mjs';
import { describeChrome, launch, newPage } from './lib/browser.mjs';

const DEFAULT_TARGETS = ['https://www.canva.com/', 'https://www.canva.com/templates/'];
const argv = process.argv.slice(2);

const positional = argv.filter((a) => !a.startsWith('--'));
const fromFlag = argValue(argv, 'targets', null);
const TARGETS = fromFlag
  ? String(fromFlag).split(',').map((s) => s.trim()).filter(Boolean)
  : positional.length
    ? positional
    : DEFAULT_TARGETS;

const WAIT = Number(argValue(argv, 'wait', 8000));
const PREFIX = String(argValue(argv, 'prefix', 'canva'));
const PRIMARY = TARGETS[0];
const AS_JSON = hasFlag(argv, 'json');
const INSTRUMENT_OBSERVERS = !hasFlag(argv, 'no-observer-probe');

// A real desktop UA. Headless Chrome's default UA announces itself, and the
// point of the probe is to observe the same document a browser user gets; a
// bot-wall response is recorded either way, but this removes one trivial
// reason to be served a different page.
const UA =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
  'Chrome/154.0.0.0 Safari/537.36';

// `disabled-by-default-devtools.timeline.stack` is the category DevTools adds when
// it wants the "forced reflow" annotation: it attaches an `args.stackTrace` to
// Layout events that were begun from script. Without it a *forced synchronous*
// layout is indistinguishable from a scheduled one in the trace, which is the
// question this pass asks. Whether the category actually produces stack traces is
// measured at run time, not assumed — `--format=json` prints the count.
const TRACE_CATEGORIES = [
  'devtools.timeline',
  'blink.user_timing',
  'loading',
  'v8',
  'disabled-by-default-devtools.timeline',
  'disabled-by-default-devtools.timeline.stack',
  'disabled-by-default-devtools.timeline.invalidationTracking',
  'disabled-by-default-v8.compile',
];

/**
 * Count observer construction and callback invocations on the page.
 *
 * There is no ResizeObserver trace event in Chrome's trace format — measured:
 * a 157,111-event trace of canva.com contains `IntersectionObserverController::
 * computeIntersections` (759) and no event whose name mentions resize-observer
 * (
 * artifacts/canva-trace.json). So the only way to answer "does the page drive
 * its layout from a ResizeObserver" is to wrap the constructor before the page's
 * own scripts run and count. This is added instrumentation: it observes, it does
 * not alter the boxes the page sees (the wrapped callback is called with the
 * original entry list), and the report says so.
 */
const OBSERVER_PROBE = `(() => {
  const c = { resizeObservers: 0, resizeCallbacks: 0, resizeEntries: 0,
              intersectionObservers: 0, intersectionCallbacks: 0,
              mutationObservers: 0, mutationCallbacks: 0,
              wrapErrors: 0 };
  window.__observerCounters = c;
  const wrap = (name, ctorKey, cbKey, entryKey, entryLenKey) => {
    const Orig = window[name];
    if (typeof Orig !== 'function') return;
    function Wrapped(cb, ...rest) {
      try {
        c[ctorKey] += 1;
        const guarded = function (entries, observer) {
          try {
            c[cbKey] += 1;
            if (entries && typeof entries.length === 'number') c[entryLenKey] += entries.length;
            else if (entries) c[entryLenKey] += 1;
          } catch (e) { /* counting must never break the page */ }
          return cb.call(this, entries, observer);
        };
        return new Orig(guarded, ...rest);
      } catch (e) { c.wrapErrors += 1; return new Orig(cb, ...rest); }
    }
    Wrapped.prototype = Orig.prototype;
    Object.defineProperty(Wrapped, 'name', { value: name });
    window[name] = Wrapped;
  };
  wrap('ResizeObserver', 'resizeObservers', 'resizeCallbacks', 'resizeEntries', 'resizeEntries');
  wrap('IntersectionObserver', 'intersectionObservers', 'intersectionCallbacks', 'intersectionEntries', 'intersectionEntries');
  wrap('MutationObserver', 'mutationObservers', 'mutationCallbacks', 'mutationEntries', 'mutationEntries');
})();`;

const browser = await launch({ kind: 'full', extraArgs: ['--disable-blink-features=AutomationControlled'] });

const targets = [];
let primaryEvents = null;
const scripts = new Map(); // url -> { url, type, transferBytes, decodedBytes, target }

for (const url of TARGETS) {
  const page = await newPage(browser, { width: 1440, height: 900 });
  await page.setUserAgent(UA);
  if (INSTRUMENT_OBSERVERS) await page.evaluateOnNewDocument(OBSERVER_PROBE);
  const cdp = await page.target().createCDPSession();

  const responses = new Map(); // requestId -> { url, type, encodedDataLength, mimeType, status }
  const events = [];
  cdp.on('Network.responseReceived', (e) => {
    responses.set(e.requestId, {
      url: e.response.url,
      type: e.type,
      status: e.response.status,
      mimeType: e.response.mimeType,
      encodedDataLength: e.response.encodedDataLength ?? 0,
    });
  });
  cdp.on('Network.loadingFinished', (e) => {
    const hit = responses.get(e.requestId);
    if (hit) hit.encodedDataLength = e.encodedDataLength ?? hit.encodedDataLength;
  });
  await cdp.send('Network.enable', {});

  const isPrimary = url === PRIMARY;
  if (isPrimary) {
    cdp.on('Tracing.dataCollected', ({ value }) => events.push(...value));
  }
  let tracingDone = Promise.resolve();
  if (isPrimary) {
    tracingDone = new Promise((resolve) => cdp.once('Tracing.tracingComplete', resolve));
    await cdp.send('Tracing.start', {
      transferMode: 'ReportEvents',
      traceConfig: { recordMode: 'recordAsMuchAsPossible', includedCategories: TRACE_CATEGORIES },
    });
  }

  const started = Date.now();
  let error = null;
  let status = null;
  try {
    const resp = await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    status = resp ? resp.status() : null;
  } catch (e) {
    error = String(e && e.message ? e.message : e);
  }
  // The load event is not the end of a marketing page: fonts swap, lazy hero
  // images decode, and the framework hydrates after `load`. Wait for network
  // idle within the budget so the trace covers the work, not just the shell.
  try {
    await page.waitForNetworkIdle({ idleTime: 1000, timeout: WAIT }).catch(() => {});
  } catch { /* older API shape: fall through to the flat wait */ }
  await new Promise((r) => setTimeout(r, Math.min(WAIT, 2500)));
  const elapsed = Date.now() - started;

  let observerCounters = null;
  try {
    observerCounters = await page.evaluate(() => window.__observerCounters || null);
  } catch { /* page context gone */ }

  let title = null;
  let resourceEntries = [];
  try {
    title = await page.title();
  } catch { /* navigation may have left no document */ }
  try {
    resourceEntries = await page.evaluate(() =>
      performance.getEntriesByType('resource').map((r) => ({
        name: r.name,
        initiatorType: r.initiatorType,
        transferSize: r.transferSize,
        decodedBodySize: r.decodedBodySize,
        duration: r.duration,
      })),
    );
  } catch { /* page context gone */ }

  if (isPrimary) {
    await cdp.send('Tracing.end').catch(() => {});
    await tracingDone;
    primaryEvents = events;
  }

  // Fold both views together: the Network domain reports status/mime/type,
  // the PerformanceResourceTiming view reports decoded body size, which is the
  // number that matters when comparing payloads rather than transfer size.
  const decodedByUrl = new Map(resourceEntries.map((r) => [r.name, r]));
  for (const hit of responses.values()) {
    if (!/javascript|css|script/i.test(`${hit.type} ${hit.mimeType}`)) continue;
    const key = hit.url;
    const perf = decodedByUrl.get(key);
    const prev = scripts.get(key) || { url: key, type: hit.type, mimeType: hit.mimeType, seenOn: [] };
    scripts.set(key, {
      ...prev,
      type: hit.type || prev.type,
      mimeType: hit.mimeType || prev.mimeType,
      status: hit.status,
      transferBytes: Math.max(prev.transferBytes || 0, hit.encodedDataLength || 0),
      decodedBytes: Math.max(prev.decodedBytes || 0, perf ? perf.decodedBodySize || 0 : 0),
      seenOn: Array.from(new Set([...(prev.seenOn || []), url])),
    });
  }

  targets.push({
    url,
    finalUrl: page.url(),
    status,
    title,
    error,
    elapsedMs: elapsed,
    responses: responses.size,
    resources: resourceEntries.length,
    traceEvents: isPrimary ? events.length : 0,
    traced: isPrimary,
    observerCounters,
  });

  await page.close().catch(() => {});
}

await browser.close();

const scriptRows = Array.from(scripts.values()).sort((a, b) => (b.decodedBytes || 0) - (a.decodedBytes || 0));
const scriptsArtifact = {
  capturedAt: new Date().toISOString(),
  ua: UA,
  chrome: describeChrome('full'),
  targets: TARGETS,
  count: scriptRows.length,
  totalDecodedBytes: scriptRows.reduce((n, r) => n + (r.decodedBytes || 0), 0),
  totalTransferBytes: scriptRows.reduce((n, r) => n + (r.transferBytes || 0), 0),
  scripts: scriptRows,
};

writeFileSync(artifactPath(`${PREFIX}-scripts.json`), JSON.stringify(scriptsArtifact, null, 1));
if (primaryEvents) {
  writeFileSync(
    artifactPath(`${PREFIX}-trace.json`),
    JSON.stringify({ primaryTarget: PRIMARY, capturedAt: new Date().toISOString(), traceEvents: primaryEvents }),
  );
}
writeFileSync(
  artifactPath(`${PREFIX}-probe-summary.json`),
  JSON.stringify(
    {
      capturedAt: new Date().toISOString(),
      chrome: describeChrome('full'),
      instrumented: { observers: INSTRUMENT_OBSERVERS, traceCategories: TRACE_CATEGORIES },
      targets,
    },
    null,
    1,
  ),
);

// The forced-reflow question, answered from the trace rather than asserted: how
// many Layout events carry the stack trace the `...timeline.stack` category is
// supposed to attach.
const layoutEvents = (primaryEvents || []).filter((e) => e.ph === 'X' && e.name === 'Layout');
const forcedLayouts = layoutEvents.filter((e) => e.args && e.args.stackTrace);
const observerTotals = targets.reduce(
  (acc, t) => {
    for (const [k, v] of Object.entries(t.observerCounters || {})) acc[k] = (acc[k] || 0) + v;
    return acc;
  },
  {},
);

if (AS_JSON) {
  console.log(JSON.stringify({ targets, scriptCount: scriptRows.length, totalDecodedBytes: scriptsArtifact.totalDecodedBytes }, null, 1));
} else {
  console.log(`CANVA_PROBE chrome=${describeChrome('full')}`);
  for (const t of targets) {
    console.log(
      `  ${t.status ?? 'ERR'}  ${t.url}  title=${JSON.stringify(t.title)}  responses=${t.responses}  resources=${t.resources}  traceEvents=${t.traceEvents}  ${t.elapsedMs}ms${t.error ? `  error=${t.error}` : ''}`,
    );
  }
  console.log(
    `CANVA_SCRIPTS {"count": ${scriptRows.length}, "totalDecodedBytes": ${scriptsArtifact.totalDecodedBytes}, "totalTransferBytes": ${scriptsArtifact.totalTransferBytes}}`,
  );
  console.log(
    `CANVA_LAYOUT {"layoutEvents": ${layoutEvents.length}, "withStackTrace": ${forcedLayouts.length}}`,
  );
  console.log(`CANVA_OBSERVERS ${JSON.stringify(observerTotals)}`);
  console.log('  top 10 by decoded bytes:');
  for (const r of scriptRows.slice(0, 10)) {
    console.log(`    ${String(r.decodedBytes).padStart(9)}  ${r.type.padEnd(10)}  ${r.url.slice(0, 110)}`);
  }
}
