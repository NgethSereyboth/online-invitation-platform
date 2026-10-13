# Bulk guest import and per-guest invitation links — implementation report

Authority: [`docs/reviews/bulk-guest-import-research.md`](bulk-guest-import-research.md)
(the design authority for this pass; every §-reference below is to that document).
House standard for evidence: [`docs/reviews/instrument-repair-report.md`](instrument-repair-report.md).

Base: `842038b` — the research pass's HEAD ("docs: record the commit, push and deploy
state the report promised"), verified with `git log --oneline -5` before the first edit.

Result: nine commits, `842038b..bb5e23f` (eight goals plus the Goal 4 regression fix,
`git rev-list --count 842038b..bb5e23f` = 9), pushed to `origin/main`, deployed to Render.
The feature is implemented end to end and every gate in the brief is green.

---

## 1. Summary

**Shipped.** `url` shape `/i/<project-slug>/<guest-code>`; a frozen per-guest code
(`clean_slug(name)` for Latin names, an opaque 6-character code from
`23456789abcdefghjkmnpqrstuvwxyz` otherwise); Excel/CSV import with BOM sniffing and a
row preview; the mapping screen and the "freeze and generate" action; a re-import key;
the `guest.name` content binding in the editor and its resolution when a served
document belongs to a guest; per-guest `og:title`/`og:description`/`og:image`; a
per-guest social card with its own cache file and a background warm job; the batch
share UI; and a pytest module that runs the whole thing against a real server.

**Also fixed, because the feature sits on them (Goal 0).** `clean_slug` no longer
returns the shared `our-invitation` constant for a Khmer-only title; a Khmer face is
vendored in the repository with a startup verdict; the social-card URL carries the
publication version.

**Not done, deliberately.** No bulk write endpoint (the per-row path is enough for
hundreds of guests, §5.7 phase A); no "send all" delivery (§5.5 — channels need
per-host credentials, and the requirement is that the link itself is sufficient); no
Romanization of Khmer names (§3.1 — four official systems disagree, so the code is
opaque instead).

**Two defects were found by verification, not by reading the code**, and both are
fixed in-tree with the measurement recorded below: a temporal-dead-zone crash that
stopped the guest list rendering at all (Goal 6), and a dispatcher regression that a
security test caught (the fix commit `bb5e23f`).

---

## 2. Per-phase sections

### Goal 0 — pull-forward fixes (§2.6, §5.4, §3.7)

Commit `0c68cf6` — 11 files, +560/−17.

**0a. `clean_slug`'s Khmer collapse.** `clean_slug(value, fallback=None)` now returns
`short_code(6)` for an input with no `[a-z0-9-]` character left, unless the caller
needs determinism (`fallback`). Tenant keys keep their deterministic fallback; the
invitation slug does not.

Raw output, `python3 tools/khmer-slug-probe.py`:

```
KHMER_SLUG_PROBE corpus=docs/i18n/TRANSLATIONS.csv tested=8 collapsed=0/8 fallback='our-invitation'

input (truncated to 16 chars)  ->  slug
ការគ្រប់គ្រង                   ->  'be9b5x'
អ្នកប្រើ                       ->  'm7f3cw'
ពុម្ពអត្ថបទ                    ->  'mnryet'
ការអញ្ជើញ                      ->  '88srg2'
ទងជម្រើសមុខងារ                 ->  'w2zhas'
ស្វែងរកទិដ្ឋភាពន               ->  'm7mb52'
គ្រប់គ្រង                      ->  'berqru'
សម្ភារែ                        ->  'jb77wk'
Sok Dara                       ->  'sok-dara'   (ASCII control)
```

8 of 8 collapsed before this change; 0 of 8 now, with the ASCII control unchanged. The
codes are drawn per run and so differ between invocations — `collapsed=0/8` and the ASCII
control are the stable assertions; the codes above are the ones that run printed.

