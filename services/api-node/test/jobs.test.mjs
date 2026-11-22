import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DEFAULT_LEASE_MS,
  LEGACY_LEASE_MS,
  claimJob,
  claimPlatformJob,
  ensureJobLeaseSchema,
  releaseJob,
  releasePlatformJob,
  renewJobLease,
  renewPlatformJobLease,
} from '../lib/jobs.mjs';

function fakeDb(results) {
  const calls = [];
  return {
    calls,
    async query(sql, params = []) {
      calls.push({ sql, params });
      const next = results.length > 1 ? results.shift() : results[0];
      return next ?? { rows: [], rowCount: 0 };
    },
  };
}

test('the legacy cutoff matches Python\u2019s 30-minute stale sweep', () => {
  assert.equal(LEGACY_LEASE_MS, 30 * 60 * 1000);
  assert.equal(DEFAULT_LEASE_MS, 5 * 60 * 1000);
});

test('claimJob adds the lease columns once, then claims atomically', async () => {
  const db = fakeDb([
    { rows: [], rowCount: 0 },
    { rows: [], rowCount: 0 },
    {
      rows: [
        {
          id: 'job-1',
          kind: 'webhook.deliver',
          payload_json: '{"endpointId":"e1"}',
          attempts: '3',
          created_at: 10,
          updated_at: 1000,
        },
      ],
      rowCount: 1,
    },
  ]);
  const job = await claimJob(db, { workerId: 'node-a', leaseMs: 500, now: 1000, kinds: ['webhook.deliver', 'storage.delete'] });
  assert.deepEqual(job, {
    id: 'job-1',
    kind: 'webhook.deliver',
    payload: { endpointId: 'e1' },
    attempts: 3,
    createdAt: 10,
    updatedAt: 1000,
    leaseExpiresAt: 1500,
  });
  assert.equal(db.calls.length, 3);
  assert.match(db.calls[0].sql, /ADD COLUMN IF NOT EXISTS lock_owner/);
  assert.match(db.calls[1].sql, /ADD COLUMN IF NOT EXISTS lease_expires_at/);
  assert.match(db.calls[2].sql, /FOR UPDATE SKIP LOCKED/);
  assert.match(db.calls[2].sql, /kind IN \(\?,\?\)/);
  assert.deepEqual(db.calls[2].params, [
    1000,
    1000,
    1000 - LEGACY_LEASE_MS,
    'webhook.deliver',
    'storage.delete',
    'node-a',
    1000,
    1500,
    1000,
  ]);

  // The WeakSet memo means a second claim on the same connection skips the ALTERs.
  await claimJob(db, { workerId: 'node-a', now: 2000 });
  assert.equal(db.calls.length, 4);
  assert.match(db.calls[3].sql, /^WITH candidate/);
});

test('claimJob returns null when nothing is due and tolerates a malformed payload', async () => {
  assert.equal(await claimJob(fakeDb([{ rows: [], rowCount: 0 }]), { workerId: 'w' }), null);
  const job = await claimJob(
    fakeDb([
      { rows: [], rowCount: 0 },
      { rows: [], rowCount: 0 },
      { rows: [{ id: 'j', kind: 'k', payload_json: 'not json', attempts: 0, created_at: 1, updated_at: 1 }], rowCount: 1 },
    ]),
    { workerId: 'w', now: 5 },
  );
  assert.deepEqual(job.payload, {});
});

test('claimJob rejects a missing owner or a non-positive lease', async () => {
  await assert.rejects(() => claimJob(fakeDb([{ rows: [], rowCount: 0 }]), {}), /workerId/);
  await assert.rejects(() => claimJob(fakeDb([{ rows: [], rowCount: 0 }]), { workerId: 'w', leaseMs: 0 }), /leaseMs/);
});

test('renewJobLease heartbeats only the owner\u2019s running row', async () => {
  const db = fakeDb([{ rows: [], rowCount: 1 }]);
  assert.equal(await renewJobLease(db, { jobId: 'j', workerId: 'a', leaseMs: 700, now: 100 }), true);
  assert.match(db.calls[0].sql, /state='running' AND lock_owner=\?/);
  assert.deepEqual(db.calls[0].params, [100, 800, 100, 'j', 'a']);
  assert.equal(
    await renewJobLease(fakeDb([{ rows: [], rowCount: 0 }]), { jobId: 'j', workerId: 'b' }),
    false,
  );
});

