#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p test-results/v20
for run in 1 2 3; do
  echo "=== V20 Linux gate run ${run}/3 ==="
  python3 release_check.py 2>&1 | tee "test-results/v20/linux-release-gate-${run}.log"
done