**0b. The Khmer font.** Option (i) from the brief: the face is vendored at
`vendor/noto-khmer/` (SIL OFL 1.1, the licence already vendored at
`licenses/fonts/Noto-OFL-1.1.txt`) with `README.md` and `INTEGRITY.txt`, and its path is
the first candidate in `khmer_font_candidates()`. Startup reports the verdict using the
same `_khmer_font_metadata` that validates uploaded fonts:

```
KHMER_FONT_STATUS ok resolved=/media/ngethsereyboth/LocalDisk/eInvite/einvite-platform/vendor/noto-khmer/NotoSansKhmer-Regular.ttf vendored=True support=ready coreCoverage=100.0 shaping=True
```

The failure branch is `KHMER_FONT_STATUS WARN resolved=… reason=… — personalized Khmer
guest names will render as empty boxes. Vendor a Khmer face under …`. It was **not**
exercised on this host: moving the mirror copy aside still resolves the checkout copy
(measured — same line, `vendored=True`), and hiding the machine's
`/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf` as well needs administrator
rights, which this pass did not take. Reported as a limitation, not as a pass.

**0c. Versioned card URL.** `serve_public` now advertises
`/api/public/<slug>/social-card-v<version>.<fmt>`; the unversioned path still resolves,
so a preview already sitting in a chat keeps working. The route matched both forms
before Goal 4 added the guest segment.

### Goal 1 — phase A: import (§5.7 phase A, risk 2)

Commit `da277b5` — 18 files, +834/−12.

`src/js/guests.js` gained `readImportFile` (Excel through the vendored SheetJS build,
`vendor/sheetjs/xlsx.mini.min.js`, loaded lazily so the guests route keeps its page
budget), `decodeImportText` (UTF-8 with/without BOM, UTF-16LE, UTF-16BE; an undecodable
byte stream is refused rather than imported as mojibake), `importFindings` (blank names
by sheet row number, duplicate names, "keep both" as the default) and the preview
dialog: detected header, chosen name column, first five and last two rows, the counts
of what will be added versus updated, and the freezer action. Import writes through the
existing per-row `POST /api/invitations/<id>/guests`; no bulk endpoint was added.

Raw output, the real file driven headlessly in Node (`IMPORT_HARNESS_PASSED 13 checks`):

```
PASS csv utf-8 (no BOM) decodes — rows=11 source=CSV · UTF-8
PASS csv utf-8 Khmer round-trips — "សុខ ដារា"
PASS csv utf-8 with BOM — CSV · UTF-8 with BOM
PASS csv utf-16le with BOM — CSV · UTF-16LE with BOM "សុខ ដារា"
PASS csv utf-16be with BOM — CSV · UTF-16BE with BOM "សុខ ដារា"
PASS undecodable CSV is refused — decodeFailure=true
PASS quoted cells parse — [["Name","Phone"],["Sok, Dara","012"],["Ly \"Meng\"","013"]]
PASS header detected, header row skipped — {"header":true,"columns":2,"entries":5,"blank":[4],"duplicates":["Sok Dara"],"keepBoth":5,"skipDupes":4}
PASS blank name reported by sheet row number — [4]
PASS duplicate name reported — ["Sok Dara"]
PASS keep both is the default — keepBoth=5
PASS skip-later-duplicates removes one row — skipDupes=4
PASS headerless sheet keeps all rows — {"header":false,"columns":2,"entries":2,"blank":[],"duplicates":[],"keepBoth":2,"skipDupes":2}
PASS xlsx reads through readImportFile — rows=11 source=Excel
PASS xlsx Khmer names round-trip — ["សុខ ដារា","ហេង សុវណ្ណ"]
PASS xlsx header detected and importable — {"header":true,"columns":2,"entries":10,"blank":[],"duplicates":[],"keepBoth":10,"skipDupes":10}
```

The dialog was additionally driven in Chromium on the real page (the file input, the
preview, the Khmer names rendering). 20 guests imported over HTTP and compared in SQL
round-trip byte-for-byte — the same check now lives permanently in the end-to-end test
(§4 below), which asserts the ten names through SQLite rather than the UI.

