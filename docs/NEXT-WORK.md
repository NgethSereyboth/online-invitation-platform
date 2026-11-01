# eInvite — What To Do Next

**Compiled:** 2026-11-01 · **Supersedes:** every work order, bug inventory, audit and plan removed in
the same clean-up — `NEXT-WORK-TASK.md`, `FREEBUFF-OPEN-ISSUES-2026-10-21.md`, `UI-VISUAL-AUDIT-FIX-TASK.md`,
`DESIGN-FIX-TASK.md`, `CANVAS-MOTION-FIX-TASK.md`, `IMPROVEMENT-AND-VISUAL-FIX-PLAN-2026-10-22.md`,
`RELEASE-CANDIDATE.md`, `docs/reviews/*`, `docs/superpowers/plans/*`, and the four `plans/00*.md` files
(the last four still exist under `plans/`).

This is the **forward-looking** queue only. What was fixed, what was tried and what was rejected lives in
`docs/HISTORY.md`; every removed source is listed with its reason in `docs/CLEANUP_MANIFEST.md` and can be
read again with `git checkout backup/pre-cleanup -- <path>`.

> **Authority.** If an item here contradicts the repository or its gates, the repository and the gates win.
> Record the discrepancy in `docs/HISTORY.md`, fix this file, and say so. Never bend a gate, budget or
> threshold to match a document (**OD-6**).

---

## 0. State at compilation

| | |
|---|---|
| Version | **0.70.13**, branch `chore/cleanup` (base `fix/2026-10-22-open-issues`) |
| Gate of record | `GATES_PASSED` at `4880fcb` (Stage E, 2026-10-29) — ten phases, **223 pytest passed** |
| Since that matrix | UI commits of 2026-10-30/31 (header, budgets, FB-150/151) and the 2026-11-01 clean-up |
| **Baseline attempt, 2026-11-01** | build, bundles and smoke **passed** (16 pages, 0 console errors, 0 non-2xx). Layout **failed once** on 3 long-task rows (index 375 light 622 ms, 375 dark 613 ms, 1440 light 606 ms; ceiling 600) and **passed on rerun** (`UI_LAYOUT_GUARD_PASSED`, long-task 0 failed, 173 s) with no other browser running. pytest, budgets, LHCI, CSP, canvas and `!important` did **not** run: the runner stops the chain at the first red |
| Clean-up effect | documentation only — no `src/`, no dependency, no build-logic change. `build.py all` → `BUILD_OK`; `build.py bundles --check` → `ROUTE_BUNDLE_CHECK_PASSED` |
| Working rules | **OD-3**: local commits only — no push, PR, merge or tag. Agents never write Khmer. Never stage `artifacts/`, `data/`, `src/python/data/`, `.claude/`, `deploy/sites/` |
| Counts in this file | **15** open/owner-blocked defects (7 fixed in rounds 1–3 and phases 4–6; 1 stuck manual runner) · **36** open work-order tasks · **18** owner-held decisions · **12** verification debts |

**Status legend.** `OPEN` verified still present · `VERIFY` implemented but not re-measured · `OWNER` needs a
decision only the owner can make · `NOT RUN` never executed in a valid environment · `DO NOT START` deferred
by the owner.

**Priority** is the source document's own severity, not re-scored here: **P1** = required for a trustworthy
release, **P2** = quality/hygiene, **P3** = cosmetic or documentation-level. Nothing in the surviving
material is rated **P0** any more; every P0 from the 2026-10-21 order (Pillow CVEs, LHCI config, budget
regressions, CI gaps) was closed and is recorded in `docs/HISTORY.md` §2.

### Progress log

