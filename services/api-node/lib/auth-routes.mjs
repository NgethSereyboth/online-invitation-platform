// The two session routes the S6 proof needs, ported from server.py.
// `/api/auth/me` (4879) and `logout()` (7502).
import { CsrfRejection, guardCookieOrigin, hashToken, resolveSession, sessionToken } from './session.mjs';

export function registerSessionRoutes(app, { db, cipher }) {
  app.get('/api/auth/me', async (request, reply) => {
    reply.header('cache-control', 'no-store');
    const session = await resolveSession(db, { cookieHeader: request.headers.cookie });
    const user = session?.user ? cipher.revealRow({ ...session.user }) : null;
    return { user };
  });

  app.post('/api/auth/logout', async (request, reply) => {
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
    reply.header(
      'set-cookie',
      'einvite_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax',
    );
    reply.header('set-cookie', 'einvite_csrf=; Path=/; Max-Age=0; SameSite=Lax');
    reply.header('cache-control', 'no-store');
    return { signedOut: true };
  });
}
