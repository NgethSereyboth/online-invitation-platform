# eInvite — Status Read, Improvement Plan & Visual Bug Fix Plan

**Written:** 2026-10-22 (Thu) · **Repo:** `/media/ngethsereyboth/LocalDisk/eInvite/einvite-platform`
**Branch read:** `fix/2026-10-22-open-issues` (local only, OD-3) · **Code changed by writing this:** none
**Basis:** repo ledgers, `git` reflog, the work orders, and the 2026-10-21 Khmer-sweep screenshots in `artifacts/next-work/nw-4-4/after/`. I did **not** run any gate or open the app myself; gate numbers below are quoted from your own ledgers.

---

## 1. Where you are

### 1.1 The product
Self-hosted, bilingual (EN + Khmer) invitation design and event platform: 16 pages, Python backend (`src/python`), governed AI agent (80 tools), Postgres/S3-capable storage layer, laptop installer. Public version V0.52; internal milestone V53.1; hardening V54.

### 1.2 The branch
`fix/2026-10-22-open-issues` is **15 commits** past `6f7de27` (the last pushed commit). `main` is still at `50721ef`. The newest commit (`fa1d657`, docs reconcile) landed around 09:32 this morning, so Freebuff is mid-run.

| Work-order item | State |
|---|---|
| FB-01 Pillow CVEs · FB-02 LHCI server/artifacts · FB-03 admin +716 B · FB-04 README digest (OD-7) | **Done** |
| FB-05 child-process capture · FB-06 `reproduce.sh` fails closed · FB-07 pytest CI workflow · FB-08 zero-test runners · FB-09 server-readiness flake · FB-10 npm audit | **Done** |
| FB-11 v14 note · FB-12/22 doc truth-up · FB-13 rate-limit reference · FB-14 i18n audit | **Done** (docs/audit only; nothing translated) |
| FB-15 final gate matrix | **Started** — smoke, pip-audit, v14, v55 logs exist; no repeat full-suite logs yet |
| FB-19 CSS `!important` cleanup (OD-1, 25–40 %) | Approved, **not started** |
| FB-20 dashboard parity subset (OD-2) | Approved, **not started** |
| FB-16/17/18 canvas visual, canvas perf, RILL | Blocked by environment (see §4) |
| FB-21 Khmer for feature flags (OD-8) | **Deferred** by you |

### 1.3 Gate status (quoted from `RELEASE-CANDIDATE.md` addendum)
- Build, bundles, v55 budget: PASS · pip-audit: clean · `npm audit`: 0 · LHCI autorun: 16/16 URLs, a11y 1.00
- Full pytest: **146 passed / 0 failed** (first fully green run, 4:03). **Repeatability not yet proven** — you need consecutive green runs before calling it stable.
- v14: known red, non-blocking by your decision · Canvas acceptance: 22/0/2 · Canvas perf/visual: not verified on this machine

### 1.4 The honest weak spots
1. **4,033 `!important` declarations** across ~130 CSS files, layered as patch sheets (`editor-suite` 659, `canvas-plus` 542, `modern-ui` 296, `stabilized` 220, `final-polish` 217, `ux-refine` 209 = 2,143 in those six). This is the main source of the visual bugs below.
2. **Mobile/tablet editor layout** and the **app header at ≤ 375 px** still look broken in the latest captures (§2), even though the older audit marks them closed.
3. **~305 i18n fallback rows** — Khmer pages show English strings mixed in.
4. Nothing has run on **real CI** for this branch (no PR/push by design).

---

## 2. Visual bugs found

Source: `artifacts/next-work/nw-4-4/after/*.png` (2026-10-21, EN/KM, 375/768/1440). Those shots pre-date commit `a71746b` and may have used a static server without the API, so **Phase 0 re-captures at HEAD before anything is fixed**. Severity uses the scale from `UI-VISUAL-AUDIT-FIX-TASK.md`.

