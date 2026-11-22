// S12b/S12c: the Node port of server.process_webhook_jobs() and the local-disk
// half of server.process_storage_delete_jobs().
//
// One due job is claimed through the S12b lease and processed exactly once.
// `webhook.deliver` keeps Python's 1/2/4/8 s retry schedule; `storage.delete`
// removes the upload and its derivative-cache entries, with Python's 30 s
// doubling backoff and no terminal failure. Python owns the queue's schema and
// endpoint encryption; this module only consumes them. Object-storage deletion
// remains Python's until S12c ports the bucket client.
import { createHash, createHmac } from 'node:crypto';
import { lookup as dnsLookup } from 'node:dns/promises';
import { existsSync, unlinkSync } from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import { join, resolve } from 'node:path';

import { DEFAULT_LEASE_MS, claimJob, releaseJob } from './jobs.mjs';

export const RETRYABLE_STATUSES = new Set([408, 409, 425, 429, 500, 502, 503, 504]);
export const QUEUE_BACKOFF_BASE_S = 1.0;
export const QUEUE_MAX_ATTEMPTS = 5;
export const MAX_BACKOFF_S = 30.0;
export const DEFAULT_TIMEOUT_MS = 5000;
export const MAX_RESPONSE_BYTES = 64 * 1024;
export const SIGNATURE_HEADER = 'X-EInvite-Signature';
export const TIMESTAMP_HEADER = 'X-EInvite-Timestamp';
export const IMAGE_WIDTH_ALLOWLIST = Object.freeze([320, 480, 768, 960, 1440, 1920]);
export const DERIVATIVE_FORMATS = Object.freeze([
  ['webp', '.webp'],
  ['jpeg', '.jpg'],
  ['jpg', '.jpg'],
  ['png', '.png'],
  ['avif', '.avif'],
]);
export const STORAGE_DELETE_BACKOFF_BASE_S = 30.0;
export const STORAGE_DELETE_BACKOFF_MAX_S = 3600.0;

const BLOCKED_ADDRESSES = new net.BlockList();
for (const [address, prefix] of [
  ['0.0.0.0', 8],
  ['10.0.0.0', 8],
  ['127.0.0.0', 8],
  ['169.254.0.0', 16],
  ['172.16.0.0', 12],
  ['192.0.0.0', 24],
  ['192.0.2.0', 24],
  ['192.168.0.0', 16],
  ['198.18.0.0', 15],
  ['198.51.100.0', 24],
  ['203.0.113.0', 24],
  ['224.0.0.0', 4],
  ['240.0.0.0', 4],
]) {
  BLOCKED_ADDRESSES.addSubnet(address, prefix, 'ipv4');
}
for (const [address, prefix] of [
  ['::', 128],
  ['::1', 128],
  ['2001:db8::', 32],
  ['fc00::', 7],
  ['fe80::', 10],
  ['ff00::', 8],
]) {
  BLOCKED_ADDRESSES.addSubnet(address, prefix, 'ipv6');
}

function pythonTimestamp(nowMs) {
  return Math.trunc(Number(nowMs));
}

/** core.webhooks.sign_webhook(): t=<ms>,v1=hex(HMAC-SHA256(secret, "<ms>." + body)). */
export function signWebhook(body, secret, timestampMs = Date.now()) {
  if (typeof secret !== 'string' || !secret) throw new Error('webhook secret must be non-empty');
  const payload = Buffer.concat([Buffer.from(`${pythonTimestamp(timestampMs)}.`, 'ascii'), Buffer.from(body)]);
  const digest = createHmac('sha256', secret).update(payload).digest('hex');
  return `t=${pythonTimestamp(timestampMs)},v1=${digest}`;
}

export function buildWebhookHeaders(body, secret, timestampMs = Date.now()) {
  const timestamp = pythonTimestamp(timestampMs);
  return {
    'Content-Type': 'application/json',
    [SIGNATURE_HEADER]: signWebhook(body, secret, timestamp),
    [TIMESTAMP_HEADER]: String(timestamp),
  };
}

