#!/usr/bin/env bash
# Close the isolated-branch PRs and delete their remote branches once the
# consolidated integration PR has been reviewed and accepted.
#
# Dry-run by default. Pass --execute to actually close PRs and delete branches.
# This script never touches main/master and never deletes the integration branch.
set -euo pipefail

REMOTE="${REMOTE:-origin}"
BRANCHES=(
  "fix/security-audit-remediation-2026-11"
  "fix/ci-test-reliability"
  "feat/authenticated-dast-pipeline"
  "feat/csp-nonce-hardening"
  "chore/update-template-pack-assets"
  "feat/invitation-pagination-search"
  "chore/playwright-e2e-suite"
)
PRS=(18 19 20 21 22 23 24)
COMMENT="Closed in favor of the consolidated integration PR; the code remains in integration/consolidated-2026-11."

for cmd in git gh; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Required command missing: $cmd" >&2; exit 1; }
done

echo "Remote: $REMOTE"
echo "Close PRs: ${PRS[*]}"
printf 'Delete remote branches:\n'
printf '  %s\n' "${BRANCHES[@]}"

if [[ "${1:-}" != "--execute" ]]; then
  echo
  echo "DRY RUN — no PRs or branches were changed."
  echo "Re-run with: scripts/cleanup-remote-branches.sh --execute"
  exit 0
fi

read -r -p "Type 'yes' to close these PRs and delete these remote branches: " answer
[[ "$answer" == "yes" ]] || { echo "Aborted."; exit 1; }

for pr in "${PRS[@]}"; do
  state="$(gh pr view "$pr" --json state --jq '.state' 2>/dev/null || true)"
  if [[ "$state" == "OPEN" ]]; then
    gh pr close "$pr" --comment "$COMMENT"
  else
    echo "Skipping PR #$pr (state: ${state:-unknown})."
  fi
done

for branch in "${BRANCHES[@]}"; do
  case "$branch" in
    main|master) echo "Refusing to delete protected branch: $branch" >&2; continue ;;
  esac
  if git ls-remote --exit-code --heads "$REMOTE" "$branch" >/dev/null 2>&1; then
    git push "$REMOTE" --delete "$branch"
  else
    echo "Remote branch already absent: $branch"
  fi
done

echo "Cleanup complete. The integration branch and PR are untouched."
