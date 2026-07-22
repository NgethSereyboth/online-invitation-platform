# Production Readiness & Commercial Scaffolding Phase — 2026-07-21

This phase continues the existing invitation-platform codebase without replacing the established dependency-free local architecture.

## Completed in this phase

### Featured video
- Added MP4 and WebM material support.
- Added featured-video editor controls and material-library selection.
- Added guest-facing video rendering and section animation/style support.
- Added 50 MB video upload allowance with file-signature validation.
- Added video document validation and publish-snapshot persistence.

### Material library and upload pipeline
- Added an account-wide Material Library page.
- Added folders, tags, favorites, rename, type filters, search, and deletion.
- Added raw binary upload support to avoid base64 expansion for large materials.
- Added image/audio/video account-level reuse.
- Fixed material serving when `EINVITE_DATA_DIR` points outside the repository.

### Optional object storage
- Added an S3-compatible storage adapter used automatically when `EINVITE_OBJECT_STORAGE_BUCKET` is configured.
- Supports Cloudflare R2, Amazon S3, and compatible providers.
- Added optional CDN/public-base URL support.
- Added migration tooling for moving existing local uploads to object storage.
- Local disk remains the default and requires no third-party Python packages.

### Email verification and password reset
- Added one-time verification and password-reset tokens.
- Added optional SMTP delivery.
- Added verification and reset pages.
- Added local-development token exposure only when `EINVITE_DEV_AUTH_TOKENS=1` is explicitly enabled.
- Password reset revokes active sessions.

### Plans and account usage
- Added Free, Creator, and Studio plans to user accounts.
- Added account usage reporting for:
  - active invitations;
  - reusable templates;
  - uploaded material storage.
- Added optional server-side plan limit enforcement with `EINVITE_ENFORCE_PLAN_LIMITS=1`.
- Limits remain informational by default.
- Added Plans & Usage page.
- Added plan information to Account settings.
- Added administrator plan assignment controls.
- No fake payment flow was added. Actual checkout/subscription billing still requires a real payment provider.

### Designer workflow
- Added a role-protected Designer Workspace for designer and administrator accounts.
- Provides focused access to Template Studio, account materials, and invitation production.
- Added contextual dashboard navigation for designer/admin roles.

### PostgreSQL preparation
- Updated the PostgreSQL target schema with account plans.
- Included SQLite-to-PostgreSQL transfer tooling.
- The current runtime intentionally remains SQLite; the migration script prepares a production copy but does not silently switch the running server.

## Automated verification

The primary smoke test now covers:
- administrator registration and default Studio plan;
- account usage endpoint;
- email verification;
- reusable template creation and marketplace publication;
- invitation creation;
- raw PNG upload;
- raw MP4 upload;
- asset folders/tags/favorites;
- featured video publication;
- password-protected invitation unlock;
- custom RSVP validation and persistence;
- private guest wishes;
- owner RSVP updates;
- administrator plan assignment;
- password reset;
- account export;
- password change;
- unpublishing and public endpoint closure.

Run:

```text
python tests/smoke_test.py
```

A separate quota test verifies optional Free-plan enforcement:

```text
python tests/plan_limit_test.py
```

## Production integrations that remain provider-dependent

The repository is intentionally not pretending that the following are complete without external providers or deployment credentials:

1. Automatic subscription billing and payment webhooks.
2. Premium-template checkout and creator payouts.
3. The final runtime switch from SQLite to PostgreSQL.
4. Production R2/S3 credentials and CDN configuration.
5. Production SMTP credentials.
6. Production hosting, HTTPS, custom domain, monitoring, and alerting.
7. Optional AI writing, translation, and design services.

The local application remains fully runnable without these providers, while the interfaces and migration paths for storage/email/database scaling are now present.
