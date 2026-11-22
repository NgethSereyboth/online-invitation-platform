import assert from 'node:assert/strict';
import test from 'node:test';

import {
  adminOverview,
  auditEventsCsv,
  auditFilterTimestamp,
  getAdminJob,
  hashForLookup,
  listAdminInvitations,
  listAdminUsersPage,
  listAuditEvents,
  maskEmail,
  pyInt,
  pySlice,
  pyTruthy,
} from '../lib/admin-reads.mjs';
import { canonicalJson } from '../lib/audit.mjs';
import { pythonLower, pythonStrip } from '../lib/pystr.mjs';

function fakeDb(rowsFor) {
  const calls = [];
  return {
    calls,
    async query(sql, params = []) {
      calls.push({ sql, params });
      return { rows: typeof rowsFor === 'function' ? rowsFor(sql, params) : rowsFor };
    },
  };
}

test('maskEmail follows Python partition and first-code-point rules', () => {
  assert.equal(maskEmail('ada@example.test'), 'a***@example.test');
  assert.equal(maskEmail('@example.test'), '***@example.test');
  assert.equal(maskEmail('no-at-sign'), '***');
  assert.equal(maskEmail(''), '***');
  assert.equal(maskEmail(null), '***');
  assert.equal(maskEmail('😀x@example.test'), '😀***@example.test');
});

test('hashForLookup hashes the lowercased, stripped text', () => {
  assert.equal(
    hashForLookup('  ADA@Example.Test '),
    'b97222ea69dadf792baa97fa768ecb840a0023714c831ab1328838cba9f7f437',
  );
  assert.equal(hashForLookup(''), '');
  assert.equal(hashForLookup(null), null);
  // Python lower + strip: U+00A0 is stripped, a BOM is not.
  assert.equal(hashForLookup('\u00a0A@B\u00a0'), hashForLookup('a@b'));
  assert.notEqual(hashForLookup('\ufeffA@B'), hashForLookup('a@b'));
});

test('pyInt accepts signs and whitespace but not decimals', () => {
  assert.equal(pyInt(' 25 '), 25);
  assert.equal(pyInt('+7'), 7);
  assert.equal(pyInt('-3'), -3);
  assert.equal(pyInt('2.5'), null);
  assert.equal(pyInt('abc'), null);
  assert.equal(pyInt(''), null);
});

test('pySlice and pyTruthy count and judge like Python', () => {
  assert.equal(pySlice('😀ab', 2), '😀a');
  assert.equal(pyTruthy(''), false);
  assert.equal(pyTruthy(0), false);
  assert.equal(pyTruthy([]), false);
  assert.equal(pyTruthy({}), false);
  assert.equal(pyTruthy('0'), true);
  assert.equal(pyTruthy([0]), true);
});

test('audit date filters match digits, dates and rejection', () => {
  assert.equal(auditFilterTimestamp('1760000000000'), 1760000000000);
  assert.equal(auditFilterTimestamp('2000-1-5'), new Date(2000, 0, 5).getTime());
  assert.equal(auditFilterTimestamp('2026-02-29'), null);
  assert.equal(auditFilterTimestamp('2024-02-29'), new Date(2024, 1, 29).getTime());
  assert.equal(auditFilterTimestamp('yesterday'), null);
  assert.equal(auditFilterTimestamp('-5'), null);
});

test('canonicalJson sorts keys at every level like json.dumps(sort_keys=True)', () => {
  assert.equal(
    canonicalJson({ b: 1, a: { d: 2, c: [3, { f: 4, e: 5 }] } }),
    '{"a":{"c":[3,{"e":5,"f":4}],"d":2},"b":1}',
  );
  assert.equal(canonicalJson({ admin: true, count: 2 }), '{"admin":true,"count":2}');
});

test('auditEventsCsv quotes minimally and ends every row with CRLF', () => {
  const body = auditEventsCsv([
    {
      id: 'a1',
      created_at: 1760000000123,
      user_id: null,
      action: 'admin.users_unmasked',
      target_type: 'user',
      target_id: '',
      ip_address: '127.0.0.1',
      metadata_json: '{"admin":true,"note":"a,b\\"c"}',
    },
  ]);
  assert.equal(
    body,
    'id,timestamp_iso,user_id,action,target_type,target_id,ip_address,metadata\r\n' +
      'a1,2025-10-09T08:53:20Z,,admin.users_unmasked,user,,127.0.0.1,"{""admin"":true,""note"":""a,b\\""c""}"\r\n',
  );
});

test('adminOverview keeps the seven counts as numbers', async () => {
  const counts = [7, 4, 3, 9, 2, 11, 5];
  const db = fakeDb(() => [{ c: String(counts.shift()) }]);
  assert.deepEqual(await adminOverview(db), {
    users: 7,
    invitations: 4,
    publishedInvitations: 3,
    templates: 9,
    marketplaceTemplates: 2,
    rsvps: 11,
    assets: 5,
  });
  assert.equal(db.calls.length, 7);
});