**Autonomous decision.** SheetJS 0.18.5's `xlsx.mini.min.js` reader was confirmed to
parse `.xlsx` in a browser bundle before vendoring (the pass's own web check of the
SheetJS browser-usage documentation); the licence and provenance are recorded in
`vendor/sheetjs/README.md`.

### Goal 2 — phase C: mapping screen and slug generation (§5.2, §5.6, §5.7 phase C)

Commit `25ab2e1` — 12 files, +437/−34.

Schema (`guests.slug TEXT NOT NULL DEFAULT ''` plus
`CREATE UNIQUE INDEX IF NOT EXISTS idx_guests_slug ON guests(invitation_id, slug)`) in
both the SQLite path and the PostgreSQL path, with the same contract; `short_code(6)`
and `guest_slug(name, taken)` next to `clean_slug`, using the alphabet that excludes
`0 1 i l o` (§4.1); `POST /api/invitations/<id>/guests/freeze`; the mapping screen with
per-row edit, "regenerate all" and "freeze and generate"; and the re-import key
(`(invitation_id, lower(name))`, match → update, no match → add, never silent merge).
`update_guest_details` keeps a frozen code (`COALESCE(?, slug)`), and the mapper's
payload deliberately omits `slug`, so a re-import cannot rename a shared link.

Verified over HTTP and in the browser (mapping screen screenshot, `queued: 3` in the
freeze response), plus the migration proof in §3.

### Goal 3 — phase B: editor variable binding (§2.2, §5.3)

Commit `9de0d5b` — 13 files, +140/−24.

`src/js/template-bindings-v25.js`: `resolve()` learns `guest.<key>`; `refresh()`
normalises a guest-bound object to its placeholder (`{{name}}`) instead of a stale
resolved name; the dialog gained a "Selected object" control whose options are "No
binding", "Guest name" (`guest.name`), `schedule`, `heroImage` and the document's own
`fields.*`; `applyBinding` writes the binding and the placeholder in one labelled
transaction; `setGuestRow` lets a caller resolve guest bindings outside the editor.

`src/python/server.py`: `merge_fields` (the Python twin of `canva-scale-v31.js`'s
`mergeFields` — same `/\{\{\s*([\w.-]+)\s*\}\}/` token, a missing key becomes `''`) and
`apply_guest_bindings`, called from `get_public` when the request's `?g=` token
identifies a guest, over the same two canvas groups the editor's inspector walks.

Raw output, the real module in Node:

```
ALL_BINDING_CHECKS_PASSED
PASS  guest.name row is a placeholder, not outdated
PASS  refresh rewrites a guest binding to its placeholder      actual="{{name}}"
PASS  refresh still resolves fields.* normally                 actual="Sophea & Dara"
PASS  applying Guest name sets the binding / writes the placeholder
PASS  resolve uses the guest row for guest.name                actual="សុភា ចាន់"
PASS  resolve handles any guest key                            actual="7"
PASS  without a guest row the binding resolves to null
```

Raw output, the real editor in Chromium (`/invitations/<id>/editor`):

```
{"version":25.3,"apply":"function","setGuestRow":"function"}
dialog select: "=No binding","guest.name=Guest name","schedule=schedule","heroImage=heroImage","fields.names=…"
after choosing Guest name: {"binding":"guest.name","html":"{{name}}","stageText":"{{name}}"}
dialog row: "current :: Filled in per guest when that guest opens their link."
after a page reload:       {"ready":"true","binding":"guest.name","html":"{{name}}","dom":"guest.name"}
```

Raw output, the served document (`GET /api/public/<slug>?g=<token>`):

```
guest name in the document          : 'សុភា ចាន់'
guest table binding resolved        : 'Table 7'
fields.* binding untouched          : 'Sophea &amp; Dara'
unbound object untouched            : 'Welcome'
--- without a guest token ---
placeholder preserved               : '{{name}}'
no guest leaked in the payload      : True
--- a different guest gets their own value ---
second guest name                   : 'Dara Sok'
first guest name not leaked         : True
```