| ID | Where | What I saw | Where to look | Sev |
|---|---|---|---|---|
| **VB-01** | Dashboard signed-out, 1440 | Auth card and hero panel have **no inner padding**: inputs and labels touch the card edges, hero headline and bullets sit flush on the panel's left edge, footer links ("Forgot password" / "Privacy") sit on the rounded bottom edge, and the brand icon overlaps the card's top edge | auth-pane / `.login` rules in `dashboard-page.css`, `canva-ui.css` — look for padding being overridden by a later sheet | P1 |
| **VB-02** | All app pages at 375 (templates, guests, admin, dashboard) | Header eats ~170 of 667 px; **blank white rounded squares** (buttons with no visible icon/label); breadcrumb renders like an input box; language switch drops to its own row | shared app header (`app-shell.css`, `workspace.css`); check whether the icons fail to render or the buttons have no content | P1 |
| **VB-03** | Templates, 768 | Breadcrumb "Workspace / Template Studio" wraps and **overlaps** a Khmer-labelled button in the header | header grid needs `min-width:0`, ellipsis on the crumb, no wrap | P1 |
| **VB-04** | Editor, 375 | Empty header squares; language card takes a full row; "Hide controls ▴" renders oversized and pushes Style/Font fields off-screen; **canvas squeezed to ~190 px tall**; vertical tool palette sits on top of the canvas | `mobile-editor.js`, `editor-responsive-contract.css`, `studio-experience.css` | P1 |
| **VB-05** | Editor, 768 | Typography toolbar clipped at right (Color swatch cut), context toolbar clips "Shape", selection toolbar uses oversized bold text and clips at "Tidy", zoom bar partly covered by the bottom action pill, title truncated to "Khmer swee" with a stray "/" | `editor-responsive-contract.css`, `typography-system.css`, `organized/editor-layout-stability.css` | P1/P2 |
| **VB-06** | Editor canvas, 768 | Headline "Khmer sweep" is cropped top and bottom inside its box | Could be the seeded document (88 px display text) rather than a bug — confirm with a stock template first | P2 (low confidence) |
| **VB-07** | KM captures | Language pill shows **English active** while parts of the page are Khmer; headings and subtitles stay English (fallback rows) | Pill state is a possible bug; the English strings belong to FB-14/OD-8 | P2 |
| **VB-08** | Guests/admin/templates, KM | Khmer H1s render in a thin slanted display face unlike the body text | Check the heading font stack under `:lang(km)` and that the self-hosted Noto Khmer loads | P2 (verify) |
| **VB-09** | Older audit items | Right inspector past viewport at 1440, two zoom readouts, device-toggle label collision, dark-theme contrast (Built-in chips 1.03:1, public venue 1.27:1), 8–11 px text, horizontal scroll at 320 px (analytics 395, admin 371, privacy 364, templates 345) | Ledgers say closed; I have **no fresh capture** of dark theme or 320 px, so re-verify | — |

Do **not** chase the documented false positives (billing gradient contrast, sticky-header occlusion, admin mock-403 rows, etc. — work order §10).

---

## 3. Visual fix plan

**Ground rules (unchanged):** no new `!important`, no budget/threshold changes, no frozen canvas files, every new string bilingual, `python3 build.py all` + `python3 build.py bundles --check` after each `src/` edit, local commits only, one browser at a time. Fix at the cause in the correct sheet; do not paper over with another override.

### Phase 0 — Confirm at HEAD (≈ 1 h)
1. Start the dev server (recipe in work order §4), then capture before-state:
   `.venv/bin/python tools/ui-audit-capture.py --base http://127.0.0.1:8124 --out artifacts/visual-fix/before` — narrow with `--only/--states/--viewports/--themes/--langs` (check `--help`) to: dashboard, templates, guests, admin, index × 1440, 1024, 768, 375, 320 × light+dark × en+km.
2. Mark each VB-xx *confirmed / not reproduced / artefact* in `artifacts/visual-fix/CONFIRMED.md`. Only confirmed items proceed.

