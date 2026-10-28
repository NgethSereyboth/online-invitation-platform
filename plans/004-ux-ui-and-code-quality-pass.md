# Plan 004: Close the visible UX/UI defects and cut the CSS/layout debt behind them

> **Executor instructions (Freebuff)**: This plan is written for an autonomous run with zero owner
> contact. Follow it item by item. Run every verification and quote its signature line before
> moving on. If a STOP condition occurs, record it in `artifacts/next-work/OWNER-QUEUE.md` (one
> line: `date · item · what happened · default taken`), take the stated default and continue with
> the next item. Never ask the owner. When an item closes, update its row in `plans/README.md`
> and the "Improvement pass" section of `artifacts/ui-audit/fixes/STATE.md`.
>
> **Drift check (run first)**:
> `git diff --stat 0d01c23..HEAD -- src/css/app-shell.css src/css/dashboard-page.css src/html/dashboard.html src/html/index.html src/js/dashboard-polish.js src/js/ai-assistant-pro.js src/js/typography-layout-service.js src/js/ui/app-shell.js tools/ui-layout-guard.py`
> Files that changed after `0d01c23` (the TP-1.6 / FB-87 commit this plan was written on) are fine
> to work on, but re-read them: any excerpt below that no longer matches is a "reproduce first"
> failure, not a reason to improvise. Write "not reproduced" and tick the item.

# HARD RULES — READ BEFORE YOUR FIRST TOOL CALL

These override anything else in this file, in `AGENTS.md`, and in your own judgement. "MUST" and
"MUST NOT" are literal. Breaking one means: revert that commit (`git revert`, never `reset --hard`
on shared history), write the violation and the revert to `artifacts/next-work/OWNER-QUEUE.md`, and
redo the item correctly.

## H1. Authority and scope

1. This file is your contract. You MUST do only the items in it, in the order in it:
   **UX-1 → UX-9, Part A matrix, CQ-1 → CQ-4, Part B matrix.** You MUST NOT start an item before the
   previous one is committed and ledgered. If an item's prerequisite is unmet, skip it, write one
   OWNER-QUEUE line, and return to it once after the last item.
2. You MUST NOT do anything not named in the item you are on: no extra refactors, no renames, no
   "while I'm here" fixes, no formatting sweeps, no dependency or tool upgrades. If you find another
   defect, write one line in `artifacts/next-work/OWNER-QUEUE.md` and leave it.
3. One item = one commit. The commit MUST contain only files the item names or that its
   verification proves necessary. You MUST list every changed file with its reason in
   `fb-NN/NOTES.md`.
4. You MUST NOT ask the owner anything and MUST NOT wait for a reply. Every decision is already made
   in this file. Where it is not, take the safest default (the smaller change, the one that keeps
   current behaviour), write the default to OWNER-QUEUE, and continue.

## H2. Reproduce first, or do nothing

5. Before editing anything for an item you MUST capture the "before" state (named PNGs and/or a
   numeric probe) and write what you measured into `fb-NN/NOTES.md`.
6. If the defect does not reproduce, you MUST write `not reproduced` with the measurement, tick the
   item, and make **no code change**. You MUST NOT "fix" something you could not reproduce.
7. Findings marked `[shot]` were read from images. They are leads, not facts, until you reproduce
   them in a real browser.

## H3. Forbidden changes (no exceptions, whatever an item seems to ask)

You MUST NOT:

- add any `!important` (the count may only go **down**, and `IMPORTANT_PIN` is lowered in the same
  commit as each reduction);
- add `'unsafe-inline'`, `innerHTML`/`outerHTML`/`insertAdjacentHTML` in editor JS, a dependency, a
  font file, an npm/pip package, a CDN reference, or any remote request;
- change a budget, threshold, `tools/lighthouserc.js` assertion, the 600 ms ceiling, the CLS target,
  or any frozen canvas harness file (new canvas checks go in **new** test files only);
- write Khmer: not a word, not as an escape, not in a test, a comment, a commit message or a note.
  New visible strings are English, with a `fallback` row in `docs/i18n/TRANSLATIONS.csv` and a line
  in `docs/i18n/KHMER-GAP-ROUND5-2026-10-24.md`;
- rename or change identifiers, classes, routes, `EINVITE_*`, `einvite-*` storage keys;
- hand-edit generated files (`src/css/bundle-*.css`, `bundle-*.js`, `src/python/build/*`, mirrors,
  manifests). Fix the source, then run `python3 build.py all`;
- run any migration or write script against `data/` or a real database;
- run `git push`, open a PR, merge, tag, amend, rebase, force, or `git reset --hard`.

## H4. Forbidden shortcuts (anti-gaming)

You MUST NOT:

- skip, delete, `xfail`, `skip`-mark, or loosen any test or assertion to get green. Fix the cause;
- add `# noqa`, `# nosec`, `eslint-disable`, `@ts-ignore`, `try/except: pass`, or an empty `catch`
  to silence a failure;
- report a gate as passing unless its own signature line is in its output **and you quote that line
  verbatim** in the report. "Should pass" and "looks fine" are not evidence;
- substitute `--skip-heavy` or a narrower phase for a gate the item requires;
- re-run a flaky gate until it goes green. If a gate flakes, record every number, run the isolation
  probe that exists for it, and decide from the data;
- accept an extra canvas skip: the canvas gate MUST read `22 pass / 0 fail / 2 skipped`;
- replace a screenshot with a description, reuse an old screenshot as "after", or capture "after"
  from a different seed than "before" (use `--seed-preset artifacts/next-work/fb-19/matrix/seed-preset.json`
  for both);
- mark an item done while any of its Done criteria is unverified.

## H5. Git hygiene (exact)

- You MUST stage with explicit paths only: `git add <path> <path>`. You MUST NOT run `git add -A`,
  `git add .` or `git commit -a`.
- Before every commit run `git diff --cached --name-only` and `git status --porcelain`. The commit
  MUST NOT include: `artifacts/`, `data/`, `src/python/data/`, `.claude/`, `deploy/sites/`, owner
  screenshots, root `FREEBUFF-*.md` / `*-TASK.md`, `RILL-WALKTHROUGH.md`, any untracked owner path,
  or any modified `src/python/build/*` mirror. If one is present, unstage it.
- Before every commit run `python3 build.py all` then `python3 build.py bundles --check` and quote
  `ROUTE_BUNDLE_CHECK_PASSED`.
