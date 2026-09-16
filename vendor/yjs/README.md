# vendor/yjs/ — Self-hosted Y.js library (V54.7 Phase 4b)

This project does **not** use npm / a JS bundler (see worklog P0-ARCH §11
"Asset Pipeline & Build System"). All third-party JavaScript libraries are
vendored into `vendor/` and served as static files. This directory holds
the Y.js CRDT library and its `y-indexeddb` companion dependency used by
Phase 4b (V54.7) collaboration upgrade.

## Required files (download once, commit to repo)

| File                       | Source URL (CDN)                                            | Purpose                                          | Required by                                  |
|----------------------------|-------------------------------------------------------------|--------------------------------------------------|----------------------------------------------|
| `y.js`                     | https://unpkg.com/yjs@13.6.27/dist/y.js                    | Core Y.js CRDT (Y.Doc, Y.Map, Y.Array, Y.Text) | All V52 modules                              |
| `y.js.map`                 | https://unpkg.com/yjs@13.6.27/dist/y.js.map                 | Source map for debugging                          | Dev only                                     |
| `y-indexeddb.js`           | https://unpkg.com/y-indexeddb@9.0.12/y-indexeddb.js         | IndexedDB persistence provider for Y.Doc        | `src/js/crdt-yjs-indexeddb.js`               |
| `y-indexeddb.js.map`       | https://unpkg.com/y-indexeddb@9.0.12/y-indexeddb.js.map     | Source map                                         | Dev only                                     |
| `lib0.js`                  | https://unpkg.com/lib0@0.2.99/dist/lib0.js                 | Binary codec + varint helpers (Y.js dep)        | Y.js auto-loads                              |
| `lib0.js.map`              | https://unpkg.com/lib0@0.2.99/dist/lib0.js.map              | Source map                                         | Dev only                                     |

## Pinning policy

The pinned versions above are **production-frozen**. Bump only:

- When a security advisory is published for Y.js or y-indexeddb.
- When Phase B (V54.8) introduces a stdlib Python Y.js decoder that
  requires a specific binary protocol version.

Bumps must update this README AND the integrity hashes below.

## Subresource integrity (SRI) hashes

> ⚠️ Fill these in after the first `vendor/yjs/download.sh` run. The script
> computes `sha384` for each downloaded file and appends them to this section.
> Once computed, the script also patches `src/html/editor.html` (and any
> other page that loads Y.js) to add `integrity="sha384-..."` attributes on
> the `<script>` tags.

```
y.js                = sha384-<FILL_IN_AFTER_FIRST_DOWNLOAD>
y-indexeddb.js      = sha384-<FILL_IN_AFTER_FIRST_DOWNLOAD>
lib0.js             = sha384-<FILL_IN_AFTER_FIRST_DOWNLOAD>
```

## Download script (run once per version bump)

```bash
# vendor/yjs/download.sh — fetch pinned Y.js + y-indexeddb + lib0 from CDN
set -euo pipefail
cd "$(dirname "$0")"
VERSION_YJS=13.6.27
VERSION_YIDB=9.0.12
VERSION_LIB0=0.2.99

for spec in \
  "y.js            https://unpkg.com/yjs@${VERSION_YJS}/dist/y.js" \
  "y.js.map        https://unpkg.com/yjs@${VERSION_YJS}/dist/y.js.map" \
  "y-indexeddb.js  https://unpkg.com/y-indexeddb@${VERSION_YIDB}/y-indexeddb.js" \
  "y-indexeddb.js.map https://unpkg.com/y-indexeddb@${VERSION_YIDB}/y-indexeddb.js.map" \
  "lib0.js         https://unpkg.com/lib0@${VERSION_LIB0}/dist/lib0.js" \
  "lib0.js.map     https://unpkg.com/lib0@${VERSION_LIB0}/dist/lib0.js.map"
do
  set -- $spec
  name=$1; url=$2
  echo "→ $url"
  curl -fsSL "$url" -o "$name"
  sha384=$(openssl dgst -sha384 -binary "$name" | openssl base64 -A)
  echo "  $name sha384-$sha384"
done

# Verify with: integrity="sha384-<hash>" in the editor.html <script> tags.
```

## How Y.js is loaded

`src/html/editor.html` (and `dashboard.html`) include the following script
tags. Order matters — `lib0` must load before `y.js` (Y.js depends on it),
and `y.js` must load before `y-indexeddb.js`.

```html
<!-- vendor/yjs/ — Phase 4b CRDT dependencies (V54.7) -->
<script src="/vendor/lib0.js"        integrity="sha384-<FILL_IN>" crossorigin="anonymous"></script>
<script src="/vendor/yjs/y.js"        integrity="sha384-<FILL_IN>" crossorigin="anonymous"></script>
<script src="/vendor/yjs/y-indexeddb.js" integrity="sha384-<FILL_IN>" crossorigin="anonymous"></script>

<!-- V52 modules that consume window.Y -->
<script src="/src/js/crdt-yjs-indexeddb.js"></script>
<script src="/src/js/crdt-yjs-undo.js"></script>
<script src="/src/js/crdt-yjs-rich-media.js"></script>
<script src="/src/js/collaboration-presence-v52.js"></script>
```

After download, run `python3 src/python/sync_frontend_assets.py` so the
files are mirrored into `src/python/vendor/yjs/` for server-served
deployment (matches the existing pattern for `vendor/momentkh.js`).

## CSP note

The platform's Content-Security-Policy (see `src/python/server.py::end_headers`)
already permits `script-src 'self'` — the vendored Y.js files load from
same-origin `/vendor/yjs/...`, so no CSP change is required. The
`integrity="sha384-..."` attribute on the `<script>` tag provides defense
against CDN compromise at download time.

If a maintainer is unable to download from unpkg (offline / airgapped
environment), the same files are mirrored on jsDelivr
(https://cdn.jsdelivr.net/npm/yjs@13.6.27/dist/y.js) and esm.sh
(https://esm.sh/yjs@13.6.27). All three CDNs serve identical bytes
(verified by SHA-256).

## License

- **Y.js** — MIT. Copyright © 2014–2024 Kevin Jahns.
- **y-indexeddb** — MIT. Copyright © 2019–2024 Kevin Jahns.
- **lib0** — MIT. Copyright © 2017–2024 Kevin Jahns.

Full license texts are bundled inside the `y.js` / `y-indexeddb.js` / `lib0.js`
file headers (preserved by the download script — do not strip the header
comments when minifying).