| Date | Item | Commit | Verification |
|---|---|---|---|
| 2026-11-01 | Round 1 live sweep: 114 records + 31 local checks; P1 signed-out-editor JSON redirect fixed and deployed | `fix-round-1` | full suite **223 passed in 883.42 s**; live 302/401 contract and bundle hash verified; two P2s and one stale manual runner logged |
| 2026-11-01 | Round 2 live sweep: 120 records + 42 local checks; three guest-page P2s fixed and deployed | `fix-round-2` (`0604f2c`, `33b43eb`, `ef78d67`) | 0 failed checks; live feature panels 0, credits 1, overflow 0; served JS/CSS hashes match; PNG 39,023 B; full suite **223 passed in 1033.18 s** |
| 2026-11-01 | Round 3 live sweep: 120 records, 118 verified; no new product defects; Brotli 1.2.1 | `940a799` + docs | 44 flow checks, 0 failed; 0 overflow, 0 page errors; 2 × 1440 records external 429 from Sites daily quota; deploy blocked until reset 2026-11-02 |
| 2026-11-01 | Improvement research: guest/editor/forms/Khmer plus invitation metadata, check-in PWA, photo EXIF and multi-tab autosave | `docs/IMPROVEMENT-RESEARCH-2026-11-01.md` | No app source changed; IMP-1–IMP-12 and guideline table recorded; indexability, photo retention and offline scope flagged as owner decisions |
| 2026-11-01 | Full pytest phase of the baseline (`--phase pytest`) | `1bd1717` | **5 failed, 218 passed in 901.65 s** — untriaged, listed below |
| 2026-11-01 | Baseline matrix attempt — build/bundles/smoke green, layout flake, six phases unrun | `—` | `artifacts/next-work/gates/20261101-081428/gates.log`; rerun `…/20261101-082220/gates.log` |
| 2026-11-01 | #2 guest-page `HTTP 401` blocks hidden for anonymous visitors | `bbd3b9d` | bundles rebuilt; `ux9_public_sections_test`, `public_guest_feature_runtime_test`, `bulk_guest_import_test` pass |
| 2026-11-01 | #3 guest-row actions (Edit/Link/QR/Check-in/Remove) delegated again | `12087a8` | handler present in `bundle-guests.js`; guest tests pass; per-action browser tests still owed |
| 2026-11-01 | #6 D-3 second-tab autosave | `a9c5e51` | `connectServer()` refreshes the server revision while preserving a newer local draft; two-tab regression passes |
| 2026-11-01 | #12 admin suspension UI coverage | `98d0306` | `users-v2` Suspended/Active badge pinned on the real row; no product change |
| 2026-11-01 | #14 test data-dir isolation + inline editor runner | `e4a81c0` | autouse `EINVITE_DATA_DIR` restore; `env_isolation_test`; runner boots professional editor v17 |
| 2026-11-01 | Phase-7/8 close-out: generated manifests, Khmer policy | `3d6ff85`, `f2bfcfe` | full suite **230 passed in 1125.10 s (exit 0)**; final build/compile/bundle checks recorded in `PROGRESS.md` |

---

## 1. Open defects

Each row is a code-level bug with a named next action. Where the fix is a product decision, it says so.

