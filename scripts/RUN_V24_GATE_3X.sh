#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
i=1
while [ "$i" -le 3 ]; do
  echo "V24.6.3 release gate run $i of 3"
  python3 release_check.py
  i=$((i + 1))
done
echo "V24.6.3 three-run Linux gate passed."