test('releaseJob refuses a state outside done/queued/failed', async () => {
  await assert.rejects(
    () => releaseJob(fakeDb([{ rows: [], rowCount: 1 }]), { jobId: 'j', workerId: 'a', state: 'running' }),
    /unsupported release state/,
  );
});

test('releaseJob clears the lease only for the owning worker', async () => {
  const done = fakeDb([{ rows: [], rowCount: 1 }]);
  assert.equal(await releaseJob(done, { jobId: 'j', workerId: 'a', now: 50 }), true);
  assert.match(done.calls[0].sql, /lock_owner='', locked_at=NULL, lease_expires_at=NULL/);
  assert.deepEqual(done.calls[0].params, ['done', '', null, 50, 'j', 'a']);

  const retry = fakeDb([{ rows: [], rowCount: 1 }]);
  assert.equal(
    await releaseJob(retry, {
      jobId: 'j',
      workerId: 'a',
      state: 'queued',
      error: 'boom',
      availableAt: 999,
      now: 50,
    }),
    true,
  );
  assert.deepEqual(retry.calls[0].params, ['queued', 'boom', 999, 50, 'j', 'a']);

  assert.equal(
    await releaseJob(fakeDb([{ rows: [], rowCount: 0 }]), { jobId: 'j', workerId: 'b' }),
    false,
  );
});

test('claimPlatformJob claims a queued or stale platform row atomically', async () => {
  const db = fakeDb([
    { rows: [], rowCount: 0 },
    { rows: [], rowCount: 0 },
    {
      rows: [{ id: 'p1', kind: 'harness.lease', payload_json: '{"n":2}', retry_count: 1, created_at: 5, updated_at: 1000 }],
      rowCount: 1,
    },
  ]);
  const job = await claimPlatformJob(db, { workerId: 'node-a', leaseMs: 500, now: 1000, kinds: ['harness.lease'] });
  assert.deepEqual(job, {
    id: 'p1',
    kind: 'harness.lease',
    payload: { n: 2 },
    retryCount: 1,
    createdAt: 5,
    updatedAt: 1000,
    leaseExpiresAt: 1500,
  });
  assert.match(db.calls[2].sql, /FOR UPDATE SKIP LOCKED/);
  assert.match(db.calls[2].sql, /status='running'/);
  assert.deepEqual(db.calls[2].params, [1000, 1000 - LEGACY_LEASE_MS, 'harness.lease', 1000, 'node-a', 1500, 1000]);
});

test('renewPlatformJobLease and releasePlatformJob require the owner', async () => {
  const renew = fakeDb([{ rows: [], rowCount: 1 }]);
  assert.equal(await renewPlatformJobLease(renew, { jobId: 'p1', workerId: 'a', leaseMs: 700, now: 100 }), true);
  assert.deepEqual(renew.calls[0].params, [800, 100, 'p1', 'a']);

  const release = fakeDb([{ rows: [], rowCount: 1 }]);
  assert.equal(await releasePlatformJob(release, { jobId: 'p1', workerId: 'a', now: 50 }), true);
  assert.match(release.calls[0].sql, /lock_owner='', lease_expires_at=NULL/);
  assert.deepEqual(release.calls[0].params, ['completed', 1, '{}', '', 50, 50, 'p1', 'a']);
  await assert.rejects(
    () => releasePlatformJob(fakeDb([{ rows: [], rowCount: 0 }]), { jobId: 'p1', workerId: 'a', state: 'running' }),
    /unsupported release state/,
  );
});

test('ensureJobLeaseSchema is idempotent per connection', async () => {
  const db = fakeDb([{ rows: [], rowCount: 0 }]);
  await ensureJobLeaseSchema(db);
  await ensureJobLeaseSchema(db);
  assert.equal(db.calls.length, 2);
});
