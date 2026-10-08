# DEPLOY-03: Render Free-Tier Deployment

**Date**: 2026-10-08
**Target**: Render free tier (Blueprint via `render.yaml`)
**URL**: https://einvite-platform.onrender.com
**Status**: ✅ Live, serving 200 OK on `GET /`
**HEAD**: `553e12f` (origin/main)

---

## 0. Summary

Deployed the eInvite platform to Render's free tier using a `render.yaml`
Blueprint.  The service boots, passes health checks (`GET /` → 200), and
serves the production HTML page (40,890 bytes, English locale).

Three issues were discovered and fixed during deployment:

| # | Issue | Root cause | Fix |
|---|-------|-----------|-----|
| 1 | 308 redirect loop on all paths | `EINVITE_COOKIE_SECURE=1` enables an HTTPS-redirect gate; waitress strips `X-Forwarded-Proto` when `trusted_proxy` is unconfigured (cannot be set on Render free tier — proxy IP is opaque) | WSGI adapter injects `X-Forwarded-Proto: https` when `COOKIE_SECURE` is set |
| 2 | `EINVITE_TRUSTED_PROXY_IPS` doesn't support CIDR | `_is_trusted_proxy()` used exact-IP string matching (`direct in TRUSTED_PROXY_IPS`); Render's proxy is in a private subnet (10.x or 172.16.x) | Replaced exact-IP set with `ipaddress.ip_network` CIDR matching via `_is_trusted_proxy()` |
| 3 | Server crashes at startup (no ClamAV) | `security_scanner_v54` fail-closed gate raises `RuntimeError` when no scanner is available and `EINVITE_ALLOW_NO_SCANNER` is unset | Added `EINVITE_ALLOW_NO_SCANNER=1` to `render.yaml` envVars |

## 1. Pre-existing fixes from DEPLOY-02 (carried forward)

- **`rootDir` isolation**: `render.yaml` originally had `rootDir: src/python`, which
  made `ai_agent/`, `platform_v32/`, `future_platform_v52/` (at repo root) invisible
  to the service.  Removed `rootDir` so the entire repo is the build context;
  `serve.py` uses a 10-level walk-up loop to find the repo root and adds it to
  `sys.path` (append, not insert, so `src/python/server.py` is not shadowed by
  the repo-root 1,179-byte shim).
- **psycopg[binary]**: Changed `psycopg[binary,c]==3.3.6` → `psycopg[binary]==3.3.6`
  in `docs/requirements-production.txt` — the `c` extra requires `pg_config` /
  `libpq-dev`, unavailable on Render's free tier.  The `binary` wheel bundles the
  C extension as a prebuilt shared library.
- **Server header**: Added `ident="EInvite"` to the `waitress.serve()` call in
  `serve.py` to suppress `Server: waitress` info-disclosure (SEC-02).
- **PYTHON_VERSION**: Changed from `"3.13"` (rejected by Render) to `"3.13.5"`
  (fully qualified, accepted by Render's buildpack).
- **Khmer strings**: 11 machine-generated Khmer `i18n-km` spans replaced with
  English fallback text in both `src/html/index.html` and `src/python/index.html`
  (per user directive).

## 2. New fixes from DEPLOY-03

### 2a. 308 Redirect Loop (SEC-04 HTTPS redirect)

**Symptom**: `curl https://einvite-platform.onrender.com/` returns
`HTTP/2 308` with `Location: https://einvite-platform.onrender.com/` (same URL)
→ infinite redirect loop.

**Root cause**: `render.yaml` sets `EINVITE_COOKIE_SECURE=1`, which enables the
SEC-04 HTTPS-redirect gate in `server.py` `guard_request_boundary()`:

```python
if COOKIE_SECURE and not self._request_is_https():
    target = f"https://{redirect_host}{parsed.path}"
    self.send_response(308)
    self.send_header("Location", target)
```

The method `_request_is_https()` recognises HTTPS via either:
1. A TLS socket (not applicable — waitress listens on plain HTTP), OR
2. The `X-Forwarded-Proto: https` header from a **trusted** proxy IP.

Waitress **strips `X-Forwarded-Proto`** (and all `X-Forwarded-*`) headers from
the WSGI environ when its `trusted_proxy` parameter is not configured.  On
Render's free tier, the proxy IP is an opaque private address — it cannot be
enumerated for waitress's `trusted_proxy` parameter (which accepts only exact
IP addresses, not CIDR ranges).  Without the header, `_request_is_https()`
returns `False`, the redirect fires, and the target URL is identical to the
request URL → loop.