**Autonomous decision, and a defect fixed because of it.** The measurement above was
first run against the *saved* document and found the binding gone after a reload:
`capture()` in `src/js/app.js` rebuilds every object from the element's `dataset`, and
`apply()` never put `contentBinding` there — so a binding could not survive a page load
and could never be published. Pre-existing, and the same reason adaptive-template
bindings are re-applied on load rather than persisted. `apply()` now writes
`contentBinding`, `bindingDetached` and `bindingLastSyncedAt` to the dataset and
`capture()` reads them back; the reload line above is the proof. This is the one place
this pass touched a file the brief did not name, and the reason is in the commit.

### Goal 4 — phase E: per-guest OG tags (§5.3)

Commit `06437ef` — 1 file, +25/−5.

The `/i/` dispatcher reads two segments; `serve_public(self, slug, guest_slug=None)`
looks the guest up by `(invitation_id, slug)` under the existing published-and-not-
password-protected gate; `title` becomes `guestTitleTemplate` or `"<name> · <couple>"`
and `description` becomes `guestDescriptionTemplate` or the document's message; the
image URL gains both the guest segment and the version.

Raw output:

```
guest codes: 7nwja6 dara-sok
--- guest page og tags ---
  og:title: អញ្ជើញ សុភា ចាន់
  og:description: សុភា ចាន់ — Sophea &amp; Dara
  og:image: http://127.0.0.1:43001/api/public/og-check/7nwja6/social-card-v1791818083114.png
  guest name in og:title : True
  template title applied : True
  template description   : True
  versioned image URL    : True
--- project page (no guest) ---
  og:title: Sophea &amp; Dara
  unchanged title        : True
  no guest segment in img: True
--- wrong guest slug (falls through) ---
  same as project page   : True
trailing slash treated as project page: True
--- escaping ---
  raw <script> not present: True
  escaped in og:title    : True
```

**The regression this phase caused, and its fix (commit `bb5e23f`).** The first
dispatcher version split the remainder on `/` unconditionally, so a slug containing a
slash was truncated before it reached `serve_public`.
`tests/security_reflected_injection_test.py::test_reflected_injection_in_serve_public`
failed on it (`expected escaped slug … to appear at least twice … found 0 time(s)`),
which is what the full-suite gate is for. The segment is now a guest code only when
`safe_guest_code` accepts it — the same validator the card cache path uses — and
otherwise the whole remainder is the slug, exactly as before the guest segment existed.

### Goal 5 — phase F: per-guest OG image (§5.4)

Commit `9aa22a8` — 2 files, +113/−5.

`render_social_card_png_bytes(..., guest_name=None)` draws one extra line — the name in
the card's accent colour, under the couple's names, so the detail block is pushed down
instead of overlapped — with the same font resolution as the title, which after Goal 0b
is the vendored Khmer face. `social_cache_path(..., guest_slug=None)` gives each guest
their own file; `safe_guest_code` validates the one request-supplied path component
before it becomes a filename. `warm_guest_social_cards` renders the `og` card for every
guest (82 ms and 26 KB per card per §5.4; 300 guests ≈ 25 s and 7.8 MB, a 5,000-guest
import ≈ 7 minutes) and never runs in a request: `social.guest_warm` is a
`media_worker` job kind when `EINVITE_BACKGROUND_MEDIA=1` and a daemon thread otherwise,
triggered by publish and by freeze.

Raw output — warm through the freeze action, no request for any card:

```
after publish (guests already existed): []
freeze response: {'updated': 0, 'frozen': True, 'conflicts': [], 'queued': 3}
guest cards warmed in 0.5s without any request for them:
  67jept: ...-v1791816484149-67jept-og.png (30657 bytes)
  dara-sok: ...-v1791816484149-dara-sok-og.png (31247 bytes)
  9uwg6a: ...-v1791816484149-9uwg6a-og.png (29920 bytes)
```

Raw output — fetch, dimensions, and pixel proof that the name is in the image:

```
advertised image path: /api/public/card-check/92cagp/social-card-v1791816426852.png
fetched 30657 bytes
dimensions: (1200, 630)
guest card differs from the project card in 9102 pixels
two guests differ from each other in 5841 pixels
unknown code falls back to a real card, not a 404: True
unknown-code card equals the project card: True
cache after fetch: [... -92cagp-og.png, ...-dara-sok-og.png, ...-og.png, ...-square.png, ...-story.png]
```

