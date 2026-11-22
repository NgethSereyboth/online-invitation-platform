import assert from 'node:assert/strict';
import test from 'node:test';

import { mediaIngestJob, processPlatformJobs } from '../lib/platform-runner.mjs';

function fakeDb(results) {
  const calls = [];
  return {
    calls,
    async query(sql, params = []) {
      calls.push({ sql, params });
      return results.length > 1 ? results.shift() : results[0];
    },
  };
}

function platformRow(overrides = {}) {
  return {
    kind: 'media-ingest',
    payload_json: '{"assetId":"asset-1"}',
    retry_count: 0,
    max_retries: 3,
    ...overrides,
  };
}

function runner({ db, claim, handlers, nowMs = 1000 }) {
  return processPlatformJobs(db, {
    workerId: 'node-runner',
    limit: 1,
    nowMs,
    claim: claim ?? (async () => ({ id: 'pj-1', kind: 'media-ingest' })),
    handlers,
  });
}

test('media-ingest echoes the asset id and marks progress like _media_job', async () => {
  const marks = [];
  assert.deepEqual(await mediaIngestJob({ assetId: 'asset-1' }, { progress: (value) => marks.push(value) }), {
    status: 'provider-hook-ready',
    assetId: 'asset-1',
  });
  assert.deepEqual(marks, [0.5]);
  assert.deepEqual(await mediaIngestJob({}, {}), { status: 'provider-hook-ready', assetId: '' });
  // payload.get("assetId", "") keeps an explicit null; Object.hasOwn matches it.
  assert.deepEqual(await mediaIngestJob({ assetId: null }, {}), {
    status: 'provider-hook-ready',
    assetId: null,
  });
});

test('processPlatformJobs completes a job with Python progress and result JSON', async () => {
  const db = fakeDb([{ rows: [platformRow()] }, { rows: [] }, { rows: [] }]);
  const processed = await runner({ db });
  assert.equal(processed, 1);
  assert.deepEqual(db.calls[1].params, [0.5, 1000, 'pj-1', 'node-runner']);
  assert.deepEqual(db.calls[2].params, [
    'completed',
    1,
    '{"status":"provider-hook-ready","assetId":"asset-1"}',
    '',
    1000,
    1000,
    'pj-1',
    'node-runner',
  ]);
});

test('the result keeps a non-ASCII asset id unescaped and a null asset id null', async () => {
  for (const [payload, expected] of [
    ['{"assetId":"asset-café-1"}', '{"status":"provider-hook-ready","assetId":"asset-café-1"}'],
    ['{"assetId":null}', '{"status":"provider-hook-ready","assetId":null}'],
  ]) {
    const db = fakeDb([{ rows: [platformRow({ payload_json: payload })] }, { rows: [] }, { rows: [] }]);
    await runner({ db });
    assert.equal(db.calls[2].params[2], expected);
  }
});

test('a failing handler requeues with retry_count+1 while retries remain', async () => {
  const db = fakeDb([
    { rows: [platformRow()] },
    { rows: [{ cancellation_requested: 0, status: 'running' }] },
    { rows: [] },
  ]);
  const processed = await runner({
    db,
    handlers: {
      'media-ingest': () => {
        throw new Error('provider hook unavailable');
      },
    },
  });
  assert.equal(processed, 1);
  assert.deepEqual(db.calls[2].params, [1, 'provider hook unavailable', 1000, 'pj-1', 'node-runner']);
  assert.match(db.calls[2].sql, /status='queued'/);
});

test('the last retry is final and records Python result and error fields', async () => {
  const db = fakeDb([
    { rows: [platformRow({ retry_count: 3, max_retries: 3 })] },
    { rows: [{ cancellation_requested: 0, status: 'running' }] },
    { rows: [] },
  ]);
  await runner({
    db,
    handlers: {
      'media-ingest': () => {
        throw new Error('boom');
      },
    },
  });
  assert.deepEqual(db.calls[2].params, ['failed', 0, '{}', 'boom', 1000, 1000, 'pj-1', 'node-runner']);
});

test('a cancel request during a failure finishes the row as cancelled', async () => {
  const db = fakeDb([
    { rows: [platformRow({ retry_count: 3, max_retries: 3 })] },
    { rows: [{ cancellation_requested: 1, status: 'running' }] },
    { rows: [] },
  ]);
  await runner({
    db,
    handlers: {
      'media-ingest': () => {
        throw new Error('cancelled by owner');
      },
    },
  });
  assert.equal(db.calls[2].params[0], 'cancelled');
  assert.equal(db.calls[2].params[1], 0);
});

test('a non-numeric progress value fails like Python float() raising', async () => {
  const db = fakeDb([
    { rows: [platformRow()] },
    { rows: [{ cancellation_requested: 0, status: 'running' }] },
    { rows: [] },
  ]);
  await runner({
    db,
    handlers: {
      'media-ingest': (_payload, { progress }) => {
        progress('not-a-number');
        return {};
      },
    },
  });
  assert.match(db.calls[2].params[1], /progress must be a number/);
});

test('a claimed kind with no handler fails instead of staying running', async () => {
  const db = fakeDb([{ rows: [platformRow({ kind: 'workspace-backup' })] }, { rows: [] }]);
  const processed = await runner({
    db,
    claim: async () => ({ id: 'pj-1', kind: 'workspace-backup' }),
  });
  assert.equal(processed, 1);
  assert.deepEqual(db.calls[1].params, [
    'failed',
    0,
    '{}',
    'No handler registered for workspace-backup',
    1000,
    1000,
    'pj-1',
    'node-runner',
  ]);
});

test('only the implemented kinds are claimed and an empty queue stops at once', async () => {
  const claims = [];
  const db = fakeDb([{ rows: [] }]);
  const processed = await runner({
    db,
    claim: async (_db, options) => {
      claims.push(options.kinds);
      return null;
    },
  });
  assert.equal(processed, 0);
  assert.deepEqual(claims, [['media-ingest']]);
  assert.deepEqual(db.calls, []);
});
