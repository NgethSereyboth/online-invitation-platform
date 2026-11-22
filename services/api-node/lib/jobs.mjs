// S12b: the lease a Node worker must hold before it runs a queued job.
//
// Python's queue claim is a compare-and-swap on state='queued', so a job cannot
// be claimed twice. What it lacks is an owner and an expiry: a worker that dies
// after flipping the row to 'running' leaves it there until the 30-minute
// cleanup sweep. This module adds both without changing the claim's atomicity:
//
//   * one statement selects the oldest eligible row with FOR UPDATE SKIP LOCKED
//     and updates it, so concurrent claimers — Python, Node, or both — resolve
//     to exactly one winner;
//   * the winner records `lock_owner` and `lease_expires_at`; renewal and
//     release only succeed while its owner still holds a running row;
//   * a running row is stale when its Node lease expired (expiry before now
//     and a heartbeat no newer than the expiry) or when it has not been
//     touched for Python's own 30-minute stale window. Python claims leave the
//     previous Node lease fields behind, so a freshly claimed Python row has a
//     locked_at newer than its lease_expires_at and is not treated as stale.
export const DEFAULT_LEASE_MS = 5 * 60 * 1000;

/** Matches cleanup_expired_security_rows()' 30-minute stale sweep. */
export const LEGACY_LEASE_MS = 30 * 60 * 1000;

const RELEASE_STATES = new Set(['done', 'queued', 'failed']);

const schemaReady = new WeakSet();
const platformSchemaReady = new WeakSet();

/** Adds the lease columns to a database booted by an older build. */
export async function ensureJobLeaseSchema(db) {
  if (schemaReady.has(db)) return;
  await db.query("ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS lock_owner TEXT NOT NULL DEFAULT ''");
  await db.query('ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS lease_expires_at BIGINT');
  schemaReady.add(db);
}

/** Same columns for the platform_jobs queue used by platform_v32/jobs.py. */
export async function ensurePlatformJobLeaseSchema(db) {
  if (platformSchemaReady.has(db)) return;
  await db.query("ALTER TABLE platform_jobs ADD COLUMN IF NOT EXISTS lock_owner TEXT NOT NULL DEFAULT ''");
  await db.query('ALTER TABLE platform_jobs ADD COLUMN IF NOT EXISTS lease_expires_at BIGINT');
  platformSchemaReady.add(db);
}

function parsePayload(value) {
  try {
    return JSON.parse(value || '{}');
  } catch {
    return {};
  }
}

/**
 * Claims the oldest eligible job, or null when none is due.
 *
 * Eligible means queued and due, or running with an expired lease. A running
 * row with no owner is Python's and only becomes eligible at the legacy cutoff.
 */
export async function claimJob(
  db,
  { workerId, leaseMs = DEFAULT_LEASE_MS, kinds = null, now = Date.now() } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (!Number.isFinite(leaseMs) || leaseMs <= 0) throw new TypeError('leaseMs must be a positive number');
  await ensureJobLeaseSchema(db);

  const params = [now, now, now - LEGACY_LEASE_MS];
  let kindClause = '';
  if (Array.isArray(kinds) && kinds.length) {
    kindClause = ` AND kind IN (${kinds.map(() => '?').join(',')})`;
    params.push(...kinds);
  }
  const leaseExpiresAt = now + leaseMs;
  params.push(workerId, now, leaseExpiresAt, now);

  const row = (
    await db.query(
      'WITH candidate AS (' +
        'SELECT id FROM background_jobs ' +
        'WHERE ((state=\'queued\' AND available_at<=?) ' +
        'OR (state=\'running\' AND ((COALESCE(lease_expires_at,0)<=? ' +
        'AND COALESCE(locked_at,0)<=COALESCE(lease_expires_at,0)) ' +
        'OR COALESCE(locked_at,0)<=?)))' +
        `${kindClause} ` +
        'ORDER BY created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED' +
        ') ' +
        'UPDATE background_jobs j SET state=\'running\', lock_owner=?, locked_at=?, lease_expires_at=?, ' +
        'attempts=attempts+1, updated_at=? FROM candidate c WHERE j.id=c.id ' +
        'RETURNING j.id,j.kind,j.payload_json,j.attempts,j.created_at,j.updated_at',
      params,
    )
  ).rows[0];
  if (!row) return null;
  return {
    id: row.id,
    kind: row.kind,
    payload: parsePayload(row.payload_json),
    attempts: Number(row.attempts),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    leaseExpiresAt,
  };
}

