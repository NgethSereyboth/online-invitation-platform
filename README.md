# eInvite Platform

A self-hosted, professional invitation design & event management platform. Bilingual (English + Khmer). Governed AI agent with 80 typed tools. Production hardening (Argon2id, MFA, passkeys, CSP, audit events, malware scanning). Self-hostable on a laptop or scaled to PostgreSQL + S3/R2/MinIO.

> **Public version:** V0.52 · **Latest internal milestone:** V53.1 (AI Project Operator) · **Hardening:** V54
> See `VERSION_HISTORY.md` for the full version timeline.

---

## 📁 Directory Structure

```
einvite-platform/
├── src/                      # Source code
│   ├── css/                  # Stylesheets (design tokens + per-page sheets;
│   │                         #   bundle-*.css and editor-suite.css are GENERATED)
│   ├── js/                   # JavaScript modules (bundle-*.js and
│   │                         #   editor-suite.js are GENERATED)
│   ├── html/                 # HTML pages (16 + manifest.webmanifest)
│   └── python/               # Python backend (26 source files + synced bundles)
│
├── ai_agent/                 # AI Agent service (V28, V35, V53.1)
│   ├── service.py            # Main AI service
│   ├── tools.py              # 80 typed tool definitions
│   ├── capabilities.py       # Capability discovery + access snapshots
│   ├── providers.py          # 6 LLM provider classes (external/local/failover)
│   └── local_providers.py    # Offline fallback providers
│
├── platform_v32/             # V32 production platform
│   ├── service.py            # Workspaces, roles, authorization
│   ├── storage.py            # ObjectStorage: local | s3 | r2 | minio
│   ├── jobs.py               # Durable JobQueue + idempotency keys
│   └── observability.py      # Per-workspace metrics + secret-redacting logger
│
├── future_platform_v52/      # V34–V52 capability layer
│   ├── service.py            # Event ecosystem, automation, marketplace
│   └── schema.py             # Schema 27 additive migrations
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
│   ├── ROADMAP.md            # Development roadmap (Phases 0–5)
│   └── V*_RELEASE_*.sha256   # Release verification hashes
│
├── assets/                   # Static assets
│   └── fonts/                # Self-hosted fonts (Noto Sans/Serif Latin + Khmer, OFL-1.1)
│
├── licenses/                 # License files
│   └── fonts/                # Font licenses (Noto OFL-1.1)
│
├── vendor/                   # Third-party libraries
│   └── momentkh.js           # Khmer lunar calendar library
│
├── .gitignore                # Git ignore rules
└── .nojekyll                 # GitHub Pages bypass
```

---

## 🚀 Quick Start (verified from a clean clone; Ubuntu 24.04 · Python 3.12)

### Option A — Production-style install (with malware scanning)

```bash
# 1. System packages
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip \
  clamav clamav-daemon ca-certificates curl git
sudo systemctl enable --now clamav-daemon
sudo freshclam                                   # first-time virus DB

# 2. Clone (or unzip) and enter the repo — <YOUR_REPO_URL> is a placeholder:
#    pass your fork's clone URL, or a local path ending in .git
git clone <YOUR_REPO_URL> einvite-platform
cd einvite-platform

# 3. Create venv + install Python deps
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r docs/requirements-production.txt

# 4. Start the server (PYTHONPATH includes src/python/ for local module
#    imports + repo root for ai_agent/, platform_v32/, future_platform_v52/)
PYTHONPATH=src/python:. .venv/bin/python src/python/server.py --host 127.0.0.1 --port 4175

# 5. Open http://127.0.0.1:4175 in a browser.
```

### Option B — Dev-only fast path (no ClamAV, for quick evaluation)

```bash
git clone <YOUR_REPO_URL> einvite-platform
cd einvite-platform
python3 -m venv .venv
.venv/bin/pip install -r docs/requirements-production.txt
PYTHONPATH=src/python:. EINVITE_ALLOW_NO_SCANNER=1 .venv/bin/python src/python/server.py
# → http://127.0.0.1:4175
```

> Ubuntu 24.04+ and Debian 12+ mark the system interpreter as externally managed
> (PEP 668), so a bare `pip install` is refused. The venv above is the supported
> path on every machine — no `sudo`, no `--break-system-packages`.

### Option C — One-command demo

