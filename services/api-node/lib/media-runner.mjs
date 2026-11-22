// S12b: the Node port of media_worker.py's `image.derivatives` handler.
//
// Python's media worker claims any queued background job, dispatches on kind and
// completes or fails it through claim/complete/fail_background_job. Only the
// derivative kind is ported here: it is a resize plus WEBP encode, which sharp
// covers. The `social.warm` / `social.guest_warm` card renderers, the
// `maintenance.cleanup` sweep and the `admin.bulk_*` operations stay Python's
// until S13 (they need Pillow's text layout and Khmer fonts).
//
// The observable contract is Python's, field for field:
//   * `pre_generate_common_derivatives()` warms 320/768/1440 as WEBP quality 84,
//     skips non-image and GIF payloads, never upscales, and stops at the first
//     failing width — so a broken upload completes as a no-op, not a failure;
//   * a derivative is `sha256(f"{basename}|{sha256(source)[:20]}|{width}|webp")`
//     in `image-cache/` with a `.webp` suffix, reused when it already exists;
//   * a failure retries with a 60 s doubling backoff capped at 3,600 s and is
//     final on the fifth attempt, with `available_at` set on both states.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';

import sharp from 'sharp';

import { DEFAULT_LEASE_MS, claimJob, releaseJob } from './jobs.mjs';
import { objectStorageEnabled } from './webhook-runner.mjs';

export const MEDIA_DERIVATIVE_WIDTHS = Object.freeze([320, 768, 1440]);
export const MEDIA_DERIVATIVE_FORMAT = 'webp';
export const MEDIA_DERIVATIVE_QUALITY = 84;
export const MEDIA_BACKOFF_BASE_MS = 60_000;
export const MEDIA_BACKOFF_MAX_MS = 3_600_000;
export const MEDIA_MAX_ATTEMPTS = 5;
export const IMAGE_WIDTH_ALLOWLIST = Object.freeze([320, 480, 768, 960, 1440, 1920]);
export const DEFAULT_MAX_IMAGE_DIMENSION = 12_000;
export const DEFAULT_MAX_IMAGE_MEGAPIXELS = 40;
export const DEFAULT_IMAGE_CACHE_MAX_BYTES = 536_870_912;
export const DEFAULT_IMAGE_CACHE_MAX_FILES = 5_000;

// Python's mimetypes.guess_type() for the extensions an upload can carry.
const IMAGE_MIME_TYPES = new Map([
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.webp', 'image/webp'],
  ['.gif', 'image/gif'],
  ['.avif', 'image/avif'],
  ['.svg', 'image/svg+xml'],
  ['.bmp', 'image/bmp'],
  ['.tif', 'image/tiff'],
  ['.tiff', 'image/tiff'],
  ['.ico', 'image/vnd.microsoft.icon'],
]);
const ORIENTATION_SWAPS_AXES = new Set([5, 6, 7, 8]);

/** Path(...).name: Python splits on "/", never on the host platform. */
function posixBasename(value) {
  const parts = String(value ?? '').split('/');
  return parts[parts.length - 1] || '';
}

/** Python's round(): half-to-even, unlike Math.round's half-up. */
export function pythonRound(value) {
  const floored = Math.floor(value);
  const fraction = value - floored;
  if (fraction < 0.5) return floored;
  if (fraction > 0.5) return floored + 1;
  return floored % 2 === 0 ? floored : floored + 1;
}

function intEnv(env, name, fallback, minimum, maximum) {
  const raw = Number.parseInt(String(env?.[name] ?? ''), 10);
  const value = Number.isFinite(raw) ? raw : fallback;
  return Math.min(maximum, Math.max(minimum, value));
}

export function mediaDataDir(dataDir, env = process.env) {
  const raw = String(dataDir ?? env.EINVITE_DATA_DIR ?? '').trim();
  if (!raw) throw new Error('EINVITE_DATA_DIR is required for image.derivatives');
  return resolve(raw);
}

/** media_worker's payload gate uses the supplied mime; nothing else does. */
function derivativePayloadAllowed(mime) {
  const value = String(mime ?? '');
  return value.startsWith('image/') && value.toLowerCase() !== 'image/gif';
}

