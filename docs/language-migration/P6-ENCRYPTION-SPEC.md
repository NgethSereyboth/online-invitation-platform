# P6 — Field-encryption byte-compatibility spec (blocks S5)

**Date:** 2026-11-12 · **Plan:** `language-optimization-plan-v3.1.md` §4 (P6), §5 (S5)
**Source of truth:** `src/python/core/crypto.py`, `src/python/core/db.py`,
`scripts/migrate_encrypt_sensitive_fields.py` — read in full, line numbers cited.
**Status:** spec **written and reviewed against the code**. It is not a port; S5 still needs
a Node implementation and the bidirectional proof in §9.

> S5 is the step the plan says is "most likely to silently corrupt data — never compress it".
> Anything below marked **⚠** differs from the plan text or from `docs/NEXT-WORK.md` and is a
> decision for the owner, not for the implementation.

---

## 1. Key material and resolution

| Order | Source | Condition | Result | `key_source()` |
|---|---|---|---|---|
| 1 | `EINVITE_FIELD_ENCRYPTION_KEY` | present **and** a valid Fernet key | use it | `env` |
| 2 | `EINVITE_FIELD_ENCRYPTION_KEY` | present but **invalid** | **a freshly generated, unpersisted key** | `env-invalid` |
| 3 | `<EINVITE_DATA_DIR>/.field-encryption-key` | file exists and is valid | use it | `sidecar` |
| 4 | same path, absent | writable directory | generate, write it, `chmod 0600` | `generated` |
| 5 | same path, `OSError` | read-only data dir | process-local generated key | `ephemeral` |

Key format: 32 random bytes, urlsafe base64, 44 characters, as produced by
`Fernet.generate_key()`. A second, **decrypt-only** key may be supplied in
`EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS` for a rotation window; it is never used to encrypt.

### 1.1 ⚠ Finding 1 — a malformed key is worse than documented

`NEXT-WORK.md` #13 says a malformed `EINVITE_FIELD_ENCRYPTION_KEY` "logs `source=env-invalid`
and falls back to the data-dir key". **The code does not do that.** `_load_or_create_key`
returns `_generate_key(), "env-invalid"` immediately — it does not fall through to step 3 and
does not write the key anywhere (`core/crypto.py:96–101`).

Consequences, in order of discovery:

1. Writes after boot are encrypted under a key that exists only in this process.
2. On restart that key is gone, so those rows cannot be decrypted.
3. `decrypt_field` never raises: it returns the input unchanged when both keys fail
   (`core/crypto.py:224–236`), so `reveal` hands handlers the literal `gAAAAA…` token.
   Nothing crashes; the data simply reads as base64 garbage.

The plan's S5 says to match "Python's documented soft-fail (open defect #13)". There is no
soft fallback to match — there is an ephemeral-key path. **Node must not invent a third
behaviour.** This needs the owner answer that #13 already asks for (refuse to boot vs keep a
documented fallback), and the answer should be applied to Python and Node together.

---

## 2. Token format (Fernet, RFC-style, public)

A token is urlsafe-base64 (no padding stripped) of:

| Offset | Length | Content |
|---|---|---|
| 0 | 1 | version byte `0x80` |
| 1 | 8 | timestamp, **big-endian uint64, seconds** |
| 9 | 16 | AES IV |
| 25 | n | AES-128-CBC ciphertext of the UTF-8 plaintext, PKCS7 padded |
| 25+n | 32 | HMAC-SHA256 over bytes `0..25+n` (version‖timestamp‖IV‖ciphertext) |

- AES key and HMAC key are both derived from the 32-byte Fernet key: the first 16 bytes are
  the AES key, the second 16 are the HMAC key.
- Verification uses a **constant-time** compare of the full 32-byte HMAC.
- Fernet rejects a token whose timestamp is more than 60 seconds in the future; the Python
  library applies that check, so a Node implementation must too or clock-skew behaviour
  diverges.
- This is why `CIPHERTEXT_PREFIX = "gAAAAA"` (`core/crypto.py:240`): base64 of `0x80` plus the
  first timestamp bytes. The prefix is a **shape test, not an integrity test**.