And by eye, in Chromium (the guest card and the project card side by side):

> guest card: `YOU ARE INVITED` / `Sophea & Dara` / `សុភា និង ដារា` / **`សុភា ចាន់`** (accent
> colour) / `2027-02-14` / `Phnom Penh`
> project card: identical, without the guest line

The Khmer name renders as Khmer script, not boxes; the raw font verdict is in §2 Goal 0b.

### Goal 6 — phase D: batch share UI (§5.1, §5.5)

Commit `22a0375` — 14 files, +168/−24.

`guestUrl` builds `/i/<slug>/<code>?g=<token>`, falling back to `/i/<slug>?g=<token>`
when the guest has no code yet. A selection column, "Select all" and "Copy all links"
copy the **bare** URLs, one per line and without tokens. The guest-links dialog gained
Telegram / WhatsApp / Facebook per row, using the same URL shapes the public share panel
builds (`public-share-panel.js` is page-local and exports nothing, so the three formats
are mirrored in `guests.js` with a comment naming the source of truth), and the note
that a bare link on its own is what makes Telegram show the preview. No "send all".

Raw output, the real page in Chromium:

```
rows: 6, picks: 6, selectAll: true, copyBtn: true
after Select all: picks=6 all=6
copy all links: lines=6  first=http://127.0.0.1:47123/i/mgv55d/sok-dara
               last=http://127.0.0.1:47123/i/mgv55d/2mf6mb  allMatchSlug=true  noTokens=true
dialog: 6 rows × [Telegram, WhatsApp, Facebook]
note: "Send a bare link on its own: Telegram then shows the invitation preview, and any text beside it suppresses the card."
computed styles: .share-channels display=flex gap=8px, .guest-pick input width=18px
```

**The defect this found.** The first version declared the selection set in the link-code
section near the end of the file, while the wiring that reads it runs earlier; the
declaration is therefore in its temporal dead zone at that point. Chromium reported
`ReferenceError: Cannot access 'pickedGuests' before initialization` and **the guest
list did not render at all**. It now sits with the other module-level state at the top
of `guests.js`, and the reload line above is the measurement after the fix.

### Goal 7 — phase G: end-to-end test (§5.7 phase G)

Commit `3e91d39` — 1 file, +320.

`tests/bulk_guest_import_test.py`, two pytest tests, no network and no external service
(details and raw output in §4).

---

## 3. Schema migration — before and after

Before: `guests` had no `slug`; the page keyed a guest only by id and the shareable URL
was the project slug plus a 32-character `?g=` token.

After, additive and idempotent:

```sql
ALTER TABLE guests ADD COLUMN slug TEXT NOT NULL DEFAULT '';             -- only if missing
CREATE UNIQUE INDEX IF NOT EXISTS idx_guests_slug ON guests(invitation_id, slug);
```

Backfill visits rows in `(invitation_id, id)` order: `clean_slug(name)` when the name
yields one, otherwise `short_code(6)`, and a collision in the same invitation gets
`-2`, `-3`. Raw output on a hand-built legacy table (five rows, no `slug` column, three
of them sharing one name in one invitation):

```
LEGACY rows: 5 | has slug column: False
RUN 1: {'columnAdded': True, 'backfilled': 5, 'index': 'idx_guests_slug'}
    g1 inv-A 'Sok Dara' -> sok-dara
    g2 inv-A 'Sok Dara' -> sok-dara-2
    g3 inv-A 'សុខ ដារា' -> 2jfn8k
    g4 inv-B 'Sok Dara' -> sok-dara
    g5 inv-A 'Sok Dara' -> sok-dara-3
unique index present: True
RUN 2: {'columnAdded': False, 'backfilled': 0, 'index': 'idx_guests_slug'}
second run is a no-op: True
all slugs non-empty: True
per-invitation uniqueness holds: True
same name in one invitation gets -2/-3: ['sok-dara', 'sok-dara-2', 'sok-dara-3']
same name in another invitation keeps its own code: ['sok-dara']
after connect(): slug column True | empty slugs 0 | idx_guests_slug True
```

