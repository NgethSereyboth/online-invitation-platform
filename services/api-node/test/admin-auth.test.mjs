import assert from 'node:assert/strict';
import test from 'node:test';

import { checkAdminIpAllowed, parseAdminAllowlist } from '../lib/admin-auth.mjs';

test('an empty allowlist allows every client, as Python does', () => {
  assert.equal(checkAdminIpAllowed('203.0.113.9', ''), true);
  assert.equal(checkAdminIpAllowed('127.0.0.1', undefined), true);
});

test('bare IPs and CIDRs both match, IPv6 included', () => {
  assert.equal(checkAdminIpAllowed('127.0.0.1', '127.0.0.1/32,::1'), true);
  assert.equal(checkAdminIpAllowed('10.1.2.3', '10.0.0.0/8'), true);
  assert.equal(checkAdminIpAllowed('192.168.1.5', '10.0.0.0/8'), false);
  assert.equal(checkAdminIpAllowed('::1', '127.0.0.1/32,::1'), true);
  assert.equal(checkAdminIpAllowed('::ffff:10.9.9.9', '10.0.0.0/8'), true);
});

test('malformed entries are rejected at parse time', () => {
  assert.throws(() => parseAdminAllowlist('10.0.0.0/8,nope'), /Invalid CIDR\/IP/);
  assert.throws(() => parseAdminAllowlist('10.0.0.0/33'), /Invalid CIDR\/IP/);
});
