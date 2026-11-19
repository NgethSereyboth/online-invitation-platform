// S10: the invitation read cluster — the editor's first load:
//   GET /api/invitations/:id          (server.py get_invitation)
//   GET /api/invitations/:id/guests   (get_guests)
//   GET /api/invitations/:id/rsvps    (get_rsvps)
// All reads. Authorisation mirrors require_user/can_manage_invitation.
import {
  AUTH_REQUIRED,
  INVITATION_NOT_FOUND,
  MANAGEMENT_REQUIRED,
  canManageInvitation,
  canReadInvitation,
  currentUser,
  invitationRole,
  roleFromRow,
} from './authz.mjs';
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';
import { guestTokenValue, resolveGuestTokenSecret } from './public-document.mjs';

const INVITATION_ROW =
  'SELECT i.id,i.slug,i.draft_json,i.updated_at,i.archived,i.access_mode,i.is_published,i.owner_id,' +
  'i.last_client_id,i.last_mutation_id,i.custom_domain,i.publish_at,i.unpublish_at,i.expires_at,' +
  'i.gallery_access_password_hash,i.deleted_at,c.role collaborator_role ' +
  'FROM invitations i LEFT JOIN invitation_collaborators c ' +
  'ON c.invitation_id=i.id AND c.user_id=? WHERE i.id=?';

const GUEST_ROWS =
  'SELECT i.owner_id,i.deleted_at,' +
  '(SELECT role FROM invitation_collaborators c WHERE c.invitation_id=i.id AND c.user_id=?) collaborator_role,' +
  'g.id,g.name,g.slug,g.phone,g.email,g.group_name,g.household_id,g.tags_json,g.table_name,g.seat_label,' +
  'g.delivery_status,g.opened_at,g.token_salt,g.token_version,g.token_expires_at,g.token_revoked_at,' +
  'g.created_at,g.checked_in,g.checked_in_at ' +
  'FROM invitations i LEFT JOIN guests g ON g.invitation_id=i.id ' +
  'WHERE i.id=? ORDER BY g.created_at DESC';

const GUEST_RSVP_STATUSES =
  'SELECT lower(name) lookup_name,status FROM rsvps WHERE invitation_id=? ORDER BY created_at DESC';

const GUEST_ACCESS_COLUMNS = ['owner_id', 'deleted_at', 'collaborator_role'];

const SNAPSHOT_LIMIT = 50;

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

