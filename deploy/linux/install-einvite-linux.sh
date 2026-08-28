#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ENVIRONMENT_FILE="$PROJECT_ROOT/.env.production"
DOMAIN=""
BACKEND_PORT="8080"
INSTALL_CADDY_SNIPPET=""
NO_START="0"

usage() {
  cat <<'EOF'
Usage: sudo bash deploy/linux/install-einvite-linux.sh --domain invite.example.com [options]

Options:
  --env-file PATH          Production dotenv file (default: PROJECT/.env.production)
  --backend-port PORT      Private loopback port (default: 8080)
  --caddy-snippet PATH     Write a new Caddy site snippet to this exact path
  --no-start               Install and validate without starting services

This installs the Python application as a hardened systemd service. It never
overwrites an existing Caddy file. PostgreSQL, Redis, object storage, ClamAV,
DNS, and Caddy packages must already be available.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="${2:-}"; shift 2 ;;
    --env-file) ENVIRONMENT_FILE="${2:-}"; shift 2 ;;
    --backend-port) BACKEND_PORT="${2:-}"; shift 2 ;;
    --caddy-snippet) INSTALL_CADDY_SNIPPET="${2:-}"; shift 2 ;;
    --no-start) NO_START="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

[[ $EUID -eq 0 ]] || { echo 'Run this installer with sudo/root.' >&2; exit 1; }
[[ "$DOMAIN" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]] || { echo 'Invalid --domain hostname.' >&2; exit 1; }
[[ "$BACKEND_PORT" =~ ^[0-9]+$ ]] && (( BACKEND_PORT >= 1024 && BACKEND_PORT <= 65535 )) || { echo 'Invalid --backend-port.' >&2; exit 1; }
[[ -f "$ENVIRONMENT_FILE" ]] || { echo "Environment file not found: $ENVIRONMENT_FILE" >&2; exit 1; }
[[ "$PROJECT_ROOT" != /home/* && "$PROJECT_ROOT" != /root/* ]] || { echo 'Install the extracted project under /opt/einvite (not a home directory).' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'python3 is required.' >&2; exit 1; }
command -v systemctl >/dev/null || { echo 'systemd is required.' >&2; exit 1; }
command -v clamdscan >/dev/null || { echo 'clamdscan is required and must connect to a running clamd service.' >&2; exit 1; }

id -u einvite >/dev/null 2>&1 || useradd --system --home-dir "$PROJECT_ROOT" --shell /usr/sbin/nologin einvite
python3 -m venv "$PROJECT_ROOT/.venv"
"$PROJECT_ROOT/.venv/bin/python" -m pip install --disable-pip-version-check -r "$PROJECT_ROOT/requirements-production.txt"
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/production_preflight.py" --env-file "$ENVIRONMENT_FILE" --check-dependencies

install -d -o einvite -g einvite -m 0750 "$PROJECT_ROOT/data" "$PROJECT_ROOT/data/logs"
chown -R einvite:einvite "$PROJECT_ROOT/.venv" "$PROJECT_ROOT/data"
chmod 0640 "$ENVIRONMENT_FILE"
chown root:einvite "$ENVIRONMENT_FILE"

SERVICE_TMP="$(mktemp)"
trap 'rm -f "$SERVICE_TMP"' EXIT
sed -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    -e "s|__ENVIRONMENT_FILE__|$ENVIRONMENT_FILE|g" \
    -e "s|__DOMAIN__|$DOMAIN|g" \
    -e "s|PORT=8080|PORT=$BACKEND_PORT|g" \
    -e "s|--port 8080|--port $BACKEND_PORT|g" \
    "$PROJECT_ROOT/deploy/linux/einvite.service.template" > "$SERVICE_TMP"
install -o root -g root -m 0644 "$SERVICE_TMP" /etc/systemd/system/einvite.service

if [[ -n "$INSTALL_CADDY_SNIPPET" ]]; then
  [[ ! -e "$INSTALL_CADDY_SNIPPET" ]] || { echo "Refusing to overwrite existing Caddy file: $INSTALL_CADDY_SNIPPET" >&2; exit 1; }
  CADDY_TMP="$(mktemp)"
  sed -e "s|__DOMAIN__|$DOMAIN|g" -e "s|127.0.0.1:8080|127.0.0.1:$BACKEND_PORT|g" "$PROJECT_ROOT/deploy/linux/Caddyfile.template" > "$CADDY_TMP"
  install -D -o root -g root -m 0644 "$CADDY_TMP" "$INSTALL_CADDY_SNIPPET"
  rm -f "$CADDY_TMP"
  echo "Caddy snippet installed at $INSTALL_CADDY_SNIPPET. Confirm the main Caddyfile imports it before starting Caddy."
fi

systemctl daemon-reload
systemctl enable einvite.service
if [[ "$NO_START" == "0" ]]; then
  systemctl restart einvite.service
fi

echo "LINUX_SERVER_INSTALL_COMPLETE"
echo "Private application health: http://127.0.0.1:$BACKEND_PORT/api/health/ready"
echo "Public target after DNS and Caddy are ready: https://$DOMAIN"
