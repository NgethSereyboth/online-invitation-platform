/**
 * lighthouserc.js — Lighthouse CI configuration for the 16 shipped routes.
 *
 * This is the ONLY Lighthouse CI config in the repo. The former repo-root
 * `.lighthouserc.json` was removed in the same change: two configs where only one
 * is picked up by `npx lhci autorun` is a trap, and the silent one was the one
 * that looked authoritative. Run it explicitly:
 *
 *     npx lhci autorun --config=tools/lighthouserc.js
 *     make perf          # same thing, with the server and the assertions
 *
 * Two delivery details that are load-bearing:
 *
 * 1. `chromePath` is RESOLVED, not hard-coded. The previous config named
 *    /usr/bin/google-chrome, which reproduced only on Linux with distro Chrome.
 *    CHROME_PATH wins if set; otherwise the first existing known location is
 *    used; if none is found the key is omitted and Lighthouse CI does its own
 *    discovery (which finds a puppeteer-downloaded Chrome).
 *
 * 2. Both `budgetsFile` and `upload.outputDir` are resolved by Lighthouse CI
 *    against process.cwd(), not against this file. So this config MUST be run
 *    from the repo root — which `make perf` and `make reproduce` both do. (lhci
 *    internals: @lhci/cli/src/assert/assert.js `path.resolve(process.cwd(), ...)`.)
 *
 * `assert` carries a budgetsFile and NOT an `assertions` set: Lighthouse CI
 * rejects using both at once ("Cannot use both budgets AND assertions"), so the
 * per-page budgets in docs/perf/lighthouse-budgets.json are the single assert
 * strategy. The RequestCount assertions that used to live in that file were
 * structurally unsatisfiable (39 <= 3 scripts is impossible while the page
 * deliberately defers 23 feature modules) and were replaced with byte budgets —
 * see docs/perf/lighthouse-budgets.json and §7 of
 * docs/reviews/reproducibility-and-performance-report.md.
 *
 * Server requirement: the numbers only reproduce against tools/serve-gzip.py
 * (gzip on the wire, like every real static host). Against an uncompressed
 * server index.html reads 54 instead of 73 and every byte budget looks violated.
 */
const fs = require('fs');

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
];

const chromePath = CHROME_CANDIDATES.find((p) => p && fs.existsSync(p));

/** @type {import('@lhci/cli').LighthouseRc} */
module.exports = {
  ci: {
    collect: {
      url: [
        'index.html',
        'dashboard.html',
        'public.html',
        'admin.html',
        'account.html',
        'billing.html',
        'verify.html',
        'reset.html',
        'privacy.html',
        'guests.html',
        'responses.html',
        'analytics.html',
        'materials.html',
        'checkin.html',
        'templates.html',
        'designer.html',
      ].map((p) => `http://127.0.0.1:${process.env.PORT || 8124}/${p}`),
      numberOfRuns: 1,
      settings: {
        preset: 'desktop',
        ...(chromePath ? { chromePath } : {}),
        chromeFlags: '--headless=new --no-sandbox --disable-dev-shm-usage --disable-gpu',
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
      },
    },

    // Either budgetsFile or assertions — never both (Lighthouse CI configuration).
    assert: {
      budgetsFile: 'docs/perf/lighthouse-budgets.json',
    },

    upload: {
      target: 'filesystem',
      // Inside .lighthouseci/, which .gitignore already excludes: generated
      // reports are regenerable output, not source.
      outputDir: './.lighthouseci/reports',
    },
  },
};
