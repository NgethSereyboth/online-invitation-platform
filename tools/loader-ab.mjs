/**
 * loader-ab.mjs — does the deferred loader's serial promise chain cost anything,
 * and is the load ORDER load-bearing?
 *
 * performance-loader-v22.js appends its 23 feature modules through
 *   a.reduce((p, n) => p.then(() => new Promise(...)), Promise.resolve())
 * which is strictly one-at-a-time: module n+1 is not even requested until module
 * n has loaded and executed. Dynamically inserted scripts are `async` by
 * default, so that chain is the only thing enforcing order.
 *
 * Arm A serves the bundle unchanged. Arm B serves the SAME bundle with only the
 * chain replaced by Promise.all — identical module list, identical insertion
 * code, the sole difference being whether the next request waits.
 *
 * Two questions, answered in one run:
 *   1. how much wall-clock does the chain cost, and
 *   2. does dropping it change the page (globals defined, DOM size, errors)?
 *
 * Why the assertions matter: the first version of this experiment intercepted
 * `performance-loader-v22.js` as a URL. It never matched, because the loader is
 * concatenated into the route bundle, so it silently compared the serial build
 * against itself and printed a plausible-looking "-206 ms". `patched` is now
 * asserted and a run where arm B was not actually patched ABORTS (exit 3)
 * instead of printing noise. One pair is also not a measurement: the rejected
 * change in the prior report only looked like a win until three pairs were run.
 *
 * Usage
 *   node tools/loader-ab.mjs [url] [--pairs=3] [--bundle=bundle-index-v15.js]
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: a per-pair metric table, a globals diff and a verdict; exit 3 if
 * arm B was never patched.
 */
import { hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')) || pageUrl('index.html'));
const PAIRS = Number((argv.find((a) => a.startsWith('--pairs=')) || '--pairs=3').split('=')[1]);
// The loader is NOT a separate request: it is concatenated into the route
// bundle, so the bundle is what has to be intercepted.
const LOADER = (argv.find((a) => a.startsWith('--bundle=')) || '--bundle=bundle-index-v15.js').split('=')[1];
const AS_JSON = hasFlag(argv, 'json');

const SERIAL = "a.reduce((p,n)=>p.then(()=>new Promise((r,j)=>{let s=document.createElement('script');s.src=n;s.onload=r;s.onerror=j;document.head.append(s)})),Promise.resolve())";
const PARALLEL = "Promise.all(a.map(n=>new Promise((r,j)=>{let s=document.createElement('script');s.src=n;s.onload=r;s.onerror=j;document.head.append(s)})))";

async function run(arm) {
  const browser = await launch({ kind: 'full' });
  const page = await newPage(browser, { width: 1366, height: 900 });
  await page.setRequestInterception(true);
  let patched = 0, patchFailed = null;
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e).slice(0, 140)));

  page.on('request', async (req) => {
    if (arm === 'parallel' && req.url().endsWith(LOADER) && req.resourceType() === 'script') {
      try {
        const res = await fetch(req.url());
        const body = await res.text();
        if (!body.includes(SERIAL)) { patchFailed = 'chain text not found verbatim'; }
        const out = body.includes(SERIAL) ? body.replace(SERIAL, PARALLEL) : body;
        patched++;
        req.respond({ status: 200, contentType: 'application/javascript', body: out });
      } catch (e) {
        patchFailed = String(e).slice(0, 120);
        req.continue();
      }
      return;
    }
    req.continue();
  });

  const t0 = Date.now();
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 90000 });
  const wallToIdle = Date.now() - t0;
  await new Promise((r) => setTimeout(r, 1500));

  const measured = await page.evaluate(() => {
    const res = performance.getEntriesByType('resource').filter((e) => e.name.endsWith('.js'));
    const ends = res.map((e) => e.responseEnd).sort((a, b) => a - b);
    const nav = performance.getEntriesByType('navigation')[0] || {};
    const fcp = (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime ?? null;
    const lcp = performance.getEntriesByType('largest-contentful-paint').slice(-1)[0];
    const globals = Object.keys(window)
      .filter((k) => /^(EInvite|EI|Studio|Canvas|Render|Scene|Workflow|Template|Photo|Asset|Review|Brand|Collab|Export|Print|Smart|Direct|Content|Navigation|Style|Adaptive|Professional)/.test(k))
      .sort();
    return {
      jsRequests: res.length,
      scriptSpanMs: ends.length ? Math.round(ends[ends.length - 1] - ends[0]) : 0,
      lastScriptEndMs: ends.length ? Math.round(ends[ends.length - 1]) : 0,
      domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd || 0),
      loadEventMs: Math.round(nav.loadEventEnd || 0),
      fcpMs: fcp === null ? null : Math.round(fcp),
      lcpMs: lcp ? Math.round(lcp.startTime) : null,
      domElements: document.querySelectorAll('*').length,
      globalsCount: globals.length,
      globals,
      canvases: document.querySelectorAll('canvas').length,
    };
  });
  await browser.close();
  return { arm, wallToIdle, patched, patchFailed, errors: pageErrors, ...measured };
}

const pairs = [];
for (let i = 0; i < PAIRS; i++) {
  const A = await run('serial');
  const B = await run('parallel');
  pairs.push({ pair: i + 1, A, B });
}

const keys = ['wallToIdle', 'jsRequests', 'scriptSpanMs', 'lastScriptEndMs', 'domContentLoadedMs',
  'loadEventMs', 'fcpMs', 'lcpMs', 'domElements', 'globalsCount', 'canvases'];

let voided = false;
if (AS_JSON) {
  console.log(JSON.stringify(pairs, null, 1));
} else {
  console.log(`URL ${URL}   bundle=${LOADER}   pairs=${PAIRS}\n`);
  for (const { pair, A, B } of pairs) {
    console.log(`--- pair ${pair} ---`);
    console.log(`  ${'metric'.padEnd(20)} ${'A serial'.padStart(12)} ${'B parallel'.padStart(12)}   delta`);
    for (const k of keys) {
      const a = A[k], b = B[k];
      const delta = (typeof a === 'number' && typeof b === 'number') ? b - a : '';
      console.log(`  ${k.padEnd(20)} ${String(a).padStart(12)} ${String(b).padStart(12)}   ${delta === '' ? '' : (delta > 0 ? '+' : '') + delta}`);
    }
    const onlyA = A.globals.filter((g) => !B.globals.includes(g));
    const onlyB = B.globals.filter((g) => !A.globals.includes(g));
    console.log(`  globals only in A (serial): ${onlyA.length ? onlyA.join(', ') : 'none'}`);
    console.log(`  globals only in B (parallel): ${onlyB.length ? onlyB.join(', ') : 'none'}`);
    console.log(`  page errors A=${A.errors.length} B=${B.errors.length}\n`);
    if (B.patched === 0 || B.patchFailed) {
      voided = true;
      console.log(`ARM B WAS NEVER PATCHED (patched=${B.patched}, error=${B.patchFailed}) —`);
      console.log('this comparison is void, not evidence.\n');
    }
  }
  const last = pairs[pairs.length - 1];
  const anyGlobalsDiffer = pairs.some(({ A, B }) => A.globals.some((g) => !B.globals.includes(g)));
  console.log(`VERDICT: ${!voided && !anyGlobalsDiffer && !last.B.errors.length
    ? 'identical module surface across all pairs — the chain is not protecting load order on this page'
    : 'module surface DIFFERS (or a pair was void) — order is load-bearing, keep the chain'}`);
}
process.exitCode = voided ? 3 : 0;
