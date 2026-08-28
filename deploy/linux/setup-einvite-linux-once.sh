#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
MODE="local"
WITH_TESTS="0"
INSTALL_PACKAGES="0"

usage() {
  cat <<'EOF'
Usage: bash deploy/linux/setup-einvite-linux-once.sh [options]

Options:
  --mode local|docker|systemd  Validate prerequisites for the intended host
  --with-tests                Install pinned browser/review dependencies
  --install-system-packages   Install basic packages with apt-get or dnf
  -h, --help                  Show this help

The script creates .venv and installs Python dependencies. Docker Engine,
production databases, object storage, DNS, TLS, and provider credentials are
never installed or invented automatically.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --with-tests) WITH_TESTS="1"; shift ;;
    --install-system-packages) INSTALL_PACKAGES="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

case "$MODE" in local|docker|systemd) ;; *) echo 'Invalid --mode.' >&2; exit 2 ;; esac

install_packages() {
  local packages=(python3 python3-venv python3-pip curl ca-certificates)
  if [[ "$MODE" == "systemd" ]]; then packages+=(clamav-daemon); fi
  if command -v apt-get >/dev/null 2>&1; then
    [[ $EUID -eq 0 ]] || { echo 'Use sudo with --install-system-packages.' >&2; exit 1; }
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    [[ $EUID -eq 0 ]] || { echo 'Use sudo with --install-system-packages.' >&2; exit 1; }
    local dnf_packages=(python3 python3-pip curl ca-certificates)
    if [[ "$MODE" == "systemd" ]]; then dnf_packages+=(clamav clamav-update); fi
    dnf install -y "${dnf_packages[@]}"
  else
    echo 'Automatic package installation supports apt-get and dnf only.' >&2
    exit 1
  fi
}

if [[ "$INSTALL_PACKAGES" == "1" ]]; then install_packages; fi

command -v python3 >/dev/null 2>&1 || { echo 'Missing python3. Install Python 3.10 or newer.' >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10 or newer is required"'
python3 -m venv --help >/dev/null 2>&1 || { echo 'Missing Python venv support (usually python3-venv).' >&2; exit 1; }

if [[ "$MODE" == "docker" ]]; then
  command -v docker >/dev/null 2>&1 || { echo 'Docker Engine is missing. Install it from docs.docker.com for this distribution.' >&2; exit 1; }
  docker compose version >/dev/null || { echo 'Docker Compose v2 is required.' >&2; exit 1; }
fi
if [[ "$MODE" == "systemd" ]]; then
  command -v systemctl >/dev/null 2>&1 || { echo 'systemd is required for native Linux hosting.' >&2; exit 1; }
  command -v clamdscan >/dev/null 2>&1 || { echo 'clamdscan and a running ClamAV daemon are required.' >&2; exit 1; }
fi

cd "$PROJECT_ROOT"
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-production.txt
if [[ "$WITH_TESTS" == "1" ]]; then
  .venv/bin/python -m pip install --disable-pip-version-check -r requirements-test.txt
  .venv/bin/python -m playwright install chromium
fi

install -d -m 0750 "$PROJECT_ROOT/data" "$PROJECT_ROOT/data/logs" "$PROJECT_ROOT/data/uploads"
.venv/bin/python -m py_compile server.py production_preflight.py

cat <<EOF
LINUX_FIRST_TIME_SETUP_COMPLETE mode=$MODE
Project: $PROJECT_ROOT
Next: read FIRST_TIME_INSTALL_AND_HOSTING.md
EOF
