// Per-response security headers, byte-compatible with Python's Handler.
// CSP is built per request with a fresh nonce, exactly like csp_header().
import { randomBytes } from 'node:crypto';

export const REPORT_TO = '{"group":"csp","max_age":10886400,"endpoints":[{"url":"/api/csp-report"}]}';

/** 16 random bytes, url-safe, no padding — like secrets.token_urlsafe(16). */
export function newNonce() {
  return randomBytes(16).toString('base64url');
}

/** 32 lowercase hex, like the Python request id. */
export function newRequestId() {
  return randomBytes(16).toString('hex');
}

/**
 * safe_request_id(): keep correlation across the router and both backends.
 * Python reflects a sanitized inbound id and falls back to a fresh one, so a
 * request that crosses the boundary keeps one id in every log line.
 */
export function safeRequestId(value) {
  const clean = String(value ?? '')
    .replace(/[^A-Za-z0-9._:-]/g, '')
    .slice(0, 80);
  return clean || newRequestId();
}

export function cspHeader(nonce) {
  return (
    "default-src 'self'; script-src 'self'; style-src 'self' 'nonce-" +
    nonce +
    "'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self' data:; " +
    "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://w.soundcloud.com; " +
    "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'"
  );
}

/**
 * Apply the shared header set. `permissions` differs per route: /checkin keeps
 * the camera carve-out for QR scanning, everything else denies it.
 */
export function applySecurityHeaders(reply, { nonce, permissions, requestId }) {
  reply.header('x-request-id', safeRequestId(requestId));
  reply.header('x-content-type-options', 'nosniff');
  reply.header('referrer-policy', 'strict-origin-when-cross-origin');
  reply.header('permissions-policy', permissions);
  reply.header('x-frame-options', 'SAMEORIGIN');
  reply.header('cross-origin-opener-policy', 'same-origin');
  reply.header('cross-origin-resource-policy', 'same-site');
  const policy = cspHeader(nonce);
  reply.header('content-security-policy', policy);
  reply.header('content-security-policy-report-only', policy + '; report-uri /api/csp-report; report-to csp');
  reply.header('report-to', REPORT_TO);
}

export const PERMISSIONS_DEFAULT = 'camera=(), microphone=(), geolocation=()';
export const PERMISSIONS_CHECKIN = 'camera=(self), microphone=(), geolocation=()';

/**
 * Python's json() helper writes `{"error": "Not found"}` — a space after the
 * colon and after each comma. Flat objects only, which is all the 404 path uses.
 */
export function jsonBody(value) {
  const pairs = Object.entries(value).map(
    ([key, entry]) => `${JSON.stringify(key)}: ${JSON.stringify(entry)}`,
  );
  return `{${pairs.join(', ')}}`;
}