- Commit subject: `<type>(<area>): <what> (UX-n, FB-n)` or `(CQ-n, FB-n)`. FB-n = highest number in
  `artifacts/ui-audit/fixes/STATE.md` + 1; never reuse one. Body: one line per changed file.

## H6. The exact procedure for every item (do these steps, in this order)

1. Re-read the item and its excerpts; run the drift check for its files. A mismatch you cannot
   explain is a STOP condition.
2. Create `artifacts/next-work/fb-NN/NOTES.md` with the item id, the HEAD SHA, and the file list you
   expect to change.
3. Capture **before** (PNGs at the viewports the item names, plus the numeric probe). 1440 shots also
   get a 1000 px `-preview` copy.
4. Write the measured defect into NOTES.md. If not reproduced: stop here (H2.6).
5. Make the smallest change that fixes the cause, in the file the item names.
6. `python3 build.py all`, then `python3 build.py bundles --check`.
7. Run **only** the gates the item lists (and the gate-selection table), each once. Quote every
   signature line into NOTES.md.
8. Capture **after** with the same seed, viewports and names; run the pixel diff where the item says
   so; explain every differing shot or revert.
9. Walk the item's Done criteria one by one and tick each in NOTES.md with its evidence.
10. Stage explicit paths, run the H5 checks, commit.
11. Ledger: one line in the "Improvement pass (plans/004)" section of `artifacts/ui-audit/fixes/STATE.md`:
    `item · FB-n · commit · verdict · evidence path`; update the row in `plans/README.md`.
12. Only then start the next item.

## H7. Required report after every item (exact shape, facts only, no questions)

```
ITEM: UX-n | CQ-n — <title>
COMMIT: <short sha> FB-<n>
VERDICT: done | not reproduced | done (partial: <what is missing>) | defaulted: not done
CHANGED: <path> — <reason> (one line per file)
BEFORE -> AFTER: <the measured numbers that prove it, e.g. rightmost header edge 369.0 -> 318.4 at 320 px>
GATES: <phase>: "<verbatim signature line>" (one line per gate run)
NOT RUN: <gate or check not run, and why> | none
EVIDENCE: artifacts/next-work/fb-<NN>/
OWNER-QUEUE: <line written> | none
```

## H8. When it goes wrong

- **Three strikes:** three different approaches fail their gates → `git revert` to the last green
  commit, record all three attempts with numbers in NOTES.md, write `defaulted: not done` to
  OWNER-QUEUE, continue with the next item.
- **Unexplained diff** in a pixel comparison → revert that change, shrink it, retry once; second
  failure = strike.
