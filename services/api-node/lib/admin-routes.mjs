// Admin reads. The reports queue, the console overview, the user lists, the
// invitation list, the audit explorer and one background job. None of these
// handlers calls rate_limit in Python, so P7's pin rule does not apply.
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';
import { requireAdmin } from './admin-auth.mjs';
import {
  adminOverview,
  auditEventsCsv,
  getAdminJob,
  listAdminInvitations,
  listAdminUsers,
  listAdminUsersPage,
  listAuditEvents,
  pyInt,
  pySlice,
} from './admin-reads.mjs';
import { writeAuditEvent } from './audit.mjs';
import { pythonLower, pythonStrip } from './pystr.mjs';
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

/** Python's parse_qs takes the first value and drops a blank one. */
function queryValue(query, name) {
  const value = query?.[name];
  if (Array.isArray(value)) return value.length ? String(value[0]) : '';
  return value === undefined || value === null ? '' : String(value);
}

export function registerAdminRoutes(app, { db, cipher = null, adminIpAllowlist = process.env.EINVITE_ADMIN_IP_ALLOWLIST }) {
  const reveal = cipher ? (value) => cipher.reveal(value) : (value) => value;
  const gate = (request, reply) => requireAdmin(db, request, reply, adminIpAllowlist, cipher);

  /** GET /api/admin/reports — admin_reports_list(). */
  app.get('/api/admin/reports', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
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

  /** GET /api/admin/overview — admin_overview(). */
  app.get('/api/admin/overview', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
    if (!admin) return reply;
    return reply.send(await adminOverview(db));
  });

  /** GET /api/admin/users — admin_users(), the legacy array. */
  app.get('/api/admin/users', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
    if (!admin) return reply;
    return reply.send(await listAdminUsers(db, reveal));
  });

  /** GET /api/admin/users-v2 — admin_users_v2(). */
  app.get('/api/admin/users-v2', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
    if (!admin) return reply;

    const query = request.query ?? {};
    const rawLimit = queryValue(query, 'limit');
    const parsedLimit = pyInt(rawLimit === '' ? '25' : rawLimit);
    if (parsedLimit === null) return reply.code(400).send({ error: 'Invalid limit' });
    const limit = Math.max(1, Math.min(parsedLimit, 100));
    const unmask = queryValue(query, 'unmask') === '1';
    const search = pySlice(pythonLower(pythonStrip(queryValue(query, 'q'))), 254);

    let cursor = null;
    const rawCursor = queryValue(query, 'cursor');
    if (rawCursor) {
      const separator = rawCursor.indexOf(':');
      const created = separator === -1 ? null : pyInt(rawCursor.slice(0, separator));
      if (created === null) return reply.code(400).send({ error: 'Invalid cursor' });
      cursor = { created, id: rawCursor.slice(separator + 1) };
    }

    const result = await listAdminUsersPage(db, { limit, unmask, search, cursor }, reveal);
    if (unmask) {
      try {
        await writeAuditEvent(db, {
          cipher,
          userId: admin.id,
          action: 'admin.users_unmasked',
          targetType: 'user',
          metadata: { count: result.items.length },
          ipAddress: request.ip,
          adminRoute: true,
        });
      } catch (error) {
        request.log.warn({ err: String(error) }, 'audit write failed');
      }
    }
    return reply.send(result);
  });

  /** GET /api/admin/invitations — admin_invitations(). */
  app.get('/api/admin/invitations', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
    if (!admin) return reply;
    return reply.send(await listAdminInvitations(db, reveal));
  });

  /** GET /api/admin/audit-events — admin_audit_events(), JSON or CSV. */
  app.get('/api/admin/audit-events', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
    if (!admin) return reply;

    const query = request.query ?? {};
    const rawLimit = queryValue(query, 'limit');
    const parsedLimit = pyInt(rawLimit === '' ? '50' : rawLimit);
    if (parsedLimit === null) return reply.code(400).send({ error: 'Invalid limit' });
    const limit = Math.max(1, Math.min(parsedLimit, 200));

    const result = await listAuditEvents(
      db,
      {
        user: queryValue(query, 'user'),
        action: queryValue(query, 'action'),
        targetType: queryValue(query, 'targetType'),
        targetId: queryValue(query, 'targetId'),
        ip: queryValue(query, 'ip'),
        adminOnly: queryValue(query, 'adminOnly'),
        from: queryValue(query, 'from'),
        to: queryValue(query, 'to'),
        limit,
      },
      reveal,
    );
    if (result === null) return reply.code(400).send({ error: 'Invalid date filter' });

    if (pythonLower(queryValue(query, 'format')) === 'csv') {
      const body = auditEventsCsv(result.rows);
      reply.header('content-type', 'text/csv; charset=utf-8');
      reply.header('content-disposition', 'attachment; filename="audit-events.csv"');
      reply.header('content-length', String(Buffer.byteLength(body)));
      return reply.send(body);
    }
    return reply.send({ items: result.items, count: result.items.length });
  });

  /** GET /api/admin/jobs/:id — admin_job_status(). */
  app.get('/api/admin/jobs/:id', async (request, reply) => {
    secure(reply, request);
    const admin = await gate(request, reply);
    if (!admin) return reply;
    const job = await getAdminJob(db, request.params.id);
    if (!job) return reply.code(404).send({ error: 'Job not found' });
    return reply.send(job);
  });
}
