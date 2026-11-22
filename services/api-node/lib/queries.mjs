// The first ported slice: the two reads every request path needs before any
// route can move — a user by email and a guest by invitation+slug.
// Semantics are copied from core/db.py and core/crypto.py, not reinvented.
import { createHash } from 'node:crypto';

import { pythonLower, pythonStrip } from './pystr.mjs';

/** core.crypto.hash_for_lookup: None→None, ""→"", else sha256(lower(strip)). */
export function hashForLookup(plaintext) {
  if (plaintext === null || plaintext === undefined) return null;
  if (!plaintext) return '';
  return createHash('sha256').update(pythonStrip(pythonLower(plaintext)), 'utf8').digest('hex');
}

/**
 * Indexed-hash lookup with the legacy plaintext fallback. The fallback exists
 * only for rows the encryption migration has not converted yet, so it can be
 * deleted once every row carries an email_hash.
 */
export async function findUserByEmail(db, email) {
  if (!email) return null;
  const normalized = String(email).trim().toLowerCase();
  const first = await db.query('SELECT * FROM users WHERE email_hash=? LIMIT 1', [
    hashForLookup(normalized),
  ]);
  if (first.rows.length) return first.rows[0];
  const legacy = await db.query(
    "SELECT * FROM users WHERE lower(email)=? AND (email_hash IS NULL OR email_hash='') LIMIT 1",
    [normalized],
  );
  return legacy.rows[0] ?? null;
}

/** The check-in and public shell lookup: one guest inside one invitation. */
export async function findGuestBySlug(db, invitationId, slug) {
  const result = await db.query('SELECT name FROM guests WHERE invitation_id=? AND slug=?', [
    invitationId,
    slug,
  ]);
  return result.rows[0] ?? null;
}
