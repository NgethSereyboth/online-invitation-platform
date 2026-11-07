#!/usr/bin/env bash
# Install the tracked Git hooks for this checkout.
# Reversible with: git config --unset core.hooksPath
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [ ! -x .githooks/pre-commit ]; then
  chmod +x .githooks/pre-commit
fi

git config --local core.hooksPath .githooks
echo "Installed Git hooks from .githooks (core.hooksPath=.githooks)."
echo "The pre-commit hook runs gitleaks with .gitleaks.toml."
