// Reports queue read model (features/reports.py). Python creates the table on
// first use with idempotent CREATE TABLE IF NOT EXISTS, so the Node side runs
// the same statements once rather than assuming a migration has happened.
const SCHEMA_STATEMENTS = [
  `CREATE TABLE IF NOT EXISTS reports(
  id TEXT PRIMARY KEY,
  reporter_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open',
  resolved_by TEXT,
  resolved_at BIGINT,
  resolution_note TEXT NOT NULL DEFAULT '',
  created_at BIGINT NOT NULL
)`,
  'CREATE INDEX IF NOT EXISTS idx_reports_status_created ON reports(status,created_at DESC)',
  'CREATE INDEX IF NOT EXISTS idx_reports_target ON reports(target_type,target_id,created_at DESC)',
  'CREATE INDEX IF NOT EXISTS idx_reports_reporter ON reports(reporter_id,created_at DESC)',
];

export const STATUS_VALUES = [
  'open',
  'investigating',
  'resolved_actioned',
  'resolved_no_action',
  'duplicate',
];

let schemaReady = false;

export async function ensureReportsSchema(db) {
  if (schemaReady) return;
  for (const statement of SCHEMA_STATEMENTS) await db.query(statement);
  // Epoch-ms timestamps do not fit PostgreSQL INTEGER; widen a table created
  // by an older build. A no-op when the declaration above already won.
  for (const column of ['created_at', 'resolved_at']) {
    try {
      await db.query(`ALTER TABLE reports ALTER COLUMN ${column} TYPE BIGINT`);
    } catch {
      // Column absent on a table this build did not create — same swallow as
      // Python's on-first-use schema path.
    }
  }
  schemaReady = true;
}

function rowToDict(row) {
  return {
    id: row.id,
    reporterId: row.reporter_id,
    targetType: row.target_type,
    targetId: row.target_id,
    reason: row.reason,
    body: row.body,
    status: row.status,
    resolvedBy: row.resolved_by || '',
    resolvedAt: row.resolved_at,
    resolutionNote: row.resolution_note || '',
    createdAt: row.created_at,
  };
}

/** list_reports(): newest first, cursor on created_at strictly below it. */
export async function listReports(db, { status = null, targetType = null, limit = 100, cursor = null } = {}) {
  const capped = Math.max(1, Math.min(Number(limit) || 100, 200));
  const params = [];
  const clauses = [];
  if (status) {
    clauses.push('status=?');
    params.push(status);
  }
  if (targetType) {
    clauses.push('target_type=?');
    params.push(targetType);
  }
  if (cursor) {
    clauses.push('created_at<?');
    params.push(Number(cursor));
  }
  const where = clauses.length ? ` WHERE ${clauses.join(' AND ')}` : '';
  params.push(capped);
  const rows = await db.query(
    'SELECT id,reporter_id,target_type,target_id,reason,body,status,resolved_by,resolved_at,resolution_note,created_at ' +
      `FROM reports${where} ORDER BY created_at DESC LIMIT ?`,
    params,
  );
  const items = rows.rows.map(rowToDict);
  const nextCursor = items.length >= capped ? items[items.length - 1].createdAt : null;
  return { items, nextCursor };
}
