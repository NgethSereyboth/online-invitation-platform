// S7: guest bindings and the public document projection.
// merge_fields/apply_guest_bindings/guest_token_hash are copied from server.py.
import { createHash } from 'node:crypto';

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
