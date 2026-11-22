# S7 · Public invitation read path

Status: **ported and proven identical locally 2026-11-14.** The traffic ramp (shadow → 5 % → 25 % →
100 %) and the p95 comparison against the P1 baseline are **deployment steps that have not been
performed** — see "Not done here".

## What moved

`GET /api/public/<slug>` — Python's `get_public()` (server.py 8725), the read the public page makes
before it renders. New Node code:

```
services/api-node/lib/public-routes.mjs    the route + projection (get_public)
services/api-node/lib/media.mjs            signed media URLs, gallery locking, document URL rewriting
services/api-node/lib/public-document.mjs  guest bindings, merge fields, guest token hashing
services/api-node/test/public-document.test.mjs  unit tests for the helpers
tools/public-parity.py                     cross-backend proof, 9 cases
```

The response contract is copied field for field: `invitationId`, `publicationId`, `version`,
`document`, `guest`, `analyticsConsentRequired`, `externalMediaConsentRequired`, `galleryProtected`,
`galleryAuthorized`, `studioBrand`, `sentAt`, `editedAfterSendAt`; 404 `Published invitation not
found`; 403 `{error: "Password required", protected: true}`.

Behaviour that could not be invented, only copied:

- **Publication selection** — most recent `publications` row for a live invitation
  (`archived=0`, `deleted_at IS NULL`, `is_published=1`, unexpired), not the draft.
- **View counting** — `views+1` plus one `view_events` row, skipped entirely when the document
  requires analytics consent. A public read is not read-only, and a port that forgot this would
  silently change the owner's analytics.
- **Media signatures** — `/api/media/<file>?i=<invitation>&exp=<epoch>&sig=<hmac-sha256>` over
  `"<file>|<invitation>|<exp>"`, the same payload Python verifies on the way back in. The secret is
  `EINVITE_MEDIA_SIGNING_SECRET`, else the `.media-signing-secret` sidecar, so both runtimes sign
  with one key.
- **Gallery protection** — only images that appear *nowhere else* in the document are locked; an
  authorised gallery signs them instead, and `galleryProtection.locked` is only set when protection
  is configured.
- **Password mode** — never leaks raw `/uploads/…` paths: every managed URL, including ones embedded
  in rich-text/CSS strings, is rewritten to a signed first-party URL.
- **Guest tokens** — a token resolves only its own guest, stamps `opened_at` once, and resolves
  `guest.*`-bound objects in both canvas groups. Precedence is header → `?guest=` → `?g=`, as Python.

## Proof

`tools/public-parity.py` seeds one real PostgreSQL database, boots Python and the Node service
against it with one shared data directory and signing secret, and sends every request to both.
Media URLs are normalised only after each response's signature is **recomputed and verified** with
that secret; expiry is masked because it is wall-clock.

| Case | Python | Node | Result |
|---|---|---|---|
| unknown slug | 404 | 404 | identical |
| empty slug (`/api/public/`) | 404 | 404 | identical |
| plain document (no gallery) | 200 | 200 | identical |
| gallery protected, no token | 200 | 200 | identical (locked, media cleared) |
| gallery protected, valid token | 200 | 200 | identical (signed media) |
| guest token | 200 | 200 | identical (guest + bound text) |
| analytics-consent document | 200 | 200 | identical (no view write) |
| password mode, no token | 403 | 403 | identical |
| password mode, accepted token | 200 | 200 | identical (rewritten URLs) |

**PUBLIC PARITY 9/9 identical, 0 failing.** Service tests: **34 passed** (media signature shape,
gallery lock/unlock, embedded-URL rewriting, merge fields, guest bindings).

## Not done here

- **Shadow / 5 % / 25 % / 100 % ramp** — a routing and deployment action, not a code change. The
  replay above covers every status code the route produces; it is not a 72 h shadow.
- **p95 within 10 % of the P1 baseline** — P1's load baseline has never run (`k6` is not installed).
  Until it does, this exit criterion is unmeasured, not met.
- **`/i/<slug>` HTML** — the page itself is still rendered by Python; S3 already serves the shell's
  no-row branch. The plan's "`GET /i/<slug>` data" is this JSON route, which is what the page calls.
- **"Public RSVP status read"** — the plan names it, but the codebase has no public GET for RSVP
  status: RSVP is a write-only `POST /api/public/<slug>/rsvps`, and status reads are the host's
  authenticated `GET /api/invitations/<id>/rsvps`. The read slice is therefore the public document
  plus its guest data. Recorded here rather than inventing an endpoint to match the plan.
- Rate limiting does not apply to this route (no `rate_limit()` call in Python), so it does not
  conflict with the pinning decision in `P7-SHARED-STATE.md`.
