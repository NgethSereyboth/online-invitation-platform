import assert from 'node:assert/strict';
import test from 'node:test';

import {
  InvalidToken,
  createFieldCipher,
  decryptWithKey,
  encryptWithKey,
  generateKey,
} from '../lib/crypto.mjs';
import { pythonLower, pythonStrip } from '../lib/pystr.mjs';
import { hashForLookup } from '../lib/queries.mjs';

const KEY = generateKey();
const PREVIOUS = generateKey();

function cipherFor(env) {
  return createFieldCipher({ env, dataDir: undefined });
}

test('a token round-trips and stays inside the Fernet shape', () => {
  const token = encryptWithKey('café 🙂', KEY);
  assert.ok(token.startsWith('gAAAAA'));
  assert.equal(token.length % 4, 0, 'urlsafe base64 keeps its padding');
  assert.equal(decryptWithKey(token, KEY), 'café 🙂');
});

test('a token under another key is left untouched, never thrown', () => {
  const token = encryptWithKey('secret', KEY);
  const cipher = cipherFor({ EINVITE_FIELD_ENCRYPTION_KEY: PREVIOUS });
  assert.equal(cipher.reveal(token), token);
});

test('a token more than 60 s in the future is rejected, as Fernet does', () => {
  const future = encryptWithKey('secret', KEY, Math.floor(Date.now() / 1000) + 120);
  assert.throws(() => decryptWithKey(future, KEY), InvalidToken);
  assert.equal(cipherFor({ EINVITE_FIELD_ENCRYPTION_KEY: KEY }).reveal(future), future);
});

test('the previous key decrypts but is not a rotation candidate', () => {
  const old = encryptWithKey('rotate me', PREVIOUS);
  const cipher = cipherFor({
    EINVITE_FIELD_ENCRYPTION_KEY: KEY,
    EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS: PREVIOUS,
  });
  assert.equal(cipher.reveal(old), 'rotate me');
  assert.equal(cipher.isCurrentKeyCiphertext(old), false);
  assert.equal(cipher.isCurrentKeyCiphertext(cipher.protect('new')), true);
});

test('protect() is idempotent by shape and off-switchable', () => {
  const cipher = cipherFor({ EINVITE_FIELD_ENCRYPTION_KEY: KEY });
  const token = cipher.protect('value');
  assert.equal(cipher.protect(token), token);
  assert.equal(cipher.protect(''), '');
  assert.equal(cipher.protect(null), null);
  assert.equal(cipherFor({ EINVITE_FIELD_ENCRYPTION_KEY: KEY, EINVITE_FIELD_ENCRYPTION: '0' }).protect('x'), 'x');
});

test('revealRow decrypts every string column without naming them', () => {
  const cipher = cipherFor({ EINVITE_FIELD_ENCRYPTION_KEY: KEY });
  const row = { id: 'u1', email: cipher.protect('a@b.c'), guests: 3, note: 'plain' };
  assert.deepEqual(cipher.revealRow(row), { id: 'u1', email: 'a@b.c', guests: 3, note: 'plain' });
});

test('a malformed key refuses production but keeps development running', () => {
  assert.throws(
    () =>
      cipherFor({
        EINVITE_PRODUCTION: '1',
        EINVITE_FIELD_ENCRYPTION_KEY: 'not-a-key',
      }),
    /Refusing to start in production/,
  );
  const dev = cipherFor({ EINVITE_FIELD_ENCRYPTION_KEY: 'not-a-key' });
  assert.equal(dev.keySource, 'env-invalid');
});

test('pythonLower and pythonStrip follow Python, not JavaScript', () => {
  assert.equal(pythonLower('ΑΣ'), 'ας'); // Final_Sigma: JS gives 'ασ'
  assert.equal(pythonLower('ΣΣ'), 'σς');
  assert.equal(pythonLower('İstanbul'), 'i̇stanbul');
  assert.equal(pythonStrip('\ufeffkeep'), '\ufeffkeep'); // JS trim() drops the BOM
  assert.equal(pythonStrip('\u3000x\u3000'), 'x');
  assert.equal(
    hashForLookup('  User@Example.COM  '),
    'b4c9a289323b21a01c3e940f150eb9b8c542587f1abfd8f0e1cc1ffc5e475514',
  );
});
