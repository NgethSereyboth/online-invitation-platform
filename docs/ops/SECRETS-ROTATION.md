# Secrets rotation procedure (ROADMAP §4.7)

How to rotate every long-lived secret this build reads, with the downtime each rotation costs.
The goal is **no read downtime**: rotate the key that verifies old material *behind* the new one,
re-encrypt or wait out the old material, then drop the old key.

The companion script is [`scripts/rotate-secrets.sh`](../../scripts/rotate-secrets.sh); it edits an
env file in place, keeps a timestamped backup, and prints **fingerprints**, never values (add
`--print` only when you must copy a value into a secret manager).

## Inventory — what this build actually reads

| Secret | What it protects | Consumer | Rotation behavior | Downtime |
|---|---|---|---|---|
| `EINVITE_SECRET_KEY` | Reserved for session signing | `features.secrets.ensure_secret` bootstrap only — **no signing consumer exists in this build** (`server.py` line 292 is the only reference) | Generate a new value; nothing is invalidated | none |
| `EINVITE_FIELD_ENCRYPTION_KEY` | Field-level encryption of the six listed columns | `core/crypto.py` (env var, else `<data-dir>/.field-encryption-key`) | Two-key window: new key encrypts, old key keeps decrypting; re-encrypt, then drop the old key | one restart; re-encryption runs in the background of normal traffic |
| `EINVITE_MEDIA_SIGNING_SECRET` | Signed media URLs | `server.py` HMAC; accepts a comma-separated previous list in `EINVITE_MEDIA_SIGNING_PREVIOUS_SECRETS` | New current + old in the previous list, wait out the URL TTL (`EINVITE_MEDIA_URL_TTL_SECONDS`, default 900 s, max 3600), remove the old value | none |
| `EINVITE_UPLOAD_SIGNING_SECRET` | Signed upload URLs | `server.py` HMAC; accepts `EINVITE_UPLOAD_SIGNING_PREVIOUS_SECRETS` | Same previous-list mechanic as media | none |
| `EINVITE_GUEST_TOKEN_SECRET` | Derivation of guest RSVP links | `guest_token_value` (`server.py:2940`) | Verification compares the stored SHA-256 of the *presented* token, so **existing links keep working**; only newly issued links use the new secret | none |
| `EINVITE_IMPERSONATION_SECRET` | Impersonation hand-back cookie (30 min TTL) | `impersonation_sign` (`server.py:2955`) | No previous-key support: rotating invalidates in-flight hand-backs; admins simply re-impersonate | none |
| `EINVITE_BILLING_WEBHOOK_SECRET`, `EINVITE_STRIPE_WEBHOOK_SECRET` | Webhook signature verification | billing/stripe routes | Rotate at the provider and in the env together; the provider retries deliveries across the short gap | none |
| `EINVITE_SMTP_USER` / `EINVITE_SMTP_PASSWORD` | Outbound email | `send_platform_email` | Provider-issued: create the new credential at the SMTP provider, update the env, restart, revoke the old credential | one restart |
| `EINVITE_OBJECT_STORAGE_ACCESS_KEY` / `EINVITE_OBJECT_STORAGE_SECRET_KEY` | S3/R2 API access | object-storage client | Provider-issued: create the new key pair, update the env, restart, delete the old pair | one restart |
| Plugin-marketplace CA key | (not in this build) | — | The marketplace currently reads only `EINVITE_MARKETPLACE_REQUIRES_MODERATION`; the CA key arrives with the marketplace release | — |

The upload, media, impersonation and guest secrets (and the field-encryption key) are also
auto-generated as 0600 sidecar files in the data directory (`.upload-signing-secret`,
`.media-signing-secret`, `.impersonation-secret`, `.guest-token-secret`,
`.field-encryption-key`) when no env value is set. **An env value always wins**; setting one during
rotation makes the sidecar irrelevant. To see which source is live, read the boot log:
`field encryption ready (source=env, key=<fingerprint>)`.

## The script

```
scripts/rotate-secrets.sh [--env-file PATH] [--dry-run] [--print]
                          [--field-encryption] [NAME ...]
```

