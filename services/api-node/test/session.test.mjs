import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CSRF_COOKIE,
  SESSION_COOKIE,
  guardCookieOrigin,
  hashToken,
  parseCookies,
  resolveSession,
  sessionToken,
} from '../lib/session.mjs';

/** Minimal stand-in for the query layer; records the SQL it was asked for. */
function stubDb(handler) {
  const calls = [];
  return {
    calls,
    async query(sql, params = []) {
      calls.push({ sql, params });
      return handler(sql, params);
    },
  };
}

test('cookies parse without splitting values that contain "="', () => {
  const cookies = parseCookies('einvite_session=abc=def; einvite_csrf=xyz; empty=');
  assert.equal(cookies.get(SESSION_COOKIE), 'abc=def');
  assert.equal(cookies.get(CSRF_COOKIE), 'xyz');
  assert.equal(sessionToken(''), '');
  assert.equal(sessionToken(undefined), '');
});

test('no cookie means no session and no query', async () => {
  const db = stubDb(() => ({ rows: [] }));
  assert.equal(await resolveSession(db, { cookieHeader: '' }), null);
  assert.equal(db.calls.length, 0);
});

test('a session row resolves to its user and touches last_seen when stale', async () => {
  const now = 1_700_000_000_000;
  const db = stubDb((sql) => {
    if (sql.startsWith('SELECT u.id')) {
      return {
        rows: [
          {
            id: 'u1',
            role: 'customer',
            session_never_expires: 0,
            last_seen_at: now - 5 * 60_000,
          },
        ],
      };
    }
    return { rows: [] };
  });
  const session = await resolveSession(db, { cookieHeader: `einvite_session=tok`, now });
  assert.equal(session.user.id, 'u1');
  assert.ok(
    db.calls.some((call) => call.sql.startsWith('UPDATE sessions SET last_seen_at')),
    'stale session is touched once',
  );
});

test('an idle session past the non-admin limit is treated as expired', async () => {
  const now = 1_700_000_000_000;
  const db = stubDb((sql) => {
    if (sql.startsWith('SELECT u.id')) {
      return { rows: [{ id: 'u1', role: 'customer', session_never_expires: 0, last_seen_at: now - 8 * 86_400_000 }] };
    }
    return { rows: [] };
  });
  const session = await resolveSession(db, { cookieHeader: 'einvite_session=tok', now });
  assert.equal(session.expired, true);
});

test('a cross-site Sec-Fetch-Site is rejected before any session lookup', async () => {
  const db = stubDb(() => ({ rows: [] }));
  await assert.rejects(
    () =>
      guardCookieOrigin(
        db,
        { headers: { host: 'example.test', 'sec-fetch-site': 'same-site', origin: 'http://example.test' } },
        {},
      ),
    (error) => error.status === 403 && error.body.code === 'csrf_rejected',
  );
  assert.equal(db.calls.length, 0);
});

test('a foreign Origin is rejected', async () => {
  const db = stubDb(() => ({ rows: [] }));
  await assert.rejects(
    () =>
      guardCookieOrigin(
        db,
        { headers: { host: 'example.test', origin: 'http://evil.test' } },
        {},
      ),
    (error) => error.body.code === 'csrf_rejected',
  );
});

test('a session request without the double-submit pair is csrf_required', async () => {
  const db = stubDb(() => ({ rows: [{ '?column?': 1 }] }));
  await assert.rejects(
    () =>
      guardCookieOrigin(
        db,
        {
          headers: {
            host: 'example.test',
            origin: 'http://example.test',
            cookie: `einvite_session=tok`,
            'x-csrf-token': 'abc',
          },
        },
        {},
      ),
    (error) => error.body.code === 'csrf_required',
  );
});

test('a token that matches the cookie but not the session is csrf_invalid', async () => {
  const db = stubDb((sql) => {
    if (sql.startsWith('SELECT 1 FROM sessions WHERE token_hash=? AND csrf_hash=?')) return { rows: [] };
    return { rows: [{ '?column?': 1 }] };
  });
  await assert.rejects(
    () =>
      guardCookieOrigin(
        db,
        {
          headers: {
            host: 'example.test',
            origin: 'http://example.test',
            cookie: `einvite_session=tok; einvite_csrf=abc`,
            'x-csrf-token': 'abc',
          },
        },
        {},
      ),
    (error) => error.body.code === 'csrf_invalid',
  );
});

test('a matching pair passes and the stored hashes are what the port computes', async () => {
  const db = stubDb(() => ({ rows: [{ '?column?': 1 }] }));
  await guardCookieOrigin(
    db,
    {
      headers: {
        host: 'example.test',
        origin: 'http://example.test',
        cookie: `einvite_session=tok; einvite_csrf=abc`,
        'x-csrf-token': 'abc',
      },
    },
    {},
  );
  const csrfCall = db.calls.find((call) => call.sql.includes('csrf_hash=?'));
  const [tokenHash, csrfHash, expiresAt] = csrfCall.params;
  assert.equal(tokenHash, hashToken('tok'));
  assert.equal(csrfHash, hashToken('abc'));
  assert.equal(typeof expiresAt, 'number');
});
