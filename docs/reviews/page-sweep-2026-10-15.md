# Page sweep — all 16 routes, signed out and signed in (2026-10-15)

Run against a local dev server (`src/python/server.py`, loopback, throwaway `EINVITE_DATA_DIR`,
`EINVITE_ALLOW_NO_SCANNER=1`), headless Chromium via `tools/page-errors.mjs`, viewport 1366×900.
Signed in as a seeded `super_admin` account. Instrument: `tools/page-errors.mjs --all`
and `tools/page-errors.mjs --all --as=<email>:<password>`.

## Result

| Pass | Pages | Console errors | non-2xx | Exit |
|---|---|---|---|---|
| Signed out | 16/16 loaded | 0 | 0 | 0 |
| Signed in (final) | 16/16 loaded | 0 | 0 | 0 |
| Signed in (first run, before the fixes below) | 16/16 loaded | 2 | 1 | 1 |

The first signed-in run is the reason this report exists: it found two defects the signed-out
sweep cannot see, because both live on the server-answered half of a page.

---

## ISSUE 1 — `checkin.html` requested an invitation that does not exist

**Severity**: low (a user-visible wrong message, plus a request that cannot succeed)
**Page**: `/checkin.html`, signed in, with no invitation selected or remembered

### What happened

The page loaded, then showed *"Could not load this guest list: …"* over a failed request:

```
404 /api/invitations/
```

The URL ends in a bare `/` — the invitation id was the empty string. `src/js/checkin.js` resolved
its id with `EInviteContext.getInvitationId({allowRemembered:false}) || getInvitationId() || ''`
and then built `${encodeURIComponent(inviteId)}` into the path unconditionally, so the empty case
was sent to the server instead of being handled locally. This is the class of defect **A1**
established a rule for (refuse to send a request that cannot succeed) on the signed-out path; this
was the same defect on a different trigger — a missing invitation rather than a missing session.

The sibling invitation-scoped pages already guard it: `analytics.js` renders an empty state,
`materials.js` refuses with a message, `guests.js` falls back to a local id. `checkin.js` was the
one that asked anyway.

### Fix

`src/js/checkin.js` — a guard first in `load()`, so a missing invitation reads as a missing
invitation and never as a missing server, plus the empty state in `render()` so a language switch
(a re-render) cannot replace the message with "No matching guests."

The new string uses this file's existing `_txt(en, km)` convention with the English text in both
slots, like every other string in the file. **The Khmer for it still needs native review** —
CONTRIBUTING §4 forbids inventing Khmer, and the two near-matching rows in
`docs/i18n/TRANSLATIONS.csv` are scoped to polls and sign-up sheets ("…to manage its polls"), so
reusing them here would put the wrong words on screen.

### Evidence

| | |
|---|---|
| Before | `checkin.html: consoleErrors=1 non2xx=1` → `404 /api/invitations/` |
| After | `checkin.html: consoleErrors=0 non2xx=0` |
| Rebuild | `python3 build.py all` exit 0; `build.py all --check` exit 0; the string is present in both `src/js/bundle-checkin-v15.js` and the served mirror `src/python/bundle-checkin-v15.js` |

---

## ISSUE 2 — the signed-in dashboard never reached network idle, and downloaded 28 KB it discarded

**Severity**: low (a wasted 28 KB request per cold dashboard load; it also made the smoke gate
unusable on that page, which is how it was found)
**Page**: `/dashboard.html`, signed in

### What happened

`dashboard.html` was reported as `nav: Navigation timeout of 40000 ms exceeded` — the same channel
as a page that throws, so the gate could not distinguish "broken" from "never settles".

The page issues `/api/invitations` **twice**, and Puppeteer shows a CDP terminal event for only the
first, so counting requests does not explain the stall. `tools/dashboard-network-idle.mjs` varies
one thing instead: `dashboard-polish.js` returns early when its local-first key
(`sovan-multi-invites-v1`) is present, so seeding it removes exactly one request.

| `seedLocal` | `/api/invitations` requests | `networkidle0` |
|---|---|---|
| `false` | 2 | **timeout** (25 s) |
| `true` | 1 | settled |

Cause: the probe fetched the list and never read the response body — it only inspects
`response.ok`. An unconsumed body keeps the request in flight, so the page never goes idle and the
28 KB payload is transferred for nothing.

The server was never at fault: `GET /api/invitations` answers **200 in 6–10 ms** (28 406 bytes) to
a signed-in `curl`, and from inside the page the request completes in 53 ms.

### Fix

`src/js/dashboard-polish.js` — cancel the response body in the probe's `.then()`, which releases
the stream and leaves the probe's one job (does the server answer?) intact.

### Evidence

Same instrument, same command, after a rebuild:

| `seedLocal` | requests | `networkidle0` |
|---|---|---|
| `false` | 2 | settled |
| `true` | 1 | settled |

`EXIT=0`. The full signed-in sweep then reports `dashboard.html: consoleErrors=0 non2xx=0`.

---

## Instrument change — a signed-in sweep

`tools/page-errors.mjs` gained `--as=email:password`. A signed-out sweep cannot see the half of
each page that only the server answers for a session: `dashboard.html` renders its empty shell with
no console error, so the cheap gate stays green over a broken signed-in route. Both defects above
were found within a minute of adding the flag and were invisible without it.

The flag logs in from a page already on `BASE_URL`, so the request carries the origin and session
cookie the app expects, and it exits 2 rather than reporting a "signed-in" pass that was not signed
in.

## How to re-run

```bash
# dev server on a throwaway data dir, then:
BASE_URL=http://127.0.0.1:8395 node tools/page-errors.mjs --all
BASE_URL=http://127.0.0.1:8395 node tools/page-errors.mjs --all --as=<email>:<password>
BASE_URL=http://127.0.0.1:8395 node tools/dashboard-network-idle.mjs --as=<email>:<password>
```

## Limitations of this pass

- **One viewport (1366×900), headless only.** No responsive or mobile pass; `tools/ui-sweep.mjs`
  (the 80-row layout pass) and the click pass were not run, so this says nothing about layout,
  overflow or dead controls.
- **Load and error reporting only.** The pages were proven to load and to answer without error, not
  to be *correct*: no flow was driven end to end across the 16 routes.
- **The seven Playwright-dependent modules did not run** (playwright is not installed here; see
  `tests/conftest.py`). Nothing here covers them.
- **Both defects were found with a freshly seeded account that owns invitations but no stored
  client state.** The dashboard probe's local-first early return means a returning browser never
  made the second request, which is why the stall needed a cold context to appear.
- The new `checkin.js` string is English in both language slots pending native Khmer review.

## Repo state

`python3 build.py all` exit 0 · `build.py all --check` exit 0 · `make check` exit 0 ·
`python3 -m pytest tests/` 86 passed (exit 0) · `scripts/check-bilingual-consistency.py` exit 0.
