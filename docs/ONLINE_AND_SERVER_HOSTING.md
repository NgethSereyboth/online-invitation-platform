# Online, VPS, Linux, and Windows Server hosting

This project now has separate deployment paths for local laptop review and permanent public hosting. The laptop launcher remains the easiest private demo. Public hosting must use HTTPS, durable services, protected secrets, upload malware scanning, backups, and health monitoring.

## Choose a target

| Target | Recommended use | Entry point |
|---|---|---|
| Windows laptop | Private LAN demo or review | `HOST_EINVITE_ON_LAPTOP.bat` |
| Linux cloud VM/VPS | Recommended permanent single-server deployment | `DEPLOY_EINVITE_SERVER.bat DockerOnline ...` or the equivalent PowerShell command |
| Windows Server | Permanent server with external PostgreSQL, Redis, and S3/R2 | `DEPLOY_EINVITE_SERVER.bat WindowsServer ...` |
| Bare-metal Linux | Existing managed Linux server | `deploy/linux/install-einvite-linux.sh` |
| Container PaaS | Railway, Render, Fly.io, Azure Container Apps, AWS ECS, Google Cloud Run, or similar | `Dockerfile.online` plus the platform contract in `deploy/paas/PAAS_DEPLOYMENT.md` |

GitHub Pages and other static-only hosting cannot run this complete platform because authentication, invitations, uploads, RSVP persistence, publishing, and background work require the Python backend and durable services.

## Before any public deployment

1. Own a domain or subdomain, for example `invite.example.com`.
2. Point its DNS `A`/`AAAA` record to the public server.
3. Permit inbound TCP 80 and 443 at the cloud firewall/security group. Permit UDP 443 if HTTP/3 is desired.
4. Do not publicly expose 8080, PostgreSQL, Redis, MinIO, or ClamAV.
5. Create the secret environment file. Never commit it:

```powershell
python prepare_production_env.py --public-url https://invite.example.com --trusted-proxy-ips 172.31.52.10
```

6. Store a protected offline copy of `.env.production`. Losing signing keys invalidates active signed operations; leaking them requires a rotation plan.

Run the non-secret file check at any time:

```powershell
DEPLOY_EINVITE_SERVER.bat ValidateFiles
```

## Recommended: Docker on any Linux VPS/cloud VM

This path works on providers that supply a normal Linux VM, including AWS EC2, Azure VM, Google Compute Engine, DigitalOcean, Hetzner, Linode/Akamai, Vultr, and an on-premises Docker server.

Install Docker Engine and the Compose v2 plugin, extract the project, create `.env.production`, then run from the project directory:

```powershell
DEPLOY_EINVITE_SERVER.bat DockerOnline -Domain invite.example.com
```

On a Linux shell, invoke the same Compose files directly:

```bash
export EINVITE_DOMAIN=invite.example.com
docker compose --env-file .env.production \
  -f docker-compose.production.example.yml \
  -f deploy/docker-compose.online.yml config --quiet
docker compose --env-file .env.production \
  -f docker-compose.production.example.yml \
  -f deploy/docker-compose.online.yml up -d --build
```

The stack provides:

- Caddy HTTPS termination and certificate renewal;
- a private application network;
- PostgreSQL, authenticated Redis, and private MinIO volumes;
- a web process, worker, and scheduler;
- ClamAV scanning that fails uploads closed when unavailable;
- liveness/readiness health checks and restart policies.

The first ClamAV start can take several minutes while signatures are initialized. Verify:

```bash
docker compose --env-file .env.production -f docker-compose.production.example.yml -f deploy/docker-compose.online.yml ps
curl -fsS https://invite.example.com/api/health/ready
```

Back up the PostgreSQL, MinIO, and application volumes to a different machine/provider. A snapshot on the same VPS is not an adequate only backup. Perform a restore drill before accepting customer data.

## Windows Server

Windows Server is supported as an application host. For a durable production installation, first edit `.env.production` so PostgreSQL, authenticated Redis, S3/R2 object storage, and backup settings point to real external services. The default generated `postgres`, `redis`, and `minio` hostnames are Docker-internal names and are not valid for a native Windows installation.

Install Python 3.10+, enable Microsoft Defender, and download an official `caddy.exe`. Run PowerShell as Administrator:

```powershell
DEPLOY_EINVITE_SERVER.bat WindowsServer `
  -Domain invite.example.com `
  -CaddyExe C:\Tools\caddy.exe
```

If the Windows network profile is intentionally `Public`, explicitly include:

```powershell
-AllowPublicFirewall
```

The installer creates an isolated virtual environment and two restartable startup tasks:

- `EInvite-Web`: Python bound only to `127.0.0.1:8080`, with Defender-required uploads.
- `EInvite-Caddy`: public HTTPS on 80/443 and reverse proxying to the application.

Inspect with:

```powershell
Get-ScheduledTask EInvite-Web,EInvite-Caddy
Invoke-RestMethod https://invite.example.com/api/health/ready
```

If an organization already uses IIS, omit `-CaddyExe`, keep 8080 private, and configure IIS as the HTTPS reverse proxy. Only `127.0.0.1`/`::1` are trusted to supply forwarded headers by the Windows launcher.

## Bare-metal Linux with systemd

The Docker path is preferred because it supplies the complete service set. For an existing managed Linux server, extract the project under `/opt/einvite`, install PostgreSQL/Redis/S3-compatible storage and ClamAV, configure `.env.production` with their real endpoints, and run:

```bash
sudo bash deploy/linux/install-einvite-linux.sh \
  --domain invite.example.com \
  --caddy-snippet /etc/caddy/conf.d/einvite.caddy
```

The installer refuses to overwrite an existing Caddy snippet. Ensure the main Caddyfile contains an import for that directory, validate Caddy, and reload it. The systemd service uses sandboxing, an unprivileged `einvite` account, loopback-only binding, automatic restart, and required `clamdscan` uploads.

## Container hosting platforms

See `deploy/paas/PAAS_DEPLOYMENT.md`. The application image can run on several platforms, but a static frontend deployment or a single disposable container is not the full production system. A production PaaS configuration needs:

- one public web service and separate worker/scheduler processes;
- managed PostgreSQL and password/TLS-protected Redis;
- private S3/R2 storage and an external backup destination;
- a reachable ClamAV service or another scanner command with equivalent fail-closed behavior;
- a persistent custom domain with HTTPS;
- sticky signing secrets shared by every process;
- health path `/api/health/ready` and liveness path `/api/health/live`.

Use the hosting provider's secret manager. Never paste secrets into a Dockerfile, Compose file, public build log, repository, or browser environment variable.

## Operations after deployment

- Alert when readiness fails, certificates approach expiry, storage capacity is low, ClamAV signatures are stale, or backups fail.
- Patch the host, container images, Python dependencies, Caddy, ClamAV, PostgreSQL, Redis, and MinIO on a scheduled cadence.
- Run `python release_check.py` before promoting a changed build.
- Keep the previous known-good image and database migration/rollback procedure.
- Test upload, RSVP, publish snapshot, personalized invitation, email, backup, and restore against the real providers before launch.

The deployment scripts deliberately do not purchase domains, create cloud databases, or invent provider credentials. Those values remain the production owner's responsibility.
