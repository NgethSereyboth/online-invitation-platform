# Field-level encryption (ROADMAP §4.1)

Application-layer encryption for the sensitive columns §4.1 names: the values are
ciphertext in the SQLite file (or a PostgreSQL row), and the HTTP layer keeps
working with plaintext because every row is revealed at the connection boundary.
Disk encryption is not assumed — a stolen `invites.db` without the key file is
unreadable for these columns.

Status: implemented for **reads, writes and existing rows**:

| Table | Column | Encrypted on write | Notes |
|---|---|---|---|
| `users` | `email` | yes (register) | plus `email_hash` for lookup |
| `guests` | `email`, `phone` | yes (create + edit) | no lookup on these columns |
| `delivery_attempts` | `recipient` | yes (deliver route) | — |
| `audit_events` | `metadata_json` | yes (`write_audit_event`) | plus `admin_only` flag (below) |
| `invitation_edit_history` | `diff_json` | yes (post-send edit) | — |
| `webhook_endpoints` | `secret` | yes (create/rotate) | not in §4.1's list; same mechanism |

`passkeys.public_key` and `mfa_recovery_codes.code_hash` are deliberately skipped,
as §4.1 says: one is public, the other already a hash.

## Keys

Resolution order (first hit wins, resolved once per process):

1. `EINVITE_FIELD_ENCRYPTION_KEY` — a **valid Fernet key** (44-char urlsafe
   base64). A malformed value does not crash the boot: the server logs
   `source=env-invalid` and falls back to the next step.
2. `<data dir>/.field-encryption-key` — generated on first boot, `0600`, beside
   the data it encrypts so a restart still decrypts.
3. A process-local generated key, reported as such (`encryption_available()`
   returns false-ish for the migration script); only happens on a read-only data
   directory.

Diagnostics never print the key: `key_source()` says where it came from and
`key_fingerprint()` is a 12-char SHA-256 so two processes can be compared by an
operator. Boot logs one line with both.

`EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS` is a **decrypt-only** window for a
rotation (see `docs/ops/SECRETS-ROTATION.md`); `EINVITE_FIELD_ENCRYPTION=0` stops
new writes while reads keep decrypting, so the kill switch never strands data.

## Read and write paths

* **Reads** — `server.connect()` yields `core.db.reveal_connection`, whose cursor
  reveals every value that is a Fernet token (`gAAAAA…`). A plaintext row passes
  through unchanged, which is what makes mixed states (partly migrated, or a
  fresh install next to legacy rows) safe: nothing is double-decrypted, and a
  column added to `PROTECTED_COLUMNS` needs no change at a call site.
* **`users.email` lookups** — `core.db.find_user_by_email()` matches
  `email_hash` (SHA-256 of the lowercased, trimmed address, indexed and unique)
  and falls back to `lower(email)` for rows the migration has not converted.
  Sign-in, duplicate checks, resets, admin search and the comment-author lookup
  all go through it.
* **Writes** — deliberately *not* intercepted. Rewriting `INSERT`/`UPDATE`
  parameters would mean mapping `?` positions to columns from SQL text, and a
  silent mis-map corrupts data; instead each statement that writes a protected
  column calls `protect()` (or `protect_row_columns()` for a generated
  statement) at the call site.
* **`audit_events.metadata_json`** — encrypted at write. The hash chain still
  digests the *plaintext* JSON (the verifier reads the revealed value, so
  existing chains keep validating), and the one SQL search over the JSON — the
  admin `adminOnly=1` filter — now matches an indexed `admin_only` column
  written alongside the metadata; pre-migration rows still match by `LIKE`.
  The CSV export writes the revealed value.

## Migration and rollback

`scripts/migrate_encrypt_sensitive_fields.py` (temp databases only — it refuses
the repo's own `src/python/data` with exit 3 unless
`--allow-repo-data-dir` is passed deliberately):

```
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --dry-run
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py      # apply
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --rollback
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py --reencrypt
```

* `--apply` encrypts each column and writes a `<table>_plaintext_backup` table
  first (30-day retention by convention); `--dry-run` reports counts only.
* `--rollback` restores real per-row values from that backup (including the old
  `email_hash` state) and drops it; the users column is nullable and the unique
  index is partial (`WHERE email_hash IS NOT NULL`) so a rollback cannot collide.
* `--reencrypt` is the rotation pass: rewrites exactly the rows the active key
  cannot read, never writes plaintext, and exits 1 without touching a ciphertext
  neither the active nor the previous key can decrypt.
* Two legacy addresses that collide on the hash (case/whitespace) abort the run
  with exit 1 and a named sample instead of dying mid-way on an `IntegrityError`.

## Limits (what this does not do)

* Not ORM-enforced: a **new** write path must call `protect()` itself; the read
  wrapper will still decrypt, so a missed write shows up as plaintext in the
  file, not as a bug in the browser.
* `email_hash` is an unsalted SHA-256 — it is a lookup key, not a verifier, and
  it is the reason a DB-only attacker can confirm a guessed address. Password
  hashing stays Argon2id/PBKDF2 with per-row salts.
* Ciphertext length grows (~1.4× for Fernet), so `LIKE`/`ORDER BY` on a
  protected column is meaningless — use the hash or a companion flag. The only
  such query in the codebase is the audit `adminOnly` filter above.
* Backups taken by the migration are as sensitive as the source and live in the
  same data directory until dropped.
* Values are plaintext in server memory and in any log line that prints a row;
  this protects the file at rest, not a compromised process.

Tests: `tests/security_field_encryption_test.py` (live round trip + restart,
write-path coverage per column, migration apply/rollback/re-encrypt, the
repo-data-dir guard). Rotation procedure: `docs/ops/SECRETS-ROTATION.md`.