---

## 3. Operations and their exact edge semantics

| Input | `encrypt_field` | `decrypt_field` |
|---|---|---|
| `None` | `None` | `None` |
| `""` | `""` (no token) | `""` |
| non-empty str, encryption **enabled** | new token | plaintext, or the input unchanged if it is not a decryptable token |
| non-empty str, `EINVITE_FIELD_ENCRYPTION` ∈ {0,false,no,off} | the input unchanged | still decrypts |
| non-string | not reached — `protect()` passes non-strings through | — |

Two properties the Node port must copy exactly:

1. **Decryption never throws.** Any failure returns the original string. Every "invalid
   ciphertext" path is silent by design.
2. **`protect()` is idempotent by shape**: it encrypts only when the value is a non-empty
   string that does **not** already start with `gAAAAA` (`core/db.py:110–115`). A plaintext
   that happens to start with `gAAAAA` is stored as-is and will never be encrypted. That is a
   real (if unlikely) hole; it exists in Python and must either be preserved or fixed on both
   sides with owner sign-off.

Encryption enabled means "not explicitly off": the default is **on**
(`core/crypto.py:76–80`).

---

## 4. Lookup hashing — deterministic, so it is the compatibility anchor

```
hash_for_lookup(None) = None
hash_for_lookup("")   = ""        # explicit empty guard — NOT sha256("")**
hash_for_lookup(s)    = sha256( s.lower().strip().encode("utf-8") ).hexdigest()
```

** An implementation that mirrors the formula without the guard produces
`e3b0c442…` for the empty string. That is the value a naive Node port returns, and it is
wrong. This table was corrected against the module after a first draft carried the naive
value; the guard is at `core/crypto.py:216–218`.

Real vectors, printed by `core.crypto.hash_for_lookup` itself:

| Input | `email_hash` |
|---|---|
| `None` | `None` |
| `""` | `""` (empty) |
| `user@example.com` | `b4c9a289323b21a01c3e940f150eb9b8c542587f1abfd8f0e1cc1ffc5e475514` |
| `  User@Example.COM  ` | `b4c9a289323b21a01c3e940f150eb9b8c542587f1abfd8f0e1cc1ffc5e475514` |
| `srey@example.kh` | `fea0c569a9c1a8a8f43e9aa498f8542335f88ab9b6316882fd37f27fb05f0f48` |