/** generate_image_derivative()'s per-file type check, from the file name. */
export function guessImageMime(path) {
  return IMAGE_MIME_TYPES.get(extname(posixBasename(path)).toLowerCase()) ?? '';
}

/**
 * evict_image_cache(): delete the oldest entries until the cache is inside its
 * file-count and byte budgets.
 */
export function evictImageCache({ dataDir, env = process.env } = {}) {
  const cache = join(mediaDataDir(dataDir, env), 'image-cache');
  const maxFiles = intEnv(env, 'EINVITE_IMAGE_CACHE_MAX_FILES', DEFAULT_IMAGE_CACHE_MAX_FILES, 100, 1e9);
  const maxBytes = intEnv(env, 'EINVITE_IMAGE_CACHE_MAX_BYTES', DEFAULT_IMAGE_CACHE_MAX_BYTES, 50_000_000, 1e15);
  let entries;
  try {
    entries = readdirSync(cache, { withFileTypes: true });
  } catch {
    return 0;
  }
  const files = [];
  let total = 0;
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    const path = join(cache, entry.name);
    try {
      const stat = statSync(path);
      files.push({ name: entry.name, path, mtimeMs: stat.mtimeMs, size: stat.size });
      total += stat.size;
    } catch {
      // Python skips an entry whose stat fails.
    }
  }
  if (files.length <= maxFiles && total <= maxBytes) return 0;
  files.sort((left, right) => left.mtimeMs - right.mtimeMs || left.size - right.size || left.name.localeCompare(right.name));
  let removed = 0;
  for (const file of files) {
    if (files.length - removed <= maxFiles && total <= maxBytes) break;
    try {
      unlinkSync(file.path);
      removed += 1;
      total -= file.size;
    } catch {
      // Python logs and continues.
    }
  }
  return removed;
}

/**
 * generate_image_derivative(path, width, "webp"): resize (never upscale) and
 * write the WEBP derivative, or return the cached one.
 */
export async function generateImageDerivative(path, width, { dataDir, env = process.env } = {}) {
  const clean = posixBasename(path);
  const targetWidth = Number(width);
  if (!IMAGE_WIDTH_ALLOWLIST.includes(targetWidth)) throw new RangeError('Unsupported responsive image width');
  const base = mediaDataDir(dataDir, env);
  let source = null;
  if (clean) {
    try {
      source = readFileSync(join(base, 'uploads', clean));
    } catch {
      source = null;
    }
  }
  if (source === null) throw new Error(`upload not found: ${clean}`);
  const sourceMime = guessImageMime(clean);
  if (!sourceMime.startsWith('image/')) throw new TypeError('Responsive derivatives are available for images only');

  const sourceHash = createHash('sha256').update(source).digest('hex');
  const key = createHash('sha256')
    .update(`${clean}|${sourceHash.slice(0, 20)}|${targetWidth}|${MEDIA_DERIVATIVE_FORMAT}`, 'utf8')
    .digest('hex');
  const cache = join(base, 'image-cache');
  const target = join(cache, key + '.webp');
  if (existsSync(target)) return { key, sourceHash, cached: true };

  const maxDimension = intEnv(env, 'EINVITE_MAX_IMAGE_DIMENSION', DEFAULT_MAX_IMAGE_DIMENSION, 2048, 30_000);
  const maxMegapixels = intEnv(env, 'EINVITE_MAX_IMAGE_MEGAPIXELS', DEFAULT_MAX_IMAGE_MEGAPIXELS, 10, 120);
  const limitInputPixels = maxMegapixels * 1_000_000;
  const metadata = await sharp(source, { limitInputPixels }).metadata();
  const swapsAxes = ORIENTATION_SWAPS_AXES.has(Number(metadata.orientation) || 1);
  const sourceWidth = Number(swapsAxes ? metadata.height : metadata.width) || 0;
  const sourceHeight = Number(swapsAxes ? metadata.width : metadata.height) || 0;
  if (!sourceWidth || !sourceHeight) throw new Error('Image could not be decoded');
  if (
    sourceWidth > maxDimension ||
    sourceHeight > maxDimension ||
    sourceWidth * sourceHeight > limitInputPixels
  ) {
    throw new RangeError('Image exceeds responsive-processing safety limits');
  }

  // .rotate() applies EXIF orientation, like ImageOps.exif_transpose(); an
  // explicit height keeps PIL's round() instead of sharp's own rounding.
  let pipeline = sharp(source, { limitInputPixels }).rotate();
  if (sourceWidth > targetWidth) {
    pipeline = pipeline.resize(targetWidth, Math.max(1, pythonRound(sourceHeight * (targetWidth / sourceWidth))), {
      fit: 'fill',
    });
  }
  // Python converts non-RGB/L images to RGB, dropping alpha; sharp's equivalent
  // is removeAlpha(). sharp strips metadata by default, as the derivatives do.
  pipeline = pipeline.removeAlpha().webp({ quality: MEDIA_DERIVATIVE_QUALITY });
  const body = await pipeline.toBuffer();
  mkdirSync(cache, { recursive: true });
  writeFileSync(target, body);
  evictImageCache({ dataDir: base, env });
  return { key, sourceHash, cached: false };
}