export function registerInvitationRoutes(app, { db, cipher, guestTokenSecret } = {}) {
  const secret = guestTokenSecret ?? resolveGuestTokenSecret();

  app.get('/api/invitations/:id', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) {
      reply.code(401);
      return AUTH_REQUIRED;
    }
    const found = await db.query(INVITATION_ROW, [user.id, request.params.id]);
    if (!found.rows.length) {
      reply.code(404);
      return INVITATION_NOT_FOUND;
    }
    const row = cipher ? cipher.revealRow(found.rows[0]) : found.rows[0];
    const role = roleFromRow(row, user.id);
    if (!role) {
      reply.code(404);
      return INVITATION_NOT_FOUND;
    }
    return {
      id: row.id,
      slug: row.slug,
      document: JSON.parse(row.draft_json),
      updatedAt: row.updated_at,
      archived: Boolean(row.archived),
      accessMode: row.access_mode || 'unlisted',
      published: Boolean(row.is_published),
      collaborationRole: role,
      owner: row.owner_id === user.id,
      lastClientId: row.last_client_id,
      lastMutationId: row.last_mutation_id,
      customDomain: row.custom_domain || '',
      publishAt: row.publish_at,
      unpublishAt: row.unpublish_at,
      expiresAt: row.expires_at,
      galleryProtected: Boolean(row.gallery_access_password_hash),
    };
  });

  app.get('/api/invitations/:id/guests', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) {
      reply.code(401);
      return AUTH_REQUIRED;
    }
    const found = await db.query(GUEST_ROWS, [user.id, request.params.id]);
    // _guest_page returns None for "no invitation" as well as "no permission",
    // so Python answers 403 in both cases — not 404.
    if (!found.rows.length) {
      reply.code(403);
      return MANAGEMENT_REQUIRED;
    }
    const rows = cipher ? found.rows.map((row) => cipher.revealRow(row)) : found.rows;
    if (!canManageInvitation(roleFromRow(rows[0], user.id))) {
      reply.code(403);
      return MANAGEMENT_REQUIRED;
    }
    if (rows[0].id === null || rows[0].id === undefined) return [];

    const statuses = await db.query(GUEST_RSVP_STATUSES, [request.params.id]);
    const latest = new Map();
    for (const row of statuses.rows) {
      if (!latest.has(row.lookup_name)) latest.set(row.lookup_name, row.status);
    }

    const now = Date.now();
    return rows.map((row) => {
      const item = { ...row };
      for (const key of GUEST_ACCESS_COLUMNS) delete item[key];
      item.rsvp_status = latest.get(String(row.name ?? '').toLowerCase()) ?? null;
      let token = null;
      if (
        item.token_salt &&
        !item.token_revoked_at &&
        (!item.token_expires_at || item.token_expires_at > now)
      ) {
        token = guestTokenValue(item.id, item.token_salt, item.token_version || 1, secret);
      }
      item.token = token;
      item.personalLinkAvailable = Boolean(token);
      item.tags = parseJson(item.tags_json ?? '[]', []);
      delete item.tags_json;
      return item;
    });
  });

  app.get('/api/trash', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) {
      reply.code(401);
      return AUTH_REQUIRED;
    }
    const rows = await db.query(
      'SELECT id,slug,draft_json,deleted_at,purge_at FROM invitations ' +
        'WHERE owner_id=? AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
      [user.id],
    );
    return rows.rows.map((raw) => {
      const row = cipher ? cipher.revealRow(raw) : raw;
      const document = parseJson(row.draft_json ?? '{}', {});
      return {
        id: row.id,
        slug: row.slug,
        title: document.fields?.names || 'Untitled invitation',
        deletedAt: row.deleted_at,
        purgeAt: row.purge_at,
      };
    });
  });

  // The version timeline merges publications with automatic snapshots. Both
  // kinds are reads; `list_versions` swallows its own failure in Python, so a
  // missing snapshot table degrades to "publications only" here as well.
  app.get('/api/invitations/:id/versions', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) {
      reply.code(401);
      return AUTH_REQUIRED;
    }
    if (!canReadInvitation(await invitationRole(db, request.params.id, user.id))) {
      reply.code(404);
      return INVITATION_NOT_FOUND;
    }
    const publications = await db.query(
      'SELECT id,version,published_at,length(document_json) document_bytes FROM publications ' +
        'WHERE invitation_id=? ORDER BY published_at DESC',
      [request.params.id],
    );
    let snapshots = [];
    try {
      const rows = await db.query(
        'SELECT * FROM invitation_versions WHERE invitation_id=? ORDER BY created_at DESC LIMIT ?',
        [request.params.id, SNAPSHOT_LIMIT],
      );
      snapshots = rows.rows.map((row) => ({
        id: row.id,
        authorName: row.author_name ?? '',
        createdAt: row.created_at,
      }));
    } catch {
      snapshots = [];
    }
    const timeline = publications.rows.map((row) => ({ ...row }));
    for (const snapshot of snapshots) {
      timeline.push({
        id: snapshot.id,
        version: 'auto',
        published_at: snapshot.createdAt,
        isAuto: true,
        authorName: snapshot.authorName,
      });
    }
    timeline.sort((left, right) => Number(right.published_at ?? 0) - Number(left.published_at ?? 0));
    return timeline;
  });

  app.get('/api/invitations/:id/versions/:version', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) {
      reply.code(401);
      return AUTH_REQUIRED;
    }
    if (!canReadInvitation(await invitationRole(db, request.params.id, user.id))) {
      reply.code(404);
      return INVITATION_NOT_FOUND;
    }
    const wanted = String(request.params.version);
    const published = await db.query(
      'SELECT id,version,published_at,document_json FROM publications ' +
        'WHERE invitation_id=? AND (id=? OR CAST(version AS TEXT)=?) ' +
        'ORDER BY published_at DESC LIMIT 1',
      [request.params.id, wanted, wanted],
    );
    if (published.rows.length) {
      const row = cipher ? cipher.revealRow(published.rows[0]) : published.rows[0];
      return {
        id: row.id,
        version: row.version,
        publishedAt: row.published_at,
        document: JSON.parse(row.document_json),
      };
    }
    const found = await db.query(
      'SELECT * FROM invitation_versions WHERE id=? AND invitation_id=?',
      [wanted, request.params.id],
    );
    if (!found.rows.length) {
      reply.code(404);
      return { error: 'Version not found' };
    }
    const snapshot = cipher ? cipher.revealRow(found.rows[0]) : found.rows[0];
    return {
      id: snapshot.id,
      version: 'auto',
      publishedAt: snapshot.created_at,
      isAuto: true,
      document: JSON.parse(snapshot.document_json),
    };
  });

  app.get('/api/invitations/:id/rsvps', async (request, reply) => {
    secure(reply, request);
    const user = await currentUser(db, request);
    if (!user) {
      reply.code(401);
      return AUTH_REQUIRED;
    }
    if (!canManageInvitation(await invitationRole(db, request.params.id, user.id))) {
      reply.code(403);
      return MANAGEMENT_REQUIRED;
    }
    const rows = await db.query('SELECT * FROM rsvps WHERE invitation_id=? ORDER BY created_at DESC', [
      request.params.id,
    ]);
    return rows.rows.map((raw) => {
      const item = cipher ? { ...cipher.revealRow(raw) } : { ...raw };
      item.answers = parseJson(item.answers_json ?? '{}', {});
      delete item.answers_json;
      return item;
    });
  });
}
