// Admin console reads, copied from server.py's admin_* handlers. Every query
// is fixed SQL with bound parameters; the only assembled fragment is a WHERE
// built from literal clause strings, as in Python.
import { createHash } from 'node:crypto';

import { pythonLower, pythonStrip } from './pystr.mjs';

/** Python int(): optional sign, surrounding whitespace, no decimal point. */
export function pyInt(value) {
  const text = pythonStrip(value);
  return /^[+-]?\d+$/.test(text) ? Number.parseInt(text, 10) : null;
}

/** Python's s[:n] counts code points, not UTF-16 units. */
export function pySlice(value, length) {
  return [...String(value)].slice(0, length).join('');
}

/** Python truthiness for the few JSON values these reads pass through. */
export function pyTruthy(value) {
  if (value === null || value === undefined || value === false || value === 0 || value === '') return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value).length > 0;
  return true;
}

/** _mask_email(): first code point + ***@domain; "***" without an @. */
export function maskEmail(email) {
  const text = email === null || email === undefined ? '' : String(email);
  const at = text.indexOf('@');
  if (at === -1) return '***';
  const local = text.slice(0, at);
  const domain = text.slice(at + 1);
  return `${[...local].slice(0, 1).join('')}***@${domain}`;
}

/** core.crypto.hash_for_lookup(): sha256(lower(strip(text))) as hex. */
export function hashForLookup(value) {
  if (value === null || value === undefined) return null;
  if (value === '') return '';
  return createHash('sha256').update(pythonLower(pythonStrip(value)), 'utf8').digest('hex');
}

/** admin_overview(): seven counts, in Python's key order. */
export async function adminOverview(db) {
  const count = async (sql) => Number((await db.query(sql)).rows[0].c);
  return {
    users: await count('SELECT COUNT(*) c FROM users'),
    invitations: await count('SELECT COUNT(*) c FROM invitations'),
    publishedInvitations: await count('SELECT COUNT(*) c FROM invitations WHERE is_published=1'),
    templates: await count('SELECT COUNT(*) c FROM user_templates'),
    marketplaceTemplates: await count(
      "SELECT COUNT(*) c FROM user_templates WHERE visibility='public' AND marketplace_status='approved'",
    ),
    rsvps: await count('SELECT COUNT(*) c FROM rsvps'),
    assets: await count('SELECT COUNT(*) c FROM assets'),
  };
}

/** admin_users(): the legacy 1000-row array with revealed addresses. */
export async function listAdminUsers(db, reveal = (value) => value) {
  const rows = (
    await db.query(
      'SELECT u.id,u.email,u.role,u.plan,u.upload_enabled,u.created_at,u.suspended_at,' +
        '(SELECT COUNT(*) FROM invitations i WHERE i.owner_id=u.id) invitation_count,' +
        '(SELECT COUNT(*) FROM user_templates t WHERE t.owner_id=u.id) template_count ' +
        'FROM users u ORDER BY u.created_at DESC LIMIT 1000',
    )
  ).rows;
  return rows.map((row) => ({
    id: row.id,
    email: reveal(row.email),
    role: row.role,
    plan: row.plan,
    uploadEnabled: Boolean(row.upload_enabled),
    createdAt: row.created_at,
    suspended: row.suspended_at !== null,
    invitationCount: Number(row.invitation_count),
    templateCount: Number(row.template_count),
  }));
}

/**
 * admin_users_v2(): masked by default, searchable by exact address through
 * email_hash, cursor on (created_at, id) descending.
 */
export async function listAdminUsersPage(db, { limit = 25, unmask = false, search = '', cursor = null } = {}, reveal = (value) => value) {
  const clauses = [];
  const params = [];
  if (search) {
    clauses.push('(LOWER(u.email) LIKE ? OR u.email_hash = ?)');
    params.push(`%${search}%`, hashForLookup(search));
  }
  if (cursor) {
    clauses.push('(u.created_at < ? OR (u.created_at = ? AND u.id < ?))');
    params.push(cursor.created, cursor.created, cursor.id);
  }
  const where = clauses.length ? ` WHERE ${clauses.join(' AND ')}` : '';
  const rows = (
    await db.query(
      'SELECT u.id,u.email,u.role,u.plan,u.upload_enabled,u.created_at,u.suspended_at,u.force_mfa,' +
        '(SELECT COUNT(*) FROM invitations i WHERE i.owner_id=u.id) invitation_count,' +
        '(SELECT COUNT(*) FROM user_templates t WHERE t.owner_id=u.id) template_count ' +
        `FROM users u${where} ORDER BY u.created_at DESC, u.id DESC LIMIT ?`,
      [...params, limit + 1],
    )
  ).rows;
  const hasMore = rows.length > limit;
  const page = rows.slice(0, limit);
  const items = page.map((row) => ({
    id: row.id,
    email: unmask ? reveal(row.email) : maskEmail(reveal(row.email)),
    role: row.role,
    plan: row.plan,
    uploadEnabled: Boolean(row.upload_enabled),
    createdAt: row.created_at,
    suspended: row.suspended_at !== null,
    forceMfa: Boolean(row.force_mfa),
    invitationCount: Number(row.invitation_count),
    templateCount: Number(row.template_count),
  }));
  const nextCursor = hasMore ? `${page[page.length - 1].created_at}:${page[page.length - 1].id}` : null;
  return { items, nextCursor, hasMore };
}

