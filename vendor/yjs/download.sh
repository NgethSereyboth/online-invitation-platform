#!/usr/bin/env bash
# vendor/yjs/download.sh — fetch pinned Y.js + y-indexeddb + lib0 from CDN.
#
# Run this script once per version bump. It downloads the pinned browser-ready
# ESM bundles, post-processes them so they resolve cleanly against our own
# origin (rewriting the esm.sh CDN import specifiers to /vendor/yjs/... paths),
# computes sha384 subresource-integrity hashes, and writes them to
# vendor/yjs/INTEGRITY.txt for inclusion in <script integrity="..."> tags.
#
# See vendor/yjs/README.md for the full vendoring policy.
#
# Why esm.sh and not unpkg/jsdelivr:
#   Y.js 13.6.x ships ESM-only (no UMD bundle at /dist/y.js). unpkg and jsdelivr
#   serve the raw ESM source which has bare-specifier imports like
#   `import * from 'lib0/array'` — those do NOT resolve in the browser without
#   an importmap and a complete lib0 submodule tree (lib0 has 70+ submodules).
#   esm.sh's `?bundle` parameter produces a self-contained ESM bundle with all
#   transitive deps inlined (lib0 is bundled into y.js). This is the only
#   practical way to self-host Y.js without an npm/bundler toolchain.
set -euo pipefail
cd "$(dirname "$0")"

VERSION_YJS=13.6.27
VERSION_YIDB=9.0.12
VERSION_LIB0=0.2.99

# esm.sh serves browser-ready ESM bundles at /<pkg>@<ver>/es2022/<name>.bundle.mjs
YJS_URL="https://esm.sh/yjs@${VERSION_YJS}/es2022/yjs.bundle.mjs"
YIDB_URL="https://esm.sh/y-indexeddb@${VERSION_YIDB}/es2022/y-indexeddb.bundle.mjs"

echo "→ Downloading Y.js ESM bundles from esm.sh (pinned versions)..."
echo "    Y.js         ${VERSION_YJS}   -> ${YJS_URL}"
echo "    y-indexeddb  ${VERSION_YIDB}  -> ${YIDB_URL}"
echo

# ----------------------------------------------------------------------------
# 1) y.js — Y.js core (esm.sh bundle, lib0 inlined, only external import is
#    /node/process.mjs which we rewrite to our local stub).
# ----------------------------------------------------------------------------
curl -fsSL --max-time 120 --connect-timeout 15 "$YJS_URL" -o y.js.raw
# Rewrite the /node/process.mjs import to point to our local stub.
# (lib0's process.env probes are Node-only; the stub returns an empty object
#  so all accesses yield undefined, which lib0 handles gracefully in browser.)
sed 's|"/node/process.mjs"|"/vendor/yjs/process-stub.js"|g' y.js.raw > y.js
rm y.js.raw

# ----------------------------------------------------------------------------
# 2) y-indexeddb.js — y-indexeddb persistence provider (esm.sh bundle).
#    The bundle imports yjs via /yjs@^13.0.0?target=es2022 — rewrite to our
#    local y.js so the browser fetches from our own origin.
# ----------------------------------------------------------------------------
curl -fsSL --max-time 120 --connect-timeout 15 "$YIDB_URL" -o y-indexeddb.js.raw
sed 's|"/yjs@\^13\.0\.0?target=es2022"|"/vendor/yjs/y.js"|g' y-indexeddb.js.raw > y-indexeddb.js
rm y-indexeddb.js.raw

