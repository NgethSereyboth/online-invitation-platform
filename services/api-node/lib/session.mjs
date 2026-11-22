// S6: sessions and CSRF, ported from server.py `user()` (4461) and
// `guard_cookie_origin()` (4350). Sessions are already DB rows keyed by the
// SHA-256 of the cookie token, so cross-backend validity is a property of the
// schema — the point of the port is to apply exactly the same checks.
import { createHash, timingSafeEqual } from 'node:crypto';

export const SESSION_COOKIE = process.env.EINVITE_SESSION_COOKIE_NAME || 'einvite_session';
export const CSRF_COOKIE = 'einvite_csrf';
export const ADMIN_SESSION_IDLE_MS = 30 * 60 * 1000;
export const DEFAULT_NON_ADMIN_IDLE_DAYS = 7;
const TOUCH_INTERVAL_MS = 60_000;

export function hashToken(token) {
  return createHash('sha256').update(token, 'utf8').digest('hex');
}

export function parseCookies(header) {
  const out = new Map();
  for (const part of String(header ?? '').split(';')) {
    const index = part.indexOf('=');
    if (index < 0) continue;
    const name = part.slice(0, index).trim();
    if (name) out.set(name, part.slice(index + 1).trim());
  }
  return out;
}

export function sessionToken(cookieHeader) {
  return parseCookies(cookieHeader).get(SESSION_COOKIE) || '';
}

/**
 * Resolve the session behind a request. Mirrors the Python query, including
 * the idle timeout and the once-a-minute `last_seen_at` touch.
 */
export async function resolveSession(db, { cookieHeader, now = Date.now() } = {}) {
  const token = sessionToken(cookieHeader);
  if (!token) return null;
  const tokenHash = hashToken(token);
  const result = await db.query(
    'SELECT u.id,u.email,u.role,u.email_verified,u.plan,u.upload_enabled,u.mfa_enabled,' +
      'u.deleted_at,u.session_never_expires,s.created_at session_created_at,s.last_seen_at ' +
      'FROM sessions s JOIN users u ON u.id=s.user_id ' +
      'WHERE s.token_hash=? AND s.expires_at>? AND u.deleted_at IS NULL AND u.suspended_at IS NULL',
    [tokenHash, now],
  );
  const row = result.rows[0];
  if (!row) return null;

  if (!row.session_never_expires) {
    const idleDays = await sessionIdleDays(db);
    const idleLimit = row.role === 'admin' ? ADMIN_SESSION_IDLE_MS : idleDays * 24 * 60 * 60 * 1000;
    if (now - Number(row.last_seen_at || 0) > idleLimit) return { expired: true, tokenHash };
    if (now - Number(row.last_seen_at || 0) > TOUCH_INTERVAL_MS) {
      try {
        await db.query('UPDATE sessions SET last_seen_at=? WHERE token_hash=?', [now, tokenHash]);
      } catch {
        /* the touch is best effort, as in Python */
      }
    }
  }
  return { user: row, tokenHash };
}

/** `session_idle_days_nonadmin` setting, defaulting to 7 as Python does. */
export async function sessionIdleDays(db) {
  try {
    const result = await db.query("SELECT value FROM settings WHERE key='session_idle_days_nonadmin'");
    const parsed = Number.parseInt(result.rows[0]?.value, 10);
    return Number.isFinite(parsed) ? parsed : DEFAULT_NON_ADMIN_IDLE_DAYS;
  } catch {
    return DEFAULT_NON_ADMIN_IDLE_DAYS;
  }
}

function sameSecret(left, right) {
  const a = Buffer.from(String(left));
  const b = Buffer.from(String(right));
  return a.length === b.length && timingSafeEqual(a, b);
}

export class CsrfRejection {
  constructor(status, body) {
    this.status = status;
    this.body = body;
  }
}

/**
 * Port of guard_cookie_origin(): Origin/Sec-Fetch-Site first, then the
 * double-submit token bound to the session row. Throws CsrfRejection so the
 * caller can send Python's exact status and body.
 */
export async function guardCookieOrigin(db, request, { now = Date.now(), requireSessionCsrf = true } = {}) {
  const origin = String(request.headers.origin ?? '').trim();
  const fetchSite = String(request.headers['sec-fetch-site'] ?? '').trim().toLowerCase();
  const host = request.headers.host;
  const allowed = new Set([`http://${host}`, `https://${host}`]);
  if (process.env.PUBLIC_BASE_URL) {
    try {
      allowed.add(new URL(process.env.PUBLIC_BASE_URL).origin);
    } catch {
      /* ignore a malformed PUBLIC_BASE_URL, as the Python path does */
    }
  }
  if (fetchSite === 'cross-site' || fetchSite === 'same-site') {
    throw new CsrfRejection(403, { error: 'Cross-site request rejected', code: 'csrf_rejected' });
  }
  if (origin && ![...allowed].some((value) => value.replace(/\/$/, '') === origin.replace(/\/$/, ''))) {
    throw new CsrfRejection(403, { error: 'Cross-site request rejected', code: 'csrf_rejected' });
  }

  let token = sessionToken(request.headers.cookie);
  let validSession = false;
  if (token) {
    const result = await db.query('SELECT 1 FROM sessions WHERE token_hash=? AND expires_at>?', [
      hashToken(token),
      now,
    ]);
    validSession = result.rows.length > 0;
    if (!validSession) token = '';
  }

  const strict = ['1', 'true', 'yes'].includes(
    String(process.env.EINVITE_STRICT_SESSION_CSRF ?? '').toLowerCase(),
  ) || String(process.env.EINVITE_PRODUCTION ?? '0') === '1';
  const needsToken = requireSessionCsrf && validSession && (strict || Boolean(origin) || Boolean(fetchSite));
  if (!needsToken) return;

  const header = String(request.headers['x-csrf-token'] ?? '').trim();
  const cookieValue = parseCookies(request.headers.cookie).get(CSRF_COOKIE) || '';
  if (!header || !cookieValue || !sameSecret(header, cookieValue)) {
    throw new CsrfRejection(403, { error: 'Missing or invalid CSRF token', code: 'csrf_required' });
  }
  const result = await db.query(
    'SELECT 1 FROM sessions WHERE token_hash=? AND csrf_hash=? AND expires_at>?',
    [hashToken(token), hashToken(header), now],
  );
  if (!result.rows.length) {
    throw new CsrfRejection(403, { error: 'CSRF token does not match this session', code: 'csrf_invalid' });
  }
}
