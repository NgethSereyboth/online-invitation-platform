# V32 Security Architecture

V32 centralizes workspace/invitation authorization, role checks, request and upload bounds, signed private object delivery, mass-assignment allowlists, collaboration path restrictions, publish asset validation, audit-safe errors and secret redaction. Existing Argon2id, session rotation, CSRF, Origin checks, MFA/passkey foundations, rate limits and account lifecycle controls remain in place.

Production startup requires HTTPS public configuration and stable secrets. External email, messaging, bot-risk, AI, object-storage, monitoring and tracing providers remain environment adapters. No credential is stored in invitation documents, browser storage, exports, logs or the ZIP.
