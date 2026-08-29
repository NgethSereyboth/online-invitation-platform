#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
i=1
while [ "$i" -le 3 ]; do
  echo "V26.3.3 release gate run $i of 3"
  "$PYTHON" release_check.py
  i=$((i+1))
done
echo "V26.3.3 three-run Linux gate passed."
