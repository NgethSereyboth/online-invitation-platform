# Production deployment guide

For the current one-command Docker/VPS, native Windows Server, bare-metal Linux,
and Docker-compatible PaaS paths, start with `ONLINE_AND_SERVER_HOSTING.md`.

The application can still run as a zero-dependency local review server, while optional production adapters support PostgreSQL, Redis, object storage, SMTP, external AI and billing providers.

## Local review

```powershell
python -u server.py --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

## Production dependencies

```text
pip install -r requirements-production.txt
```

This installs:

- `psycopg` for PostgreSQL runtime/migration.
- `boto3` for S3-compatible/Cloudflare R2 media storage.
- `redis` for distributed rate limiting.

Browser QA tools are separate:

```text
pip install -r requirements-test.txt
playwright install chromium
```

`requirements-test.txt` pins the audited Playwright version because browser geometry and timing evidence is not reproducible when the browser engine changes silently. Upgrade that pin only in a dedicated compatibility pass followed by the complete release gate.

## Core configuration

Copy the production template, replace every `REPLACE_*` value with an independently generated secret, and keep the resulting file out of Git:

```powershell
python prepare_production_env.py --public-url https://invite.example.com
python production_preflight.py --env-file .env.production --check-dependencies
```

The generator creates independent PostgreSQL, Redis, MinIO, upload, media, and guest-token secrets without printing them and refuses to overwrite an existing file. Alternatively, copy `.env.production.example` manually and replace every placeholder. The preflight never prints credential values. Production server startup runs the same validation and exits before opening the database when the configuration is unsafe or incomplete.

Before accepting customer data, complete `PRODUCTION_LAUNCH_CHECKLIST.md`, including a real provider upload check and an isolated database/object recovery drill.

Important values:

- `EINVITE_DATA_DIR` — persistent SQLite/local-media directory.
- `EINVITE_PUBLIC_BASE_URL` — canonical external HTTPS origin.
- `EINVITE_DATABASE_URL` — set to a PostgreSQL URL to run against PostgreSQL; leave empty for SQLite.
- `EINVITE_COOKIE_SECURE=1` — required behind production HTTPS.
- `EINVITE_REDIS_URL` — recommended for multi-instance rate limiting.
- `EINVITE_REQUIRE_DURABLE_SERVICES=1` — requires PostgreSQL, authenticated Redis, non-local object storage, and non-local backups.
- `EINVITE_UPLOAD_SIGNING_SECRET`, `EINVITE_MEDIA_SIGNING_SECRET`, and `EINVITE_GUEST_TOKEN_SECRET` — distinct stable secrets with at least 32 random characters each.
- `EINVITE_ENFORCE_PLAN_LIMITS=1` — enforces configured account quotas.

## Database

### SQLite

Suitable for local review, demonstrations and a single small server instance. WAL and busy timeout are enabled.

### PostgreSQL runtime

Set:

```text
EINVITE_DATABASE_URL=postgresql://user:password@host:5432/e_invitation_website
```

The server selects the PostgreSQL adapter automatically and initializes `postgres_schema.sql`.

To migrate existing SQLite data first:

```text
python migrate_sqlite_to_postgres.py --database-url "$EINVITE_DATABASE_URL"
```

The repository includes the runtime adapter and migration tooling. A real production PostgreSQL deployment still needs to be exercised against the chosen managed PostgreSQL service before launch.

## Object storage / CDN

Set the `EINVITE_OBJECT_STORAGE_*` variables to use S3-compatible storage such as Cloudflare R2 or Amazon S3. If `EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL` is present, published invitations use the CDN/custom-domain URL; otherwise the app proxies `/uploads/*`.

The browser upload client uses the following production flow when object storage is configured:

```text
POST /api/invitations/{id}/assets/presign
        ↓
short-lived signed PUT URL + signed upload claim
        ↓
browser uploads the binary directly to R2/S3
        ↓
POST /api/invitations/{id}/assets/complete
        ↓
server verifies claim, object size, and file signature, then registers the material
```

Set a stable, high-entropy `EINVITE_UPLOAD_SIGNING_SECRET` across all application instances. Local deployments where object storage is not configured return HTTP 409 from the presign endpoint; the shared browser client then uses the normal `/assets/raw` server upload automatically.

For browser-direct uploads, configure the bucket CORS policy to allow `PUT` requests from the exact production application origin and allow the `Content-Type` request header. Do not use a wildcard origin for a private production studio unless the storage provider/security model specifically requires it. A typical policy concept is:

```json
[
  {
    "AllowedOrigins": ["https://your-domain.example"],
    "AllowedMethods": ["PUT"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Provider-specific CORS syntax may vary. Keep object-storage credentials server-side and grant only the minimum bucket permissions needed for upload, read/head, and deletion.

Move historical local files with:

```text
python migrate_assets_to_object_storage.py
```

The signed upload flow is covered by deterministic local fallback tests. Real R2/S3 credentials, provider CORS behavior, CDN/custom-domain configuration, and cross-origin browser PUT behavior must still be verified against the selected production provider before launch.

## Collaboration transport

The editor opens an authenticated Server-Sent Events stream at:

```text
GET /api/invitations/{id}/events
```

The stream emits `invitation-update` events when the server draft timestamp changes. EventSource automatically uses the HttpOnly session cookie; the client falls back to periodic polling if SSE is unavailable or disconnected. This is remote-change awareness, not a CRDT/operational-transform engine: simultaneous conflicting edits still require user review rather than silent merging.

## Sessions and security

The server sets an HttpOnly SameSite session cookie. The browser review application keeps only a non-secret compatibility marker in localStorage for feature-gating; API tests can still use returned bearer tokens.

Production requirements:

```text
EINVITE_COOKIE_SECURE=1
EINVITE_PUBLIC_BASE_URL=https://your-domain.example
```

The backend also sends CSP, HSTS when secure mode is enabled, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP and CORP headers. Cookie-authenticated state changes receive a same-origin check.

The current CSP blocks inline scripts and inline style elements. A narrowly scoped
`style-src-attr 'unsafe-inline'` compatibility allowance remains for legacy dynamic
element style attributes; remove it only after those editor paths are migrated.

## SMTP

Configure `EINVITE_SMTP_*` for real email verification and password-reset delivery. Keep:

```text
EINVITE_DEV_AUTH_TOKENS=0
```

in production.

## AI provider

The local invitation-writing fallback always works without a provider. To connect a hosted AI service, configure:

```text
EINVITE_AI_ENDPOINT=
EINVITE_AI_API_KEY=
EINVITE_AI_MODEL=
```

The endpoint receives `task`, `prompt`, `context` and `model`. It can return a direct `text`, `output`, `output_text`, or an OpenAI-like `choices` response.

No hosted AI model is claimed as active until real provider credentials are configured and tested.

## Billing

The application includes:

- Free / Creator / Studio plan definitions.
- Usage accounting and optional enforcement.
- A provider-neutral hosted-checkout adapter.
- HMAC-signed subscription lifecycle webhook handling.

Configure:

```text
EINVITE_BILLING_CHECKOUT_ENDPOINT=
EINVITE_BILLING_API_KEY=
EINVITE_BILLING_WEBHOOK_SECRET=
```

Actual card charging, tax/invoicing and subscription settlement depend on the payment provider chosen for deployment and must be tested with that provider's sandbox before production.

## Redis

For multiple application instances:

```text
EINVITE_REDIS_URL=redis://host:6379/0
```

Without Redis the server uses an in-process fallback, suitable only for one instance.

## Monitoring

Enable structured logs:

```text
EINVITE_JSON_LOGS=1
```

The Admin System panel consumes `/api/admin/metrics`. Use `/api/health/live` for process liveness and `/api/health/ready` for traffic readiness. Readiness returns HTTP 503 unless configuration validation, a database query, an object-storage probe, and configured Redis connectivity all succeed. In production, forward JSON logs and health/metrics to the selected monitoring/alerting platform.

## Backups

SQLite/local-media deployments can use:

```text
python backup.py
```

For PostgreSQL/object-storage deployments, configure provider-native automated backups/versioning as well as periodic restore testing.

## Container

Single-container deployment:

```text
docker build -t e-invitation-website .
docker run --env-file .env.production -p 8080:8080 e-invitation-website
```

The image runs as unprivileged UID/GID `10001`, uses `/api/health/ready`, and does not include `.env` files, databases, logs, caches, or local secrets in its build context.

Credential-wired PostgreSQL, authenticated Redis, and private MinIO stack:

```powershell
docker compose --env-file .env.production -f docker-compose.production.example.yml config --quiet
docker compose --env-file .env.production -f docker-compose.production.example.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.example.yml ps
```

The example binds the web port to `127.0.0.1` by default so a host reverse proxy can terminate HTTPS. Set `EINVITE_BIND_ADDRESS` only when direct network exposure is intentional. PostgreSQL, Redis, and MinIO remain on an internal Docker network and are not published to the host.

Mount `EINVITE_DATA_DIR` when SQLite/local media are used. The Compose example retains a shared application volume for bounded temporary jobs and recovery material even though PostgreSQL and MinIO hold durable application data.

## Release QA

Run the complete deterministic suite:

```text
python run_review_checks.py
```


Backend tests:

```text
python tests/smoke_test.py
python tests/plan_limit_test.py
python tests/final_features_test.py
python tests/production_foundations_test.py
python tests/static_integrity_test.py
python tests/provider_adapters_test.py
python tests/realtime_storage_test.py
python tests/signed_upload_backend_test.py
python tests/v0_52_production_deployment_hardening_test.py
```

Browser QA where local Chromium access is allowed:

```text
python tests/ui_smoke_test.py
python tests/visual_regression.py --update
python tests/visual_regression.py
```

Always review Light and Dark mode at desktop and mobile widths before a public release.
