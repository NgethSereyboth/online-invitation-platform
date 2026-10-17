# Version-Free Source Names — Staged Plan

Supersedes [`2026-10-15-eliminate-version-labeling.md`](2026-10-15-eliminate-version-labeling.md).

## Why the previous plan was replaced

That plan was an open-ended audit: five phases of "review each version-looking
string in context", with no endpoint and no acceptance test. Its one concrete
work item — a release version disclosed by `/api/health/live` — was already
implemented before it was written, and no user-visible release label existed to
remove. Measured against the tree:

- `src/python/server.py` returns exactly `{"ok": true, "status": "live"}`.
- `/api/health/ready` has no `version` field at all.
- No page in `src/html/` renders a version, and no `content:` rule in `src/css/`
  renders one.
- The `-vNN` tokens are file names, CSS class prefixes, JS namespace names and
  semantic contracts — not product branding.

So the real work was never "remove version labels from the UI". It was "stop
encoding the authoring milestone in file names", which is a rename problem with
a measurable end state.

## Goal

Source files under `src/js/` and `src/css/` carry no version suffix in their
names, and nothing regresses: the build gate, the served routes, and the
existing test contract all stay green. This is explicitly **not** a ban on
version-shaped strings anywhere in the repo.

## Out of scope (semantic versions — must keep)

- DB columns and their values: `token_version`, `current_version`,
  `document_version`, `release_version`.
- `schemaVersion`, `modelVersion`, `typography-model-version`.
- The plugin manifest `version` field and `plugins/sdk/manifest.schema.json`.
- Migration numbering and index names.
- The `"version": 15`-style field inside generated bundle manifests.
- Protocol and API route segments (`/api/platform/v32/`,
  `collaboration/v31|v52`, `raster/v30`, `/api/health/*`).
- The numeric `version:` property on frozen JS module exports. Only the *file
  name* changes; the exposed property name is a consumer contract.
- Historical records: `VERSION_HISTORY.md`, `docs/LEGACY-VERSION-HISTORY.md`,
  `docs/V*_*` dated reports and changelogs, `docs/STRUCTURE-*`,
  `*RELEASE_FILE_HASHES*`, `docs/reviews/`, `plans/`, `tools/evidence/`, and
  `vendor/`.

## Stage 0 — Green baseline and two missing guards (done)

1. `src/python/route-deferred-loader-v15.js` was absent from the served mirror
   while the served manifest listed it as a startup script for five routes.
   `python3 build.py all --check` was **red** (exit 1, `MIRROR_CHECK_FAILED`)
   and the whole pytest suite was green, because no test read the mirror.
   Restored through the supported `build.py mirror` step.
2. `tests/served_asset_resolution_test.py` — every asset a served page declares
   must resolve inside `src/python/`, every manifest-declared bundle and
   deferred chunk must exist, and the mirror must be byte-faithful. It calls the
   syncer's own `mirror_drift()` rather than re-implementing the comparison, so
   the gate and the test cannot disagree.
3. `tests/version_free_source_names_test.py` + `tests/versioned_name_allowlist.json`
   — the ratchet. A new version-shaped source name fails; an allowlist entry
   with no file behind it also fails, so the list can only shrink.

Both guards were proven sensitive before being relied on: a mirror drift, an
injected version-shaped file, and a stale allowlist entry each produced a
failure, and each was then restored.

## Stage 1 — Generated bundle family (done)

`bundle-<page>-v15.{js,css}` → `bundle-<page>.{js,css}`,
`bundle-<page>-deferred-v15.*` → `bundle-<page>-deferred.*`,
`route-deferred-loader-v15.js` → `route-deferred-loader.js`,
`route-bundles-v15.json` → `route-bundles.json`,
`page-assets-v15.json` → `page-assets.json`,
`route-bundle-sources-v15.json` → `route-bundle-sources.json`.

Owned end to end by the three generators plus the mirror's `GENERATED` allowlist.
The runtime contract also moved: the loader derives the deferred chunk from its
own `<script>` URL, so its stem regex now reads
`/bundle-([A-Za-z0-9_-]+?)(?:-deferred)?\.js/`, which was verified against both
the startup and deferred forms. `src/js/service-worker.js`'s precache list was
updated with it.

