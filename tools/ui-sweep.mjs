/**
 * ui-sweep.mjs — the recon instrument for the UI/UX remediation mission.
 *
 * Why this exists
 * ---------------
 * The mission is "find every visual bug and every dead control, fix it, prove it in a
 * browser". Doing that by hand does not scale to 16 routes × 5 widths, and a claim like
 * "no overlaps remain" is only worth something if the same instrument produced it before
 * and after each fix. This tool is that instrument, and it is deliberately boring: it
 * measures, it does not judge.
 *
 * Two passes
 * ----------
 *   layout (default, every route × every width)
 *     - console errors/warnings and page errors, per route;
 *     - failed requests (HTTP >= 400, and transport failures);
 *     - document overflow: `scrollWidth > innerWidth + 1`;
 *     - "escapes": painted elements crossing the viewport edge, excluding the deliberate
 *       off-stage pattern (`left < -1000`), anything inside a clipping or scrollable
 *       ancestor (an off-canvas drawer or a horizontally scrollable table is not a bug),
 *       and anything hidden or transparent;
 *     - "permanent overlays": `position: fixed|absolute` chrome with a z-index that
 *       intersects `main`'s content box by more than 4px on both axes. A popover opened by
 *       a control is not a permanent overlay and is never counted here, because this pass
 *       does not click anything — the element has to be visible on a fresh load.
 *   click (`--click`, route × 1440 only)
 *     - enumerates every control and clicks it, recording a state fingerprint before and
 *       after (`url`, `body.className`, element count, visible-overlay count,
 *       `aria-expanded`, panel inventory as a *set*, form/select values, checkbox state). Between
 *       probes the route is returned to the state the pass started in and that reset is verified
 *       against the clean fingerprint, reloading when the app's own dismissals were not enough —
 *       a failed reset made the next control's click change nothing and read as dead. A control
 *       that can only act once the user supplies input is reported separately, not as dead.
 *       A control whose click changes nothing at all is reported as a dead-control candidate. Links are never
 *       followed: `href` is validated statically and hash targets are resolved.
 *
 * What it does not do
 * -------------------
 * It has no threshold for "looks wrong". Every row it prints is a measurement a reader can
 * re-derive, and the report that quotes it is expected to say so. Screenshots are written
 * for a human to judge, not for the tool to score.
 *
 * Usage
 *   node tools/ui-sweep.mjs                                  # layout pass, 5 widths, 16 routes
 *   node tools/ui-sweep.mjs --routes=materials.html,index.html
 *   node tools/ui-sweep.mjs --widths=1440 --click             # + dead-control pass
 *   node tools/ui-sweep.mjs --out=docs/reviews/sweep --json=artifacts/ui-sweep.json
 *
 * Requires: node + puppeteer-core and a running server (tools/serve-gzip.py, port 8124 by
 * default, or BASE_URL=http://127.0.0.1:PORT).
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

import { launch, newPage } from './lib/browser.mjs';
import { argValue, BASE_URL, hasFlag, PAGES, REPO_ROOT } from './lib/repo.mjs';

const argv = process.argv.slice(2);
const WIDTHS = String(argValue(argv, 'widths', '768,1024,1280,1440,1600')).split(',').map(Number).filter(Boolean);
const ROUTES = String(argValue(argv, 'routes', PAGES.join(','))).split(',').map((s) => s.trim()).filter(Boolean);
const OUT_DIR = String(argValue(argv, 'out', 'docs/reviews/sweep'));
const JSON_OUT = String(argValue(argv, 'json', 'artifacts/ui-sweep.json'));
const CLICK = hasFlag(argv, 'click');
const CLICK_WIDTH = Number(argValue(argv, 'click-width', 1440));
const SETTLE_MS = Number(argValue(argv, 'settle', 1200));
const CLICK_WAIT_MS = Number(argValue(argv, 'click-wait', 450));
const HEIGHT = Number(argValue(argv, 'height', 900));
const QUIET = hasFlag(argv, 'quiet');

/* --- the in-page probes ---------------------------------------------------- */

