import assert from 'node:assert/strict';
import test from 'node:test';

import { buildApp } from '../app.mjs';

test('GET /healthz returns 200 and a no-store body', async (t) => {
  const app = buildApp();
  t.after(() => app.close());

  const response = await app.inject({ method: 'GET', url: '/healthz' });

  assert.equal(response.statusCode, 200);
  assert.equal(response.headers['cache-control'], 'no-store');
  const body = response.json();
  assert.equal(body.status, 'ok');
  assert.equal(body.service, 'einvite-api-node');
  assert.equal(typeof body.uptimeSeconds, 'number');
});

test('unported routes are a JSON 404, not an HTML page', async (t) => {
  const app = buildApp();
  t.after(() => app.close());

  const response = await app.inject({ method: 'GET', url: '/api/events' });

  assert.equal(response.statusCode, 404);
  assert.match(response.headers['content-type'], /application\/json/);
  // Byte-shape parity with Python's json(): a space after the colon.
  assert.equal(response.body, '{"error": "Not found"}');
});

test('a page is served with the Python transform and CSP nonce', async (t) => {
  const app = buildApp();
  t.after(() => app.close());

  const response = await app.inject({ method: 'GET', url: '/checkin' });
  const nonce = /nonce-([A-Za-z0-9_-]+)/.exec(response.headers['content-security-policy'])[1];

  assert.equal(response.statusCode, 200);
  assert.equal(response.headers['cache-control'], 'no-cache');
  assert.equal(response.headers['permissions-policy'], 'camera=(self), microphone=(), geolocation=()');
  assert.match(response.body, /<meta name="einvite-backend" content="full"><base href="\/">/);
  assert.ok(response.body.includes(`nonce="${nonce}"`), 'the body nonce matches the header');
  assert.ok(
    response.body.includes(`nonce="${nonce}" data-critical`),
    'critical CSS is inlined and carries the nonce',
  );
});

test('/i/<slug> with no invitation is a 404 shell with no-store and noindex', async (t) => {
  const app = buildApp();
  t.after(() => app.close());

  const response = await app.inject({ method: 'GET', url: '/i/does-not-exist' });

  assert.equal(response.statusCode, 404);
  assert.equal(response.headers['cache-control'], 'no-store');
  assert.equal(response.headers['x-robots-tag'], 'noindex');
  assert.match(response.headers['content-type'], /text\/html/);
});

test('non-GET on /healthz is a 404 (parity with the Python route table)', async (t) => {
  const app = buildApp();
  t.after(() => app.close());

  const response = await app.inject({ method: 'POST', url: '/healthz' });

  assert.equal(response.statusCode, 404);
});
