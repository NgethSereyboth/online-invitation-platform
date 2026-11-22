// The two session routes the S6 proof needs, ported from server.py.
// `/api/auth/me` (4879) and `logout()` (7502).
import { CsrfRejection, guardCookieOrigin, hashToken, resolveSession, sessionToken } from './session.mjs';
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';

function secure(reply, request) {
  applySecurityHeaders(reply, {
    nonce: newNonce(),
    permissions: PERMISSIONS_DEFAULT,
    requestId: request.requestId,
  });
  reply.header('content-type', 'application/json; charset=utf-8');
  reply.header('cache-control', 'no-store');
}

export function registerSessionRoutes(app, { db, cipher }) {
  app.get('/api/auth/me', async (request, reply) => {
    secure(reply, request);
    const session = await resolveSession(db, { cookieHeader: request.headers.cookie });
    const user = session?.user ? cipher.revealRow({ ...session.user }) : null;
    return { user };
  });

  app.post('/api/auth/logout', async (request, reply) => {
    secure(reply, request);
    try {
      await guardCookieOrigin(db, request);
    } catch (error) {
      if (error instanceof CsrfRejection) {
        reply.code(error.status);
        return error.body;
      }
      throw error;
    }
    const token = sessionToken(request.headers.cookie);
    if (token) await db.query('DELETE FROM sessions WHERE token_hash=?', [hashToken(token)]);
    // Two Set-Cookie headers, as Python sends: passing them one at a time would
    // leave only the last one on the response.
    reply.header('set-cookie', [
      'einvite_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax',
      'einvite_csrf=; Path=/; Max-Age=0; SameSite=Lax',
    ]);
    return { signedOut: true };
  });
}
