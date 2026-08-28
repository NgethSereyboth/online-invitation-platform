#!/usr/bin/env bash
set -euo pipefail
for i in 1 2 3; do
  python release_check.py 2>&1 | tee "V21_0_RELEASE_LINUX_FINAL_${i}.txt"
  grep -q "EINVITATION_V21_0_ALL_REQUIRED_REVIEW_CHECKS_PASSED" "V21_0_RELEASE_LINUX_FINAL_${i}.txt"
  grep -q "EINVITATION_V21_0_RELEASE_CHECK_PASSED" "V21_0_RELEASE_LINUX_FINAL_${i}.txt"
done
