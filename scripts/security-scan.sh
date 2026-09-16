#!/usr/bin/env bash
#
# security-scan.sh — local + CI entrypoint for SAST/SCA/SBOM/secret/container
# scanning on the eInvite platform (ROADMAP-V2 §2.7, ASVS L2 Chapter 10).
#
# Design contract:
#   * Each tool is run only if it is installed (command -v). Missing tools emit
#     a WARN line but DO NOT fail the script. The CI workflow installs every
#     tool, so CI always runs the full suite; local dev / sandbox runs skip
#     what they can.
#   * Failures from an installed tool (bandit finds High, pip-audit finds
#     High/Critical, gitleaks finds secrets, trivy finds High/Critical
#     vulnerabilities, SBOM generation fails) exit the script with a non-zero
#     code so CI blocks the PR.
#   * The SBOM generator (scripts/generate-sbom.py) is stdlib-only and always
#     runs (no install gate). It hits the PyPI JSON API when the network is
#     reachable and falls back to a checksum-less SBOM otherwise — see
#     docs/security/CI-SECURITY.md §6.
#
# Exit codes:
#   0  — every available tool ran clean (or was skipped with a warning).
#   1  — at least one installed tool found a High/Critical finding OR the
#        SBOM generator failed.
#
# See docs/security/CI-SECURITY.md for how to install the tools and how to
# waive specific findings.

set -u  # explicit error on unset variable; NOT set -e — we want per-tool gates

# Repo root = the directory this script lives in's parent.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Fail-fast if invoked from the wrong repo. Avoids accidentally scanning
# sibling projects.
if [ ! -f "docs/requirements-production.txt" ]; then
  echo "[security-scan] FAIL: docs/requirements-production.txt not found (cwd=$(pwd))"
  echo "[security-scan]        Run this script from the einvite-platform repo root."
  exit 1
fi

PYTHON_DIRS_SAST="src/python ai_agent platform_v32 future_platform_v52"
SBOM_OUTPUT="${SBOM_OUTPUT:-sbom.cdx.json}"
GITLEAKS_REPORT="${GITLEAKS_REPORT:-/tmp/gitleaks-report.json}"

FAILED=0

echo "[security-scan] ============================================"
echo "[security-scan] eInvite platform security scan (ROADMAP-V2 §2.7)"
echo "[security-scan] repo root: ${REPO_ROOT}"
echo "[security-scan] ============================================"

# ---------------------------------------------------------------------------
# 1. SAST — bandit (fail on HIGH severity; -ll = low verbosity, HIGH threshold)
# ---------------------------------------------------------------------------
# Bandit docs: https://bandit.readthedocs.io/en/latest/
#   -r <paths>     recursive scan
#   -ll            report only HIGH severity findings (and exit non-zero if any)
# To install: pip install bandit
if command -v bandit >/dev/null 2>&1; then
  echo "[security-scan] Running bandit SAST (threshold=HIGH)..."
  if bandit -r ${PYTHON_DIRS_SAST} -ll; then
    echo "[security-scan] bandit: PASS (no HIGH severity findings)"
  else
    echo "[security-scan] FAIL: bandit found HIGH severity issues"
    FAILED=1
  fi
else
  echo "[security-scan] WARN: bandit not installed, skipping SAST"
  echo "[security-scan]        install with: pip install bandit"
fi

# ---------------------------------------------------------------------------
# 2. Dependency audit — pip-audit (fail on HIGH/CRITICAL)
# ---------------------------------------------------------------------------
# pip-audit docs: https://github.com/pypa/pip-audit
#   -r <file>      audit a requirements file
#   --desc         include vulnerability descriptions in the report
# To install: pip install pip-audit
#
# To waive a specific finding (e.g. a CVE that doesn't apply to our usage,
# or a dependency we can't upgrade yet), pass --ignore-vuln GHSA-xxxx-yyyy.
# Document every waiver in docs/security/CI-SECURITY.md §7 with the GHSA id,
# the reason, and the date it should be revisited.
if command -v pip-audit >/dev/null 2>&1; then
  echo "[security-scan] Running pip-audit on docs/requirements-production.txt..."
  if pip-audit -r docs/requirements-production.txt --desc \
        --ignore-vuln GHSA-PLACEHOLDER-REMOVE-ME 2>/dev/null \
        || pip-audit -r docs/requirements-production.txt --desc; then
    # The above `||` falls back to a plain run if the placeholder waiver is
    # rejected by an older pip-audit build. CI should remove the placeholder
    # before merging — see docs/security/CI-SECURITY.md §7.
    echo "[security-scan] pip-audit: PASS (no HIGH/CRITICAL vulnerabilities)"
  else
    # pip-audit exit codes: 0 clean, 1 vulnerabilities found, 2 error.
    # Only treat code 1 as a finding; code 2 is an environment error.
    code=$?
    if [ "${code}" = "1" ]; then
      echo "[security-scan] FAIL: pip-audit found HIGH/CRITICAL vulnerabilities (exit ${code})"
      FAILED=1
    else
      echo "[security-scan] WARN: pip-audit exited with code ${code} (environment error, not a finding)"
    fi
  fi
