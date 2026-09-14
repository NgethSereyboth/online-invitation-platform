# eInvite Platform - Project Structure

A professional invitation design and event management platform with self-hosting capabilities.

## 📁 Directory Structure

```
einvite/
├── src/                      # Source code
│   ├── css/                  # Stylesheets (119 files)
│   ├── js/                   # JavaScript modules (175 files)
│   ├── html/                 # HTML pages (17 files)
│   └── python/               # Python backend utilities (26 files)
│
├── ai_agent/                 # AI Agent service (V53)
│   ├── service.py            # Main AI service
│   ├── tools.py              # AI tool definitions
│   ├── providers.py          # LLM provider adapters
│   └── ...
│
├── platform_v32/             # Core platform service (V32)
│   ├── service.py            # Main platform service
│   ├── schema.py             # Database schema
│   ├── storage.py            # Storage backend
│   └── ...
│
├── future_platform_v52/      # Next-gen platform (V52)
│   ├── service.py            # Event automation service
│   └── schema.py             # Extended schema
│
├── deploy/                   # Deployment configurations
│   ├── linux/                # Linux deployment scripts
│   │   ├── install-einvite-laptop.sh    # One-click laptop installer
│   │   ├── backup-einvite.sh            # Automated backups
│   │   └── einvite.service.template     # Systemd service
│   ├── windows/              # Windows deployment scripts
│   ├── paas/                 # PaaS configurations
│   ├── Dockerfile            # Container build
│   └── docker-compose.*.yml  # Compose configurations
│
├── scripts/                  # Utility scripts
│   ├── *.ps1                 # PowerShell scripts (Windows)
│   ├── *.sh                  # Shell scripts (Linux/Mac)
│   └── *.cmd/.bat            # Batch files (Windows)
│
├── tests/                    # Test suite (200+ tests)
│   ├── v*_*.py               # Version-specific tests
│   └── visual_regression.py  # Visual testing
│
├── docs/                     # Documentation & References
│   ├── *.md                  # Markdown documentation (111 files)
│   ├── *.json                # JSON configs & reports
│   ├── postgres_schema.sql   # Database schema reference
│   ├── requirements-*.txt    # Python dependencies
│   └── V*_RELEASE_*.sha256   # Release verification hashes
│
├── assets/                   # Static assets
│   └── fonts/                # Custom fonts
│
├── licenses/                 # License files
│   └── fonts/                # Font licenses
│
├── vendor/                   # Third-party libraries
│   └── momentkh.js           # Khmer calendar library
│
├── .gitignore                # Git ignore rules
└── .nojekyll                 # GitHub Pages bypass
```

## 🚀 Quick Start

### Linux Laptop Hosting
```bash
cd deinveitate
sudo bash deploy/linux/install-einvite-laptop.sh --install-system-packages
```

### Windows Laptop Hosting
```powershell
.\scripts\host-einvite-laptop.ps1
```

### Docker Deployment
```bash
docker-compose -f deploy/docker-compose.production.example.yml up -d
```

## 📊 Project Statistics

- **Frontend**: 175 JS modules, 119 CSS stylesheets, 17 HTML pages
- **Backend**: 3 Python service packages (platform_v32, future_platform_v52, ai_agent)
- **Tests**: 200+ integration and unit tests
- **Documentation**: 111 markdown files covering all features
- **Deployment**: Multi-platform support (Linux, Windows, Docker, PaaS)

## 🎯 Key Features

- 🎨 Canva-quality visual invitation editor
- 🌐 Bilingual support (English + Khmer)
- 👥 Guest management with RSVP
- 🤖 AI-powered design assistance
- 🔐 Multi-user collaboration with review workflows
- 📦 Template marketplace
- 🔌 Plugin platform
- 🎬 Event automation & operations
- 🖥️ Self-hosted deployment (SQLite or PostgreSQL)
- ☁️ Production-ready with backups, monitoring, and security

## 📖 Documentation

See `/docs` directory for comprehensive documentation:
- `ARCHITECTURE.md` - System architecture overview
- `LINUX_LAPTOP_HOSTING.md` - Linux installation guide
- `FIRST_TIME_INSTALL_AND_HOSTING.md` - Getting started
- `PRODUCTION_DEPLOYMENT.md` - Production setup
- `AI_LEARNING_AND_AUTOMATION_V53.md` - AI features

## 🔧 Development

```bash
# Install dependencies
pip install -r docs/requirements-production.txt

# Run tests
python -m pytest tests/

# Start development server
python -m platform_v32.service
```

## 📝 License

See individual license files in `/licenses` directory.
