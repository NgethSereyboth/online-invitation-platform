# Security notes

The review build contains production-oriented security foundations, but deployment security still depends on correct environment configuration.

## Implemented

- PBKDF2 password hashing and server-side hashed session records.
- HttpOnly, SameSite session cookie; `Secure` is enabled with `EINVITE_COOKIE_SECURE=1`.
- Same-origin validation for cookie-authenticated state-changing requests.
- CSP, HSTS when secure cookies are enabled, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP and CORP headers.
- Owner/collaborator authorization on invitation data.
- Rate limiting with optional Redis backend.
- File-size, declared MIME and binary-signature validation for normal uploads.
- Quarantine-first upload handling with optional fail-closed malware scanning; the laptop launcher uses Microsoft Defender by default.
- Deny-by-default static delivery: backend source, environment files, databases, backups, logs, tests and signing secrets are never generic web files.
- Configurable Host allowlisting, duplicate/unsupported request-framing rejection, idle socket timeouts and bounded concurrent request handling.
- Signed billing webhook verification.
- Password reset and verification tokens are stored hashed and expire.
- Public invitation passwords are hashed; unlock tokens expire.

## Deployment requirements

1. Serve only behind HTTPS and set `EINVITE_COOKIE_SECURE=1`.
2. Set a strong, private billing webhook secret when billing is connected.
3. Use restricted object-storage credentials and configure bucket CORS deliberately.
4. Keep `EINVITE_DEV_AUTH_TOKENS=0` in production.
5. Use PostgreSQL and Redis for multi-instance deployments.
6. Configure backups, monitoring, log retention and secret rotation.
7. Tighten CSP further after remaining legacy inline style attributes are migrated; executable inline scripts are already blocked.
8. Require a working malware scanner for every upload-processing instance. Laptop mode probes Microsoft Defender before startup; production can use `EINVITE_MALWARE_SCANNER_COMMAND` with a maintained scanner such as ClamAV.
9. Configure `EINVITE_ALLOWED_HOSTS` with the exact application and custom-domain hosts accepted by the deployment.

## Laptop security boundary

- Keep the Windows network profile set to **Private** only on networks you trust.
- Do not forward the laptop-hosting port through the router and do not expose it directly to the Internet.
- Keep Windows, browsers, Microsoft Defender or the active endpoint-security product, Python dependencies and router firmware updated.
- `-AllowUploadsWithoutMalwareScan` is an emergency compatibility override. It weakens the application upload gate and should be used only when another active endpoint-security product is providing equivalent scanning.

## Responsible disclosure

For a public launch, publish a dedicated security contact and disclosure policy before accepting real customer/event data.
