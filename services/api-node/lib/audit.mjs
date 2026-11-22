// The audit hash chain, copied from server.py's write_audit_event(). A read
// route needs it because admin_users_v2?unmask=1 records who unmasked what;
// skipping that would make the Node backend the one place an admin action
// leaves no trace.
import { createHash, randomUUID } from 'node:crypto';

/** json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False). */
export function canonicalJson(value) {
  if (value === null) return 'null';
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (typeof value === 'object') {
    const keys = Object.keys(value).sort();
    return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

/**
 * Appends one chained event. `adminRoute` mirrors audit()'s stamp: every event
 * written while serving /api/admin/* carries {"admin":true}, which is also the
 * bit the adminOnly filter reads from the indexed column.
 */
export async function writeAuditEvent(
  db,
  {
    cipher = null,
    userId = null,
    action,
    targetType = '',
    targetId = '',
    metadata = null,
    ipAddress = 'system',
    adminRoute = false,
  } = {},
) {
  const enriched = { ...(metadata ?? {}) };
  if (adminRoute) enriched.admin = true;
  const meta = [...canonicalJson(enriched)].slice(0, 20000).join('');

  const now = Date.now();
  const previous = (
    await db.query('SELECT event_hash FROM audit_events ORDER BY created_at DESC,id DESC LIMIT 1')
  ).rows[0];
  const previousHash = previous?.event_hash ?? '';
  const eventId = randomUUID();
  const payload = `${eventId}|${userId ?? ''}|${action}|${targetType}|${targetId}|${meta}|${String(ipAddress).slice(0, 80)}|${previousHash}|${now}`;
  const eventHash = createHash('sha256').update(payload, 'utf8').digest('hex');
  const adminOnly = meta.includes('"admin":true') ? 1 : 0;
  const stored = cipher ? cipher.protect(meta) : meta;
  await db.query(
    'INSERT INTO audit_events(id,user_id,action,target_type,target_id,metadata_json,ip_address,previous_hash,event_hash,created_at,admin_only) ' +
      'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
    [eventId, userId, action, targetType, targetId, stored, String(ipAddress).slice(0, 80), previousHash, eventHash, now, adminOnly],
  );
  return eventId;
}