function isPublicAddress(address) {
  const family = net.isIP(address);
  if (!family) return false;
  if (family === 6 && address.toLowerCase().startsWith('::ffff:')) {
    const mapped = address.slice('::ffff:'.length);
    if (net.isIP(mapped) === 4) return isPublicAddress(mapped);
  }
  return !BLOCKED_ADDRESSES.check(address, family === 4 ? 'ipv4' : 'ipv6');
}

/** core.webhooks.validate_destination(): https-only unless allow_private. */
export async function validateWebhookDestination(rawUrl, { allowPrivate = false } = {}) {
  const endpoint = String(rawUrl ?? '').trim();
  let parsed;
  try {
    parsed = new URL(endpoint);
  } catch {
    throw new Error(allowPrivate ? 'Webhook URL must be an absolute http(s) URL' : 'Webhook URL must be https');
  }
  const scheme = parsed.protocol.replace(':', '').toLowerCase();
  if (!allowPrivate && scheme !== 'https') throw new Error('Webhook URL must be https');
  if (!['http', 'https'].includes(scheme)) throw new Error('Webhook URL must be an absolute http(s) URL');
  if (!parsed.hostname) throw new Error('Webhook URL must be an absolute http(s) URL');
  if (parsed.username || parsed.password) throw new Error('Webhook URL must not embed credentials');

  const host = parsed.hostname.replace(/^\[|\]$/g, '');
  const port = parsed.port ? Number(parsed.port) : scheme === 'https' ? 443 : 80;
  let resolved;
  try {
    resolved = await dnsLookup(host, { all: true, verbatim: true });
  } catch (error) {
    throw new Error(`Webhook host cannot be resolved: ${error.message}`);
  }
  const addresses = [...new Set(resolved.map((entry) => entry.address))];
  if (!addresses.length) throw new Error('Webhook host resolved to no address');
  if (!allowPrivate && addresses.some((address) => !isPublicAddress(address))) {
    throw new Error('Webhook URL must not point at a private or loopback address');
  }
  return {
    url: endpoint,
    scheme,
    host,
    port,
    path: parsed.pathname || '/',
    query: parsed.search.replace(/^\?/, ''),
    addresses,
  };
}

function postPinned(destination, body, headers, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  return new Promise((resolve, reject) => {
    const isHttps = destination.scheme === 'https';
    const transport = isHttps ? https : http;
    const path = destination.path + (destination.query ? `?${destination.query}` : '');
    const options = {
      protocol: `${destination.scheme}:`,
      hostname: destination.host,
      port: destination.port,
      path,
      method: 'POST',
      headers: { ...headers, 'Content-Length': body.length },
      // Pin the address that validate_destination checked. TLS still verifies
      // the certificate against the hostname through servername.
      lookup: (_hostname, _options, callback) =>
        callback(null, destination.addresses[0], net.isIP(destination.addresses[0])),
      timeout: timeoutMs,
      signal: AbortSignal.timeout(timeoutMs),
      agent: false,
    };
    if (isHttps) {
      options.servername = destination.host;
      options.rejectUnauthorized = true;
    }

    let settled = false;
    let received = 0;
    const finish = (status) => {
      if (settled) return;
      settled = true;
      resolve(status);
    };
    const request = transport.request(options, (response) => {
      response.on('data', (chunk) => {
        received += chunk.length;
        if (received <= MAX_RESPONSE_BYTES) return;
        response.destroy();
        finish(Number(response.statusCode) || 0);
      });
      response.on('end', () => finish(Number(response.statusCode) || 0));
      response.on('error', (error) => {
        if (settled) return;
        settled = true;
        reject(error);
      });
    });
    request.on('error', (error) => {
      if (settled) return;
      settled = true;
      reject(error);
    });
    request.end(body);
  });
}

/** core.webhooks.deliver(..., attempts=1): one signed POST, no redirects. */
export async function deliverWebhook(
  url,
  body,
  secret,
  { allowPrivate = false, timeoutMs = DEFAULT_TIMEOUT_MS, timestampMs } = {},
) {
  if (!url) throw new Error('webhook url must be non-empty');
  if (!secret) throw new Error('webhook secret must be non-empty');
  let destination;
  try {
    destination = await validateWebhookDestination(url, { allowPrivate });
  } catch (error) {
    return { ok: false, status: null, error: `invalid destination: ${error.message}` };
  }
  const payload = Buffer.from(body);
  try {
    const status = await postPinned(destination, payload, buildWebhookHeaders(payload, secret, timestampMs), {
      timeoutMs,
    });
    const ok = status >= 200 && status < 300;
    return { ok, status, error: ok ? null : `HTTP ${status}` };
  } catch (error) {
    return { ok: false, status: null, error: `${error.name}: ${error.message}` };
  }
}

