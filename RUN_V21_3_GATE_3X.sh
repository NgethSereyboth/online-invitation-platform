#!/usr/bin/env bash
set -euo pipefail
for i in 1 2 3; do python release_check.py 2>&1 | tee V21_3_RELEASE_LINUX_${i}.log; done
