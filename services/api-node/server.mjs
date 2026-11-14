import { buildApp } from './app.mjs';

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

try {
  await app.listen({ port, host });
} catch (error) {
  app.log.error({ error }, 'listen failed');
  process.exit(1);
}