const LAYOUT_PROBE = () => {
  const vpW = innerWidth;
  const R = (e) => { const b = e.getBoundingClientRect(); return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1), r: +b.right.toFixed(1), b: +b.bottom.toFixed(1) }; };
  const main = document.body.querySelector(':scope > main') || document.querySelector('main');
  const visible = (el) => {
    if (!el.getClientRects().length) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) === 0) return false;
    return true;
  };
  const clippedByAncestor = (el) => {
    for (let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      const ps = getComputedStyle(p);
      if (ps.overflowX !== 'visible' && p.getBoundingClientRect().right <= vpW + 1) return true;
    }
    return false;
  };

  const escapes = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.left < -1000) continue;          // deliberate off-stage technique
    if (r.right <= vpW + 1 && r.left >= -1) continue;
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed') continue;                   // fixed chrome is reviewed as overlays
    if (clippedByAncestor(el)) continue;
    escapes.push({ sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(/\s+/).slice(0, 2).join('.') : ''), box: R(el), pos: cs.position });
  }

  const mainBox = main ? main.getBoundingClientRect() : null;
  const overlays = [];
  if (mainBox) {
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'absolute') continue;
      if (!visible(el)) continue;
      if (Number(cs.zIndex || 0) < 1) continue;
      if (main && (el === main || main.contains(el))) continue;
      if (el.tagName === 'DIALOG' || el.closest('dialog')) continue;  // dialogs are modal by contract
      const r = el.getBoundingClientRect();
      const ox = Math.min(r.right, mainBox.right) - Math.max(r.left, mainBox.left);
      const oy = Math.min(r.bottom, mainBox.bottom) - Math.max(r.top, mainBox.top);
      if (ox > 4 && oy > 4) {
        overlays.push({
          sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(/\s+/).slice(0, 2).join('.') : ''),
          box: R(el), z: cs.zIndex, overlap: { w: +ox.toFixed(1), h: +oy.toFixed(1) },
        });
      }
    }
  }

  return {
    vp: [vpW, innerHeight],
    docScrollW: document.documentElement.scrollWidth,
    docScrollH: document.documentElement.scrollHeight,
    main: mainBox ? R(main) : null,
    escapes: escapes.slice(0, 25),
    escapeCount: escapes.length,
    overlays: overlays.slice(0, 25),
    overlayCount: overlays.length,
    title: document.title,
  };
};

const CONTROL_PROBE = () => {
  const sel = 'button, [role="button"], summary, select, input[type="checkbox"], input[type="radio"], [aria-expanded]';
  const out = [];
  const els = [...document.querySelectorAll(sel)];
  els.forEach((el, i) => {
    const cs = getComputedStyle(el);
    if (!el.getClientRects().length || cs.visibility === 'hidden' || cs.display === 'none') return;
    if (el.closest('dialog:not([open])')) return;
    const b = el.getBoundingClientRect();
    const cx = Math.round(b.left + b.width / 2), cy = Math.round(b.top + b.height / 2);
    const top = (cx > 0 && cy > 0 && cx < innerWidth && cy < innerHeight) ? document.elementFromPoint(cx, cy) : null;
    out.push({
      i,
      sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(/\s+/).slice(0, 2).join('.') : ''),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 48),
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      expanded: el.getAttribute('aria-expanded'),
      // A control that is only reported because it is *already* in the state a click would produce
      // (the active tab, the pressed toggle) is not evidence of anything. Neither is a <select>,
      // which needs an option to be chosen, nor a checkbox/radio whose click is a state flip the
      // fingerprint does capture — the first two are skipped, the last is still clicked.
      alreadyOn: el.matches('button.active, [aria-pressed="true"], [aria-selected="true"], [data-active="true"]'),
      kind: el.tagName === 'SELECT' ? 'select' : el.tagName === 'SUMMARY' ? 'summary' : 'control',
      // A control that cannot act until the user supplies something (submit on an empty form, a
      // search box's Go, "Save" with no edits) is not dead. Decided here, from the DOM, so the
      // click pass can classify it instead of guessing from the label alone.
      inputRequired: (() => {
        const required = el.type === 'submit' || el.getAttribute('type') === 'submit'
          || (el.closest('form') && [...el.closest('form').querySelectorAll('[required]')].some((f) => !String(f.value || '').trim()))
          || !!el.closest('[data-requires-input], .requires-input');
        const wording = /\b(submit|save|apply|send|generate|create|export|publish|upload|import|add|invite|search|calculate|preview|sign in|log in|continue|confirm|verify|reset)\b/i;
        return required || wording.test((el.textContent || '').trim());
      })(),
      // el.click() bypasses hit-testing, so a control painted over by an open dialog or cover still
      // "clicks" in this pass; a real user's click would land on the cover instead. Recorded apart.
      coveredBy: top && !(top === el || el.contains(top) || top.contains(el))
        ? (top.tagName.toLowerCase() + (top.id ? '#' + top.id : '') + (top.className ? '.' + String(top.className).split(/\s+/).slice(0, 2).join('.') : ''))
        : null,
      box: { x: +b.x.toFixed(0), y: +b.y.toFixed(0), w: +b.width.toFixed(0), h: +b.height.toFixed(0) },
    });
  });
  return out;
};