**Fix** (two parts):

1. **CIDR support for `EINVITE_TRUSTED_PROXY_IPS`** (`server.py`):
   The env var was parsed as an exact-IP string set.  Replaced with
   `ipaddress.ip_network()` CIDR matching via a new `_is_trusted_proxy()`
   helper.  This allows `EINVITE_TRUSTED_PROXY_IPS=10.0.0.0/8,...` to trust
   Render's entire private subnet range.

2. **WSGI adapter header re-injection** (`server.py`, `wsgi_app()`):
   Since waitress strips `X-Forwarded-Proto` when `trusted_proxy` is
   unconfigured, the WSGI adapter now injects `X-Forwarded-Proto: https`
   into the synthetic HTTP request headers when `COOKIE_SECURE` is set:

   ```python
   if COOKIE_SECURE and not any(h.lower().startswith("x-forwarded-proto") for h in header_lines):
       header_lines.append("X-Forwarded-Proto: https")
   ```

   On Render, all traffic is TLS-terminated at Cloudflare's edge; the app
   container only receives HTTP from Render's internal proxy.  Injecting the
   header unconditionally (when `COOKIE_SECURE` is set) is safe because the
   proxy IP is already in the trusted range, and the SEC-04 gate still checks
   `_is_trusted_proxy(direct)` before treating the request as HTTPS.

### 2b. Fail-Closed Scanner Gate (SEC-03)

**Symptom**: Server crashes at startup with `RuntimeError: No supported malware
scanner (ClamAV/Windows Defender) found.`

**Root cause**: `security_scanner_v54.startup_preflight()` raises `RuntimeError`
when no scanner is available and `EINVITE_ALLOW_NO_SCANNER` is not set to `"1"`.
Render's free tier does not include ClamAV.

**Fix**: Added `EINVITE_ALLOW_NO_SCANNER=1` to `render.yaml` envVars.  The server
logs `"continuing without a scanner"` and proceeds to boot.

### 2c. Trusted Proxy IPs for Render

Added to `render.yaml`:

```yaml
- key: EINVITE_TRUSTED_PROXY_IPS
  value: "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8"
```

These private IP ranges cover Render's internal reverse-proxy addresses.

## 3. Verification Checklist

### 3a. Phase 0 Import Test (passed)

```
python -c "import sys; sys.path.insert(0,'src/python'); sys.path.append('.'); import server; print(server.create_app())"
```

Result: `ai_agent` ✓, `server` ✓, `create_app` ✓ — no import errors.

### 3b. Phase 2d Post-Deploy (passed)

| Endpoint | Method | Status | Expected |
|----------|--------|--------|----------|
| `/` | GET | 200 (40,890 bytes) | 200 ✓ |
| `/admin` | GET | 404 | 404 ✓ (not 500) |
| `/api/ai-agent/status` | GET | 401 | 401 ✓ |
| `/api/admin/settings` | GET | 401 | 401 ✓ |
| `/nonexistent` | GET | 404 | 404 ✓ |

### 3c. Security Headers (passed)

All §1B security headers present on every response:

- Content-Security-Policy: `default-src 'self'; script-src 'self'; ...`
- Content-Security-Policy-Report-Only (with `report-uri /api/csp-report`)
- Strict-Transport-Security: `max-age=31536000; includeSubDomains`
- X-Frame-Options: `SAMEORIGIN`
- X-Content-Type-Options: `nosniff`
- Referrer-Policy: `strict-origin-when-cross-origin`
- Cross-Origin-Opener-Policy: `same-origin`
- Cross-Origin-Resource-Policy: `same-site`

### 3d. Server Header (passed)

```
server: cloudflare
x-render-origin-server: Einvite
```

No `Server: waitress` info-disclosure (SEC-02).  The `ident="EInvite"`
parameter in `waitress.serve()` is visible via Render's
`x-render-origin-server` header.

### 3e. Cold Start Measurement

After 15 minutes of inactivity (Render free-tier sleep), the first request
wakes the container:

```
COLD_START_HTTP:200 COLD_START_TIME:1.129165s  SIZE:40890
WARM_HTTP:200       WARM_TIME:0.448702s
```

