// S7: the public invitation read path (server.py `get_public`, routed from
// do_GET's `/api/public/` branch). Reads only, except the view counter and a
// guest's first-open stamp — both copied so behaviour matches on the wire and
// in the database.
import { randomUUID } from 'node:crypto';

import {
  applyGalleryAccess,
  mediaTtlSeconds,
  resolveSigningSecret,
  rewriteDocumentMediaUrls,
} from './media.mjs';
import { applyGuestBindings, guestTokenHash } from './public-document.mjs';
import { applySecurityHeaders, newNonce, PERMISSIONS_DEFAULT } from './headers.mjs';

const PUBLIC_LOOKUP =
  'SELECT i.id, i.access_mode, i.gallery_access_password_hash, i.gallery_access_password_salt, ' +
  'i.owner_id, i.sent_at, i.edited_after_send_at, p.id AS publication_id, p.version, ' +
  'p.document_json, u.studio_name, u.white_label_json ' +
  'FROM invitations i JOIN publications p ON p.invitation_id=i.id ' +
  'LEFT JOIN users u ON u.id=i.owner_id ' +
  'WHERE i.slug=? AND i.archived=0 AND i.deleted_at IS NULL AND i.is_published=1 ' +
  'AND (i.expires_at IS NULL OR i.expires_at>?) ' +
  'ORDER BY p.published_at DESC LIMIT 1';

function jsonString(value) {
  if (value === null || value === undefined) return '{}';
  return String(value);
}

function parseJsonObject(text) {
  try {
    const parsed = JSON.parse(jsonString(text));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function queryValue(value) {
  // parse_qs drops blank values; Python then sees None.
  return typeof value === 'string' && value !== '' ? value : null;
}

async function tokenValid(db, table, invitationId, token) {
  if (!token) return false;
  const now = Date.now();
  const tokenHash = guestTokenHash(token);
  const result = await db.query(
    `SELECT 1 FROM ${table} WHERE token_hash=? AND invitation_id=? AND expires_at>?`,
    [tokenHash, invitationId, now],
  );
  return result.rows.length > 0;
}

function studioBrand(row) {
  const white = parseJsonObject(row.white_label_json);
  return {
    name: row.studio_name ?? '',
    logo: white.logo ?? '',
    primaryColor: white.primaryColor ?? '',
    accentColor: white.accentColor ?? '',
    website: white.website ?? '',
    hidePlatformBrand: Boolean(white.hidePlatformBrand),
  };
}

export function registerPublicRoutes(app, { db, cipher, signingSecret } = {}) {
  const secret = signingSecret ?? resolveSigningSecret();

  app.get('/api/public/*', async (request, reply) => {
    applySecurityHeaders(reply, { nonce: newNonce(), permissions: PERMISSIONS_DEFAULT });
    reply.header('content-type', 'application/json; charset=utf-8');
    reply.header('cache-control', 'no-store');

    const rawPath = (request.raw.url ?? request.url).split('?')[0];
    const remainder = rawPath.slice('/api/public/'.length);
    let slug;
    try {
      slug = decodeURIComponent(remainder);
    } catch {
      slug = remainder;
    }

    const query = request.query ?? {};
    const guestToken =
      request.headers['x-invitation-guest'] || queryValue(query.guest) || queryValue(query.g);
    const accessToken = request.headers['x-invitation-access'] || queryValue(query.access);
    const galleryToken = request.headers['x-gallery-access'];

    const found = await db.query(PUBLIC_LOOKUP, [slug, Date.now()]);
    if (!found.rows.length) {
      reply.code(404);
      return { error: 'Published invitation not found' };
    }
    const row = cipher ? cipher.revealRow(found.rows[0]) : found.rows[0];

    if (row.access_mode === 'password') {
      if (!(await tokenValid(db, 'access_tokens', row.id, accessToken))) {
        reply.code(403);
        return { error: 'Password required', protected: true };
      }
    }

    const publicDocument = parseJsonObject(row.document_json);
    const privacy =
      publicDocument.privacy && typeof publicDocument.privacy === 'object' ? publicDocument.privacy : {};
    const analyticsConsentRequired = Boolean(privacy.analyticsConsentRequired);
    const externalMediaConsentRequired = Boolean(privacy.externalMediaConsentRequired);
    const galleryProtection =
      publicDocument.galleryProtection && typeof publicDocument.galleryProtection === 'object'
        ? publicDocument.galleryProtection
        : {};
    const galleryProtected = Boolean(row.gallery_access_password_hash && galleryProtection.enabled);
    const galleryAuthorized =
      !galleryProtected || (await tokenValid(db, 'gallery_access_tokens', row.id, galleryToken));

    if (!analyticsConsentRequired) {
      await db.query('UPDATE invitations SET views=views+1 WHERE id=?', [row.id]);
      await db.query('INSERT INTO view_events(id,invitation_id,publication_id,viewed_at) VALUES(?,?,?,?)', [
        randomUUID(),
        row.id,
        row.publication_id,
        Date.now(),
      ]);
    }

    let guest = null;
    if (guestToken) {
      const guestResult = await db.query(
        'SELECT id,name,group_name,household_id,table_name,seat_label FROM guests ' +
          'WHERE invitation_id=? AND token_hash=? AND token_revoked_at IS NULL ' +
          'AND (token_expires_at IS NULL OR token_expires_at>?)',
        [row.id, guestTokenHash(guestToken), Date.now()],
      );
      guest = guestResult.rows[0] ?? null;
      if (guest) {
        await db.query(
          "UPDATE guests SET opened_at=COALESCE(opened_at,?), " +
            "delivery_status=CASE WHEN delivery_status='sent' THEN 'opened' ELSE delivery_status END " +
            'WHERE id=?',
          [Date.now(), guest.id],
        );
      }
    }

    const ttlSeconds = mediaTtlSeconds();
    let document = applyGalleryAccess(publicDocument, row.id, galleryAuthorized, { secret, ttlSeconds });
    if (row.access_mode === 'password') {
      document = rewriteDocumentMediaUrls(document, row.id, { secret, ttlSeconds });
    }
    if (guest) document = applyGuestBindings(document, guest);

    return {
      invitationId: row.id,
      publicationId: row.publication_id,
      version: row.version,
      document,
      guest: guest ? { ...guest } : null,
      analyticsConsentRequired,
      externalMediaConsentRequired,
      galleryProtected,
      galleryAuthorized,
      studioBrand: studioBrand(row),
      sentAt: row.sent_at,
      editedAfterSendAt: row.edited_after_send_at,
    };
  });
}