/** Path(...).name: Python splits on "/", never on the host platform. */
function posixBasename(value) {
  const parts = String(value ?? '').split('/');
  return parts[parts.length - 1] || '';
}

/** Object-storage deletion is still Python's until S12c ports the bucket client. */
export function objectStorageEnabled(env = process.env) {
  return Boolean(String(env.EINVITE_OBJECT_STORAGE_BUCKET ?? '').trim());
}

function storageDataDir(dataDir, env) {
  const raw = String(dataDir ?? env.EINVITE_DATA_DIR ?? '').trim();
  if (!raw) throw new Error('EINVITE_DATA_DIR is required for storage.delete');
  return resolve(raw);
}

/** purge_derivative_cache(): delete the resize cache entries keyed by path/hash. */
export function purgeDerivativeCache(path, sourceHash = '', { dataDir, env = process.env } = {}) {
  const clean = posixBasename(path);
  if (!clean) return;
  const tag = String(sourceHash ?? '').slice(0, 20);
  if (!tag) return;
  const cache = join(storageDataDir(dataDir, env), 'image-cache');
  for (const width of IMAGE_WIDTH_ALLOWLIST) {
    for (const [format, suffix] of DERIVATIVE_FORMATS) {
      const key = createHash('sha256').update(`${clean}|${tag}|${width}|${format}`, 'utf8').digest('hex');
      const target = join(cache, key + suffix);
      try {
        if (existsSync(target)) unlinkSync(target);
      } catch {
        // Python logs this cleanup failure and still completes the job.
      }
    }
  }
}

/**
 * delete_stored_asset(): local upload + derivative removal. Object storage is
 * refused here so a Node worker can never mark a bucket object deleted.
 */
export function deleteStoredAsset(path, sourceHash = '', { dataDir, env = process.env } = {}) {
  const clean = posixBasename(path);
  if (!clean) return;
  if (objectStorageEnabled(env)) throw new Error('object-storage deletion is still Python-owned');
  const base = storageDataDir(dataDir, env);
  const local = join(base, 'uploads', clean);
  if (existsSync(local)) unlinkSync(local);
  purgeDerivativeCache(clean, sourceHash, { dataDir: base, env });
}

/**
 * Attempt due `storage.delete` jobs once each, scheduling Python's retries.
 *
 * Python has no terminal failure for this kind: every exception requeues with
 * a 30 s base that doubles to 32 minutes, forever. A missing file is a
 * successful no-op. When object storage is configured the jobs stay queued for
 * Python's worker instead of being executed here.
 */
export async function processStorageDeleteJobs(
  db,
  {
    limit = 25,
    nowMs,
    workerId,
    leaseMs = DEFAULT_LEASE_MS,
    dataDir = process.env.EINVITE_DATA_DIR,
    env = process.env,
    claim = claimJob,
    release = releaseJob,
    deleteAsset = deleteStoredAsset,
    logger = null,
  } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (objectStorageEnabled(env)) return 0;
  const base = storageDataDir(dataDir, env);
  const clock = () => (nowMs === undefined ? Date.now() : nowMs);
  let processed = 0;
  for (let index = 0; index < Math.max(0, Number(limit) || 0); index += 1) {
    const now = clock();
    const job = await claim(db, { workerId, leaseMs, kinds: ['storage.delete'], now });
    if (!job) break;
    const attempts = Number(job.attempts);
    let ok = true;
    let error = '';
    try {
      await deleteAsset(String(job.payload?.path ?? ''), String(job.payload?.sha256 ?? ''), {
        dataDir: base,
        env,
      });
      await release(db, { jobId: job.id, workerId, state: 'done', error: '', availableAt: null, now });
    } catch (failure) {
      ok = false;
      error = String(failure instanceof Error ? failure.message : failure).slice(0, 1000);
      const priorAttempts = Math.max(0, attempts - 1);
      const delaySeconds = Math.min(
        STORAGE_DELETE_BACKOFF_MAX_S,
        STORAGE_DELETE_BACKOFF_BASE_S * 2 ** Math.min(priorAttempts, 6),
      );
      await release(db, {
        jobId: job.id,
        workerId,
        state: 'queued',
        error,
        availableAt: now + delaySeconds * 1000,
        now,
      });
    }
    processed += 1;
    if (logger) {
      logger({
        level: ok ? 'info' : 'warning',
        event: 'storage_delete',
        path: posixBasename(job.payload?.path),
        attempts,
        ok,
        error: error || null,
        jobId: job.id,
      });
    }
  }
  return processed;
}

