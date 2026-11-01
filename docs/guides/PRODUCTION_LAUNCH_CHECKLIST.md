# Production launch checklist

Use this checklist for the first production deployment and for every material infrastructure change. Keep completed evidence in a private operations system; do not commit credentials, database exports, or customer media.

## 1. Freeze and identify the release

- Record the release ZIP SHA-256 and the Git commit deployed.
- Verify `V0_52_RELEASE_FILE_HASHES.sha256` before building the image.
- Confirm the release evidence test and the complete review gate pass from a clean extraction.
- Keep the previous known-good image and configuration available for rollback.

## 2. Generate and validate configuration

```powershell
python prepare_production_env.py --public-url https://invite.example.com
python production_preflight.py --env-file .env.production --check-dependencies
docker compose --env-file .env.production -f docker-compose.production.example.yml config --quiet
```

- Store `.env.production` in the deployment secret store, never Git or a public CI artifact.
- Back up the three application signing secrets in a protected recovery vault.
- Confirm the public URL is the final HTTPS origin and secure cookies are enabled.
- Restrict trusted proxy IPs to the actual reverse proxy or load balancer.
- Use distinct production credentials; do not reuse staging or developer secrets.

## 3. DNS, TLS, and edge controls

- Point DNS to the reverse proxy or load balancer only after its HTTPS certificate is valid.
- Redirect HTTP to HTTPS at the edge.
- Proxy to the application on the private/loopback port; do not expose PostgreSQL, Redis, or MinIO publicly.
- Set conservative request-body and timeout limits compatible with the configured upload limits.
- Preserve the real client IP only from explicitly trusted proxies.
- Configure rate limiting and abuse monitoring at both the edge and application layers.

## 4. Database readiness

- Create a dedicated least-privilege PostgreSQL role and database.
- Enable encrypted connections when the database crosses a host or provider boundary.
- Take a pre-deployment snapshot before migration.
- Run the schema/migration procedure once and record its output privately.
- Verify connection capacity, storage alerts, automated backups, retention, and point-in-time recovery.
- Test a restore into an isolated database and verify the recovered invitation count.

## 5. Object storage and uploads

- Use a private bucket with public listing disabled.
- Grant the application only required bucket/object permissions.
- Configure exact-origin CORS for browser `PUT`; do not use wildcard origins for the private studio.
- Enable provider encryption, object versioning, lifecycle rules, and deletion protection as appropriate.
- Verify presign, direct upload, completion, download, and deletion using harmless test media.
- Confirm uploaded object metadata never exposes credentials or private internal paths.
- If using a CDN, verify cache rules do not expose private draft assets.

## 6. Redis and background services

- Require Redis authentication and private networking.
- Confirm the web, worker, and scheduler use the same durable configuration and signing secrets.
- Confirm only one intended scheduler instance is active.
- Exercise one retryable job, one cancelled job, and one idempotent repeated job.
- Alert on queue age, repeated failures, and worker unavailability.

## 7. Start and verify

```powershell
docker compose --env-file .env.production -f docker-compose.production.example.yml build --pull
docker compose --env-file .env.production -f docker-compose.production.example.yml up -d
docker compose --env-file .env.production -f docker-compose.production.example.yml ps
```

- `/api/health/live` returns HTTP 200.
- `/api/health/ready` returns HTTP 200 and reports configuration, database, storage, and Redis ready.
- Sign up or sign in with a non-administrator test account.
- Create an invitation, upload image/audio material, edit, autosave, publish, and open the public snapshot.
- Submit an RSVP where enabled and verify it appears only to the correct owner.
- Verify RSVP-disabled invitations show no attend/decline controls.
- Verify Khmer text, Khmer date presentation, mobile layout, music consent/opening behavior, and reduced motion.
- Verify logout invalidates the session and private APIs reject unauthenticated access.

## 8. Monitoring and security operations

- Forward structured application logs without secrets or raw authentication tokens.
- Alert on readiness failures, elevated 5xx responses, authentication abuse, storage failures, database saturation, and queue backlog.
- Confirm clocks are synchronized across hosts.
- Configure dependency and container-image vulnerability monitoring.
- Define who receives security, privacy, billing, and availability alerts.
- Record an incident response contact and a credential-rotation procedure.

## 9. Backup and disaster recovery gate

- Verify the most recent database backup and object-storage recovery/versioning policy.
- Perform a documented restore drill before accepting real customer data.
- Confirm restored invitation documents still reference recoverable media objects.
- Record recovery point and recovery time results against the business targets.
- Keep backups in a separate failure domain with access logging and limited delete authority.

## 10. Cutover and rollback

- Announce the maintenance/cutover window to operators.
- Keep schema changes backward-compatible for the rollback window.
- Shift traffic gradually when the hosting provider supports it.
- If readiness, publishing, uploads, or authentication fail, stop cutover and restore the previous image/configuration.
- Never roll back the database destructively without a verified snapshot and an explicit recovery decision.
- After rollback, confirm live/ready health and run the core invitation smoke flow again.

## 11. Post-launch review

- Review logs, latency, error rates, storage growth, queue age, and database utilization after 15 minutes, 1 hour, and 24 hours.
- Rotate any credential exposed during troubleshooting.
- Remove temporary test accounts and harmless test media when evidence has been retained.
- Schedule the next restore drill and dependency/security review.
