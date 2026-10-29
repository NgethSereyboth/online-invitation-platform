# Field-encryption runbook

**Scope.** `users.email`, `guests.email`, `guests.phone`, `delivery_attempts.recipient`,
`audit_events.metadata_json` and `invitation_edit_history.diff_json` are stored as Fernet
ciphertexts. `users.email` and `guests.email` also carry a SHA-256 `email_hash`, so
login-by-email stays an indexed lookup. The design is in
[`docs/security/FIELD-ENCRYPTION.md`](../security/FIELD-ENCRYPTION.md); this file is the
operator's sequence.

**Reads are dual.** A row whose value still starts with `gAAAAA` is decrypted; a plaintext
row is returned as-is. That is what makes the migration below safe to interrupt, and what
makes the rollback possible.

**The switch is `EINVITE_FIELD_ENCRYPTION`.** `1` (the default) encrypts new writes; `0`
stops new encryption and leaves existing ciphertext readable. The work order that
requested this feature asked for "default off"; the shipped posture is **on by default**
(a new install must not write plaintext by accident). Set it to `0` only as a stop-switch
while keeping the key in place.

**The key** resolves in this order: `EINVITE_FIELD_ENCRYPTION_KEY` (env), then
`<data-dir>/.field-encryption-key` (0600), then a freshly generated key persisted to that
sidecar. An env value always wins. **Losing every copy of the key loses the ciphertext in
those six columns** — the plaintext backup tables written by the migration are the recovery
path, and they are dropped by a rollback.

## 0. Back up first

```bash
# stop the server, or use the online backup form; never copy a hot WAL file casually
DATA=/path/to/data-dir
sqlite3 "$DATA/invites.db" ".backup '$DATA/invites.db.pre-encryption-$(date +%F)'"
cp "$DATA/.field-encryption-key" "$DATA/.field-encryption-key.pre-encryption-$(date +%F)"
```

The migration writes its own `<table>_plaintext_backup` tables and keeps them for 30 days,
but a database copy is the thing that survives a wrong `--rollback`.

## 1. Dry run

```bash
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py \
  --data-dir "$DATA" --dry-run
```

It reports the rows it would encrypt per column and writes nothing. A refusal with exit
code `3` means the target is the repo's own `src/python/data`; use a copy (that guard is
deliberate).

## 2. Apply

```bash
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py \
  --data-dir "$DATA"
```

Exit `0` means every plaintext row in the six columns was rewritten, the `email_hash`
column was populated, and the backup tables exist. Exit `1` is a key or database problem —
fix it before retrying; the script is re-runnable and skips ciphertext rows.

## 3. Verify

```bash
sqlite3 "$DATA/invites.db" \
  "SELECT COUNT(*) FROM users WHERE email NOT LIKE 'gAAAAA%';"      # expect 0 (or only '')
sqlite3 "$DATA/invites.db" \
  "SELECT COUNT(*) FROM users WHERE email_hash IS NULL AND email != '';"  # expect 0
```

Then restart the server and check the paths that read those columns:

1. sign in with an existing email (hash path) and open `/api/auth/me` — the original casing
   must come back;
2. register a new account — the row must be ciphertext with a hash;
3. open a guest list and one guest's edit form — email and phone readable;
4. admin → audit events — metadata readable, not `gAAAAA…`.

The automated equivalent is `tests/security_field_encryption_test.py`.

## 4. Roll back

```bash
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py \
  --data-dir "$DATA" --rollback
```

It decrypts every ciphertext back to plaintext, clears `email_hash`, and drops the
`*_plaintext_backup` tables. Exit `2` means the backup tables are missing — restore the
database copy from step 0 instead of improvising. The test suite proves a 1,000-user +
1,000-guest round trip restores the exact original bytes.

After a rollback, also set `EINVITE_FIELD_ENCRYPTION=0` if the intent is to stay plaintext;
otherwise the next write encrypts again.

## Key rotation (tied to B-3)

`docs/ops/SECRETS-ROTATION.md` owns the procedure; the short form is a two-key window:

```bash
python3 scripts/rotate-secrets.py --field-encryption        # current -> PREVIOUS, fresh key written
PYTHONPATH=src/python:. python3 scripts/migrate_encrypt_sensitive_fields.py \
  --data-dir "$DATA" --reencrypt                            # rewrites rows only the old key can read
# then unset EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS
```

Deleting the previous key before `--reencrypt` finishes makes those rows unreadable. Both
commands expect the live data directory and refuse the repo default without an explicit
override.

## Failure modes

| Symptom | Cause | Action |
|---|---|---|
| `sign-in fails after a restart` | the key was regenerated (env key changed, sidecar lost) | restore the key from the backup; do not re-run the migration |
| `email_hash IS NULL` after apply | the row was inserted after the migration with encryption explicitly off | set the flag back to `1` and re-run the migration |
| `--rollback` exits 2 | backup tables were dropped (30-day cleanup or a second rollback) | restore the step-0 database copy |
| ciphertext visible in an API response | a read path bypasses `core/db` | that is a bug; the read wrapper reveals protected columns and the tests assert the routes |