The second run is asserted byte-for-byte in the committed test
(`after_second == after_first`), together with the index refusing a duplicate
`(invitation_id, slug)` inside one invitation while accepting the same slug in another.
No row is deleted, no name changes, and the collision resolution is deterministic, so a
migration that fails cannot leave the table in a different shape than a successful one.

---

## 4. End-to-end test

```
$ .venv/bin/python -m pytest tests/bulk_guest_import_test.py -v
collected 2 items
tests/bulk_guest_import_test.py::test_bulk_import_end_to_end PASSED                       [ 50%]
tests/bulk_guest_import_test.py::test_guest_slug_migration_is_additive_and_idempotent PASSED [100%]
============================== 2 passed in 3.62s ===============================
```

`test_bulk_import_end_to_end` runs the brief's twelve steps against the real server
(`tests/v14_test_utils.app_server`, a temporary data directory, real SQLite) and real
HTTP: a Khmer-titled invitation whose slug is not `our-invitation`; ten imported guests
(five Latin, five Khmer) whose Latin names take readable codes and whose Khmer names all
match `^[23456789abcdefghjkmnpqrstuvwxyz]{6}$`; the names compared through SQL; the
freeze; the published per-guest page whose `og:title` carries that guest's name and
whose `og:image` carries the guest segment and the version; the 1200×630 card rendered
by the application's own Pillow path and written to the cache the test then reads from
disk; the project-card fallback for an unknown code; and a re-import that updates one
phone number, creates no row and keeps the frozen code.

Two notes on it. The card is fetched over HTTP rather than rendered in-process, because
the guests live in the server subprocess's database — that request *is* the
application's render path, and the test proves it synchronously by reading the cache
file afterwards. And the test needed a publish step that the brief's step list does not
name: `og:title` comes from the published document (§5.3 pattern A), so without it the
page correctly serves the generic fallback. The first run of the test failed on exactly
that and the fix is in the test, not in the application.

---

## 5. Verification set

Run after the last source change; each command's own exit status is reported.

| # | Command | Result |
|---|---------|--------|
| 1 | `python3 build.py all --check` | `exit=0`, `BUILD_OK editor bundles manifests mirror (check)` |
| 2 | `python3 tools/mirror-diff.py` | `0 drifted, 0 unmigrated, 0 orphans (19 named and exempt)` |
| 3 | `.venv/bin/python -m pytest tests/ -q` | `70 passed in 143.22s` — `pytest_exit=0` |
| 4 | `python3 tools/khmer-slug-probe.py` | `collapsed=0/8` (was 8/8); ASCII control `sok-dara` |
| 5 | `wc -c src/js/bundle-index-v15.js src/js/bundle-public-v15.js` | 1,136,779 / 1,420,000 and 251,960 / 260,000 — both under, 283,221 and 8,040 bytes of headroom |
| 6 | `!important` counts, `842038b` vs `HEAD`, per file | total 82,969 → 82,969 (whole tracked tree: `git archive <rev> \| tar -x -C /tmp/<rev> && grep -ro '!important' /tmp/<rev> \| wc -l`); CSS-only 81,731 → 81,731; files whose count increased: **NONE** |
| 7 | Migration idempotence | §3 — `RUN 2: {'columnAdded': False, 'backfilled': 0}`, second run a no-op |
| 8 | `pytest tests/bulk_guest_import_test.py -v` | 2 passed (§4) |
| 9 | `git status --short` | only this pass's files in the commits; the working tree holds only changes that were already there before the pass (`package.json`, `package-lock.json` and six untracked files from another session, left alone) |The whole set was re-run on 2026-10-13, after this report was first drafted, against an
unmodified tree at `bb5e23f` (the same tree the feature commits left), and every row above
reproduced: `build_exit=0`, `mirror_exit=0`, `pytest_exit=0` (`70 passed`), `collapsed=0/8`,
both bundles under budget, no file's `!important` count increased, 2 passed, and a clean
`git status` apart from the pre-existing entries.

