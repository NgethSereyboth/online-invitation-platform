#!/usr/bin/env bash
# vendor/yjs/download.sh — fetch pinned Y.js + y-indexeddb + lib0 from CDN.
#
# Run this script once per version bump. It downloads the pinned files,
# computes sha384 subresource-integrity hashes, and writes them to
# vendor/yjs/INTEGRITY.txt for inclusion in <script integrity="..."> tags.
#
# See vendor/yjs/README.md for the full vendoring policy.
set -euo pipefail
cd "$(dirname "$0")"

VERSION_YJS=13.6.27
VERSION_YIDB=9.0.12
VERSION_LIB0=0.2.99

SPECS=(
  "y.js                https://unpkg.com/yjs@${VERSION_YJS}/dist/y.js"
  "y.js.map            https://unpkg.com/yjs@${VERSION_YJS}/dist/y.js.map"
  "y-indexeddb.js      https://unpkg.com/y-indexeddb@${VERSION_YIDB}/y-indexeddb.js"
  "y-indexeddb.js.map  https://unpkg.com/y-indexeddb@${VERSION_YIDB}/y-indexeddb.js.map"
  "lib0.js             https://unpkg.com/lib0@${VERSION_LIB0}/dist/lib0.js"
  "lib0.js.map         https://unpkg.com/lib0@${VERSION_LIB0}/dist/lib0.js.map"
)

echo "→ Downloading Y.js vendor files (pinned versions)..."
: > INTEGRITY.txt
for spec in "${SPECS[@]}"; do
  set -- $spec
  name=$1; url=$2
  echo "  $url"
  curl -fsSL "$url" -o "$name"
  if command -v openssl >/dev/null 2>&1; then
    sha384=$(openssl dgst -sha384 -binary "$name" | openssl base64 -A)
    echo "$name sha384-$sha384" | tee -a INTEGRITY.txt
  else
    echo "$name (openssl missing — SRI hash not computed)" | tee -a INTEGRITY.txt
  fi
done

echo
echo "✓ Downloaded. SRI hashes in vendor/yjs/INTEGRITY.txt."
echo "  Add these as integrity=\"sha384-...\" attributes on <script> tags"
echo "  in src/html/editor.html and src/html/dashboard.html."
echo "  Then run: python3 src/python/sync_frontend_assets.py"