`email_hash` is the indexed lookup column for `users`; `users.email` holds the token. Lookup
falls back to the plaintext column only when `email_hash` is empty. Node must reproduce
`.lower()` (Python's Unicode case folding) and `.strip()` exactly — a JS `toLowerCase()`
differs from Python's `lower()` for a few code points, so the parity test must include
non-ASCII addresses, not only ASCII ones.

---

## 5. Read boundary — where decryption happens

`core/db.py` wraps the connection: every fetched row passes through `reveal_row`, which
applies `reveal` to **every value in the row, whatever its column name**
(`core/db.py:160–176`). The rule is intentionally shape-based so that a column added later
cannot be forgotten on read.

Rows come back as `SensitiveRow`, a `dict` subclass that also supports positional access and
iterates its values (`core/db.py:128–158`) because callers rely on `sqlite3.Row` semantics.
A Node port needs the same ordering/`len`/`dict()` behaviour or handler code that indexes
rows positionally will silently misread.

**Consequence for S5:** the Node data layer must decrypt at the same boundary, not per
handler. A per-handler `decrypt()` is exactly the "a handler must not be able to forget"
failure the plan warns about.

---

## 6. Write boundary — explicit, and one column is outside the map

Writes are **not** intercepted. `protect()` is called explicitly at the statement that writes
each protected column. Verified call sites in `src/python/server.py`:

| Line | Statement | Column |
|---|---|---|
| 7401 | `INSERT INTO users(…)` | `users.email` |
| 9159 | `INSERT INTO guests(…)` | `guests.phone`, `guests.email` |
| 8800 | `UPDATE guests SET …` | `guests.phone`, `guests.email` |
| 11779 | outbound delivery attempt | `delivery_attempts.recipient` |
| 2298 | audit event | `audit_events.metadata_json` |
| 8547 | invitation edit history | `invitation_edit_history.diff_json` |
| **7628, 7639** | webhook endpoint create / rotate | **`webhook_endpoints.secret`** |

The declared map is smaller than reality:

```python
PROTECTED_COLUMNS = {
    "users": ("email",),
    "guests": ("email", "phone"),
    "delivery_attempts": ("recipient",),
    "audit_events": ("metadata_json",),
    "invitation_edit_history": ("diff_json",),
}
```

### 6.1 ⚠ Finding 2 — `webhook_endpoints.secret` is encrypted but invisible to rotation

`server.py` encrypts the webhook signing secret with `protect()` (twice), yet the column is in
neither `PROTECTED_COLUMNS` nor the rotation script's `SENSITIVE_COLUMNS`
(`scripts/migrate_encrypt_sensitive_fields.py:64–71`).

Reads still work, because `reveal` is shape-based. **Rotation does not**: `--reencrypt`
walks only the six listed columns, so after a key rotation and removal of
`…_KEY_PREVIOUS`, existing webhook secrets can no longer be decrypted and HMAC signing for
those endpoints breaks — silently, per §3's never-throw rule.

The plan's S5 column list therefore needs correcting from six to seven. Whether the fix is
"add the column to the map and the script" or "stop encrypting it" is an owner decision; the
Node port must not pick one on its own.

`protect_row_columns(columns, values)` exists as a write-side helper (`core/db.py:178–193`)
but has **no call sites** — writes are all explicit. Do not treat it as the established
pattern.

---

## 7. Rotation

1. Set the new key in `EINVITE_FIELD_ENCRYPTION_KEY`, move the old one to
   `EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS`.
2. Both keys are live: reads try the active key then the previous; writes use the active key.
3. `scripts/migrate_encrypt_sensitive_fields.py --reencrypt` rewrites rows the active key
   cannot read, reporting `unreadable` counts (subject to Finding 2).
4. Unset the previous key only after `unreadable` is zero.
5. `--rollback` restores from the `<column>_plaintext_backup` columns (30-day retention).

`is_current_key_ciphertext()` is the predicate that selects rotation candidates: prefix-shaped
**and** decryptable by the active key (`core/crypto.py:246–258`). Its asymmetry (a
previous-key row decrypts but fails this check) is deliberate and must survive the port.

---

## 8. Diagnostics that must not leak the key

`key_source()` returns the reason string, `key_fingerprint()` the first 12 hex characters of
`sha256(key)`. Both are used by preflight/logging. Node must expose equivalents with the same
values for the same key, and must never log the key itself.

---

## 9. The proof S5 owes (unchanged by this spec, now testable)

| Test | Pass condition |
|---|---|
| Python → Node | Node decrypts a token written by Python, for all 7 columns |
| Node → Python | Python decrypts a token written by Node |
| Edge values | `None`, `""`, 1-character, maximum-length, Khmer text, emoji |
| Mixed-state DB | plaintext rows and token rows in one table both read correctly; nothing double-encrypts |
| Plaintext-leak scan | after every Node write test, no protected column contains a value that is neither empty nor `gAAAAA…` |
| Rotation | a row under the previous key still reads; `is_current_key_ciphertext` returns false for it |
| Hash parity | the four vectors in §4, plus non-ASCII addresses |
| Malformed key | Node matches whatever the owner decides in §1.1 — not the current Python accident |

Implementation constraint from the plan: use `node:crypto` directly. Fernet is small enough
that a package is not required, and D2 (dependency override) is still unanswered.

---

## 10. What this spec does not decide

- **D2**: a Node implementation may add no package.
- **#13 / §1.1**: fail-fast or documented fallback for a malformed key — owner.
- **§6.1**: rotate the webhook secret or stop encrypting it — owner.
- **§3**: whether to keep the `gAAAAA`-prefixed-plaintext hole — owner, and it must be fixed
  on both sides or neither.
