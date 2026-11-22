#!/usr/bin/env node
// Harness driver for lib/jobs.mjs. It is not product code: each mode performs
// one queue operation and prints JSON so the Python harness can compare what
// both backends did to the same PostgreSQL queue.
import { createDatabase } from '../services/api-node/lib/db.mjs';
import {
  claimJob,
  claimPlatformJob,
  releaseJob,
  releasePlatformJob,
  renewJobLease,
  renewPlatformJobLease,
} from '../services/api-node/lib/jobs.mjs';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const databaseUrl = arg('database-url');
const worker = arg('worker', 'node-agent');
const mode = arg('mode', 'drain');
const kind = arg('kind', 'harness.lease');
const leaseMs = Number(arg('lease-ms', '60000'));
const holdMs = Number(arg('hold-ms', '0'));
const renewMs = Number(arg('renew-ms', '0'));
const maxClaims = Number(arg('max-claims', '100'));
const jobId = arg('job-id', '');
const state = arg('state', 'done');
const startAt = Number(arg('start-at', '0'));

const db = createDatabase({ connectionString: databaseUrl });
try {
  const wait = startAt - Date.now();
  if (wait > 0) await sleep(wait);
  if (mode === 'platform-drain') {
    const claims = [];
    let misses = 0;
    while (claims.length < maxClaims && misses < 3) {
      const job = await claimPlatformJob(db, { workerId: worker, leaseMs, kinds: [kind] });
      if (!job) {
        misses += 1;
        await sleep(20);
        continue;
      }
      misses = 0;
      claims.push({ id: job.id, attempts: job.retryCount });
      await releasePlatformJob(db, { jobId: job.id, workerId: worker, state: 'completed', result: { ok: true } });
      await sleep(5);
    }
    console.log(JSON.stringify({ worker, claims }));
  } else if (mode === 'platform-claim') {
    const job = await claimPlatformJob(db, { workerId: worker, leaseMs, kinds: [kind] });
    console.log(JSON.stringify({ worker, job }));
  } else if (mode === 'platform-hold') {
    const job = await claimPlatformJob(db, { workerId: worker, leaseMs, kinds: [kind] });
    let renew = null;
    if (job) {
      await sleep(holdMs);
      if (renewMs > 0) renew = await renewPlatformJobLease(db, { jobId: job.id, workerId: worker, leaseMs: renewMs });
      if (arg('release', 'false') === 'true') {
        await releasePlatformJob(db, { jobId: job.id, workerId: worker, state: 'completed' });
      }
    }
    console.log(JSON.stringify({ worker, job, renew }));
  } else if (mode === 'platform-renew') {
    console.log(
      JSON.stringify({ ok: await renewPlatformJobLease(db, { jobId, workerId: worker, leaseMs: renewMs || leaseMs }) }),
    );
  } else if (mode === 'platform-release') {
    console.log(JSON.stringify({ ok: await releasePlatformJob(db, { jobId, workerId: worker, state }) }));
  } else if (mode === 'drain') {
    const claims = [];
    let misses = 0;
    while (claims.length < maxClaims && misses < 3) {
      const job = await claimJob(db, { workerId: worker, leaseMs, kinds: [kind] });
      if (!job) {
        misses += 1;
        await sleep(20);
        continue;
      }
      misses = 0;
      claims.push({ id: job.id, attempts: job.attempts });
      await releaseJob(db, { jobId: job.id, workerId: worker, state: 'done' });
      await sleep(5);
    }
    console.log(JSON.stringify({ worker, claims }));
  } else if (mode === 'claim') {
    const job = await claimJob(db, { workerId: worker, leaseMs, kinds: [kind] });
    console.log(JSON.stringify({ worker, job }));
  } else if (mode === 'hold') {
    const job = await claimJob(db, { workerId: worker, leaseMs, kinds: [kind] });
    let renew = null;
    if (job) {
      await sleep(holdMs);
      if (renewMs > 0) renew = await renewJobLease(db, { jobId: job.id, workerId: worker, leaseMs: renewMs });
      if (arg('release', 'false') === 'true') {
        await releaseJob(db, { jobId: job.id, workerId: worker, state: 'done' });
      }
    }
    console.log(JSON.stringify({ worker, job, renew }));
  } else if (mode === 'renew') {
    console.log(
      JSON.stringify({ ok: await renewJobLease(db, { jobId, workerId: worker, leaseMs: renewMs || leaseMs }) }),
    );
  } else if (mode === 'release') {
    console.log(JSON.stringify({ ok: await releaseJob(db, { jobId, workerId: worker, state }) }));
  } else {
    throw new Error(`unknown mode: ${mode}`);
  }
} finally {
  await db.close();
}
