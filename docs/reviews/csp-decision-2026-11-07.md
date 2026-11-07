# CSP decision — 2026-11-07

**Status:** `NEEDS_HUMAN_ACTION` — proposed `RISK_ACCEPTED_WITH_SIGNOFF`, pending owner signature
**Expiry / re-review:** 2027-05-07
**Scope:** enforcing and report-only CSP headers served by `src/python/server.py`.

## Current policy

```text
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob: https:;
media-src 'self' blob:;
font-src 'self' data:;
frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://w.soundcloud.com;
connect-src 'self';
object-src 'none';
base-uri 'self';
frame-ancestors 'self';
form-action 'self'
```

The Report-Only header mirrors the policy with `report-uri /api/csp-report; report-to csp`.

Evidence: `reports/headers-final-2026-11-07.secure.txt`, `reports/zap-active-health.json`, `reports/vamp-headers.json`.

## Why each accepted directive exists

### `style-src 'unsafe-inline'`

- Many generated invitation/editor surfaces use inline `style` attributes and JS-created style elements for dynamic geometry, responsive layout, and user-selected colours.
- Replacing these with nonces/hashes would require a coordinated change across generated HTML, JS renderers, and the email/print surfaces, plus regression coverage for the editor and guest pages.
- `style-src 'unsafe-inline'` permits CSS injection, but not script execution. The higher-impact `script-src` is strict (`'self'`, no `unsafe-inline`, no `unsafe-eval`).

### `img-src 'self' data: blob: https:`

- Invitation media can be hosted on external HTTPS origins selected by hosts; the public invitation and album surfaces must render those images.
- `data:` and `blob:` are required for editor previews and client-side image handling.
- A narrow origin allowlist is not yet available because the product supports customer-supplied media origins. This is a functional constraint, not an unexamined default.

### Absent `Cross-Origin-Embedder-Policy`

- COEP `require-corp` would block the YouTube, YouTube-nocookie, and SoundCloud frames and cross-origin invitation media unless every provider and media origin emits compatible CORP/CORS headers.
- The application already sends `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-site`. Those controls are compatible with the current media model and remain in place.
- Enabling COEP is a separate compatibility project and must be tested against the full external-media matrix before adoption.

## Exploitability

- **Style injection:** An attacker who can inject markup could add arbitrary CSS, potentially hiding UI or exfiltrating some data through CSS selectors/URLs. It cannot execute JavaScript because `script-src` is strict and `object-src` is `none`.
- **Image-origin breadth:** A malicious page cannot read cross-origin image pixels without CORS, but broad `https:` permits requests to attacker-selected image URLs. The relevant exfiltration path is constrained by the strict script policy and same-origin `connect-src`.
- **COEP absence:** Cross-origin resources can be embedded subject to the other headers. COOP/CORP reduce cross-origin isolation attacks but do not provide the full `crossOriginIsolated` guarantee.

## Compensating controls

- Strict script policy: no `unsafe-inline` and no `unsafe-eval`.
- `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'self'`, `form-action 'self'`.
- COOP `same-origin`, CORP `same-site`.
- CSP Report-Only monitoring to `/api/csp-report` with a documented weekly review query.
- Server-side output escaping and the SEC-01 DOM-XSS fix.
- Authenticated mutation CSRF checks; no CORS reflection.

## Hardening options

1. **Preferred medium-term:** move inline styles to named classes or nonce-bearing style blocks for editor/guest routes, then remove `unsafe-inline` from `style-src`.
2. **Media allowlist:** introduce a host-configured `img-src` allowlist per deployment and keep `https:` only as an explicit compatibility fallback.
3. **COEP:** evaluate `require-corp` only on a separate test origin with the complete provider/media matrix; do not enable globally until all required resources pass.
4. **Report-only first:** keep the report-only policy in place for at least one clean week before tightening enforcement.

No automated hardening was applied in this pass: the changes would be broad, cross-cutting, and could break invitation rendering, external media, or the editor. The safe decision is to retain the current policy under explicit owner sign-off.

## Owner sign-off

I, the system owner, accept the residual risk of `style-src 'unsafe-inline'`, `img-src https:`, and absent COEP for the period ending **2027-05-07**, based on the compensating controls above.

- Name:
- Role:
- Date:
- Signature / ticket reference:

**Re-review trigger:** any CSP violation spike, new external media provider, editor inline-style migration, or the expiry date above.
