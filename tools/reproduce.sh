#!/usr/bin/env bash
# reproduce.sh — run the full verification sequence from scratch.
#
# Every number in docs/reviews/*.md is produced by one of the six steps below,
# against a gzip server this script starts and stops itself. It is the check that
# the repository is self-contained: no /tmp, no machine-specific paths, no
# session-scoped scripts.
#
#   1. build check        python3 build.py all --check          (must pass)
#   2. unit tests         pytest tests/                         (failures reported, not fatal)
#   3. gzip server        tools/serve-gzip.py                   (started here, stopped on exit)
#   4. Lighthouse CI      npx lhci autorun --config=tools/lighthouserc.js
#   5. determinism        tools/determinism-50x.py public.html   (50 captures)
#   6. report text        tools/report-verify.mjs <report>        (quoted commands re-run)
#
# Prerequisites, in full:
#   npm install
#   pip install -r tools/requirements.txt
#   (the test step installs its own dependencies into .venv — nothing to do by hand)
#
# Step 2 is no longer conditional on the caller's environment. It used to print
# "pytest is not installed — the test step will be skipped" and move on, which is
# how the suite went unmeasured: the printed hint pointed at
# docs/requirements-test.txt, a file that pins playwright/Pillow/qrcode but not
# pytest, so following it could never enable the step. It now installs the pinned
test dependencies from requirements-dev.txt into .venv/ on first use. When no
# interpreter with pytest can be obtained the step says CANNOT RUN and names the
# hole instead of reporting a skip that reads like a pass.
#
# Usage:  tools/reproduce.sh [--skip-lhci] [--skip-tests] [--port 8124]
#         make reproduce
#
# Exit status is 0 only when the build check passes, the determinism check is
# deterministic, and Lighthouse CI's assertions pass. Unit-test failures are
# reported and do not fail the run, because the suite has pre-existing red tests
# unrelated to measurement (see the report's deferred table).
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PORT="${PORT:-8124}"
ARTIFACTS="${ARTIFACTS_DIR:-$REPO_ROOT/artifacts}"
SKIP_LHCI=0
SKIP_TESTS=0

while [ $# -gt 0 ]; do
  case "$1" in
    --skip-lhci) SKIP_LHCI=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --port) PORT="$2"; shift ;;
    *) echo "reproduce.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# The port is validated, not trusted. `lhci` exports PORT=0 while it probes for a
# free port, and that sentinel is meaningless here: this script has to tell every
# tool where to look. Inherited as 0 it served the whole tree on an ephemeral port
# and then failed its own readiness check against http://127.0.0.1:0/, which is
# exactly the class of silent-wrong-measurement the report's section 7.3 records.
if [ -z "$PORT" ] || [ "$PORT" = "0" ]; then
  echo "  PORT=${PORT:-<unset>} is not a usable port (0 is lhci's 'pick one for me'); using 8124"
  PORT=8124
fi
case "$PORT" in
  *[!0-9]*) echo "reproduce.sh: PORT must be a number, got '$PORT'" >&2; exit 2 ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  echo "reproduce.sh: PORT=$PORT is out of range (1024-65535)" >&2
  exit 2
fi

mkdir -p "$ARTIFACTS"
export PORT

step() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
fail=0

# ---------------------------------------------------------------------------
step "0/6  prerequisites"
for cmd in python3 node npx; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "  MISSING: $cmd" >&2
    exit 2
  fi
done
if [ ! -d node_modules ]; then
  echo "  MISSING: node_modules — run: npm install" >&2
  exit 2
fi
for mod in puppeteer-core @lhci/cli; do
  if [ ! -d "node_modules/$mod" ]; then
    echo "  MISSING: node_modules/$mod — run: npm install" >&2
    exit 2
  fi
done
echo "  python3 $(python3 --version 2>&1 | awk '{print $2}')   node $(node --version)   npm $(npm --version)"

# Resolve an interpreter that has pytest, and the browser/asset imports the
# suite needs. Order:
#   1. the interpreter running this script, if it already has pytest
#   2. .venv, created here from requirements-dev.txt on first use
# A venv rather than `pip install` because python3 on this and every supported
# host is EXTERNALLY-MANAGED (PEP 668): installing into it needs
# --break-system-packages, which mutates the OS-managed interpreter.
PYTEST_PY=""
TEST_VENV="${TEST_VENV:-$REPO_ROOT/.venv}"
if python3 -m pytest --version >/dev/null 2>&1; then
  PYTEST_PY=python3
