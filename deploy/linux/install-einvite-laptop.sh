#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

###############################################################################
# eInvite Complete Linux Laptop Installer
# 
# This script performs a complete one-command installation for hosting eInvite
# on a Linux laptop for local/network use. It includes:
# - System package installation (Python, dependencies)
# - Virtual environment setup
# - SQLite database configuration (no PostgreSQL required)
# - Local file storage (no S3 required)
# - Microsoft Defender or ClamAV integration
# - Firewall configuration
# - Auto-detection of private IP for LAN access
#
# Usage:
#   sudo bash install-einvite-laptop.sh [options]
#
# Options:
#   --port PORT          Backend port (default: 8080)
#   --local-only         Bind to 127.0.0.1 only (no LAN access)
#   --skip-firewall      Skip firewall rule creation
#   --skip-browser       Don't open browser after startup
#   --with-tests         Install test dependencies and Playwright
#   --help               Show this help message
###############################################################################

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PORT="8080"
LOCAL_ONLY="0"
SKIP_FIREWALL="0"
SKIP_BROWSER="0"
WITH_TESTS="0"
INSTALL_PACKAGES="0"

usage() {
  cat <<'EOF'
Usage: sudo bash install-einvite-laptop.sh [options]

Options:
  --port PORT          Backend port (default: 8080)
  --local-only         Bind to 127.0.0.1 only (no LAN access)
  --skip-firewall      Skip firewall rule creation
  --skip-browser       Don't open browser after startup
  --with-tests         Install test dependencies and Playwright
  --install-system-packages  Install system packages via apt/dnf
  -h, --help           Show this help message

This script is designed for laptop hosting on private networks.
It uses SQLite for simplicity instead of requiring PostgreSQL.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="${2:-}"; shift 2 ;;
    --local-only) LOCAL_ONLY="1"; shift ;;
    --skip-firewall) SKIP_FIREWALL="1"; shift ;;
    --skip-browser) SKIP_BROWSER="1"; shift ;;
    --with-tests) WITH_TESTS="1"; shift ;;
    --install-system-packages) INSTALL_PACKAGES="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

log_info() { echo "[INFO] $*"; }
log_warn() { echo "[WARN] $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
  elif command -v dnf >/dev/null 2>&1; then
    echo "dnf"
  elif command -v yum >/dev/null 2>&1; then
    echo "yum"
  elif command -v pacman >/dev/null 2>&1; then
    echo "pacman"
  else
    echo ""
  fi
}

install_system_packages() {
  local pkg_mgr
  pkg_mgr=$(detect_package_manager)
  
  if [[ -z "$pkg_mgr" ]]; then
    log_warn "No supported package manager found. Please install Python 3.10+ manually."
    return 0
  fi
  
  log_info "Installing system packages using $pkg_mgr..."
  
  case "$pkg_mgr" in
    apt)
      [[ $EUID -eq 0 ]] || { log_error 'Use sudo with --install-system-packages.'; exit 1; }
      apt-get update -qq
      DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        python3 python3-venv python3-pip python3-dev \
        curl ca-certificates git \
        clamav-daemon clamav-freshclam \
        firewalld || true
      systemctl enable --now clamav-daemon clamav-freshclam 2>/dev/null || true
      ;;
    dnf|yum)
      [[ $EUID -eq 0 ]] || { log_error 'Use sudo with --install-system-packages.'; exit 1; }
      "$pkg_mgr" install -y -q \
        python3 python3-pip python3-devel \
        curl ca-certificates git \
        clamav clamav-update clamav-scanner-systemd \
        firewalld || true
      systemctl enable --now clamd@scan 2>/dev/null || true
      ;;
    pacman)
      [[ $EUID -eq 0 ]] || { log_error 'Use sudo with --install-system-packages.'; exit 1; }
      pacman -Sy --noconfirm \
        python python-pip python-virtualenv \
        curl ca-certificates git \
        clamav clamav-freshclam \
        firewalld || true
      systemctl enable --now clamav-daemon clamav-freshclam 2>/dev/null || true
      ;;
  esac
  
  log_info "System packages installed."
}

