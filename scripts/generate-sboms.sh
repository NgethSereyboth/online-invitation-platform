#!/usr/bin/env bash
#
# generate-sboms.sh — generate the two Sprint 11 SBOMs from the committed locks.
#
# Output (default artifacts/sbom/):
#   python.cdx.json  CycloneDX 1.5 JSON from docs/requirements-production.lock
#   npm.cdx.json     CycloneDX 1.5 JSON from package-lock.json
#
# Prerequisites:
#   python3 -m pip install cyclonedx-bom==8.0.1
#   npm ci
#
# The generated files are build artifacts. They are ignored by git and must
# never be committed to the source tree.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

OUT_DIR="${1:-artifacts/sbom}"
mkdir -p "${OUT_DIR}"

if ! command -v cyclonedx-py >/dev/null 2>&1; then
  echo "ERROR: cyclonedx-py is not installed." >&2
  echo "       python3 -m pip install cyclonedx-bom==8.0.1" >&2
  exit 127
fi

if [ ! -x node_modules/.bin/cyclonedx-npm ]; then
  echo "ERROR: cyclonedx-npm is not installed." >&2
  echo "       npm ci" >&2
  exit 127
fi

echo "Generating Python SBOM (CycloneDX 1.5 JSON)..."
cyclonedx-py requirements docs/requirements-production.lock \
  --output-file "${OUT_DIR}/python.cdx.json" \
  --output-format JSON \
  --spec-version 1.5 \
  --validate

echo "Generating npm SBOM (CycloneDX 1.5 JSON)..."
node_modules/.bin/cyclonedx-npm \
  --package-lock-only \
  --output-file "${OUT_DIR}/npm.cdx.json" \
  --output-format JSON \
  --spec-version 1.5 \
  --validate

python3 - "${OUT_DIR}" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
for name in ("python.cdx.json", "npm.cdx.json"):
    path = out / name
    bom = json.loads(path.read_text(encoding="utf-8"))
    assert bom.get("bomFormat") == "CycloneDX", name
    assert bom.get("specVersion") == "1.5", name
    assert bom.get("components"), name
    print(f"{name}: {len(bom['components'])} components, CycloneDX 1.5")
PY

echo "SBOMs written to ${OUT_DIR}"
