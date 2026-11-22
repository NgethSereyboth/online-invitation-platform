#!/usr/bin/env node
// Harness probe for the Node background runner: process `--limit` due jobs of
// `--kind` at a fixed clock and print the count. Production runs
// bin/webhook-runner.mjs.
import { createDatabase } from '../services/api-node/lib/db.mjs';
import { processMediaDerivativeJobs } from '../services/api-node/lib/media-runner.mjs';
import {
  processStorageDeleteJobs,
  processWebhookJobs,
} from '../services/api-node/lib/webhook-runner.mjs';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

const db = createDatabase({ connectionString: arg('database-url') });
try {
  const options = {
    workerId: arg('worker', 'node-webhook-probe'),
    limit: Number(arg('limit', '1')),
    nowMs: Number(arg('now-ms', String(Date.now()))),
  };
  const kind = arg('kind', 'webhook.deliver');
  let processed;
  if (kind === 'storage.delete') {
    processed = await processStorageDeleteJobs(db, { ...options, dataDir: process.env.EINVITE_DATA_DIR });
  } else if (kind === 'image.derivatives') {
    processed = await processMediaDerivativeJobs(db, { ...options, dataDir: process.env.EINVITE_DATA_DIR });
  } else {
    processed = await processWebhookJobs(db, {
      ...options,
      allowPrivate: arg('allow-private', 'true') === 'true',
    });
  }
  console.log(JSON.stringify({ processed }));
} finally {
  await db.close();
}
