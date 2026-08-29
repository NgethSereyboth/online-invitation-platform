# E-Invitation Platform — Professional Invitation Design & Event Management

[![Release](https://img.shields.io/badge/release-V28-blue)](V28_ARCHITECTURE.md)
[![License](https://img.shields.io/badge/license-proprietary-red)](LICENSE)

## 🎨 What It Does

**eInvite** is a professional invitation design and event management platform with:

- **Canva-quality visual editor** with drag-and-drop design
- **Bilingual support**: English + Khmer (with lunar calendar integration)
- **Guest management** with RSVP, meal preferences, and private messages
- **Team collaboration** with real-time review and approval workflows
- **AI-powered design assistance** with budget controls
- **Template marketplace** for reusable designs
- **Plugin platform** for extensible features
- **Event automation** for programs, tasks, vendors, and incidents
- **Self-hosted deployment** on Windows, Linux, or Docker

## 🚀 Quick Start

### Windows Laptop Hosting
```cmd
HOST_EINVITE_ON_LAPTOP.bat
```

### Linux Laptop Hosting
```bash
sudo bash deploy/linux/install-einvite-laptop.sh --install-system-packages
```

### Docker Production Hosting
```bash
# See FIRST_TIME_INSTALL_AND_HOSTING.md for complete instructions
```

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [FIRST_TIME_INSTALL_AND_HOSTING.md](FIRST_TIME_INSTALL_AND_HOSTING.md) | Complete installation guide for all platforms |
| [LINUX_LAPTOP_HOSTING.md](LINUX_LAPTOP_HOSTING.md) | One-command Linux laptop setup |
| [LAPTOP_HOSTING.md](LAPTOP_HOSTING.md) | Windows laptop hosting guide |
| [ONLINE_AND_SERVER_HOSTING.md](ONLINE_AND_SERVER_HOSTING.md) | Production server deployment |
| [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) | Production architecture and operations |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture overview |
| [SECURITY.md](SECURITY.md) | Security features and hardening |

## ✨ Core Features

### Design & Editing (V24-V32)
- Professional visual editor with direct manipulation
- Smart layouts and responsive templates
- Custom typography with Khmer font support
- Photo editing and media workflow
- Animation export capabilities (V44)

### Guest Management (V23-V32)
- RSVP system with custom questions
- Guest lists and contact management
- Private wishes/messages from guests
- QR code invitation sharing
- Public guest pages

### Collaboration (V23.8+)
- Multi-user collaboration with presence indicators
- Comment threads and approvals
- Activity timeline tracking
- Publishing gates with 1-5 required approvals
- Version control with snapshots

### AI & Automation (V35, V48, V52)
- AI Agent for design assistance
- Plugin platform for extensions
- Event program and task automation
- Vendor and incident management
- Deterministic conflict detection

### Enterprise Features (V42-V47)
- Government/enterprise protocols (V42)
- Publishing domains with verification (V45)
- Data merge and bulk operations (V47)

## 🔧 Self-Hosting Options

| Method | Best For | Complexity |
|--------|----------|------------|
| **Windows Laptop** | Personal use on Windows | ⭐ Simplest |
| **Linux Laptop** | Personal use on Linux | ⭐ Simplest |
| **Docker Compose** | Production server | ⭐⭐⭐ Advanced |
| **Native Linux** | Enterprise deployment | ⭐⭐ Moderate |
| **PaaS** | Cloud hosting | ⭐⭐ Moderate |

### Requirements

**Minimum:**
- Python 3.10+
- Modern browser (Chrome, Firefox, Edge)
- 2GB RAM, 1GB disk space

**Production (Docker/Native):**
- PostgreSQL 14+
- Redis 6+
- Object storage (S3/R2/MinIO)
- HTTPS reverse proxy (Caddy/Nginx)
- ClamAV for malware scanning

## 🛡️ Security Features

- Scoped roles and workspace memberships
- Signed URLs for secure media access
- GDPR-style privacy requests
- Immutable publication fingerprints
- Malware scanning on all uploads
- Secret-safe logging
- Audit timelines with hash verification

## 📦 Backup & Recovery

- Automated backup scheduling
- Recovery archives for download
- Hash-verified audit timeline
- Off-host backup support
- Documented restore procedures

## 🧪 Testing & Quality

Run the complete test suite:
```bash
python release_check.py
```

Version-specific tests:
```bash
python tests/v28_*.py
```

Three-run certification:
```bash
./RUN_V28_RELEASE_CHECK_LINUX.sh  # Linux
RUN_V28_RELEASE_CHECK_LINUX.bat   # Windows
```

## 📄 License

Proprietary software. See LICENSE file for terms.

## 🤝 Support

For issues and questions:
1. Check relevant documentation in project root
2. Review version-specific reports (V*_REPORT.md files)
3. Check logs in `data/logs/`
4. Run preflight checks: `python production_preflight.py`

## 🗺️ Roadmap

- ✅ V24-V28: Core platform stability
- ✅ V29-V32: Advanced editing and collaboration
- ✅ V35-V36: AI agent and template marketplace
- ✅ V42-V48: Enterprise features and plugin platform
- ✅ V52-V53: Event automation ecosystem
- 🔜 Future: Mobile apps, advanced analytics, more integrations

---

**Ready to get started?** Run the laptop hosting script for your platform above, or see [FIRST_TIME_INSTALL_AND_HOSTING.md](FIRST_TIME_INSTALL_AND_HOSTING.md) for complete deployment options.