Note on #3: the plain `python3 -m pytest` in the brief has no `pytest` module in this
environment (`/usr/bin/python3: No module named pytest`); the repository's virtualenv
does, so that is the interpreter used. #3 also caught the Goal 4 dispatcher regression
described above — the first run was `1 failed, 69 passed`, the final run is `70 passed`.

### What the pass changed, in files

```
44 files changed, 2565 insertions(+), 82 deletions(-)   (842038b..bb5e23f)
vendor/sheetjs/…                        vendor/noto-khmer/…
src/js/guests.js                        src/js/template-bindings-v25.js
src/js/app.js                           src/css/organized/guests-page.css
src/html/guests.html                    src/python/server.py
src/python/media_worker.py              tests/bulk_guest_import_test.py
docs/postgres_schema.sql                generated bundles and manifests
```

### Khmer strings

Every Khmer string in the new UI is from `docs/i18n/TRANSLATIONS.csv`:
`Select all → ជ្រើសទាំងអស់`, `Close → បិទ`, `Cancel → បោះបង់`. Everything else is left
with an empty Khmer slot (**KH_PENDING**, blank rather than invented):

1. `Copy all links`
2. `Select this guest for the link list` (checkbox label)
3. `There are no guest links to copy yet.`
4. `link(s) copied`
5. `Add 10 guest(s)` / `Import guests` dialog headings from phase A
6. `Found N rows, name column detected as '…'` and the headerless variant
7. `This CSV is neither UTF-8, UTF-16LE nor UTF-16BE. Export the guest list as .xlsx…`
8. `N row(s) have no name…`, `N duplicate name(s)…`, `Skip later duplicates…`
9. The mapping screen's `Guest links` paragraph, `Regenerate all`, `Freeze and generate`,
   `Guest link code`, `Generate a new code`, `N link(s) frozen`
10. `Send a bare link on its own: Telegram then shows the invitation preview, and any text
    beside it suppresses the card.`
