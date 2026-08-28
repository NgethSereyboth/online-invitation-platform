# Per-account upload permission

Implemented on 2026-08-09 without changing the project README.

## Administrator behavior

The Administration > Users view now includes an `Allow uploads` checkbox and a
separate `Save uploads` action for every account. New and migrated accounts are
enabled by default. Changes apply immediately to existing login sessions.

The account profile shows either `Allowed` or `Disabled by administrator` so a
customer can distinguish an account restriction from storage quota, validation,
or malware-scanner failures.

## Server enforcement

Disabled accounts receive HTTP 403 with the stable code `upload_disabled` from:

- regular binary and legacy base64 material uploads;
- resumable upload creation, chunk append, and completion;
- direct object-storage presign and completion;
- custom-font uploads;
- V32 workspace upload creation, part signing, and completion.

The capability belongs to the acting user. A disabled collaborator therefore
cannot upload into another owner's invitation. Storage quota continues to be
calculated against the invitation owner.

Existing files remain readable and removable. Cancelling a pending resumable
upload remains available so disabling uploads cannot trap temporary data.

## Persistence and audit

SQLite and PostgreSQL both use `users.upload_enabled INTEGER NOT NULL DEFAULT 1`.
The SQLite startup migration and PostgreSQL idempotent migration support existing
installations. Administrator changes emit `account.upload_permission_changed`
audit events and account exports include the current capability.

## Verification

`tests/v0_52_upload_permission_test.py` exercises default enablement, admin-only
updates, invalid input, immediate session behavior, every upload family, existing
asset access, resumable cleanup, re-enablement, UI bundle propagation, PostgreSQL
schema coverage, and audit evidence.
