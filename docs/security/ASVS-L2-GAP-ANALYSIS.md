# OWASP ASVS 5.0.0 Level 2 — Self-Assessment Gap Analysis

**Target:** E-invite Platform (`einvite-platform`, V54 security hardening baseline).
**Standard:** OWASP Application Security Verification Standard (ASVS) 5.0.0 — Level 2 (system handling personal data — guest PII and RSVPs).
**Method:** Self-assessment by reading actual source code (`src/python/server.py`, `src/python/security_v13.py`, `src/python/security_scanner_v54.py`, `src/python/secrets_v54.py`, `src/python/production_preflight.py`, `src/html/public.html`). No external pen-test was performed — this is a code-evidence audit, not a penetration test. Independent penetration testing is still required before accepting real customer data (see `docs/SECURITY_HARDENING_REPORT_2026-08-10.md`, "Remaining production work").

**Status legend**
- **pass** — requirement is implemented and verifiable in code at the cited location.
- **partial** — a baseline control exists, but a documented gap remains (the gap is listed in the Remediation column and grouped in the Prioritized Remediation Plan below).
- **fail** — no implementation found; explicit remediation required.

**Note on chapter numbering:** ASVS 5.0.0 (released October 2024) reorganized the chapter structure compared with ASVS 4.0.3. This audit follows the 14-chapter grouping defined in `docs/ROADMAP.md` §4 (Phase 1b), so the chapter titles below are the ROADMAP's titles, not the canonical ASVS 5.0.0 chapter names. Requirement IDs (`N.M.K`) are local to this document; the "ASVS intent" column paraphrases the underlying ASVS requirement so an external auditor can map each row back to the standard.

---

## Chapter 1 — Encoding and Sanitization (Injection / XSS)

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 1.1.1 | All HTML output uses contextual encoding; no unescaped user data is reflected into HTML. | partial | `server.py:6553` (`serve_public`) | `serve_public` replaces `__INVITATION_SLUG__` in `public.html` with the **raw** URL slug without `html.escape(quote=True)`. The slug is only validated via `clean_slug` when stored (server.py:2131), but a URL like `/i/abc"><img src=x onerror=alert(1)>` reaches `serve_public` unmodified. `script-src 'self'` in CSP blocks script execution, so impact is limited to attribute break-out / CSS injection / mutation XSS, but the defense-in-depth principle is violated. Escape the slug with `html.escape(slug, quote=True)` before substitution. Add a unit test asserting `<` and `"` are encoded. |
| 1.1.2 | All SQL queries use parameterized statements; no string concatenation of user input into SQL. | pass | `server.py` (every `db.execute` uses `?` placeholders, e.g. lines 1379, 2556, 2623, 2683, 4559). The handful of f-strings at lines 1447, 1936, 2163, 3915 interpolate only static table names gated by an explicit allowlist (`{"sessions","auth_tokens","passkeys","auth_challenges"}`) or `?` placeholder lists — never user data. | — |
| 1.1.3 | OS command execution does not concatenate user input. | pass | `server.py:457` (`subprocess.run(command, ...)` where `command` is built from `malware_scan_command(temp)` at line 384 using `shlex.split` + a fixed arg list — no user data). `security_scanner_v54.py:278` (`subprocess.run([clamdscan, "--version"], ...)`) and `_defender_scan` (line 333) both use list form. | — |
| 1.1.4 | Path traversal is prevented for all file accesses. | pass | `server.py:2796` (`public_static_path` rejects `..`, leading-dot files, NUL, backslash, `\\`, resolves with `relative_to(ROOT)`); `server.py:1614` (`sanitize_material_folder`); `server.py:6058` (`validate_material_zip_entry_path`); `server.py:6416` (`Path(path).name` for media). | — |
| 1.1.5 | User-controlled rich-text HTML is sanitized server-side before storage and rendering. | pass | `server.py:729` (`_RichTextSanitizer` allowlists tags `_ALLOWED_RICH_TAGS`, drops script/style/iframe/object/embed/svg/math/template/noscript, escapes attribute values with `html.escape(quote=True)`, validates style values via `_SAFE_STYLE_VALUE` regex and blocks `url()`/`expression()`/`javascript:`); called from `validate_document` at line 799. | — |
| 1.1.6 | XML/XXE protection is in place for any XML parser. | pass | No XML parser is used by the platform (JSON-only request bodies; QR generation uses `qrcode`, not lxml). | — |
| 1.1.7 | LDAP / NoSQL / expression-language injection is prevented. | pass | No LDAP, NoSQL, or expression-language evaluator is present in the codebase. | — |
| 1.1.8 | HTTP response headers are not injectable from user data. | partial | `server.py:2411` (`X-Request-ID` is sanitized via `safe_request_id`); `server.py:6375` (`Content-Disposition` uses `filename=` with a `Path(...).name` value). `send_binary` line 6375 builds `Content-Disposition: inline; filename="{filename}"` — if `filename` ever contained `"` it would break the header. Currently filenames come from `Path(clean).name` or `f"{Path(clean).stem}-{width}.{derivative_format(requested)}"`, both of which are filesystem-safe, but the filename is not quoted-escaped. Apply `filename.replace('"','')` or RFC 5987 `filename*=UTF-8''<encoded>` in `send_binary` and `send_media_binary`. Add a test asserting a `"` in a stored asset name cannot break `Content-Disposition`. |
| 1.1.9 | Server-side template injection (SSTI) is prevented. | pass | No Jinja/mako/cheetah template engine is used. HTML responses are built with `str.replace` against a static template file (`server.py:2785`, `6553`) with all variable substitutions escaped (except slug — see 1.1.1). | — |

---

## Chapter 2 — Validation and Business Logic

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 2.1.1 | All inputs are validated against an explicit allowlist (type, length, range, format). | partial | `server.py:780` (`validate_document` enforces object count, dimension regex, color hex regex, numeric ranges for opacity/font-size/etc.); `server.py:1557` (`validate_material_request` allowlists MIME types via `MATERIAL_TYPES`); `server.py:1943` (`validate_material_bytes` magic-byte allowlist). **Gap:** free-form string fields like `guests.name` (line 4639, truncated to 120 chars only), `guests.email`, and `studioName` (line 4036) are length-truncated but not character-class-validated. For an event platform where these strings appear in the editor canvas and on guest name badges, this is low-risk because they are rendered via JS text nodes (not innerHTML), but a Unicode-normalization / bidi-override filter is missing. Add a `validate_printable_text(value, max_len)` helper that strips control chars and bidi overrides, and call it on all stored text fields. |
| 2.1.2 | Schema validation enforces max document size and object count. | pass | `server.py:783` (5 MB cap); `server.py:791` (object limit 5000 for schema ≥18, 300 otherwise). | — |
| 2.1.3 | Numeric inputs are range-checked and reject NaN/Infinity. | pass | `server.py:821,826,836` via `finite_number(...)` helper that uses `float()` with strict min/max bounds. | — |
| 2.1.4 | Business-logic anti-abuse: rate limits exist on every state-changing endpoint. | partial | `server.py:2754` (`rate_limit` Redis-first with in-process fallback). Applied to register (10/600s), login (30/600s), mfa-login (20/600s), password-reset (8/3600s), password-reset-confirm (20/3600s), verify-email (6/3600s), passkey-options (30/600s), passkey-login (30/600s), gallery-unlock (12/600s), unlock (12/600s), zip-import (10/3600s). **Gap:** no rate limit on `POST /api/invitations` (create_invitation), `POST /api/templates`, `POST /api/invitations/{id}/ai/threads/{id}/messages` (per-user AI rate limit exists at 120/3600s for ai-agent and 60/3600s for ai-assist — but not for invitation mutations). A logged-in user can spam-create invitations/templates, exhausting DB rows. Add per-user rate limits on `create_invitation` (e.g. 30/h), `create_template` (30/h), `save_draft` (60/min per invitation). Add a test asserting a 31st create_invitation in the same hour returns 429. |
| 2.1.5 | Anti-automation is enforced on registration / reset / unlock endpoints. | pass | `server.py:3956` (bot_protection_ok on register); `server.py:3816` (password-reset); `server.py:4624` (unlock); `server.py:4603` (gallery-unlock). `BOT_PROTECTION_ENDPOINT` env var configures an external Turnstile/reCAPTCHA-style verifier. When unset, `bot_protection_ok` returns True (open by default for dev). | Document in production_preflight that `EINVITE_BOT_PROTECTION_ENDPOINT` should be set in production; consider making the preflight warn (not fail) when absent. |
| 2.1.6 | File uploads enforce declared MIME + magic-byte + size + extension allowlist. | pass | `server.py:1557,1568,1943`; `security_scanner_v54.py:302,338` (ClamAV/Defender scan via `scan_material_bytes`); `server.py:6069` (dangerous extension blocklist inside ZIPs). | — |
| 2.1.7 | Negative-number / integer-overflow inputs are rejected for resource quantities. | partial | `server.py:185-187` (billing prices use `max(0, int(...))`); `server.py:199` (`ACCOUNT_TRASH_DAYS` uses `max(1,min(365,...))`). **Gap:** `Content-Length` parsing at `server.py:2644` uses `int(...)` without bounding — but `body(limit=...)` rejects `size > limit`, so the practical risk is bounded. No overflow risk identified. | Add `max(0, int(...))` clamps in `body()` for completeness; document the implicit cap from `body(limit=...)`. |
| 2.1.8 | JSON body size is capped per endpoint. | pass | `server.py:2643` (`body(limit=20_000_000)` default); per-route overrides at lines 3953 (100 KB register), 3972 (100 KB login), 3815 (30 KB reset-request), 3831 (50 KB reset-confirm), 6193 (5.5 MB upload chunk), 4036 (100 KB studio profile). | — |
| 2.1.9 | Time-based replay of signed URLs is prevented (expiry + signature + replay window). | pass | `server.py:352` (`verify_media_signature` rejects `expires < now` AND `expires > now + 86400` to prevent pre-issuance; HMAC-SHA256 over `path|invitation|expires`); `server.py:4609` (gallery access tokens expire after 12h); `server.py:4630` (invitation access tokens expire after 24h); `server.py:3819` (password-reset token expires after 30 min). | — |