11. The per-guest chat message `You are invited to <couple>. <url>` (EN only; the public
    share panel's message is EN-only for the same reason)

### Where the dev-only scripts went

The probes used while building live in `/tmp` and are deleted with the environment. The
two that carry real assertions were graduated into the repository and are not temporary:
the migration and end-to-end checks are `tests/bulk_guest_import_test.py`. Nothing was
added to `tools/`.

---

## 6. Push and Render

```
$ git push origin main
remote: GitHub found 6 vulnerabilities on …'s default branch (3 high, 2 moderate, 1 low). …
To https://github.com/NgethSereyboth/online-invitation-platform.git
   842038b..bb5e23f  main -> main
push_exit=0
```

Render: the service is a Web Service with `autoDeploy: true` (`render.yaml`), so the push
is the deploy trigger and no deploy hook was called.

```
$ curl -fsS https://einvite-platform.onrender.com/ -o /dev/null -w "%{http_code}\n"
200
$ curl -fsS https://einvite-platform.onrender.com/api/health -o /dev/null -w "%{http_code}\n"
200
$ curl -sS -w "\nstatus=%{http_code}\n" \
    https://einvite-platform.onrender.com/api/public/deploy-probe-none/abc123/social-card-v1.png
{"error": "Invitation not found"}
status=404
$ curl -sS -w "\nstatus=%{http_code}\n" \
    https://einvite-platform.onrender.com/api/public/zzz/unmatched-deploy-probe
{"error": "Published invitation not found"}
status=404
$ curl -sS -o /dev/null -w "guest_page=%{http_code}\n" \
    https://einvite-platform.onrender.com/i/deploy-probe-slug/abc123
guest_page=200
```

The `curl` to `/` answered `200` here only on the retry: the first probe of the session
timed out at 25 s with no bytes, which is the free-tier instance waking from idle rather
than a failure — the three attempts after it returned `200` in ~0.44 s each.

Read carefully: `/` and `/api/health` returning 200 says the service is live, but it says
nothing about *which* code is live. The third probe is the one that does: the two-segment
guest card path answers with **this pass's** body, `{"error": "Invitation not found"}`
(from `_published_document` inside `public_guest_social_card`) — a body the pre-pass
server could not produce for that path. The deployed guest page shape returns 200 rather
than 404 because `/i/<slug>` has always served `public.html` with fallback tags when the
slug is unknown, which is the behaviour §5.3 asks for.

Not verified on production, and reported as such: that a *real* guest link renders a card
with a real Khmer name there. That needs a published invitation with guests on the live
service, which this pass did not create. The card is verified locally instead (§2 Goal 5),
and the font verdict for the deployed machine is what the `KHMER_FONT_STATUS` line inside
`/api/health` reports when `DISCLOSE_HEALTH_DETAILS` is on.

---

## 7. Findings, limitations, retractions

1. **A security test caught a real regression** (`bb5e23f`): the first dispatcher split
   truncated any slug containing a slash. Fixed by validating the guest segment; the
   suite is green afterwards. Retained here rather than quietly amended, because the
   first Goal 4 verification (which used only clean slugs) passed.
2. **The guest list did not render at all** in the first version of Goal 6, from a
   temporal-dead-zone read of a `const` declared below the wiring. Found in Chromium, not
   by reading the code; fixed by moving the declaration to the top of `guests.js`.
3. **`contentBinding` did not survive a page load** (`app.js`'s DOM round-trip), which
   would have made the guest binding unpublishable. Measured, fixed, and documented in the
   Goal 3 commit. This is the only file changed outside the brief's list.
4. **The Khmer font WARN branch was not exercised** on this host (a system Noto Sans Khmer
   exists and hiding it needs administrator rights). Only the `ok` line and the redundancy
   between the two vendored copies are measured. Reported as a limitation.
5. **`tests/v25_template_governance_browser_test.py` is broken and predates this pass**:
   it loads its CSS and JS from the repository root
   (`FileNotFoundError: …/direct-manipulation-v24.css`), while those files live under
   `src/css/` and `src/js/`. It is untouched since the baseline commit `cfbb764` and pytest
   does not collect it (it defines `main()`, not `test_*`), so it neither fails nor passes
   the suite — it simply never runs. Left as found and recorded here.
6. **Environment note:** the plain `python3` in this environment has no `pytest`; the
   checks above use `.venv/bin/python`, whose pytest is 9.1.1.
7. **The dev server used for the browser checks is gone.** It ran on
   `http://127.0.0.1:47123` with its data in `/tmp/einvite-preview` (one Khmer-guest
   invitation with six guests, unpublished); it did not survive the editor restart at the
   end of this pass, and the probe confirms the port is closed. It was this pass's process,
   not the application's, so nothing is left running and nothing needs stopping. The
   findings it produced (§2 Goals 1, 3 and 6) are the browser-run outputs quoted above; a
   future pass that wants to click through the feature again must start its own server.

---

## 8. Remaining work

| Item | Why it is not in this pass | Size |
|---|---|---|
| Bulk write endpoint | §5.7 phase A: the per-row path handles hundreds of guests; a Cambodian wedding list is hundreds | small, additive |
| "Send all" delivery | §5.5: channels need per-host credentials; the requirement is that the link alone is sufficient | large (credentials, per-channel adapters, delivery status) |
| Khmer romanization for readable codes | §3.1: four official systems disagree and no library is maintained; an opaque code is honest | research-sized |
| Romanized-code opt-in | A designer may prefer `sok-dara` for a Khmer name; would need a transliteration table plus a frozen-vs-regenerated policy | medium |
| The eleven KH_PENDING strings | No approved Khmer exists in `TRANSLATIONS.csv` for them | one translation review |
| Warm-job progress surface | The freeze response reports how many cards are queued, but nothing reports completion to the designer | small |
| Production verification of a real guest link | Needs a published invitation with guests on the live service | operator action |
| `v25_template_governance_browser_test.py`'s stale asset paths | Pre-existing, one-line fix per path, but it is another pass's file | small |
