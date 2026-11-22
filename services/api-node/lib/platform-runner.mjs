// S12b: the Node port of platform_v32's JobQueue runner for the one kind whose
// handler needs no Python-only library.
//
// JobQueue._run() moves a row claimed -> running (a compare-and-swap, so a
// duplicate queue entry or a row another backend owns is not executed twice),
// invokes the handler with `progress` and `cancelled`, then finishes it:
// `completed` with a compact result, `queued` with retry_count+1 while retries
// remain, or `failed` / `cancelled`. This module keeps that lifecycle and adds
// the S12b lease, so exactly one backend owns the row for the run.
//
// Only `media-ingest` is portable today — Python's handler is
//   progress(.5); return {'status':'provider-hook-ready','assetId':…}
// with no dependency beyond the payload. The other registered kinds stay
// Python's, and are never claimed here:
//   * workspace-backup / workspace-restore — zipfile and the Python document model;
//   * raster-render — Pillow edits plus an object-storage write;
//   * privacy-export — the Python account-export builders;
//   * bulk-personalize — fingerprints each row with Python's JSON rendition,
//     which cannot distinguish `1` from `1.0` after a JavaScript parse.
import { DEFAULT_LEASE_MS, claimPlatformJob } from './jobs.mjs';

export const PLATFORM_RESULT_MAX_CHARS = 1_000_000;
export const PLATFORM_RETRY_ERROR_MAX_CHARS = 1_000;
export const PLATFORM_FINAL_ERROR_MAX_CHARS = 2_000;

function parsePayload(value) {
  try {
    const parsed = JSON.parse(value || '{}');
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

/** Python's json.dumps(result, ensure_ascii=False, separators=(",", ":")). */
function compactJson(value) {
  return JSON.stringify(value === undefined ? {} : value);
}

function errorText(failure) {
  return String(failure instanceof Error ? failure.message : failure);
}

/**
 * media-ingest: Python's `_media_job`. It is a provider hook, so the whole
 * handler is the progress marker and the echoed asset id. `payload.get(k, "")`
 * keeps an explicit null, which Object.hasOwn reproduces.
 */
export async function mediaIngestJob(payload, { progress } = {}) {
  await progress?.(0.5);
  const body = payload ?? {};
  return {
    status: 'provider-hook-ready',
    assetId: Object.hasOwn(body, 'assetId') ? body.assetId : '',
  };
}

export const PLATFORM_HANDLERS = Object.freeze({
  'media-ingest': mediaIngestJob,
});

/** Python's _finish(), with the lease released and the owner checked. */
async function finishPlatformJob(db, { jobId, workerId, status, result, error, now }) {
  const resultJson = compactJson(result).slice(0, PLATFORM_RESULT_MAX_CHARS);
  await db.query(
    'UPDATE platform_jobs SET status=?, progress=?, result_json=?, error_text=?, completed_at=?, ' +
      "updated_at=?, lock_owner='', lease_expires_at=NULL WHERE id=? AND status='running' AND lock_owner=?",
    [
      status,
      status === 'completed' ? 1 : 0,
      resultJson,
      String(error ?? '').slice(0, PLATFORM_FINAL_ERROR_MAX_CHARS),
      now,
      now,
      jobId,
      workerId,
    ],
  );
}

/**
 * Run up to `limit` due platform jobs whose kind this module implements.
 *
 * Handlers receive Python's `(payload, progress, cancelled)` contract. A
 * failure requeues while `retry_count+1 <= max_retries`, otherwise the row is
 * final. `progress` and `started_at` are left untouched on a retry, exactly as
 * `JobQueue._run()` leaves them.
 */
export async function processPlatformJobs(
  db,
  {
    limit = 25,
    nowMs,
    workerId,
    leaseMs = DEFAULT_LEASE_MS,
    handlers = PLATFORM_HANDLERS,
    claim = claimPlatformJob,
    logger = null,
  } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  const kinds = Object.keys(handlers);
  if (!kinds.length) return 0;
  const clock = () => (nowMs === undefined ? Date.now() : nowMs);
  let processed = 0;
  for (let index = 0; index < Math.max(0, Number(limit) || 0); index += 1) {
    const now = clock();
    const job = await claim(db, { workerId, leaseMs, kinds, now });
    if (!job) break;
    const row = (
      await db.query(
        'SELECT kind,payload_json,retry_count,max_retries FROM platform_jobs ' +
          "WHERE id=? AND status='running' AND lock_owner=?",
        [job.id, workerId],
      )
    ).rows[0];
    if (!row) continue;
    const handler = handlers[row.kind] ?? handlers[job.kind];
    if (!handler) {
      // Python fails a row whose kind has no handler; do the same rather than
      // leaving it running under this lease.
      await finishPlatformJob(db, {
        jobId: job.id,
        workerId,
        status: 'failed',
        result: {},
        error: `No handler registered for ${row.kind}`,
        now: clock(),
      });
      processed += 1;
      continue;
    }

    const cancelled = async () => {
      const current = (
        await db.query('SELECT cancellation_requested,status FROM platform_jobs WHERE id=?', [job.id])
      ).rows[0];
      return !current || Boolean(Number(current.cancellation_requested)) || current.status === 'cancelled';
    };
    // Python's _progress() is synchronous: a non-numeric value raises before
    // anything is written, so validate here and let the handler await the write.
    const progress = (value) => {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) throw new TypeError('progress must be a number');
      return db.query(
        "UPDATE platform_jobs SET progress=?, updated_at=? WHERE id=? AND status='running' AND lock_owner=?",
        [Math.max(0, Math.min(1, numeric)), clock(), job.id, workerId],
      );
    };

    let ok = true;
    let error = '';
    try {
      const payload = parsePayload(row.payload_json);
      const result = await handler(payload, { progress, cancelled });
      await finishPlatformJob(db, {
        jobId: job.id,
        workerId,
        status: 'completed',
        result: result ?? {},
        error: '',
        now: clock(),
      });
    } catch (failure) {
      ok = false;
      error = errorText(failure);
      const retryCount = Number(row.retry_count) + 1;
      const exhausted = retryCount > Number(row.max_retries);
      const wasCancelled = await cancelled();
      if (!exhausted && !wasCancelled) {
        await db.query(
          "UPDATE platform_jobs SET status='queued', retry_count=?, error_text=?, updated_at=?, " +
            "lock_owner='', lease_expires_at=NULL WHERE id=? AND status='running' AND lock_owner=?",
          [
            retryCount,
            error.slice(0, PLATFORM_RETRY_ERROR_MAX_CHARS),
            clock(),
            job.id,
            workerId,
          ],
        );
      } else {
        await finishPlatformJob(db, {
          jobId: job.id,
          workerId,
          status: wasCancelled ? 'cancelled' : 'failed',
          result: {},
          error,
          now: clock(),
        });
      }
    }
    processed += 1;
    if (logger) {
      logger({
        level: ok ? 'info' : 'warning',
        event: 'platform_job',
        kind: row.kind,
        attempts: Number(row.retry_count) + 1,
        ok,
        error: error || null,
        jobId: job.id,
      });
    }
  }
  return processed;
}