| # | Area | Symptom | Pri | Next action | Src |
|---|---|---|---|---|---|
| 1 | Editor | First-paint CLS **0.5003** at 1440 px: late `.ei-section-order-builder` mount shifts the page grid 184 px; `page-experience.js` rebuilds the Pages host with `innerHTML` after the builder exists. Nine CSS reservations were measured and refuted. | P1 | Fix the boot order — render the builder before the Pages host is replaced. Do **not** add another reservation. | FB-75 → OD-23 |
| 2 | Guest page | **Fixed 2026-11-01** (`bbd3b9d`). Every published invitation showed **three `HTTP 401` blocks** (`signup-sheets`, `polls`, `album` fetch host routes anonymously). | fixed | Shipped the documented default: a 401 removes the section. Public read routes with `/api/public/` access checks remain the alternative if guests should read them. | UX-9 / OWNER-QUEUE |
| 3 | Guests | **Fixed 2026-11-01** (`12087a8`). Row actions **Edit / Link / QR / Check-in / Remove did nothing** — the `[data-edit]` delegation was removed in `92806ad`; the functions and API routes were intact. | fixed | Delegated handler on the stable list container; **still owed:** one browser test per action. | UX-8 / OWNER-QUEUE |
| 4 | Templates | `templates.html` CLS **0.604**, never fixed. | P2 | Ship the first screen's geometry in markup, as FB-43/44/67/75 did elsewhere. | D-1 |
| 5 | Guest page | Guest LCP above the 4G target, never fixed. | P2 | Profile with the hero image as the LCP candidate; do not change budgets. | D-2 |
| 6 | Editor | **Fixed 2026-11-01** (`phase-4`). Second tab reused a stale cached revision and its first autosave returned `409 revision_conflict`. | fixed | `connectServer()` refreshes the server row every session; the document is adopted only when no local draft exists. Two-tab regression: `tests/editor_multi_tab_autosave_test.py`. | D-3 |
| 7 | Shell | Topbar still needs a **swipe at 320/375**; measured budget 487 px with the account chip hidden, two rows exceed the 96 px guard limit. | P2 | Accepted partial. Follow-up option: move theme/language into the workspace launcher menu (markup change). | UX-1 |
| 8 | Editor | Artboard default fit **251–275 px** at 1440 (target ≥ 300). | P2 | **Blocked:** fit is height-bound; needs +53 px viewport height or a change to `updateCanvasView`, which the work orders forbid. Declare or lift the constraint. | DESIGN-FIX |
| 9 | Build | Editor route still **1.52 MB** before images. | P2 | Diet arithmetic: ~217 KB must go to reach the 600 ms compile target; deferred candidates total ~148 KB, so the already-shipped split is the working fix. Only a new source split helps. | FB-64/65 |
| 10 | Editor | Design check has **no Publish menu** to join — `#publishBtn` publishes directly, the check is a standalone topbar button. | P3 | Owner default kept: standalone button. Revisit only if a publish pre-flight is approved. | PW-14.4 |
| 11 | Editor | PW-14 tier-2 merges 2, 3, 5, 6 (inspector header, invitation styles, recipes, duplicate links) were **not reproduced** or already satisfied when measured 2026-10-31. | P3 | Do not work from the old list; re-measure before touching anything. | PW-14 |
| 12 | Admin | **Verified implemented 2026-11-01** (`phase-5`). `pages/admin/users.js` reads `users-v2` and renders the Suspended/Active badge. | fixed | Regression pins the real row and badge: `tests/admin_users_suspension_test.py`; no product change needed. | LT-7.2 |
| 13 | Ops | A malformed `EINVITE_FIELD_ENCRYPTION_KEY` is a **soft failure** — logs `source=env-invalid` and falls back to the data-dir key, so a typo silently encrypts under a different key. | P3 | Owner choice: refuse to boot in production, or keep the documented fallback. | LT-7.2 |
| 14 | Tests | **Fixed 2026-11-01** (`phase-6`). An autouse fixture snapshots and restores `EINVITE_DATA_DIR` around every test. | fixed | `tests/env_isolation_test.py` proves the restore; no product change. | LT-7.2 |
| 15 | Templates | `wd-royal-maroon-gold.json` is **hand-edited** (lead `x/w`, English-name and `&` line-height, groom height) because the generator's 14 TTFs are absent and `build_pack.py` refuses estimated layouts. | P3 | Move the edits into `template-pack/generator/layouts.py` / catalog options, then re-run `tools/build-template-pack.py`. Never hand-edit again. | D-8 |
| 16 | Print/PDF | `lt_2_6` MAE sits on its **4.5 tolerance** (4.24–4.75 across identical runs; two different rasterizers). | P3 | Owner choice: move the locked tolerance, or compare text boxes only. Do **not** touch it unilaterally. | LT-7.close |
| 17 | Assets | No icon sprite; 12 display fonts substituted. | P3 | Owner-held: run UX-4 (one inline sprite at `assets/icons.svg` used through `<use>`, 13 pages) and/or buy the 12 OFL families. Budget impact is real. | UX-4 / OWNER-QUEUE |
| 18 | Repo | **15 generated PNGs tracked** under `src/python/data/social-cache/` — runtime state that should never be committed. | P3 | `git rm --cached` in one commit (they stay on disk). Needs a yes. | OWNER-QUEUE |
| 19 | API | Per-key **1000/h limit wired but not flood-tested**; API-key scope is route-level, not per invitation. | P3 | Owner: accept as documented, or commission the 1 000-request proof / narrower scopes. | LT-7.2 |
| 20 | Editor | Headless `set_viewport_size` at 375 crashes the GPU process on a heavy canvas page. | P3 | Reproduce on a real device; acceptance already opens a separate 375 page. No product change unless it reproduces outside headless. | OWNER-QUEUE |
| 21 | Guest page | **Fixed in round 2** (`122a31a`). A missing `/i/<slug>` returned HTTP **200** while the API returned 404. | fixed | `serve_public` now derives status from the published row and returns 404 with `no-store` + `noindex`; legitimate invitations stay 200. | R1 sweep |
| 22 | Guest page | **Fixed in round 2** (`82d16a0`). CSP blocked a generated `data:image/svg+xml` fetch on the guest/export path. | fixed | `inlineImages` copies `data:`/`blob:` sources directly instead of fetching them; export produces a valid PNG with no CSP errors. | R1 sweep |
| 23 | Tests | **Fixture fixed 2026-11-01** (`phase-6`); runner now boots `EInviteProfessionalEditor` v17. Remaining manual assertions are **stuck**: the rotation test compares a rotated AABB to an unrotated overlay box, and the canvas-drag test expects the outline hidden during a drag; both assert the pre-v17 model. | stuck | Do not weaken assertions. Re-baseline the visual-contract tests against the current overlay design before making them part of a gate. Not in pytest. | R1 sweep |

