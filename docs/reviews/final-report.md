# Final report — UI/UX sweep and fix pass, 2026-10-13

Server under test: the real application server, `python3 src/python/server.py` on `127.0.0.1:4175`
(`make dev`), not the static preview, so `EInviteBackend` reports `online` and every route's real
signed-out and signed-in behaviour is exercised.

## Verification, run against the final tree

| Check | Command | Result |
| --- | --- | --- |
| Console + network, all 16 routes | `BASE_URL=http://127.0.0.1:4175 node tools/page-errors.mjs --all` | **`TOTAL pages=16 consoleErrors=0 non2xx=0`** |
| Layout sweep, 16 routes × 5 widths (final tree) | `BASE_URL=… node tools/ui-sweep.mjs` | `rows=80 overflow=0 escapes=0 console=0 netfail=0 brokenLinks=0`, `overlays=1` |
| Click pass | `BASE_URL=… node tools/ui-sweep.mjs --click` | classification per route in `docs/reviews/sweep/*-dead-controls.json` |
| Per-route failing requests, signed out | `BASE_URL=… node artifacts/probe_a1_401.mjs` | 16 × `clean` (was 37 failures) |
| Per-route failing requests, signed in | `BASE_URL=… node artifacts/probe_a1_signed_in.mjs` | no failing `/api` requests; dashboard/account/editor render their signed-in UI |
| Console baseline record | `BASE_URL=… node artifacts/console-baseline.mjs` | `0 page errors / 0 failed requests` per load |
| CSP violations + inline scripts | `BASE_URL=… node artifacts/probe_csp_detail.mjs` | `csp=[] inlineScripts=0` on index, dashboard, public |
| Pre-paint language, guest page | `BASE_URL=… node artifacts/probe_c1b_public.mjs` | `htmlLang=km rootLang=km kmVisible=23 enVisible=0` |
| Generated artifacts are current | `python3 build.py all --check` | exit **0** |
| Python suite | `.venv/bin/python -m pytest tests/ -q` | exit **0**, `85 passed` |
| Static integrity (inline JS parses) | `.venv/bin/python tests/static_integrity_test.py` | `STATIC_INTEGRITY_TEST_PASSED` |

## What was fixed in this pass

| ID | Fix | Evidence |
| --- | --- | --- |
| **A1** | Signed-out pages no longer send session-only requests (37 failed requests → 0). The shell owns the session contract; a remembered local demo id is no longer treated as a real invitation; the account page's detached-element write is gone. | [A1-2026-10-13.md](A1-2026-10-13.md) |
| **A3** | public.html no longer requests an unsubstituted `__INVITATION_SLUG__`. | [A1-2026-10-13.md](A1-2026-10-13.md) |
| **C1 / C1b / C2 / D2 / D3** | Every CSP-refused inline block moved into a module (16 pages for the language bootstrap; 3 blocks on dashboard). Pre-paint language now works on public.html too. `csp=[] inlineScripts=0` on the three routes that had violations. | [C1-2026-10-13.md](C1-2026-10-13.md) |
| **D4 (detector)** | The dead-control pass now separates *skipped* (already-active, disabled, `<select>`) and *covered* (painted over by an open overlay) from real candidates, tolerates a click that navigates, dismisses one-time overlays before probing, and its fingerprint sees language state, panel inventory, checkbox state and field values. Candidates: **112 → 37**, with 85 controls on the editor alone reclassified as "covered at load by `dialog.final-tour.final-dialog`". | `docs/reviews/sweep/*-dead-controls.json`, `artifacts/probe_d4_controls.mjs` |
| **D4 (real stub)** | `#eiAiTopButton` on the editor did nothing at all: `index.html` ships the button statically, while the AI module only wires a launcher it *creates itself*, and the deferred-tool bootstrap needs `data-deferred-tool="ai"`. The button now carries that tag (and `data-open-ai`); clicking it loads the module and opens `#eiAiFloating`. | `artifacts/probe_d4_controls.mjs`: `loader:false → true`, panel appears, no console error |
| **L1** | Language buttons work on all 16 routes (reload-based switch; verified). Two real defects fixed alongside: the switch was injected into every `<header>` with duplicate ids (6 × `#lang-km` on the editor) and relied on per-node listeners, so a re-rendered header could leave the visible copy dead. Now one delegated listener, ids on the first copy only. | `artifacts/probe_l1_click.mjs`, [A1-2026-10-13.md](A1-2026-10-13.md) |
| **D1, E1–E4, J1, J2, M1, M2, S1–S4** | Fixed in earlier iterations of this pass; see the Fixed table in [bug-inventory.md](bug-inventory.md) for the per-item evidence. | — |
| **Test bug** | `tests/static_integrity_test.py`'s inline-`<script>` regex matched the literal `<script>` inside a page comment, so index.html collected a syntax error that was never a script. The extraction is comment-aware; the check still syntax-checks every inline block. | `STATIC_INTEGRITY_TEST_PASSED` |

