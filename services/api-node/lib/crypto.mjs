// S5: byte-compatible field encryption. The token format is public (spec at
// docs/language-migration/P6-ENCRYPTION-SPEC.md §2), so this uses node:crypto
// and adds no package:
//   0x80 | uint64be(seconds) | 16B IV | AES-128-CBC ciphertext | HMAC-SHA256
// The first 16 key bytes sign (HMAC), the last 16 encrypt (AES-128) — the
// Fernet spec's split, which is the opposite of the intuitive reading.
import {
  createCipheriv,
  createDecipheriv,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from 'node:crypto';
import { chmodSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export const CIPHERTEXT_PREFIX = 'gAAAAA';
const VERSION = 0x80;
const KEY_FILE = '.field-encryption-key';
const MAX_CLOCK_SKEW_SECONDS = 60;

export class InvalidToken extends Error {
  constructor(message = 'Invalid Fernet token') {
    super(message);
    this.name = 'InvalidToken';
  }
}

function isProduction(env = process.env) {
  const value = String(env.EINVITE_PRODUCTION ?? '0').trim().toLowerCase();
  return value === '1' || value === 'true' || value === 'yes';
}

/** 32 bytes, urlsafe base64, exactly as Fernet.generate_key() emits. */
export function isValidKey(value) {
  if (typeof value !== 'string') return false;
  try {
    const decoded = Buffer.from(value, 'base64url');
    return decoded.length === 32 && /^[A-Za-z0-9_-]{43}=?$/.test(value);
  } catch {
    return false;
  }
}

export function generateKey() {
  return randomBytes(32).toString('base64url');
}

function toFernetBase64(buffer) {
  return buffer.toString('base64url').padEnd(Math.ceil(buffer.length / 3) * 4, '=');
}

function fromFernetBase64(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_\-+/=]+$/.test(value)) throw new InvalidToken();
  return Buffer.from(value, 'base64url');
}

export function encryptWithKey(plaintext, key, nowSeconds = Math.floor(Date.now() / 1000)) {
  if (typeof plaintext !== 'string') throw new TypeError('plaintext must be a string');
  const raw = Buffer.from(key, 'base64url');
  const hmacKey = raw.subarray(0, 16);
  const aesKey = raw.subarray(16, 32);
  const iv = randomBytes(16);
  const cipher = createCipheriv('aes-128-cbc', aesKey, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);

  const timestamp = Buffer.alloc(8);
  timestamp.writeBigUInt64BE(BigInt(nowSeconds));
  const basic = Buffer.concat([Buffer.from([VERSION]), timestamp, iv, ciphertext]);
  const signature = createHmac('sha256', hmacKey).update(basic).digest();
  return toFernetBase64(Buffer.concat([basic, signature]));
}

export function decryptWithKey(token, key, nowSeconds = Math.floor(Date.now() / 1000)) {
  const data = fromFernetBase64(token);
  if (data.length < 1 + 8 + 16 + 32) throw new InvalidToken();
  if (data[0] !== VERSION) throw new InvalidToken();
  const timestamp = Number(data.readBigUInt64BE(1));
  if (timestamp > nowSeconds + MAX_CLOCK_SKEW_SECONDS) throw new InvalidToken('Timestamp is in the future');
  const iv = data.subarray(9, 25);
  const ciphertext = data.subarray(25, data.length - 32);
  const signature = data.subarray(data.length - 32);
  const raw = Buffer.from(key, 'base64url');
  const expected = createHmac('sha256', raw.subarray(0, 16))
    .update(data.subarray(0, data.length - 32))
    .digest();
  if (!timingSafeEqual(signature, expected)) throw new InvalidToken('Signature mismatch');
  const decipher = createDecipheriv('aes-128-cbc', raw.subarray(16, 32), iv);
  const padded = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return padded.toString('utf8');
}

/**
 * Key resolution, mirroring core.crypto._load_or_create_key: env → sidecar →
 * generated-and-persisted, and (owner decision 2026-11-14) a malformed env key
 * refuses to boot in production while development keeps an ephemeral one.
 */
export function resolveKey({ dataDir = process.env.EINVITE_DATA_DIR, env = process.env } = {}) {
  const configured = String(env.EINVITE_FIELD_ENCRYPTION_KEY ?? '').trim();
  if (configured) {
    if (isValidKey(configured)) return { key: configured, source: 'env' };
    if (isProduction(env)) {
      throw new Error(
        'EINVITE_FIELD_ENCRYPTION_KEY is set but is not a valid Fernet key ' +
          '(32 urlsafe-base64 bytes). Refusing to start in production.',
      );
    }
    return { key: generateKey(), source: 'env-invalid' };
  }
  if (!dataDir) return { key: generateKey(), source: 'ephemeral' };
  const path = join(dataDir, KEY_FILE);
  try {
    const stored = readFileSync(path, 'utf8').trim();
    if (isValidKey(stored)) return { key: stored, source: 'sidecar' };
  } catch {
    /* missing file falls through to generation */
  }
  try {
    const key = generateKey();
    mkdirSync(dataDir, { recursive: true });
    writeFileSync(path, key, { encoding: 'utf8', mode: 0o600 });
    try {
      chmodSync(path, 0o600);
    } catch {
      /* best effort, as in Python */
    }
    return { key, source: 'generated' };
  } catch {
    return { key: generateKey(), source: 'ephemeral' };
  }
}

export function encryptionEnabled(env = process.env) {
  const value = String(env.EINVITE_FIELD_ENCRYPTION ?? '1').trim().toLowerCase();
  return !['0', 'false', 'no', 'off'].includes(value);
}

/** Stateful facade: one resolved key, an optional decrypt-only previous key. */
export function createFieldCipher({ env = process.env, dataDir = env.EINVITE_DATA_DIR } = {}) {
  const { key, source } = resolveKey({ env, dataDir });
  const previous = String(env.EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS ?? '').trim();
  const previousKey = isValidKey(previous) ? previous : null;
  const enabled = encryptionEnabled(env);

  const isToken = (value) => typeof value === 'string' && value.startsWith(CIPHERTEXT_PREFIX);

  return {
    keySource: source,
    enabled,
    hashState: { hasPrevious: Boolean(previousKey) },

    protect(value) {
      if (!enabled) return value;
      if (typeof value !== 'string' || !value || isToken(value)) return value;
      return encryptWithKey(value, key);
    },

    /** Never throws: returns the input unchanged when it cannot be decrypted. */
    reveal(value) {
      if (value === null || value === undefined) return value;
      if (typeof value !== 'string' || !value) return value;
      try {
        return decryptWithKey(value, key);
      } catch {
        if (previousKey) {
          try {
            return decryptWithKey(value, previousKey);
          } catch {
            /* fall through to the legacy plaintext path */
          }
        }
        return value;
      }
    },

    /** Applies reveal to every string value, whatever the column name. */
    revealRow(row) {
      if (row === null || row === undefined) return row;
      if (Array.isArray(row)) return row.map((value) => this.reveal(value));
      const out = {};
      for (const [column, value] of Object.entries(row)) out[column] = this.reveal(value);
      return out;
    },

    /** Rotation predicate: prefix-shaped *and* readable by the active key. */
    isCurrentKeyCiphertext(value) {
      if (!isToken(value)) return false;
      try {
        decryptWithKey(value, key);
        return true;
      } catch {
        return false;
      }
    },
  };
}
