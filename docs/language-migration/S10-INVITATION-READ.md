# S10 · Invitation read cluster

Status: **ported and proven identical locally 2026-11-14.** Six authenticated GET routes moved;
writes and the version timeline stay on Python. Traffic ramp and p95 remain deployment work.

## What moved

```
services/api-node/lib/authz.mjs              current user, invitation roles, predicates
services/api-node/lib/invitation-routes.mjs  GET /api/invitations/:id
                                             GET /api/invitations/:id/guests
                                             GET /api/invitations/:id/rsvps
                                             GET /api/invitations/:id/versions
                                             GET /api/invitations/:id/versions/:version
                                             GET /api/trash
services/api-node/test/invitation-authz.test.mjs
tools/invitation-read-parity.py              16-case cross-backend proof
```

These are the editor's first load, the guests/RSVP dashboards' first read, the version timeline and the owner's trash
list. Three behaviours are
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
| owner / collaborator versions | 200 | 200 |
| stranger / unauthenticated versions | 404 / 401 | 404 / 401 |
| version by number / by publication id | 200 | 200 |
| auto snapshot by id | 200 | 200 |
| missing version | 404 | 404 |
| unauthenticated trash | 401 | 401 |
| owner trash (titled + untitled) | 200 | 200 |
| stranger trash (empty) | 200 (`[]`) | 200 (`[]`) |

**INVITATION READ PARITY 27/27 identical, 0 failing.** Service suite **42 passed**.

## Not done, and why

- **Version writes and restore** — `create_snapshot`, `capture_auto_snapshot`, `_prune` and
  `restore_version` stay on Python. The port covers only the two reads; writes need the
  snapshot-state comparison Rule 8 requires.
- **Every write** (archive, slug, guest add, RSVP update/delete) — Phase D writes need snapshot-based
  comparison (Rule 8), not a response diff, and RSVP is the load-test target. They stay Python.
- **S9 (auth) is owner-gated by D2, not by native-code availability.** An earlier note here claimed
  every Node Argon2id implementation is a native addon; that is false (pure-JS and WASM packages
  exist). The gate is the dependency policy itself. `docs/NEXT-WORK.md` §"Decisions taken
  2026-11-14" records the owner answer verbatim: **"Approved and used at S2: `fastify@5.12.8` only
  (closure pinned by `services/api-node/package-lock.json`); each package listed at S2 and installed
  with `npm ci --ignore-scripts` into the Node service's own `package.json`/lockfile."** The plan's
  P3 requires an **"Owner-written override of "never add a dependency" (D2), listing each package
  and why."** No Argon2 package — native or WASM — is listed, so adding either would breach D2
  regardless of how it is compiled. S9 therefore needs a written D2 extension naming the package;
  it is not something code can settle.
- **Traffic ramp and p95** — deployment steps; P1 still has no baseline.
