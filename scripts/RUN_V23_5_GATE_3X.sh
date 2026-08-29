#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
i=1
while [ "$i" -le 3 ]; do
  echo "Running V23.5.3 release gate $i of 3..."
  python3 release_check.py > "V23_5_RELEASE_LINUX_FINAL_${i}.txt" 2>&1
  i=$((i+1))
done
echo "V23.5.3 passed three Linux release-gate runs."
