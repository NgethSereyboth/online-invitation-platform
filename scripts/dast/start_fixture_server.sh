#!/usr/bin/env bash
#
# Start a disposable eInvite server for the authenticated DAST job.
#
# Safety properties:
#   * binds to 127.0.0.1 only;
#   * uses a fresh temporary EINVITE_DATA_DIR for every run;
#   * never reads a target URL or production credentials;
#   * disables email verification and the optional malware scanner so the
#     fixture can register and log in without external services.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${RUNNER_TEMP:-/tmp}/einvite-dast"
ARTIFACTS="${DAST_ARTIFACTS:-$ROOT/artifacts/dast}"
PYTHON="${PYTHON:-python3}"

mkdir -p "$RUN_DIR" "$ARTIFACTS"
chmod 700 "$RUN_DIR"
DATA_DIR="$(mktemp -d "$RUN_DIR/data.XXXXXX")"
chmod 700 "$DATA_DIR"

PORT="$("$PYTHON" - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
BASE="http://127.0.0.1:${PORT}"
LOG="$ARTIFACTS/fixture-server.log"
: > "$LOG"

if command -v setsid >/dev/null 2>&1; then
  setsid env \
    EINVITE_DATA_DIR="$DATA_DIR" \
    EINVITE_REQUIRE_EMAIL_VERIFICATION=0 \
    EINVITE_ALLOW_NO_SCANNER=1 \
    EINVITE_DEV_AUTH_TOKENS=0 \
    PYTHONPATH="$ROOT/src/python:$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    PYTHONUNBUFFERED=1 \
    "$PYTHON" -u "$ROOT/src/python/server.py" --host 127.0.0.1 --port "$PORT" \
    >"$LOG" 2>&1 &
else
  env \
    EINVITE_DATA_DIR="$DATA_DIR" \
    EINVITE_REQUIRE_EMAIL_VERIFICATION=0 \
    EINVITE_ALLOW_NO_SCANNER=1 \
    EINVITE_DEV_AUTH_TOKENS=0 \
    PYTHONPATH="$ROOT/src/python:$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    PYTHONUNBUFFERED=1 \
    "$PYTHON" -u "$ROOT/src/python/server.py" --host 127.0.0.1 --port "$PORT" \
    >"$LOG" 2>&1 &
fi
PID=$!
printf '%s\n' "$PID" > "$RUN_DIR/server.pid"

{
  printf 'DAST_BACKEND_BASE=%s\n' "$BASE"
  printf 'DAST_DATA_DIR=%s\n' "$DATA_DIR"
  printf 'DAST_SERVER_PID=%s\n' "$PID"
  printf 'DAST_SERVER_LOG=%s\n' "$LOG"
} > "$RUN_DIR/fixture.env"
chmod 600 "$RUN_DIR/fixture.env"

for _ in $(seq 1 60); do
  if curl --silent --show-error --fail --max-time 2 "$BASE/api/health" >/dev/null 2>&1; then
    echo "FIXTURE_READY $BASE"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Fixture server exited before readiness" >&2
    tail -100 "$LOG" >&2 || true
    exit 1
  fi
  sleep 1
done

echo "Fixture server did not become ready at $BASE" >&2
tail -100 "$LOG" >&2 || true
kill -TERM -- "-$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null || true
exit 1
