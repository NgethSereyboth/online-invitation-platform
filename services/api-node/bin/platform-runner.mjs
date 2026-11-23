#!/usr/bin/env node
// Standalone worker for the platform_v32 job table (`platform_jobs`). Only the
// kinds lib/platform-runner.mjs implements are claimed; backup, restore, raster
// rendering, privacy export and bulk personalization stay Python's.
import { randomUUID } from 'node:crypto';

import { createDatabase } from '../lib/db.mjs';
import { processPlatformJobs } from '../lib/platform-runner.mjs';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

function envFlag(name, fallback = false) {
  const value = process.env[name];
  if (value === undefined) return fallback;
  return ['1', 'true', 'yes'].includes(String(value).trim().toLowerCase());
}

const once = process.argv.includes('--once') || envFlag('EINVITE_PLATFORM_RUNNER_ONCE');
const limit = Number(arg('limit', process.env.EINVITE_PLATFORM_RUNNER_LIMIT ?? '25'));
const intervalMs = Math.max(100, Number(process.env.EINVITE_PLATFORM_RUNNER_INTERVAL_MS ?? '1000'));
const workerId =
  process.env.EINVITE_PLATFORM_WORKER_ID || `node-platform-${process.pid}-${randomUUID().slice(0, 8)}`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const db = createDatabase();
let stopping = false;
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => {
    stopping = true;
  });
}

try {
  do {
    const processed = await processPlatformJobs(db, {
      workerId,
      limit,
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
