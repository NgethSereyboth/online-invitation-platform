// S7: the media-URL and gallery logic the public invitation read path needs.
// Copied from server.py (signed_media_url, managed_media_path,
// protected_gallery_media_paths, apply_gallery_access, rewrite_document_media_urls)
// rather than reinvented: these URLs are validated by Python's HMAC on the way
// back in, so the signature payload is a wire contract.
import { createHmac, randomBytes } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

/** Python's `quote(value, safe='')`: encodeURIComponent plus the five extras it escapes. */
export function pythonQuote(value) {
  return encodeURIComponent(String(value)).replace(
    /[!'()*]/g,
    (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

/** basename(): Python's Path(...).name is "/"-split, never platform-specific. */
function posixBasename(value) {
  const parts = String(value).split('/');
  return parts[parts.length - 1] || '';
}

/** urllib.parse.urlparse(value).path without a URL polyfill's normalisation. */
function urlPath(value) {
  const withoutFragment = String(value).split('#')[0];
  const withoutQuery = withoutFragment.split('?')[0];
  const scheme = withoutQuery.match(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//);
  if (!scheme) return withoutQuery;
  const rest = withoutQuery.slice(scheme[0].length);
  const slash = rest.indexOf('/');
  return slash === -1 ? '/' : rest.slice(slash);
}

export function mediaTtlSeconds(env = process.env) {
  const parsed = Number.parseInt(env.EINVITE_MEDIA_URL_TTL_SECONDS ?? '900', 10);
  if (!Number.isFinite(parsed)) return 900;
  return Math.max(60, Math.min(3600, parsed));
}

/**
 * persistent_data_secret("EINVITE_MEDIA_SIGNING_SECRET", ".media-signing-secret"):
 * configured env wins, then the sidecar Python already wrote, then generate one
 * so a service-only deployment does not sign with a different key each boot.
 */
export function resolveSigningSecret({ env = process.env, dataDir = env.EINVITE_DATA_DIR } = {}) {
  const configured = String(env.EINVITE_MEDIA_SIGNING_SECRET ?? '').trim();
  if (configured) return configured;
  if (!dataDir) return randomBytes(36).toString('base64url');
  const path = join(dataDir, '.media-signing-secret');
  try {
    const stored = readFileSync(path, 'utf8').trim();
    if (stored) return stored;
  } catch {
    /* missing sidecar falls through to generation */
  }
  const value = randomBytes(36).toString('base64url');
  try {
    mkdirSync(dataDir, { recursive: true });
    writeFileSync(path, value, { encoding: 'utf8', mode: 0o600 });
    return value;
  } catch {
    return value;
  }
}

export function mediaSignature(path, invitationId, expires, secret) {
  const clean = posixBasename(String(path ?? ''));
  const payload = `${clean}|${invitationId}|${Math.trunc(Number(expires))}`;
  return createHmac('sha256', secret).update(payload, 'utf8').digest('hex');
}

/** `/api/media/<file>?i=<id>&exp=<ms>&sig=<hmac>` — the shape Python serves. */
export function signedMediaUrl(path, invitationId, expires, secret, ttlSeconds = mediaTtlSeconds()) {
  const clean = posixBasename(String(path ?? ''));
  const exp = Math.trunc(Number(expires ?? Math.floor(Date.now() / 1000) + ttlSeconds));
  const signature = mediaSignature(clean, invitationId, exp, secret);
  return `/api/media/${pythonQuote(clean)}?i=${pythonQuote(invitationId)}&exp=${exp}&sig=${signature}`;
}

/** managed_media_path(): the stored filename a first-party URL points at. */
export function managedMediaPath(value, publicBaseUrl = process.env.EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL ?? '') {
  const raw = String(value ?? '').trim();
  if (!raw) return '';
  const path = urlPath(raw);
  for (const prefix of ['/uploads/', '/api/image/', '/api/media/']) {
    if (path.startsWith(prefix)) return posixBasename(decodeURIComponent(path.slice(prefix.length)));
  }
  const base = String(publicBaseUrl).replace(/\/$/, '');
  if (base && raw.startsWith(`${base}/`)) return posixBasename(decodeURIComponent(path));
  return '';
}

function documentReferencesMedia(documentJson, path, publicBaseUrl) {
  const clean = posixBasename(String(path ?? ''));
  if (!clean) return false;
  const text = String(documentJson ?? '');
  return (
    text.includes(clean) &&
    (text.includes(`/uploads/${clean}`) ||
      text.includes(`/api/image/${clean}`) ||
      (publicBaseUrl && text.includes(clean)))
  );
}

/** Gallery-only media paths: images that appear nowhere else in the document. */
export function protectedGalleryMediaPaths(document, publicBaseUrl) {
  if (!document || typeof document !== 'object' || Array.isArray(document)) return new Set();
  const objects = document.objects && typeof document.objects === 'object' ? document.objects : {};
  const candidates = new Map();
  for (const [objectId, object] of Object.entries(objects)) {
    if (!object || typeof object !== 'object' || Array.isArray(object)) continue;
    if (object.type !== 'image' || object.showInGallery === false || object.showInHero !== false) continue;
    const clean = managedMediaPath(object.src, publicBaseUrl);
    if (!clean) continue;
    if (!candidates.has(clean)) candidates.set(clean, []);
    candidates.get(clean).push(objectId);
  }
  if (!candidates.size) return new Set();
  const result = new Set();
  for (const [clean, ids] of candidates) {
    const clone = structuredClone(document);
    for (const objectId of ids) {
      const target = (clone.objects ?? {})[objectId];
      if (target && typeof target === 'object') {
        target.src = '';
        target.responsiveBase = '';
      }
    }
    if (!documentReferencesMedia(JSON.stringify(clone), clean, publicBaseUrl)) result.add(clean);
  }
  return result;
}

/** Lock or sign every gallery-only image, matching Python field-for-field. */
export function applyGalleryAccess(
  document,
  invitationId,
  authorized = false,
  { secret, ttlSeconds = mediaTtlSeconds(), publicBaseUrl } = {},
) {
  if (!document || typeof document !== 'object' || Array.isArray(document)) return document;
  const protectedPaths = protectedGalleryMediaPaths(document, publicBaseUrl);
  const protection =
    document.galleryProtection && typeof document.galleryProtection === 'object'
      ? document.galleryProtection
      : {};
  if (!protection.enabled || !protectedPaths.size) return document;
  const clone = structuredClone(document);
  clone.galleryProtection = { ...(clone.galleryProtection ?? {}), locked: !authorized };
  for (const object of Object.values(clone.objects ?? {})) {
    if (!object || typeof object !== 'object') continue;
    const clean = managedMediaPath(object.src, publicBaseUrl);
    if (!protectedPaths.has(clean)) continue;
    if (authorized) {
      object.src = signedMediaUrl(clean, invitationId, undefined, secret, ttlSeconds);
      object.responsiveBase = signedMediaUrl(clean, invitationId, undefined, secret, ttlSeconds);
    } else {
      object.showInGallery = false;
      object.src = '';
      object.responsiveBase = '';
    }
  }
  return clone;
}

const MEDIA_IN_TEXT = /(?:\/(?:uploads|api\/image)\/)([^\s"'()<>?]+)(?:\?([^\s"'()<>#]*))?/gi;

/** rewrite_document_media_urls(): password-protected documents never leak raw paths. */
export function rewriteDocumentMediaUrls(
  document,
  invitationId,
  { secret, ttlSeconds = mediaTtlSeconds(), nowSeconds = Math.floor(Date.now() / 1000), publicBaseUrl } = {},
) {
  const expires = Math.trunc(nowSeconds) + ttlSeconds;
  const signedFor = (clean, query = '') => {
    let signed = signedMediaUrl(clean, invitationId, expires, secret, ttlSeconds);
    const extras = [];
    for (const key of ['w', 'format']) {
      for (const raw of new URLSearchParams(query).getAll(key)) extras.push([key, raw]);
    }
    if (extras.length) {
      signed += `&${extras.map(([key, value]) => `${pythonQuote(key)}=${pythonQuote(value)}`).join('&')}`;
    }
    return signed;
  };
  const walk = (value) => {
    if (Array.isArray(value)) return value.map(walk);
    if (value && typeof value === 'object') {
      const out = {};
      for (const [key, item] of Object.entries(value)) out[key] = walk(item);
      return out;
    }
    if (typeof value !== 'string') return value;
    const clean = managedMediaPath(value, publicBaseUrl);
    if (clean) return signedFor(clean, new URL(value, 'http://local').search.replace(/^\?/, ''));
    return value.replace(MEDIA_IN_TEXT, (_match, rawPath, query) =>
      signedFor(posixBasename(decodeURIComponent(rawPath)), query ?? ''),
    );
  };
  return walk(document);
}