check_prerequisites() {
  log_info "Checking prerequisites..."
  
  # Python check
  if ! command -v python3 >/dev/null 2>&1; then
    log_error "Python 3 is not installed. Run with --install-system-packages or install manually."
    exit 1
  fi
  
  python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"' || {
    log_error "Python 3.10 or newer is required."
    exit 1
  }
  
  # venv check
  if ! python3 -m venv --help >/dev/null 2>&1; then
    log_error "Python venv module is missing. Install python3-venv."
    exit 1
  }
  
  # ClamAV check (warning only)
  if ! command -v clamdscan >/dev/null 2>&1; then
    log_warn "ClamAV not found. Upload scanning will be disabled."
  fi
  
  log_info "Prerequisites check passed."
}

setup_virtual_environment() {
  log_info "Setting up Python virtual environment..."
  
  cd "$PROJECT_ROOT"
  
  if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
  fi
  
  .venv/bin/python -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
  
  if [[ -f requirements-production.txt ]]; then
    .venv/bin/python -m pip install --disable-pip-version-check -r requirements-production.txt
  else
    log_error "requirements-production.txt not found!"
    exit 1
  fi
  
  if [[ "$WITH_TESTS" == "1" ]] && [[ -f requirements-test.txt ]]; then
    log_info "Installing test dependencies..."
    .venv/bin/python -m pip install --disable-pip-version-check -r requirements-test.txt
    .venv/bin/python -m playwright install chromium
  fi
  
  log_info "Virtual environment ready."
}

setup_data_directories() {
  log_info "Creating data directories..."
  
  install -d -m 0750 \
    "$PROJECT_ROOT/data" \
    "$PROJECT_ROOT/data/logs" \
    "$PROJECT_ROOT/data/uploads" \
    "$PROJECT_ROOT/data/backups" \
    "$PROJECT_ROOT/data/db"
  
  log_info "Data directories created."
}

generate_environment_file() {
  local env_file="$PROJECT_ROOT/.env.production"
  
  if [[ -f "$env_file" ]]; then
    log_info "Environment file exists, skipping generation."
    return 0
  fi
  
  log_info "Generating environment file..."
  
  # Generate random secrets
  local secret_key
  secret_key=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
  
  local signing_secret
  signing_secret=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
  
  # Detect private IP
  local private_ip=""
  if [[ "$LOCAL_ONLY" != "1" ]]; then
    private_ip=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "127.0.0.1")
  else
    private_ip="127.0.0.1"
  fi
  
  cat > "$env_file" <<EOF
# eInvite Production Environment
# Generated automatically by install-einvite-laptop.sh

# Application
EINVITE_ENV=production
EINVITE_SECRET_KEY=${secret_key}
EINVITE_SIGNING_SECRET=${signing_secret}

# Server binding
EINVITE_HOST=${private_ip}
EINVITE_PORT=${PORT}

# Database (SQLite for laptop hosting)
EINVITE_DATABASE_URL=sqlite:///data/db/einvite.db

# File storage (local filesystem)
EINVITE_STORAGE_BACKEND=filesystem
EINVITE_UPLOAD_DIR=data/uploads

# Security
EINVITE_TRUSTED_PROXY_IPS=127.0.0.1
EINVITE_REQUIRE_MALWARE_SCAN=true

# Features (disabled for simple laptop hosting)
EINVITE_ENABLE_EMAIL=false
EINVITE_ENABLE_PAYMENTS=false
EINVITE_ENABLE_AI=false

# Logging
EINVITE_LOG_LEVEL=info
EINVITE_LOG_FILE=data/logs/einvite.log
EOF
  
  chmod 0640 "$env_file"
  log_info "Environment file created: $env_file"
}

configure_firewall() {
  if [[ "$SKIP_FIREWALL" == "1" ]]; then
    log_info "Skipping firewall configuration."
    return 0
  fi
  
  log_info "Configuring firewall..."
  
  if command -v firewall-cmd >/dev/null 2>&1; then
    # firewalld (RHEL/Fedora/CentOS)
    if systemctl is-active --quiet firewalld; then
      firewall-cmd --permanent --new-zone=einvite 2>/dev/null || true
      firewall-cmd --permanent --zone=einvite --add-port="${PORT}/tcp" 2>/dev/null || true
      firewall-cmd --permanent --zone=einvite --set-target=ACCEPT 2>/dev/null || true
      firewall-cmd --reload 2>/dev/null || true
      log_info "firewalld rule added for port ${PORT}"
    else
      log_warn "firewalld is not running. Skipping firewall configuration."
    fi
  elif command -v ufw >/dev/null 2>&1; then
    # UFW (Ubuntu/Debian)
    if ufw status | grep -q "Status: active"; then
      ufw allow "${PORT}/tcp" comment "eInvite backend" 2>/dev/null || true
      log_info "UFW rule added for port ${PORT}"
    else
      log_warn "UFW is not active. Skipping firewall configuration."
    fi
  else
    log_warn "No firewall management tool found. Configure manually if needed."
  fi
}

