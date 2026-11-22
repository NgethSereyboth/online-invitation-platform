import { buildApp } from './app.mjs';
import { createFieldCipher } from './lib/crypto.mjs';
import { assertSchema, createDatabase } from './lib/db.mjs';

const port = Number.parseInt(process.env.PORT ?? '8080', 10);
const host = process.env.HOST ?? '127.0.0.1';

let db = null;
let cipher = null;
if (process.env.EINVITE_DATABASE_URL) {
  db = createDatabase();
  try {
    await assertSchema(db);
    // A malformed key refuses production boot here, before any request runs.
    cipher = createFieldCipher();
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    await db.close();
    process.exit(1);
  }
}

const app = buildApp({ logger: { level: process.env.LOG_LEVEL ?? 'info' }, db, cipher });

for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, async () => {
    app.log.info({ signal }, 'shutting down');
    try {
      await app.close();
      process.exit(0);
    } catch (error) {
      app.log.error({ error }, 'shutdown failed');
      process.exit(1);
    }
  });
}

// The schema contract is asserted above, before the app exists, so a
// half-migrated database fails loudly instead of 500-ing per request.
if (db) {
  app.addHook('onClose', async () => {
    await db.close();
  });
}

try {
  await app.listen({ port, host });
} catch (error) {
  app.log.error({ error }, 'listen failed');
  process.exit(1);
}