```bash
# One-liner for evaluation (ClamAV-less dev mode)
git clone <YOUR_REPO_URL> einvite-platform && cd einvite-platform \
  && python3 -m venv .venv \
  && .venv/bin/pip install -r docs/requirements-production.txt \
  && PYTHONPATH=src/python:. EINVITE_ALLOW_NO_SCANNER=1 .venv/bin/python src/python/server.py
# → open http://127.0.0.1:4175
```

> The server auto-generates `EINVITE_SECRET_KEY` and `EINVITE_BILLING_WEBHOOK_SECRET` into a repo-root `.env` (mode 0600) on first run via `src/python/features/secrets.py`. You do **not** need to pre-set secrets for the dev fast path.

### Windows laptop hosting

```powershell
# From an elevated PowerShell in the repo root
.\scripts\setup-einvite-complete.ps1
```

### Docker deployment (production)

> ℹ️ **V2 syntax.** The legacy `docker-compose` V1 CLI is deprecated. Use `docker compose` (V2 plugin) with the `--env-file` flag.

```bash
# Generate production secrets into ./.env.production (repo root, mode 0600).
# Both flags are required: your canonical HTTPS origin, and the CIDRs/IPs allowed
# to reach /api/admin/* (your reverse proxy or VPN ranges).
python3 src/python/build/prepare_production_env.py \
  --public-url https://events.example.com \
  --admin-ip-allowlist 203.0.113.0/24

# Start with the production overlay
docker compose --env-file .env.production \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.online.yml up -d
```

---

## 📊 Project Statistics

- **Frontend**: 175 JS modules · 119 CSS stylesheets · 16 HTML pages + `manifest.webmanifest`
- **Backend**: 3 Python service packages (`platform_v32`, `future_platform_v52`, `ai_agent`)
- **Tests**: 200+ integration and unit tests
- **Documentation**: 111 markdown files covering all features
- **Deployment**: Multi-platform (Linux, Windows, Docker, PaaS)

---

## 🎯 Key Features (vs. market benchmark)

| Capability | eInvite | Paperless Post | Evite | Zola | Canva |
|---|---|---|---|---|---|
| True digital invitations (incl. formal send) | ✅ | ✅ | ✅ | ❌ (print only) | ✅ |
| Event / RSVP / guest management | ✅ | ❌ | ✅ | ✅ (partial) | ❌ |
| **Self-hostable (private / laptop)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Bilingual (English + Khmer)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Governed AI agent** (80 tools, multi-stage auth, confirmation boundaries) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Plugin platform (V48, sandboxing in Phase 4a) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **No per-guest fees** (storage-tier pricing) | ✅ | ❌ (coins $0.50–$1.44/guest) | ❌ (Pro $249.99/yr + ads) | ❌ | ❌ |
| Post-send editing *(planned, Phase 2a)* | ✅ roadmap | ❌ (locks after send) | ❌ | — | — |
| Multi-channel delivery (SMS / WhatsApp / Telegram) *(planned, Phase 2a)* | ✅ roadmap | ❌ | ❌ | ❌ | ❌ |

### Existing feature highlights

- 🎨 Canva-quality visual editor with direct manipulation + WebGL/GPU projection (V22, V29, V30)
- 🤝 Snapshot-based publishing; **CRDT collaboration** (V31 — polling + durable checkpoints, not pure SSE)
- 🌐 Production adapters: PostgreSQL, Redis, S3/R2/MinIO, SMTP, billing, external AI
- 🔐 Security: **Argon2id, MFA (TOTP), passkeys (WebAuthn), CSP** (`script-src 'self'`), rate limiting (Redis or in-process), hash-chained immutable audit events
- 🦠 **Malware scanning on every upload** (V54 — ClamAV on Linux, Defender on Windows, fail-closed)
- 💾 SQLite for dev/single-instance; PostgreSQL for production
- 🔄 Backups + restore drill support (Phase 1c deliverable)

---

## 📖 Documentation

All documentation lives under `docs/`. Key entry points:

