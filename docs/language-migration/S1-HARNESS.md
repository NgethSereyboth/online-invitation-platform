# S1 — round-trip equivalence harness

**Date:** 2026-11-14 · **Plan:** `language-optimization-plan-v3.1.md` §5 (S1), §8 (Class A)
**Status:** S1 first cut **built and self-verified**. This is the artefact the plan calls
"the single highest-value artifact", and the one thing that survives a decision to stop.

| File | Role |
|---|---|
| `tools/parity-harness.py` | the harness: record, replay, compare, self-check |
| `tools/route-inventory.py` | seeds the corpus from the frozen P2 inventory |
| `tests/v14_test_utils.py` | base-URL switch (`EINVITE_TEST_BASE_URL`) |
| `docs/language-migration/ROUTE-INVENTORY.md` | the frozen route universe |

---

## 1. What it does

```
--record BASE --corpus F     capture responses from a backend
--replay BASE --corpus F     re-send the corpus and diff
--compare A B                record from A, replay to B  ← the shadow tee (R3)
--self-check                 boot two fresh Python instances; A → B must be 0 diffs
```

The corpus is a **file**, not a packet capture, so shadow proof does not depend on live
traffic volume — that is the plan's R4 alternative to a 72-hour window.

Each entry stores the request and a **normalised** response: status, nine compared headers,
and the body. Comparison is exact after normalisation; a diff prints the first differing
offset with 40 bytes of context on each side, so a 200 KB page diff is still readable.

### Modes in practice at cutover

```bash
# 1. record the Python baseline once
.venv/bin/python tools/parity-harness.py --record http://127.0.0.1:4175 --corpus baseline.json

# 2. when the Node route is up, diff it against the corpus (no Python writes involved)
.venv/bin/python tools/parity-harness.py --replay http://127.0.0.1:3000 --corpus baseline.json

# 3. or run both live, Python as the reference
.venv/bin/python tools/parity-harness.py --compare http://127.0.0.1:4175 http://127.0.0.1:3000
```

Exit code is **1 on any diff**, so it can be a gate, not a report.

---

## 2. Self-check result (the S1 exit criterion)

```
CORPUS 96 GET requests · 16 routes not exercisable
INSTANCES A=http://127.0.0.1:45717 B=http://127.0.0.1:50001
UNEXERCISED GET /api/invitations/probe/campaigns/probe/deliveries (transport)
PARITY 95/96 identical · 0 diff · 1 skipped
```

Two independently booted Python instances agree on **95 of 96** exercised GET requests.
Two diffs had to be understood before they could be normalised, and both were instance
facts rather than behaviour:

- `GET /api/health` — `uptimeSeconds` (11 vs 5),
- `GET /api/health/ready` — `localRoot` pointing at each instance's own temp directory.

Plus one that is *not* normalised but was already recurring: the CSP `nonce-…` in the
header and `nonce="…"` in markup is minted per boot.

Normalisation rules, all deliberate (`NORMALISERS` in the harness): CSP nonce (both forms),
loopback host:port, UUID, epoch-ms, ISO timestamp, ≥32-hex strings, `uptimeSeconds`,
temp data directories. **Nothing else.** A rule added to silence a real difference would
defeat the harness, so additions need a stated reason like the two above.

---

## 3. Known gaps — recorded, not hidden

The plan requires that every route the harness cannot exercise be a documented gap. Today:

| Gap | Count / detail | Why | Where it belongs |
|---|---|---|---|
| Non-GET verbs | POST 144, PUT 36, DELETE 22 declarations never sent | Replaying a write twice mutates one database — the plan's Rule 8 forbids exactly that. Writes need a per-replay DB snapshot (SQLite file copy / PG template). | S11 (write-heavy domain) |
| Artefact routes | 16 route families skipped: media, images, social cards, exports, backups, `.ics`, `qr` | They generate or stream files; a probe would write artefacts into a data dir or a browser cache. | S3 / S13, with a fixture data dir |
| Authenticated corpus | 0 requests | A session created on instance A does not exist on B, so a cross-instance diff would report 401s that mean nothing. Needs the shared session store. | S6 |
| Unexercised route | `GET /api/invitations/<id>/campaigns/<id>/deliveries` | Transport error/timeout on the probe sample; it is also the one route that timed out in the P2 probe. | next harness pass |
| Static fixtures | `.html` passthrough served, not diffed separately | Product pages only, per P2's fixture decision. | S3 |