- **Environment limits** (this machine's Chromium has no Khmer ICU data; heavy gates are slow): record
  the limit; it is never a reason to skip a required gate you can run.
- **Interrupted or context getting long:** finish the current item, write the ledger line, and
  continue from STATE.md. Never leave a half-finished item uncommitted without a ledger line saying
  exactly which step you stopped at.

## H9. End of each Part

Run `.venv/bin/python tools/run-gates.py --phase all` **once**, quote every signature line, capture
the after-set, update STATE.md, `docs/STATUS-INDEX.md`, rewrite `artifacts/next-work/HANDOFF.md` from
scratch (true HEAD, true gate state, next exact command) and add the next patch entry to
`VERSION_HISTORY.md`. No tag. After Part B, write the final report: what you completed, what you
verified and how, what you did not do or could not check, and the top three next steps.

---

## Status

- **Priority**: P1 (CQ-1), P2 (all UX items, CQ-2), P3 (CQ-3, CQ-4)
- **Effort**: ≈ 14 items, S–M each; CQ-1 is a recurring lane
- **Risk**: MED. Every item touches shared chrome or the editor. The gates below are the safety net.
- **Depends on**: the template-pack queue (`FREEBUFF-TEMPLATES-WORKORDER-2026-10-25.md`) is
  exhausted first. This plan then runs **before** the parked LT-3.2 item (8) and the rest of the
  long-term plan. It does not replace either; it only adds items.
- **Category**: bug (visual) · tech-debt · perf
- **Planned at**: commit `0d01c23`, 2026-10-25 (branch `fix/2026-10-22-open-issues`)
- **Authority**: `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` §2 (protocol), §3 (decisions), §5 (gate
  selection) still govern. This plan adds no new owner decisions: every choice below is already
  made, in the recommended direction.

## Why this matters

The product works and is heavily gated (smoke 16/0/0, layout 1533/0, pytest 161, LHCI 16/16 at
a11y 1.00, canvas 22/0/2), so what is left is polish and debt, and both are visible to a user:

1. The shared top bar still clips on phones (5 routes, measured 329–369 px at a 320 px viewport),
   the dashboard search box renders as a box inside a box in dark mode, icons are a mix of Unicode
   glyphs plus one colour emoji, and the editor's most important action ("Publish snapshot") looks
   like every other text button.
2. The cause of most of these is **layered override CSS**: 3816 `!important` declarations across
   ~60 files (`editor-suite.css` 659, `canvas-plus.css` 542, `modern-ui.css` 296 at the last full
   inventory), several sheets that each "win" the same header. New fixes keep needing another
   override. The ratchet pin only moves down, so the cleanest fixes below *delete* a rule.
3. The editor's blocking bundle spends 695 ms of its 741 ms evaluate slice just compiling 1.07 MB
   of JavaScript, and four forced layouts of 168–252 ms sit on the load path. The layout gate
   (frozen 600 ms ceiling) fails 4–6 % of cells for exactly this reason.

## Evidence classes used below

`[code]` I opened the file this session and the excerpt is real · `[shot]` seen in a screenshot in
`artifacts/next-work/review-lt2/after/` (read from the image, so **reproduce before editing**) ·
`[doc]` recorded by an earlier Freebuff pass in the named artifact.

## Standing rules (restated so this file is self-contained)

- Local commits only. No push, PR, merge, tag, amend, rebase, force.
- Never change a budget, a threshold, `tools/lighthouserc.js` assertions or frozen canvas harness
  files. Never raise `IMPORTANT_PIN`; it only goes down, **in the same commit as the reduction**.
- No new `!important`, no `'unsafe-inline'`, no new `innerHTML` in editor JS, no new dependency,
  no new font file.
- **Never write Khmer** (no word, no escape, no test fixture). Khmer enters only by script from the
  three maps in `docs/i18n/`. A new visible string is written in English, gets a `fallback` row in
  `docs/i18n/TRANSLATIONS.csv` and a line in `docs/i18n/KHMER-GAP-ROUND5-2026-10-24.md`.
- Visible-text brand changes only; never identifiers, `EINVITE_*`, `einvite-*` keys, classes, routes.
- Generated files (`src/css/bundle-*.css`, `bundle-*.js`, mirrors, manifests) are fixed at the
  source and rebuilt. Before every commit: `python3 build.py all` and
  `python3 build.py bundles --check`, with no modified `src/python/build/*` mirror in
  `git status --porcelain`.
- Never stage `artifacts/`, `data/`, `src/python/data/`, `.claude/`, `deploy/sites/`, owner
  screenshots, root `FREEBUFF-*.md` / `*-TASK.md`, or `RILL-WALKTHROUGH.md`.
- A gate is green only when its own signature line is in its output and quoted in your notes.
- Numbering: the next commit is **FB-(highest number in STATE.md) + 1** (FB-88 at the time of
  writing). Subject ends `(UX-n, FB-n)` or `(CQ-n, FB-n)`. Never reuse a number.
- Three strikes: three different approaches fail their gates → revert to the last green commit,
  record the three attempts with numbers in `fb-NN/NOTES.md`, add an OWNER-QUEUE line
  ("defaulted: not done") and move on.

## Commands you will need (all verified in this repo)

| Purpose | Command | Expect |
|---|---|---|
| Build | `python3 build.py all` | `BUILD_OK`, `MIRROR_CHECK_PASSED` |
| Bundle check | `python3 build.py bundles --check` | `ROUTE_BUNDLE_CHECK_PASSED` |
| One gate phase | `.venv/bin/python tools/run-gates.py --phase <build\|bundles\|smoke\|layout\|pytest\|budgets\|lhci\|csp\|canvas\|important>` | the phase's own signature line |
| Full matrix (phase close only, once) | `.venv/bin/python tools/run-gates.py --phase all` | `GATES_PASSED` |
| `!important` inventory | `.venv/bin/python tools/css-important-inventory.py --out artifacts/next-work/fb-NN/inv` | `CSS_IMPORTANT_INVENTORY total=N` |
| Who wins a property | `node tools/css-cascade-winner.mjs` (read its header for flags) | winner file + selector |
| Computed-style probe | `node tools/computed-style-probe.mjs` | computed values per selector |
| Bilingual check | `python3 scripts/check-bilingual-consistency.py` | exit 0 |
| Pinned-seed captures | `.venv/bin/python tools/ui-audit-capture.py --seed-preset artifacts/next-work/fb-19/matrix/seed-preset.json --out artifacts/next-work/fb-NN/<name>` | PNG set |
| Pixel diff | `.venv/bin/python tools/fb19-pixel-diff.py <before/shots> <after/shots>` | per-shot diff JSON |
| Serve the real app | `EINVITE_DATA_DIR=artifacts/next-work/fb-35/datadir EINVITE_DEV_AUTH_TOKENS=1 EINVITE_ALLOW_NO_SCANNER=1 PYTHONPATH=.:src/python .venv/bin/python src/python/server.py --port 8124` | app on :8124 |

Gate selection per item (from the long-term plan §5): CSS/layout on any route → build + bundles +
smoke + `--phase layout`. Editor DOM → also `--phase canvas` (**22 pass / 0 fail / 2 skipped; any
extra skip is a failure**). Bundle composition → also `--phase budgets`, `--phase pytest`, three
LHCI single runs. Public page → also `tools/csp-violation-check.py` and `scrollWidth == viewport`
at 375 and 1440. Run the full matrix once at the end of each Part, never twice.

## Findings table (vetted: each was reproduced from code, a recorded measurement, or a screenshot)

| ID | Finding | Impact | Effort | Risk | Confidence |
|---|---|---|---|---|---|
| UX-1 | Topbar right cluster runs past a 320 px viewport on 5 routes | Last control partly off-screen on phones | S–M | MED (shared header, 13 routes) | HIGH |
| UX-2 | Dashboard search is a box inside a box in dark mode | Looks broken on the first page after sign-in | S | LOW | HIGH (dark only) |
| UX-3 | Dashboard offers create / templates / guests from 3 places; the 3rd uses a colour emoji | Clutter, inconsistent icons | S | LOW | HIGH |
| UX-4 | Icons are Unicode glyphs and one emoji, not an icon set | Renders differently per OS/Android font; no consistent weight | M | MED (13 pages + budgets) | HIGH |
| UX-5 | Editor "Publish snapshot" has no primary emphasis | Weak hierarchy on the key action | S | LOW | MED |
| UX-6 | Editor right panel stacks three headings over one empty state; diagnostics shown to everyone; two floating pills look orphaned | Visual noise around a small artboard | M | MED (canvas gate) | MED |
| UX-7 | Empty photo slot renders as a solid maroon block in editor, dashboard thumbnails and card previews | Poor first impression of every new invitation | M | MED (export fidelity) | MED (cause unconfirmed) |
| UX-8 | Guest-list rows: "Remove" stretches full width, checkbox floats | Hard to scan; awkward target | S–M | LOW | HIGH |
| UX-9 | Public page showed section headings with empty space under them | May be reveal-on-scroll in a static capture | S | LOW | LOW (investigate) |
| CQ-1 | Header styling is split across ≥4 sheets that win with `!important`; one stray `!important` sits in the sheet that claims none | Every shell fix needs yet another override | M, recurring | MED | HIGH |
| CQ-2 | Forced layouts on editor load (168–252 ms each) and `availableSpace` 161 ms self time | Layout-gate ceiling, slow first interaction | M | MED | MED |
| CQ-3 | `ai-assistant-pro.js:4` binds a service at load, blocking its deferral | Prerequisite for any bundle diet; small direct gain | S | LOW | HIGH |
| CQ-4 | `dashboard-page.css` carries three generations of the same rules | Dead weight and confusion | S | LOW | HIGH |

### Considered and not recommended (so nobody re-audits them)

- **Splitting the editor bundle by 40 %.** The three named deferral candidates are 38.2 + 9.8 + 7.2
  KB raw, about 5 % of 1,027,696 B critical JS `[doc: docs/perf/editor-module-inventory-2026-10-24.md]`.
  No dependency-safe boundary for more is known. CQ-3 is a prerequisite, not a fix. Do not claim the
  ceiling is solved by it.
- **Raising the 600 ms ceiling, the CLS target or any budget.** Forbidden (OD-6).
- **A bigger artboard on a 375 px editor.** LT-1.6 settled that layout and the canvas gate is frozen.
- **Editor-internal icons to SVG.** Large glyph surface in frozen canvas code; later, own item.
- **Rewriting the editor shell or migrating frameworks.** Not needed for any finding here.
- **Template-pack quality, Messenger share, KHQR gift, `?guest=` greeting.** Already queued in the
  TP and LT plans; do not duplicate.
- **Untranslated English on the Khmer Templates and Guests pages** (heading, subtitle, filters,
  placeholders `[shot]`). That is the accepted English-fallback state until Claude drafts the next
  Khmer map. Add one OWNER-QUEUE line listing the strings; do not translate.

---

# PART A — Visible UX/UI defects

Do these in order. Each is one commit. After each: capture before and after at the viewports named,
save PNGs in `artifacts/next-work/fb-NN/` with 1000 px `-preview` copies of 1440 shots, write
`fb-NN/NOTES.md`.

## UX-1 — Topbar right cluster must fit at 320 and 375

**Evidence.** `[doc: artifacts/next-work/lt-1-8/FINDINGS.md]` at a 320 px viewport the right edge of
the last header control is: dashboard `button.app-drawer-toggle` 329.0, guests `div.app-topbar-right`
349.0, templates 369.0, materials `div.ui-theme` 360.0, responses 352.0. `[shot: templates-km-light-375.png]`
the Khmer "Refresh" button is cut off at the right edge and the account email chip takes ~140 px.

**Current state `[code: src/css/app-shell.css]`.**
```css
body:not(.guest) > header { display:flex; align-items:center; gap:var(--space-2); ...
  flex-wrap:nowrap; overflow:hidden; ... }            /* §3 */
.app-topbar-right { margin-left:auto; }
.app-account { max-width:min(220px, calc(100vw - 200px)); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; ... }
@media (max-width:700px) {
  body:not(.guest) > header .app-topbar-right { margin-left:42px; }   /* reserve the launcher lane */
  .app-account { max-width:min(220px, calc(100vw - 240px)); }
}
/* §3: header text buttons: min-width:36px; height:36px; padding:0 var(--space-3) */
```
The sheet's own ≤480 note says the winners for the bar's height/wrap are `organized/styles.css`
(a bare `header{…flex-wrap:wrap!important}`) and `modern-ui.css` block (c); do not add a competing
declaration there. Markup (`src/html/templates.html`): `.app-topbar-right` holds `#studioAccount.app-account`,
`#refreshBtn`, `.app-drawer-toggle`. Dashboard adds `#accountName`, `#logoutBtn`, plus the injected
`.ui-theme` and `.ui-app-launcher`.

**Steps (stop at the first step after which every check below passes).**
1. Reproduce: capture the five routes at 320 and 375, EN and KM, light and dark, with the pinned
   seed. Write each header descendant's `getBoundingClientRect().right` to `fb-NN/before.json`.
2. At `max-width:480px`, in app-shell.css §11, set `.app-account { display:none }` (the account name
   is also on the Account page; its full value stays in the `title`). Re-measure.
3. If still over: at `max-width:480px` remove the 42 px reserve only if the launcher does not
   overlap the cluster (measure the two rects; keep it otherwise), and set
   `body:not(.guest) > header > button, … .app-topbar-right > button { padding:0 var(--space-2) }`.
4. If still over: let the cluster shrink: `.app-topbar-right { flex:0 1 auto; min-width:0 }` and
   `#refreshBtn, #logoutBtn { flex:0 1 auto; min-width:36px; overflow:hidden; text-overflow:ellipsis }`.
5. Never hide the language switch and never add `!important`. If a legacy `!important` wins over
   your declaration, find it with `node tools/css-cascade-winner.mjs`, prove it superseded, and delete
   it as part of this commit (that is CQ-1 work and lowers the pin).

**Verify.** Extend `tools/ui-layout-guard.py` with a cell `topbar-cluster-in-viewport`: every visible
header descendant has `rect.right <= innerWidth + 0.5` at 320 and 375, all routes, both languages,
both themes, plus a negative control (inject a 400 px span, expect the cell to fail) following the
existing `SELFTEST_PASSED` pattern. Adding a check is allowed; changing a threshold is not.
Gates: build, bundles, smoke, `--phase layout` (`UI_LAYOUT_GUARD_PASSED`), and `--phase canvas`
(the editor header is a different element, but run it once because `canvas-plus.css` and
`editor-suite.css` also style `body:not(.guest) > header button`).

**Done.** Five routes × 2 widths × 2 languages × 2 themes: 0 elements past the viewport; page
`scrollWidth == viewport` unchanged; before/after PNGs.

**STOP.** The fix needs a markup change on more than the five routes, or touches the editor's own
header (`index.html`). Take the CSS-only result you have, record the remainder.

## UX-2 — Dashboard search must be one box in dark mode

**Evidence.** `[shot: dashboard-en-dark-1440-preview.png]` the field shows an inset second box with a
stray gap at its top; the light theme `[shot: dashboard-km-light-1440-preview.png]` is a single box.
`[code]` the container and input rules are `.app-search { border:1px solid var(--app-line); padding:0 var(--space-3); … }`
and `.app-search input { border:0; background:transparent; padding:0; min-height:32px }` in
`app-shell.css` §15, and the markup is injected by `src/js/dashboard-polish.js`. So some dark-theme
`input` rule outranks `.app-search input` (0,1,1).

**Steps.**
1. Capture the dashboard at 1440 dark. Use `node tools/css-cascade-winner.mjs` (or the computed-style
   probe) on `.app-search input` for `border-top-width`, `background-color`, `padding-left`,
   `min-height` in dark. Record the winning file and selector.
2. Fix at the cause, in this order of preference: (a) delete or narrow the dark `input` rule so it
   no longer reaches `.app-search input`; (b) raise the `.app-search` rules to
   `.app-search input[type="search"], .app-search input` (0,2,1). No `!important`.
3. Confirm the same field is single-boxed in dark and light, EN and KM, at 320, 375, 1440.

**Verify.** Computed style in dark: `border-top-width 0px`, `background-color rgba(0, 0, 0, 0)`.
Before/after PNGs. Gates: build, bundles, smoke, `--phase layout`.

## UX-3 — One way in to each dashboard action

**Evidence `[code: src/html/dashboard.html]`.** The head has `#studioBtn` ("Template Studio") and
`#newBtn` ("+ Create invitation"); directly below, `.dash-quickstart` repeats New invitation,
Templates and Guest list (`#quickstartNew`, `#quickstartTemplates`, `#quickstartGuests`), and the
rail already has Templates and Guest list. Each tile's icon is a pair of language spans such as
`<span class="i18n i18n-en">✦</span><span class="i18n i18n-km" lang="km">✦</span>`, and the third
is the colour emoji `👥` while the others are monochrome glyphs `[shot]`.

**Decision (pre-made).** The quick-start row is onboarding. Hide it once the account has at least
one invitation; keep it for an empty account. Do it where the invitation list renders (read
`src/js/dashboard.js` and `src/js/dashboard-polish.js`; reuse whatever state decides the existing
`.dashboard-empty` panel, do not invent a second source of truth). Set the `hidden` attribute rather
than `display:none` so assistive tech agrees.

**Steps.** (1) `rg -n "quickstart" tests tools src` and list every consumer. (2) If more than two
tests drive the tiles on a non-empty dashboard, STOP this approach and instead keep the row but make
it one quiet line of text links (no tiles, no icons); record why. (3) Implement; the icon swap
itself is UX-4, so leave the glyph spans alone here except removing nothing.

**Verify.** Dashboard with 0 and with 4 invitations at 375 and 1440, EN and KM: 0 → tiles shown,
4 → tiles hidden, header actions unchanged. `python3 scripts/check-bilingual-consistency.py` exit 0.
Gates: build, bundles, smoke, `--phase layout`, `--phase pytest`.

## UX-4 — One icon set (inline SVG), starting with the shell

**Evidence.** `[code]` `src/js/ui/app-shell.js` writes text glyphs: `«`, `»` (rail), `☾`, `☀`
(theme); `templates.html`/`dashboard.html` rail icons are `⌂ ✦ ▣ ☰ ≣ ◔ ◎ ⚙` in
`<span class="app-rail__icon" aria-hidden="true">`; `dashboard-page.css` uses `content:'✦'`. The
capability list asks for "one consistent icon set at consistent stroke and size". Unicode geometric
glyphs fall back to different fonts per device; on low-end Android that can be tofu.

**Scope.** Shell only: the rail (13 pages), topbar toggles, dashboard quick tiles, auth-card bullets
and brand mark. **Not** the editor (frozen canvas code, separate item).

**Decisions (pre-made).**
- Draw an original 16-icon set in-repo (24×24 viewBox, 1.75 stroke, round caps and joins,
  `currentColor`, no fill): home, sparkle, image-grid, list, table, pie, card, cog, chevrons-left,
  chevrons-right, menu, sun, moon, users, plus, star. Do not copy a third-party pack. Record
  "original, authored in this repo" in a new `docs/ASSETS.md` (the capability matrix lists it as
  absent).
- Ship it as one file `assets/icons.svg` (the static whitelist already serves `assets/*.svg`).
  Markup: `<svg class="icon" aria-hidden="true" focusable="false"><use href="assets/icons.svg#i-home"/></svg>`.
  Style once in `app-shell.css`: `.icon{width:1.25em;height:1.25em;fill:none;stroke:currentColor;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round;flex:none}`.
- Rail collapse chevron: keep `[data-rail-glyph]`, put one `<use>` inside it, and rotate with CSS
  (`body.rail-collapsed .app-rail-toggle .icon{transform:rotate(180deg)}`). Theme toggle: include
  both sun and moon and show one with `html[data-theme="dark"]` selectors. `app-shell.js` must stop
  assigning `textContent` to those spans. No `innerHTML` anywhere.
- Icons sit **outside** `.i18n` spans, so no Khmer map is needed and the bilingual checker stays green.

**Steps.** (1) Create the sprite and CSS, convert **one** page (`templates.html`) and run
`tools/csp-violation-check.py`. If an external `<use>` raises a CSP or load error, switch to an
inline `<svg hidden>` sprite included once per page by the HTML source and measure with
`--phase budgets`; record the choice. (2) Convert the other rail pages with one scripted
replacement per glyph (list the 13 files in the notes and diff each). (3) Replace the dashboard
quick tiles (`✦`, `⌂`, `👥`) and delete the duplicate Khmer-language icon spans. (4) Remove the
`content:'✦'` decoration from `.template-choice .template-art::after` only if its tile still reads
correctly without it; otherwise leave it.

**Verify.** `--phase budgets` (`V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED`, 6 pages within budget),
`CSP_CHECK_PASSED`, smoke 16/0/0, layout, pytest, three LHCI single runs on `dashboard.html` (a11y
stays 1.00). A grep proves none of `⌂ ✦ ▣ ≣ ◔ ◎ ⚙ « » ☾ ☀ 👥` remain in shell markup:
`rg -n "[⌂✦▣≣◔◎⚙«»☾☀👥]" src/html src/js/ui` returns only intentional text content.
Screenshots at 1440 and 375, light and dark: icon stroke and size identical across rail items.

**STOP.** Any budget breach you cannot fix by removing bytes elsewhere in the same commit.

## UX-5 — Make "Publish snapshot" the primary action in the editor

**Evidence.** `[shot: editor-en-light-1440-preview.png]` the top bar reads `Undo · Redo · Design
check · Guest preview · Publish snapshot · AI · ⌘K` in identical text style. `[doc]` `#publishBtn`
sits in `div.studio-topbar-right` (`fb-59/CLS-ATTRIBUTION.md`).

**Steps.** (1) In `src/html/index.html`, find `id="publishBtn"` and add the class `primary` (the
shell already defines `body:not(.guest) > header > button.primary` and `button.primary`; both give a
flat accent fill with `#fff`, audited). (2) Read computed `background-color` and `color` in light and
dark. If an editor sheet forces a transparent background with `!important`, find it with
`css-cascade-winner.mjs`, prove it superseded for this button and delete that declaration (CQ-1);
never add one. (3) Check the label does not change `div.studio-topbar-right` width by more than
the existing late-arriving buttons already do.

**Verify.** Contrast white on the accent ≥ 4.5:1 in both themes (quote the measured numbers). Three
LHCI single runs on `index.html`: CLS median not worse than the recorded 0.1415 (it is not a target
change, only a no-regression check). Gates: build, bundles, smoke, `--phase layout`, `--phase canvas`
(22/0/2). Before/after PNG at 1440 light and dark.

## UX-6 — Calm the editor chrome around the artboard

**Evidence `[shot: editor-en-light-1440-preview.png]`.** With nothing selected the right column shows
the small label "Inspector" with an "Essentials" button, then a section label "EDIT", then a large
"STYLE & MOTION" heading, then a card saying to select an object; a "Graphics diagnostics"
disclosure sits at the bottom for every user. Two white pills, "Timeline" and "Studio Ops", float
in the lower corners of the canvas area. LT-1.7 already removed the duplicate search and one
"Inspector" eyebrow and measured no overlap with the artboard, so this is about visual weight, not
collision.

**Decisions (pre-made).**
- Keep the tab's section label and the empty card; **remove the third heading** (the large
  "STYLE & MOTION") only while the empty state is showing. It returns when an object is selected.
