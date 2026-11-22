#!/usr/bin/env node
// Standalone webhook.deliver worker. The API server does not start it: one
// process per queue during the parallel run, selected explicitly by ops.
import { randomUUID } from 'node:crypto';

import { createFieldCipher } from '../lib/crypto.mjs';
import { createDatabase } from '../lib/db.mjs';
import { processWebhookJobs } from '../lib/webhook-runner.mjs';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

function envFlag(name, fallback = false) {
  const value = process.env[name];
  if (value === undefined) return fallback;
  return ['1', 'true', 'yes'].includes(String(value).trim().toLowerCase());
}

const once = process.argv.includes('--once') || envFlag('EINVITE_WEBHOOK_RUNNER_ONCE');
const limit = Number(arg('limit', process.env.EINVITE_WEBHOOK_RUNNER_LIMIT ?? '25'));
const intervalMs = Math.max(100, Number(process.env.EINVITE_WEBHOOK_RUNNER_INTERVAL_MS ?? '1000'));
const allowPrivate = envFlag('EINVITE_ALLOW_PRIVATE_WEBHOOKS');
const workerId =
  process.env.EINVITE_WEBHOOK_WORKER_ID || `node-webhook-${process.pid}-${randomUUID().slice(0, 8)}`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const db = createDatabase();
const cipher = createFieldCipher();
let stopping = false;
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => {
    stopping = true;
  });
}

try {
  do {
    const processed = await processWebhookJobs(db, {
      workerId,
      limit,
      allowPrivate,
      cipher,
      logger: (entry) => console.log(JSON.stringify(entry)),
    });
    if (once || stopping) break;
    if (!processed) await sleep(intervalMs);
  } while (!stopping);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
} finally {
  await db.close();
}
