// GET /api/feature-flags — the boot read every page makes (server.py
// public_feature_flags). Public: an anonymous caller gets the tier-less flags,
// a signed-in caller also gets the flags for their plan.
import { resolveSession } from './session.mjs';
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';
import { flagSnapshot, isFlagEnabled, publicFlagsForTier } from './feature-flags.mjs';

export function registerMetaRoutes(app, { db }) {
  app.get('/api/feature-flags', async (request, reply) => {
    applySecurityHeaders(reply, {
      nonce: newNonce(),
      permissions: PERMISSIONS_DEFAULT,
      requestId: request.requestId,
    });
    reply.header('content-type', 'application/json; charset=utf-8');
    reply.header('cache-control', 'no-store');

    const session = await resolveSession(db, { cookieHeader: request.headers.cookie });
    const tier = session?.user?.plan || null;
    const snapshot = await flagSnapshot(db);
    return {
      flags: publicFlagsForTier(snapshot, tier),
      maintenanceMode: isFlagEnabled(snapshot, 'maintenance_mode'),
    };
  });
}
