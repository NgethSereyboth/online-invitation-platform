# V32 Deployment Topology

Supported production shape: Web/API service, worker service, scheduler, PostgreSQL, Redis-compatible queue/presence service, S3/R2/MinIO-compatible object storage, reverse proxy/CDN and monitoring adapters. `docker-compose.production.example.yml` is an example, not a secret-bearing deployment.

Use `.env.example` as the configuration schema. Production requires HTTPS, stable signing secrets, transactional database migrations, bounded database pools/workers/uploads/requests and explicit trusted proxies. The web role may set `EINVITE_WORKER_CONCURRENCY=0`; `platform_worker_v32.py` claims durable jobs. `platform_scheduler_v32.py` performs bounded scheduled maintenance. Unknown newer platform/document schemas must be reviewed before deployment.