/**
 * Attempt due `webhook.deliver` jobs once each, scheduling Python's retries.
 *
 * `claim`, `release` and `deliver` are injectable for unit tests; production
 * uses the S12b lease and the pinned HTTP transport above.
 */
export async function processWebhookJobs(
  db,
  {
    limit = 25,
    nowMs,
    workerId,
    leaseMs = DEFAULT_LEASE_MS,
    allowPrivate = false,
    cipher = null,
    claim = claimJob,
    release = releaseJob,
    deliver = deliverWebhook,
    logger = null,
  } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  const clock = () => (nowMs === undefined ? Date.now() : nowMs);
  let processed = 0;
  for (let index = 0; index < Math.max(0, Number(limit) || 0); index += 1) {
    const now = clock();
    const job = await claim(db, { workerId, leaseMs, kinds: ['webhook.deliver'], now });
    if (!job) break;

    const endpointId = String(job.payload?.endpointId ?? '');
    const event = String(job.payload?.event ?? '');
    const body = Buffer.from(String(job.payload?.body ?? ''), 'utf8');
    const endpoint = (
      await db.query('SELECT id,url,secret,active FROM webhook_endpoints WHERE id=?', [endpointId])
    ).rows[0];
    if (!endpoint || !Number(endpoint.active)) {
      await release(db, {
        jobId: job.id,
        workerId,
        state: 'done',
        error: 'endpoint removed',
        availableAt: null,
        now,
      });
      processed += 1;
      continue;
    }

    const secret = cipher ? cipher.reveal(endpoint.secret) : endpoint.secret;
    const result = await deliver(endpoint.url, body, secret, { allowPrivate });
    const ok = Boolean(result.ok);
    const status = result.status ?? null;
    const retryable = !ok && (status === null || RETRYABLE_STATUSES.has(Number(status)));
    const attempt = Number(job.attempts);

    if (ok) {
      await release(db, { jobId: job.id, workerId, state: 'done', error: '', availableAt: null, now });
    } else if (retryable && attempt < QUEUE_MAX_ATTEMPTS) {
      const delayMs = Math.trunc(
        Math.min(MAX_BACKOFF_S, QUEUE_BACKOFF_BASE_S * 2 ** (attempt - 1)) * 1000,
      );
      await release(db, {
        jobId: job.id,
        workerId,
        state: 'queued',
        error: String(result.error ?? '').slice(0, 1000),
        availableAt: now + delayMs,
        now,
      });
    } else {
      await release(db, {
        jobId: job.id,
        workerId,
        state: 'failed',
        error: String(result.error ?? '').slice(0, 1000),
        availableAt: null,
        now,
      });
    }

    await db.query(
      'UPDATE webhook_endpoints SET last_delivery_at=?,last_status=?,'
        + 'failure_count=CASE WHEN ?=1 THEN 0 ELSE failure_count+1 END WHERE id=?',
      [now, status, ok ? 1 : 0, endpointId],
    );
    processed += 1;
    if (logger) {
      logger({
        level: ok ? 'info' : 'warning',
        event: 'webhook_delivery',
        endpoint: endpointId,
        eventName: event,
        status,
        attempts: attempt,
        ok,
        error: result.error ?? null,
        jobId: job.id,
      });
    }
  }
  return processed;
}
