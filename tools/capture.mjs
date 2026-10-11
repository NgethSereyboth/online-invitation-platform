/**
 * capture.mjs — N independent captures of a page's document + section geometry.
 *
 * This is the determinism instrument. It exists because a single screenshot (or
 * a single height measurement) cannot distinguish "this page is stable" from
 * "this page happened to land on the same value twice". 50 captures, each in a
 * fresh page in the same browser process, produce a distribution; a distribution
 * with exactly one bucket is determinism, and a distribution with two is a race
 * with a reproducible signature.
 *
 * The public.html content-visibility race was identified and then closed with
 * this tool: pre-fix it reported `5440|5440.06|14|833` (the intrinsic-size
 * placeholder), post-fix `4220|4220.06|14|1258` (the real content height), each
 * 50 times out of 50.
 *
 * Usage
 *   node tools/capture.mjs [url] [--n=50] [--settle=1200] [--mode=wild|fixed]
 *                         [--width=1280] [--height=900] [--json] [--out=FILE]
 *
 *   --mode=fixed  injects the motion-freeze stylesheet before the document
 *                 script runs, so layout is the only variable left.
 *   --lang=km     pins the UI language before any document script runs, by
 *                 writing the same localStorage key the site's own language
 *                 picker writes (`einvite-lang`). Needed because half the
 *                 regression surface is Khmer and the default depends on the
 *                 browser's Accept-Language. Also sets documentElement.lang.
 *   --quiet       print only the machine-readable summary line.
 *
 * Output: a `docHeight|bodyHeight|nSections|textLen` distribution, a section
 * layout distribution, a console-error count, and (with --json/--out) the full
 * per-capture rows. Written to stdout and optionally to artifacts/.
 *
 * Requires: node + the repo's package.json devDependencies (puppeteer-core).
 */
import { writeFileSync } from 'node:fs';

import { FREEZE_CSS, launch, newPage } from './lib/browser.mjs';
import { artifactPath, hasFlag, pageUrl, urlFromArg } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const URL = urlFromArg(argv.find((a) => !a.startsWith('--')));
const N = Number((argv.find((a) => a.startsWith('--n=')) || '--n=50').split('=')[1]);
const SETTLE_MS = Number((argv.find((a) => a.startsWith('--settle=')) || '--settle=1200').split('=')[1]);
const MODE = (argv.find((a) => a.startsWith('--mode=')) || '--mode=wild').split('=')[1];
const WIDTH = Number((argv.find((a) => a.startsWith('--width=')) || '--width=1280').split('=')[1]);
const HEIGHT = Number((argv.find((a) => a.startsWith('--height=')) || '--height=900').split('=')[1]);
const AS_JSON = hasFlag(argv, 'json');
const QUIET = hasFlag(argv, 'quiet');
const LANG = (argv.find((a) => a.startsWith('--lang=')) || '').split('=')[1] || null;
const OUT = (argv.find((a) => a.startsWith('--out=')) || '').split('=')[1] || null;

if (LANG && !/^(en|km)$/.test(LANG)) {
  console.error(`capture.mjs: --lang must be en or km (got ${LANG})`);
  process.exit(2);
}

const browser = await launch({ kind: 'shell' });

