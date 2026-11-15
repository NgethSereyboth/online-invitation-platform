import assert from 'node:assert/strict';
import test from 'node:test';

import { buildApp } from '../app.mjs';
import { safeRequestId } from '../lib/headers.mjs';

test('a safe inbound request id is reflected, as Python does', () => {
  assert.equal(safeRequestId('trace-123.abc:def_x'), 'trace-123.abc:def_x');
});

test('unsafe characters are stripped and long ids are truncated to 80', () => {
  assert.equal(safeRequestId('a b<script>c\n'), 'abscriptc');
  assert.equal(safeRequestId('x'.repeat(200)).length, 80);
});

test('no usable inbound id falls back to 32 lowercase hex', () => {
  assert.match(safeRequestId(''), /^[0-9a-f]{32}$/);
  assert.match(safeRequestId(undefined), /^[0-9a-f]{32}$/);
  assert.match(safeRequestId('<>'), /^[0-9a-f]{32}$/);
});

test('every response carries the id and the security header set', async () => {
  const app = buildApp();
  try {
    const health = await app.inject({ method: 'GET', url: '/api/health', headers: { 'x-request-id': 'route-42' } });
    assert.equal(health.headers['x-request-id'], 'route-42');
    assert.equal(health.headers['x-content-type-options'], 'nosniff');
    assert.equal(health.headers['permissions-policy'], 'camera=(), microphone=(), geolocation=()');
    assert.match(health.headers['content-security-policy'], /default-src 'self'/);

    // HTTP itself rejects spaces and `!` in a header value, so exercise the
    // sanitiser with characters the transport allows but the id must not keep.
    const notFound = await app.inject({
      method: 'GET',
      url: '/no-such-path',
      headers: { 'x-request-id': 'bad/id<script>' },
    });
    assert.equal(notFound.statusCode, 404);
    assert.equal(notFound.headers['x-request-id'], 'badidscript');
  } finally {
    await app.close();
  }
});
