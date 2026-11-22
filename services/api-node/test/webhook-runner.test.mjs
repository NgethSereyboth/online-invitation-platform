import assert from 'node:assert/strict';
import test from 'node:test';

import {
  QUEUE_BACKOFF_BASE_S,
  QUEUE_MAX_ATTEMPTS,
  RETRYABLE_STATUSES,
  buildWebhookHeaders,
  deliverWebhook,
  processWebhookJobs,
  signWebhook,
  validateWebhookDestination,
} from '../lib/webhook-runner.mjs';

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

function job(overrides = {}) {
  return {
    id: 'job-1',
    kind: 'webhook.deliver',
    attempts: 1,
    payload: { endpointId: 'e1', event: 'rsvp.created', body: '{"event":"x"}' },
    ...overrides,
  };
}

function runner({ db, releaseCalls, deliverCalls, result = { ok: true, status: 200, error: null }, claim, extra = {} }) {
  return processWebhookJobs(db, {
    workerId: 'node-runner',
    limit: 1,
    nowMs: 1000,
    claim: claim ?? (async () => job()),
    release: async (_db, options) => {
      releaseCalls.push(options);
      return true;
    },
    deliver: async (...args) => {
      deliverCalls.push(args);
      return result;
    },
    ...extra,
  });
}

test('signWebhook matches the Python HMAC vector', () => {
  assert.equal(
    signWebhook(Buffer.from('{"event":"x"}'), 'whsec_test', 1700000000000),
    't=1700000000000,v1=6b8d465023f0967312908ba01f9c603d07c16455e93b774a2febe8f683eda577',
  );
  assert.deepEqual(buildWebhookHeaders(Buffer.from('{}'), 's', 5), {
    'Content-Type': 'application/json',
    'X-EInvite-Signature': 't=5,v1=773bda493dbd21f7ba124152afde2ffc93155f8f6599511f49b7bf4641bda33e',
    'X-EInvite-Timestamp': '5',
  });
});

test('the retry constants match Python', () => {
  assert.equal(QUEUE_MAX_ATTEMPTS, 5);
  assert.equal(QUEUE_BACKOFF_BASE_S, 1.0);
  assert.deepEqual([...RETRYABLE_STATUSES].sort((a, b) => a - b), [408, 409, 425, 429, 500, 502, 503, 504]);
});

test('validateWebhookDestination enforces the D-6 rules', async () => {
  const destination = await validateWebhookDestination('https://93.184.216.34/hook?x=1');
  assert.equal(destination.scheme, 'https');
  assert.equal(destination.port, 443);
  assert.deepEqual(destination.addresses, ['93.184.216.34']);

  for (const url of [
    'http://93.184.216.34/hook',
    'https://127.0.0.1/hook',
    'https://10.1.2.3/hook',
    'https://172.16.0.9/hook',
    'https://169.254.169.254/latest/meta-data/',
    'https://[::1]/hook',
    'https://user:pw@93.184.216.34/h',
    'ftp://93.184.216.34/hook',
    'not-a-url',
    '',
  ]) {
    await assert.rejects(() => validateWebhookDestination(url), `${url} should be refused`);
  }

  const local = await validateWebhookDestination('http://127.0.0.1:1234/hook', { allowPrivate: true });
  assert.equal(local.port, 1234);
  assert.deepEqual(local.addresses, ['127.0.0.1']);
});

test('deliverWebhook validates again and never throws for a refused destination', async () => {
  const result = await deliverWebhook('http://127.0.0.1:9/hook', Buffer.from('{}'), 'whsec_x');
  assert.deepEqual(result, {
    ok: false,
    status: null,
    error: 'invalid destination: Webhook URL must be https',
  });
});