const dist = new Map();
const sectionDist = new Map();
const rows = [];
for (let i = 0; i < N; i++) {
  const page = await newPage(browser, { width: WIDTH, height: HEIGHT, deviceScaleFactor: 1 });
  if (LANG) {
    await page.evaluateOnNewDocument((lang) => {
      try { localStorage.setItem('einvite-lang', lang); } catch { /* ignore */ }
      document.documentElement.lang = lang;
    }, LANG);
  }
  if (MODE === 'fixed') {
    await page.evaluateOnNewDocument((css) => {
      const s = document.createElement('style');
      s.textContent = css;
      document.documentElement.appendChild(s);
    }, FREEZE_CSS);
  }
  const errs = [];
  // Record the failing URL, not just the console text. A bare
  // "Failed to load resource: 404" says nothing about WHAT 404'd; the URL is
  // how a dangling reference (a tracked page pointing at an uncommitted asset)
  // is told apart from a genuine server fault.
  page.on('response', (r) => { if (r.status() >= 400) errs.push(`http ${r.status()} ${r.url().replace(/^https?:\/\/[^/]+/, '')}`); });
  page.on('requestfailed', (r) => errs.push(`requestfailed ${r.url().replace(/^https?:\/\/[^/]+/, '')} ${r.failure()?.errorText || ''}`));
  page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
  await new Promise((r) => setTimeout(r, SETTLE_MS));
  const snap = await page.evaluate(() => {
    const secs = [...document.querySelectorAll('section,form#rsvp,main > *')].map((el) => ({
      tag: el.tagName,
      cls: (el.className && typeof el.className === 'string') ? el.className : '',
      h: Math.round(el.getBoundingClientRect().height * 100) / 100,
    }));
    const root = document.getElementById('publicRoot') || document.body;
    return {
      docH: document.documentElement.scrollHeight,
      bodyH: Math.round(document.body.getBoundingClientRect().height * 100) / 100,
      nSecs: secs.length,
      secs,
      text: (root.innerText || '').length,
    };
  });
  const key = `${snap.docH}|${snap.bodyH}|${snap.nSecs}|${snap.text}`;
  dist.set(key, (dist.get(key) || 0) + 1);
  const sk = JSON.stringify(snap.secs.map((s) => [s.tag, s.cls, s.h]));
  sectionDist.set(sk, (sectionDist.get(sk) || 0) + 1);
  rows.push({ i, ...snap, errs });
  await page.close();
}
await browser.close();

const byCountDesc = (m) => [...m.entries()].sort((a, b) => b[1] - a[1]);
const sortedDoc = byCountDesc(dist);
const errCount = rows.reduce((a, r) => a + r.errs.length, 0);
const summary = {
  url: URL,
  mode: MODE,
  lang: LANG,
  n: N,
  settleMs: SETTLE_MS,
  viewport: `${WIDTH}x${HEIGHT}`,
  distinctStates: dist.size,
  deterministic: dist.size === 1,
  docDist: sortedDoc.map(([k, v]) => ({ key: k, count: v })),
  sectionStates: sectionDist.size,
  consoleErrors: errCount,
};
const report = { summary, rows };

if (!QUIET) {
  console.log(`MODE=${MODE} URL=${URL} N=${N} SETTLE_MS=${SETTLE_MS} VIEWPORT=${WIDTH}x${HEIGHT}`);
  console.log('--- docHeight|bodyHeight|nSections|textLen distribution ---');
  for (const [k, v] of sortedDoc) console.log(`${String(v).padStart(3)}x  ${k}`);
  console.log('--- section-layout distribution ---');
  for (const [k, v] of byCountDesc(sectionDist)) console.log(`${String(v).padStart(3)}x  ${k}`);
  console.log('total console errors:', errCount);
  if (errCount) console.log(JSON.stringify([...new Set(rows.flatMap((r) => r.errs))], null, 1));
  console.log(`VERDICT: ${summary.deterministic ? `deterministic — ${N}/${N} captures identical` : `NONDETERMINISTIC — ${dist.size} distinct states in ${N} captures`}`);
}

if (OUT) {
  const file = artifactPath(OUT);
  writeFileSync(file, JSON.stringify(report, null, 1));
  console.log(summaryLine(summary) + ` raw=${file}`);
} else if (AS_JSON) {
  console.log(JSON.stringify(report, null, 0));
}

function summaryLine(s) {
  return `CAPTURE_SUMMARY url=${s.url} n=${s.n} distinct=${s.distinctStates} ` +
    `deterministic=${s.deterministic} docH=${s.docDist.map((d) => `${d.count}x:${d.key.split('|')[0]}`).join(',')} ` +
    `consoleErrors=${s.consoleErrors}`;
}
