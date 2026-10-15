// Puppeteer-based bilingual i18n audit script.
// Downloads chrome-headless-shell into /dev/shm, starts server, runs audit.
const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = path.resolve(__dirname, '..');
const PY_DIR = path.join(ROOT, 'src', 'python');
const DATA_DIR = path.join(ROOT, 'data');

process.env.PUPPETEER_CACHE_DIR = '/dev/shm/puppeteer-cache';
process.env.EINVITE_DATA_DIR = DATA_DIR;
process.env.EINVITE_ALLOW_NO_SCANNER = '1';

async function waitForServer(url, timeout = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const r = await fetch(url);
      if (r.ok) return true;
    } catch {}
    await new Promise(r => setTimeout(r, 500));
  }
  return false;
}

const wait = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const puppeteer = require('puppeteer');
  const results = { started: false, chrome: '', feature_flags: {}, pages: {}, screenshots: {} };

  // Find chrome-headless-shell in /dev/shm or the workspace cache
  let execPath = process.env.PUPPETEER_CHROME_PATH || '';
  if (!execPath) {
    const { execSync } = require('child_process');
    const candidates = [
      '/dev/shm/puppeteer-cache',
      path.join(ROOT, '.cache', 'puppeteer'),
    ];
    for (const dir of candidates) {
      try {
        const found = execSync(`find "${dir}" -name "chrome-headless-shell" -type f 2>/dev/null | head -1`).toString().trim();
        if (found && fs.existsSync(found)) { execPath = found; break; }
      } catch {}
    }
  }
  results.chrome = execPath;
  console.log('[AUDIT] Chrome executable:', execPath);
  if (!execPath || !fs.existsSync(execPath)) { console.error('[AUDIT] No chrome found'); process.exit(1); }

  // Start server
  console.log('[AUDIT] Starting server...');
  const { spawn } = require('child_process');
  const serverProc = spawn('python3', ['server.py', '--host', '127.0.0.1', '--port', '3180'], {
    cwd: PY_DIR,
    env: { ...process.env, PYTHONPATH: ROOT + path.delimiter + PY_DIR, EINVITE_DATA_DIR: DATA_DIR, EINVITE_ALLOW_NO_SCANNER: '1' },
    stdio: 'pipe',
  });
  serverProc.stderr.on('data', d => console.log('[SERVER]', d.toString().slice(0, 200)));

  const serverReady = await waitForServer('http://127.0.0.1:3180/admin.html');
  if (!serverReady) {
    console.error('[AUDIT] Server did not start in time');
    serverProc.kill();
    process.exit(1);
  }
  results.started = true;
  console.log('[AUDIT] Server is ready');

  const base = 'http://127.0.0.1:3180';
  const browser = await puppeteer.launch({
    executablePath: execPath,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security',
           '--disable-features=site-per-process', '--force-device-scale-factor=1',
           '--window-size=1280,800'],
    headless: 'new',
  });

  const auditPage = async (name, urlPath, extraClicks = []) => {
    const page = await browser.newPage();
    const audit = { name, url: urlPath, en: {}, km: {}, switches: {} };
    try {
      await page.goto(base + urlPath, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await wait(1500);

      // Clear language preference and reload to start in EN
      await page.evaluate(() => localStorage.removeItem('einvite-lang'));
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
      await wait(1500);

      audit.en = await page.evaluate(() => {
        const root = document.documentElement;
        const enSpans = document.querySelectorAll('.i18n-en');
        const kmSpans = document.querySelectorAll('.i18n-km');
        const enTexts = Array.from(enSpans).map(s => s.textContent.trim());
        const kmTexts = Array.from(kmSpans).map(s => s.textContent.trim());
        let diffCount = 0;
        for (let i = 0; i < enSpans.length; i++) {
          if (kmSpans[i] && enSpans[i].textContent.trim() !== kmSpans[i].textContent.trim()) diffCount++;
        }
        return {
          html_lang: root.lang || '',
          i18n_en: enSpans.length,
          i18n_km: kmSpans.length,
          identical_pairs: enSpans.length - diffCount,
          different_pairs: diffCount,
          en_visible: Array.from(enSpans).filter(e => { try { return getComputedStyle(e).display !== 'none' } catch { return false } }).length,
          km_visible: Array.from(kmSpans).filter(e => { try { return getComputedStyle(e).display !== 'none' } catch { return false } }).length,
          i18n_loaded: typeof window.EInviteI18n !== 'undefined',
          i18n_version: window.EInviteI18n?.VERSION || 'undefined',
          has_switch: !!document.querySelector('#lang-en') || !!document.querySelector('#lang-km'),
        };
      });
      console.log(`[AUDIT] ${name} EN: spans=${audit.en.i18n_en}/${audit.en.i18n_km} diff=${audit.en.different_pairs} en_visible=${audit.en.en_visible} km_visible=${audit.en.km_visible} loaded=${audit.en.i18n_loaded} switch=${audit.en.has_switch} lang=${audit.en.html_lang}`);

      // Try switching to Khmer
      if (audit.en.has_switch) {
        const kmBtn = await page.$('#lang-km');
        if (kmBtn) {
          await page.evaluate((btn) => { btn.scrollIntoView({block:'center'}); btn.click(); }, kmBtn);
          await wait(500);
          const switched = await page.evaluate(() => document.documentElement.lang);
          audit.switches.km = { success: switched === 'km', lang_after: switched };
          console.log(`[AUDIT] ${name} switch KM: lang=${switched}`);
        }
      }

      audit.km = await page.evaluate(() => {
        const enSpans = document.querySelectorAll('.i18n-en');
        const kmSpans = document.querySelectorAll('.i18n-km');
        return {
          html_lang: document.documentElement.lang || '',
          en_visible: Array.from(enSpans).filter(e => { try { return getComputedStyle(e).display !== 'none' } catch { return false } }).length,
          km_visible: Array.from(kmSpans).filter(e => { try { return getComputedStyle(e).display !== 'none' } catch { return false } }).length,
        };
      });
      console.log(`[AUDIT] ${name} KM: en_visible=${audit.km.en_visible} km_visible=${audit.km.km_visible} lang=${audit.km.html_lang}`);

      // Extra clicks
      for (const [label, selector] of extraClicks) {
        try {
          const el = await page.$(selector);
          if (el) {
            await page.evaluate((s) => { const b = document.querySelector(s); if (b) { b.scrollIntoView({block:'center'}); b.click(); } }, selector);
            await wait(800);
            audit.switches[label] = { success: true };
            console.log(`[AUDIT] ${name} click '${label}': OK`);
          } else {
            audit.switches[label] = { success: false, error: 'element not found' };
            console.log(`[AUDIT] ${name} click '${label}': NOT FOUND`);
          }
        } catch (e) {
          audit.switches[label] = { success: false, error: e.message };
          console.log(`[AUDIT] ${name} click '${label}': ERROR ${e.message}`);
        }
      }

      // Screenshot
      const ssDir = path.join(ROOT, 'screenshots');
      fs.mkdirSync(ssDir, { recursive: true });
      const pngPath = path.join(ssDir, `${name}.png`);
      await page.screenshot({ path: pngPath, fullPage: true, type: 'png' });
      audit.screenshot = { path: pngPath, size: fs.statSync(pngPath).size };
      console.log(`[AUDIT] ${name} screenshot: ${fs.statSync(pngPath).size} bytes`);

    } catch (e) {
      audit.error = e.message;
      console.error(`[AUDIT] ${name} ERROR: ${e.message}`);
    } finally {
      await page.close();
    }
    return audit;
  };

  // === Feature flags tab test ===
  console.log('[AUDIT] === Feature flags tab test ===');
  const ffPage = await browser.newPage();
  const ffResult = { tabs: [], clicks: {} };
  try {
    await ffPage.goto(base + '/admin.html', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await wait(2000);

    // List admin tabs
    ffResult.tabs = await ffPage.evaluate(() => {
      const tabs = document.querySelectorAll('[data-admin-tab]');
      return Array.from(tabs).map(t => ({ text: t.textContent.trim().slice(0, 40), exists: true }));
    });
    console.log('[AUDIT] Admin tabs:', ffResult.tabs.map(t => t.text));

    // Click feature-flags tab
    const ffBtn = await ffPage.$('[data-admin-tab="feature-flags"]');
    if (ffBtn) {
      await ffPage.evaluate((btn) => { btn.scrollIntoView({block:'center'}); btn.click(); }, ffBtn);
      await wait(1500);
      const visiblePanel = await ffPage.evaluate(() => {
        const panels = document.querySelectorAll('.admin-panel');
        for (const p of panels) {
          if (!p.hidden && p.id) return { id: p.id, visible_text: p.textContent.trim().slice(0, 100) };
        }
        return { visible_panel: 'none found' };
      });
      ffResult.clicks['feature-flags-tab'] = { success: true, panel: visiblePanel };
      console.log('[AUDIT] Feature flags tab clicked -> panel:', visiblePanel);

      // --- i18n toggle computed-style check on the feature-flags tab button ---
      // Per Part D: verify that .i18n-km is display:none when lang=en, and
      // .i18n-en is display:none when lang=km, inside [data-admin-tab="feature-flags"].
      ffResult.i18n = {};
      const ffTabEl = await ffPage.$('[data-admin-tab="feature-flags"]');
      if (ffTabEl) {
        const enState = await ffPage.evaluate(() => {
          const tab = document.querySelector('[data-admin-tab="feature-flags"]');
          const en = tab.querySelector('.i18n-en');
          const km = tab.querySelector('.i18n-km');
          return {
            lang: document.documentElement.lang,
            en_display: en ? getComputedStyle(en).display : null,
            km_display: km ? getComputedStyle(km).display : null,
            en_visible: en ? getComputedStyle(en).display !== 'none' : false,
            km_visible: km ? getComputedStyle(km).display !== 'none' : false,
          };
        });
        ffResult.i18n.en = enState;
        console.log(`[AUDIT] FF i18n EN: lang=${enState.lang} .i18n-en=${enState.en_display} .i18n-km=${enState.km_display}`);

        const kmBtn = await ffPage.$('#lang-km');
        if (kmBtn) {
          await ffPage.evaluate((btn) => { btn.scrollIntoView({block:'center'}); btn.click(); }, kmBtn);
          await wait(1000);
          const kmState = await ffPage.evaluate(() => {
            const tab = document.querySelector('[data-admin-tab="feature-flags"]');
            const en = tab.querySelector('.i18n-en');
            const km = tab.querySelector('.i18n-km');
            return {
              lang: document.documentElement.lang,
              en_display: en ? getComputedStyle(en).display : null,
              km_display: km ? getComputedStyle(km).display : null,
              en_visible: en ? getComputedStyle(en).display !== 'none' : false,
              km_visible: km ? getComputedStyle(km).display !== 'none' : false,
            };
          });
          ffResult.i18n.km = kmState;
          console.log(`[AUDIT] FF i18n KM: lang=${kmState.lang} .i18n-en=${kmState.en_display} .i18n-km=${kmState.km_display}`);
          ffResult.i18n.en_pass = enState.km_visible === false;
          ffResult.i18n.km_pass = kmState.en_visible === false;
        } else {
          ffResult.i18n.en_pass = false;
          ffResult.i18n.km_pass = false;
          console.log('[AUDIT] FF i18n: #lang-km button not found');
        }
      }
    } else {
      ffResult.clicks['feature-flags-tab'] = { success: false, error: 'button not found' };
      console.log('[AUDIT] Feature flags button not found');
    }

    // Check for the 6 feature flag sub-tabs
    const ffSubTabs = await ffPage.evaluate(() => {
      const container = document.querySelector('#featureFlagsPanel') || document.querySelector('.admin-panel:not([hidden])');
      if (!container) return [];
      const btns = container.querySelectorAll('button');
      return Array.from(btns).map(b => b.textContent.trim().slice(0, 40));
    });
    console.log('[AUDIT] Feature flag sub-tabs:', ffSubTabs);

    ffResult.subtabs = ffSubTabs;
    // Try clicking each sub-tab
    const labels = ['Templates', 'AI providers', 'System', 'Manage accounts', 'Shared templates', 'Public invitations'];
    for (const label of labels) {
      try {
        await ffPage.evaluate((lbl) => {
          const btns = document.querySelectorAll('button');
          for (const b of btns) {
            if (b.textContent.trim().includes(lbl)) { b.scrollIntoView({block:'center'}); b.click(); return true; }
          }
          return false;
        }, label);
        await wait(500);
        const newActive = await ffPage.evaluate(() => {
          const active = document.querySelector('.active');
          return active ? active.textContent.trim().slice(0,40) : 'none';
        });
        ffResult.clicks[label] = { success: true, active_after: newActive };
        console.log(`[AUDIT] FF sub-tab '${label}': clicked, active=${newActive}`);
      } catch (e) {
        ffResult.clicks[label] = { success: false, error: e.message };
        console.log(`[AUDIT] FF sub-tab '${label}': ERROR ${e.message}`);
      }
    }

    // Screenshot admin
    await ffPage.screenshot({ path: path.join(ROOT, 'screenshots', 'admin.png'), fullPage: true, type: 'png' });

  } catch (e) {
    ffResult.error = e.message;
    console.error('[AUDIT] Feature flags test ERROR:', e.message);
  } finally {
    await ffPage.close();
  }
  results.feature_flags = ffResult;

  // === 6 page screenshots + audit ===
  const pages = [
    ['checkin', '/checkin.html'],
    ['privacy', '/privacy.html'],
    ['public', '/public.html'],
    ['verify', '/verify.html'],
    ['index', '/index.html'],
    ['dashboard', '/dashboard.html'],
  ];

  for (const [name, urlPath] of pages) {
    const audit = await auditPage(name, urlPath);
    results.pages[audit.name] = audit;
  }

  await browser.close();
  serverProc.kill();

  // Save results
  const resultPath = path.join(ROOT, '_i18n_all_result.json');
  fs.writeFileSync(resultPath, JSON.stringify(results, null, 2, null));
  console.log('[AUDIT] Results saved to', resultPath);
  console.log('[AUDIT] === SUMMARY ===');
  console.log('[AUDIT] Feature flags tabs:', ffResult.tabs.length);
  console.log('[AUDIT] Feature flags clicks:', Object.keys(ffResult.clicks));
  console.log('[AUDIT] Feature flags i18n: EN_PASS=' + (ffResult.i18n?.en_pass ?? 'n/a') + ' KM_PASS=' + (ffResult.i18n?.km_pass ?? 'n/a'));
  for (const [name, audit] of Object.entries(results.pages)) {
    console.log(`[AUDIT] ${name}: en_spans=${audit.en.i18n_en} km_spans=${audit.en.i18n_km} diff=${audit.en.different_pairs} switch=${audit.switches.km?.success ?? 'n/a'}`);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
