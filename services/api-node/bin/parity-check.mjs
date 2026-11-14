#!/usr/bin/env node
// Seeds a disposable PostgreSQL schema with the S4 fixtures and prints the
// ported queries' results as JSON, for tools/db-parity.py to diff against the
// Python backend reading the same rows from SQLite.
import { assertSchema, createDatabase } from '../lib/db.mjs';
import { findGuestBySlug, findUserByEmail, hashForLookup } from '../lib/queries.mjs';

const EMAILS = [
  'alice@example.com',
  '  ALICE@Example.com  ',
  'legacy@example.com',
  'other@example.com',
  'nobody@example.com',
  '',
  null,
];

const USERS = [
  {
    id: 'u-parity-alice',
    email: 'Alice@Example.com',
    email_hash: hashForLookup('alice@example.com'),
    created_at: 1700000000123,
    email_verified: 1,
    failed_login_attempts: 2,
    storage_used_bytes: 1234567890123,
  },
  {
    id: 'u-parity-legacy',
    email: 'Legacy@Example.com',
    email_hash: '',
    created_at: 1700000000000,
    email_verified: 0,
    failed_login_attempts: 0,
    storage_used_bytes: 0,
  },
  {
    id: 'u-parity-other',
    email: 'Other@Example.com',
    email_hash: hashForLookup('other@example.com'),
    created_at: 1700000000999,
    email_verified: 1,
    failed_login_attempts: 0,
    storage_used_bytes: 7,
  },
];

function projectUser(row) {
  if (!row) return null;
  return {
    id: row.id,
    email: row.email,
    created_at: row.created_at,
    created_at_type: typeof row.created_at,
    email_verified: row.email_verified,
    failed_login_attempts: row.failed_login_attempts,
    storage_used_bytes: row.storage_used_bytes,
  };
}

async function main() {
  const connectionString =
    process.argv[2] ?? process.env.EINVITE_DATABASE_URL ?? process.env.DATABASE_URL;
  const db = createDatabase({ connectionString });

  try {
    await assertSchema(db);
    await db.query("DELETE FROM guests WHERE invitation_id='inv-parity'");
    await db.query("DELETE FROM invitations WHERE id='inv-parity'");
    await db.query("DELETE FROM users WHERE id LIKE 'u-parity-%'");
    for (const user of USERS) {
      await db.query(
        'INSERT INTO users(id,email,email_hash,password_hash,salt,created_at,email_verified,failed_login_attempts,storage_used_bytes) VALUES(?,?,?,?,?,?,?,?,?)',
        [
          user.id,
          user.email,
          user.email_hash,
          'hash',
          'salt',
          user.created_at,
          user.email_verified,
          user.failed_login_attempts,
          user.storage_used_bytes,
        ],
      );
    }
    await db.query(
      "INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id) VALUES('inv-parity','inv-parity','{}',1,NULL)",
    );
    await db.query(
      "INSERT INTO guests(id,invitation_id,name,slug,token,created_at) VALUES('g-parity','inv-parity','Guest One','g-one','tok-g-one',1700000000000)",
    );

    const users = {};
    for (const email of EMAILS) {
      users[String(email)] = projectUser(await findUserByEmail(db, email));
    }
    const guest = await findGuestBySlug(db, 'inv-parity', 'g-one');
    const missingGuest = await findGuestBySlug(db, 'inv-parity', 'nope');

    process.stdout.write(
      JSON.stringify({
        users,
        guest: guest?.name ?? null,
        missingGuest: missingGuest?.name ?? null,
      }),
    );
  } finally {
    await db.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
