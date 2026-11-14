// Static-file parity with Python's SimpleHTTPRequestHandler. Observed and
// matched deliberately: no Range support (Python returns 200 for a Range
// request), 304 on If-Modified-Since, a JSON 404 for a missing file, and
// `public, max-age=3600, must-revalidate` on hits.
import { createReadStream, statSync } from 'node:fs';
import { extname, join, normalize, resolve, sep } from 'node:path';

// Python's mimetypes values for the extensions the mirror actually uses.
const MIME = new Map([
  ['.html', 'text/html'],
  ['.js', 'text/javascript'],
  ['.mjs', 'text/javascript'],
  ['.css', 'text/css'],
  ['.json', 'application/json'],
  ['.map', 'application/json'],
  ['.webmanifest', 'application/manifest+json'],
  ['.svg', 'image/svg+xml'],
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.gif', 'image/gif'],
  ['.webp', 'image/webp'],
  ['.avif', 'image/avif'],
  ['.ico', 'image/vnd.microsoft.icon'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
  ['.ttf', 'font/ttf'],
  ['.otf', 'font/otf'],
  ['.txt', 'text/plain'],
  ['.xml', 'application/xml'],
  ['.wasm', 'application/wasm'],
  ['.mp4', 'video/mp4'],
  ['.webm', 'video/webm'],
  ['.mp3', 'audio/mpeg'],
  ['.pdf', 'application/pdf'],
]);

export function contentTypeFor(filePath) {
  return MIME.get(extname(filePath).toLowerCase()) ?? 'application/octet-stream';
}

/**
 * Resolve a URL path to a file inside webRoot, or null when it escapes or is
 * not a regular file. Mirrors Python's translate_path safety: no traversal.
 */
export function resolveAsset(webRoot, pathname) {
  const decoded = decodeURIComponent(pathname);
  if (decoded.includes('\0')) return null;
  const relative = normalize(decoded).replace(/^([/\\])+/, '');
  if (relative.split(/[/\\]/).includes('..')) return null;
  const full = resolve(join(webRoot, relative));
  const rootWithSep = resolve(webRoot) + sep;
  if (full !== resolve(webRoot) && !full.startsWith(rootWithSep)) return null;
  try {
    const stat = statSync(full);
    if (!stat.isFile()) return null;
    return { path: full, stat };
  } catch {
    return null;
  }
}

/** Seconds precision, like getmtime() fed to formatdate(). */
export function lastModified(stat) {
  return new Date(Math.floor(stat.mtimeMs / 1000) * 1000).toUTCString();
}

export function notModifiedSince(request, stat) {
  const header = request.headers['if-modified-since'];
  if (!header) return false;
  const since = Date.parse(header);
  if (Number.isNaN(since)) return false;
  return Math.floor(stat.mtimeMs / 1000) * 1000 <= since;
}

export function sendAsset(reply, request, { path, stat }) {
  reply.header('content-type', contentTypeFor(path));
  reply.header('cache-control', 'public, max-age=3600, must-revalidate');
  reply.header('last-modified', lastModified(stat));
  reply.header('content-length', String(stat.size));
  if (notModifiedSince(request, stat)) {
    reply.code(304).send();
    return reply;
  }
  reply.send(createReadStream(path));
  return reply;
}
