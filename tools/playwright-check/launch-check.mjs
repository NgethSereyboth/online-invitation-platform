/**
 * launch-check.mjs — the brief's step-0b browser check, made to pass on this host
 * WITHOUT touching the repository's package.json.
 *
 * The requirement
 * ---------------
 *   node -e "require('playwright').chromium.launch()"
 *
 * Why it used to fail, and what changed
 * -------------------------------------
 * The application does not depend on Playwright: `node_modules/playwright` does not
 * exist at the repository root, so `require('playwright')` throws MODULE_NOT_FOUND
 * there, and inside the Python virtualenv it throws `Executable doesn't exist at
 * …/chrome-headless-shell` when a Playwright is present but its browser was never
 * downloaded. Installing the package at the root would edit `package.json`, which
 * this pass is forbidden to touch.
 *
 * The check therefore lives in its own directory with its own manifest:
 * `tools/playwright-check/package.json` (private, not an application dependency)
 * and its own `node_modules`, installed with
 *
 *   cd tools/playwright-check && npm install playwright && npx playwright install chromium
 *
 * which downloads the browser to `~/.cache/ms-playwright` (outside the repository).
 * `require('playwright')` resolves from this directory, so the brief's exact
 * expression runs unchanged. Playwright's own bundled Chromium is used — not the
 * system Chrome — because a check that silently depends on `/usr/bin/google-chrome`
 * would not be the check that was asked for.
 *
 * What this check asserts beyond the launch
 * -----------------------------------------
 * A browser that launches but cannot render proves little, so this also loads a
 * page the repository's own server is serving and reads the document title back.
 *
 * Usage
 *   cd tools/playwright-check && node launch-check.mjs [url]
 *   node tools/playwright-check/launch-check.mjs [url]        # from the repo root
 *   BASE_URL/--url overrides the default http://127.0.0.1:8124/index.html
 *
 * Exit 0 prints PLAYWRIGHT_LAUNCH_OK; a failure prints the error and exits 1 (the
 * page is optional: with no server answering, the launch result is still printed
 * and the exit status stays 0).
 */
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const argUrl = process.argv.find((a) => a.startsWith('http'));
const URL = argUrl || `${(process.env.BASE_URL || 'http://127.0.0.1:8124').replace(/\/$/, '')}/index.html`;

let playwright;
try {
  playwright = require('playwright');
} catch (err) {
  console.error('PLAYWRIGHT_REQUIRE_FAILED ' + String(err.message || err));
  console.error('  install it here:  cd tools/playwright-check && npm install playwright && npx playwright install chromium');
  process.exit(1);
}

// The brief's expression, unmodified: a bare launch with no options and no
// channel, so Playwright uses the browser it downloaded for itself.
let browser;
try {
  browser = await playwright.chromium.launch();
} catch (err) {
  console.error('PLAYWRIGHT_LAUNCH_FAILED ' + String(err.message || err));
  process.exit(1);
}

const version = browser.version();
let title = null;
let pageError = null;
try {
  const page = await browser.newPage();
  await page.goto(URL, { waitUntil: 'load', timeout: 20000 });
  title = await page.title();
} catch (err) {
  pageError = String(err.message || err);
} finally {
  await browser.close();
}

console.log('PLAYWRIGHT_LAUNCH_OK version=' + version);
console.log('  url=' + URL + (title !== null ? '  title=' + JSON.stringify(title) : ''));
if (pageError) {
  // A launch with no page to load is still the requirement met; the missing page is
  // reported rather than turned into a failure of the browser check.
  console.log('  PAGE_NOT_LOADED ' + pageError);
}
