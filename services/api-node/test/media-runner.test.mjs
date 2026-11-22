import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import sharp from 'sharp';

import {
  MEDIA_BACKOFF_BASE_MS,
  MEDIA_BACKOFF_MAX_MS,
  MEDIA_DERIVATIVE_QUALITY,
  MEDIA_DERIVATIVE_WIDTHS,
  MEDIA_MAX_ATTEMPTS,
  generateImageDerivative,
  preGenerateCommonDerivatives,
  processMediaDerivativeJobs,
  pythonRound,
} from '../lib/media-runner.mjs';

async function sourcePng(width = 900, height = 600) {
  return sharp({ create: { width, height, channels: 3, background: { r: 12, g: 34, b: 56 } } })
    .png()
    .toBuffer();
}

function workspace() {
  const dataDir = mkdtempSync(join(tmpdir(), 'einvite-media-'));
  mkdirSync(join(dataDir, 'uploads'), { recursive: true });
  mkdirSync(join(dataDir, 'image-cache'), { recursive: true });
  return dataDir;
}

function cacheNames(dataDir) {
  return readdirSync(join(dataDir, 'image-cache')).sort();
}

test('the media constants match media_worker and pre_generate_common_derivatives', () => {
  assert.deepEqual([...MEDIA_DERIVATIVE_WIDTHS], [320, 768, 1440]);
  assert.equal(MEDIA_DERIVATIVE_QUALITY, 84);
  assert.equal(MEDIA_MAX_ATTEMPTS, 5);
  assert.equal(MEDIA_BACKOFF_BASE_MS, 60_000);
  assert.equal(MEDIA_BACKOFF_MAX_MS, 3_600_000);
});

test('pythonRound rounds halves to even', () => {
  assert.equal(pythonRound(213.333), 213);
  assert.equal(pythonRound(213.5), 214);
  assert.equal(pythonRound(214.5), 214);
  assert.equal(pythonRound(2.5), 2);
  assert.equal(pythonRound(3.5), 4);
});

test('the three derivatives use Python cache keys and PIL resize arithmetic', async () => {
  const dataDir = workspace();
  try {
    const png = await sourcePng();
    writeFileSync(join(dataDir, 'uploads', 'photo.png'), png);
    const tag = createHash('sha256').update(png).digest('hex').slice(0, 20);
    const expected = new Map();
    for (const [width, height] of [
      [320, 213],
      [768, 512],
      [1440, 600],
    ]) {
      const key = createHash('sha256').update(`photo.png|${tag}|${width}|webp`).digest('hex');
      expected.set(key + '.webp', { width, height });
    }

    await preGenerateCommonDerivatives('photo.png', 'image/png', { dataDir, env: {} });

    assert.deepEqual(cacheNames(dataDir), [...expected.keys()].sort());
    for (const [name, size] of expected) {
      const metadata = await sharp(join(dataDir, 'image-cache', name)).metadata();
      assert.equal(metadata.format, 'webp');
      assert.equal(metadata.width, Math.min(size.width, 900));
      // 1440 is the no-upscale case: the source is re-encoded at 900×600.
      assert.equal(metadata.height, size.height);
    }
  } finally {
    rmSync(dataDir, { recursive: true, force: true });
  }
});

test('an existing derivative is reused instead of re-encoded', async () => {
  const dataDir = workspace();
  try {
    writeFileSync(join(dataDir, 'uploads', 'photo.png'), await sourcePng());
    const first = await generateImageDerivative('photo.png', 320, { dataDir, env: {} });
    const second = await generateImageDerivative('photo.png', 320, { dataDir, env: {} });
    assert.equal(first.cached, false);
    assert.equal(second.cached, true);
    assert.equal(first.key, second.key);
    assert.equal(cacheNames(dataDir).length, 1);
  } finally {
    rmSync(dataDir, { recursive: true, force: true });
  }
});

test('non-image, GIF and missing uploads are no-ops, not failures', async () => {
  const dataDir = workspace();
  try {
    writeFileSync(join(dataDir, 'uploads', 'photo.png'), await sourcePng(120, 80));
    writeFileSync(join(dataDir, 'uploads', 'anim.gif'), Buffer.from('GIF89a', 'ascii'));
    for (const [path, mime] of [
      ['photo.png', 'application/pdf'],
      ['anim.gif', 'image/gif'],
      ['absent.png', 'image/png'],
    ]) {
      assert.deepEqual(await preGenerateCommonDerivatives(path, mime, { dataDir, env: {} }), []);
    }
    assert.deepEqual(cacheNames(dataDir), []);
  } finally {
    rmSync(dataDir, { recursive: true, force: true });
  }
});

test('a render failure stops at the first width and does not throw', async () => {
  const dataDir = workspace();
  try {
    writeFileSync(join(dataDir, 'uploads', 'broken.png'), Buffer.from('not a png', 'ascii'));
    assert.deepEqual(await preGenerateCommonDerivatives('broken.png', 'image/png', { dataDir, env: {} }), []);
    assert.deepEqual(cacheNames(dataDir), []);
  } finally {
    rmSync(dataDir, { recursive: true, force: true });
  }
});

function mediaRunner({ claim, env = {}, dataDir = '/tmp/einvite-media', generate } = {}) {
  const releaseCalls = [];
  return processMediaDerivativeJobs(
    {},
    {
      workerId: 'node-runner',
      limit: 1,
      nowMs: 1000,
      dataDir,
      env,
      claim:
        claim ??
        (async () => ({
          id: 'md-1',
          kind: 'image.derivatives',
          attempts: 1,
          payload: { path: 'photo.png', mime: 'image/png', sha256: 'x' },
        })),
      release: async (_db, options) => {
        releaseCalls.push(options);
        return true;
      },
      generate: generate ?? (async () => []),
    },
  ).then((processed) => ({ processed, releaseCalls }));
}

test('processMediaDerivativeJobs completes a derivative job', async () => {
  const { processed, releaseCalls } = await mediaRunner({});
  assert.equal(processed, 1);
  assert.deepEqual(releaseCalls, [
    { jobId: 'md-1', workerId: 'node-runner', state: 'done', error: '', availableAt: null, now: 1000 },
  ]);
});

test('a payload without a path fails and requeues with 60 s doubling', async () => {
  for (const [attempts, delayMs] of [
    [1, 60_000],
    [4, 480_000],
    [5, 960_000],
    [8, 3_600_000],
  ]) {
    const { processed, releaseCalls } = await mediaRunner({
      claim: async () => ({ id: 'md-1', kind: 'image.derivatives', attempts, payload: { mime: 'image/png' } }),
    });
    assert.equal(processed, 1);
    assert.equal(releaseCalls[0].state, attempts < MEDIA_MAX_ATTEMPTS ? 'queued' : 'failed');
    assert.equal(releaseCalls[0].availableAt, 1000 + delayMs);
    assert.match(releaseCalls[0].error, /path/);
  }
});

test('a throwing render is retried, not completed', async () => {
  const { releaseCalls } = await mediaRunner({
    generate: async () => {
      throw new Error('EACCES: permission denied');
    },
  });
  assert.equal(releaseCalls[0].state, 'queued');
  assert.match(releaseCalls[0].error, /permission denied/);
});

test('object-storage mode leaves image.derivatives jobs for Python', async () => {
  let claimed = 0;
  const { processed, releaseCalls } = await mediaRunner({
    env: { EINVITE_OBJECT_STORAGE_BUCKET: 'materials' },
    claim: async () => {
      claimed += 1;
      return null;
    },
  });
  assert.equal(processed, 0);
  assert.equal(claimed, 0);
  assert.deepEqual(releaseCalls, []);
});
