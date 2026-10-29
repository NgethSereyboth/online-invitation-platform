# Outbound webhooks (v0.62.1)

This document describes how outbound webhooks from the eInvite platform are
signed and how receivers should verify them.

## Registering a destination

Destinations are managed over the account API (session or bearer auth):

| Method | Path | Body / result |
|---|---|---|
| `POST`   | `/api/account/webhooks` | `{url, events: ["rsvp.created", …]}` (or `["*"]`); returns `{id, secret, secretHint, …}` — the **secret is shown once** |
| `GET`    | `/api/account/webhooks` | list; carries `secretHint` (last 4) and the last delivery status, never the secret |
| `POST`   | `/api/account/webhooks/{id}/rotate` | new secret, shown once; deliveries use it immediately |
| `DELETE` | `/api/account/webhooks/{id}` | revoke; deliveries stop immediately |

URLs must be absolute **https** and must not resolve to private, loopback,
link-local (including the cloud metadata address) or reserved addresses; set
`EINVITE_ALLOW_PRIVATE_WEBHOOKS=1` only for a deliberately private receiver
(a local relay or the test suite), which also permits plain `http`. The host is
resolved at registration **and again before every attempt**, and the request is
sent to the address that was just checked, so a DNS answer that changes later
cannot redirect a delivery. Redirects are **not** followed: a `3xx` is a final
answer. Each attempt has a 5 s timeout and reads at most 64 KiB of the reply.

Deliveries are durable. `dispatch_webhook_event` writes one `webhook.deliver`
job per subscribed endpoint into the `background_jobs` queue; a worker drains it
and retries transport errors, 408/409/425/429 and 5xx on a 1, 2, 4, 8 s backoff,
with the fifth failure final. Any other status (including a `4xx` and a
redirect) is final immediately. Each attempt is freshly signed, so a retry
minutes later still verifies.

## Header layout

Every outbound webhook request includes these three headers:

| Header                  | Purpose                                        |
|-------------------------|------------------------------------------------|
| `Content-Type`          | Always `application/json`.                     |
| `X-EInvite-Signature`  | `t=<ts>,v1=<hex>` HMAC-SHA256 of `"<ts>.<body>"`. |
| `X-EInvite-Timestamp`  | Same timestamp as `t=` in the signature header (ms). |

The signature is computed as:

```text
payload  = f"{ts}." + body_bytes
v1       = HMAC-SHA256(secret, payload).hex()
header   = f"t={ts},v1={v1}"
```

`<ts>` is a Unix millisecond timestamp captured at signing time. The body
is the EXACT bytes that will be sent on the wire (do NOT re-serialize JSON
before verifying — field-order changes would invalidate the signature).

## Receiver verification

In Python:

```python
import hashlib, hmac, time

def verify_einvite_signature(body: bytes, signature_header: str, secret: str,
                              tolerance_ms: int = 5 * 60 * 1000) -> bool:
    parts = signature_header.split(",")
    if len(parts) < 2:
        return False
    ts_str, v1_str = parts[0], ",".join(parts[1:])
    if not ts_str.startswith("t=") or not v1_str.startswith("v1="):
        return False
    try:
        ts = int(ts_str[2:])
    except ValueError:
        return False
    expected_payload = f"{ts}.".encode("ascii") + body
    expected = hmac.new(secret.encode("utf-8"), expected_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, v1_str[3:]):
        return False
    now_ms = int(time.time() * 1000)
    if ts > now_ms + 30_000:  # clock skew
        return False
    if (now_ms - ts) > tolerance_ms:  # replay window
        return False
    return True
```

In Node.js:

```javascript
const crypto = require('crypto');

function verifyEinviteSignature(body, signatureHeader, secret, toleranceMs = 5 * 60 * 1000) {
  const parts = signatureHeader.split(',');
  if (parts.length < 2) return false;
  const tsStr = parts[0];
  const v1Str = parts.slice(1).join(',');
  if (!tsStr.startsWith('t=') || !v1Str.startsWith('v1=')) return false;
  const ts = parseInt(tsStr.slice(2), 10);
  const provided = v1Str.slice(3);
  const expected = crypto.createHmac('sha256', secret)
    .update(`${ts}.${body}`)
    .digest('hex');
  if (!crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(provided))) return false;
  const now = Date.now();
  if (ts > now + 30000) return false;
  if (now - ts > toleranceMs) return false;
  return true;
}
```

## Replay protection

Receivers MUST reject any signature whose `t=` timestamp is more than 5
minutes (default) older than the receiver's current time, OR whose timestamp
is more than 30 seconds in the future (to allow for clock skew between sender
and receiver).

If your receiver's clock is known to drift (e.g. a Lambda in a region with
NTP issues), increase the tolerance via the `tolerance_ms` argument. 5
minutes is the platform default — longer windows weaken replay protection.

## Secret management

Each webhook destination has its own secret. The secret is generated via
`core.webhooks.generate_webhook_secret()` (32-byte URL-safe) and stored
**encrypted at rest** via `core.crypto.encrypt_field` (the same Fernet key
used for PII columns). The secret is shown ONCE on creation (similar to API
keys); the platform surfaces only the last 4 characters in subsequent
listings.

If a secret is compromised:

1. `POST /api/account/webhooks/{id}/rotate` and capture the new secret.
2. Update the receiver with the new secret.
3. Every request is signed **at send time** with the current secret, so no
   sender-side dual-key window exists or is needed: once the receiver has the
   new secret, verifications succeed. If you want a receiver-side overlap,
   accept both secrets there for a few minutes. See
   [`docs/ops/SECRETS-ROTATION.md`](../ops/SECRETS-ROTATION.md) for the
   full rotation runbook.

## Event types

| Event                | Fired when                                            | Status |
|----------------------|------------------------------------------------------|--------|
| `rsvp.created`        | A guest submits an RSVP.                             | wired |
| `rsvp.updated`        | A guest updates their RSVP.                          | wired |
| `invitation.published`| A host publishes an invitation.                      | reserved |
| `invitation.unpublished` | A host unpublishes an invitation.                 | reserved |
| `invitation.archived` | A host archives an invitation.                       | reserved |
| `billing.checkout_completed` | A billing checkout session was paid.         | reserved |
| `billing.subscription_cancelled` | A subscription was cancelled.              | reserved |
| `ai.blueprint_created` | An AI agent generated a design blueprint.         | reserved |

“Reserved” events are part of the contract but have no emitter yet; a
destination subscribed to one simply receives nothing until the emitter lands.

Each event body has the shape:

```json
{
  "event": "rsvp.created",
  "timestamp": "2026-09-15T13:28:25.123Z",
  "data": { /* event-specific payload */ },
  "eventId": "uuid"
}
```

## Testing the verifier

The platform ships a Python verifier at `src/python/core/webhooks.py`.
Run the smoke test:

```bash
PYTHONPATH=src/python:. python3 -c "
from core import webhooks
body = b'{\"event\":\"rsvp.created\",\"id\":42}'
sig = webhooks.sign_webhook(body, 'whsec_test', timestamp_ms=1700000000000)
print('verify:', webhooks.verify_signature(body, sig, 'whsec_test', now_ms=1700000000000))
"
```

The acceptance criterion for §4.6 is: outbound webhooks are signed and the
receiver can verify them. This document, the module, and the smoke test
satisfy that criterion.