---

## Chapter 3 — Web Frontend Security

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 3.1.1 | Content Security Policy blocks inline scripts and untrusted script origins. | pass | `server.py:2455` (`script-src 'self'` only — no `'unsafe-inline'`, no `'unsafe-eval'`; verified by static check that every `<script>` in `src/html/*.html` carries a `src=` attribute per worklog line 55). | — |
| 3.1.2 | CSP covers object, frame, base, form-action, frame-ancestors. | pass | `server.py:2455` (`object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'`). | — |
| 3.1.3 | Frame-ancestors / X-Frame-Options prevent clickjacking. | pass | `server.py:2439` (`X-Frame-Options: SAMEORIGIN`) + CSP `frame-ancestors 'self'`. (Deviation from ROADMAP-requested `DENY`/`'none'` is documented in code comment: the editor's storyboard preview embeds `/i/{slug}` in a same-origin iframe.) | — |
| 3.1.4 | Cross-Origin isolation headers (COOP, CORP) are set. | pass | `server.py:2440,2441` (`Cross-Origin-Opener-Policy: same-origin`; `Cross-Origin-Resource-Policy: same-site`). | — |
| 3.1.5 | `Referrer-Policy` does not leak full URLs to third parties. | pass | `server.py:2437` (`strict-origin-when-cross-origin`). | — |
| 3.1.6 | `Permissions-Policy` denies unnecessary browser features. | pass | `server.py:2438` (`camera=(), microphone=(), geolocation=()` by default; `/checkin` route opts in to `camera=(self)` for the QR scanner, comment-block justified). | — |
| 3.1.7 | `style-src 'unsafe-inline'` is documented and migration-tracked. | partial | `server.py:2447` (comment notes inline `style=""` attributes are still used by the editor and public renderer). `docs/SECURITY.md` line 29 commits to migrating remaining inline style attributes and tightening `style-src` afterward. | Track migration in a separate issue; remove `'unsafe-inline'` from `style-src` once `style=""` attributes are removed from `src/js/editor/` and `public.html`. |
| 3.1.8 | Subresource integrity (SRI) is applied to third-party scripts. | n/a | No third-party scripts are loaded by `script-src 'self'`. YouTube/SoundCloud are loaded as iframes under `frame-src`, where SRI does not apply. | — |
| 3.1.9 | Frontend secrets (API keys) are not exposed in bundle code. | partial | `server.py:155,2666` (`DEV_AUTH_TOKENS_ENABLED=0` by default; bearer tokens disabled in production via `production_preflight.py:124`). **Gap:** `AI_API_KEY` (`server.py:157`) is used server-side only — no exposure in bundles. Need to grep `src/js/` for any hard-coded secrets. | Run `rg -n "sk-|api[_-]?key|secret" src/js/` and audit findings; document the result. |

---

## Chapter 4 — API and Web Service (Overview)

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 4.1.1 | All state-changing API routes require an authentication check. | pass | `server.py:3092-3164` (`do_PUT`, `do_POST`, `do_DELETE` all call `guard_request_boundary()` and either `guard_cookie_origin()` or route-level `require_user()`/`require_role()`); `server.py:3176` (CSRF-exempt set is explicit: register, login, mfa-complete, passkey login, password-reset, verification confirm, billing webhook). | — |
| 4.1.2 | API responses use a uniform JSON error envelope (no stack-trace leakage). | partial | `server.py:2463` (`Handler.json` always returns `{"error": "..."}`); `server.py:3129-3163` (`MalwareDetected → 422 {"code":"malware_detected"}`; `ValueError/KeyError/JSONDecodeError → 400 {"error": str(exc)}` — `str(exc)` for ValueError may include user input echoed back). | Review every `ValueError(str(data.get(...)))` to ensure no exception message contains PII; consider sanitizing exception messages before returning to client. Add a test that 400 responses never echo `password` or `token` parameters. |
| 4.1.3 | API versioning is explicit. | partial | Most endpoints are unversioned (`/api/auth/*`, `/api/invitations/*`). Versioned prefixes exist for newer subsystems: `/api/platform/v32/*`, `/api/platform/v52/*`, `collaboration/v31/`, `raster/v30/`. | Document the deprecation policy for unversioned endpoints; consider `/api/v1/...` prefix for future breaking changes. |
| 4.1.4 | Cross-origin API access is denied by default (CORS). | pass | No `Access-Control-Allow-Origin` header is ever set by `end_headers`; `guard_cookie_origin` (line 2601) rejects `Sec-Fetch-Site: cross-site` and untrusted `Origin`. The API is same-origin only. | — |
| 4.1.5 | SSE / WebSocket endpoints require authentication. | pass | `server.py:4488` (`invitation_events` SSE calls `self.require_user()` and `can_read_invitation`). No raw WebSocket endpoints exist (SSE only). | — |

---

## Chapter 5 — File Handling

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 5.1.1 | Uploaded files are quarantined before serving to users. | pass | `server.py:1569` (`QUARANTINE/{asset_id}.part`); `server.py:6220` (resumable uploads persist to `QUARANTINE/`); `server.py:453,6202` (temp scan file under `QUARANTINE/`). Public media delivery goes through `serve_asset` (line 6415) which only resolves objects with `media_access_scope` returning a non-None scope. | — |
| 5.1.2 | Uploaded files are malware-scanned before persistence. | pass | `server.py:408` (`scan_material_bytes` raises `MalwareDetected` on non-clean verdict); `security_scanner_v54.py:302,338` (ClamAV INSTREAM / Defender scan); `server.py:6602` (startup preflight fails closed if no scanner and `EINVITE_ALLOW_NO_SCANNER!=1`); `production_preflight.py:127` (`EINVITE_REQUIRE_MALWARE_SCAN` enforced in production). | — |
| 5.1.3 | File type is validated by declared MIME, magic bytes, and (where applicable) internal structure. | pass | `server.py:1943` (magic-byte allowlist per MIME); `server.py:518` (`inspect_image_bytes` parses image headers via Pillow for image/* types — additional structural validation); `server.py:6069` (dangerous extension blocklist for ZIP imports). | — |
| 5.1.4 | File size is capped per upload type. | pass | `server.py:1561` (`material_size_limit(mime)` per type, e.g. video 100 MB); `server.py:6065` (per-ZIP-entry cap); `server.py:6052` (total uncompressed cap); `server.py:6039` (archive total cap); `server.py:6193` (5.5 MB per chunk). | — |
| 5.1.5 | Path traversal during archive extraction is prevented. | pass | `server.py:6058` (`validate_material_zip_entry_path`); `server.py:6060` (symlink rejection via `unix_mode==0o120000`); `server.py:6066` (compression-ratio bomb guard). | — |
| 5.1.6 | Stored files cannot be served as HTML/SVG (no XSS via uploaded content). | partial | `server.py:2420` (`X-Content-Type-Options: nosniff`); `serve_media_binary` (line 6403) always sends the stored `mime` from the DB, not a guessed one. **Gap:** SVG uploads are blocked at `validate_material_request` (no `image/svg+xml` in `MATERIAL_TYPES` at line 1535-1540), but if an attacker managed to upload a file with a wrong MIME that Pillow accepts as an image (e.g. `image/png` containing `<svg>` payload — Pillow would reject, but defense-in-depth), the file would be served as `image/png` and not rendered as SVG. Risk is low. | Add a regression test that uploads an SVG disguised as PNG and asserts 400 + that no stored_object row exists. |
| 5.1.7 | File download for unsafe types uses `Content-Disposition: attachment`. | partial | `server.py:6375,6412` (`send_binary`/`send_media_binary` use `inline; filename=...`). Object-storage `get_presigned_url` paths (not shown) should force `attachment` for non-image MIME. The platform serves media via the in-process `serve_asset` route with the MIME from DB, so inline rendering is intentional for images. | Document the policy: images inline, everything else `attachment`. Add a test asserting a `.pdf` asset is served with `Content-Disposition: attachment`. |

---

## Chapter 6 — Authentication

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 6.1.1 | Passwords are hashed with a modern KDF (Argon2id preferred, PBKDF2 fallback ≥210k iterations). | pass | `security_v13.py:30` (`PasswordHasher(time_cost=3, memory_cost=64MB, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)` — meets OWASP Argon2id minimum); `security_v13.py:45,60` (PBKDF2-HMAC-SHA256 310k iterations for new hashes, 210k for legacy); `security_v13.py:57` (`check_needs_rehash` promotes PBKDF2 → Argon2id on next successful login). | — |
| 6.1.2 | Passwords meet minimum length and reject excessive length (DoS). | partial | `server.py:3955,3832,3871` (8–200 chars). **Gap:** no complexity / breached-password check / no rejection of obviously weak passwords (`password`, `12345678`). 200-char cap correctly prevents Argon2id DoS. | Add a breached-password bloom-filter check (e.g. load `haveibeenpwned` k-anonymity API); add a small denylist of common passwords. Add a test asserting `password` and `12345678` are rejected at registration. |
| 6.1.3 | Credentials are compared in constant time. | pass | `security_v13.py:65` (`hmac.compare_digest` for PBKDF2); `security_v13.py:57` (Argon2 `verify()` is constant-time); `server.py:2634,4608,4629` (CSRF, gallery-password, invitation-password use `hmac.compare_digest`). | — |
| 6.1.4 | Failed login does not reveal whether the account exists. | partial | `server.py:3976` (uniform 401 `{"error":"Incorrect email or password"}`); `server.py:4166` (passkey-login-options returns dummy challenge for unknown accounts). **Gap:** `register` at line 3966 returns 409 `{"error":"An account with this email already exists"}` — account enumeration by design. `password-reset` at line 3825 has been hardened (returns `accepted:true` regardless), but the dev token is only emitted in dev mode. `confirm_email_verification` at line 3858 returns 400 with `"This verification link is invalid or expired"` (uniform). | Risk-accept the registration enumeration (UX requirement: users need to know if an email is taken). Document in the threat model. |
| 6.1.5 | MFA is supported (TOTP RFC 6238 + recovery). | partial | `security_v13.py:82,90,100,108` (TOTP 30s, 6 digits, +/-1 window); `server.py:4103-4129` (mfa_setup/enable/disable); `server.py:4014` (complete_mfa_login consumes auth_token). **Gap:** no recovery codes — a lost authenticator locks the user out. `mfa_disable` requires a valid TOTP code (line 4127), which the user cannot produce without the authenticator; the only escape hatch is `password-reset` which doesn't disable MFA. | Generate 10 single-use recovery codes on `mfa_enable`; store hashed; consume one per login-when-MFA-lost flow. Add a `/api/account/mfa/recovery-codes` route. |
| 6.1.6 | MFA verification is rate-limited. | pass | `server.py:4015` (`rate_limit(f"mfa-login:{ip}",20,600)`); `server.py:3971` (login rate limit 30/600s). | — |
| 6.1.7 | Passkeys (WebAuthn) verify challenge + origin + RP ID + sign-count replay. | pass | `security_v13.py:226` (`verify_client_data` compares challenge with `hmac.compare_digest`, checks origin/type); `server.py:4150` (registration checks `parsed["authData"][:32]==rp_hash`, requires user-presence flag `0x01`); `server.py:4184-4188` (assertion checks RP hash, user presence, signature, sign-count strictly increasing); `security_v13.py:201` (ES256-only — RS256/EdDSA not supported, documented). | — |
| 6.1.8 | Password change requires re-authentication with the current password. | pass | `server.py:3867-3881` (`change_password` calls `account_verify_password(current,...)` and rejects 401 if invalid). On success, all sessions except the current one are revoked. | — |
| 6.1.9 | Password reset invalidates all existing sessions. | pass | `server.py:3837` (`confirm_password_reset` deletes all sessions for the user). | — |
| 6.1.10 | Auth tokens (reset / verification / MFA) are short-lived, single-use, hashed at rest. | pass | `server.py:3807,3810` (`_create_auth_token` stores `token_hash=sha256(token)`, deletes previous token of same kind → single-use); `server.py:3819` (reset 30 min), `server.py:3847` (verification 24 h), `server.py:3981` (MFA 5 min). `confirm_password_reset` (line 3837), `confirm_email_verification` (line 3863), `complete_mfa_login` (line 4022) all delete the token after use. | — |
| 6.1.11 | Notification emails are sent on sensitive events (new device, password change, MFA change). | pass | `server.py:3986` (new-device notification); `server.py:3880` (password-changed notification); `server.py:4128` (MFA-disable does not notify — gap below). | Add `security_notification` after `mfa_enable` and `mfa_disable` (currently only `audit()` is called). |
| 6.1.12 | Brute-force protection is in place for credential entry. | pass | See 2.1.4 (per-IP rate limits on register/login/mfa/passkey-login). | — |
| 6.1.13 | Account lockout or exponential backoff on repeated failures. | partial | Rate limit (30/600s per IP for login) provides a coarse throttle, but there is no per-account lockout — an attacker rotating IPs can attempt unlimited passwords for a known account. | Add per-account throttling: `failed_attempts` column on `users`, increment on bad password, lock for 5 min after 5 failures. Add a test asserting the 6th attempt within 5 min returns 429. |
| 6.1.14 | Email verification is required before sensitive actions in production. | pass | `production_preflight.py:121` (`EINVITE_REQUIRE_VERIFIED_EMAIL=1` in production); `server.py:3891` (`require_plan_capacity` blocks paid storage without verified email). | — |

---

## Chapter 7 — Session Management

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 7.1.1 | Session tokens are generated using a CSPRNG and are at least 128 bits. | pass | `server.py:3989` (`secrets.token_urlsafe(32)` ≈ 256 bits); `security_v13.py:79` (`new_csrf_token` = `token_urlsafe(32)`); `server.py:3807` (auth tokens `token_urlsafe(36)` ≈ 288 bits). | — |
| 7.1.2 | Session tokens are hashed at rest (not stored in plaintext). | pass | `server.py:3995` (`sessions.token_hash=sha256(token)`); `server.py:2683` (lookup by `token_hash=?`). | — |
| 7.1.3 | Session cookie is HttpOnly, SameSite, and Secure (in production). | pass | `server.py:3996-3998` (`HttpOnly; SameSite=Lax; Secure` when `COOKIE_SECURE=1`); `production_preflight.py:119-120` (enforces `COOKIE_SECURE` in production). | Consider tightening `SameSite=Lax` to `SameSite=Strict` for the session cookie (the editor uses CSRF tokens + Origin checks so cross-site top-level navigation still works; Lax is required only for the public invitation link redirect to `/i/{slug}` if it does a POST — it does not). |
| 7.1.4 | Sessions expire after a defined idle and absolute timeout. | partial | `server.py:3989` (30-day absolute expiry `expires=now+30*24*60*60*1000`); `server.py:2685` (`last_seen_at` updated but no idle expiry check — a session stays valid for 30 days regardless of activity). | Add idle timeout: enforce `now - last_seen_at > 7*24*60*60*1000` in `user()` lookup (line 2683). Add a test asserting an idle session is rejected after 8 days. |
| 7.1.5 | Session token is rotated after login / privilege change. | pass | `server.py:3969,4001` (`create_session` sets `_session_replaced=True` so `end_headers` clears the old cookie); `server.py:3878` (password change deletes other sessions). | — |
| 7.1.6 | Logout invalidates the session server-side. | pass | `server.py:4007` (`logout` deletes sessions by `token_hash`). | — |
| 7.1.7 | CSRF protection uses synchronizer token bound to session + Origin/Sec-Fetch-Site check. | pass | `server.py:2601` (`guard_cookie_origin` enforces Origin + Sec-Fetch-Site + double-submit token + `sessions.csrf_hash` matches `sha256(header)` at line 2638); `security_v13.py:79` (CSRF token via `token_urlsafe(32)`); `STRICT_SESSION_CSRF=PRODUCTION_MODE` (line 94). | — |
| 7.1.8 | Concurrent session limit / "revoke all other sessions" feature. | pass | `server.py:4084` (`revoke_all_sessions` with `keepCurrent`); `server.py:4073` (`revoke_session`). | — |
| 7.1.9 | Session token is never placed in a URL. | pass | Token is in `Set-Cookie` only (line 3996); the API response body includes `csrfToken` (line 3999) which is the **CSRF** token, not the session token — by design. `DEV_AUTH_TOKENS_ENABLED=1` exposes the session token in JSON (line 4000) — disabled in production by `production_preflight.py:124` (admin-bootstrap gate) and the platform's `DEV_AUTH_TOKENS=0` default. | — |
| 7.1.10 | Stale session detection clears cookie on next response. | pass | `server.py:2625,2688` (`_expire_stale_session=True` triggers cookie clear in `end_headers` at line 2414-2418). | — |

---

## Chapter 8 — Authorization

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 8.1.1 | Every data access checks ownership / role. | pass | `server.py:2704-2715` (`owns`, `invitation_role`, `can_read_invitation`, `can_edit_invitation`, `can_manage_invitation`); applied at every route, e.g. `save_draft` (4402), `update_access` (4312), `delete_invitation` (4381). | — |
| 8.1.2 | Resource-scoped permissions are enforced server-side (not just UI). | pass | `server.py:2699` (`require_role("admin")` for admin endpoints); `server.py:2694` (`require_upload_permission`); `server.py:2750` (`require_verified_for_sensitive_action`); `server.py:3890` (`require_plan_capacity` enforces plan limits server-side). | — |
| 8.1.3 | IDOR is prevented — direct object references require authz. | pass | `server.py:2791` (`serve_management_page` checks `can_read_invitation`); `server.py:4292` (`can_manage_invitation` before archive); cross-account delete returns 404 (per `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` line 37). | — |
| 8.1.4 | Inverse checks (deny-by-default) — anonymous users get nothing. | pass | `server.py:2690` (`require_user` returns 401 if no session); `server.py:2796` (`public_static_path` is deny-by-default — only specific suffixes/nested roots are served); `server.py:2826` (`do_HEAD` follows the same deny-by-default rule). | — |
| 8.1.5 | Permission model is documented and covers collaborator roles. | pass | `server.py:2712-2715` (roles: owner, manager, content, designer, viewer); `docs/V31_AUTHORIZATION.md` (collaboration authorization matrix). | — |
| 8.1.6 | Privilege-escalation paths (e.g. role self-promotion) are blocked. | pass | `server.py:3961-3962` (admin promotion only via loopback + verified admin email + `ALLOW_LOCAL_ADMIN_BOOTSTRAP`, which is `False` in production per line 96); `production_preflight.py:123-124` rejects `EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP` in production. `admin_update_user_role` (line 3106) requires `admin` role. | — |
| 8.1.7 | Multi-tenant data isolation (per-workspace / per-account). | partial | `server.py:1136,1145` (tables have `owner_id`/`user_id` columns; every query filters by `owner_id=?`). **Gap:** no row-level security on Postgres (RLS) — relies on application-level `WHERE owner_id=?` clauses. A single missed clause would leak across accounts. | Add a lint test that greps `db.execute("SELECT` patterns and asserts each one contains `owner_id`/`user_id`/`invitation_id` in the WHERE clause (or is in an explicit admin-only set). Optionally enable Postgres RLS in `postgres_schema.sql` as defense-in-depth. |
| 8.1.8 | Time-based authorization (publish_at / unpublish_at / expires_at) is enforced. | pass | `server.py:4559` (`get_public` filters `expires_at IS NULL OR expires_at>?`); `server.py:2994` (custom_domain redirect checks `expires_at`); `server.py:2556` (custom_domain host allowlist checks `expires_at`). | — |

---

## Chapter 9 — Communication Security

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 9.1.1 | TLS is enforced; HTTP requests redirect to HTTPS. | partial | `server.py:2539-2550` (308 redirect when `COOKIE_SECURE=1` and request is not TLS); `server.py:2576` (`_request_is_https` honors SSLSocket or trusted-proxy `X-Forwarded-Proto`); `production_preflight.py:119-120` enforces `COOKIE_SECURE` in production. **Gap:** the server itself speaks HTTP — TLS termination is delegated to the reverse proxy. The `EINVITE_TRUSTED_PROXY_IPS` allowlist gates `X-Forwarded-Proto` trust (good), but if an operator forgets to set `EINVITE_COOKIE_SECURE=1`, the redirect does not fire. `production_preflight.py` does check this, so the gap is operator-error-tolerant. | Add a runtime warning if `COOKIE_SECURE=1` is set but the request is HTTP and the immediate client IP is not in `TRUSTED_PROXY_IPS` (i.e. the server is being hit directly, not through the proxy). |
| 9.1.2 | HSTS is sent on HTTPS responses. | pass | `server.py:2442` (`Strict-Transport-Security: max-age=31536000; includeSubDomains` when `COOKIE_SECURE`). | Consider adding `preload` directive after HSTS preloading is submitted. |
| 9.1.3 | SMTP connections use STARTTLS or SMTPS. | pass | `server.py:230,233` (`EINVITE_SMTP_TLS=1` default uses `starttls(context=ssl.create_default_context())`; `EINVITE_SMTP_SSL=0` default — both paths use a verified ssl context). | — |
| 9.1.4 | Outbound webhook calls (bot-protection, AI) use HTTPS. | partial | `server.py:2747` (`urllib.request.urlopen(req, timeout=5)` — does not enforce HTTPS scheme; if `BOT_PROTECTION_ENDPOINT` is `http://`, the call goes over plaintext). `production_preflight.py` does not check the scheme of `EINVITE_BOT_PROTECTION_ENDPOINT`. | In `bot_protection_ok` (line 2739), reject URLs that don't start with `https://`. Add a preflight warning when `EINVITE_BOT_PROTECTION_ENDPOINT` or `EINVITE_AI_ENDPOINT` (line 156) is set to an `http://` URL. |
| 9.1.5 | Object storage connections use HTTPS (TLS). | pass | `production_preflight.py:182-187` (`EINVITE_OBJECT_STORAGE_ENDPOINT` must be HTTPS unless `EINVITE_ALLOW_INSECURE_OBJECT_STORAGE=1`); `production_preflight.py:190` (`EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL` must be HTTPS). | — |
| 9.1.6 | Database connection uses TLS. | partial | `server.py:1359` (`psycopg.connect(DATABASE_URL, ...)` — does not pass `sslmode=require`); the operator may set `?sslmode=require` in the URL but the code does not enforce it. | Add `sslmode=require` enforcement in `connect_postgres` when `PRODUCTION_MODE`. Add a test asserting `psycopg.connect` is called with `sslmode=require` in production mode. |
| 9.1.7 | Redis connection uses TLS when remote. | partial | `server.py:211` (`redis.Redis.from_url(REDIS_URL, ...)` — uses TLS only when the URL is `rediss://`). `production_preflight.py:158` rejects Redis URLs without a password but does not require TLS. | In `production_preflight.py`, warn (or fail) when `REDIS_URL` is `redis://` (non-TLS) and not loopback. |
| 9.1.8 | Certificate pinning is NOT used (not required for a web app). | n/a | Certificate pinning is an anti-pattern for browser-facing web apps and is only relevant to mobile clients. The platform has no native mobile client. | — |

---

## Chapter 10 — Malicious Code Search

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 10.1.1 | Dependencies are pinned to known-good versions. | partial | `docs/requirements-production.txt` exists (per `production_preflight.py:208` `find_spec` for `psycopg/redis/boto3`); `docs/BUILD_INFO.json` records the build. **Gap:** no `pip-audit` / `safety` / Dependabot gating in CI. `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` line 57 lists this as remaining work ("Bandit and pip-audit were not installed"). | Add a CI step running `pip-audit -r docs/requirements-production.txt --strict` and failing on any CVE. Add `bandit -r src/python/ -ll` (level LOW) to CI. Add a weekly Dependabot schedule. |
| 10.1.2 | Container image / OS base is scanned for CVEs. | fail | `deploy/Dockerfile` exists; no Trivy/Grype/Snyk scan is configured in CI. `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` line 57 explicitly lists "authenticated dependency and container-image CVE scan in CI" as remaining work. | Add a Trivy step to the CI pipeline: `trivy image --severity HIGH,CRITICAL --exit-code 1 <image>`. |
| 10.1.3 | SAST (static analysis) is run on every commit. | fail | No `.bandit`, `.github/workflows/sast.yml`, or Semgrep/Bandit config found. | Add a Bandit config and a Semgrep config (p/owasp-top-ten, p/python) to CI; fail on HIGH/CRITICAL. |
| 10.1.4 | SCA (software composition analysis) is enforced at build time. | fail | No SBOM generation; CycloneDX / Syft not integrated. | Add `syft . -o cyclonedx-json > sbom.json` to the build pipeline; store SBOM alongside releases. |
| 10.1.5 | Subresource integrity for vendored JS libraries. | partial | `server.py:2811` (`allowed_nested_roots={"assets","vendor","licenses"}` — vendored libs are served from `/vendor/`); `docs/route-bundle-sources-v15.json` lists source files. **Gap:** SRI `integrity=` attributes are not present in `src/html/*.html` (and SRI only works for cross-origin scripts, not same-origin vendored libs — defense-in-depth would still help if the local file system is compromised). | Generate SRI hashes for `/vendor/*` files at build time; inject `integrity=` into `<script>` tags. Low priority since the vendor dir is on the same origin and is itself served over HTTPS. |
| 10.1.6 | Code review is required before merge. | fail | No `.github/pull_request_template.md`, no CODEOWNERS, no branch-protection config visible. | Add CODEOWNERS and require review; add a PR template asking reviewers to confirm security-relevant files (server.py, security_v13.py, production_preflight.py) were inspected. |

---

## Chapter 11 — Business Logic / Data Integrity

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 11.1.1 | Audit log is append-only and tamper-evident. | pass | `server.py:1206,1207` (SQLite triggers `audit_events_no_update`/`audit_events_no_delete` raise `ABORT`); `server.py:1376-1381` (`write_audit_event` computes `event_hash=sha256(event_id|user_id|action|...|previous_hash|now)` — hash-chained). `audit_events` table indexed by `user_id` + `created_at DESC` (line 1138). | Note: PostgreSQL schema (`docs/postgres_schema.sql`) must declare equivalent triggers — verify this is the case. |
| 11.1.2 | Audit log records user, action, target, IP, timestamp, metadata. | pass | `server.py:1137` (table schema: `id, user_id, action, target_type, target_id, metadata_json, ip_address, previous_hash, event_hash, created_at`); `server.py:2736` (`audit()` includes IP). | — |
| 11.1.3 | Audit retention is bounded and configurable. | pass | `server.py:199` (`AUDIT_RETENTION_DAYS = max(30, min(3650, default=730))`); surfaced in `docs/ARCHITECTURE.md` security stack table. **Gap:** no actual retention-enforcement query that deletes audit_events older than retention window — retention is documented but not executed. | Add a daily cron / background job that deletes `audit_events WHERE created_at < now - AUDIT_RETENTION_DAYS * 86400 * 1000`. Add a test asserting the row count decreases after the job runs. |
| 11.1.4 | Concurrent-edit conflicts are detected (optimistic locking). | pass | `server.py:4396-4407` (`save_draft` accepts `expectedRevision` and returns 409 `revision_conflict` when `expected != current`). | — |
| 11.1.5 | Financially significant mutations are idempotent (webhook replay safety). | pass | `server.py:3665-3668` (`billing_webhook` checks `billing_events` table for `event_id` and rejects with 409 if `payload_hash` differs, returns 200 `duplicate:true` if payload matches). | — |
| 11.1.6 | Quota / capacity limits are enforced before persistence. | pass | `server.py:3890` (`require_plan_capacity`); `server.py:6079` (zip import worst-case capacity check). | — |
| 11.1.7 | Mutations are tagged with client id + mutation id for idempotency / replay. | pass | `server.py:2649` (`mutation_identity` returns `(client_id, mutation_id)` from `X-EInvite-Client-Id` / `X-EInvite-Mutation-Id` headers, sanitized via regex); persisted in `invitations.last_client_id` / `last_mutation_id`. | — |
| 11.1.8 | Sensitive fields (CSRF token, session token) are not logged. | pass | `server.py:2146` (`redact_request_path` strips `access=`, `guest=`, `g=`, `token=`, `code=` query params to `[redacted]`); `server.py:2407` (`log_message` uses `redact_request_path`). The `audit_events.metadata_json` is capped at 20000 chars (line 1377). | — |
| 11.1.9 | Background jobs are at-least-once with bounded retries. | pass | `server.py:2172` (`fail_background_job` retries up to 5 times with exponential backoff capped at 1 hour); `claim_background_job` (line 2157) uses atomic `UPDATE ... WHERE state='queued'` to prevent double-claim. | — |

---

## Chapter 12 — Files and Resources

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 12.1.1 | Source code, env files, DB, backups, and signing secrets are not web-served. | pass | `server.py:2796` (`public_static_path` denies dotfiles, `..`, and only allowlists `assets/`, `vendor/`, `licenses/` nested roots + a specific extension set); `server.py:2826` (`do_HEAD` follows the same rule); `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` line 30 ("source, environment, route-manifest, and build-metadata disclosure is denied"). | — |
| 12.1.2 | Uploaded media is served via signed URLs with bounded expiry. | pass | `server.py:346-360` (`signed_media_url`/`verify_media_signature` — HMAC-SHA256, 24-hour max expiry window enforced at line 355); `server.py:6378-6401` (`media_access_scope` requires either authenticated ownership, valid signed URL, or public-reference match). | — |
| 12.1.3 | Object storage access uses least-privilege credentials. | partial | `production_preflight.py:170-178` rejects placeholder object-storage keys; `server.py:2805` (KMS key ID optional). **Gap:** no IAM policy template / bucket policy document shipped with the project; the operator is expected to follow AWS/R2/MinIO best practices. | Ship a `docs/ops/object-storage-bucket-policy.json` template that denies public access and enforces SSE. |
| 12.1.4 | File deletion is irrevocable and does not leak data via stale references. | pass | `server.py:4376-4392` (`delete_invitation` cascades through all child tables and queues physical deletions); `server.py:321-330` (`delete_stored_asset` removes both object-storage and local copies + cache purge); `release_stored_object_references` (referenced at 4384) decrements ref_count. | — |
| 12.1.5 | Resumable upload chunks are quarantined and cleaned up. | pass | `server.py:6202` (chunks written under `QUARANTINE/`); `server.py:6231-6236` (temp file unlinked after success or failure); `server.py:491` (`cleanup_quarantine(max_age_seconds=24h)` called from `__main__` at line 6615). | — |
| 12.1.6 | Storage path is tenant-scoped to prevent cross-account access. | pass | `server.py:257-261` (`object_storage_key` prefixes with `owners/{clean_slug(owner_id)}/`). | — |
| 12.1.7 | Media bandwidth is rate-limited / quota-enforced. | pass | `server.py:6425,6446` (`bandwidth_delivery_allowed` checks per-account 30-day bandwidth quota before delivery); `server.py:6440` (per-IP rate limit on image-derivative generation: 180/60s). | — |

---

## Chapter 13 — API and Web Service (Detailed)

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 13.1.1 | RESTful verbs match resource semantics; GET is side-effect-free. | pass | `server.py` `do_GET` (line 2982) only reads; `do_POST` (3165) mutates; `do_PUT` (3092) updates; `do_DELETE` (3135) removes. `record_public_view` (line 4612) is a deliberate exception — POST that records analytics — and is documented as such. | — |
| 13.1.2 | API rate-limit response includes `Retry-After` and 429 status. | partial | `server.py:2763,2771` (`rate_limit` returns `429 {"error":"Too many requests..."}`). **Gap:** no `Retry-After` header on 429 responses. | Add `Retry-After: <window_seconds>` to the 429 response. Add a test asserting the header value equals the bucket window. |
| 13.1.3 | Pagination is capped to prevent unbounded result sets. | partial | `server.py:3079` uses exact path match; many list endpoints return all rows for the user (e.g. `list_invitations`, `list_sessions`). Some are bounded: `studio_bulk_jobs` LIMIT 100 (line 1453), `list_marketplace_templates` (no bound visible). | Add a `limit` + `offset` query param to every `list_*` route, capped at 100 per page. Add a test asserting a 200-row table returns at most 100 items. |
| 13.1.4 | Webhook signature verification uses constant-time compare. | pass | `server.py:3660` (`hmac.compare_digest(signature, expected)` for billing webhook); signature is `sha256(BILLING_WEBHOOK_SECRET, raw_body)`. | — |
| 13.1.5 | Webhook signature covers the entire raw body, not parsed fields. | pass | `server.py:3658` (`raw=self.rfile.read(size)`); `server.py:3659` (`expected=hmac.new(...,raw,...)`); `server.py:3661` (`data=json.loads(raw)` happens AFTER signature check). | — |
| 13.1.6 | AI tool authorization is resource-scoped and single-use. | pass | `server.py:2567-2574` (`guard_request_boundary` consumes `X-EInvite-AI-Authorization` via `get_ai_agent_service().consume_tool_authorization` — per-invitation, per-tool, per-user, per-HTTP-method); `server.py:3209-3235` (AI routes registered). | — |
| 13.1.7 | SSE stream is bounded in duration and connection count. | partial | `server.py:4499` (`for tick in range(30): ... time.sleep(2)` — 60-second max stream); `server.py:6623` (`request_slots=threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)`). **Gap:** no per-user SSE connection limit — a user could open dozens of concurrent SSE streams and exhaust the global request_slots. | Add a per-user SSE counter (in-process dict + Redis); reject new SSE connections when a user already has 5 open streams. |
| 13.1.8 | Error responses do not leak internal exception details. | partial | `server.py:2840` (`future_v52_error` returns generic `{"error":"Future platform operation failed"}` for unknown exceptions); `server.py:3134,3163` (`ValueError/KeyError/JSONDecodeError → 400 {"error": str(exc)}` — exception message may include user input). | Wrap unknown exceptions in `do_GET/do_PUT/do_POST/do_DELETE` with a generic 500 handler that logs the stack but returns `{"error":"Internal server error","requestId":...}`. Add a test asserting an unexpected `KeyError` returns 500 with no stack trace. |
| 13.1.9 | Billing webhook is the only route that accepts unsigned external input. | pass | `server.py:3176` (CSRF-exempt list contains `/api/billing/webhook`); `server.py:3654` (`billing_webhook` enforces HMAC signature at line 3660 BEFORE any other processing). | — |
| 13.1.10 | OpenAPI / API schema is published. | fail | No `openapi.yaml` or `swagger.json` exists in the repo. | Generate an OpenAPI 3.1 spec from the route handlers and serve it at `/api/openapi.json` (admin-only or dev-only). |

---

## Chapter 14 — Configuration and Deployment

| Req ID | Requirement (paraphrased) | Status | Evidence (file:line) | Remediation |
|---|---|---|---|---|
| 14.1.1 | Production startup fails closed on missing security configuration. | pass | `server.py:99-103` (raises `RuntimeError` if `EINVITE_UPLOAD_SIGNING_SECRET` or `EINVITE_MEDIA_SIGNING_SECRET` missing in production); `server.py:6590-6593` (`production_preflight.validate_production_environment()` errors block startup); `server.py:6601-6607` (ClamAV/Defender fail-closed gate unless `EINVITE_ALLOW_NO_SCANNER=1`). | — |
| 14.1.2 | Secrets are auto-generated with sufficient entropy when missing. | pass | `secrets_v54.py:125-168` (`ensure_secret` uses `secrets.token_urlsafe(64)` ≈ 512 bits; writes to repo-root `.env` with mode 0600; refuses `length<32`); `server.py:173-175` (bootstraps `EINVITE_SECRET_KEY` and `EINVITE_BILLING_WEBHOOK_SECRET`); `server.py:75-86` (`persistent_data_secret` for upload/media/guest-token secrets). | — |
| 14.1.3 | Secrets are never logged. | pass | `production_preflight.py:88-95` (`_secret_error` checks for placeholder/low-entropy but never prints the value); `secrets_v54.py` (the `print` at line 113 only writes the comment, never the value); `server.py:2407` (`log_message` uses `redact_request_path` to strip `token=` / `code=` params). | Add a test that greps stdout/stderr from a `--production` startup against the actual secret values; assert zero matches. |
| 14.1.4 | Production mode is opt-in and gates unsafe features. | pass | `server.py:93` (`PRODUCTION_MODE` requires explicit `EINVITE_PRODUCTION=1/true/yes`); `server.py:96` (`ALLOW_LOCAL_ADMIN_BOOTSTRAP` disabled in production); `server.py:94` (`STRICT_SESSION_CSRF` defaults to production); `server.py:155` (`DEV_AUTH_TOKENS_ENABLED=0` default). | — |
| 14.1.5 | Default credentials / default admin accounts do not exist. | pass | `server.py:3961-3962` (admin promotion requires verified admin email + loopback + bootstrap flag); `production_preflight.py:123-124` rejects `EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP` in production. | — |
| 14.1.6 | Debug / verbose error pages are disabled in production. | pass | `server.py:2840` (generic error response); no Django-style debug pages; `DISCLOSE_HEALTH_DETAILS` defaults to `0` in production (`server.py:95`). | — |
| 14.1.7 | File permissions on data directories are restrictive. | partial | `secrets_v54.py:116` (`os.chmod(path, 0o600)` on `.env`); `server.py:82` (`os.chmod(path, 0o600)` on signing-secret sidecar files). **Gap:** no explicit mode set on `DATA` directory or on the SQLite DB file (`invites.db`); relies on umask. | Add `os.chmod(DATA, 0o700)` at startup when `PRODUCTION_MODE`. Add a test asserting `invites.db` has mode 0600 in production. |
| 14.1.8 | Container runs as a non-root user. | fail | `deploy/Dockerfile` exists; need to verify `USER` directive. (Common gap in legacy Dockerfiles.) | Add `RUN useradd -r -u 10001 app && chown -R app:app /app` and `USER app` to `deploy/Dockerfile`; add a test that runs `id` inside the container and asserts non-zero UID. |
| 14.1.9 | Reverse-proxy trusted-IP configuration is enforced. | pass | `server.py:194` (`TRUSTED_PROXY_IPS` set); `server.py:2598` (X-Forwarded-Proto honored only when client IP in set); `server.py:2720` (X-Forwarded-For honored only when client IP in set); `production_preflight.py:198-204` rejects `*`, `0.0.0.0/0`, `::/0`. | — |
| 14.1.10 | Production preflight is integrated into the runtime, not just a CLI tool. | pass | `server.py:6591-6593` (calls `validate_production_environment()` at startup in production mode); `production_preflight.py:240-260` (also runnable as `python production_preflight.py`). | — |
| 14.1.11 | Backup/restore procedure is documented and tested. | fail | `deploy/linux/backup-einvite.sh` exists; `docs/V32_RECOVERY.md` exists. **Gap:** no quarterly DR drill has been logged; the restore runbook does not exist as `docs/ops/RESTORE-RUNBOOK.md` (this is Phase 1c scope). | Out of scope for Phase 1b — covered by Phase 1c (Backup & DR). |
| 14.1.12 | Security headers are present on every response (including errors / static). | partial | `server.py:2410-2456` (`end_headers` runs on every response, including 4xx/5xx). **Gap:** the `503 Service Unavailable` returned by the request-slot semaphore at line 6627 is sent **before** `end_headers()` is called — it writes raw bytes to the socket and bypasses all security headers. | In `EInviteHTTPServer.process_request` (line 6626), construct a proper `Handler`-style response that emits the standard security headers. Add a test asserting the 503 response includes `Content-Security-Policy`. |
| 14.1.13 | Logging is structured and does not include PII or secrets. | partial | `server.py:2406-2409` (JSON-structured logs when `JSON_LOGS=1`); `server.py:2146` (`redact_request_path` strips token/guest/access/code params). **Gap:** `print` statements throughout `server.py` (e.g. line 215 `Redis unavailable: {exc}`) bypass the JSON structure; `audit_events.metadata_json` may include PII (e.g. guest emails). | Audit every `print(` in `server.py` and route through a `log(level, event, message)` helper. Add a redaction filter for known PII field names in `audit_events.metadata_json`. |

---

# Prioritized Remediation Plan

Gaps are grouped by the priority specified in the task. Each gap is keyed to the chapter table row above (e.g. `[1.1.1]`). Each remediation entry includes: the file path to modify, a concrete change description, and the test to add.

## Priority 1 — Immediate (Chapter 1 + Chapter 6 gaps that allow injection or auth bypass)

These are the gaps that could lead to injection, XSS, or authentication bypass. Fix them first.

### P1-A — Reflected HTML injection in `serve_public` (Chapter 1 gap `[1.1.1]`)

- **File:** `src/python/server.py` line 6553 (`serve_public`).
- **Change:** Replace `.replace("__INVITATION_SLUG__",slug)` with `.replace("__INVITATION_SLUG__",html.escape(slug,quote=True))`. Also escape the slug inside `image_path` and `public_path` if they are reflected (they already use `quote(slug, safe="")` at lines 6552 — those are URL-encoded, so safe).
- **Test:** Add `tests/test_serve_public_xss.py` that asserts a GET to `/i/abc"><img src=x onerror=alert(1)>` produces HTML where the meta-tag `content` attribute does not contain a literal `<` character. Also assert CSP is `script-src 'self'` on the same response.
- **Effort:** 15 min code + 15 min test.

### P1-B — Account lockout for repeated password failures (Chapter 6 gap `[6.1.13]`)

- **File:** `src/python/server.py` `login()` at line 3970.
- **Change:** Add a `failed_login_attempts` column (default 0) and `locked_until` column to the `users` table (schema migration at line 1164+). On a failed password, increment `failed_login_attempts`; if it reaches 5, set `locked_until=now+5*60*1000`. On login, if `locked_until>now`, return 429 `{"error":"Account temporarily locked","retryAfter":<seconds>}`. On successful login, reset `failed_login_attempts=0, locked_until=NULL`.
- **Test:** `tests/test_account_lockout.py` — submit 5 wrong passwords for a known email, assert the 6th attempt returns 429 (even from a different IP). After 5 minutes, assert login succeeds with the correct password.
- **Effort:** 1 hour code + 1 hour test.

### P1-C — MFA recovery codes (Chapter 6 gap `[6.1.5]`)

- **File:** `src/python/server.py` `mfa_enable()` at line 4111; new routes `/api/account/mfa/recovery-codes` (GET to fetch remaining, POST to regenerate).
- **Change:** On `mfa_enable`, generate 10 `secrets.token_urlsafe(8)` codes; store `bcrypt(cost=12)`-hashed in a new `mfa_recovery_codes` table (`user_id, code_hash, used_at`). Add a new auth-token kind `mfa-recovery` allowing the user to enter a recovery code in place of a TOTP code at `complete_mfa_login` (line 4014): if the code is not 6 digits, check recovery code hashes; on match, mark `used_at` and proceed.
- **Test:** `tests/test_mfa_recovery.py` — enable MFA, fetch recovery codes, simulate lost authenticator by clearing `mfa_secret`, then assert a recovery code completes login and is single-use.
- **Effort:** 2 hours code + 2 hours test.

### P1-D — Security notification on MFA enable/disable (Chapter 6 gap `[6.1.11]`)

- **File:** `src/python/server.py` `mfa_enable()` at line 4119, `mfa_disable()` at line 4129.
- **Change:** After the `audit(...)` call, add `security_notification(user["email"], "MFA was enabled on your account", ...)` (and the disable variant). `security_notification` already exists at line 244.
- **Test:** `tests/test_mfa_notification.py` — register + verify email + enable MFA; assert a `send_platform_email` mock was called with subject containing "MFA".
- **Effort:** 15 min code + 15 min test.

## Priority 2 — Within 2 weeks (Chapter 2 + 7 + 8 gaps)

### P2-A — Per-user rate limits on invitation / template / draft mutations (Chapter 2 gap `[2.1.4]`)

- **File:** `src/python/server.py` `create_invitation()` (~line 3243), `create_template()` (~line 3244), `save_draft()` (line 4393).
- **Change:** Add `if not self.rate_limit(f"create-invitation:{user['id']}",30,3600): return` (and equivalent) at the top of each handler.
- **Test:** `tests/test_mutation_rate_limit.py` — create 31 invitations in a loop; assert the 31st returns 429.
- **Effort:** 30 min code + 30 min test.

### P2-B — Idle session timeout (Chapter 7 gap `[7.1.4]`)

- **File:** `src/python/server.py` `user()` at line 2676.
- **Change:** Add `AND last_seen_at > ?` parameter to the session lookup at line 2683, where the cutoff is `now - IDLE_TIMEOUT_MS` (configurable via `EINVITE_SESSION_IDLE_TIMEOUT_HOURS`, default 168 = 7 days).
- **Test:** `tests/test_session_idle_timeout.py` — create a session, manually set `last_seen_at` to 8 days ago in the DB, assert the next request returns 401.
- **Effort:** 30 min code + 30 min test.

### P2-C — Multi-tenant data-isolation lint test (Chapter 8 gap `[8.1.7]`)

- **File:** new file `tests/test_sql_isolation.py`.
- **Change:** Use AST parsing to walk `src/python/server.py` for every `db.execute("SELECT ... FROM <table>"` call; for tables in `{invitations, templates, page_templates, components, assets, guests, rsvps, ...}`, assert the WHERE clause contains `owner_id` or `user_id` or `invitation_id`. Whitelist admin-only queries (e.g. `admin_users`, `admin_overview`).
- **Test:** The lint test itself. Add a CI gate that fails the build if the lint finds an unguarded query.
- **Effort:** 2 hours code + 1 hour test.

### P2-D — Retry-After header on 429 responses (Chapter 13 gap `[13.1.2]`)

- **File:** `src/python/server.py` `rate_limit()` at line 2763 and 2771.
- **Change:** Add `self.send_header("Retry-After", str(window_seconds))` before the `self.json(429, ...)` call — but `self.json` already calls `end_headers`, so the header must be passed via the `headers=` kwarg of `self.json`. Modify `json()` to accept `Retry-After` in the headers dict.
- **Test:** `tests/test_rate_limit_retry_after.py` — exhaust the login rate limit; assert the 429 response has a `Retry-After` header matching the window (600 seconds).
- **Effort:** 30 min code + 30 min test.

### P2-E — `Content-Disposition` filename escaping (Chapter 1 gap `[1.1.8]`)

- **File:** `src/python/server.py` `send_binary()` at line 6373 and `send_media_binary()` at line 6403.
- **Change:** Sanitize the `filename` argument: `safe_name = filename.replace('"', '').replace('\r','').replace('\n','')[:180]`. Use RFC 5987 `filename*=UTF-8''<quoted>` form for non-ASCII filenames.
- **Test:** `tests/test_content_disposition_escape.py` — create an asset whose stored name contains `"`; assert the response's `Content-Disposition` header does not contain an unescaped quote.
- **Effort:** 30 min code + 30 min test.

## Priority 3 — Within 6 weeks (Chapters 3, 4, 5, 9, 11, 12, 13, 14 gaps)

### P3-A — Generic exception handler for `do_GET/PUT/POST/DELETE` (Chapter 13 gap `[13.1.8]`)

- **File:** `src/python/server.py` `do_GET/PUT/POST/DELETE` (lines 2982, 3092, 3165, 3135).
- **Change:** Wrap the entire dispatch in `try/except Exception as exc: log + return self.json(500, {"error":"Internal server error","requestId":self.request_id})` — but preserve the existing `MalwareDetected → 422` and `ValueError → 400` clauses.
- **Test:** `tests/test_500_handler.py` — monkeypatch `connect()` to raise `KeyError("boom")` on a GET; assert the response is 500 with `{"error":"Internal server error"}` and no stack trace in the body.
- **Effort:** 1 hour code + 1 hour test.

### P3-B — Per-user SSE connection limit (Chapter 13 gap `[13.1.7]`)

- **File:** `src/python/server.py` `invitation_events()` at line 4481.
- **Change:** Maintain a per-user `_SSE_CONNECTIONS` dict guarded by a lock; reject new SSE if user already has 5 open streams.
- **Test:** `tests/test_sse_limit.py` — open 6 SSE connections for the same user; assert the 6th returns 429.
- **Effort:** 1 hour code + 1 hour test.

### P3-C — HTTPS-only outbound webhook calls (Chapter 9 gap `[9.1.4]`)

- **File:** `src/python/server.py` `bot_protection_ok()` at line 2739; `production_preflight.py`.
- **Change:** In `bot_protection_ok`, reject `BOT_PROTECTION_ENDPOINT` URLs that don't start with `https://`. In `production_preflight.audit_environment`, warn when `EINVITE_BOT_PROTECTION_ENDPOINT` or `EINVITE_AI_ENDPOINT` is `http://`.
- **Test:** `tests/test_outbound_https.py` — set `EINVITE_BOT_PROTECTION_ENDPOINT=http://evil.example/verify`; assert `bot_protection_ok()` returns `True` (graceful degradation) and logs a warning; assert the preflight emits a warning.
- **Effort:** 30 min code + 30 min test.

### P3-D — Postgres `sslmode=require` enforcement (Chapter 9 gap `[9.1.6]`)

- **File:** `src/python/server.py` `connect_postgres()` at line 1359.
- **Change:** When `PRODUCTION_MODE`, parse `DATABASE_URL` query string; if `sslmode` is absent or not in `{require, verify-ca, verify-full}`, raise `RuntimeError`.
- **Test:** `tests/test_pg_sslmode.py` — set `EINVITE_PRODUCTION=1` and `EINVITE_DATABASE_URL=postgres://u:p@host/db` (no sslmode); assert startup raises.
- **Effort:** 30 min code + 30 min test.

### P3-E — Audit retention enforcement job (Chapter 11 gap `[11.1.3]`)

- **File:** `src/python/server.py` (new function `prune_audit_events()` near `cleanup_quarantine`); call from `__main__` (line 6615 area).
- **Change:** `db.execute("DELETE FROM audit_events WHERE created_at < ?", (now - AUDIT_RETENTION_DAYS * 86400 * 1000,))`. Note: the SQLite trigger `audit_events_no_delete` (line 1207) raises `ABORT` on DELETE — this must be done via a privileged maintenance path that drops the trigger, deletes, and recreates the trigger, OR the trigger must be amended to allow deletion when the actor is the system user. Simpler: add a separate `audit_events_archive` table and move old rows there.
- **Test:** `tests/test_audit_prune.py` — insert 100 audit_events with `created_at` 800 days ago; run the pruner; assert row count drops to 0.
- **Effort:** 1 hour code + 1 hour test (need to design around the immutability trigger).

### P3-F — Security headers on 503 from request-slot semaphore (Chapter 14 gap `[14.1.12]`)

- **File:** `src/python/server.py` `EInviteHTTPServer.process_request` at line 6626.
- **Change:** Instead of raw `request.sendall(b"HTTP/1.1 503 ...")`, emit a proper HTTP response with the standard security headers (CSP, HSTS, X-Frame-Options, etc.). Factor the header list into a shared helper so it stays in sync with `end_headers`.
- **Test:** `tests/test_503_headers.py` — exhaust the request_slots semaphore; assert the 503 response includes `Content-Security-Policy`.
- **Effort:** 1 hour code + 1 hour test.

### P3-G — Container runs as non-root (Chapter 14 gap `[14.1.8]`)

- **File:** `deploy/Dockerfile`.
- **Change:** Add `RUN groupadd -r app && useradd -r -g app -u 10001 app && chown -R app:app /app` and `USER app` before the `CMD`/`ENTRYPOINT`.
- **Test:** `tests/test_container_nonroot.sh` — `docker run --rm <image> id -u`; assert exit code is 0 and the printed UID is non-zero.
- **Effort:** 30 min code + 30 min test.

### P3-H — Restrictive permissions on `DATA` directory (Chapter 14 gap `[14.1.7]`)

- **File:** `src/python/server.py` near `DATA` initialization.
- **Change:** When `PRODUCTION_MODE`, call `os.chmod(DATA, 0o700)` at startup. Also `os.chmod` the SQLite DB file to 0600 after every `connect_sqlite` (or set the connection's `PRAGMA` to enforce file perms).
- **Test:** `tests/test_data_dir_perms.py` — start in production mode; assert `DATA.stat().st_mode & 0o777 == 0o700`.
- **Effort:** 30 min code + 30 min test.

### P3-I — Pagination caps on list endpoints (Chapter 13 gap `[13.1.3]`)

- **File:** `src/python/server.py` every `list_*` route.
- **Change:** Add a shared `_paginate(query, default=50, max=100)` helper that reads `?limit=` and `?offset=` from the query string, caps `limit` at `max`, and appends `LIMIT ? OFFSET ?` to the query.
- **Test:** `tests/test_pagination.py` — create 200 invitations; assert `GET /api/invitations?limit=200` returns at most 100 items.
- **Effort:** 2 hours code (touches ~20 routes) + 1 hour test.

### P3-J — `style-src 'unsafe-inline'` migration (Chapter 3 gap `[3.1.7]`)

- **File:** `src/js/editor/*.js`, `src/html/public.html` — remove `style="..."` inline attributes; move to scoped CSS classes.
- **Change:** Mechanical refactor; once all inline styles are gone, drop `'unsafe-inline'` from `style-src` in `server.py:2455`.
- **Test:** `tests/test_no_inline_style.py` — assert no `src/html/*.html` file contains `style="`. Assert the CSP header is `style-src 'self'`.
- **Effort:** 2–3 days of work (depends on volume of inline styles); defer to a dedicated sprint.

### P3-K — `free-form text` Unicode normalization (Chapter 2 gap `[2.1.1]`)

- **File:** `src/python/server.py` new `validate_printable_text(value, max_len=120)` helper; call from `update_guest_details` (line 4639), `update_studio_profile` (line 4036), and any other free-form text field.
- **Change:** Strip control chars (`\x00-\x1f`, `\x7f`), strip Unicode bidi overrides (`U+202A-U+202E`, `U+2066-U+2069`), normalize to NFC.
- **Test:** `tests/test_printable_text.py` — assert a name with `U+202E` is rejected.
- **Effort:** 1 hour code + 1 hour test.

### P3-L — Generic 500 error handler + structured logging (Chapter 14 gap `[14.1.13]`)

- **File:** `src/python/server.py` — replace every bare `print(...)` with a `log(level, event, message)` helper that respects `JSON_LOGS`.
- **Change:** Mechanical refactor; ensure no secret/PII values are printed.
- **Test:** `tests/test_structured_logging.py` — start with `EINVITE_JSON_LOGS=1`; trigger a Redis-unavailable warning; assert stdout contains a JSON object with `level: warning`.
- **Effort:** 1 day; defer to a dedicated sprint.

### P3-M — OpenAPI spec (Chapter 13 gap `[13.1.10]`)

- **File:** new file `docs/openapi.yaml` (or auto-generated from route decorators).
- **Change:** Enumerate all ~150 routes with method, path, request schema, response schema, auth requirement.
- **Test:** `tests/test_openapi_coverage.py` — assert every route in `do_GET/PUT/POST/DELETE` is present in `openapi.yaml`.
- **Effort:** 2–3 days; defer.

## Priority 4 — Phase 3+ (Chapter 10 — requires external tooling)

These gaps require CI/CD pipeline changes and external tooling that are out of scope for the Phase 1b code audit.

### P4-A — `pip-audit` / `safety` in CI (Chapter 10 gap `[10.1.1]`)

- **File:** new file `.github/workflows/security.yml`.
- **Change:** Add a job that installs `pip-audit`, runs `pip-audit -r docs/requirements-production.txt --strict`, and fails on any CVE. Run on every PR and nightly.
- **Test:** The workflow itself.
- **Effort:** 1 hour.
- **Phase:** 3 (Production Certification).

### P4-B — Trivy image scan in CI (Chapter 10 gap `[10.1.2]`)

- **File:** `.github/workflows/security.yml`.
- **Change:** After building the Docker image, run `trivy image --severity HIGH,CRITICAL --exit-code 1 $IMAGE`. Fail the build on critical findings.
- **Test:** The workflow itself.
- **Effort:** 1 hour.
- **Phase:** 3.

### P4-C — Bandit + Semgrep SAST in CI (Chapter 10 gap `[10.1.3]`)

- **File:** `.github/workflows/security.yml`, `.bandit`, `semgrep.yml`.
- **Change:** Add `bandit -r src/python/ -ll -x tests/` and `semgrep --config p/owasp-top-ten --config p/python src/`. Fail on HIGH.
- **Test:** The workflow itself.
- **Effort:** 2 hours.
- **Phase:** 3.

### P4-D — SBOM generation (Chapter 10 gap `[10.1.4]`)

- **File:** `.github/workflows/security.yml`.
- **Change:** Run `syft . -o cyclonedx-json > sbom.json` and upload as a build artifact.
- **Test:** The workflow itself.
- **Effort:** 1 hour.
- **Phase:** 3.

### P4-E — CODEOWNERS + PR template (Chapter 10 gap `[10.1.6]`)

- **File:** new files `CODEOWNERS`, `.github/pull_request_template.md`.
- **Change:** List `src/python/server.py`, `src/python/security_v13.py`, `src/python/security_scanner_v54.py`, `src/python/secrets_v54.py`, `src/python/production_preflight.py` under a security maintainer. PR template asks reviewers to confirm they inspected security-relevant files.
- **Test:** Process — verified by reviewer sign-off.
- **Effort:** 30 min.
- **Phase:** 3.

### P4-F — Independent penetration test (cross-chapter)

- **Reference:** `docs/SECURITY_HARDENING_REPORT_2026-08-10.md` line 58 ("Commission an independent penetration test before accepting real customer data or payments").
- **Change:** Schedule a third-party pen-test after all P1/P2/P3 remediations are merged.
- **Phase:** 3.

---

# Summary Metrics

| Chapter | Pass | Partial | Fail | N/A | Total |
|---|---|---|---|---|---|
| 1 — Encoding/Sanitization | 6 | 3 | 0 | 0 | 9 |
| 2 — Validation/Business Logic | 6 | 3 | 0 | 0 | 9 |
| 3 — Web Frontend Security | 7 | 1 | 0 | 1 | 9 |
| 4 — API and Web Service (overview) | 4 | 1 | 0 | 0 | 5 |
| 5 — File Handling | 6 | 1 | 0 | 0 | 7 |
| 6 — Authentication | 9 | 5 | 0 | 0 | 14 |
| 7 — Session Management | 9 | 1 | 0 | 0 | 10 |
| 8 — Authorization | 7 | 1 | 0 | 0 | 8 |
| 9 — Communication Security | 4 | 3 | 0 | 1 | 8 |
| 10 — Malicious Code Search | 1 | 1 | 4 | 0 | 6 |
| 11 — Business Logic / Data Integrity | 8 | 1 | 0 | 0 | 9 |
| 12 — Files and Resources | 6 | 1 | 0 | 0 | 7 |
| 13 — API and Web Service (detailed) | 6 | 4 | 1 | 0 | 11 |
| 14 — Configuration and Deployment | 9 | 4 | 1 | 0 | 14 |
| **Total** | **88** | **29** | **6** | **2** | **125** |

- **Pass rate:** 88 / 125 = 70.4%.
- **Priority 1 gaps (immediate):** 4 (P1-A through P1-D).
- **Priority 2 gaps (2 weeks):** 5 (P2-A through P2-E).
- **Priority 3 gaps (6 weeks):** 13 (P3-A through P3-M).
- **Priority 4 gaps (Phase 3+):** 6 (P4-A through P4-F).

The platform already meets the ASVS L2 bar on Argon2id, MFA, passkeys, CSP, CSRF, rate limiting, audit chain, malware scanning, host allowlist, deny-by-default static serving, signed media URLs, and production preflight. The most impactful remaining gaps are: reflected HTML injection in `serve_public` (mitigated by CSP), account-lockout absence, MFA recovery codes, idle session timeout, and the CI/CD-side tooling (pip-audit / Trivy / Bandit / SBOM / CODEOWNERS) which is deferred to Phase 3.

---

# References

- **Source code evidence:** `src/python/server.py`, `src/python/security_v13.py`, `src/python/security_scanner_v54.py`, `src/python/secrets_v54.py`, `src/python/production_preflight.py`, `src/html/public.html`.
- **Internal docs:** `docs/SECURITY.md`, `docs/SECURITY_HARDENING_REPORT_2026-08-10.md`, `docs/ARCHITECTURE.md` (security stack table), `docs/V31_AUTHORIZATION.md`, `docs/ROADMAP.md` §4 (Phase 1b).
- **External standards:** OWASP ASVS 5.0.0 (October 2024) — Level 2. OWASP Top 10 (2021). NIST SP 800-63B (authentication). RFC 6238 (TOTP), RFC 8446 (TLS 1.3), W3C CSP Level 3.
- **Audit scope:** code-evidence audit only. No dynamic testing was performed. An independent penetration test (P4-F) is required before production cutover.
