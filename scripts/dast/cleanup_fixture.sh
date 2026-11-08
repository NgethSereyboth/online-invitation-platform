#!/usr/bin/env bash
#
# Stop the DAST fixture server/proxy and delete only the temporary data created
# by this run. Report artifacts are retained for upload.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="${RUNNER_TEMP:-/tmp}/einvite-dast"

stop_pid() {
  local pid_file="$1"
  [ -f "$pid_file" ] || return 0
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  case "$pid" in
    ''|*[!0-9]*) rm -f "$pid_file"; return 0 ;;
  esac

  local cmd=""
  if [ -r "/proc/$pid/cmdline" ]; then
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  fi
  case "$cmd" in
    *"safe_proxy.py"*|*"src/python/server.py"*)
      if kill -0 "$pid" 2>/dev/null; then
        kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
        for _ in $(seq 1 30); do
          kill -0 "$pid" 2>/dev/null || break
          sleep 0.1
        done
        kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
      fi
      ;;
    *)
      echo "Skipping PID $pid from $pid_file: process is not the DAST fixture" >&2
      ;;
  esac
  rm -f "$pid_file"
}

stop_pid "$RUN_DIR/proxy.pid"
stop_pid "$RUN_DIR/server.pid"

if [ -f "$RUN_DIR/fixture.env" ]; then
  DATA_DIR="$(sed -n 's/^DAST_DATA_DIR=//p' "$RUN_DIR/fixture.env" | head -n 1)"
  case "$DATA_DIR" in
    "$RUN_DIR"/data.*) rm -rf -- "$DATA_DIR" ;;
    '') ;;
    *) echo "Skipping unexpected data directory $DATA_DIR" >&2 ;;
  esac
  rm -f "$RUN_DIR/fixture.env"
fi
rm -f "$RUN_DIR/proxy.env"

if [ -n "${RUNNER_TEMP:-}" ]; then
  rm -rf -- "$RUNNER_TEMP/dast-auth"
fi

ZAP_WORK="${ZAP_WORK:-${RUNNER_TEMP:-/tmp}/zap-work}"
if [ -n "$ZAP_WORK" ]; then
  rm -rf -- "$ZAP_WORK"
fi

rmdir "$RUN_DIR" 2>/dev/null || true

echo "DAST_CLEANUP_OK"
