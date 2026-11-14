// Page rendering parity with Python's serve_html_file (src/python/server.py).
// The transform is deliberately small and ordered: critical CSS, then the
// per-response style nonce, then the head bits.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

export const PAGE_ALIASES = {
  '/account': 'account.html',
  '/admin': 'admin.html',
  '/analytics': 'analytics.html',
  '/billing': 'billing.html',
  '/checkin': 'checkin.html',
  '/dashboard': 'dashboard.html',
  '/designer': 'designer.html',
  '/guests': 'guests.html',
  '/materials': 'materials.html',
  '/privacy': 'privacy.html',
  '/public': 'public.html',
  '/reset': 'reset.html',
  '/responses': 'responses.html',
  '/templates': 'templates.html',
  '/verify': 'verify.html',
};

const CRITICAL_CSS_MARKER = '<!--CRITICAL_CSS-->';
const BACKEND_MARKER = '<meta name="einvite-backend" content="full">';
const BASE_MARKER = '<base href="/">';

/** Page files that exist in the web root, exactly like HTML_PAGE_FILES. */
export function pageFiles(webRoot) {
  const files = new Map();
  for (const name of readdirSync(webRoot)) {
    if (!name.endsWith('.html')) continue;
    const full = join(webRoot, name);
    try {
      if (statSync(full).isFile()) files.set(name, full);
    } catch {
      /* raced with a delete; the page simply does not exist */
    }
  }
  return files;
}

/** Resolve a URL path to a page file name, or null. */
export function pageForPath(pathname) {
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  if (trimmed === '/' || trimmed === '') return 'index.html';
  const alias = PAGE_ALIASES[trimmed];
  if (alias) return alias;
  const name = trimmed.replace(/^\//, '');
  if (name.endsWith('.html') && !name.includes('/')) return name;
  return null;
}

/** Python's urllib.parse.quote(slug) with the default safe set. */
export function quotePathSegment(value) {
  return encodeURIComponent(value).replace(/[!'()*]/g, (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`);
}

/** html.escape(..., quote=True) for the attribute contexts the shell uses. */
export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

/**
 * The public shell with its placeholders filled. Defaults match Python's
 * no-row branch: an unknown slug still renders the invitation page (status
 * 404), because /i/<slug> links already live in chats.
 */
export function substitutePublicPlaceholders(page, { slug, title, description, imagePath, publicUrl, imageFormat }) {
  return page
    .replaceAll('__INVITATION_SLUG__', escapeHtml(slug))
    .replaceAll('__INVITATION_TITLE__', escapeHtml(title))
    .replaceAll('__INVITATION_DESCRIPTION__', escapeHtml(description))
    .replaceAll('__INVITATION_OG_IMAGE__', escapeHtml(imagePath))
    .replaceAll('__INVITATION_PUBLIC_URL__', escapeHtml(publicUrl))
    .replaceAll('__INVITATION_OG_TYPE__', imageFormat === 'png' ? 'image/png' : 'image/svg+xml');
}

function injectCriticalCss(page, criticalCss) {
  if (!page.includes(CRITICAL_CSS_MARKER)) return page;
  const replacement = criticalCss === null ? '' : `<style data-critical>${criticalCss}</style>`;
  return page.replace(CRITICAL_CSS_MARKER, replacement);
}

function injectStyleNonce(page, nonce) {
  if (!nonce) return page;
  return page.replace(/<style(?=[\s>])/gi, `<style nonce="${nonce}"`);
}

/** Render one page buffer. Returns null when the file does not exist. */
export function renderPage(files, fileName, { nonce, criticalCss }) {
  const path = files.get(fileName);
  if (!path) return null;
  let page = readFileSync(path, 'utf8');
  page = injectCriticalCss(page, criticalCss);
  page = injectStyleNonce(page, nonce);
  const headBits =
    (page.includes(BACKEND_MARKER) ? '' : BACKEND_MARKER) + (page.includes('<base ') ? '' : BASE_MARKER);
  if (headBits) page = page.replace('<head>', `<head>${headBits}`);
  return Buffer.from(page, 'utf8');
}