- Show "Graphics diagnostics" only when the panel is in the Advanced mode (the "Essentials" button
  already exists). Do not delete the feature.
- Do **not** move the Timeline or Studio Ops DOM (canvas gate is frozen). Reduce their weight only:
  12 px label, 32 px height, `--app-surface-3` background, no shadow, 0.9 opacity until hover/focus.

**Steps.** (1) Reproduce at 1280 and 1440 and write the real class names and ids of each piece to
`fb-NN/before.json`. (2) `rg -n "diagnostics|Studio Ops|studio-ops|Timeline" tests tools` to list
consumers; if a test asserts the diagnostics row exists in Essentials mode, keep it present in the
DOM and hide it with `hidden` plus a mode attribute instead of removing it. (3) Implement in the
editor's own shell sheet. No new `!important`; if a legacy one wins, delete the superseded rule.

**Verify.** `--phase layout` and `--phase canvas` (22/0/2, skips = 2). Panel still reachable by
keyboard, `aria-live` regions unchanged. Before/after PNG at 1280 and 1440, light and dark.
**STOP** if the canvas gate changes in any way you cannot attribute to the three edits above.

## UX-7 — Give an empty photo slot a designed placeholder

**Evidence `[shot]`.** The seeded invitation shows a flat maroon rectangle where a photo belongs, in
the editor, on dashboard thumbnails and in the card previews. `[doc: docs/templates/INTEGRATION-NOTES-2026-10-25.md]`
the five built-in templates ship `designPages: []` and `objects: {}` and "look empty in the
editor", and a pack `photo` layer maps to an `image` object with an empty `src` plus
`imageMask`. I have **not** confirmed which object produces the maroon block (a `shape` with
`fillColor`, or an `image` with empty `src` on a coloured panel).

