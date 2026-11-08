#!/usr/bin/env bash
#
# Start the read-only policy proxy used as the DAST origin. ZAP never talks to
# the fixture server directly, so its active scan cannot reach mutation routes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${RUNNER_TEMP:-/tmp}/einvite-dast"
ARTIFACTS="${DAST_ARTIFACTS:-$ROOT/artifacts/dast}"
PYTHON="${PYTHON:-python3}"

if [ -z "${DAST_BACKEND_BASE:-}" ]; then
  if [ -f "$RUN_DIR/fixture.env" ]; then
    # shellcheck disable=SC1090
    . "$RUN_DIR/fixture.env"
  fi
fi
if [ -z "${DAST_BACKEND_BASE:-}" ]; then
  echo "DAST_BACKEND_BASE is not set" >&2
  exit 1
fi

PORT="$("$PYTHON" - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
BASE="http://127.0.0.1:${PORT}"
LOG="$ARTIFACTS/safe-proxy.log"
BLOCKED="$ARTIFACTS/blocked-requests.log"
: > "$LOG"
: > "$BLOCKED"

if command -v setsid >/dev/null 2>&1; then
  setsid "$PYTHON" -u "$ROOT/scripts/dast/safe_proxy.py" \
    --backend "$DAST_BACKEND_BASE" \
    --port "$PORT" \
    --blocked-log "$BLOCKED" \
    >"$LOG" 2>&1 &
else
  "$PYTHON" -u "$ROOT/scripts/dast/safe_proxy.py" \
    --backend "$DAST_BACKEND_BASE" \
    --port "$PORT" \
    --blocked-log "$BLOCKED" \
    >"$LOG" 2>&1 &
fi
PID=$!
printf '%s\n' "$PID" > "$RUN_DIR/proxy.pid"

{
  printf 'DAST_PROXY_BASE=%s\n' "$BASE"
  printf 'DAST_PROXY_PID=%s\n' "$PID"
  printf 'DAST_PROXY_LOG=%s\n' "$LOG"
  printf 'DAST_BLOCKED_LOG=%s\n' "$BLOCKED"
} > "$RUN_DIR/proxy.env"
chmod 600 "$RUN_DIR/proxy.env"

for _ in $(seq 1 30); do
  if curl --silent --show-error --fail --max-time 2 "$BASE/api/health" >/dev/null 2>&1; then
    echo "SAFE_PROXY_READY $BASE"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Policy proxy exited before readiness" >&2
    tail -100 "$LOG" >&2 || true
    exit 1
  fi
  sleep 1
done

echo "Policy proxy did not become ready at $BASE" >&2
tail -100 "$LOG" >&2 || true
kill -TERM -- "-$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null || true
exit 1
