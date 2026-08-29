# First-time installation and hosting guide

This is the starting point for a new computer or server. Run only the path that matches your host. The scripts are safe to rerun, but production environment generation refuses to overwrite an existing secret file.

## Quick choice

| Goal | First command | Result |
|---|---|---|
| Use on one Windows computer | `FIRST_TIME_SETUP.cmd` | Installs the local runtime; then use `RUN_EINVITE_LOCAL.bat` |
| Share from a Windows laptop on the same network | `FIRST_TIME_HOSTING_SETUP.cmd Network` | Configures and runs the LAN host on port 8080 |
| Temporary public demonstration | `FIRST_TIME_SETUP.cmd`, then `RUN_EINVITE_PUBLIC_TUNNEL.bat` | Temporary HTTPS tunnel; not permanent production hosting |
| Permanent Docker/VPS host | `FIRST_TIME_HOSTING_SETUP.cmd Docker -Domain invite.example.com` on Windows, or the Linux Docker steps below | HTTPS stack with web, worker, scheduler, PostgreSQL, Redis, MinIO, Caddy, and ClamAV |
| Native Windows Server | `FIRST_TIME_HOSTING_SETUP.cmd WindowsServer ...` | Scheduled application/Caddy services using external durable providers |
| Native Linux/systemd | `deploy/linux/setup-einvite-linux-once.sh`, then `deploy/linux/install-einvite-linux.sh` | Hardened systemd service using external durable providers |
| Railway, Render, Fly.io, Azure, AWS, Google Cloud, or another container host | `Dockerfile.online` | Provider-managed deployment; see `deploy/paas/PAAS_DEPLOYMENT.md` |

GitHub Pages and other static-only hosts can show static files but cannot run the complete platform. Authentication, uploads, RSVP storage, publishing, background jobs, and AI routing require the Python backend and durable services.

## Software requirements

### Basic/local operation

- 64-bit Python 3.10 or newer.
- A modern browser.
- The Python packages in `requirements-production.txt`.
- Git and Node.js are useful developer tools but are not required to run the Python application.

### Automated testing

- Everything above.
- Packages in `requirements-test.txt`.
- Playwright Chromium. Use `SETUP_EINVITE_COMPLETE.bat` on Windows or Linux setup with `--with-tests`.

### Permanent production hosting

- A domain/subdomain and working DNS.
- HTTPS reverse proxy such as Caddy or an existing IIS/Nginx installation.
- PostgreSQL, authenticated Redis, private S3/R2/MinIO object storage, and off-host backups.
- A fail-closed malware scanner such as ClamAV or Microsoft Defender.
- SMTP for transactional email when email features are enabled.
- Payment and AI-provider credentials only when those optional features are enabled.

Never commit `.env.production`, database files, signing secrets, provider keys, private uploads, or backup archives.

## Windows 10/11 local setup

1. Extract the entire ZIP to a normal folder. Do not run it from inside the ZIP.
2. Right-click `FIRST_TIME_SETUP.cmd` and choose **Run as administrator**, or double-click it and approve the prompt.
3. After it reports `FIRST_TIME_SETUP_COMPLETE`, run `RUN_EINVITE_LOCAL.bat`.
4. Open `http://127.0.0.1:8080` if the browser does not open automatically.

The quick setup installs production runtime libraries but skips the large browser-testing download. Use `SETUP_EINVITE_COMPLETE.bat` when this computer will also run the full review suite.

For other devices on the same trusted Wi-Fi/LAN:

```cmd
FIRST_TIME_HOSTING_SETUP.cmd Network
```

Keep the hosting window open. Use the displayed private-network address on the other device. Do not forward port 8080 directly to the public internet.

## Permanent Docker host

This is the recommended single-server path. On Windows 10/11, install/start Docker Desktop. On Linux, install Docker Engine and the Compose v2 plugin from Docker's instructions for that distribution.

Point the domain to the server and allow inbound TCP 80/443 (and optionally UDP 443). Keep 8080, PostgreSQL, Redis, MinIO, and ClamAV private.

Windows command:

```cmd
FIRST_TIME_HOSTING_SETUP.cmd Docker -Domain invite.example.com
```

The first run creates `.env.production` with random independent secrets when it does not exist. It does not overwrite an existing file.

