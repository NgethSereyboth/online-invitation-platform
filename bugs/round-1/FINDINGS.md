# Round 1 — findings

Sweep target: production `https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page`
(2026-11-01 build). Public routes were driven live; editor, RSVP and export ran on the
local server from the same source because production has no test account and preview-origin
writes are rejected by design (`deploy/local/README.md`). All six viewports were covered:
360, 390, 768, 1024, 1280, 1440.

Evidence: `bugs/round-1/live-sweep.json` (114 records), `flow-sweep.json` (31 checks), key
screenshots in `evidence/`, full 148-shot matrix in `shots/` (gitignored raw output).

| ID | Page/route | Viewport | Steps | Expected | Actual | Severity | Status |
|---|---|---|---|---|---|---|---|
| BUG-R1-1 | `/invitations/<id>/editor` signed out | all | Open an editor URL with no/expired session | Reach the sign-in screen and return to the editor | Raw JSON `{"error":"Authentication required"}` with a browser pretty-print view | **P1** | **Fixed** (`fix-round-1`) |
| BUG-R1-2 | `/i/missing-slug` | all | Open a published-link slug that does not exist | 404 response (the unavailable page may still render) | A clear "Invitation unavailable" page, but HTTP **200** and the API 404 in the console | P2 | Open (logged) |
| BUG-R1-3 | Guest invitation | 390 (flow) | Open the invitation cover / let the guest page settle | No CSP console errors | CSP blocks a `data:image/svg+xml` fetch (`connect-src`), twice | P2 | Open (logged) |
| BUG-R1-4 | `v0_52_free_canvas_drag_test.py` | manual runner | `.venv/bin/python tests/v0_52_free_canvas_drag_test.py` | `EInviteProfessionalEditor.version === 17` in the inline fixture | 20 s timeout; the fixture's inline `<script src>` crawl no longer loads the bundle that defines it | P2 tooling | **Stuck** (see below) |

## BUG-R1-1 — signed-out editor navigation showed raw JSON (P1, fixed)

`serve_management_page()` called `require_user()`, whose only failure mode is the API's JSON
401. A browser navigation renders that as the pretty-printed JSON document in
`evidence/r1-1-before-raw-401.png`.

Fix: the management page now checks the session itself and, when the request's `Accept`
includes `text/html`, answers `302 Location: /dashboard.html?next=<path>` with
`Cache-Control: no-store`. API clients (no HTML accept) still receive the 401 that
`tests/v12_immediate_stabilization_test.py` asserts; that script still prints
`V12_IMMEDIATE_STABILIZATION_TEST_PASSED`. Post-fix navigation:
`evidence/r1-1-after-redirect.png`, landing on
`/dashboard.html?next=%2Finvitations%2F…%2Feditor`.

## BUG-R1-2 — missing invitation returns 200 (P2, open)

The rendered page is correct (`evidence/r1-2-missing-slug-200.png`): "Invitation unavailable",
no broken layout, no overflow. The defect is the status: a missing published slug returns
`200` with an API `404` in the console. Search engines and link checkers treat it as an indexable
page. Root cause: `/i/<slug>` serves `public.html` unconditionally and the client resolves the
document via `/api/public/<slug>`. Next action: have `serve_public` send 404 with the same shell
when no published row exists, and confirm cached/soft-deleted slugs keep their current policy.

## BUG-R1-3 — CSP blocks a data-URI SVG fetch (P2, open)

The flow run recorded two console errors on the guest path:
`Connecting to 'data:image/svg+xml,…%239d4555…' violates Content Security Policy` and
`Fetch API cannot load data:image/svg+xml…`. The export still produced a valid 41 KB PNG.
Root cause is a `fetch()` on a generated `data:` placeholder; the CSP allows it neither as a
connect target nor as a script source. Next action: find the placeholder fetch in the cover/export
path and pass the Blob/ObjectURL directly instead of fetching the data URI; do not widen
`connect-src` to `data:` just to silence it.

## BUG-R1-4 — manual-runner fixture no longer boots (P2 tooling, stuck)

`tests/inline_editor_runtime_test.py` builds an inline editor by crawling `<script src>` from the
page and inlining those files. After the editor bundle reshuffle, the bundle that defines
`EInviteProfessionalEditor` is no longer among the directly referenced scripts, so
`v17_professional_editor_test.boot()` times out at 20 s. Attempts: (1) ran the script standalone —
same timeout; (2) confirmed `professional-editor.js` still sets `version:17` and the real editor
boots in the flow sweep; (3) confirmed the test is a `manual-runner` in `runner-manifest.json`,
not part of the 223-test pytest suite. This is a stale fixture, not a product regression, but it
must not be marked green. Next action: add the defining bundle (or `professional-editor.js` and
its prerequisites) to the fixture's extras and re-run; do not weaken the version assertion.

## Not bugs (triaged)

- `.skip-link` / `.sr-only` hits: intentional clipping; not text loss.
- `app-brand` under 24 px: wordmark links, not tap controls; no unlabelled inputs or unnamed buttons.
- Zero horizontal overflow at every route and viewport; no missing `alt`.
- 404 route console error: expected for a deliberate 404.
- Cloudflare `beacon.min.js` CSP warning: third-party injection on the missing-slug page, not our code.
- Second concurrent editor context never reaching `editorReady`: known defect **#6** (draft lock);
  it reproduced only when the desktop context was left open, so the 390 leg now carries the session
  and runs after closing it.
- `#addText` hidden in the retired pane: the working route is the canvas add-text shortcut exercised
  by `ui_smoke_test`; not recorded as a new defect.

## Coverage and limits

- Live: 16 routes + 404 + missing slug + signed-out editor, six widths, 114 records, zero overflow.
- Local authenticated: 31 checks, 0 failed — registration, empty dashboard/guests/responses/analytics,
  public invitation at six widths with Khmer digits, RSVP invalid + submit, template filter (36→1),
  editor Pages pane, save/reload (4 objects preserved), 1× PNG export (41,042 bytes), 390 editor
  (0 overflow), wrong-password error, signed-out redirect.
- Transform coverage (add/drag/resize/rotate/multi-select/undo/redo) lives in the repo's own
  contracts: `v0_52_free_canvas_drag_test` is stuck per BUG-R1-4; `ui_smoke_test` and the 223-test
  pytest suite pass. This round did not add new transform assertions.
