# Hosted demo (A-4, D-16)

A throwaway, demo-data-only instance the owner can open from a phone. It is
**not** a production deployment: no real guest data, no billing keys, no
scanner, no `data/` copy, admin unreachable, dev auth tokens unset.

## What is here

| File | Purpose |
|---|---|
| `seed-demo.py` | Idempotent seed: one verified demo account, three published invitations from the shipped 36-template pack (`wd-royal-maroon-gold`, `bd-first-pastel`, `biz-corporate-gala`), placeholder content only. |
| `README.md` | This file. |

The seed uses the application's own schema pass, password hashing, document
validator and personal-workspace helper, so the rows it writes are the rows the
server writes. It reads nothing from `artifacts/` (a clean checkout does not
have it) and changes one thing in each pack document: RSVP is switched on,
because the demo must accept an RSVP.

Idempotency: an existing account is left in place (only `email_verified` is
forced to 1); an existing `demo-<template-id>` invitation is skipped. Running it
on every boot is therefore safe, which matters because a free host may have an
ephemeral disk.

## Local demo (works today)

From a **clean worktree of the committed HEAD** — never the dirty tree:

```bash
# 1. one-time worktree
git worktree add ../einvite-demo <commit>

# 2. data directory on the same machine, outside the repository
mkdir -p ~/einvite-demo-data

# 3. seed (password is read from the environment and never printed)
cd ../einvite-demo
EINVITE_DATA_DIR=~/einvite-demo-data \
EINVITE_DEMO_PASSWORD='<throwaway-password>' \
EINVITE_ALLOW_NO_SCANNER=1 \
python3 deploy/demo/seed-demo.py

# 4. serve (waitress lives in the main checkout's .venv)
EINVITE_DATA_DIR=~/einvite-demo-data \
EINVITE_ALLOW_NO_SCANNER=1 \
../einvite-platform/.venv/bin/python src/python/serve.py --host 127.0.0.1 --port 8941
```

Open <http://127.0.0.1:8941/>. Sign in as `demo@einvite.test` with the password
you generated. The three invitations are published at
`/i/demo-wd-royal-maroon-gold`, `/i/demo-bd-first-pastel` and
`/i/demo-biz-corporate-gala`.

### Redeploy (refresh the local demo to a new commit)

```bash
git -C ../einvite-demo checkout <new-commit>
EINVITE_DATA_DIR=~/einvite-demo-data EINVITE_DEMO_PASSWORD='<same password>' \
EINVITE_ALLOW_NO_SCANNER=1 python3 ../einvite-demo/deploy/demo/seed-demo.py
```

Restart the server process afterwards. The seed is idempotent, so the data
survives the refresh; delete `~/einvite-demo-data` to start from an empty demo.

## Public hosting: not deployed

The documented free host for this repository is the Render Blueprint
(`render.yaml`, free tier: sleeps after 15 min idle, ~30 s cold start). Deploying
it needs the owner's GitHub-connected Render account and a push, so it is
recorded as a `BLOCKER:` line in `artifacts/next-work/HANDOFF.md` instead of
being done unasked. Freebuff's own hosting cannot serve this app: it runs
Cloudflare Workers + static assets, and this backend needs Python (`serve.py`,
Waitress, SQLite/Postgres).

If that blocker clears, the start command is:

```bash
EINVITE_DEMO_PASSWORD='<throwaway-password>' python3 deploy/demo/seed-demo.py && cd src/python && python serve.py --host 0.0.0.0 --port $PORT
```

The seed script itself needs no third-party package; only `serve.py` needs
`waitress`, which the host installs from `docs/requirements-production.txt`.

Environment for a public demo (from `FREEBUFF-ANSWERS-2026-10-28.md` Q6, D-16):

```
EINVITE_PRODUCTION=1
EINVITE_PUBLIC_BASE_URL=https://<host>
EINVITE_ALLOWED_HOSTS=<host>
EINVITE_COOKIE_SECURE=1
EINVITE_REQUIRE_VERIFIED_EMAIL=1
EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP=0
EINVITE_DEV_AUTH_TOKENS=0
EINVITE_REQUIRE_MALWARE_SCAN=0
EINVITE_ALLOW_NO_SCANNER=1
EINVITE_REQUIRE_DURABLE_SERVICES=0
EINVITE_ADMIN_IP_ALLOWLIST=<operator IP>/32
EINVITE_SECRET_KEY=<generated>
EINVITE_UPLOAD_SIGNING_SECRET=<generated, 32+ chars>
EINVITE_MEDIA_SIGNING_SECRET=<generated, 32+ chars, distinct>
EINVITE_GUEST_TOKEN_SECRET=<generated, 32+ chars, distinct>
EINVITE_DEMO_PASSWORD=<generated, never committed>
```

No billing keys are set, so the plans page is expected to be inert on the demo.
Destroy the host and its disk when the review period ends.
