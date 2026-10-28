/**
 * dashboard-network-idle.mjs — why a signed-in page never reaches network idle.
 *
 * The gap this closes
 * -------------------
 * `tools/page-errors.mjs --all --as=…` loads each page with `waitUntil:
 * 'networkidle0'`. On the signed-in dashboard that never settles, and a navigation
 * timeout is reported like any other console error — indistinguishable from a page
 * that really is broken. It is not obvious from the outside which request is
 * responsible: the page issues two `/api/invitations` GETs and only one of them
 * shows a CDP terminal event, so counting requests does not explain the stall.
 *
 * This probe answers it by varying one thing. `dashboard-polish.js` has a
 * local-first guard (`sovan-multi-invites-v1`): when the key is present the module
 * returns before it probes the server, so exactly one `/api/invitations` request is
 * made. Running the same page twice — once seeding that key, once not — turns the
 * stall into a difference of one request.
 *
 * Measured 2026-10-15, signed-in dashboard, before the fix in `dashboard-polish.js`:
 *
 *   seedLocal=false  → 2 requests, networkidle0 timed out after 25 s
 *   seedLocal=true   → 1 request,  networkidle0 settled
 *
 * Cause: the probe fetched `/api/invitations` and never read the response body, so
 * the request stayed in flight and the 28 KB payload was downloaded unused.
 * After cancelling the body, both rows settle and the difference disappears.
 *
 * Usage
 *   node tools/dashboard-network-idle.mjs --as=user@example.com:password
 *   BASE_URL=http://127.0.0.1:8395 node tools/dashboard-network-idle.mjs --as=…
 *
 * Requires: node + puppeteer-core, and a running server. Exits 1 if either run
 * fails to settle, so it can be used as a regression gate for this specific stall.
 */
import { BASE_URL } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const AS = (process.argv.slice(2).find((a) => a.startsWith('--as=')) || '').slice('--as='.length);
if (!AS) {
  console.error('usage: node tools/dashboard-network-idle.mjs --as=email:password');
  process.exit(2);
}
const [EMAIL, PASSWORD] = [AS.slice(0, AS.indexOf(':')), AS.slice(AS.indexOf(':') + 1)];

async function run({ seedLocal }) {
  const browser = await launch({ kind: 'full' });
  const login = await newPage(browser);
  await login.goto(`${BASE_URL}/index.html`, { waitUntil: 'domcontentloaded', timeout: 40000 });
  const signedIn = await login.evaluate(async (email, password) => {
    const r = await fetch('/api/auth/login', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return r.status;
  }, EMAIL, PASSWORD);
  if (signedIn >= 400) {
    await browser.close();
    console.error(`login failed: status=${signedIn}`);
    process.exit(2);
  }
  const cookies = await login.cookies();
  await login.close();

  const page = await newPage(browser, { width: 1366, height: 900 });
  await page.setCookie(...cookies);
  if (seedLocal) {
    // dashboard-polish.js treats a stored array — empty or not — as authoritative.
    await page.evaluateOnNewDocument(() => {
      try { localStorage.setItem('sovan-multi-invites-v1', '[]'); } catch (e) { /* storage disabled */ }
    });
  }
  let invitations = 0;
  page.on('request', (r) => { if (/\/api\/invitations(\?|$)/.test(r.url())) invitations += 1; });
  let outcome;
  try {
    await page.goto(`${BASE_URL}/dashboard.html`, { waitUntil: 'networkidle0', timeout: 25000 });
    outcome = 'settled';
  } catch (e) {
    outcome = 'timeout';
  }
  const marker = await page.evaluate(() => document.body.dataset.page || 'NONE');
  await browser.close();
  return { seedLocal, outcome, invitations, marker, signedIn };
}

const rows = [await run({ seedLocal: false }), await run({ seedLocal: true })];
for (const r of rows) {
  console.log(
    `seedLocal=${String(r.seedLocal).padEnd(5)} networkidle0=${r.outcome.padEnd(8)} ` +
    `invitationsRequests=${r.invitations} marker=${r.marker}`
  );
}
process.exitCode = rows.every((r) => r.outcome === 'settled') ? 0 : 1;
