#!/usr/bin/env node
// Harness probe for the Node platform runner: process `--limit` due jobs at a
// fixed clock and print the count. Production runs bin/platform-runner.mjs.
import { createDatabase } from '../services/api-node/lib/db.mjs';
import { processPlatformJobs } from '../services/api-node/lib/platform-runner.mjs';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

const db = createDatabase({ connectionString: arg('database-url') });
try {
  const processed = await processPlatformJobs(db, {
    workerId: arg('worker', 'node-platform-probe'),
    limit: Number(arg('limit', '1')),
    nowMs: Number(arg('now-ms', String(Date.now()))),
  });
  console.log(JSON.stringify({ processed }));
} finally {
  await db.close();
}
