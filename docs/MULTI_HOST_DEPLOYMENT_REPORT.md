# V0.52 multi-host deployment implementation

Implemented on 2026-08-09 without modifying the project README.

## Added

- Unified Windows entry point: `DEPLOY_EINVITE_SERVER.bat`.
- PowerShell target manager for file validation, Docker/VPS deployment, and Windows Server installation.
- Public Docker overlay with Caddy automatic HTTPS, private backend networking, ClamAV, health checks, and persistent volumes.
- Online container image with an unprivileged runtime and remote `clamdscan` client.
- Native Windows Server launchers using restartable Scheduled Tasks, loopback-only backend binding, Caddy, and required Microsoft Defender scanning.
- Hardened Linux systemd service, cautious installer, and Caddy template.
- Docker-compatible PaaS process/service contract.
- Canonical allowed-host generation in `.env.production`.

## Intentional boundaries

- Cloud accounts, domains, DNS, external database/storage credentials, and payment/mail/AI credentials are not created automatically.
- Native Windows/Linux production still requires real external durable services.
- Existing Caddy/IIS configuration is never overwritten automatically.
- Public firewall exposure on Windows requires an explicit switch when the NIC uses the Public profile.