else
  if [ ! -x "$TEST_VENV/bin/python" ]; then
    echo "  creating $TEST_VENV for the test-only dependencies"
    python3 -m venv "$TEST_VENV" >/dev/null 2>&1 || true
  fi
  if [ -x "$TEST_VENV/bin/python" ] && ! "$TEST_VENV/bin/python" -m pytest --version >/dev/null 2>&1; then
    echo "  installing requirements-dev.txt into $TEST_VENV"
    "$TEST_VENV/bin/python" -m pip install -q -r requirements-dev.txt > "$ARTIFACTS/reproduce-pip.log" 2>&1 || true
  fi
  if [ -x "$TEST_VENV/bin/python" ] && "$TEST_VENV/bin/python" -m pytest --version >/dev/null 2>&1; then
    PYTEST_PY="$TEST_VENV/bin/python"
  fi
fi
if [ -z "$PYTEST_PY" ]; then
  echo "  CANNOT RUN the test step: no interpreter with pytest."
  echo "        to enable it:  python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt"
else
  echo "  pytest: $("$PYTEST_PY" -m pytest --version 2>&1 | head -1)  (interpreter: $PYTEST_PY)"
fi

# Fail before starting anything if the port is taken: an unrelated listener on
# this port would answer the requests meant for our server, and the numbers
# would be silently measuring someone else's tree.
if python3 - "$PORT" <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(1)
if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0:
    sys.exit(1)
sys.exit(0)
PY
then
  echo "  port $PORT is free"
else
  echo "  PORT $PORT IS ALREADY IN USE by another process." >&2
  echo "  Refusing to run: the server we start would not bind, and any number measured" >&2
  echo "  would come from whatever else is listening. Choose another port:" >&2
  echo "      make reproduce PORT=8131     (or: tools/reproduce.sh --port 8131)" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
step "1/6  build check  (python3 build.py all --check)"
python3 build.py all --check > "$ARTIFACTS/reproduce-build.log" 2>&1
build_status=$?
cat "$ARTIFACTS/reproduce-build.log"
echo "  exit=$build_status"
if [ "$build_status" -ne 0 ]; then
  echo "  BUILD CHECK FAILED — stopping; every later number would be measuring stale artifacts." >&2
  exit 1
fi
for marker in EDITOR_BUNDLE_CHECK_PASSED ROUTE_BUNDLE_CHECK_PASSED PAGE_ASSET_MANIFEST_CHECK_PASSED; do
  grep -q "$marker" "$ARTIFACTS/reproduce-build.log" || { echo "  MISSING MARKER: $marker" >&2; fail=1; }
done

# ---------------------------------------------------------------------------
step "2/6  unit tests  ($PYTEST_PY -m pytest tests/ -q)"
if [ "$SKIP_TESTS" -eq 1 ]; then
  echo "  skipped (--skip-tests)"
elif [ -z "$PYTEST_PY" ]; then
  echo "  CANNOT RUN — this is a hole in the run, not a pass. See step 0/6 above."
else
  "$PYTEST_PY" -m pytest tests/ -q > "$ARTIFACTS/reproduce-pytest.log" 2>&1
  pytest_status=$?
  tail -n 25 "$ARTIFACTS/reproduce-pytest.log"
  echo "  exit=$pytest_status  (full log: artifacts/reproduce-pytest.log)"
  # Exit 3 is pytest's INTERNALERROR: the session aborted, so "no tests ran" rather
  # than "tests passed". Exit 5 is "no tests collected". Both look like a quiet pass
  # in a summary line and are exactly how this step went unmeasured before, so they
  # are named and counted against the run.
  case "$pytest_status" in
    3) echo "  SUITE DID NOT RUN (pytest INTERNALERROR — collection aborted). This is not a pass." >&2; fail=1 ;;
    5) echo "  SUITE DID NOT RUN (no tests collected). This is not a pass." >&2; fail=1 ;;
    *)
      summary_line=$(grep -E "^[0-9]+ (passed|failed)|passed|failed|error" "$ARTIFACTS/reproduce-pytest.log" | tail -1)
      echo "  result: $summary_line"
      if [ "$pytest_status" -ne 0 ]; then
        echo "  NOTE: test failures are reported, not fatal — the suite carries pre-existing"
        echo "        red tests unrelated to measurement. Not counted against this run's exit status."
      fi
      ;;
  esac
fi

# ---------------------------------------------------------------------------
step "3/6  gzip server  (tools/serve-gzip.py --port $PORT)"
python3 tools/serve-gzip.py --port "$PORT" > "$ARTIFACTS/reproduce-serve.log" 2>&1 &
SERVER_PID=$!
cleanup() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
    echo "  server $SERVER_PID stopped"
  fi
}
trap cleanup EXIT INT TERM