The **13 unexercised routes** are listed on every run (`not exercisable: …`), so the gap
list cannot drift away from the corpus.

---

## 4. The base-URL switch (plan C1)

The plan's C1 correction says the contract-test base-URL switch is *not free*: the spawner
must learn to target another backend. That is now in one place:

```python
# tests/v14_test_utils.py — fresh_server()
external = os.environ.get('EINVITE_TEST_BASE_URL', '').strip().rstrip('/')
if external:
    yield None, external, None
    return
```

- Unset (the old behaviour): spawn `src/python/server.py` on a free port with a temp data
  dir, exactly as before, including the FB-09 port-race retry.
- Set: spawn nothing, create no data dir, yield `(None, base, None)`. The caller owns the
  lifecycle.

`tests/conftest.py::server_url` goes through `app_server` (= `fresh_server`), so every Class A
test that uses the fixture becomes backend-agnostic by setting one variable:

```bash
EINVITE_TEST_BASE_URL=http://127.0.0.1:3000 .venv/bin/python -m pytest tests/api_contract_test.py
```

### 4.1 Enumeration of the tests the switch does not reach

The list is now generated, not guessed: `tools/class-a-coverage.py` classifies all **327**
files under `tests/` and writes [`CLASS-A-COVERAGE.md`](CLASS-A-COVERAGE.md).

| Class | Files | Meaning |
|---|---|---|
| `covered` | **153** | `server_url` / `app_server` / `fresh_server`, or a pure HTTP client — the switch reaches these today |
| `needs-convert` | **35** | inline `Popen([sys.executable, 'server.py', …])` — invisible to the switch |
| `not-backend` | 119 | browser runners and other non-backend processes (Class B) |
| `not-portable` | 20 | import the backend in-process — Class C, deliberately stays Python |
| `external` | 0 | nothing hard-codes `127.0.0.1:4175` |

**None of the 35 was converted in this pass, and that is deliberate.** Each one builds its
own environment (data dir, port, seeding) and asserts against it; a mechanical rewrite of 35
contract tests that cannot all be re-run in one pass would trade a real risk for a nominal
number. They are documented instead, which is what the plan's S1 exit requires.

The conversion recipe, to be applied one file at a time with that file's tests run afterwards:

1. the test's local `server()` helper already builds `env` with `EINVITE_DATA_DIR` and any
   flags — pass that same dict as `fresh_server(extra_env=env)`;
2. replace the `Popen` + `wait_http` pair with the context manager, which already retries the
   FB-09 port race and kills the process group on exit;
3. use the yielded `base` for every request (no `f'http://127.0.0.1:{port}'` reconstruction);
4. run the file with `EINVITE_TEST_BASE_URL` unset (spawn path) **and** set to a live origin
   (switch path) — both must behave, or the conversion is not finished.

Until a file gets that treatment it is excluded from any `--compare` wave, and the ledger
says so on every run rather than leaving the cutover looking more complete than it is.

One near-miss worth recording: `tests/security_admin_ip_allowlist_test.py` matched a search
for the owner's port, but the hit was `port = 14175`, a fixed test port. It is a
`needs-convert` file for the spawn reason only, and the `external` class is genuinely empty.
Checking that instead of reporting it was the difference between a finding and a wrong claim.

---

## 5. Why this is additive and revertible

No production code, no dependency, no lockfile, no gate, no budget. The two test-helper
edits only add a branch that is inert unless an environment variable is set. Deleting
`tools/parity-harness.py` restores the previous state entirely.

**Verified this pass:** `--self-check` → 95/96 identical, 0 diff, exit 0; the switch
short-circuits in 0.11 s with `process=None`; `python3 build.py all --check` and
`compileall` on both tools (recorded in `docs/HISTORY.md`).