/** Heartbeats a running job. false means the lease was lost. */
export async function renewJobLease(
  db,
  { jobId, workerId, leaseMs = DEFAULT_LEASE_MS, now = Date.now() } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (!Number.isFinite(leaseMs) || leaseMs <= 0) throw new TypeError('leaseMs must be a positive number');
  const result = await db.query(
    'UPDATE background_jobs SET locked_at=?, lease_expires_at=?, updated_at=? ' +
      "WHERE id=? AND state='running' AND lock_owner=?",
    [now, now + leaseMs, now, jobId, workerId],
  );
  return result.rowCount > 0;
}

/**
 * Releases a job the caller still owns. `queued` also needs `availableAt` for
 * the retry delay; `failed` is final.
 */
/**
 * Claims a platform_jobs row, or null when none is due.
 *
 * Python's JobQueue sets `claimed` then `running` without an owner. Node goes
 * straight to `running`; a running row with no owner is Python's and only
 * becomes eligible after a 30-minute no-touch window.
 */
export async function claimPlatformJob(
  db,
  { workerId, leaseMs = DEFAULT_LEASE_MS, kinds = null, now = Date.now() } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (!Number.isFinite(leaseMs) || leaseMs <= 0) throw new TypeError('leaseMs must be a positive number');
  await ensurePlatformJobLeaseSchema(db);

  const params = [now, now - LEGACY_LEASE_MS];
  let kindClause = '';
  if (Array.isArray(kinds) && kinds.length) {
    kindClause = ` AND kind IN (${kinds.map(() => '?').join(',')})`;
    params.push(...kinds);
  }
  const leaseExpiresAt = now + leaseMs;
  params.push(now, workerId, leaseExpiresAt, now);

  const row = (
    await db.query(
      'WITH candidate AS (' +
        "SELECT id FROM platform_jobs WHERE cancellation_requested=0 AND (status='queued' " +
        "OR (status IN ('claimed','running') AND ((lock_owner<>'' AND COALESCE(lease_expires_at,0)<=?) " +
        "OR (lock_owner='' AND COALESCE(updated_at,0)<=?))))" +
        `${kindClause} ` +
        'ORDER BY created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED' +
        ') ' +
        "UPDATE platform_jobs j SET status='running', started_at=COALESCE(started_at,?), " +
        'lock_owner=?, lease_expires_at=?, updated_at=? FROM candidate c WHERE j.id=c.id ' +
        'RETURNING j.id,j.kind,j.payload_json,j.retry_count,j.created_at,j.updated_at',
      params,
    )
  ).rows[0];
  if (!row) return null;
  return {
    id: row.id,
    kind: row.kind,
    payload: parsePayload(row.payload_json),
    retryCount: Number(row.retry_count),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    leaseExpiresAt,
  };
}

/** Heartbeats a platform job. false means the lease was lost. */
export async function renewPlatformJobLease(
  db,
  { jobId, workerId, leaseMs = DEFAULT_LEASE_MS, now = Date.now() } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  const result = await db.query(
    'UPDATE platform_jobs SET lease_expires_at=?, updated_at=? ' +
      "WHERE id=? AND status='running' AND lock_owner=?",
    [now + leaseMs, now, jobId, workerId],
  );
  return result.rowCount > 0;
}

const PLATFORM_RELEASE_STATES = new Set(['completed', 'failed', 'queued', 'cancelled']);

/** Releases a platform job the caller still owns. */
export async function releasePlatformJob(
  db,
  { jobId, workerId, state = 'completed', result = {}, error = '', now = Date.now() } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (!PLATFORM_RELEASE_STATES.has(state)) throw new TypeError(`unsupported release state: ${state}`);
  const completedAt = state === 'queued' ? null : now;
  const released = await db.query(
    'UPDATE platform_jobs SET status=?, progress=?, result_json=?, error_text=?, ' +
      "completed_at=?, updated_at=?, lock_owner='', lease_expires_at=NULL " +
      "WHERE id=? AND status='running' AND lock_owner=?",
    [
      state,
      state === 'completed' ? 1 : 0,
      JSON.stringify(result ?? {}).slice(0, 1_000_000),
      String(error ?? '').slice(0, 2000),
      completedAt,
      now,
      jobId,
      workerId,
    ],
  );
  return released.rowCount > 0;
}

export async function releaseJob(
  db,
  { jobId, workerId, state = 'done', error = '', availableAt = null, now = Date.now() } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (!RELEASE_STATES.has(state)) throw new TypeError(`unsupported release state: ${state}`);
  const result = await db.query(
    'UPDATE background_jobs SET state=?, last_error=?, available_at=COALESCE(?, available_at), ' +
      "lock_owner='', locked_at=NULL, lease_expires_at=NULL, updated_at=? " +
      "WHERE id=? AND state='running' AND lock_owner=?",
    [state, String(error ?? '').slice(0, 2000), availableAt, now, jobId, workerId],
  );
  return result.rowCount > 0;
}
