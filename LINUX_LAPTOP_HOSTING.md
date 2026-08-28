# Linux Laptop Hosting Guide

## Quick Start

For the simplest one-command installation on a Linux laptop:

```bash
cd /path/to/einvite
sudo bash deploy/linux/install-einvite-laptop.sh --install-system-packages
```

This script performs a complete installation including:
- Installing Python 3.10+ and system dependencies
- Creating an isolated virtual environment
- Installing all production dependencies
- Setting up SQLite database (no PostgreSQL required)
- Configuring local file storage (no S3 required)
- Integrating ClamAV for malware scanning
- Configuring firewall rules
- Auto-detecting your private IP for LAN access
- Starting the server automatically

## Usage Options

```bash
# Basic installation (assumes Python already installed)
sudo bash deploy/linux/install-einvite-laptop.sh

# Install system packages too (recommended for fresh systems)
sudo bash deploy/linux/install-einvite-laptop.sh --install-system-packages

# Local-only mode (no LAN access, more secure)
sudo bash deploy/linux/install-einvite-laptop.sh --local-only

# Custom port
sudo bash deploy/linux/install-einvite-laptop.sh --port 8081

# Skip firewall configuration
sudo bash deploy/linux/install-einvite-laptop.sh --skip-firewall

# Don't auto-open browser
sudo bash deploy/linux/install-einvite-laptop.sh --skip-browser

# Include test dependencies
sudo bash deploy/linux/install-einvite-laptop.sh --with-tests

# Combine multiple options
sudo bash deploy/linux/install-einvite-laptop.sh \
  --install-system-packages \
  --port 8081 \
  --skip-browser
```

## What Gets Installed

### System Packages (with --install-system-packages)
- **Python 3.10+** with venv and pip
- **ClamAV** for malware scanning
- **Firewalld/UFW** for firewall management
- Development tools and certificates

### Application Components
- Isolated Python virtual environment in `.venv/`
- Production dependencies from `requirements-production.txt`
- SQLite database in `data/db/`
- Upload storage in `data/uploads/`
- Logs in `data/logs/`
- Backups in `data/backups/`

### Configuration
The script generates a `.env.production` file with:
- Random security secrets
- SQLite database URL (no external DB needed)
- Local filesystem storage
- Malware scanning enabled
- Email/payments/AI disabled by default

### Network Access
- **Local**: http://127.0.0.1:8080
- **Network**: http://YOUR_LAN_IP:8080 (devices on same WiFi/LAN)

## Managing the Server

### Check Status
```bash
curl http://127.0.0.1:8080/api/health/live
```

### View Logs
```bash
tail -f data/logs/server.log
```

### Stop Server
```bash
kill $(cat data/einvite.pid)
```

### Restart Server
```bash
cd /path/to/einvite
.venv/bin/python server.py --env-file .env.production
```

## Firewall Configuration

The script attempts to configure your firewall automatically:

### Ubuntu/Debian (UFW)
```bash
sudo ufw allow 8080/tcp
```

### RHEL/Fedora/CentOS (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### Manual Configuration
If automatic configuration fails, manually allow port 8080 for your private network.

## Security Notes

### This is Private Network Hosting
- ✅ Safe for home/office WiFi networks
- ✅ Devices on same LAN can access
- ❌ NOT exposed to public internet
- ❌ Do NOT forward port 8080 to router

### Malware Scanning
- ClamAV scans all uploads automatically
- Keep virus definitions updated: `sudo freshclam`
- Alternative: Use existing antivirus on your system

### Backups
Regularly backup the `data/` directory:
```bash
tar -czf einvite-backup-$(date +%Y%m%d).tar.gz data/
```

Use the provided backup script if available:
```bash
bash BACKUP_EINVITE_DATA.bat  # Windows
# or manually backup data/ on Linux
```

## Troubleshooting

### Python not found
```bash
# Ubuntu/Debian
sudo apt install python3 python3-venv python3-pip

# RHEL/Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip python-virtualenv
```

### Port already in use
```bash
# Find what's using port 8080
sudo lsof -i :8080

# Use a different port
sudo bash deploy/linux/install-einvite-laptop.sh --port 8081
```

### ClamAV not running
```bash
# Ubuntu/Debian
sudo systemctl enable --now clamav-daemon clamav-freshclam

# RHEL/Fedora
sudo systemctl enable --now clamd@scan
```

### Server won't start
Check logs:
```bash
cat data/logs/server.log
```

Common issues:
- Missing dependencies: Run with `--install-system-packages`
- Port conflict: Use `--port` to change
- Permission issues: Ensure you're using `sudo`

## Comparison with Other Deployment Methods

| Method | Best For | Complexity | External Dependencies |
|--------|----------|------------|----------------------|
| **Laptop Script** | Personal/testing use on Linux | ⭐ Simplest | None (SQLite + local files) |
| **systemd Service** | Production Linux server | ⭐⭐ Moderate | PostgreSQL, Redis, S3 |
| **Docker Compose** | Multi-server production | ⭐⭐⭐ Advanced | Docker Engine |
| **PaaS** | Cloud hosting | ⭐⭐ Moderate | Provider account |

## When to Upgrade to Full Production

The laptop installer uses simplified settings suitable for personal use. Consider upgrading to full production deployment when you need:

- ✅ Public internet access with HTTPS
- ✅ Multiple concurrent users (>50)
- ✅ Email notifications
- ✅ Payment processing
- ✅ AI features
- ✅ High availability
- ✅ Professional monitoring
- ✅ Automated backups to remote location

For production deployment, see:
- `FIRST_TIME_INSTALL_AND_HOSTING.md`
- `ONLINE_AND_SERVER_HOSTING.md`
- `PRODUCTION_DEPLOYMENT.md`

## Support

For issues specific to Linux laptop hosting:
1. Check `data/logs/server.log` for errors
2. Verify prerequisites: `python3 --version`
3. Test connectivity: `curl http://127.0.0.1:8080/api/health/live`
4. Review firewall settings
5. Ensure ClamAV is running (if enabled)

For general eInvite documentation, see the main README.md and other guides in the project root.
