# Docker-compatible PaaS contract

`Dockerfile.online` is the portable image definition for online container hosts. It is suitable for providers such as Railway, Render, Fly.io, Azure Container Apps, AWS ECS/Fargate, and Google Cloud Run after the provider resources below are attached.

## Required process types

| Process | Command | Public |
|---|---|---|
| web | `python server.py --host 0.0.0.0 --port 8080` | Yes; HTTPS/custom domain |
| worker | `python platform_worker_v32.py` | No |
| scheduler | `python platform_scheduler_v32.py` | No; exactly one active replica |

All three processes use the same immutable image and the same production secrets. Scale the web/worker processes only after Redis-backed rate limiting and provider concurrency have been verified. Do not run multiple schedulers unless leader election is added.

## Required attached services

- PostgreSQL with TLS, restricted network access, automated backups, and point-in-time recovery.
- Authenticated Redis with TLS/private networking.
- S3-compatible object storage such as Cloudflare R2, Amazon S3, or a private MinIO service.
- A private ClamAV `clamd` endpoint reachable as the hostname configured by `/etc/clamav/clamd.remote.conf`, or a replacement scanner command.
- Central JSON logs/error monitoring and uptime checks.

Generate `.env.production` locally, then enter its values through the provider's secret manager. Replace Docker-internal endpoints (`postgres`, `redis`, and `minio`) with the provider endpoints. Set at minimum:

```text
EINVITE_ALLOWED_HOSTS=invite.example.com
EINVITE_PUBLIC_BASE_URL=https://invite.example.com
EINVITE_COOKIE_SECURE=1
EINVITE_PRODUCTION=1
EINVITE_REQUIRE_DURABLE_SERVICES=1
EINVITE_REQUIRE_MALWARE_SCAN=1
EINVITE_MALWARE_SCANNER_COMMAND=clamdscan --stream --no-summary --config-file=/etc/clamav/clamd.remote.conf
```

Only add the platform's documented private reverse-proxy source addresses to `EINVITE_TRUSTED_PROXY_IPS`. Never use `*`, a public CIDR, or `0.0.0.0/0`. If the provider does not publish stable proxy source addresses, leave this empty and rely on the canonical host/origin; forwarded client IP values will intentionally be ignored.

## Platform limitations to check

- Request timeout must allow normal uploads and SSE collaboration connections.
- The filesystem is disposable; all durable data belongs in PostgreSQL/object storage.
- The platform must support separate background process types.
- Configure `/api/health/ready` for traffic readiness and `/api/health/live` for process liveness.
- Direct browser uploads require exact-origin bucket CORS.
- Set minimum instances if cold-start delay is unacceptable.
- Verify graceful shutdown provides at least 30 seconds.

Run the provider deployment first in a staging account. The release gate does not substitute for real DNS, TLS, CORS, mail, storage, database, Redis, malware-scanner, backup, and restore tests.