/** admin_invitations(): newest first; the title is the draft's names field. */
export async function listAdminInvitations(db, reveal = (value) => value) {
  const rows = (
    await db.query(
      'SELECT i.id,i.slug,i.updated_at,i.archived,i.views,i.access_mode,i.is_published,u.email owner_email,i.draft_json ' +
        'FROM invitations i LEFT JOIN users u ON u.id=i.owner_id ORDER BY i.updated_at DESC LIMIT 1000',
    )
  ).rows;
  return rows.map((row) => {
    let title = 'Untitled invitation';
    try {
      const document = JSON.parse(row.draft_json);
      const names = document && typeof document === 'object' && !Array.isArray(document) ? document.fields : undefined;
      const value = names && typeof names === 'object' ? names.names : undefined;
      if (pyTruthy(value)) title = value;
    } catch {
      /* Python swallows a malformed draft and uses the fallback title */
    }
    return {
      id: row.id,
      slug: row.slug,
      title,
      ownerEmail: reveal(row.owner_email),
      published: Boolean(row.is_published),
      archived: Boolean(row.archived),
      views: row.views,
      accessMode: row.access_mode,
      updatedAt: row.updated_at,
    };
  });
}

/** admin_audit_events(): filtered newest-first page plus the raw rows for CSV. */
export async function listAuditEvents(db, filters = {}, reveal = (value) => value) {
  const clauses = [];
  const params = [];
  for (const [field, column] of [
    ['user', 'user_id'],
    ['action', 'action'],
    ['targetType', 'target_type'],
    ['targetId', 'target_id'],
  ]) {
    const value = pythonStrip(filters[field] ?? '');
    if (value) {
      clauses.push(`${column}=?`);
      params.push(pySlice(value, 200));
    }
  }
  const ip = pythonStrip(filters.ip ?? '');
  if (ip) {
    clauses.push('ip_address=?');
    params.push(pySlice(ip, 80));
  }
  if (filters.adminOnly === '1') {
    // The metadata is encrypted at rest, so the indexed flag carries the bit;
    // the LIKE still covers rows written before the flag existed.
    clauses.push('(metadata_json LIKE ? OR admin_only=1)');
    params.push('%"admin":true%');
  }
  for (const [name, operator] of [
    ['from', '>='],
    ['to', '<='],
  ]) {
    const raw = pythonStrip(filters[name] ?? '');
    if (!raw) continue;
    const timestamp = auditFilterTimestamp(raw);
    if (timestamp === null) return null;
    clauses.push(`created_at${operator}?`);
    params.push(timestamp);
  }
  const where = clauses.length ? ` WHERE ${clauses.join(' AND ')}` : '';
  const rows = (
    await db.query(
      'SELECT id,user_id,action,target_type,target_id,metadata_json,ip_address,created_at ' +
        `FROM audit_events${where} ORDER BY created_at DESC,id DESC LIMIT ?`,
      [...params, filters.limit],
    )
  ).rows;
  const items = rows.map((row) => {
    let metadata = {};
    try {
      metadata = JSON.parse(reveal(row.metadata_json) || '{}');
    } catch {
      metadata = {};
    }
    return {
      id: row.id,
      userId: row.user_id,
      action: row.action,
      targetType: row.target_type,
      targetId: row.target_id,
      metadata,
      ipAddress: row.ip_address,
      createdAt: row.created_at,
    };
  });
  return { items, rows: rows.map((row) => ({ ...row, metadata_json: reveal(row.metadata_json) })) };
}

/**
 * The from/to parser: digits are epoch milliseconds, anything else is a
 * %Y-%m-%d date read in local time (time.mktime, as Python does). null means
 * Python's ValueError.
 */
export function auditFilterTimestamp(raw) {
  const text = String(raw);
  if (/^\d+$/.test(text)) return Number.parseInt(text, 10);
  const match = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(text);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(0);
  date.setFullYear(year, month - 1, day);
  date.setHours(0, 0, 0, 0);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
  return date.getTime();
}

function csvField(value) {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** csv.writer's excel dialect: minimal quoting and CRLF row endings. */
export function auditEventsCsv(rows) {
  const header = ['id', 'timestamp_iso', 'user_id', 'action', 'target_type', 'target_id', 'ip_address', 'metadata'];
  const lines = [header.map(csvField).join(',')];
  for (const row of rows) {
    lines.push(
      [
        row.id,
        new Date(Number(row.created_at)).toISOString().slice(0, 19) + 'Z',
        row.user_id || '',
        row.action,
        row.target_type,
        row.target_id,
        row.ip_address,
        row.metadata_json,
      ]
        .map(csvField)
        .join(','),
    );
  }
  return `${lines.join('\r\n')}\r\n`;
}

/** admin_job_status(): one queue row, 404 when absent. */
export async function getAdminJob(db, jobId) {
  const row = (
    await db.query(
      'SELECT id,kind,payload_json,state,attempts,last_error,created_at,updated_at ' +
        'FROM background_jobs WHERE id=?',
      [jobId],
    )
  ).rows[0];
  if (!row) return null;
  let payload = {};
  try {
    payload = JSON.parse(row.payload_json || '{}');
  } catch {
    payload = {};
  }
  return {
    id: row.id,
    kind: row.kind,
    state: row.state,
    payload,
    attempts: Number(row.attempts),
    lastError: row.last_error,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}
