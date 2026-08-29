#!/usr/bin/env bash
set -euo pipefail
for i in 1 2 3; do python release_check.py 2>&1 | tee "V20_1_RELEASE_LINUX_FINAL_${i}.txt"; done
