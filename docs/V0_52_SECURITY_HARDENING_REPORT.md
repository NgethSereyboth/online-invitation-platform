# V0.52 security hardening report

## Closed vulnerabilities and strengthened boundaries

- Replaced unrestricted static-file fallback with a deny-by-default public asset allowlist. Backend source, environment files, SQLite data, backups, logs, tests, scripts and signing secrets can no longer be downloaded by guessing their paths.
- Applied the same private-file boundary to `HEAD` requests to prevent file enumeration through metadata.
- Added exact Host allowlisting for laptop deployments, with support for published custom domains, to reduce Host-header injection and DNS-rebinding exposure.
- Rejects unsupported transfer encodings, duplicate content lengths, missing HTTP/1.1 Host headers and negative or invalid request lengths.
- Added idle socket timeouts and bounded request concurrency to reduce slow-connection and thread-exhaustion denial-of-service risk.
- Removed Python version disclosure from the HTTP `Server` header.
- Added quarantine-first, fail-closed upload malware scanning. One-command laptop hosting probes Microsoft Defender before startup and scans each material before storage.
- Exposed non-sensitive malware-scanner readiness in `/api/health` so launchers and operators can detect a failed security control.
- Restricted laptop Host headers to localhost, the laptop name and its detected private LAN address.

## Laptop behavior

The default laptop launcher refuses to start if Microsoft Defender cannot complete a harmless scan probe. `-AllowUploadsWithoutMalwareScan` is an explicit compatibility override for systems protected by another active endpoint-security product; it weakens the application-level upload gate.

The Windows Firewall rule remains limited to the Private profile. Laptop hosting is not intended for router port forwarding or direct public Internet exposure.

## Verification

- 94/94 deterministic platform checks passed with the complete audited dependency runtime.
- Live private-file, Host-header, request-boundary and fail-closed scanner regression tests passed.
- Targeted real-browser checks passed for static assets, full editor/server workflow, uploads, publishing, RSVP, protected media, UI smoke, public lazy loading and the guest journey.
- Release manifest integrity checks passed without changing `README.md`.

## Operational responsibilities that remain external

- Keep Windows, endpoint protection, browsers, Python dependencies and router firmware patched.
- Use HTTPS, PostgreSQL, Redis, private object storage, durable encrypted backups, monitoring and managed secrets before public production launch.
- Configure a maintained malware scanner on every production upload-processing instance.
- Do not disable the firewall, expose the laptop port publicly or treat LAN HTTP mode as Internet-grade hosting.
