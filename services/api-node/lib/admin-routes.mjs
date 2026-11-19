// Admin reads. The reports queue is the first one ported; it carries no
// rate_limit in Python, so P7's pin rule does not apply.
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';
import { requireAdmin } from './admin-auth.mjs';
import { STATUS_VALUES, ensureReportsSchema, listReports } from './reports.mjs';

function secure(reply, request) {
  applySecurityHeaders(reply, {
    nonce: newNonce(),
    permissions: PERMISSIONS_DEFAULT,
    requestId: request.requestId,
  });
  reply.header('content-type', 'application/json; charset=utf-8');
  reply.header('cache-control', 'no-store');
}

/** Python int(): optional sign, no decimals; surrounding whitespace is allowed. */
function pyInt(value) {
  const text = String(value).trim();
  return /^[+-]?\d+$/.test(text) ? Number.parseInt(text, 10) : null;
}

export function registerAdminRoutes(app, { db, adminIpAllowlist = process.env.EINVITE_ADMIN_IP_ALLOWLIST }) {
  /** GET /api/admin/reports — admin_reports_list(). */
  app.get('/api/admin/reports', async (request, reply) => {
    secure(reply, request);
    const admin = await requireAdmin(db, request, reply, adminIpAllowlist);
    if (!admin) return reply;

    const query = request.query ?? {};
    const status = String(query.status ?? '').trim().toLowerCase();
    const targetType = String(query.targetType ?? '').trim().toLowerCase() || null;

    if (status && !STATUS_VALUES.includes(status)) {
      return reply.code(400).send({ error: 'Invalid status' });
    }
    const rawLimit = query.limit ?? '100';
    const parsedLimit = pyInt(rawLimit);
    if (parsedLimit === null) return reply.code(400).send({ error: 'Invalid limit' });
    const limit = Math.max(1, Math.min(parsedLimit, 200));

    const rawCursor = String(query.cursor ?? '');
    const cursor = /^\d+$/.test(rawCursor) ? Number.parseInt(rawCursor, 10) : null;

    await ensureReportsSchema(db);
    const result = await listReports(db, {
      status: status || null,
      targetType,
      limit,
      cursor,
    });
    return reply.send(result);
  });
}