test('processWebhookJobs completes a 2xx and resets the endpoint failure counter', async () => {
  const db = fakeDb([
    { rows: [{ id: 'e1', url: 'https://example.test/hook', secret: 'whsec', active: 1 }] },
    { rows: [], rowCount: 1 },
  ]);
  const releaseCalls = [];
  const deliverCalls = [];
  const processed = await runner({ db, releaseCalls, deliverCalls });
  assert.equal(processed, 1);
  assert.deepEqual(releaseCalls, [
    {
      jobId: 'job-1',
      workerId: 'node-runner',
      state: 'done',
      error: '',
      availableAt: null,
      now: 1000,
    },
  ]);
  assert.equal(deliverCalls.length, 1);
  assert.equal(deliverCalls[0][0], 'https://example.test/hook');
  assert.equal(deliverCalls[0][1].toString('utf8'), '{"event":"x"}');
  assert.equal(deliverCalls[0][2], 'whsec');
  assert.deepEqual(db.calls[1].params, [1000, 200, 1, 'e1']);
});

test('a retryable status schedules the 1/2/4/8 second backoff', async () => {
  const db = fakeDb([
    { rows: [{ id: 'e1', url: 'https://example.test/hook', secret: 'whsec', active: 1 }] },
    { rows: [], rowCount: 1 },
  ]);
  const releaseCalls = [];
  const processed = await runner({
    db,
    releaseCalls,
    deliverCalls: [],
    result: { ok: false, status: 500, error: 'HTTP 500' },
  });
  assert.equal(processed, 1);
  assert.equal(releaseCalls[0].state, 'queued');
  assert.equal(releaseCalls[0].error, 'HTTP 500');
  assert.equal(releaseCalls[0].availableAt, 2000);
  assert.deepEqual(db.calls[1].params, [1000, 500, 0, 'e1']);
});

test('the fifth retryable failure is final', async () => {
  const db = fakeDb([
    { rows: [{ id: 'e1', url: 'https://example.test/hook', secret: 'whsec', active: 1 }] },
    { rows: [], rowCount: 1 },
  ]);
  const releaseCalls = [];
  await runner({
    db,
    releaseCalls,
    deliverCalls: [],
    claim: async () => job({ attempts: 5 }),
    result: { ok: false, status: 500, error: 'HTTP 500' },
  });
  assert.equal(releaseCalls[0].state, 'failed');
  assert.equal(releaseCalls[0].availableAt, null);
});

test('a non-retryable answer is final after one attempt', async () => {
  const db = fakeDb([
    { rows: [{ id: 'e1', url: 'https://example.test/hook', secret: 'whsec', active: 1 }] },
    { rows: [], rowCount: 1 },
  ]);
  const releaseCalls = [];
  await runner({
    db,
    releaseCalls,
    deliverCalls: [],
    result: { ok: false, status: 400, error: 'HTTP 400' },
  });
  assert.equal(releaseCalls[0].state, 'failed');
  assert.equal(releaseCalls[0].error, 'HTTP 400');
});

test('a missing or inactive endpoint completes without a request', async () => {
  for (const rows of [[], [{ id: 'e1', url: 'https://example.test/hook', secret: 'whsec', active: 0 }]]) {
    const db = fakeDb([{ rows }]);
    const releaseCalls = [];
    const deliverCalls = [];
    const processed = await runner({ db, releaseCalls, deliverCalls });
    assert.equal(processed, 1);
    assert.equal(deliverCalls.length, 0);
    assert.equal(releaseCalls[0].state, 'done');
    assert.equal(releaseCalls[0].error, 'endpoint removed');
    assert.equal(db.calls.length, 1);
  }
});

test('the runner decrypts the endpoint secret and stops when no job is due', async () => {
  const db = fakeDb([
    { rows: [{ id: 'e1', url: 'https://example.test/hook', secret: 'gAAAAA-sealed', active: 1 }] },
    { rows: [], rowCount: 1 },
  ]);
  const deliverCalls = [];
  let claimed = 0;
  const processed = await runner({
    db,
    releaseCalls: [],
    deliverCalls,
    claim: async () => {
      claimed += 1;
      return claimed === 1 ? job() : null;
    },
    extra: { cipher: { reveal: (value) => `plain:${value}` } },
  });
  assert.equal(processed, 1);
  assert.equal(deliverCalls[0][2], 'plain:gAAAAA-sealed');
});