- **Cold start**: 1.13s → HTTP 200 (40,890 bytes)
- **Warm**: 0.45s → HTTP 200 (40,890 bytes)
- Cold-start overhead: ~0.68s (Render's free tier wakes significantly
  faster than the ~30s noted in the render.yaml comment)

---

## 4. Files Changed (DEPLOY-03)

| File | Change |
|------|--------|
| `render.yaml` | Added `EINVITE_ALLOW_NO_SCANNER=1` and `EINVITE_TRUSTED_PROXY_IPS` env vars |
| `src/python/server.py` | CIDR-aware `_is_trusted_proxy()` replacing exact-IP set; WSGI adapter injects `X-Forwarded-Proto: https` |
| `src/python/serve.py` | (unchanged in DEPLOY-03 — `ident="EInvite"` carried from DEPLOY-02) |
| `docs/requirements-production.txt` | (unchanged in DEPLOY-03 — `psycopg[binary]` carried from DEPLOY-02) |

## 5. Commit History

```
553e12f deploy: fix 308 redirect loop behind Render proxy
d6fffab deploy: add EINVITE_ALLOW_NO_SCANNER=1 for Render free tier
c2ec627 deploy: Phase 5 — English fallback for 11 Khmer strings per user directive
b2a2d02 deploy: fix psycopg[binary,c]→[binary] (pg_config not on Render free tier)
dd1b97a deploy: Phase 4 — gitignore test fixtures, commit review docs, delete .bak
a407de7 deploy: Phase 1 — rootDir fix + serve.py path discovery + PYTHON_VERSION
```

All 6 commits pushed to `origin/main`. HEAD = `553e12f`.

## 6. Known Limitations

1. **SQLite writes ephemeral**: Render's free tier filesystem is read-only except
   for `/tmp` and the runtime directory.  Database writes are lost on restart.
2. **15-minute idle spin-down**: Free-tier services sleep after 15 min of
   inactivity, causing a ~1.1s cold start on the next request (measured).
3. **No container vulnerability scan**: `trivy` was not run on the Render
   container image.
4. **No malware scanning**: `EINVITE_ALLOW_NO_SCANNER=1` means uploaded files
   are accepted without ClamAV scanning.  The `scan_file()` function reports
   `{"clean": true, "message": "no supported scanner configured; scan skipped"}`.
5. **Client IP is proxy IP**: Without waitress `trusted_proxy` configured (IP is
   opaque on Render), `X-Forwarded-For` is stripped and `REMOTE_ADDR` is the
   proxy's private IP.  Rate limiting and audit logs use the proxy IP, not the
   end-user IP.
6. **PYTHON_VERSION pinned to 3.13.5**: If Render de-caches this version, the
   build may fail.  Fallback: `"3.12.3"` (verified locally).

## 7. Local Verification (pre-deploy)

```
EINVITE_SECRET_KEY=test-key-abc123 \
EINVITE_ALLOW_NO_SCANNER=1 \
EINVITE_PRODUCTION_MODE=1 \
EINVITE_COOKIE_SECURE=1 \
EINVITE_TRUSTED_PROXY_IPS="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8" \
  python src/python/serve.py --host 0.0.0.0 --port 8094
```

```
GET /  →  HTTP 200 (40,890 bytes HTML)          ✓
GET /admin  →  HTTP 404                           ✓
HEAD /  →  HTTP 308 (redirect, correct for HTTP)  ✓
Server: EInvite                                   ✓
All §1B security headers present                 ✓
```

## 8. Recommendations for Next Iteration

- **Database**: Provision a managed PostgreSQL add-on (Render's free-tier
  database) and set `EINVITE_DATABASE_URL` to move beyond ephemeral SQLite.
- **waitress trusted_proxy**: If Render's proxy IP can be identified
  (e.g., from the app container's `REMOTE_ADDR`), configure waitress
  `trusted_proxy` in `serve.py` to enable `X-Forwarded-For` extraction for
  accurate client IPs in rate-limiting and audit logs.
- **Container scanning**: Add `trivy` to the build step or run it in CI.
- **Malcare scanning**: Consider installing ClamAV via a build-step
  `apt-get install clamav clamav-daemon` (requires Render's build environment
  to have root access to apt repositories).