- `docs/ARCHITECTURE.md` — system architecture overview (with Mermaid diagram)
- `docs/ROADMAP.md` — development roadmap (Phases 0–5)
- `docs/LINUX_LAPTOP_HOSTING.md` — Linux installation guide
- `docs/FIRST_TIME_INSTALL_AND_HOSTING.md` — getting started
- `docs/PRODUCTION_DEPLOYMENT.md` — production deployment guide
- `docs/AI_LEARNING_AND_AUTOMATION_V53.md` — AI features
- `docs/SECURITY.md` — security overview
- `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` — V54 hardening report
- `VERSION_HISTORY.md` — full version timeline (V1 → V53.1 + V54)

---

## 🔧 Development

```bash
# Install the dev/test toolchain. requirements-dev.txt is the supported target:
# it pins pytest (and pytest-timeout) and pulls in docs/requirements-test.txt
# for Playwright, Pillow, qrcode, fonttools and Brotli.
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Browser tests need Chromium; without it they skip unless EINVITE_REQUIRE_BROWSER=1.
.venv/bin/python -m playwright install chromium

# Run tests (the Makefile uses .venv/bin/python when it exists, as the gates do)
.venv/bin/python -m pytest tests/

# Production-only dependencies, for a deployment that does not run tests
.venv/bin/pip install -r docs/requirements-production.txt

# Start development server (PYTHONPATH includes src/python/ for local
# module imports + repo root for ai_agent/, platform_v32/, future_platform_v52/)
PYTHONPATH=src/python:. EINVITE_ALLOW_NO_SCANNER=1 .venv/bin/python src/python/server.py

# Rebuild every generated artifact after editing JS/CSS sources
python3 build.py all
python3 build.py all --check        # must pass before you commit

# or use the Makefile
make build   # = python3 build.py all
make check   # = python3 build.py bundles --check
make test    # = python3 -m pytest tests/
make serve   # static preview on http://127.0.0.1:8124
make dev     # the real server (API + assets)
```

`build.py` is the only supported build entry point. The historical repo-root
scripts (`build_route_bundles.py`, `build_editor_bundle.py`,
`build_page_manifests.py`) still exist as deprecated shims so older callers keep
working — see [CONTRIBUTING.md](CONTRIBUTING.md) for the hard rules, the
directory map and a "where does new code go" decision tree.

> **Note:** The previous draft of this README suggested `python -m platform_v32.service` as a dev command — that module has no `__main__` block. The correct entry point is `src/python/server.py` with `PYTHONPATH=`.

### Quality & security verification

The QA branch keeps edge-case, accessibility and visual checks repeatable:

```bash
# API edge cases: malformed JSON, wrong types, boundary values, Unicode
.venv/bin/python scripts/qa_api_fuzz.py

# Accessibility and visual regressions (server must already be running)
npx playwright test --config=e2e/playwright.config.ts --project=chromium e2e/specs/06-a11y.spec.ts
npx playwright test --config=e2e/playwright.config.ts --project=chromium e2e/specs/07-visual.spec.ts
```

Every HTML response carries a fresh CSP `style-src` nonce in the
`Content-Security-Policy` header; server-rendered `<style>` tags receive that nonce, and pages
without inline scripts expose it only through the header. The authenticated ZAP DAST workflow
(`.github/workflows/dast-authenticated.yml`) runs on every pull request against a disposable
loopback fixture, so the active scanner can never be pointed at production.

---

## 🖼️ Screenshots

> Screenshots coming soon — the maintainer should add production-quality captures to `docs/screenshots/`. No screenshot images are committed yet.

| Path | What to show |
|---|---|
| `docs/screenshots/editor.png` | Studio editor canvas with a sample invitation, toolbar/sidebar/canvas visible (v54 chrome) |
| `docs/screenshots/rsvp-flow.png` | Public invitation page + RSVP form with custom questions |
| `docs/screenshots/ai-agent.png` | AI agent panel proposing an invitation draft with confirmation-boundary modal |
| `docs/screenshots/bilingual-toggle.png` | Same invitation in English and Khmer, side-by-side, showing the lunar-calendar integration |

---

## 📝 License

See individual license files in the `licenses/` directory. Notably:
- `licenses/fonts/Noto-OFL-1.1.txt` — Noto Sans/Serif Khmer & Latin, OFL-1.1

Third-party vendor code:
- `vendor/momentkh.js` — Khmer lunar calendar library (see file header for license)

---

*Phase 0.3 deliverable of `docs/ROADMAP.md`. Verified against actual code 2026-09-14.*
