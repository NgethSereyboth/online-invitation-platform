/**
 * repo.mjs — path and page constants shared by every measurement tool in tools/.
 *
 * Why this exists
 * ---------------
 * The first pass built its measurement harnesses under /tmp with absolute
 * paths to this machine baked in (`import puppeteer from
 * '/media/.../node_modules/puppeteer-core/...'`, `os.chdir('/media/.../src/python')`).
 * Every number in the resulting report was therefore reproducible only while
 * that session's /tmp existed. Every path a tool needs is derived here instead,
 * from the tool's own location, so a fresh clone on another machine resolves the
 * same directories.
 *
 * Environment overrides (all optional):
 *   REPO_ROOT      repo root                     default: tools/..
 *   SERVE_ROOT     served static tree            default: <repo>/src/python
 *   BASE_URL       origin of the running server  default: http://127.0.0.1:8124
 *   ARTIFACTS_DIR  where tools write their output default: <repo>/artifacts
 */
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const TOOLS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const REPO_ROOT = process.env.REPO_ROOT
  ? resolve(process.env.REPO_ROOT)
  : resolve(TOOLS_DIR, '..');

/** The served frontend tree. `build.py` writes generated bundles here. */
export const SERVE_ROOT = process.env.SERVE_ROOT
  ? resolve(process.env.SERVE_ROOT)
  : resolve(REPO_ROOT, 'src', 'python');

export const ARTIFACTS_DIR = process.env.ARTIFACTS_DIR
  ? resolve(process.env.ARTIFACTS_DIR)
  : resolve(REPO_ROOT, 'artifacts');

export const BASE_URL = (process.env.BASE_URL || 'http://127.0.0.1:8124').replace(/\/$/, '');

/**
 * The port every tool here defaults to.
 *
 * `Number(process.env.PORT || 8124)` looked correct and was not: an exported
 * `PORT=0` is a *truthy string*, so it resolves to the number 0 rather than to the
 * default. That is not hypothetical — the environment this pass ran in exports
 * `PORT=0`, and it cost an afternoon: report-verify's `--with-server` readiness probe
 * asked for `http://127.0.0.1:0/index.html`, never got an answer, and left the
 * server-dependent blocks reported as skipped with the flag apparently doing
 * nothing.
 *
 * tools/lhci-single.js already carries this exact fix for the same reason (Lighthouse
 * CI exports PORT=0 while it probes for a free port). It belongs here, in the one
 * place every tool reads the port from, rather than in each caller.
 *
 * Only a real, non-zero port is honoured; anything else falls back to 8124.
 */
const envPort = Number(process.env.PORT);
export const PORT = Number.isInteger(envPort) && envPort > 0 ? envPort : 8124;

/** The 16 shipped routes, in the order lhci measures them. */
export const PAGES = [
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
];

/** Absolute path inside the served tree for a page name or route. */
export function servedPath(rel) {
  return resolve(SERVE_ROOT, rel.replace(/^\/+/, ''));
}

/** Absolute path inside the page's URL, so tools can build origins consistently. */
export function pageUrl(page) {
  return `${BASE_URL}/${page.replace(/^\/+/, '')}`;
}

/** Absolute path under artifacts/, creating the directory on first use. */
export function artifactPath(...parts) {
  mkdirSync(ARTIFACTS_DIR, { recursive: true });
  return resolve(ARTIFACTS_DIR, ...parts);
}

/**
 * Turn a CLI argument into an absolute page URL. Accepts a full URL, a route
 * (`/index.html`), or a bare page name (`index.html`).
 */
export function urlFromArg(arg) {
  if (!arg) return pageUrl('index.html');
  if (/^https?:\/\//.test(arg)) return arg;
  return pageUrl(arg);
}

/** Small arg helper: `--flag` / `--key=value` extraction without a dependency. */
export function argValue(argv, name, fallback = undefined) {
  const hit = argv.find((a) => a === `--${name}` || a.startsWith(`--${name}=`));
  if (!hit) return fallback;
  if (hit === `--${name}`) return true;
  return hit.slice(name.length + 3);
}

export function hasFlag(argv, name) {
  return argv.includes(`--${name}`);
}

export function assertServed(path, hint) {
  if (!existsSync(path)) {
    console.error(`tools: not found: ${path}`);
    if (hint) console.error(`tools: ${hint}`);
    process.exit(2);
  }
}
