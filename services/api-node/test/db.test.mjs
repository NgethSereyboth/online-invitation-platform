import assert from 'node:assert/strict';
import test from 'node:test';

import { buildApp } from '../app.mjs';
import { QueryDeadlineExceeded, toPlaceholders, withDeadline } from '../lib/db.mjs';
import { hashForLookup } from '../lib/queries.mjs';

test('? placeholders become $n and literals are untouched', () => {
  assert.equal(toPlaceholders('SELECT * FROM users WHERE email_hash=?'), 'SELECT * FROM users WHERE email_hash=$1');
  assert.equal(
    toPlaceholders('SELECT * FROM guests WHERE invitation_id=? AND slug=?'),
    'SELECT * FROM guests WHERE invitation_id=$1 AND slug=$2',
  );
  // A '?' inside a string literal, a quoted identifier or a comment is data.
  assert.equal(toPlaceholders("SELECT 'what?' AS q WHERE id=?"), "SELECT 'what?' AS q WHERE id=$1");
  assert.equal(toPlaceholders('SELECT "?" FROM t WHERE a=?'), 'SELECT "?" FROM t WHERE a=$1');
  assert.equal(toPlaceholders('SELECT 1 -- why?\nWHERE a=?'), 'SELECT 1 -- why?\nWHERE a=$1');
  assert.equal(toPlaceholders('SELECT 1 /* ? */ WHERE a=?'), 'SELECT 1 /* ? */ WHERE a=$1');
  // Escaped quotes do not end the literal.
  assert.equal(toPlaceholders("SELECT 'it''s ?' AS s WHERE id=?"), "SELECT 'it''s ?' AS s WHERE id=$1");
});

test('hashForLookup matches core.crypto.hash_for_lookup', () => {
  // Vector printed by the Python module on 2026-11-14.
  assert.equal(
    hashForLookup('user@example.com'),
    'b4c9a289323b21a01c3e940f150eb9b8c542587f1abfd8f0e1cc1ffc5e475514',
  );
  assert.equal(hashForLookup('  USER@Example.com '), hashForLookup('user@example.com'));
  assert.equal(hashForLookup(''), '');
  assert.equal(hashForLookup(null), null);
});

test('withDeadline raises QueryDeadlineExceeded before the operation finishes', async () => {
  const slow = new Promise((resolve) => setTimeout(resolve, 500));
  await assert.rejects(() => withDeadline(25, () => slow), QueryDeadlineExceeded);
});

test('a database timeout becomes a 504 with Python body and headers', async (t) => {
  const app = buildApp();
  t.after(() => app.close());
  app.get('/api/boom', async () => {
    throw new QueryDeadlineExceeded();
  });
  await app.ready();

  const response = await app.inject({ method: 'GET', url: '/api/boom' });

  assert.equal(response.statusCode, 504);
  assert.equal(response.headers['retry-after'], '1');
  assert.match(response.headers['content-type'], /application\/json/);
  const body = response.json();
  assert.equal(body.error, 'The request took too long to read from the database. Please retry.');
  assert.equal(body.code, 'database_timeout');
  assert.equal(typeof body.requestId, 'string');
});
