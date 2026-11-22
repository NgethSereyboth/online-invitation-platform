# S3 · Static-file and shell parity

Status: **complete 2026-11-14** — 59/59 compared responses byte-identical (after folding the
per-request nonce and each backend's own host:port). Plan reference: §5 S3.

## What the Python server actually does (measured, not assumed)

Every claim below was taken from the running Python backend on a disposable data dir, then
matched in Node:

| Case | Python behaviour |
|---|---|
| Page (`/`, `/checkin`, aliases, `/{name}.html`) | 200, `text/html; charset=utf-8`, `Cache-Control: no-cache` |
| Page body transform | (1) replace `<!--CRITICAL_CSS-->` with `<style data-critical>{critical.css}</style>`; (2) add ` nonce="…"` to every `<style`; (3) insert `<meta name="einvite-backend" content="full"><base href="/">` after `<head>` when absent |
| Static asset hit | 200, `public, max-age=3600, must-revalidate`, `Last-Modified`, `Content-type` from the extension |
| Conditional GET | `If-Modified-Since` at or after mtime → **304**, no body |
| `Range: bytes=0-9` | **ignored** — 200 with the full body (no 206 anywhere) |
| Missing asset | 404 `{"error": "Not found"}` (space after the colon), `no-store` |
| `/i/<unknown>` | 404 **HTML shell**, `no-store`, `X-Robots-Tag: noindex`, placeholders filled with `Invitation` / `You are invited to a special event.` / `social-card-v0.png` |
| Every response | `X-Request-ID` (32 hex), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options`, `COOP`, `CORP`, CSP + report-only + `Report-To` with a fresh nonce |
| `/checkin` only | `Permissions-Policy: camera=(self), …` (QR scanning); every other route denies the camera |

## Implementation

```
services/api-node/lib/pages.mjs    page map, PAGE_ALIASES, the three-step transform, html.escape + urlquote
services/api-node/lib/static.mjs   traversal-safe resolution, MIME table, Last-Modified, 304, no Range
services/api-node/lib/headers.mjs  nonce/request-id, CSP pair, shared security headers, Python-style JSON
services/api-node/app.mjs          route order: /healthz → /api/health → pages → assets → /i/ → JSON 404
```

Two choices worth naming:

- **Pages are matched before files.** A page name must not be shadowed by a mirrored file of
  the same name — Python's dispatcher resolves pages first, so Node does too.
- **`/api/health` keeps Python's shape but not its values.** The flags describe the backend's
  own capabilities (`backend: "node"`, `database: "none"`, `dependencies.pillow: false`). A
  byte-identical copy would be a lie about which runtime answered, so parity here is the
  status, `no-store`, content type and the security headers.

## Verification (all run 2026-11-14)

| Check | Result |
|---|---|
| `python3 tools/static-parity.py` (Python `:8901` vs Node `:8902`) | **59/59 identical, 0 failing** — 16 aliases + `/`, 40 mirrored assets, a missing asset, `/i/no-such-invitation`, and a Range request |
| `npm test` in the service | **5 passed** (healthz contract, JSON 404 body, page transform + nonce match, `/i/` 404 headers, non-GET 404) |
| Container (`docker run` with the mirror mounted at `/web`) | `/checkin` **200** with exactly one `data-critical` block; `/healthz` **200** |
| `build.py all --check` | `BUILD_OK`, no drift (no Python file touched) |

The parity tool folds only what genuinely varies per request: the CSP nonce in headers and
body, `X-Request-ID`/`Date`/`Server`, and the differing `host:port` inside absolute URLs. It
compares the body bytes after those folds, plus content type, content length, cache control,
`X-Robots-Tag`, `Last-Modified` and every security header.

## Known gaps (deliberate, owned by later steps)

1. **Published invitations.** `/i/<slug>` serves Python's *no-row* branch only; real invitation
   documents need the datastore and belong to S9/S7. The router therefore keeps `/i/*` on
   Python — the Node route exists so the 404 contract is proven, not to take traffic.
2. **Social-card format.** Python picks `.png` when Pillow imports and `.svg` otherwise; Node
   pins `png` in the placeholder URL. On a Python host without Pillow the pre-rendered URL
   differs by one extension. Pin this when S9 owns the card pipeline.
3. **No router/compose upstream yet.** The service is reachable on its own port; 0 % traffic
   is still structural rather than a configured weight.
