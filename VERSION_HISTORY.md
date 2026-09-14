# eInvite Version History

This document tracks the evolution of the eInvite platform from initial development through current production-ready state.

## Version Timeline

### Early Development (V1-V17)
- **V1-V17**: Core invitation editor foundation
- Basic visual design capabilities
- Initial template system
- Simple text editing

### V18-V19: Release Check System
- Automated release validation
- Cross-platform testing (Windows/Linux)
- Quality gates for production releases

### V20-V21: Gate System Introduction
- **V20**: First gate implementation for quality control
- **V20.1**: Enhanced gate with additional checks
- **V21.0-V21.3**: Iterative improvements to gating system
- 3X reliability testing framework

### V23: Collaboration & Guest Management
- **V23.5-V23.6**: Enhanced gate systems
- **V23.7**: Guest management features
- **V23.8**: Multi-user collaboration, review system, activity timeline, publishing gates

### V24: Visual Editor Enhancement
- Canva-quality visual editor
- Smart layouts
- Professional typography
- Photo editing workflow

### V25: Security & Governance
- Scoped roles and workspace memberships
- Signed URLs for secure media access
- Privacy requests (GDPR-style)

### V26: Production Operations
- Self-hosted deployment (Docker, Windows/Linux native)
- Object storage support (local, S3, R2, MinIO)
- Durable job queues with retries/cancellation
- Windows readiness checks
- Local hosting optimizations

### V27: Enhanced Reliability
- **V27.3.5**: Advanced release checking
- Improved Windows readiness
- Better error handling and recovery
- Local hosting refinements

### V28: Cross-Platform Deployment
- Linux release checking
- Windows PowerShell automation
- Platform-specific optimizations

### V31-V32: Advanced Security
- Immutable publication fingerprints
- Secret-safe logging
- Backup/restore with recovery archives
- Audit timelines with hash verification
- Metrics, health checks, graceful shutdown

### V35: AI-Powered Features
- AI Agent for design assistance
- Budget controls
- Saved workflows
- Provider failover
- Registered tools for safe AI operations

### V36: Template Marketplace
- Versioned template catalog (public/private)
- Workspace installations
- Licensing metadata
- Moderation system
- Structured packages (no executable code)

### V42: Enterprise Protocols
- Government-grade security
- Advanced compliance features
- Enterprise workflow support

### V44: Animation Export
- Advanced animation capabilities
- Professional export formats

### V45: Publishing Domains
- Verified environments
- Domain management
- SSL/TLS support

### V47: Data Operations
- Data merge capabilities
- Bulk operations
- Import/export enhancements

### V48: Plugin Platform
- Declarative plugin manifests
- Allow-listed permissions
- Extension points
- Safe rendering of plugin blocks
- Installation/grant/revocation lifecycle

### V52: Event Automation
- Event programs, tasks, vendors, incidents
- Deterministic intelligence
- Conflict detection
- Overdue item tracking
- Bounded automations
- Operational dashboards

### V53: AI Learning & Automation
- Enhanced AI project operator
- Automated learning systems
- Advanced capability coverage
- Intelligent workflow optimization

## Current State (Latest)

The platform is now production-ready with:
- ✅ Visual invitation design with bilingual support (English + Khmer)
- ✅ Comprehensive guest management and RSVP system
- ✅ Team collaboration with review/approval workflows
- ✅ AI-assisted design and content generation
- ✅ Template marketplace with versioning
- ✅ Plugin extension system
- ✅ Event automation and operations management
- ✅ Self-hosted deployment (Linux/Windows/Docker)
- ✅ Enterprise-grade security and compliance
- ✅ Automated backups and disaster recovery
- ✅ Systemd service integration (Linux)
- ✅ One-command installation scripts

## Deprecated Scripts & Files

The following version-specific scripts have been consolidated into unified deployment tools:

### Removed Version-Specific Runners
- All `RUN_V*_GATE_3X.*` scripts (V20-V28)
- All `RUN_V*_RELEASE_CHECK_*` scripts (V18-V28)
- All `V*_WINDOWS_READINESS.*` scripts (V26-V27)

### Replaced By
- **Linux**: `deploy/linux/install-einvite-laptop.sh` - Unified installer
- **Windows**: `scripts/setup-einvite-complete.ps1` - Complete setup
- **Windows**: `scripts/host-einvite-laptop.ps1` - Laptop hosting
- **Backup**: `deploy/linux/backup-einvite.sh` - Automated backups

## Migration Notes

If you were using version-specific scripts:
1. Delete all old `RUN_V*` and `V*_READINESS` scripts
2. Use the new unified installation scripts
3. Refer to `LINUX_LAPTOP_HOSTING.md` or `FIRST_TIME_INSTALL_AND_HOSTING.md` for guidance

## Support

For deployment assistance, refer to:
- `README.md` - Quick start guide
- `docs/LINUX_LAPTOP_HOSTING.md` - Linux laptop hosting
- `docs/FIRST_TIME_INSTALL_AND_HOSTING.md` - General setup
- `docs/PRODUCTION_DEPLOYMENT.md` - Production deployment guide
