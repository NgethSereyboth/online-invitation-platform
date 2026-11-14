// S3: the Node service serves the mirrored shell pages and static assets with
// the same bytes and headers as the Python backend. API routes are still
// Python-owned except /healthz (S2) and /api/health (S3 navigation aid).
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import Fastify from 'fastify';

import { QueryDeadlineExceeded } from './lib/db.mjs';
import {
  pageFiles,
  pageForPath,
  quotePathSegment,
  renderPage,
  substitutePublicPlaceholders,
} from './lib/pages.mjs';
import { resolveAsset, sendAsset } from './lib/static.mjs';
import {
  PERMISSIONS_CHECKIN,
  PERMISSIONS_DEFAULT,
  applySecurityHeaders,
  jsonBody,
  newNonce,
} from './lib/headers.mjs';

export const SERVICE_NAME = 'einvite-api-node';
export const SERVICE_VERSION = '0.1.0';

/** The Python mirror is the single source of truth for both runtimes. */
export function defaultWebRoot() {
  if (process.env.EINVITE_WEB_ROOT) return resolve(process.env.EINVITE_WEB_ROOT);
  return fileURLToPath(new URL('../../src/python/', import.meta.url));
}

/** absolute_url(): PUBLIC_BASE_URL wins, otherwise the request authority. */
function absoluteUrl(request, path) {
  if (process.env.PUBLIC_BASE_URL) {
    return `${process.env.PUBLIC_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  }
  const host = request.headers.host;
  if (!host) return path;
  const proto = request.headers['x-forwarded-proto'] === 'https' ? 'https' : 'http';
  return `${proto}://${host}${path}`;
}

function readCriticalCss(webRoot) {
  try {
    return readFileSync(join(webRoot, 'critical.css'), 'utf8');
  } catch {
    return null;
  }
}

export function buildApp({ logger = false, webRoot = defaultWebRoot() } = {}) {
  const app = Fastify({ logger, trustProxy: true });
  const pages = pageFiles(webRoot);

  app.get('/healthz', async (_request, reply) => {
    reply.header('cache-control', 'no-store');
    return {
      status: 'ok',
      service: SERVICE_NAME,
      version: SERVICE_VERSION,
      uptimeSeconds: Math.floor(process.uptime()),
    };
  });

  // Python maps QueryDeadlineExceeded to 504 with this exact body and headers
  // (server.py database_timeout). Registered once, so every ported route that
  // queries inherits it rather than re-implementing the mapping.
  app.setErrorHandler((error, _request, reply) => {
    if (error instanceof QueryDeadlineExceeded) {
      const nonce = newNonce();
      applySecurityHeaders(reply, { nonce, permissions: PERMISSIONS_DEFAULT });
      const body = jsonBody({
        error: 'The request took too long to read from the database. Please retry.',
        code: 'database_timeout',
        requestId: reply.getHeader('x-request-id') ?? '',
      });
      reply.code(504);
      reply.header('retry-after', '1');
      reply.header('content-type', 'application/json; charset=utf-8');
      reply.header('content-length', String(Buffer.byteLength(body)));
      reply.send(body);
      return;
    }
    const nonce = newNonce();
    applySecurityHeaders(reply, { nonce, permissions: PERMISSIONS_DEFAULT });
    const body = jsonBody({ error: 'Internal server error' });
    reply.code(500);
    reply.header('content-type', 'application/json; charset=utf-8');
    reply.header('content-length', String(Buffer.byteLength(body)));
    reply.send(body);
  });

  // Same shape as Python's /api/health; the capability flags describe *this*
  // backend, so their values legitimately differ during the parallel run.
  app.get('/api/health', async (_request, reply) => {
    applySecurityHeaders(reply, { nonce: newNonce(), permissions: PERMISSIONS_DEFAULT });
    reply.header('content-type', 'application/json; charset=utf-8');
    reply.header('cache-control', 'no-store');
    return {
      ok: true,
      backend: 'node',
      database: 'none',
      assetStorage: 'local',
      redis: false,
      aiConfigured: false,
      smtpConfigured: false,
      dependencies: { pillow: false, qrcode: false, qrReady: false },
      uptimeSeconds: Math.floor(process.uptime()),
    };
  });

  app.route({
    method: ['GET', 'HEAD'],
    url: '/*',
    handler: async (request, reply) => {
      const nonce = newNonce();
      const pathname = request.url.split('?')[0];
      const permissions = pathname.includes('/checkin') ? PERMISSIONS_CHECKIN : PERMISSIONS_DEFAULT;

      // Pages first: a page name must not be shadowed by a mirrored file.
      const pageName = pageForPath(pathname);
      if (pageName) {
        const body = renderPage(pages, pageName, { nonce, criticalCss: readCriticalCss(webRoot) });
        if (body) {
          applySecurityHeaders(reply, { nonce, permissions });
          reply.header('content-type', 'text/html; charset=utf-8');
          reply.header('cache-control', 'no-cache');
          reply.header('content-length', String(body.length));
          reply.send(body);
          return reply;
        }
      }

      const asset = resolveAsset(webRoot, pathname);
      if (asset) {
        applySecurityHeaders(reply, { nonce, permissions });
        sendAsset(reply, request, asset);
        return reply;
      }

      // /i/<slug>: the public shell with placeholders filled. Invitations that
      // exist are still rendered by Python (S9 ports the document store), so
      // this serves the no-row branch: 404, uncached, noindex.
      if (pathname.startsWith('/i/')) {
        const slug = decodeURIComponent(pathname.slice(3).split('/')[0] || '');
        const publicUrl = absoluteUrl(request, `/i/${quotePathSegment(slug)}`);
        const imageFormat = 'png';
        const raw = renderPage(pages, 'public.html', { nonce, criticalCss: readCriticalCss(webRoot) });
        const body = raw
          ? Buffer.from(
              substitutePublicPlaceholders(raw.toString('utf8'), {
                slug,
                title: 'Invitation',
                description: 'You are invited to a special event.',
                imagePath: absoluteUrl(
                  request,
                  `/api/public/${quotePathSegment(slug)}/social-card-v0.${imageFormat}`,
                ),
                publicUrl,
                imageFormat,
              }),
              'utf8',
            )
          : null;
        applySecurityHeaders(reply, { nonce, permissions });
        reply.code(404);
        reply.header('content-type', 'text/html; charset=utf-8');
        reply.header('cache-control', 'no-store');
        reply.header('x-robots-tag', 'noindex');
        if (body) {
          reply.header('content-length', String(body.length));
          reply.send(body);
        } else {
          reply.send();
        }
        return reply;
      }

      const body = jsonBody({ error: 'Not found' });
      applySecurityHeaders(reply, { nonce, permissions });
      reply.code(404);
      reply.header('content-type', 'application/json; charset=utf-8');
      reply.header('cache-control', 'no-store');
      reply.header('content-length', String(Buffer.byteLength(body)));
      reply.send(body);
      return reply;
    },
  });

  return app;
}