### Baseline suite failures (2026-11-01) — resolved

`tools/run-gates.py --phase pytest` at `1bd1717`: **5 failed, 218 passed in 15:01**. After the
phase-1 fixes (`747c7af`, `4d29920`) and the round-0 editor fixes (`fix-round-0`), the full suite is
**223 passed, 2 warnings in 866.15 s** (`artifacts/verify/pytest-full.log`, 2026-11-01, exit 0).
The two warnings are a teardown-time `sqlite3.OperationalError: unable to open database file` on a
worker thread; they are non-fatal and no test failed.

| Test | Original failure | Resolution |
|---|---|---|
| `ai_resource_scopes_test` | `RemoteDisconnected` (missing `platform_jobs`) | `747c7af` creates the table in the SQLite bootstrap |
| `lt_2_2_khmer_format_test` | `Event details` timeout (harness) | `fix-round-0`: `open_studio_tab('event')` plus the disclosure helper; public-render leg always passed |
| `lt_4_3_color_picker_test` | hidden `#color` | `fix-round-0`: shell mounts in the visible Text group; the test opens its disclosure |
| `lt_4_4_run_typography_test` | hidden `#typographyControls` | `fix-round-0`: waits for `#v20RunFont` inside the real disclosure |
| `template_pack_gallery_test` | removed per-gallery chips | `4d29920`: drives `#studioCategory` / `#studioSearch`, same counts |

Round-0 verdicts and evidence: `bugs/round-0/FINDINGS.md`.

### Phase 0 — baseline (open)
- **NW-0.1** Confirm HEAD, clean tree, state file. **NW-0.2** Run the full ten-phase matrix **once** and
  record it. **NW-0.3** Rebuild the open-items ledger (this file replaces it). **NW-0.4** Evidence tree.
  > Start here: it is the only way later phases can claim a before/after.