## Stage 2 — Hand-authored modules (done)

136 of 143 versioned source files renamed, with references updated across
sources, manifests, tests, tools and live docs, and the served mirror
regenerated. The renamer refuses to act unless the rename is provably safe:

- the target path is free;
- the target does not collide with another file in the **flattened** served
  namespace (`src/css/organized/x.css` and `src/css/x.css` both land on
  `src/python/x.css`, organized winning — so an organized file must not take a
  name a flat file already holds);
- no two entries in the same batch share a target.

Seven files are deliberately left (see the allowlist): `collaboration-v24.{js,css}`,
`photo-editor-v13.{js,css}`, `workflow-creation-flow-v3.js`,
`workflow-creation-flow-v4.js`, `organized/admin-page-v13.css` and
`organized/photo-editor-v13.css`. Each would collide with a different live file
of the name it would take, so dropping the suffix would silently merge or shadow
two distinct modules. They need a meaningful name chosen by a person — this is a
naming decision, not a mechanical rewrite.

## Stage 3 — Version-prefixed CSS class names and JS identifiers (not done, measured)

Measured on 2026-10-16 before deciding:

| Surface | Count |
|---|---|
| Distinct version-prefixed class names in `src/css/` | **454** |
| …that would collide with an existing class if the prefix were stripped | **64** |
| `src/js/` files referencing any of those names | 56 / 213 |
| Distinct version-suffixed `EInvite*` globals | **39** |

This is not the same kind of change as Stages 1–2, for two measured reasons.

**The 64 collisions are not renames, they are scope disambiguators.**
`.v13-row` cannot become `.row` — `.row` already exists and means something
else. Those prefixes are separating a legacy styling scope from the current one.
Stripping them mechanically would silently restyle every component that carries
them, and the only visible signal would be in the browser suite.

**The 39 globals are cross-cutting public surfaces.** `EInviteDocumentV32`
appears in 13 source files, `EInviteFutureUIV052` in 11,
`EInviteDeferredRouteLoaderV15` in 7. Each rename is an interface change agreed
across several subsystems, and a consumer missed in a file that only loads in a
browser test fails silently at runtime.

So Stage 3 needs a per-name product decision (what is `.v13-row` for, and is it
still needed?) before any of it is a rename. Deferred deliberately: the goal of
this work was relief for a reader opening the tree, and Stages 0–2 already
deliver that. The 39-global half is the more tractable of the two and is worth
revisiting on its own.

## Verification performed

| Check | Result |
|---|---|
| `python3 build.py all --check` | exit 0 |
| `tests/served_asset_resolution_test.py`, `tests/version_free_source_names_test.py` | 35 passed |
| Targeted suite (27 files naming the renamed assets) | 42 passed, 1 pre-existing failure |
| Served routes over HTTP | 16 pages, 37 distinct assets, 10 deferred chunks — all 200 |
| Route-bundle source list | every entry resolves |
| Loader stem regex (node) | correct for `bundle-x.js` and `bundle-x-deferred.js` |

The one remaining failure, `tests/v27_3_5_release_evidence_test.py::test_release_evidence`,
asserts `digest(README.md) == 87d613…`. That assertion was **already failing
before this work** because `README.md` carried uncommitted edits; this change
edits `README.md` again (it referenced renamed artifacts), so the digest moved
again. It is left failing rather than re-baselined: re-baselining would bake
unrelated pending README edits into a V0.52 release-evidence assertion and
assert that today's README is the released one. The release-evidence owner
should re-baseline it once `README.md` is final.

## Known leftovers (not touched)

`src/python/build/bundle-*-v15.{js,css}` and
`src/python/build/route-bundles-v15.json` are tracked artifacts that the current
generators never write to; a prior review classified them as stale leftovers
from an older build layout and recommended excluding them rather than
committing changes to them (`docs/reviews/g1-restorefile.md`,
`docs/reviews/v54-commit.md`). They are left as-is. Removing them is a separate
hygiene decision.
