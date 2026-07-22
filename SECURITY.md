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
7. Tighten CSP further after the remaining legacy inline styles/scripts are migrated to external modules; the current compatibility CSP still permits inline code.

## Responsible disclosure

For a public launch, publish a dedicated security contact and disclosure policy before accepting real customer/event data.