### Phase 1 — WCAG 2.2 AA delta (open, no owner needed)
- **NW-1.1** 2.4.11 Focus Not Obscured (Minimum)
- **NW-1.2** 2.5.7 Dragging Movements
- **NW-1.3** 3.3.7 Redundant Entry
- **NW-1.4** 3.3.8 Accessible Authentication (Minimum)
- **NW-1.5** 2.5.8 Target Size (Minimum)
- **NW-1.6** Correct the 2.5.5 vs 2.5.8 wording in the audit

### Phase 2 — CSS architecture (OPEN, **OD-1 approved** 25–40 %)
- **NW-2.1** Inventory and classify. **NW-2.2** Dead rules only. **NW-2.3** Superseded declarations.
  **NW-2.4** Token convergence. **NW-2.5** Stop/report rules. Pixel-diff gated; stop at the first
  unexplained diff. `!important` inventory was 3 791.

### Phase 3 — Dashboard/editor parity (**OD-2 approved** subset)
- **NW-3.1** Gap matrix (read-only). **NW-3.2** Record the decision. **NW-3.3** Implement the approved
  subset (sheets/polls entry points, passkey row + poster type, edit history as a cheap ⋮ link).
  **NW-3.4** Poster create hooks: wire or remove. **NW-3.5** Verify.

### Phase 4 — i18n
- **NW-4.1** `<option>` labels (10 + 2) — **OD-5 confirmed**, runtime rewrite.
- **NW-4.2** `feature-flags.js` bilingual path (11 strings) — **DO NOT START** (OD-8 deferred; never
  machine-translate, never hand-write Khmer).
- **NW-4.3** CSV reconcile (59 stale + 59 fallback rows) — audit first, no blind translation.
- **NW-4.4** Khmer visual verification after the above.

### Phase 5 — test/CI durability
- **NW-5.1** `v27_3_5_release_evidence_test` child-process failure (blocked on the README pin, OD-7
  approved).
- **NW-5.2** `analytics_ingestion_test::test_phase4_rate_limit` order dependence (stale reference).
- **NW-5.3** One-command gate runner. **NW-5.4** Document it.

### Phase 6 — refinement sweep (2 of 6 done)
- **NW-6.3** Floating controls at breakpoints. **NW-6.4** Motion contract audit.
- **NW-6.5** Theme/contrast sweep. **NW-6.6** Privacy route-weight headroom.

### Phase 7 — release readiness
- **NW-7.1** Keep the state file current. **NW-7.2** Authoritative status index + banners.
- **NW-7.3** Release candidate. **NW-7.4** Handoff.

---

## 3. Owner-held decisions (18)

Nothing here is blocked on an engineer; every row needs an answer, a purchase, or an account. Defaults
already in force are listed so work can continue meanwhile.