**Steps.**
1. Reproduce and identify: open the seeded invitation, select the block, read the object's `type`,
   `src`, `fillColor` from `EInviteEditorBridge.getState()`. Write it down.
2. If it is an **image object with no `src`**: in the editor only, draw a dashed 1.5 px outline in
   `--app-line-2`, a centred camera icon (from UX-4's sprite; add `i-image` if missing) and the
   label "Add photo" (English, with a `fallback` row in `TRANSLATIONS.csv`). It must **not** appear
   in PNG/PDF export, on the guest page or in dashboard thumbnails. Implement as an editor-only CSS
   class toggled by the same code path that already renders empty images.
3. If it is a **shape** the template author coloured on purpose: do not touch it. Record that the
   template, not the editor, is the cause and add a note to the TP queue to give the five
   built-ins a pack-quality placeholder.

**Verify.** `tests/lt_2_6_export_fidelity_test.py` still passes (PNG 1× MAE 0.0 against the editor
on the sheet) and a new assertion proves the placeholder text is absent from an exported PNG's DOM
snapshot and from `public.html`. Gates: build, bundles, smoke, layout, canvas, pytest.
**STOP** if the placeholder can leak into export or guest output.

## UX-8 — Guest-list rows

**Evidence `[shot: guests-km-light-1440-preview.png]`.** Each row shows the guest name and a
"not-sent" line at the left, a status string and four buttons at the right, then a second line with
a full-width bordered "Remove" bar and a checkbox floating far right. The remove action is the
widest, loudest element in the row and the select checkbox is detached from the name.

**Steps.** (1) Dump the row's DOM at 1440 and 375 (children, rects) from `src/js/guests.js`
rendering. (2) Re-lay the row with CSS grid: `grid-template-columns: auto minmax(0,1fr) auto`, with
checkbox, name and meta, then one actions group (edit, QR, check-in, remove) of equal 36 px buttons;
"Remove" is a normal button in danger text colour (≥ 4.5:1 on its background). At ≤ 640 px the
actions wrap under the name. (3) Prefer CSS-only; if markup order must change, update only the
tests that assert it.

**Verify.** At 1440 a row is ≤ 72 px tall; at 375 `scrollWidth == viewport`; no element wider
than 50 % of the row except the name block. Gates: build, bundles, smoke, layout, pytest. Before/after
PNG, KM light 1440 and 375.

## UX-9 — Check whether the public page really shows empty headings

**Evidence `[shot: public-km-light-1440-preview.png]`.** Below the hero there are two section
headings with ~100 px of blank space under each. The capture contract takes a static shot, so this
may be reveal-on-scroll content that never intersected.

**Steps.** (1) Open the public page, scroll through it with `window.scrollTo` in steps, and
re-capture. If the content appears, record "not reproduced". (2) **Always** also run it with
`prefers-reduced-motion: reduce` and with JavaScript's `IntersectionObserver` stubbed to never fire:
every section must still be visible. If it is not, that is a real accessibility bug: make
the hidden-until-revealed state apply only when `IntersectionObserver` exists and motion is allowed.
(3) If sections with no data (no schedule, no venue) still print a heading, do not render the
heading; the capability matrix says dress code already follows that rule, so match it.

**Verify.** `tools/csp-violation-check.py` (`CSP_CHECK_PASSED`), `scrollWidth == viewport` at 375
and 1440, smoke, layout, budgets. Evidence PNG after scroll.

**End of Part A.** Run the full matrix once (`--phase all`), refresh an after-set in
`artifacts/next-work/review-ux1/after/` with an `INDEX.md`, add a patch entry to
`VERSION_HISTORY.md` (next patch number), rewrite `artifacts/next-work/HANDOFF.md`.

---

# PART B — Code quality and load performance

## CQ-1 — Consolidate the header contract and run the `!important` lane

**Evidence.** `[doc: artifacts/next-work/fb-19/REPORT.md]` the 2026-10-22 pass removed 214 tokens
(5.3 %) and stopped because the rest needs "deeper interaction-state proving"; it left the
approved 25–40 % range unmet and documented the next staged pass. `[code: src/css/app-shell.css]`
its own header says it wins "without a single forced declaration", yet the sheet's later "Pass 2"
section has `body[data-page="admin"] .admin-page > h1 { font-size:clamp(26px,8.5vw,48px) !important; }`.
Its notes also state that the header's height/wrap contract lives in `organized/styles.css` and
`modern-ui.css` block (c), and that `body:not(.guest) > header button` in `editor-suite.css` and
`canvas-plus.css` sets `display:inline-flex` at (0,1,3). That is four sheets deciding one bar.
The inventory at 2026-10-21 (`artifacts/next-work/nw-2-1/important-inventory.md`): `editor-suite.css`
659, `canvas-plus.css` 542, `modern-ui.css` 296, `stabilized.css` 220, `final-polish.css` 217,
`ux-refine.css` 209, `editor-layout-stability.css` 184, `ai-assistant-pro.css` 178. Current pin:
3816 ≤ 3823 (`IMPORTANT_PIN` in `tools/run-gates.py`).

**Existing tools (use them; do not rewrite).** `css-important-inventory.py`, `fb19-probe-dom.py`
(live selector probe), `fb19-dead-important.py` (static dead scan), `fb19-merge-dead.py`
(per-comma-alternative validation, fixes the bug the last pass hit), `fb19-superseded.py`
(same-selector later winner), `fb19-remove-rules.py`, `fb19-pixel-diff.py`, `css-cascade-winner.mjs`,
`important-removal-audit.py`.

**Method (one batch = one commit, ≤ 50 `!important` tokens).**
1. Baseline: inventory, then pinned-seed captures (`--seed-preset`) into `fb-NN/before/`.
2. Pick the batch from the **header and shell first** (the declarations that the header files above
   win with), then the non-canvas sheets in this order: `modern-ui.css`, `stabilized.css`,
   `final-polish.css`, `ux-refine.css`, `ai-assistant-pro.css`, `workflow-creation-flow.css`.
   **Last**, and only with the canvas gate in the loop: `editor-suite.css`, `canvas-plus.css`.
3. For each token prove it dead (selector matches nothing in the 16 routes × light/dark × en/km ×
   320…1440, using the live probe, and tokens-absent in shipped HTML/JS) or superseded
   (same selector and at-rule chain, a later declaration of the same property publishes after
   removal). Comma lists are validated **per alternative**. Anything that merely "looks unused"
   stays.
4. If a declaration is needed and the only reason it carries `!important` is to beat another
   sheet, move the needed declaration into `app-shell.css` at equal or higher specificity and
   delete the loser. Never add a replacement `!important`.
5. Remove; `python3 build.py all`; capture `after/`; run `fb19-pixel-diff.py` at **zero tolerance**.
   Every differing shot must be explained: the repo already documents the known noise classes
   (editor canvas fit races at 375/320, chip micro anti-aliasing, account-page session rows). An
   unexplained diff → revert that batch, shrink it, retry once; second failure → stop the lane.
6. **In the same commit** lower `IMPORTANT_PIN` in `tools/run-gates.py` to the new measured total.
7. Gates: build, bundles, smoke, layout, `--phase important`; add `--phase canvas` for any sheet that
   is loaded on the editor route; once per batch, not per file.

**First batch (do this one now, it also feeds UX-1 and UX-5).**
- List every `!important` declaration whose selector is `header`, `body:not(.guest) > header …`,
  `.app-topbar-*`, `.app-account`, `.app-drawer-toggle`, `.app-rail-toggle`, `.ui-theme*`,
  `.ui-app-launcher*` across `organized/styles.css`, `modern-ui.css`, `editor-suite.css`,
  `canvas-plus.css`, `stabilized.css`. Write the table (file, selector, property, value, winner?)
  to `fb-NN/header-important.md`.
- Resolve the stray `!important` in `app-shell.css` (admin h1) by testing whether
  `clamp(...)` still wins without it at 320/375 (the sheet's earlier `main h1` rule is the
  competitor); if not, raise the selector rather than keep the token.

**Done for the lane.** A recorded reduction of at least 150 tokens by the end of Part B with the pin
lowered to match, or a documented stop at the first unexplained diff (that is an acceptable end).
Do not chase the 25–40 % range if the evidence does not support it; the previous pass already showed
why.

## CQ-2 — Cut the forced layouts on the editor load path

**Evidence `[doc: artifacts/next-work/fb-64/LAYOUT-HEADROOM.md]`.** Longest main-thread slices on a
1440×900 signed-in load: `EvaluateScript` 741 ms (`bundle-index.js`), four forced `Layout` slices of
252 / 250 / 170 / 168 ms, and 161 ms self time in `availableSpace` called through `measurement()`.
`[code: src/js/typography-layout-service.js]` `availableSpace(outer)` calls `getComputedStyle(outer)`
and reads `clientWidth/clientHeight`; `measurement()` then reads `scrollWidth/scrollHeight` and
`getComputedStyle` again; `fit()` already caches the 16-step autofit search by box and model (the
comment records the FB-29 race, so **do not remove or loosen that cache or its "rewrite font-size on a hit" step**).
The cost that remains is read/write interleaving across many text objects.

**Steps.**
1. Reproduce with the existing probes: `node tools/forced-layout-attribution.mjs` and
   `node tools/layout-thrash-probe.mjs` against the signed-in `index.html` at 1440×900. Save the top
   forced-layout callers and slice durations to `fb-NN/before.json`.
2. If the callers are typography code: find the loop that calls `fit()`/`measurement()` for each
   text object and split it into a **read pass** (collect `availableSpace` and scroll sizes for all
   objects) then a **write pass**. Keep behaviour identical: same model, same cache key.
3. If the callers are the canvas controller (`app.js`, `editor-suite.js`): **STOP**. That code is
   under the frozen canvas gate; record the attribution and move on.
4. Optional second step only if step 2 leaves ≥ 2 forced layouts over 100 ms: defer the first fit of
   text objects on non-active pages to `requestIdleCallback` (timeout 1000 ms). Anything that changes
   what the user sees on page 1 is out.

**Verify.** Re-run the probes: the total forced-layout time drops by at least 40 % (quote both
numbers), `--phase layout` stays `max ≤ 579` ms rows over 600 = 0, `--phase canvas` 22/0/2, export
fidelity test unchanged (`tests/lt_2_6_export_fidelity_test.py`), Khmer text sheet identical
(`docs/qa/khmer-text-sheet`). If the improvement is under 40 % record the number and keep the
change only if it is strictly positive and all gates pass.

## CQ-3 — Make the AI service lazy (prerequisite, small direct gain)

**Evidence `[code: src/js/ai-assistant-pro.js:3-5]`.**
```js
const VERSION='27.3.5';if(window.EInviteAI?.version===VERSION)return;
const service=window.EInviteAIActionService,$=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!service||!$('#stage'))throw Error('AI action service is unavailable.');
```
The module needs the service at evaluation time, so `ai-editor-action-service.js` (38,170 B raw,
11,347 B gzip, `[doc]`) cannot move into the deferred chunk. `ai-creative-agent.js` and
`ai-agent-tool-registry.js` already use the lazy `() => window.EInviteAIActionService` form.
Honest size: ≈ 3.7 % of critical JS, so expect about 25 ms less compile, not a solved ceiling.

**Steps.** (1) Replace the constant with `const svc=()=>window.EInviteAIActionService;`, change
each `service.` to `svc().`, and drop `!service` from the guard. (2) At the point the assistant
opens or runs, if `svc()` is missing await `window.EInviteDeferredRouteLoaderV15?.ready` (it resolves
when the deferred chunk has evaluated or failed) and, if still missing, show one toast in English
("The assistant is still loading. Try again in a moment.", plus a `fallback` CSV row) instead of
throwing. (3) Only then move `src/js/ai-editor-action-service.js` into the editor route's deferred
group in `docs/route-bundle-sources.json` and rebuild.

**Verify.** A new test opens the editor, clicks the AI button within 300 ms of
`DOMContentLoaded`, and asserts the drawer is open within 3 s with 0 console errors, run 5 times.
`--phase budgets`, `--phase pytest`, `--phase canvas`, three LHCI single runs (record transfer and
`scriptBytes` before/after). **STOP** if any consumer other than the three named binds the service at
load; record it and keep step 1 only.

## CQ-4 — Remove the superseded legacy blocks in `dashboard-page.css`

**Evidence `[code: src/css/dashboard-page.css]`.** The same widgets are declared in three
generations: `.invite-grid` with `minmax(250px,1fr)`, again with `minmax(220px,1fr)`, and finally
the V55 section `body[data-page="dashboard"] .invite-grid` with `minmax(280px,1fr)` (plus
`app-shell.css` `#inviteGrid`). The oldest block also carries `.invite-status-pill.Draft`
(`background:#e8f0f2; color:#c62828`, red text for a draft) and hard-coded hex values, while the
visible badge in the dashboard is the token-based `.app-badge--draft` `[shot]`.

**Steps.** (1) Probe which of these selectors match anything on the 16 routes (the existing live
probe). (2) Delete only blocks that are provably dead or fully superseded; keep every
`.template-choice`, `.template-preview-*`, `.create-dialog` rule (live). (3) Replace any surviving
hard-coded colour in the lines you touch with a token from `tokens.css`.

**Verify.** `fb19-pixel-diff.py` at zero tolerance on dashboard and templates routes, all
viewports and themes. Gates: build, bundles, smoke, layout, budgets (the file should shrink; quote
bytes before/after).

**End of Part B.** Full matrix once. After set in `artifacts/next-work/review-ux2/after/`. Add the
next patch entry to `VERSION_HISTORY.md`, rewrite `HANDOFF.md`, update `docs/STATUS-INDEX.md` with
one row for this plan.

---

## Test plan (summary)

- New or extended: `tools/ui-layout-guard.py` cell `topbar-cluster-in-viewport` with a negative
  control (UX-1); a dashboard 0-vs-4-invitations check (UX-3); an export/guest no-leak assertion for
  the photo placeholder (UX-7); a reduced-motion and no-`IntersectionObserver` visibility test for
  the public page (UX-9); a cold-open AI assistant test (CQ-3). Model each on the nearest existing
  `tests/lt_2_*_test.py` file.
- Existing gates must stay at their last recorded results: smoke 16/0/0, layout 1533+/0, pytest
  ≥ 161, budgets 6/6, LHCI 16/16 a11y 1.00, CSP pass, canvas 22/0/2, important ≤ pin (pin only
  lower).

## Done criteria (machine-checkable; all must hold)

- [ ] `UI_LAYOUT_GUARD_PASSED` with the new topbar cell and its negative control
- [ ] `python3 build.py bundles --check` → `ROUTE_BUNDLE_CHECK_PASSED`; no modified `src/python/build/*`
- [ ] `--phase all` → `GATES_PASSED` at the end of Part A and again at the end of Part B
- [ ] `IMPORTANT_PIN` in `tools/run-gates.py` is lower than 3823 and equals the measured inventory
- [ ] `rg -n "[⌂✦▣≣◔◎⚙«»☾☀👥]" src/html src/js/ui` shows no icon-role glyphs
- [ ] `git status --porcelain` shows no staged path from the never-stage list
- [ ] Every item has `fb-NN/NOTES.md`, named before/after PNGs and a ledger line in STATE.md
- [ ] `plans/README.md` row 004 updated

## STOP conditions

Stop the item (not the run) and record it when: the live code does not match an excerpt above and
the finding does not reproduce; a gate fails twice after a reasonable fix; a fix needs a file on the
never-touch list (budgets, thresholds, frozen canvas harness, `tools/lighthouserc.js`); an item
would need a new `!important`, dependency, font or `innerHTML`; or an after-capture differs from
before by something you cannot attribute.

## Maintenance notes

- UX-1 and CQ-1 interact: a header rule added in `app-shell.css` only sticks while no
  higher-specificity duplicate exists elsewhere. The sheet's own comment warns against reintroducing
  a shell-qualified rail rule below §11; keep that.
- UX-4 creates the only icon source. Future icons are added to `assets/icons.svg` and
  `docs/ASSETS.md`, never as glyph characters.
- CQ-2 and the CLS work (OD-24 / LT-1.9, median 0.1415 against a 0.1 target) touch the same load
  path; a layout change that shifts CLS must be measured with `fb-60/measure.py` (three runs, median)
  because a single run swings 0.106–0.235.
- Deferred on purpose: editor-internal SVG icons, a larger 375 px artboard, a deeper bundle diet.

## Not audited in this run

Backend and Python code, security review (covered by `docs/security/` and plans 001–003), the
Playwright suites' quality, the admin, billing and analytics pages' visuals, and a full innerHTML
sink sweep. The editor's dark theme was not viewed (the screenshot was too large to load); UX-5 and
UX-6 must be checked there during reproduction.
