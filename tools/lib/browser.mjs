/**
 * browser.mjs — Chrome discovery and launch for the measurement tools.
 *
 * The /tmp harnesses hard-coded two different executables by absolute path:
 * `/usr/bin/google-chrome` for the hover audits and
 * `.../.cache/puppeteer/chrome-headless-shell/linux-154.0.8037.57/
 *  chrome-headless-shell-linux64/chrome-headless-shell` for the determinism
 * captures. Both are replaced by resolution, with the previous choices kept as
 * the preferred order so the numbers stay comparable:
 *
 *   kind 'shell'  the chrome-headless-shell build — used for determinism
 *                 captures, because "render the page and report the height"
 *                 should not depend on window chrome.
 *   kind 'full'   the full browser — used for hover audits and CDP traces,
 *                 which need CSS.getMatchedStylesForNode / CSS.enableSelectorStats.
 *
 * Resolution order (first hit wins):
 *   CHROME_PATH environment variable
 *   the repo's own .cache/puppeteer download for the requested kind
 *   the system google-chrome / chromium / chromium-browser
 *   the other puppeteer kind as a last resort
 */
import { createRequire } from 'node:module';
import { existsSync, readdirSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

import { REPO_ROOT } from './repo.mjs';

const require = createRequire(import.meta.url);
// Resolved through the repo's node_modules (declared in ./package.json), never
// by absolute path, so a fresh clone works after `npm install`.
export const puppeteer = require('puppeteer-core');

const SYSTEM_CANDIDATES = [
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/opt/google/chrome/chrome',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
];

function findExecutableUnder(dir, wanted) {
  if (!existsSync(dir)) return null;
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    let entries;
    try {
      entries = readdirSync(cur);
    } catch {
      continue;
    }
    for (const entry of entries) {
      const full = resolve(cur, entry);
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) {
        stack.push(full);
      } else if (entry === wanted && st.isFile()) {
        return full;
      }
    }
  }
  return null;
}

function puppeteerCachePath(kind) {
  const base = resolve(REPO_ROOT, '.cache', 'puppeteer');
  for (const sub of kind === 'shell' ? ['chrome-headless-shell', 'chrome'] : ['chrome', 'chrome-headless-shell']) {
    const hit = findExecutableUnder(resolve(base, sub), kind === 'shell' && sub === 'chrome-headless-shell' ? 'chrome-headless-shell' : 'chrome');
    if (hit) return hit;
  }
  return null;
}

export function resolveChrome(kind = 'full') {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const cached = puppeteerCachePath(kind);
  if (kind === 'shell' && cached) return cached;
  for (const candidate of SYSTEM_CANDIDATES) if (existsSync(candidate)) return candidate;
  if (cached) return cached;
  const other = puppeteerCachePath(kind === 'shell' ? 'full' : 'shell');
  if (other) return other;
  return null;
}

export function describeChrome(kind = 'full') {
  const path = resolveChrome(kind);
  return path ? `${path} (kind=${kind})` : `NOT FOUND (kind=${kind}) — set CHROME_PATH`;
}

/**
 * Launch a browser with the repo's standing argument set. `headless: true` is
 * deliberate and matches every number already recorded in the reports.
 */
export async function launch({ kind = 'full', viewport = { width: 1366, height: 900 }, extraArgs = [] } = {}) {
  const executablePath = resolveChrome(kind);
  if (!executablePath) {
    console.error('tools: no Chrome executable found.');
    console.error('tools: set CHROME_PATH, or run `npx puppeteer browsers install chrome` in the repo root.');
    process.exit(2);
  }
  const browser = await puppeteer.launch({
    executablePath,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars', ...extraArgs],
  });
  if (viewport) {
    browser.__viewport = viewport;
  }
  return browser;
}

/** A page with the shared viewport applied. */
export async function newPage(browser, viewport = browser.__viewport || { width: 1366, height: 900 }) {
  const page = await browser.newPage();
  if (viewport) await page.setViewport(viewport);
  return page;
}

/**
 * Freeze transitions and animations. Injected at test time only: it changes no
 * final computed value, only how quickly one is reached, so a forced-hover or
 * shift read is the settled value rather than a mid-interpolation frame.
 */
export const FREEZE_CSS =
  '*,*::before,*::after{transition-duration:0s !important;transition-delay:0s !important;' +
  'animation-duration:0s !important;animation-delay:0s !important;scroll-behavior:auto !important}';