- Default env file: the repo-root `.env`; each run copies it to `.env.bak-<timestamp>` first.
- Default names: `EINVITE_SECRET_KEY`, `EINVITE_BILLING_WEBHOOK_SECRET`,
  `EINVITE_STRIPE_WEBHOOK_SECRET`. Extra names may be passed positionally.
- `--dry-run` prints what would change and writes nothing.
- `--field-encryption` moves the current `EINVITE_FIELD_ENCRYPTION_KEY` to
  `EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS` and writes a fresh Fernet key as current. It refuses
  (exit 2, nothing written) if the active key is not in the env file — if it lives in the data
  directory's sidecar, copy that value into `_PREVIOUS` yourself first or put it in the env file.
- Exit codes: `0` success, `1` error / invalid existing key, `2` field key not found.

## Procedure A — app-generated secrets (no downtime)

1. `scripts/rotate-secrets.sh --dry-run` — check the list and the fingerprints of the values it
   will replace.
2. `scripts/rotate-secrets.sh` — writes the new values, keeps `.env.bak-<timestamp>`.
3. Restart the server so the process reads the new env file (config is read at startup).
4. For media/upload secrets, keep the old value in `EINVITE_MEDIA_SIGNING_PREVIOUS_SECRETS` /
   `EINVITE_UPLOAD_SIGNING_PREVIOUS_SECRETS` for one URL TTL, then remove it from the env file and
   restart again.
5. Delete the backup file once the deployment is confirmed healthy (it contains the old values).

## Procedure B — field-encryption key (zero read downtime)

1. Back up the data directory (`docs/ops/BACKUP-DR.md`).
2. `scripts/rotate-secrets.sh --field-encryption` — current key becomes `_PREVIOUS`, a new key
   becomes current. Nothing is invalidated: reads fall back to the previous key (implemented in
   `core/crypto.py`).
3. Restart. The boot log shows the new fingerprint; reads keep working for old and new rows.
4. Size the re-encryption pass: `python scripts/migrate_encrypt_sensitive_fields.py --data-dir <dir>
   --reencrypt --dry-run`; then run it for real (it rewrites every row the current key cannot read,
   never writes plaintext, and exits 1 if any ciphertext is unreadable by both keys).
5. Verify: `--reencrypt` again reports `0 row(s)`; spot-check a login and an admin listing.
6. Remove `EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS` and restart. Keep the backup of the old key in
   your secret manager for one backup cycle, then destroy it.
7. Rollback at any point: restore the env file from `.env.bak-<timestamp>` (and the data directory
   from its backup if the re-encryption pass was interrupted mid-way — mixed-key rows are normal
   and remain readable while `_PREVIOUS` is set).

The re-encryption pass is an offline command in this build; the roadmap's "background job" variant
is not implemented as a live worker. Expect it to run for minutes on a large database — size it
with `--dry-run` and run it in the deployment's maintenance window.

## Procedure C — provider-issued secrets

SMTP and object-storage credentials cannot be generated locally:

1. Create the replacement credential at the provider (keep the old one active).
2. Update the env file (or the platform's secret store) and restart.
3. Confirm mail/upload traffic on the new credential, then revoke the old one at the provider.
4. Same pattern for Stripe/billing keys: create the replacement in the provider dashboard, set both
   provider and env to the new value, confirm a webhook delivery, then revoke the old secret.

## Verification checklist

```
# 1. The rotation + encryption suites:
.venv/bin/python -m pytest tests/security_field_encryption_test.py \
                             tests/lt_7_2_secrets_rotation_test.py -q

# 2. The live key fingerprint matches the env file (never prints the key):
PYTHONPATH=src/python .venv/bin/python -c \
  "from core.crypto import key_source, key_fingerprint; print(key_source(), key_fingerprint())"

# 3. Production preflight accepts the new environment:
.venv/bin/python src/python/core/preflight.py --env-file .env
```

Also confirm in the server log that `field encryption ready (source=env, …)` uses the expected
fingerprint, and exercise one admin action and one public invitation before deleting the backup.