/**
 * pre_generate_common_derivatives(): warm the three common widths.
 *
 * A non-image or GIF payload is a no-op and a failing width stops the loop, so
 * this never throws for a render error. A missing payload path never reaches
 * here — media_worker.run_job raises for it, and so does the caller below.
 */
export async function preGenerateCommonDerivatives(path, mime, { dataDir, env = process.env } = {}) {
  if (!derivativePayloadAllowed(mime)) return [];
  const generated = [];
  for (const width of MEDIA_DERIVATIVE_WIDTHS) {
    try {
      generated.push({ width, ...(await generateImageDerivative(path, width, { dataDir, env })) });
    } catch {
      break;
    }
  }
  return generated;
}

/**
 * Attempt due `image.derivatives` jobs once each.
 *
 * A failure requeues with Python's 60 s doubling and is final on the fifth
 * attempt. When object storage is configured the source bytes come from the
 * bucket through boto3, which Node does not have, so no job is claimed and
 * Python's worker keeps warming the cache.
 */
export async function processMediaDerivativeJobs(
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
    generate = preGenerateCommonDerivatives,
    logger = null,
  } = {},
) {
  if (!workerId) throw new TypeError('workerId is required');
  if (objectStorageEnabled(env)) return 0;
  const base = mediaDataDir(dataDir, env);
  const clock = () => (nowMs === undefined ? Date.now() : nowMs);
  let processed = 0;
  for (let index = 0; index < Math.max(0, Number(limit) || 0); index += 1) {
    const now = clock();
    const job = await claim(db, { workerId, leaseMs, kinds: ['image.derivatives'], now });
    if (!job) break;
    const attempts = Number(job.attempts);
    let ok = true;
    let error = '';
    try {
      const path = job.payload?.path;
      // media_worker.run_job reads payload['path'] directly; a job without one
      // is a failure, not a no-op.
      if (typeof path !== 'string' || !path) throw new TypeError("'path' is required for image.derivatives");
      await generate(path, String(job.payload?.mime ?? ''), { dataDir: base, env });
      await release(db, { jobId: job.id, workerId, state: 'done', error: '', availableAt: null, now });
    } catch (failure) {
      ok = false;
      error = String(failure instanceof Error ? failure.message : failure).slice(0, 2000);
      const delayMs = Math.min(
        MEDIA_BACKOFF_MAX_MS,
        MEDIA_BACKOFF_BASE_MS * 2 ** Math.max(0, attempts - 1),
      );
      await release(db, {
        jobId: job.id,
        workerId,
        state: attempts < MEDIA_MAX_ATTEMPTS ? 'queued' : 'failed',
        error,
        availableAt: now + delayMs,
        now,
      });
    }
    processed += 1;
    if (logger) {
      logger({
        level: ok ? 'info' : 'warning',
        event: 'media_derivatives',
        path: posixBasename(job.payload?.path),
        mime: job.payload?.mime ?? '',
        attempts,
        ok,
        error: error || null,
        jobId: job.id,
      });
    }
  }
  return processed;
}