test('listAdminUsersPage masks, reveals and pages on (created_at, id)', async () => {
  const rows = [
    {
      id: 'u2',
      email: 'enc-b@example.test',
      role: 'admin',
      plan: 'studio',
      upload_enabled: 1,
      created_at: 200,
      suspended_at: null,
      force_mfa: 0,
      invitation_count: '2',
      template_count: '1',
    },
    {
      id: 'u1',
      email: 'enc-a@example.test',
      role: 'customer',
      plan: 'free',
      upload_enabled: 0,
      created_at: 100,
      suspended_at: 50,
      force_mfa: 1,
      invitation_count: '0',
      template_count: '0',
    },
  ];
  const db = fakeDb(rows);
  const revealed = (value) => String(value).replace('enc-', '');
  const page = await listAdminUsersPage(
    db,
    { limit: 1, search: 'ada@example.test', cursor: { created: 300, id: 'u9' } },
    revealed,
  );
  assert.deepEqual(page.items[0].email, 'b***@example.test');
  assert.equal(page.items[0].invitationCount, 2);
  assert.equal(page.items[0].suspended, false);
  assert.deepEqual(page, { items: page.items, nextCursor: '200:u2', hasMore: true });
  assert.match(db.calls[0].sql, /LOWER\(u\.email\) LIKE \? OR u\.email_hash = \?/);
  assert.match(db.calls[0].sql, /u\.created_at < \? OR \(u\.created_at = \? AND u\.id < \?\)/);
  assert.equal(db.calls[0].params[0], '%ada@example.test%');
  assert.equal(db.calls[0].params[1], hashForLookup('ada@example.test'));
  assert.deepEqual(db.calls[0].params.slice(2), [300, 300, 'u9', 2]);
});

test('listAdminInvitations falls back on a malformed or untitled draft', async () => {
  const db = fakeDb([
    {
      id: 'i1',
      slug: 'one',
      updated_at: 2,
      archived: 0,
      views: 3,
      access_mode: 'unlisted',
      is_published: 1,
      owner_email: 'enc-a@b',
      draft_json: '{"fields":{"names":"Ada & Bo"}}',
    },
    {
      id: 'i2',
      slug: 'two',
      updated_at: 1,
      archived: 1,
      views: 0,
      access_mode: 'unlisted',
      is_published: 0,
      owner_email: null,
      draft_json: 'not json',
    },
  ]);
  const rows = await listAdminInvitations(db, (value) => String(value).replace('enc-', ''));
  assert.equal(rows[0].title, 'Ada & Bo');
  assert.equal(rows[0].ownerEmail, 'a@b');
  assert.equal(rows[1].title, 'Untitled invitation');
  assert.equal(rows[1].published, false);
  assert.equal(rows[1].archived, true);
});

test('listAuditEvents builds bound filters and rejects a bad date', async () => {
  const db = fakeDb([
    {
      id: 'e1',
      user_id: 'u1',
      action: 'admin.users_unmasked',
      target_type: 'user',
      target_id: '',
      metadata_json: 'enc-{"admin":true}',
      ip_address: '127.0.0.1',
      created_at: 10,
    },
  ]);
  const result = await listAuditEvents(
    db,
    { user: 'u1', action: 'admin.users_unmasked', ip: '127.0.0.1', adminOnly: '1', limit: 5 },
    (value) => String(value).replace('enc-', ''),
  );
  assert.deepEqual(result.items[0].metadata, { admin: true });
  assert.equal(result.rows[0].metadata_json, '{"admin":true}');
  assert.match(db.calls[0].sql, /user_id=\?/);
  assert.match(db.calls[0].sql, /\(metadata_json LIKE \? OR admin_only=1\)/);
  assert.deepEqual(db.calls[0].params, ['u1', 'admin.users_unmasked', '127.0.0.1', '%"admin":true%', 5]);

  const rejected = await listAuditEvents(fakeDb([]), { from: 'not-a-date', limit: 5 });
  assert.equal(rejected, null);
});

test('getAdminJob returns null on a missing row and parses a payload', async () => {
  assert.equal(await getAdminJob(fakeDb([]), 'missing'), null);
  const job = await getAdminJob(
    fakeDb([
      {
        id: 'j1',
        kind: 'webhook.deliver',
        payload_json: '{"endpointId":"e1"}',
        state: 'queued',
        attempts: '2',
        last_error: '',
        created_at: 1,
        updated_at: 2,
      },
    ]),
    'j1',
  );
  assert.deepEqual(job.payload, { endpointId: 'e1' });
  assert.equal(job.attempts, 2);
});

test('python helpers keep Python whitespace and lower semantics', () => {
  assert.equal(pythonStrip('\u00a0 a \u00a0'), 'a');
  assert.equal([...pythonLower('ΟΔΟΣ')].at(-1), '\u03c2');
});