# ----------------------------------------------------------------------------
# 3) process-stub.js — minimal browser-side stub for the /node/process.mjs
#    import that esm.sh's Y.js bundle references. lib0 only uses process for
#    Node-side detection (env, argv, stdout.isTTY); an empty object makes all
#    those probes return undefined, which lib0 handles gracefully.
#
#    IMPORTANT: the file extension MUST be `.js` (NOT `.mjs`). The server's
#    public_static_path() allowlist (src/python/server.py:3117-3123) only
#    permits nested files under /vendor/ with extensions in
#    {.js,.css,.webmanifest,.png,.jpg,.jpeg,.webp,.gif,.svg,.ico,.woff,
#     .woff2,.ttf,.otf,.wasm,.txt}. `.mjs` is NOT in this list, so the server
#    would return 404 for /vendor/yjs/process-stub.mjs and Y.js would fail
#    to load. The `.js` extension is served with Content-Type: text/javascript
#    which is a valid ES-module MIME type (per HTML spec), so the browser
#    loads it as a module regardless of the extension.
# ----------------------------------------------------------------------------
cat > process-stub.js <<'EOF'
// vendor/yjs/process-stub.js — V54.30 Phase 4b vendored
//
// Minimal browser-side stub for the /node/process.mjs import that esm.sh's
// Y.js bundle references. lib0 (bundled into y.js) only uses process for
// Node-side detection (process.env, process.argv, process.stdout.isTTY,
// process.release.name) — an empty object makes all those probes return
// undefined, which lib0 handles gracefully by falling back to browser
// defaults.
//
// The file extension is `.js` (NOT `.mjs`) so the server's
// public_static_path() allowlist permits serving it (see download.sh
// comment block above for the rationale). ES modules can have any
// extension — the browser uses the response's Content-Type header
// (text/javascript) to determine module vs. classic, not the suffix.
//
// Do NOT add real Node.js polyfills here. If a future Y.js bump genuinely
// requires a polyfill, vendored the polyfill separately and update this stub.
export default {};
EOF

# ----------------------------------------------------------------------------
# 4) lib0.js — lib0 is bundled into y.js (the esm.sh yjs.bundle.mjs inlines
#    all of lib0's submodules). This file exists only so HTML <script> tags
#    that reference /vendor/yjs/lib0.js do NOT 404. It is a no-op marker.
#    Loading y.js is what makes lib0 available — lib0 is never loaded
#    separately by the browser.
# ----------------------------------------------------------------------------
cat > lib0.js <<'EOF'
// vendor/yjs/lib0.js — V54.30 Phase 4b vendored PLACEHOLDER.
//
// lib0 is bundled INTO vendor/yjs/y.js (esm.sh's yjs.bundle.mjs inlines all
// of lib0's submodules). This file exists only so HTML <script> tags that
// reference /vendor/yjs/lib0.js do NOT 404 — it is a no-op marker.
//
// The browser does NOT need to load lib0 separately. Loading y.js is what
// makes lib0's symbols available inside the Y.js module scope.
//
// See vendor/yjs/README.md for the vendoring policy and lib0's individual
// submodule tree (should a future Y.js bump require lib0 to be split out).
EOF

# ----------------------------------------------------------------------------
# 5) Compute sha384 SRI hashes for every vendored file we just produced.
# ----------------------------------------------------------------------------
: > INTEGRITY.txt
echo "# vendor/yjs/INTEGRITY.txt — auto-generated by vendor/yjs/download.sh" >> INTEGRITY.txt
echo "# Source: esm.sh bundles (Y.js ${VERSION_YJS}, y-indexeddb ${VERSION_YIDB}, lib0 ${VERSION_LIB0} bundled)" >> INTEGRITY.txt
echo "# Format: <filename> sha384-<base64>" >> INTEGRITY.txt
echo "" >> INTEGRITY.txt
for f in y.js y-indexeddb.js process-stub.js lib0.js; do
  if command -v openssl >/dev/null 2>&1; then
    sha384=$(openssl dgst -sha384 -binary "$f" | openssl base64 -A)
    echo "$f sha384-$sha384" | tee -a INTEGRITY.txt
  else
    echo "$f (openssl missing — SRI hash not computed)" | tee -a INTEGRITY.txt
  fi
done

echo
echo "✓ Downloaded. SRI hashes in vendor/yjs/INTEGRITY.txt."
echo "  Add these as integrity=\"sha384-...\" attributes on <script> tags"
echo "  in src/html/designer.html and src/html/dashboard.html."
echo "  Then run: python3 src/python/sync_frontend_assets.py"
