import assert from 'node:assert/strict';
import test from 'node:test';

import { extractEventDate, lastNDays, pyRound, utcDay } from '../lib/analytics-queries.mjs';

test('pyRound rounds halves to even, like Python round()', () => {
  assert.equal(pyRound(0.5, 0), 0);
  assert.equal(pyRound(1.5, 0), 2);
  assert.equal(pyRound(2.675, 2), 2.68);
  assert.equal(pyRound(66.66, 1), 66.7);
});

test('utcDay and lastNDays are UTC, oldest first', () => {
  const now = Date.UTC(2026, 0, 3, 12, 0, 0);
  assert.equal(utcDay(now), '2026-01-03');
  assert.deepEqual(lastNDays(now, 3), ['2026-01-01', '2026-01-02', '2026-01-03']);
});

test('extractEventDate checks the four document paths and swallows bad values', () => {
  assert.equal(extractEventDate({ fields: { eventDate: '1760000000000' } }), 1760000000000);
  assert.equal(extractEventDate({ meta: { eventDate: 1760000000001 } }), 1760000000001);
  assert.equal(extractEventDate({ settings: { eventDate: 'nope' } }), 0);
  assert.equal(extractEventDate(null), 0);
});