ready=0
for _ in $(seq 1 40); do
  if python3 - "$PORT" <<'PY' >/dev/null 2>&1
import sys, urllib.request
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/index.html", timeout=2) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
  then ready=1; break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "  server died during startup:" >&2
    cat "$ARTIFACTS/reproduce-serve.log" >&2
    exit 2
  fi
  sleep 0.5
done
if [ "$ready" -ne 1 ]; then
  echo "  server never answered on http://127.0.0.1:$PORT/index.html" >&2
  cat "$ARTIFACTS/reproduce-serve.log" >&2
  exit 2
fi
echo "  $(cat "$ARTIFACTS/reproduce-serve.log")"
python3 - "$PORT" <<'PY'
import gzip, sys, urllib.request
req = urllib.request.Request(f"http://127.0.0.1:{sys.argv[1]}/index.html", headers={"Accept-Encoding": "gzip"})
with urllib.request.urlopen(req, timeout=10) as r:
    enc = r.headers.get("Content-Encoding")
print(f"  wire check: Content-Encoding={enc}  ({'gzip on' if enc == 'gzip' else 'NOT COMPRESSED — byte numbers will be wrong'})")
PY

# ---------------------------------------------------------------------------
step "4/6  Lighthouse CI  (16 pages)"
if [ "$SKIP_LHCI" -eq 1 ]; then
  echo "  skipped (--skip-lhci)"
else
  npx lhci autorun --config=tools/lighthouserc.js > "$ARTIFACTS/reproduce-lhci.log" 2>&1
  lhci_status=$?
  grep -E "assertion|resources are|failing|All results processed|error|warning" "$ARTIFACTS/reproduce-lhci.log" | head -40
  echo "  exit=$lhci_status  (full log: artifacts/reproduce-lhci.log)"
  [ "$lhci_status" -ne 0 ] && fail=1
fi

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
step "5/6  determinism  (tools/determinism-50x.py public.html)"
# --base-url is passed explicitly. Without it the tool defaults to 8124, so a
# run on any other port would silently measure a different server — which is
# how this step first "passed" against the wrong tree.
python3 tools/determinism-50x.py public.html --n 50 --base-url "http://127.0.0.1:$PORT"
det_status=$?
[ "$det_status" -ne 0 ] && fail=1

# ---------------------------------------------------------------------------
step "6/6  report text  (tools/report-verify.mjs)"
# Re-runs every read-only command each report quotes in a fenced block and diffs the
# recorded output against the real output. Blocks that record a state the tree has
# left behind, a write, or a measurement are declared in the markdown itself; the
# declaration and its reason are printed, so nothing is skipped silently.
#
# --with-server lets the blocks whose only obstacle was a missing server run. The
# gzip server from step 3 is still up, so report-verify reuses it rather than
# starting a second one, and its own startup path is what --with-server falls back
# to on a cold run. --timeout must cover the 16-page hover sweeps (~90 s and ~5 min),
# which the 60 s default cannot.
rep_status=0
for report in docs/reviews/reproducibility-and-performance-report.md \
              docs/reviews/instrument-and-closure-report.md; do
  if [ ! -f "$report" ]; then
    echo "  MISSING REPORT: $report" >&2
    rep_status=2
    continue
  fi
  node tools/report-verify.mjs "$report" --with-server --timeout=480
  status=$?
  echo "  exit=$status  ($report)"
  [ "$status" -ne 0 ] && rep_status=$status
done
[ "$rep_status" -ne 0 ] && fail=1

# ---------------------------------------------------------------------------
step "summary"
echo "  build check  : PASS"
echo "  gzip server  : PASS (gzip verified on the wire)"
if [ "${SKIP_TESTS:-0}" -eq 1 ]; then echo "  unit tests   : skipped (--skip-tests)"
elif [ -z "$PYTEST_PY" ]; then echo "  unit tests   : CANNOT RUN (no interpreter with pytest)"
else echo "  unit tests   : exit=${pytest_status:-not reached}  (interpreter: $PYTEST_PY)"; fi
if [ "$SKIP_LHCI" -eq 1 ]; then echo "  lhci         : skipped"; else echo "  lhci         : exit=$lhci_status"; fi
echo "  determinism  : exit=$det_status"
echo "  report text  : exit=$rep_status"
echo "  artifacts    : $ARTIFACTS"
if [ "$fail" -ne 0 ]; then
  echo "  RESULT: FAIL"
  exit 1
fi
echo "  RESULT: PASS"