Linux commands:

```bash
bash deploy/linux/setup-einvite-linux-once.sh --mode docker
./.venv/bin/python prepare_production_env.py \
  --public-url https://invite.example.com \
  --trusted-proxy-ips 172.31.52.10
export EINVITE_DOMAIN=invite.example.com
docker compose --env-file .env.production \
  -f docker-compose.production.example.yml \
  -f deploy/docker-compose.online.yml config --quiet
docker compose --env-file .env.production \
  -f docker-compose.production.example.yml \
  -f deploy/docker-compose.online.yml up -d --build
```

Verify:

```bash
curl -fsS https://invite.example.com/api/health/ready
```

## Windows Server

Native Windows Server hosting is intended for organizations that already have external PostgreSQL, authenticated Redis, private S3/R2 storage, backups, and DNS. Docker Desktop is not installed on Windows Server.

1. Install 64-bit Python 3.10+ and Microsoft Defender. Install official Caddy or configure IIS as the reverse proxy.
2. Open Command Prompt or PowerShell as Administrator.
3. Run once:

```cmd
FIRST_TIME_HOSTING_SETUP.cmd WindowsServer -Domain invite.example.com -CaddyExe C:\Tools\caddy.exe
```

If `.env.production` does not exist, the first run creates it and intentionally stops. Edit the Docker-only `postgres`, `redis`, and `minio` endpoints to use the real managed services, set the off-host backup configuration, SMTP, and optional billing/AI values, then run the same command again.

The completed installer registers `EInvite-Web` and, when Caddy is supplied, `EInvite-Caddy` as restartable startup tasks. The Python app binds only to loopback port 8080.

With IIS, omit `-CaddyExe`, keep port 8080 private, and proxy HTTPS to `127.0.0.1:8080`.

## Native Linux server with systemd

The Docker path is easier and includes the full service set. For a managed native server:

```bash
sudo mkdir -p /opt/einvite
# Extract/copy the complete project into /opt/einvite first.
cd /opt/einvite
sudo bash deploy/linux/setup-einvite-linux-once.sh \
  --mode systemd --install-system-packages
```

Configure `.env.production` with real PostgreSQL, Redis, S3/R2/MinIO, off-host backup, SMTP, and optional provider endpoints. Do not use Docker hostnames for a native installation. Then run:

```bash
sudo bash deploy/linux/install-einvite-linux.sh \
  --domain invite.example.com \
  --caddy-snippet /etc/caddy/conf.d/einvite.caddy
```

The Caddy snippet is never overwritten. Ensure the main Caddyfile imports the directory, validate Caddy, and reload it. Verify both the private and public readiness endpoints.

## Container hosting services

Read `deploy/paas/PAAS_DEPLOYMENT.md`. The host must support separate web, worker, and scheduler processes using the same image and secrets. Attach managed PostgreSQL, Redis, object storage, malware scanning, HTTPS/custom domain, logging, monitoring, and external backups. A single disposable web container is not the complete system.

## Required checks before accepting customers

1. Run `python production_preflight.py --env-file .env.production --check-dependencies` for native deployments.
2. Run `python release_check.py` before promoting a changed build.
3. Confirm `/api/health/live` and `/api/health/ready` through HTTPS.
4. Test registration, upload/malware rejection, publishing, RSVP, email, payment webhook if enabled, and AI provider if enabled.
5. Back up PostgreSQL, object storage, and stable secret files to another machine/provider.
6. Perform and document a complete restore drill.
7. Enable monitoring for readiness, TLS expiry, failed jobs, storage capacity, malware signatures, and backups.

## Updating an existing installation

- Make a verified backup first.
- Keep the existing `.env.production` and signing secrets; do not regenerate them during a normal update.
- Replace application source with the new release, rerun the appropriate first-time setup script to refresh dependencies, run the release/preflight checks, and restart services.
- Keep the previous known-good release available for rollback. Database migrations and publication snapshots must not be rolled back by deleting live data.

More detailed production architecture is available in `ONLINE_AND_SERVER_HOSTING.md`, `PRODUCTION_DEPLOYMENT.md`, `PRODUCTION_LAUNCH_CHECKLIST.md`, and `V32_OPERATIONS.md`.
