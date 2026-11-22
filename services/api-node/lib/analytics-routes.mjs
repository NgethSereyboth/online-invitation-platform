// S12c: creator-analytics reads and the jobs list reads that share their shape.
// All six routes are free of the Python rate limiter, so P7's pin rule does not
// apply to them; auth and 404 bodies match server.py exactly.
import {
  AUTH_REQUIRED,
  INVITATION_NOT_FOUND,
  currentUser,
  invitationRole,
} from './authz.mjs';
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';
import { flagSnapshot, isFlagEnabled } from './feature-flags.mjs';
import {
  accountAnalyticsSummary,
  accountCreationsTable,
  invitationAnalyticsSummary,
  invitationLiveActivity,
} from './analytics-queries.mjs';

function secure(reply, request) {
  applySecurityHeaders(reply, {
    nonce: newNonce(),
    permissions: PERMISSIONS_DEFAULT,
    requestId: request.requestId,
  });
  reply.header('content-type', 'application/json; charset=utf-8');
  reply.header('cache-control', 'no-store');
}

function parseJson(text, fallback) {
  try {
    return JSON.parse(text ?? fallback);
  } catch {
    return fallback;
  }
}

/** server.py get_analytics(): owner-only legacy dashboard payload. */
export function registerAnalyticsRoutes(app, { db }) {
  app.get('/api/invitations/:id/analytics', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) return reply.code(401).send(AUTH_REQUIRED);

    const inviteId = request.params.id;
    const now = Date.now();
    const start = now - 30 * 24 * 60 * 60 * 1000;
    const owned = await db.query(
      'SELECT 1 FROM invitations WHERE id=? AND owner_id=? AND deleted_at IS NULL',
      [inviteId, user.id],
    );
    if (!owned.rows.length) return reply.code(404).send(INVITATION_NOT_FOUND);

    const inviteRows = await db.query('SELECT views,draft_json FROM invitations WHERE id=?', [inviteId]);
    const invite = inviteRows.rows[0];
    const viewRows = await db.query(
      'SELECT viewed_at FROM view_events WHERE invitation_id=? AND viewed_at>=? ORDER BY viewed_at',
      [inviteId, start],
    );
    const rsvpRows = await db.query(
      'SELECT status,guest_count,created_at FROM rsvps WHERE invitation_id=?',
      [inviteId],
    );
    const guestRows = await db.query('SELECT checked_in FROM guests WHERE invitation_id=?', [inviteId]);

    // Python formats view days with localtime, unlike the analytics module's UTC.
    const byDay = {};
    for (const row of viewRows.rows) {
      const date = new Date(Number(row.viewed_at));
      const day = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
        date.getDate(),
      ).padStart(2, '0')}`;
      byDay[day] = (byDay[day] ?? 0) + 1;
    }
    const statuses = {};
    for (const row of rsvpRows.rows) statuses[row.status] = (statuses[row.status] ?? 0) + 1;

    let rsvpEnabled = true;
    try {
      const doc = JSON.parse(invite.draft_json || '{}');
      rsvpEnabled = doc?.settings?.rsvpEnabled !== false;
    } catch {
      rsvpEnabled = true;
    }

    const analytics = await invitationAnalyticsSummary(db, inviteId);
    return reply.send({
      totalViews: Number(invite.views ?? 0),
      views30Days: viewRows.rows.length,
      viewsByDay: byDay,
      rsvpEnabled,
      rsvpTotal: rsvpRows.rows.length,
      rsvpGuests: rsvpRows.rows.reduce((sum, row) => sum + Number(row.guest_count ?? 0), 0),
      rsvpStatuses: statuses,
      guestListTotal: guestRows.rows.length,
      checkedIn: guestRows.rows.filter((row) => row.checked_in).length,
      analytics,
    });
  });

  /** invitation_analytics_live(): readable collaborators; flag-gated 403. */
  app.get('/api/invitations/:id/analytics/live', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) return reply.code(401).send(AUTH_REQUIRED);

    const inviteId = request.params.id;
    const role = await invitationRole(db, inviteId, user.id);
    if (role === null) return reply.code(404).send(INVITATION_NOT_FOUND);
    const snapshot = await flagSnapshot(db);
    if (!isFlagEnabled(snapshot, 'analytics_live_enabled')) {
      return reply
        .code(403)
        .send({ error: 'Live analytics is not enabled', code: 'feature_disabled' });
    }
    return reply.send(await invitationLiveActivity(db, inviteId));
  });

  app.get('/api/account/analytics/summary', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) return reply.code(401).send(AUTH_REQUIRED);
    return reply.send(await accountAnalyticsSummary(db, user.id));
  });

  /** GET /api/account/analytics/creations?sort=&order=&status=&limit=&offset= */
  app.get('/api/account/analytics/creations', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) return reply.code(401).send(AUTH_REQUIRED);

    const query = request.query ?? {};
    const sort = query.sort || 'updatedAt';
    const order = query.order || 'desc';
    const statusFilter = query.status || null;
    const limit = Number.parseInt(query.limit ?? '100', 10);
    const offset = Number.parseInt(query.offset ?? '0', 10);
    return reply.send(
      await accountCreationsTable(db, user.id, {
        sort,
        order,
        statusFilter,
        limit: Number.isNaN(limit) ? 100 : Math.max(1, Math.min(limit, 500)),
        offset: Number.isNaN(offset) ? 0 : Math.max(0, offset),
      }),
    );
  });

  /** list_studio_bulk_jobs(): any signed-in user, own rows, latest 50. */
  app.get('/api/studio/bulk-jobs', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) return reply.code(401).send(AUTH_REQUIRED);

    const rows = await db.query(
      'SELECT * FROM studio_bulk_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 50',
      [user.id],
    );
    const jobs = rows.rows.map((row) => ({
      id: row.id,
      kind: row.kind,
      status: row.status,
      selection: parseJson(row.selection_json, {}),
      result: parseJson(row.result_json, {}),
      createdBy: row.created_by,
      createdAt: row.created_at,
      completedAt: row.completed_at,
    }));
    return reply.send({ jobs });
  });

  /** get_material_import_jobs(): readable collaborators, latest 50. */
  app.get('/api/invitations/:id/materials/import-jobs', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) return reply.code(401).send(AUTH_REQUIRED);

    const inviteId = request.params.id;
    const role = await invitationRole(db, inviteId, user.id);
    if (role === null) return reply.code(404).send(INVITATION_NOT_FOUND);

    const rows = await db.query(
      'SELECT * FROM material_import_jobs WHERE invitation_id=? ORDER BY created_at DESC LIMIT 50',
      [inviteId],
    );
    const jobs = rows.rows.map((row) => ({
      id: row.id,
      sourceType: row.source_type,
      rootName: row.root_name,
      status: row.status,
      totalFiles: row.total_files,
      processedFiles: row.processed_files,
      failedFiles: row.failed_files,
      totalBytes: row.total_bytes,
      processedBytes: row.processed_bytes,
      failures: parseJson(row.failures_json, []),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      cancelledAt: row.cancelled_at,
    }));
    return reply.send({ jobs });
  });
}