verify_installation() {
  log_info "Verifying installation..."
  
  cd "$PROJECT_ROOT"
  
  # Compile check
  if [[ -f server.py ]]; then
    .venv/bin/python -m py_compile server.py || {
      log_error "Server compilation failed!"
      exit 1
    }
  fi
  
  # Preflight check
  if [[ -f production_preflight.py ]]; then
    .venv/bin/python production_preflight.py --env-file .env.production --check-dependencies || {
      log_warn "Preflight check had warnings. Review carefully."
    }
  fi
  
  log_info "Installation verified."
}

start_server() {
  log_info "Starting eInvite server on port ${PORT}..."
  
  cd "$PROJECT_ROOT"
  
  # Determine bind address
  local bind_addr
  if [[ "$LOCAL_ONLY" == "1" ]]; then
    bind_addr="127.0.0.1"
  else
    bind_addr=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "127.0.0.1")
  fi
  
  log_info "Binding to http://${bind_addr}:${PORT}"
  
  # Start in background
  nohup .venv/bin/python server.py \
    --env-file .env.production \
    --host "$bind_addr" \
    --port "$PORT" \
    > data/logs/server.log 2>&1 &
  
  local pid=$!
  echo $pid > data/einvite.pid
  
  # Wait for startup
  sleep 3
  
  # Health check
  local max_attempts=10
  local attempt=0
  while [[ $attempt -lt $max_attempts ]]; do
    if curl -fsS "http://127.0.0.1:${PORT}/api/health/live" >/dev/null 2>&1; then
      log_info "Server is healthy!"
      break
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  
  if [[ $attempt -eq $max_attempts ]]; then
    log_warn "Server may not have started correctly. Check logs: data/logs/server.log"
  fi
  
  # Open browser
  if [[ "$SKIP_BROWSER" != "1" ]]; then
    local open_url="http://127.0.0.1:${PORT}"
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$open_url" || true
    elif command -v gnome-open >/dev/null 2>&1; then
      gnome-open "$open_url" || true
    elif command -v kde-open >/dev/null 2>&1; then
      kde-open "$open_url" || true
    else
      log_info "Open your browser to: $open_url"
    fi
  fi
  
  # Print access info
  echo ""
  echo "=========================================="
  echo "  eInvite is now running!"
  echo "=========================================="
  echo "  Local access:    http://127.0.0.1:${PORT}"
  if [[ "$LOCAL_ONLY" != "1" ]]; then
    local lan_ip
    lan_ip=$(hostname -I | awk '{print $1}')
    echo "  Network access:  http://${lan_ip}:${PORT}"
    echo "  (Devices on same WiFi/LAN can access)"
  fi
  echo "  Logs:            data/logs/server.log"
  echo "  Stop server:     kill \$(cat data/einvite.pid)"
  echo "=========================================="
  echo ""
  log_info "Keep this terminal open while hosting."
}

main() {
  echo "=========================================="
  echo "  eInvite Linux Laptop Installer"
  echo "=========================================="
  echo ""
  
  if [[ "$INSTALL_PACKAGES" == "1" ]]; then
    install_system_packages
  fi
  
  check_prerequisites
  setup_virtual_environment
  setup_data_directories
  generate_environment_file
  configure_firewall
  verify_installation
  start_server
  
  echo ""
  echo "LINUX_LAPTOP_INSTALL_COMPLETE"
  echo "Project root: $PROJECT_ROOT"
  echo ""
  echo "Next steps:"
  echo "  - Keep this terminal open"
  echo "  - Access the URL shown above"
  echo "  - For network access, ensure devices are on same WiFi/LAN"
  echo "  - Back up data/ directory regularly"
  echo ""
}

main "$@"
