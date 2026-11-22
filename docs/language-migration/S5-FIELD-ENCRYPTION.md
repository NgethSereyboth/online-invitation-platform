# S5 · Field-encryption compatibility

Status: **complete 2026-11-14** for the primitives and both directions. Plan reference: §5 S5;
spec: `P6-ENCRYPTION-SPEC.md`.

## What exists

```
services/api-node/lib/crypto.mjs     Fernet (node:crypto), key resolution, protect/reveal/revealRow,
                                     isCurrentKeyCiphertext, production refusal
services/api-node/lib/pystr.mjs      Python's lower() and strip(), needed by email_hash
services/api-node/bin/crypto-parity.mjs   Node half of the bidirectional proof
tools/fernet-parity.py               runs both real modules and diffs the results
```

No package was added: Fernet is AES-128-CBC plus HMAC-SHA256, both in `node:crypto`.

Copied deliberately from `core/crypto.py` and `core/db.py`, not reinterpreted:

- **Token shape** `0x80 | uint64be(seconds) | 16B IV | ciphertext | HMAC-SHA256`, urlsafe base64
  **with padding preserved** (`python`'s tokens end in `=`; dropping it would change the bytes).
- **Key halves:** the first 16 bytes sign, the last 16 encrypt — see the bug below.
- **Never throws:** `reveal` falls back to the previous key, then returns the input unchanged.
- **Shape idempotence:** `protect` leaves `None`, `""` and anything already `gAAAAA…` untouched.
- **Resolution order:** env → sidecar `.field-encryption-key` (0600) → generated → ephemeral, and
  a malformed env key **refuses to boot in production** (owner decision on #13), matching the
  Python change made earlier today. Development keeps the ephemeral path, as Python does.
- **Rotation:** `isCurrentKeyCiphertext` is prefix-shaped **and** readable by the active key, so
  a previous-key row decrypts but is not reported as a rotation candidate.
- **Lookup hashing:** `hash_for_lookup` needs Python's `str.lower()`/`str.strip()`, not JS's —
  Final_Sigma (`ΑΣ` → `ας`, where `toLowerCase()` yields `ασ`) and the BOM (kept by Python,
  stripped by `trim()`).

## Two bugs the verification caught

1. **Key halves were swapped.** The first implementation used bytes 0–15 for AES and 16–31 for
   HMAC. Every Python token failed with `Signature mismatch`; comparing both sides' HMACs showed
   they agreed with each other and disagreed with the stored signature, which located the fault
   in the split rather than in the encoding. Fixed to sign with 0–15 and encrypt with 16–31.
2. **`isProduction()` read the process env, not the injected one.** A cipher built with an
   explicit `env` would have skipped the production refusal entirely — the unit test failed and
   the function now takes the same env object as key resolution.

Neither would have been found by reading the spec; both needed the cross-runtime run.

## Verification (all run 2026-11-14)

| Check | Result |
|---|---|
| `tools/fernet-parity.py` | **11/11 identical**, 0 failing |
| Python writes → Node reads | 6 values round-trip (ASCII, accents, padded spaces, emoji + tab, 4 KB, empty) |
| Node writes → Python reads | same 6 values, decoded by `core.crypto.decrypt_field` |
| Previous-key rotation | old-key rows decrypt under the new active key; `isCurrentKeyCiphertext` reports **false** for all of them |
| Tampering | a token with a broken signature is returned **unchanged** by both sides, never raised |
| Prefix-shaped plaintext | `gAAAAA-not-a-real-token` is left alone by `protect()` on both sides |
| `hash_for_lookup` | identical for ASCII, case/space-normalised, `ΣΣ`, `ΑΣ`, `İstanbul`, accented, `""`, `None`, and a BOM-prefixed address |
| Service tests | `npm test` → **17 passed** (crypto, placeholders, deadline, 504, pages, `/i/`) |

## Still open (honest scope)

- **The plaintext-leak scan has nothing to scan yet.** The plan asks for "after every Node write
  test, scan protected columns for values that are not tokens". No Node route writes to the
  database until S7, so there is no write path to leak through; the shape-level guarantee
  (`protect` always returns a token for a non-empty, non-prefixed string) is covered by tests.
  The column scan lands with the first write route.
- **The sidecar path is implemented but not exercised end-to-end** against a real data directory
  in this pass; key resolution is unit-covered for env, invalid-env, and production refusal.
