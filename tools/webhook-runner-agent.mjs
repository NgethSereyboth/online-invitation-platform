#!/usr/bin/env node
// Harness probe for the Node webhook runner: process `--limit` due jobs at a
// fixed clock and print the count. Production runs bin/webhook-runner.mjs.
import { createDatabase } from '../services/api-node/lib/db.mjs';
import { processWebhookJobs } from '../services/api-node/lib/webhook-runner.mjs';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

const db = createDatabase({ connectionString: arg('database-url') });
try {
  const processed = await processWebhookJobs(db, {
    workerId: arg('worker', 'node-webhook-probe'),
    limit: Number(arg('limit', '1')),
    nowMs: Number(arg('now-ms', String(Date.now()))),
    allowPrivate: arg('allow-private', 'true') === 'true',
  });
  console.log(JSON.stringify({ processed }));
} finally {
  await db.close();
}
