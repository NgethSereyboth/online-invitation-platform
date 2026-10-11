/**
 * lhci-single.js — the repo Lighthouse config, narrowed to one page.
 *
 * Why this exists
 * ---------------
 * tools/lighthouserc.js measures all 16 routes, which is right for the release
 * gate and wrong for a single-page before/after: 16 runs take minutes, and a
 * before/after pair is only meaningful if BOTH halves are produced by the same
 * config, the same server and the same Chrome. This wraps that config instead of
 * duplicating it, so the preset, chromePath resolution, flags and budgets file
 * cannot drift between the two entry points.
 *
 * Excluding the assertions is deliberate for a measurement run: `budgetsFile` is
 * a release gate, and a gate that fails changes nothing about the recorded
 * numbers while adding noise to them.
 *
 * Usage
 *   npx lhci collect --config=tools/lhci-single.js --collect.url=http://127.0.0.1:8124/index.html
 *   # or just:  PAGE=index.html npx lhci collect --config=tools/lhci-single.js
 *
 * Reads PAGE (default index.html) and PORT (default 8124) from the environment.
 * Products: the usual `.lighthouseci/lhr-*.json`, one per run.
 */
const base = require('./lighthouserc.js');

const page = process.env.PAGE || 'index.html';
// Lighthouse CI exports PORT=0 while it looks for a free port, so `PORT || 8124`
// resolves to the literal string "0" and every URL becomes
// http://127.0.0.1:0/... — which surfaces as CHROME_INTERSTITIAL_ERROR rather
// than as an obviously wrong port. Only a real, non-zero port is honoured.
const envPort = Number(process.env.PORT);
const port = Number.isInteger(envPort) && envPort > 0 ? envPort : 8124;

module.exports = {
  ci: {
    ...base.ci,
    collect: {
      ...base.ci.collect,
      url: [`http://127.0.0.1:${port}/${page}`],
    },
    assert: undefined,
  },
};
