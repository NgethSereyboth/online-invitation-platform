# S2 · Node service skeleton and supply-chain wiring

Status: **complete 2026-11-14** (no route ported, 0 % traffic by construction).
Plan reference: §5 S2. Preconditions used: **D2** (approved minimal package set), **P5** (green
baseline, `…/gates/20261114-192448`).

## What exists

```
services/api-node/
├── package.json          own manifest + own closure (fastify only)
├── package-lock.json     committed, installed with `npm ci --ignore-scripts`
├── app.mjs               buildApp() — /healthz and a JSON 404 fallback
├── server.mjs            listen on PORT/HOST, SIGTERM/SIGINT graceful close
├── test/healthz.test.mjs node:test, no extra dependency
└── Dockerfile            node:22-alpine, prod deps only, non-root, HEALTHCHECK
```

The root `package.json` is untouched: it remains dev tooling (eslint, playwright, axe,
cyclonedx-npm). The service resolves its own tree, so a service dependency can never change
what the lint or bundle pipeline sees.

## The package set (D2)

Pinned now: **`fastify@5.12.8`** and nothing else. Its closure is 47 components, all pinned by
the committed lockfile. `node:test` covers the tests, `node:crypto` will cover Fernet at S5, and
`fetch` is built in — so S2 needs no further package.

The plan asked for every npm version in v3 to be re-resolved rather than copied
(`npm view <pkg> version`, run 2026-11-14 on npm 10.9.9):

| Package | Latest | Note |
|---|---|---|
| fastify | 5.12.8 | **pinned** |
| @fastify/session | 11.1.6 | S6 candidate |
| @simplewebauthn/server | 14.1.0 | passkey work, not scheduled |
| sharp | 0.35.5 | S12 candidate |
| zod | 4.6.7 | S3+ validation |
| drizzle-orm | 0.45.4 | **not planned** — S4 says no ORM codegen |
| typescript | 7.0.2 | v3 doubted this; it resolves |
| argon2 | 0.45.2 | native build; prefer `node:crypto` scrypt |
| ioredis | 6.0.0 | v3 doubted this; it resolves |
| pg | 8.23.1 | D8 says PostgreSQL for the parallel run |
| subset-font | 2.9.0 | S12 candidate |
| fontkit | 3.0.0 | S12 candidate |

Resolving is not approving. Each later step still has to justify its package against D2, and
none of these are installed.

## `/healthz` contract

`GET /healthz` → `200`, `cache-control: no-store`,
`{"status":"ok","service":"einvite-api-node","version":"0.1.0","uptimeSeconds":N}`.
Any other path → `404 {"error":"not_found","path":…}`; non-GET on `/healthz` → 404. The router
forwards only this path during S2.

## Supply-chain wiring

- **`supply-chain.yml`** (`npm-sbom` job, extended rather than duplicated):
  `npm ci --ignore-scripts` in the service directory, a CycloneDX 1.5 SBOM for the service
  lockfile (`artifacts/sbom/npm-service.cdx.json`, generated with the root `cyclonedx-npm`
  binary so the service needs no SBOM tooling), and `npm audit --audit-level=critical` with its
  report (`npm-service-audit.json`). The existing `npm*.json` artifact glob already uploads
  both. `setup-node` now caches off both lockfiles.
- **CodeQL:** the `javascript-typescript` job analyses the whole repo with `build-mode: none`
  and `.github/codeql/codeql-config.yml` has only `paths-ignore` entries for generated bundles,
  so `services/api-node/**` is in scope with no config change. There is no `paths` allow-list
  to extend.
- **`security.yml`:** runs repo-wide bandit/semgrep/gitleaks; `services/` is inside the scan
  root, so the new JavaScript is SAST- and secret-scanned from the first commit.
- **Container:** `services/api-node/Dockerfile` builds a separate image; `deploy/Dockerfile`
  stays the Python backend. The image is not yet referenced by `deploy/docker-compose.*.yml` —
  see the gap below.

## Verification (all run 2026-11-14)

| Check | Result |
|---|---|
| `npm ci --ignore-scripts` in the service dir | 48 packages installed, exit 0 |
| `npm test` (node:test, 3 cases) | **3 passed** — 200 + no-store, JSON 404, non-GET 404 |
| Live process on `127.0.0.1:8091` | `/healthz` **200** with the contract body; `/api/events` **404** |
| `docker build` + `docker run` on `:8092` | image built, container `/healthz` **200** |
| `cyclonedx-npm --validate` for the service lock | **47 components**, first `fastify 5.12.8` |
| `npm audit --audit-level=critical` | **exit 0** |
| `yaml.safe_load` on `supply-chain.yml` | `YAML_OK` |
| Root `package.json` diff | none |

Not run: CodeQL itself (no `codeql` binary on this host — CI covers it), and the GitHub
Actions workflow end-to-end (it runs on push/PR, not locally; the individual commands it
invokes were run above).

## Deliberate gaps carried forward

1. **No compose/router entry.** S2's exit line says "behind the front router at 0 % traffic".
   Rather than point Caddy at a service that has no product routes, the service is reachable
   on its own port and the router has no upstream for it — that *is* 0 % traffic. The entry
   lands with S3, when there is something to route.
2. **Schema-version assertion** (S4) and **session/CSRF interop** (S6) are absent by design.
3. **Migrations stay Python-owned** during the parallel period; the service does not touch the
   DB yet.
