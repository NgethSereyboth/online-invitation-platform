# S10 · Invitation read cluster

Status: **ported and proven identical locally 2026-11-14.** Four authenticated GET routes moved;
writes and the version timeline stay on Python. Traffic ramp and p95 remain deployment work.

## What moved

```
services/api-node/lib/authz.mjs              current user, invitation roles, predicates
services/api-node/lib/invitation-routes.mjs  GET /api/invitations/:id
                                             GET /api/invitations/:id/guests
                                             GET /api/invitations/:id/rsvps
                                             GET /api/trash
services/api-node/test/invitation-authz.test.mjs
tools/invitation-read-parity.py              16-case cross-backend proof
```

These are the editor's first load, the guests/RSVP dashboards' first read, and the owner's trash list. Three behaviours are
easy to get subtly wrong, and all three are copied rather than "cleaned up":

- **Role resolution** — owner if `invitations.owner_id` matches **and** `deleted_at IS NULL`,
  otherwise the `invitation_collaborators.role`. A deleted invitation therefore demotes its owner to
  `null` and answers 404, even though the row exists.
- **Status codes differ by route** — `GET /api/invitations/:id` answers 404 when the invitation is
  missing *or* unreadable, while `/guests` answers **403** in both cases, because Python's
  `_guest_page()` returns `None` for both and the handler maps that to "management permission
  required". `/rsvps` answers 403 for anything below manager. Reproducing the inconsistency is the
  contract.
- **Personal links** — the guest payload mints `token = base64url(HMAC-SHA256("<id>|<salt>|<version>"))`
  truncated to 32 characters, from `EINVITE_GUEST_TOKEN_SECRET` (or the `.guest-token-secret`
  sidecar). A guest with a revoked or expired link gets `token: null` and
  `personalLinkAvailable: false`. The token is part of the compared payload, so a different key
  fails the proof.

Also copied: RSVP status per guest is the **newest** row for the lower-cased name; `tags_json` becomes
`tags`; guest phone/email are revealed through the field cipher; RSVP `answers_json` becomes
`answers`.

## Proof

`tools/invitation-read-parity.py` seeds one PostgreSQL database (four users with live sessions, five
invitations including a deleted and a foreign one, collaborators at `content` and `manager`, four
guests including revoked and expired links, two RSVPs) and sends every case to both backends.

| Case | Python | Node |
|---|---|---|
| unauthenticated invitation | 401 | 401 |
| owner / collaborator invitation | 200 | 200 |
| stranger / deleted / missing invitation | 404 | 404 |
| owner / manager guests | 200 | 200 |
| content / missing-invitation guests | 403 | 403 |
| empty invitation guests | 200 (`[]`) | 200 (`[]`) |
| unauthenticated guests | 401 | 401 |
| owner / manager RSVPs | 200 | 200 |
| content / stranger RSVPs | 403 | 403 |
| unauthenticated trash | 401 | 401 |
| owner trash (titled + untitled) | 200 | 200 |
| stranger trash (empty) | 200 (`[]`) | 200 (`[]`) |

**INVITATION READ PARITY 19/19 identical, 0 failing.** Service suite **42 passed**.

## Not done, and why

- **`GET /api/invitations/:id/versions` and `/versions/:version`** — both merge `publications` with
  auto-snapshots from `features/invitation_versions.py`. That module is a separate port (its own
  listing semantics and error handling); until it moves, the version timeline stays pinned to Python.
- **Every write** (archive, slug, guest add, RSVP update/delete) — Phase D writes need snapshot-based
  comparison (Rule 8), not a response diff, and RSVP is the load-test target. They stay Python.
- **S9 (auth)** is blocked on a dependency decision, not on code: verifying seeded Argon2id hashes
  needs an Argon2 implementation, and no pure-Node option exists — `argon2`/`@node-rs/argon2` are
  native addons that the approved D2 set does not include. Reordering to S10 was the smallest
  unblocked step; S9 needs a written D2 extension before it can start.
- **Traffic ramp and p95** — deployment steps; P1 still has no baseline.
