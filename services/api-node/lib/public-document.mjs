// S7: guest bindings and the public document projection.
// merge_fields/apply_guest_bindings/guest_token_hash are copied from server.py.
import { createHash, createHmac, randomBytes } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const MERGE_TOKEN = /\{\{\s*([\w.-]+)\s*\}\}/g;

/** merge_fields(): unknown keys and nulls collapse to "", as in Python. */
export function mergeFields(template, row) {
  const values = row && typeof row === 'object' ? row : {};
  return String(template ?? '').replace(MERGE_TOKEN, (_match, key) => {
    const value = values[key];
    return value === null || value === undefined ? '' : String(value);
  });
}

/**
 * Resolve every `guest.*`-bound object in both canvas groups the editor knows
 * about. Objects without a binding, and documents without any, are untouched.
 */
export function applyGuestBindings(document, guestRow) {
  if (!document || typeof document !== 'object' || Array.isArray(document) || !guestRow) return document;
  const groups = [document.objects ?? {}];
  for (const page of document.designPages ?? []) {
    if (page && typeof page === 'object') groups.push(page.objects ?? {});
  }
  for (const group of groups) {
    if (!group || typeof group !== 'object') continue;
    for (const object of Object.values(group)) {
      if (!object || typeof object !== 'object') continue;
      const binding = String(object.contentBinding ?? '');
      if (!binding.startsWith('guest.')) continue;
      const template = object.html !== undefined && object.html !== null ? object.html : object.text;
      if (template === null || template === undefined) continue;
      const merged = mergeFields(template, guestRow);
      object.html = merged;
      if ('text' in object) object.text = merged;
    }
  }
  return document;
}

/** guest_token_hash(): sha256 of the raw token, hex. */
export function guestTokenHash(token) {
  return createHash('sha256').update(String(token ?? ''), 'utf8').digest('hex');
}

/**
 * persistent_data_secret("EINVITE_GUEST_TOKEN_SECRET", ".guest-token-secret"):
 * personal links are HMACs under this key, so both runtimes must hold the same
 * one or a link minted by Python would stop resolving on Node.
 */
export function resolveGuestTokenSecret({ env = process.env, dataDir = env.EINVITE_DATA_DIR } = {}) {
  const configured = String(env.EINVITE_GUEST_TOKEN_SECRET ?? '').trim();
  if (configured) return configured;
  if (!dataDir) return randomBytes(36).toString('base64url');
  const path = join(dataDir, '.guest-token-secret');
  try {
    const stored = readFileSync(path, 'utf8').trim();
    if (stored) return stored;
  } catch {
    /* missing sidecar falls through to generation */
  }
  const value = randomBytes(36).toString('base64url');
  try {
    mkdirSync(dataDir, { recursive: true });
    writeFileSync(path, value, { encoding: 'utf8', mode: 0o600 });
    return value;
  } catch {
    return value;
  }
}

/**
 * guest_token_value(): url-safe base64 of HMAC-SHA256("<id>|<salt>|<version>"),
 * unpadded and truncated to 32 characters.
 */
export function guestTokenValue(guestId, tokenSalt, tokenVersion = 1, secret = resolveGuestTokenSecret()) {
  const payload = `${guestId}|${tokenSalt}|${Math.trunc(Number(tokenVersion || 1))}`;
  return createHmac('sha256', secret).update(payload, 'utf8').digest('base64url').slice(0, 32);
}
