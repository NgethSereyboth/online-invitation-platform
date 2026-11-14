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
  assert.equal(response.json().error, 'not_found');
});

test('non-GET on /healthz is a 404 (parity with the Python route table)', async (t) => {
  const app = buildApp();
  t.after(() => app.close());

  const response = await app.inject({ method: 'POST', url: '/healthz' });

  assert.equal(response.statusCode, 404);
});
