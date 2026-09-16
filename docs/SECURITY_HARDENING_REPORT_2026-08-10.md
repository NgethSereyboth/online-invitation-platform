# V0.52 Security Hardening Report

Date: 2026-08-10  
Status: Local security-hardened release candidate

## Scope and safety boundary

This review used non-destructive abuse cases against temporary local databases and loopback HTTP servers. It did not target GitHub, production hosting, third-party providers, other users, or any system outside the supplied project. This is a practical application-security review, not a guarantee that the platform is unhackable and not a substitute for an independent production penetration test.

## Confirmed hardening changes

- Production registration can no longer obtain administrator privileges merely by matching a configured email address. Promotion occurs only after successful email verification. The legacy local bootstrap is loopback-only and disabled in production.
- Production cookie sessions now require the session-bound CSRF token for every unsafe request, even when optional browser metadata is absent.
- Host authorities are strictly parsed and allow-listed. `X-Forwarded-Proto` is accepted only from an exact configured trusted-proxy IP.
- Reflected request IDs are normalized and bounded to prevent response-header or structured-log injection.
- Arbitrary root JSON build and route artifacts are no longer publicly served. Production health endpoints expose only minimal status unless detailed disclosure is explicitly enabled.
- Registration and login password inputs are capped at 200 characters to avoid expensive password-hash denial of service.
- Production password-reset responses are uniform. Unknown passkey accounts receive an indistinguishable ephemeral challenge instead of an account-revealing error.
- WebAuthn registration and authentication explicitly require the user-presence flag.
- Public billing failures no longer expose internal exception text.
- Archive imports reject oversized entries and suspicious compression ratios before decompression.
- V32 upload sessions enforce safe MIME types, full SHA-256 format, stored-object checksum verification, magic-byte and image validation, malware-scanner policy, and deletion/quarantine on rejection.
- Signed object URLs require a database object-version record owned by the caller's workspace. Unsafe content is forced to download instead of inline rendering.
- Registration now provisions the user's personal workspace regardless of whether a readiness probe or a platform endpoint initialized the V32 schema first.

## Live adversarial cases exercised

The regression suite verifies:

- source, environment, route-manifest, and build-metadata disclosure is denied;
- public health responses are minimal in production mode;
- malformed and untrusted Host headers are rejected;
- hostile request IDs are normalized;
- cross-site registration and tokenless cookie-session mutations are rejected;
- excessive passwords are rejected before expensive hashing;
- passkey-start account enumeration is resisted;
- cross-account invitation read/delete attempts return not found;
- executable/HTML upload types and incomplete checksums are rejected;
- script bytes declared as PNG are rejected and removed from storage;
- legacy uploads reject MIME/magic mismatches;
- high-ratio compressed archives are rejected before decompression;
- unknown or cross-boundary object keys cannot receive signed URLs;
- production settings cannot re-enable weak CSRF or unverified local-admin bootstrap.

## Validation evidence

- Python compilation of the changed security modules: passed.
- Focused live adversarial suite: passed.
- Existing authentication, upload, platform V32, production preflight, storage, and smoke compatibility suites: passed.
- Complete deterministic review gate: 101/101 passed.
- Package integrity manifest and editor/route build checks: passed after final regeneration.
- `pip check`: passed for the available test environment.

## Remaining production work

- Run the full 116-check browser matrix on the final deployment target.
- Run an authenticated dependency and container-image CVE scan in CI. Bandit and pip-audit were not installed in this offline review environment.
- Commission an independent penetration test before accepting real customer data or payments.
- Configure TLS at the reverse proxy, exact allowed hosts and proxy IPs, PostgreSQL, authenticated Redis, private S3/R2/MinIO storage, SMTP, payment-provider secrets, and regular secret rotation.
- Configure a real malware-scanning command and keep production fail-closed behavior enabled.
- Enable WAF/rate limiting at the edge, centralized immutable audit logs, alerting, encrypted backups, and tested point-in-time restoration.
- Test live billing webhooks, email verification, password reset, object storage, AI providers, and backup restoration with staging credentials before production cutover.

## Recommended production posture

Use least-privilege service accounts, separate staging and production credentials, private database/storage networks, short-lived signed URLs, enforced MFA for administrators, regular access reviews, and documented incident-response and key-rotation procedures. Never deploy the included example environment values as secrets.