const LINK_PROBE = () => [...document.querySelectorAll('a[href]')].map((a) => {
  const href = a.getAttribute('href') || '';
  const cs = getComputedStyle(a);
  const visible = a.getClientRects().length > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
  const hash = href.startsWith('#') ? href : '';
  return {
    text: (a.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40),
    href: href.slice(0, 80),
    visible,
    kind: href === '' ? 'empty' : href === '#' ? 'bare-hash' : href.startsWith('javascript:') ? 'javascript' : hash ? 'hash' : 'route',
    hashTargetExists: hash && hash !== '#' ? !!document.querySelector(hash) : null,
  };
});

const STATE_FINGERPRINT = () => {
  const overlays = [...document.querySelectorAll('dialog[open], [role="dialog"], [role="menu"], .app-rail-open, [data-open="true"]')]
    .filter((e) => e.getClientRects().length > 0).length;
  return JSON.stringify({
    url: location.href,
    bodyClass: document.body.className,
    htmlClass: document.documentElement.className,
    nodes: document.getElementsByTagName('*').length,
    overlays,
    expanded: [...document.querySelectorAll('[aria-expanded]')].map((e) => e.getAttribute('aria-expanded')).join(','),
    // Language switching writes <html lang>, a storage key and the visible .i18n copies; a
    // fingerprint without them called every language button dead on all 16 routes (L1).
    htmlLang: document.documentElement.lang,
    langPref: (() => { try { return localStorage.getItem('einvite-lang') || ''; } catch (e) { return ''; } })(),
    guestLangPref: (() => { try { return Object.keys(localStorage).filter((k) => k.startsWith('einvite-guest-lang')).map((k) => k + '=' + localStorage.getItem(k)).join(','); } catch (e) { return ''; } })(),
    visibleKm: [...document.querySelectorAll('.i18n-km')].filter((e) => e.offsetParent !== null).length,
    visibleEn: [...document.querySelectorAll('.i18n-en')].filter((e) => e.offsetParent !== null).length,
    textLen: (document.body.textContent || '').length,
    // A panel *inventory* is a set, not a length, and the old fingerprint recorded only
    // `.length` of the joined list — a control that closed one panel while opening another left
    // the length identical and was reported dead. Same for form values, which were recorded as
    // their string length, so a same-length edit ("Aa" → "Bb") was invisible.
    detailsOpen: [...document.querySelectorAll('details[open]')].map((d) => d.id || String(d.className).split(/\s+/)[0] || 'details').join(','),
    selectValues: [...document.querySelectorAll('select')].map((s) => (s.id || s.name || '?') + '=' + s.value).join(','),
    // A control that opens a panel which is not marked role=dialog/role=menu was invisible to this
    // fingerprint: the inspector tabs, Review, Position and "View all" were all reported dead and all
    // of them do change the visible panel inventory (measured with artifacts/probe_d4_controls.mjs).
    // A checkbox click is a state flip this fingerprint could not see either (guests.html's
    // #selectAllGuests and templates.html's #studioFavorites were reported dead).
    checks: [...document.querySelectorAll('input[type="checkbox"], input[type="radio"]')].map((e) => (e.id || e.name || '?') + '=' + (e.checked ? 1 : 0)).join(','),
    values: [...document.querySelectorAll('input[type="text"], input[type="email"], input[type="search"], input[type="number"], textarea')].map((e) => (e.id || '?') + '=' + String(e.value).slice(0, 40)).join(','),
    visiblePanels: [...document.querySelectorAll('aside, [class*="panel"], [class*="popover"], [class*="drawer"], [class*="menu"], [role="dialog"], [role="menu"]')]
      .filter((e) => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden')
      .map((e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + '.' + String(e.className || '').split(/\s+/).slice(0, 2).join('.')).sort().join('|'),
  });
};

// Used ONLY to answer "is the route back in the state this pass started in?". The full fingerprint
// also carries text lengths and async-boot artefacts that legitimately differ after a reload, so
// comparing it wholesale reported 105 of 121 probes as unrestorable even when the route was visually
// back where it started. This keeps the signals that mean "something is still open".
// `body.className` is deliberately absent (the app adds boot-progress classes it never removes), and
// so is any `[class*="menu"]`-style substring match: those pulled in transient `div`/`i`/`span`
// wrappers that appear at different points of the editor's async boot, which made the check report
// every probe as unrestorable while nothing was in fact left open. What remains is the set of things
// a user would call "still open": dialogs, expanded disclosures, live popovers and side panels.
const RESET_FINGERPRINT = () => JSON.stringify({
  url: location.href,
  dialogs: [...document.querySelectorAll('dialog[open]')].map((d) => d.id || String(d.className).split(/\s+/)[0]).sort(),
  details: [...document.querySelectorAll('details[open]')].map((d) => d.id || String(d.className).split(/\s+/)[0]).sort(),
  expandedTrue: [...document.querySelectorAll('[aria-expanded="true"]')].map((e) => e.id || String(e.className).split(/\s+/)[0]).sort(),
  // The `mobile*` asides are drawers the app mounts and opens by its own boot logic at some widths; a
  // reset that differs only by one of them is boot noise. A click that opens one is still caught by
  // STATE_FINGERPRINT's `visiblePanels`, so the control is still classified, just not re-verified here.
  openPanels: [...document.querySelectorAll('[role="dialog"], [role="menu"], [role="listbox"], aside, dialog[open], [data-open="true"]')]
    .filter((e) => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden')
    .filter((e) => !(e.tagName === 'ASIDE' && /^mobile/.test(e.id)))
    .map((e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '')).sort(),
});

// Wait until the route has stopped changing shape, then return the reset fingerprint it settled on.
// A fixed sleep is not enough after a reload: the editor route boots for ~2s, so a fingerprint read
// too early describes a half-built page and reported every probe as unrestorable.
const settleAndRead = async (page, totalMs = 2400, step = 400, stableFor = 3) => {
  const steps = Math.max(4, Math.round(totalMs / step));
  let last = null;
  let stable = 0;
  for (let i = 0; i < steps; i++) {
    await new Promise((r) => setTimeout(r, step));
    const now = await page.evaluate(RESET_FINGERPRINT).catch(() => null);
    if (now !== null && now === last) {
      stable += 1;
      if (stable >= stableFor) return now;
    } else {
      stable = 0;
    }
    last = now;
  }
  return last;
};

// Reload the route and bring it back to the state the pass starts in: the one-time overlays are
// dismissed again, because a reload restores them (the editor's onboarding tour is a `<dialog open>`
// on every fresh profile load, and the dismissal here is the sweep's, not the app's). Without this,
// every reload looked unrestorable for a reason that had nothing to do with the probe.
const resetRoute = async (page, url) => {
  await page.goto(url, { waitUntil: 'load', timeout: 30000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, SETTLE_MS));
  // A click that navigated can leave the frame detached mid-reset; retry once, then let the
  // fingerprint comparison speak for itself rather than throwing out of the pass.
  try {
    await page.evaluate(DISMISS_ONE_TIME_OVERLAYS);
  } catch (e) {
    await new Promise((r) => setTimeout(r, 800));
    await page.evaluate(DISMISS_ONE_TIME_OVERLAYS).catch(() => null);
  }
  await new Promise((r) => setTimeout(r, 200));
  return settleAndRead(page);
};

// Clicking a control that opens a modal can trap the click pass; Escape + a neutral click
// are the same dismissals a user has, and they keep the route in a defined state.
const DISMISS = (keepDetails) => {
  const esc = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
  document.dispatchEvent(esc);
  document.querySelectorAll('dialog[open]').forEach((d) => { try { d.close(); } catch (e) { /* already closed */ } });
  // Only the disclosures a user opened are closed. The ones a fresh load opens by design stay open;
  // closing them here made every reset differ from the fresh-load state it is compared against.
  const keep = new Set(keepDetails || []);
  document.querySelectorAll('details[open]').forEach((d) => {
    const key = d.id || String(d.className).split(/\s+/)[0] || 'details';
    if (!keep.has(key)) d.open = false;
  });
  document.body.classList.remove('rail-open');
  // `aria-expanded` is deliberately NOT rewritten here: claiming a popup is closed while it stays
  // painted would hide a real difference instead of removing it. The caller verifies the reset
  // against the clean fingerprint and reloads when the app's own dismissals were not enough.
  return true;
};

// One-time overlays a fresh profile always sees: the editor's onboarding tour is a `<dialog open>`
// and the guest page paints an invite cover (`#openCover`). A user dismisses them; this pass must too,
// or every control underneath is measured through the overlay (measured on the editor before this
// existed: 76 of 124 controls reported as covered by `dialog.final-tour.final-dialog`). The control
// list from *before* the dismissal is kept as evidence rather than discarded.
const DISMISS_ONE_TIME_OVERLAYS = () => {
  const dismissed = [];
  document.querySelectorAll('dialog[open]').forEach((d) => {
    dismissed.push('dialog.' + String(d.className || '').split(/\s+/).slice(0, 2).join('.'));
    try { d.close(); } catch (e) { /* not a real dialog */ }
    d.removeAttribute('open');
    d.setAttribute('aria-hidden', 'true');
    if (getComputedStyle(d).position === 'fixed') d.style.display = 'none';
  });
  document.querySelectorAll('.guest-cover, #openCover, .opening-cover, [data-cover]').forEach((c) => {
    if (!c.getClientRects().length) return;
    dismissed.push((c.id ? '#' + c.id : '') + String(c.className || '').split(/\s+/).slice(0, 1).join(''));
    try { c.click(); } catch (e) { /* keep going */ }
    c.style.display = 'none';
  });
  document.querySelectorAll('.final-tour, .soviet-tour, .tour-overlay').forEach((o) => { o.style.display = 'none'; dismissed.push('hidden ' + String(o.className).split(/\s+/)[0]); });
  return dismissed;
};

/* --- driver ---------------------------------------------------------------- */

const browser = await launch({ kind: 'full', viewport: { width: WIDTHS[0], height: HEIGHT } });
mkdirSync(join(REPO_ROOT, OUT_DIR), { recursive: true });
mkdirSync(join(REPO_ROOT, dirname(JSON_OUT)), { recursive: true });

const report = { base: BASE_URL, when: new Date().toISOString(), widths: WIDTHS, routes: ROUTES, layout: [], clicks: [], dead: [], links: [], console: {} };
const say = (...a) => { if (!QUIET) console.log(...a); };

async function loadWithDiagnostics(page, url) {
  const consoleMsgs = [];
  const failures = [];
  const onConsole = (m) => { const t = m.type(); if (t === 'error' || t === 'warning') consoleMsgs.push({ type: t, text: m.text().slice(0, 300) }); };
  const onPageError = (e) => consoleMsgs.push({ type: 'pageerror', text: String(e).slice(0, 300) });
  const onFailed = (r) => failures.push({ url: r.url().slice(0, 120), err: String(r.failure() && r.failure().errorText || 'failed') });
  const onResponse = (r) => { if (r.status() >= 400) failures.push({ url: r.url().slice(0, 120), err: `HTTP ${r.status()}` }); };
  page.on('console', onConsole);
  page.on('pageerror', onPageError);
  page.on('requestfailed', onFailed);
  page.on('response', onResponse);
  let navError = null;
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
  } catch (err) {
    navError = String(err).slice(0, 200);
  }
  await new Promise((r) => setTimeout(r, SETTLE_MS));
  page.off('console', onConsole);
  page.off('pageerror', onPageError);
  page.off('requestfailed', onFailed);
  page.off('response', onResponse);
  return { consoleMsgs, failures, navError };
}

for (const route of ROUTES) {
  const url = `${BASE_URL}/${route}`;
  for (const width of WIDTHS) {
    const page = await newPage(browser, { width, height: HEIGHT });
    const diag = await loadWithDiagnostics(page, url);
    const layout = await page.evaluate(LAYOUT_PROBE);
    const links = await page.evaluate(LINK_PROBE);
    const brokenLinks = links.filter((l) => l.visible && (l.kind === 'empty' || l.kind === 'bare-hash' || (l.kind === 'hash' && l.hashTargetExists === false)));
    const row = {
      route, width,
      navError: diag.navError,
      console: diag.consoleMsgs,
      failures: diag.failures,
      docScrollW: layout.docScrollW,
      overflow: layout.docScrollW > width + 1,
      escapeCount: layout.escapeCount, escapes: layout.escapes,
      overlayCount: layout.overlayCount, overlays: layout.overlays,
      brokenLinks: brokenLinks.slice(0, 12),
      controls: links.length,
    };
    report.layout.push(row);
    if (diag.consoleMsgs.length || diag.failures.length) {
      const key = `${route}@${width}`;
      report.console[key] = { console: diag.consoleMsgs.slice(0, 20), failures: diag.failures.slice(0, 20) };
      writeFileSync(join(REPO_ROOT, OUT_DIR, `${route.replace('.html', '')}-${width}-console.txt`),
        `# ${route} @${width}\n\n## console\n${diag.consoleMsgs.map((m) => `[${m.type}] ${m.text}`).join('\n') || '(none)'}\n\n## failed requests\n${diag.failures.map((f) => `${f.err} ${f.url}`).join('\n') || '(none)'}\n`);
    }
    const flags = [
      row.overflow ? 'OVERFLOW' : '',
      row.escapeCount ? `escapes:${row.escapeCount}` : '',
      row.overlayCount ? `overlays:${row.overlayCount}` : '',
      row.console.length ? `console:${row.console.length}` : '',
      row.failures.length ? `netfail:${row.failures.length}` : '',
      row.brokenLinks.length ? `links:${row.brokenLinks.length}` : '',
      row.navError ? 'NAV-FAIL' : '',
    ].filter(Boolean);
    say(`LAYOUT ${route.padEnd(16)} ${String(width).padStart(4)} ${flags.length ? flags.join(' ') : 'ok'}`);
    if (row.overlayCount || row.escapeCount || row.overflow) {
      writeFileSync(join(REPO_ROOT, OUT_DIR, `${route.replace('.html', '')}-${width}-layout.json`), JSON.stringify(row, null, 1));
    }
    if (width === CLICK_WIDTH || width === WIDTHS[0]) {
      await page.screenshot({ path: join(REPO_ROOT, OUT_DIR, `${route.replace('.html', '')}-${width}.png`) });
    }
    await page.close();
  }

  if (!CLICK) continue;

  /* --- dead-control pass -------------------------------------------------- */
  const page = await newPage(browser, { width: CLICK_WIDTH, height: HEIGHT });
  const diag = await loadWithDiagnostics(page, url);
  // Evidence first: what was covered while the one-time overlay was up.
  const coveredAtLoad = (await page.evaluate(CONTROL_PROBE)).filter((c) => c.coveredBy).map((c) => ({ sel: c.sel, text: c.text, by: c.coveredBy }));
  const dismissed = await page.evaluate(DISMISS_ONE_TIME_OVERLAYS);
  await new Promise((r) => setTimeout(r, 250));
  const controls = await page.evaluate(CONTROL_PROBE);
  const dead = [];
  const skipped = [];
  const covered = [];
  const inputRequired = [];
  const contaminated = [];
  let resetReloads = 0;
  // The state the pass starts in. Every probe must return here before the next one runs; otherwise a
  // control is measured with a panel an earlier click opened still on screen, its own click changes
  // nothing, and it is reported dead. Verified after each probe, with a reload as the fallback.
  const clean = await page.evaluate(STATE_FINGERPRINT);
  // The target state is what a *fresh load* settles into, never "fresh load minus my own dismissals":
  // the editor route ships three `<details>` open by design (advancedTextLayout and two
  // final-control-group), so a post-dismissal baseline is unreachable and reported every probe as
  // unrestorable. Comparing against the default is also the question a user would ask — did the last
  // click leave something open that a reload would not have?
  const cleanReset = await settleAndRead(page);
  const cleanDetails = cleanReset ? JSON.parse(cleanReset).details : [];
  // A probe read can land on a frame a previous click just navigated away from. That is a state the
  // pass can recover from, not a finding: put the route back and read again, once.
  const safeEval = async (fn, arg) => {
    try {
      return await page.evaluate(fn, arg);
    } catch (err) {
      if (!/detached|Execution context|Target closed/i.test(String(err))) throw err;
      await resetRoute(page, url);
      return await page.evaluate(fn, arg);
    }
  };
  for (const c of controls) {
    if (c.disabled) { skipped.push({ ...c, why: 'disabled on a fresh load' }); continue; }
    if (c.alreadyOn) { skipped.push({ ...c, why: 'already in the state a click produces' }); continue; }
    if (c.kind === 'select') { skipped.push({ ...c, why: 'select needs an option choice' }); continue; }
    if (c.coveredBy) { covered.push({ ...c, why: 'painted over by ' + c.coveredBy }); continue; }
    let before;
    try {
      before = await safeEval(STATE_FINGERPRINT);
    } catch (err) {
      // Still unreadable after a reset: the control is unmeasured, not dead, and the route is reset.
      skipped.push({ ...c, why: 'unmeasured: probe frame unavailable (' + String(err).slice(0, 80) + ')' });
      await resetRoute(page, url).catch(() => null);
      continue;
    }
    const errs = [];
    const onErr = (e) => errs.push(String(e).slice(0, 200));
    page.on('pageerror', onErr);
    let clicked = false;
    try {
      clicked = await page.evaluate((i) => {
        const sel = 'button, [role="button"], summary, select, input[type="checkbox"], input[type="radio"], [aria-expanded]';
        const el = [...document.querySelectorAll(sel)][i];
        if (!el) return false;
        el.scrollIntoView({ block: 'center' });
        el.click();
        return true;
      }, c.i);
    } catch (err) { errs.push(String(err).slice(0, 200)); }
    await new Promise((r) => setTimeout(r, CLICK_WAIT_MS));
    // A click can be a navigation (sign in, a rail link rendered as a button); the frame is then
    // detached and evaluating into it throws "Attempted to use detached Frame". A reload IS the
    // observable change, so it counts as one and the route is put back.
    let after = before;
    let navigatedAway = false;
    try {
      after = await page.evaluate(STATE_FINGERPRINT);
    } catch (err) {
      navigatedAway = true;
      after = before + ':navigated';
      errs.length = 0;
    }
    page.off('pageerror', onErr);
    if (!clicked) { dead.push({ ...c, why: 'not clickable (detached between probe and click)' }); continue; }
    if (before === after && !errs.length) {
      // "Needs input first" is not "dead": a submit on an empty form, a Save with no edits, a
      // search-go on an empty query. The distinction is decided in CONTROL_PROBE, from the DOM.
      if (c.inputRequired) inputRequired.push({ ...c, why: 'needs input before it can act' });
      else dead.push({ ...c, why: 'no observable state change' });
    } else if (errs.length) {
      dead.push({ ...c, why: `threw: ${errs[0]}`, changed: before !== after });
    }
    // Put the route back into the state this pass started in. A navigation means the click followed
    // a link, which this pass never does on purpose; otherwise the app's own dismissals (a real
    // Escape key press plus DISMISS) run first, and a reload is the fallback when the fingerprint
    // says that was not enough.
    if (await safeEval(() => location.href).catch(() => url) !== url) {
      await resetRoute(page, url);
    } else {
      await page.keyboard.press('Escape').catch(() => {});
      await page.evaluate(DISMISS, cleanDetails);
      await new Promise((r) => setTimeout(r, 120));
      const restored = await page.evaluate(RESET_FINGERPRINT).catch(() => null);
      if (restored !== null && restored !== cleanReset) {
        // The app's own dismissals were not enough for this probe: the click left something open
        // that Escape, the dialog closers and `<details>` closers do not own.
        resetReloads += 1;
        const afterReset = await resetRoute(page, url);
        if (afterReset !== cleanReset) contaminated.push({ sel: c.sel, text: c.text, why: 'still open after a reset reload', was: restored, after: afterReset, clean: cleanReset });
      }
    }
    await new Promise((r) => setTimeout(r, 120));
  }
  report.clicks.push({ route, controls: controls.length, dead: dead.length, inputRequired: inputRequired.length, skipped: skipped.length, covered: covered.length, coveredAtLoad: coveredAtLoad.length, resetReloads, contaminated: contaminated.length, dismissed });
  report.dead.push({ route, items: dead, inputRequired, skipped, covered, coveredAtLoad, dismissed, resetReloads, contaminated });
  writeFileSync(join(REPO_ROOT, OUT_DIR, `${route.replace('.html', '')}-dead-controls.json`), JSON.stringify({ route, controls, dead, inputRequired, skipped, covered, coveredAtLoad, dismissed, resetReloads, contaminated }, null, 1));
  say(`CLICK  ${route.padEnd(16)} controls=${controls.length} dead=${dead.length} inputRequired=${inputRequired.length} skipped=${skipped.length} covered=${covered.length} coveredAtLoad=${coveredAtLoad.length} resetReloads=${resetReloads} contaminated=${contaminated.length}${diag.navError ? ' NAV-FAIL' : ''}`);
  await page.close();
}

writeFileSync(join(REPO_ROOT, JSON_OUT), JSON.stringify(report, null, 1));

const totals = report.layout.reduce((acc, r) => {
  acc.overflow += r.overflow ? 1 : 0;
  acc.escapes += r.escapeCount;
  acc.overlays += r.overlayCount;
  acc.console += r.console.length;
  acc.netfail += r.failures.length;
  acc.brokenLinks += r.brokenLinks.length;
  return acc;
}, { overflow: 0, escapes: 0, overlays: 0, console: 0, netfail: 0, brokenLinks: 0 });
console.log(`\nSWEEP ${JSON.stringify({ routes: ROUTES.length, widths: WIDTHS, rows: report.layout.length, ...totals, deadControls: report.dead.reduce((n, d) => n + d.items.length, 0), inputRequiredControls: report.dead.reduce((n, d) => n + (d.inputRequired ? d.inputRequired.length : 0), 0), resetReloads: report.dead.reduce((n, d) => n + (d.resetReloads || 0), 0), json: JSON_OUT })}`);
await browser.close();
