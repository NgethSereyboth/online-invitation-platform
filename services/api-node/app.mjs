// S2 skeleton: the Node service owns exactly one route until S3 ports the
// static shell. Everything here is additive — removing the directory reverts it.
import Fastify from 'fastify';

export const SERVICE_NAME = 'einvite-api-node';
export const SERVICE_VERSION = '0.1.0';

/**
 * Build the app without listening, so tests can inject requests.
 * @param {{ logger?: boolean | object }} [options]
 */
export function buildApp({ logger = false } = {}) {
  const app = Fastify({
    logger,
    trustProxy: true,
  });

  app.get('/healthz', async (_request, reply) => {
    reply.header('cache-control', 'no-store');
    return {
      status: 'ok',
      service: SERVICE_NAME,
      version: SERVICE_VERSION,
      uptimeSeconds: Math.floor(process.uptime()),
    };
  });

  // The router in front of this service only forwards /healthz during S2.
  // Anything else is a JSON 404, mirroring the Python backend's API 404 shape.
  app.setNotFoundHandler(async (request, reply) => {
    reply.code(404).type('application/json');
    return { error: 'not_found', path: request.url };
  });

  return app;
}