The single overlay row the layout pass reports is `index.html @1024`: on a fresh profile the
first-visit onboarding tour is an open `<dialog class="final-tour final-dialog">` over the stage, and
`document.elementFromPoint()` at the mobile pane handle's centre returns that dialog — i.e. the one
"painted over" element left in the sweep is the tour modal, not the pane handle. The click pass
dismisses one-time overlays before probing (and records how many controls they covered: 85 on the
editor), the layout pass deliberately does not, because a first-time visitor does see the tour.

## What is still open (with the evidence, not an opinion)

| ID | State | Why it is not closed here |
| --- | --- | --- |
| **A2** | Open, server-side | `/api/admin/metrics-v2`, `/api/admin/system-status` and `/api/admin/users-v2` are **not implemented** in `src/python/server.py` for any caller (`grep` → 0 matches; live `curl` → 404 while `/api/admin/overview` returns 401; `tests/admin_tools_test.py`, the spec for these routes, fails on its first `-v2` call). Fixing it means writing server routes outside this pass's edit scope (`src/html`, `src/css`, `src/js`). Since A1 they are no longer requested on a signed-out load. |
| **E5** | Open | `editor-command-system-v23.js` binds Escape at `window` capture and calls `stopImmediatePropagation()`, so the app shell's and the inspector's own Escape dismissals can never fire on the editor route. The fix direction is to route them through the command system's `closeTopLayer()`, which is what D1's menu now uses — it changes app-wide dismissal semantics and was left as its own change. |
| **D1b** | Open | The `•••` popover still overlaps the left panel while open (210 px @1280, 170 @1440, 130 @1600, 4.4 px of the rail @1024). It is dismissible and anchored; edge-aware horizontal placement is unimplemented. |
| **A4** | Open | account.html's signed-out path replaces `<main>`, collapsing the page to a status stub and detaching elements other modules still reference. The write that crashed (A1's last console error) is fixed; the teardown is not. |
| **D4 residual** | Open | 37 candidates remain across 16 routes. The clear classes: signed-out no-ops that need a session or form input (`Send RSVP`, `Add to calendar`, `Send reset link`, `#exportBtn` with no guests, `Refresh`, `Guest links`), cosmetic label oddities on the editor (`TT`, `▣F`), and reorder arrows that are no-ops at the ends of a list. Two are known detector blind spots rather than product bugs: the fingerprint is a *snapshot*, so a control that mutates a panel an earlier click already opened reads as "no change", and index's candidate count varies between runs (23 → 33) for exactly that reason. Each residual candidate needs the per-control treatment `artifacts/probe_d4_controls.mjs` applies (real click + broad diff). |

## Limitations of this verification

* Three browser tests skip themselves because `playwright` is not installed in this environment
  (`tests/v22_2_page_mobile_test.py`, `tests/v20_semantic_style_parity_test.py`,
  `tests/v0_52_final_ux_refinement_browser_test.py`). Every browser claim above comes from the
  project's own puppeteer harness (`tools/lib/browser.mjs`) with the command's real exit status.
* The sweep's click pass is a heuristic, not a proof: it reports *candidates*. The numbers quoted
  here are the candidates after classification, and the remaining blind spots are named above.
* Nothing in this pass is committed. The working tree also carries other sessions' edits
  (`src/html`, `src/css`, `package.json`), which this pass did not touch.
