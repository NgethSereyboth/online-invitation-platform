# eInvite Self-Hosted Deployment for Linux Laptops

This guide covers deploying eInvite on a Linux laptop for personal use, local development, or LAN sharing.

## Quick Start

### One-Command Installation

```bash
cd /workspace
sudo bash deploy/linux/install-einvite-laptop.sh --install-system-packages
```

This will:
- Install all system dependencies (Python, ClamAV, etc.)
- Create a virtual environment
- Install Python packages
- Initialize the database
- Configure log rotation
- Set up automated backups
- Start the server
- Open your browser automatically

## Manual Installation

If you've already installed dependencies:

```bash
cd /workspace
bash deploy/linux/install-einvite-laptop.sh
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EINVITE_PORT` | 8080 | Server port |
| `EINVITE_LOCAL_ONLY` | false | Restrict to localhost only |
| `CLAMAV_ENABLED` | true | Enable malware scanning |
| `FIREWALL_ENABLED` | false | Auto-configure firewall |

### Command Line Options

```bash
# Full installation with system packages
sudo bash deploy/linux/install-einvite-laptop.sh --install-system-packages

# Enable firewall configuration
sudo bash deploy/linux/install-einvite-laptop.sh --enable-firewall

# Localhost only (no LAN access)
bash deploy/linux/install-einvite-laptop.sh --local-only

# Custom port
bash deploy/linux/install-einvite-laptop.sh --port 3000

# Disable ClamAV (faster startup)
bash deploy/linux/install-einvite-laptop.sh --no-clamav

# Show help
bash deploy/linux/install-einvite-laptop.sh --help
```

## Post-Installation

### Access the Application

- **Local**: http://127.0.0.1:8080
- **LAN**: http://<your-ip>:8080 (if not using --local-only)

### Management Commands

```bash
# Stop the server
pkill -f 'python.*app.py'

# View logs
tail -f /workspace/logs/einvite.log

# Manual backup
/workspace/deploy/linux/backup-einvite.sh

# Restart (run installer again)
bash deploy/linux/install-einvite-laptop.sh
```

### Systemd Service (Optional)

If systemd is available, a service file is created automatically:

```bash
# Start
sudo systemctl start einvite

# Stop
sudo systemctl stop einvite

# Enable on boot
sudo systemctl enable einvite

# View status
sudo systemctl status einvite
```

## Directory Structure

```
/workspace/
├── data/           # SQLite database
├── media/          # Uploaded files
├── logs/           # Application logs
├── backups/        # Automated backups
├── venv/           # Python virtual environment
└── deploy/linux/   # Deployment scripts
    ├── install-einvite-laptop.sh
    └── backup-einvite.sh
```

## Backup & Recovery

### Automated Backups

Backups run daily at 2:00 AM (if crontab is available) and include:
- SQLite database
- Media files (compressed)
- Configuration

### Manual Backup

```bash
/workspace/deploy/linux/backup-einvite.sh
```

Backup location: `/workspace/backups/einvite_backup_YYYYMMDD_HHMMSS/`

### Restore from Backup

```bash
# Stop server
pkill -f 'python.*app.py'

# Restore database
cp /workspace/backups/einvite_backup_*/einvite.db /workspace/data/

# Restore media
tar -xzf /workspace/backups/einvite_backup_*/media.tar.gz -C /workspace/media/

# Restart server
bash deploy/linux/install-einvite-laptop.sh
```

## Troubleshooting

### Server Won't Start

```bash
# Check logs
tail -f /workspace/logs/einvite.log

# Validate Python environment
source /workspace/venv/bin/activate
python -c "import flask, PIL, qrcode, bcrypt"

# Reinstall dependencies
pip install -r /workspace/server/requirements.txt
```

### Port Already in Use

```bash
# Find process using port 8080
sudo lsof -i :8080

# Use different port
bash deploy/linux/install-einvite-laptop.sh --port 3000
```

### ClamAV Issues

```bash
# Disable ClamAV temporarily
bash deploy/linux/install-einvite-laptop.sh --no-clamav

# Update virus definitions manually
sudo freshclam

# Check ClamAV status
sudo systemctl status clamav-daemon
```

### Low Disk Space

```bash
# Check disk usage
df -h /workspace

# Clean old backups (keep last 7 days)
find /workspace/backups -type d -mtime +7 -exec rm -rf {} \;

# Clean old logs
find /workspace/logs -name "*.log" -mtime +14 -delete
```

## Security Considerations

### For LAN Access

1. Enable firewall:
   ```bash
   sudo bash deploy/linux/install-einvite-laptop.sh --enable-firewall
   ```

2. Use strong passwords for admin accounts

3. Consider HTTPS setup (requires additional configuration)

### For Public Access

⚠️ **Not Recommended** - This script is designed for private/LAN use only. For public deployment, use the Docker or production deployment guides.

## Performance Tips

- Minimum 2GB RAM recommended
- SSD storage preferred for database performance
- Regular backups prevent data loss
- Monitor disk space with `df -h`

## Uninstallation

```bash
# Stop server
pkill -f 'python.*app.py'

# Remove systemd service (if exists)
sudo systemctl disable einvite
sudo rm /etc/systemd/system/einvite.service

# Remove logrotate config
sudo rm /etc/logrotate.d/einvite

# Remove application files
rm -rf /workspace/venv /workspace/data /workspace/logs /workspace/backups /workspace/media
```

## Support

For issues or questions:
1. Check logs: `/workspace/logs/einvite.log`
2. Review this documentation
3. Consult the main README.md