### Phase 1 — Quick, high-impact (≈ 1 day)
- **VB-01** restore auth-card and hero padding (≥ 24 px card, ≥ 32 px hero); footer links inside the card padding; brand lockup aligned. *Accept:* at 1440/1024/375, input left edge ≥ 16 px inside the card; footer links clear the radius.
- **VB-02/03** one shared header rule: grid `brand | crumb | actions`, `min-width:0`, crumb ellipsis, language switch inline at ≥ 375 (compact at 320); every icon-only button gets a visible icon and an `aria-label`. *Accept:* no empty button, no overlap, header ≤ 96 px at 375.

### Phase 2 — Editor responsive contract (≈ 2–3 days)
- Decide and write down the 721–1024 px contract in `editor-responsive-contract.css`: either full desktop layout or mobile mode with panes **closed by default** (never an empty sheet over the canvas).
- **VB-04** mobile: one toolbar row per surface, language switch moved into the menu, canvas minimum height ≥ 50 % of viewport, tool palette docked to an edge.
- **VB-05** one toolbar surface per breakpoint with documented `z-index`; selection toolbar uses the normal toolbar type scale and scrolls instead of clipping; zoom bar and action pill share a track.
- **VB-06** reproduce with a stock template; fix only if real.

### Phase 3 — Language and type (≈ 1 day)
- **VB-07** drive the language pill from the same state that sets `lang` on `<html>`; add a Playwright check that pill, `lang`, and visible spans agree.
- **VB-08** unify the Khmer heading stack with body; keep `line-height ≥ 1.6` for `:lang(km)`.
- English leftovers stay English until you supply Khmer (OD-8 deferred; no machine translation).

### Phase 4 — Regression guard (≈ 0.5 day)
Add one new check (new file under `tools/`, do not edit frozen gates) that fails when, across 320/375/768/1024/1440 × light/dark × en/km: `scrollWidth > innerWidth`; any visible button has no accessible name or no visible content; header children overlap; auth-card padding < 16 px. Wire it as an extra `tools/run-gates.py` phase.

### Phase 5 — Re-capture and commit
After shots to `artifacts/visual-fix/after`, side-by-side review per VB-xx, then one commit per bug: `fix(ui): <what> (VB-0n)`.

---

## 4. Improvement plan (everything else)

| Pri | Item | Next step |
|---|---|---|
| P0 | **FB-15 gate matrix** | Run the full suite 3× back-to-back (proves repeatability), then fill the matrix; keep NOT RUN rows honest |
| P1 | **FB-19 CSS cleanup** | Target 1,008–1,613 of 4,033 occurrences (25–40 %); dead rules first; stop at first unexplained pixel diff. **Do it after the visual fixes** so the diff baseline is the fixed UI |
| P1 | **FB-20 dashboard parity** | Passkey button, poster type, one card linking sheets + polls, ⋮ "Version history" link; document the role picker as absent |
| P2 | **FB-16/17 canvas gates** | Only you can unblock: copy `artifacts/canvas-motion/baseline/` from the Windows machine to this one |
| P2 | **FB-18 RILL walkthrough** | Run the nine-step flow once locally with a throwaway account |
| P2 | **i18n** | When ready, hand over the ~305 fallback rows (`docs/i18n/TRANSLATIONS.csv`) for owner-supplied Khmer |
| P3 | **Repo hygiene** | ~15 task/prompt `.md` files and scratch dirs at root (`pip-*`, `tmp*`, `.scan-*`, `.cache/puppeteer`) bury the project; delete by hand only (the rules forbid `git clean`), and `package.json` is still named `dsh-profile-test` |
| P3 | **Release path** | CI/Dependabot closure and merging 25 commits onto `main` need a push — your call (OD-3) |

---

## 5. Suggested order

1. Add this plan to the work order as **FB-23 (visual fixes)** with a dated line in §13 — it is not in the approved scope, so Freebuff could otherwise treat it as drift.
2. Phase 0 → 1 → 2 → 3 → 4 → 5 (≈ 5–6 days).
3. FB-19, then FB-20, then FB-15 last (so the final matrix reflects the real final UI).

## 6. Not verified
- Screenshots are from 2026-10-21, not from HEAD; VB-01–VB-08 are visual reads, not DOM checks.
- Dark theme and 320 px have no fresh evidence on this machine.
- All gate results are your ledgers' numbers; I ran nothing.
