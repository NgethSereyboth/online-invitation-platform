import { buildApp } from './app.mjs';
import { assertSchema, createDatabase } from './lib/db.mjs';

const port = Number.parseInt(process.env.PORT ?? '8080', 10);
const host = process.env.HOST ?? '127.0.0.1';

const app = buildApp({ logger: { level: process.env.LOG_LEVEL ?? 'info' } });

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

// S4: Python owns migrations. When a database is configured this service
// asserts the schema contract at boot and refuses to start on a mismatch, so a
// half-migrated database fails loudly instead of 500-ing per request.
if (process.env.EINVITE_DATABASE_URL) {
  const db = createDatabase();
  try {
    await assertSchema(db);
  } catch (error) {
    app.log.error({ err: error }, 'schema contract check failed; refusing to start');
    await db.close();
    process.exit(1);
  }
  app.decorate('db', db);
  app.addHook('onClose', async () => {
    await db.close();
  });
  app.log.info('database schema contract satisfied');
}

try {
  await app.listen({ port, host });
} catch (error) {
  app.log.error({ error }, 'listen failed');
  process.exit(1);
}