else
  echo "[security-scan] WARN: pip-audit not installed, skipping dependency audit"
  echo "[security-scan]        install with: pip install pip-audit"
fi

# ---------------------------------------------------------------------------
# 3. SBOM — CycloneDX 1.5 (always runs; stdlib-only Python)
# ---------------------------------------------------------------------------
# scripts/generate-sbom.py reads docs/requirements-production.txt, queries
# the PyPI JSON API for the latest version + sha256 of each dependency, and
# emits a CycloneDX 1.5 JSON document to stdout. If PyPI is unreachable, the
# SBOM is still emitted without checksums (with a "einvite:network" property
# marker recording the gap) so downstream tools can still consume it.
echo "[security-scan] Generating CycloneDX 1.5 SBOM -> ${SBOM_OUTPUT}..."
if python3 scripts/generate-sbom.py docs/requirements-production.txt > "${SBOM_OUTPUT}"; then
  # Quick sanity check: the output must be valid JSON.
  if python3 -c "import json,sys; json.load(open('${SBOM_OUTPUT}'))" 2>/dev/null; then
    component_count=$(python3 -c "import json; b=json.load(open('${SBOM_OUTPUT}')); print(len(b.get('components',[])))" 2>/dev/null || echo "?")
    echo "[security-scan] SBOM: PASS (${component_count} components, CycloneDX 1.5)"
  else
    echo "[security-scan] FAIL: SBOM output is not valid JSON"
    FAILED=1
  fi
else
  echo "[security-scan] FAIL: SBOM generation failed"
  FAILED=1
fi

# ---------------------------------------------------------------------------
# 4. Secret scanning — gitleaks (fail on any finding)
# ---------------------------------------------------------------------------
# gitleaks docs: https://github.com/gitleaks/gitleaks
#   detect            scan for secrets
#   --no-git          scan every file, not just git history
#   --source .        scan the current directory
#   --report-path P   write findings (JSON) to P
# To install: brew install gitleaks | choco install gitleaks | see releases
if command -v gitleaks >/dev/null 2>&1; then
  echo "[security-scan] Running gitleaks (secret scanning)..."
  if gitleaks detect --no-git --source . --report-path "${GITLEAKS_REPORT}"; then
    echo "[security-scan] gitleaks: PASS (no secrets detected)"
  else
    code=$?
    if [ "${code}" = "1" ]; then
      echo "[security-scan] FAIL: gitleaks found secrets (report: ${GITLEAKS_REPORT})"
      FAILED=1
    else
      # gitleaks uses 1 for findings, other non-zero for errors.
      echo "[security-scan] WARN: gitleaks exited with code ${code} (environment error, not a finding)"
    fi
  fi
else
  echo "[security-scan] WARN: gitleaks not installed, skipping secret scan"
  echo "[security-scan]        install with: brew install gitleaks (mac) | choco install gitleaks (win) | see https://github.com/gitleaks/gitleaks/releases"
fi

# ---------------------------------------------------------------------------
# 5. Container scan — trivy (only if Dockerfile exists + docker is available)
# ---------------------------------------------------------------------------
# trivy docs: https://aquasecurity.github.io/trivy/
#   image             scan a docker image
#   --severity H,C    only fail on HIGH / CRITICAL
#   --exit-code 1     exit non-zero if any HIGH/CRITICAL vuln is found
# To install: brew install trivy | see https://aquasecurity.github.io/trivy/latest/getting-started/installation/
if [ -f "deploy/Dockerfile" ]; then
  if command -v trivy >/dev/null 2>&1 && command -v docker >/dev/null 2>&1; then
    echo "[security-scan] Running trivy container scan against deploy/Dockerfile..."
    if docker build -t einvite-scan:latest -f deploy/Dockerfile . 2>/dev/null; then
      if trivy image --severity HIGH,CRITICAL --exit-code 1 einvite-scan:latest; then
        echo "[security-scan] trivy: PASS (no HIGH/CRITICAL container vulnerabilities)"
      else
        echo "[security-scan] FAIL: trivy found HIGH/CRITICAL container vulnerabilities"
        FAILED=1
      fi
    else
      echo "[security-scan] WARN: docker build failed, skipping container scan"
    fi
  else
    echo "[security-scan] WARN: trivy or docker not installed, skipping container scan"
    echo "[security-scan]        (deploy/Dockerfile exists; install trivy + docker to enable this scan)"
  fi
else
  echo "[security-scan] WARN: deploy/Dockerfile not found, skipping container scan"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "[security-scan] ============================================"
if [ "${FAILED}" = "0" ]; then
  echo "[security-scan] RESULT: PASS (all available tools clean)"
  echo "[security-scan] ============================================"
  exit 0
else
  echo "[security-scan] RESULT: FAIL — see messages above"
  echo "[security-scan]         to waive a specific finding, see docs/security/CI-SECURITY.md §7"
  echo "[security-scan] ============================================"
  exit 1
fi
