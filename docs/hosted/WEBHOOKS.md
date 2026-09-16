# Outbound webhooks (v0.62.1)

This document describes how outbound webhooks from the eInvite platform are
signed and how receivers should verify them. Applies to all webhook
destinations registered via the platform's outbound-notification system
(billing, RSVP events, AI events, plugin marketplace events).

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

1. Generate a new secret via the webhook-destination rotation endpoint.
2. Update the receiver with the new secret.
3. The old secret is invalid immediately for new requests; the platform
   keeps the previous secret for 24 hours (dual-key window) so requests
   in flight when the rotation happens still verify. See
   [`docs/ops/SECRETS-ROTATION.md`](../ops/SECRETS-ROTATION.md) for the
   full rotation runbook.

## Event types

| Event                | Fired when                                            |
|----------------------|------------------------------------------------------|
| `rsvp.created`        | A guest submits an RSVP.                             |
| `rsvp.updated`        | A guest updates their RSVP.                          |
| `invitation.published`| A host publishes an invitation.                      |
| `invitation.unpublished` | A host unpublishes an invitation.                 |
| `invitation.archived` | A host archives an invitation.                       |
| `billing.checkout_completed` | A billing checkout session was paid.         |
| `billing.subscription_cancelled` | A subscription was cancelled.              |
| `ai.blueprint_created` | An AI agent generated a design blueprint.         |

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
