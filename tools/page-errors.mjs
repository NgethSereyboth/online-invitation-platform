/**
 * page-errors.mjs — load every page and report console errors and non-2xx responses.
 *
 * This is the cheap smoke gate that runs after any change to CSS, JS or HTML:
 * a page that still renders the same but no longer resolves a resource, or now
 * throws, is a regression the screenshot diff and the height captures both miss.
 *
 * Usage
 *   node tools/page-errors.mjs [--all] [page ...] [--settle=600] [--json]
 *
 * Requires: node + puppeteer-core, and a running server (tools/serve-gzip.py).
 * Produces: per-page counts, a list of distinct errors/URLs, and a TOTAL line.
 */
import { hasFlag, pageUrl, PAGES } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const argv = process.argv.slice(2);
const AS_JSON = hasFlag(argv, 'json');
const ALL = hasFlag(argv, 'all') || argv.filter((a) => !a.startsWith('--')).length === 0;
const SETTLE = Number((argv.find((a) => a.startsWith('--settle=')) || '--settle=600').split('=')[1]);
const named = argv.filter((a) => !a.startsWith('--'));
const pages = ALL ? PAGES : named.map((p) => (p.endsWith('.html') ? p : `${p}.html`));

const browser = await launch({ kind: 'full' });
let totalErrors = 0, totalBad = 0;
const rows = [];
for (const p of pages) {
  const page = await newPage(browser, { width: 1366, height: 900 });
  const errs = [], bad = [];
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', (e) => errs.push('pageerror: ' + String(e.message).slice(0, 160)));
  page.on('response', (r) => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url().replace(/^https?:\/\/[^/]+/, '')}`); });
  try {
    await page.goto(pageUrl(p), { waitUntil: 'networkidle0', timeout: 40000 });
  } catch (e) {
    errs.push('nav: ' + String(e.message).slice(0, 120));
  }
  await new Promise((r) => setTimeout(r, SETTLE));
  totalErrors += errs.length; totalBad += bad.length;
  rows.push({ page: p, consoleErrors: errs.length, non2xx: bad.length, errors: [...new Set(errs)], http: [...new Set(bad)] });
  if (!AS_JSON) {
    console.log(`${p}: consoleErrors=${errs.length} non2xx=${bad.length}`);
    if (errs.length) console.log('   errors: ' + JSON.stringify([...new Set(errs)], null, 1));
    if (bad.length) console.log('   http:   ' + JSON.stringify([...new Set(bad)], null, 1));
  }
  await page.close();
}
await browser.close();

if (AS_JSON) console.log(JSON.stringify({ rows, totalErrors, totalBad }, null, 1));
else console.log(`TOTAL pages=${pages.length} consoleErrors=${totalErrors} non2xx=${totalBad}`);
process.exitCode = totalErrors || totalBad ? 1 : 0;