| # | Item | What the owner must do | Default kept |
|---|---|---|---|
| 1 | Pack display fonts | Add the 12 missing OFL families (Moul, Moulpali, Koulen, Bokor, Battambang, Kantumruy Pro, Cormorant Garamond, Playfair Display, Great Vibes, Cinzel, Montserrat, Jost) with subset WOFF2 + SHA-256 + licence + contract entry. | Nearest registry face; templates unaffected by a later swap. |
| 2 | Khmer copy — template pack | Native review of `template-pack/copy-bank.json` (117 keys, 48 flagged `med`). | Copy ships as drafted. |
| 3 | Khmer copy — colour picker | Khmer for 10 labels/verdicts. | English-only popover; checker passes. |
| 4 | Khmer copy — typography inspector | Khmer for 6 labels/statuses. | English-only group; checker passes. |
| 5 | Khmer copy — shared header | 72 occurrences / 42 unique strings. | English until supplied. |
| 6 | Khmer line-height (A4) | Confirm the `Math.max(1.15, lineHeight, recommended)` change on two existing drafts. | Wider value wins; floor 1.7. |
| 7 | `wd-royal-maroon-gold` residual | Shorten `…-p1-text-13` copy or widen its box (10 px floor still overflows 6.2 px). | Pack unchanged. |
| 8 | Demo host | Connect a Render/host account and approve a push, or keep the demo local. | Local at `deploy/demo/README.md`. |
| 9 | Icon sprite (UX-4) | Approve or decline the inline-sprite migration. | Glyphs unchanged. |
| 10 | API-key scope | Per invitation / guest list, or keep route-level. | Route-level (`invitations:*`, `rsvps:read`, `*`). |
| 11 | Per-key rate limit | Accept as documented or commission a flood test. | 1 000/h, unproven. |
| 12 | Malformed encryption key | Refuse production boot, or keep fallback. | Soft fallback, documented. |
| 13 | `lt_2_6` PDF tolerance | Move 4.5, or compare text boxes only. | 4.5, unchanged. |
| 14 | Tracked PNGs | Approve `git rm --cached` for 15 social-cache renders. | Still tracked. |
| 15 | Release 1.0.0 external evidence | Commission load test, DR drill, penetration test (templates ready). | `CERTIFICATION.md` §1–§5 `pending`. |
| 16 | Guest-page 401 blocks | Product choice: public read routes or hide when unauthenticated. | Blocks show (bug). |
| 17 | Artboard fit / viewport rule | Lift the “don't change `updateCanvasView`” rule, or accept 251–275 px. | Accepted as blocked. |
| 18 | Clean-up leftovers | Decide on deleting `tests/` (the gate contract) and `artifacts/` (2.7 GB, gitignored, no git backup). | Both kept; one revertable commit each. |

---

## 4. Security and certification backlog

Implemented and covered by tests — **verify, don't rebuild**: account lockout, MFA recovery codes,
security notification emails, JIT elevation, resource-scoped permissions, field encryption, durable
webhooks, scoped API keys. (`tests/security_account_lockout_test.py`, `security_mfa_recovery_test.py`,
`security_notification_emails_test.py`, `ai_jit_enforcement_test.py`, `ai_resource_scopes_test.py`,
`jit_elevation_atomic_test.py`.)

Still open:

