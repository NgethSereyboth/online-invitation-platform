import assert from 'node:assert/strict';
import test from 'node:test';

import { canEditInvitation, canManageInvitation, canReadInvitation, roleFromRow } from '../lib/authz.mjs';
import { guestTokenValue } from '../lib/public-document.mjs';

test('guest tokens are deterministic 32-character url-safe HMACs', () => {
  const token = guestTokenValue('g-1', 'salt', 1, 'secret');
  assert.equal(token, guestTokenValue('g-1', 'salt', 1, 'secret'));
  assert.equal(token.length, 32);
  assert.match(token, /^[A-Za-z0-9_-]{32}$/);
  assert.notEqual(token, guestTokenValue('g-1', 'other-salt', 1, 'secret'));
  assert.notEqual(token, guestTokenValue('g-1', 'salt', 2, 'secret'));
  assert.notEqual(token, guestTokenValue('g-1', 'salt', 1, 'other-secret'));
});

test('a guest token never contains base64 padding', () => {
  for (let index = 0; index < 20; index += 1) {
    assert.doesNotMatch(guestTokenValue(`guest-${index}`, `salt-${index}`, 1, 'secret'), /=/);
  }
});

test('role resolution mirrors owner-then-collaborator, with deletion demoting the owner', () => {
  const ownerRow = { owner_id: 'u1', deleted_at: null, collaborator_role: null };
  assert.equal(roleFromRow(ownerRow, 'u1'), 'owner');
  assert.equal(roleFromRow({ ...ownerRow, deleted_at: 123 }, 'u1'), null);
  assert.equal(
    roleFromRow({ owner_id: 'u2', deleted_at: null, collaborator_role: 'manager' }, 'u1'),
    'manager',
  );
  assert.equal(roleFromRow(null, 'u1'), null);
});

test('role predicates match Python\'s sets', () => {
  for (const role of ['owner', 'content', 'designer', 'manager']) {
    assert.equal(canReadInvitation(role), true);
    assert.equal(canEditInvitation(role), true);
  }
  assert.equal(canReadInvitation('viewer'), true);
  assert.equal(canEditInvitation('viewer'), false);
  assert.equal(canManageInvitation('manager'), true);
  assert.equal(canManageInvitation('content'), false);
  assert.equal(canManageInvitation(null), false);
});