export async function freezeMotion(page) {
  await page.addStyleTag({ content: FREEZE_CSS });
}

/**
 * Make the page behave as though it were viewed on a hover-capable, fine-pointer
 * device, so that `@media(hover:hover)` rules take part in the measurement.
 *
 * Why this is necessary, measured: headless Chrome reports
 * `matchMedia('(hover: hover)').matches === false` (and `(pointer: fine)` false),
 * and `Emulation.setEmulatedMedia` with `features:[{name:'hover',value:'hover'}]`
 * does NOT override it. So every `@media(hover:hover)` block is *inactive*
 * during a forced-`:hover` measurement, and a declaration outside such a block
 * can look inert only because its competitor inside the block is switched off on
 * this machine while it is live on a real one. Those rules are where most hover
 * styling lives (`@media(hover:hover){button:not(:disabled):hover{transform:…}}`).
 *
 * The fix rewrites the media condition instead of the environment: each media
 * query clause that asks for hover/fine-pointer is replaced with an
 * always-true clause, in the page's CSSOM, at test time only. Nothing is
 * written to disk, and the tool declares the rewrite in its report.
 *
 * `(hover: none)` / `(pointer: coarse)` blocks are deliberately left alone: a
 * touch-first block is not what is being simulated here.
 */
/**
 * Re-read the media conditions `emulateHoverCapable` rewrote, in a later task so
 * `matches` is no longer stale, and report how many are still inactive. Callers
 * fail their run when this is non-empty: a silent rewrite failure means every
 * hover verdict was taken on a touch-first page.
 */
export async function verifyHoverMediaRewrite(page, expectedCount) {
  await new Promise((r) => setTimeout(r, 100));
  const rewritten = await page.evaluate(() => {
    const out = [];
    const walk = (rules) => {
      for (const rule of rules) {
        if (rule.cssRules && rule.selectorText === undefined) {
          if (rule.media && /min-width\s*:\s*0px/.test(rule.media.mediaText)) {
            out.push({ text: rule.media.mediaText, matches: window.matchMedia(rule.media.mediaText).matches });
          }
          walk(rule.cssRules);
        }
      }
    };
    for (const sheet of document.styleSheets) {
      try { walk(sheet.cssRules); } catch { /* opaque sheet */ }
    }
    return out;
  });
  return {
    rewritten,
    stillInactive: rewritten.filter((r) => !r.matches),
    markerCountMatches: expectedCount === undefined || rewritten.length === expectedCount,
  };
}

export async function emulateHoverCapable(page) {
  return page.evaluate(() => {
    const REWRITE = [
      [/\(\s*(?:any-)?hover\s*:\s*hover\s*\)/gi, '(min-width:0px)'],
      [/\(\s*(?:any-)?pointer\s*:\s*fine\s*\)/gi, '(min-width:0px)'],
    ];
    const mentionsHoverClause = (text) => REWRITE.some(([re]) => new RegExp(re.source, 'i').test(text));
    const rewritten = [];
    let clausesFound = 0;
    const walk = (rules) => {
      for (const rule of rules) {
        if (rule.cssRules && rule.selectorText === undefined) {
          if (rule.media) {
            const text = rule.media.mediaText;
            // A CSSMediaRule's `.media` is a MediaList, which has mediaText and no
            // `matches`; evaluating the condition means asking matchMedia.
            if (mentionsHoverClause(text)) clausesFound++;
            if (mentionsHoverClause(text) && !window.matchMedia(text).matches) {
              let next = text;
              for (const [re, to] of REWRITE) next = next.replace(re, to);
              rule.media.mediaText = next;
              // The new condition is measured by the caller in a later pass,
              // keyed on the `(min-width:0px)` rewrite marker.
              rewritten.push({ from: text, to: next });
            }
          }
          walk(rule.cssRules);
        }
      }
    };
    for (const sheet of document.styleSheets) {
      try { walk(sheet.cssRules); } catch { /* opaque sheet */ }
    }
    return {
      mediaHoverCapableBefore: window.matchMedia('(hover: hover)').matches,
      pointerFineBefore: window.matchMedia('(pointer: fine)').matches,
      // `clausesFound` counts rules whose condition asks for hover/fine-pointer at
      // all; 0 is a legitimate page, so a no-op rewrite is not a failure.
      clausesFound,
      rewrittenCount: rewritten.length,
      rewritten: rewritten.slice(0, 20),
    };
  });
}