| Item | State | Next action | Src |
|---|---|---|---|
| SAST / SCA / SBOM tooling | `docs/security/CI-SECURITY.md` exists; no chapter-10 pipeline | Choose tools, wire into CI, publish an SBOM per release | ROADMAP-V2 §2.7 |
| CSP report-only monitoring | Gate exists (`csp-violation-check.py`, 13/13, 0 violations); no report collector | Enable report-only on the hosted origin and collect for a week | ROADMAP-V2 §2.8 |
| Rate-limit coverage proof | `docs/security/RATE-LIMIT-COVERAGE.md` | Prove per-key and per-route limits under load (see owner #11) | ROADMAP-V2 §2.9 |
| ASVS L2 gap analysis | `docs/security/ASVS-L2-GAP-ANALYSIS.md` | Close the listed gaps before 1.0.0 | docs/security |
| External assessments | Templates only | Load test (k6), DR drill with witness, independent pen test (ASVS 5.0.0 L2) | LT-8.3 |

The 2026-10-21 reflected-HTML-injection item in `serve_public` is **closed** — every interpolated value is
`html.escape`d (`src/python/server.py:11072–11073`); no follow-up needed.

---

## 5. Accessibility backlog

- **WCAG 2.2 AA delta:** the six Phase-1 asks above (`NW-1.1`–`NW-1.6`). This is the only a11y work not
  covered by the 2.1 audit.
- **Khmer-specific partials (35):** no `:lang(km)` overrides yet; needs typography and line-height rules,
  plus dynamic `lang` on `public.html`.
- **Missing labels** on search/filter selects in `guests`, `responses`, `templates`, `materials`.
- **Closed, do not redo:** skip-to-content on all 16 pages, `<main>` on dashboard, light-mode
  `--text-3`/`--app-faint` contrast — applied and measured in the Phase 2b pass.
- Baseline of record: 155 pass / 35 partial / 7 fail / 59 n/a of 256; axe a11y **1.00** on all 16 routes.

---

## 6. Verification debt (nothing here is a code change)

| # | Debt | Why it matters |
|---|---|---|
| 1 | Full ten-phase matrix still not green end to end since 2026-10-30/31; the 2026-11-01 attempt stopped at layout | build/bundles/smoke pass; layout grazed 600 ms once (622/613/606) and passed quiet; pytest, budgets, LHCI, CSP, canvas, `!important` unrun — finish the chain phase by phase |
| 2 | Post-clean-up verification was targeted only (build, bundles, 8 doc tests, server boot) | Proportional to a docs-only diff, but not a substitute for the matrix. |
| 3 | Canvas **visual** gate not run — frozen baseline lives on the owner's Windows box | The motion gate (22/0/2) is behavioural, not pixel. Record `NOT RUN` rather than invent a baseline. |
| 4 | Canvas **performance** gate blocked by hardware | Record `environment-blocked`. |
| 5 | Real-device checklist (`docs/qa/DEVICE-CHECKLIST.md`) not run | Native Windows/Linux, WebKit, Firefox, Android, iOS all uncertified. |
| 6 | RILL walkthrough never executed (FB-18) | P2; local run only, public URL not required. |
| 7 | `make test` full suite (223) not run since the clean-up | Four tests read `docs/` inputs; they passed, but the suite is the contract. |
| 8 | 226 zero-test files; v55/v14 not in `run-gates` (FB-08) | Coverage looks bigger than it is. |
| 9 | pytest not in CI; branch-trigger gap (FB-07) | Local-only release makes this survivable, not good. |
| 10 | Intermittent app-server readiness flake (FB-09) | Causes spurious reds in browser gates. |
| 11 | Dependabot reports **92 default-branch alerts / 49 unique advisories**: 82 Pillow alerts are already fixed on this branch by `13.0.0`; 3 Brotli alerts remain; the 7 old npm alerts are absent from this lockfile. | See `docs/security/DEPENDABOT-ALERTS-2026-11-01.md`; merge/cherry-pick the pins to `main` and upgrade Brotli to 1.2.1. |
| 12 | Long-task ceiling is being grazed: 606–622 ms under load vs the frozen 600 ms | Do **not** raise the ceiling (OD-6). Re-measure quiet before treating a red as a regression; a genuine fix must cut work on `index.html`. |

---

## 7. Hosting and production

- Static front end on Sites + PC backend through a Cloudflare Quick Tunnel is the current model. The
  tunnel is a single point of failure and the origin lives in D1 (`backend_config`).
- Real-phone checklist still unrun — the demo needs a host a phone can reach (owner #8).
- Production domain activation needs a DNS/certificate provider; native installers, external AI
  providers, payment, monitoring, malware scanning and external object storage all need credentials.
- `docs/guides/PRODUCTION_LAUNCH_CHECKLIST.md` remains the gate for anything public.

---

## 8. Documentation and process debt left by the clean-up

1. `WORKORDER_FREEBUFF.md` is referenced by no surviving file and has never existed in this checkout. If
   the owner still has it, it should land **before** the next work wave so its Phase 9 (test rebuild)
   does not conflict with `tests/` being kept.
2. `tests/` was kept against Group C of the clean-up order because it is the verification contract;
   deletion is owner item #18.
3. `artifacts/` (2.7 GB) was **not** deleted: gitignored means no git backup, and the order forbids
   deleting before a backup exists. Owner item #18.
4. `README.md` is SHA-256 pinned by `tests/v27_3_5_release_evidence_test.py` (OD-7 normalises line
   endings). Edit it only together with the pinned digest.
5. Seven `docs/V0_52_*.md` files, `MULTI_HOST_DEPLOYMENT_REPORT.md` and `docs/ASSETS.md` are read by
   tests — keep them until those tests change. `docs/FONT_LICENSES_AND_REGISTRY.md` and
   `docs/LEGACY-VERSION-HISTORY.md` are read by the font registry and a version test, so both stay put.

---

## 9. Closed — do not reopen

Heuristic false positives and accepted non-issues, from the visual audit and the bug inventories:
clipping/overlap rows E2, M1, M2-spacing; the "112 dead controls" detector; billing-gradient contrast;
admin mock-403 rows; sticky-header occlusion; icon-only buttons flagged as tiny text; `color(srgb…)`
contrast; `h1 → h3` on the editor (best practice, fixed anyway); 89 `:focus{outline:none}` rules (all pair
with a paint change); `transition: all` (count 0); `lt_2_6` as a "flake" (it was two real print defects,
D-5).

Decisions that close items: **OD-4** resize-handle exception, **OD-5** Khmer `<option>` rewrite,
**OD-8** feature-flags translation (deferred, not failed), **v14** stays non-blocking, **OD-3** local-only
release, **OD-6** no threshold changes.

---

## 10. Suggested execution order

Each wave ends with `python3 build.py all`, `python3 build.py bundles --check` and
`python3 tools/run-gates.py --phase all`; a wave that cannot pass its gate does not start the next.

1. **Baseline** — NW-0.2: run the matrix, record it (verification debt #1). Nothing else is honest before this.
2. **User-visible correctness** — guest-page 401 blocks (#2), dead guest-row actions (#3). Both are P1 and
   both are small; #2 needs the owner's default or a decision.
3. **WCAG 2.2 delta** — NW-1.1 … NW-1.6, one commit per criterion, audit updated with each.
4. **Test durability** — NW-5.1, NW-5.2, NW-5.3: make the suite trustworthy before trusting it again.
5. **CSS architecture** — NW-2.1 … NW-2.5 under OD-1's 25–40 % envelope, pixel-diff gated.
6. **i18n** — NW-4.1 and NW-4.3 (skip NW-4.2), then NW-4.4 visual proof.
7. **Performance** — OD-23 CLS boot order (#1), D-1 templates CLS (#4), D-2 guest LCP (#5).
8. **Parity** — NW-3.1 … NW-3.5 under the approved OD-2 subset.
9. **Release readiness** — NW-7.1 … NW-7.4, then the external evidence in §4. 1.0.0 stays uncertified
   until load, DR and pen tests exist.

---

## 11. Traceability

| Removed source | Section here | Restore |
|---|---|---|
| `NEXT-WORK-TASK.md` | §2 phases, §10 | `git checkout backup/pre-cleanup -- NEXT-WORK-TASK.md` |
| `FREEBUFF-OPEN-ISSUES-2026-10-21.md` | §1, §4, OD register | `… -- FREEBUFF-OPEN-ISSUES-2026-10-21.md` |
| `UI-VISUAL-AUDIT-FIX-TASK.md` | §1 rows 4/7, §9 | `… -- UI-VISUAL-AUDIT-FIX-TASK.md` |
| `DESIGN-FIX-TASK.md` | §1 row 8 | `… -- DESIGN-FIX-TASK.md` |
| `CANVAS-MOTION-FIX-TASK.md` | §6 rows 3–4 | `… -- CANVAS-MOTION-FIX-TASK.md` |
| `IMPROVEMENT-AND-VISUAL-FIX-PLAN-2026-10-22.md` | §1, §10 | `… -- IMPROVEMENT-AND-VISUAL-FIX-PLAN-2026-10-22.md` |
| `docs/ROADMAP-V2.md` §2 | §4 | `… -- docs/ROADMAP-V2.md` |
| `docs/a11y/WCAG-AA-AUDIT.md` | §5 | still on disk |
| `artifacts/next-work/OWNER-QUEUE.md` | §3 | still on disk (gitignored) |
| `plans/001…004` | superseded: all four shipped; plan 002’s 404 path is live (`src/python/server.py:3998`) | `git checkout backup/pre-cleanup -- plans/` |
| Everything ever fixed or rejected | `docs/HISTORY.md` | — |
