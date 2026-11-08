# eInvite — Playwright QA & UX Audit Report

**Date:** 2026-11-06
**Last verified:** 2026-11-07
**Target:** `einvite-platform` (static front-end bundles + Python/SQLite server)
**Harness:** `@playwright/test@1.65.0`, `@axe-core/playwright@4.14.0`, TypeScript
**Origin under test:** `http://127.0.0.1:4310` with `EINVITE_DATA_DIR=artifacts/playwright-e2e/data`
**Application source:** not modified during the original test-only pass. D1–D7 and D10–D12 were fixed afterward (§4); D8 was fixed and D9 was corrected test-side on 2026-11-07. The pre-fix results and the final clean-DB runs are both recorded below.

---

## 1. Result summary

| Project | Result | Log |
|---|---|---|
| Chromium (full, 1440×900) | **155 passed / 13 failed** | `artifacts/playwright-e2e/logs/chromium-final3.log` |
| Firefox (smoke, 1440×900) | 33 passed | `logs/firefox-smoke.log` |
| Mobile Chrome (Pixel 7) | 49 passed | `logs/mobile.log` |
| Tablet (768×1024, touch) | 10 passed | `logs/tablet.log` |
| Visual baselines (re-run) | 11 passed | `logs/visual-verify.log` |
| Flake audit (`@smoke`, `--repeat-each=3`, retries 0) | 99 passed | `logs/flake.log` |
| WebKit (smoke, 2026-11-07) | **33 passed** — browser launches; 33 route checks signed out/in + 404 | `logs/webkit-retry.log` |
| Chromium post-fix (clean DB) | **157 passed / 11 failed** — D1, D2 and D12 pass; remaining D3–D11 (D6/D9 twice, D5 failed this run) | `logs/chromium-final-d2.log` |
| Focused a11y post-fix | **20 passed** — every route, guest desktop/mobile, templates/account, create dialog | `logs/verify-a11y4.log` |
| Chromium post-a11y (clean DB) | **163 passed / 5 failed** — D3–D7 pass; remaining D8–D11 (D9 twice) | `logs/chromium-final-a11y2.log` |
| Chromium post-keyboard (D10/D11, clean DB) | **165 passed / 3 failed** — D10/D11 pass; remaining D8 and D9 (twice) | `logs/chromium-clean-final.log` |
| Chromium accumulated-data check | **161 passed / 7 failed** — D8/D9 plus four dashboard interaction/capture timeouts after the database accumulated 132 invitations (106 owner rows); all four pass on the clean baseline | `logs/chromium-final-a11y4.log` |
| Chromium final (D8 fixed, D9 test corrected, clean DB) | **169 passed / 0 failed** — full suite, including the dedicated Load-more and server-filter test | `logs/chromium-filters-full.log` |
| Chromium volume recheck (177 invitations, 144 owner rows) | **26 passed / 0 failed** — dashboard journeys, UX captures and API contracts | `logs/chromium-filters-volume.log` |
| WebKit final (2026-11-07) | **33 passed** — route smoke after D8/D9 | `logs/webkit-d8-d9-final.log` |
| WebKit final-tree rerun (2026-11-07) | **32 passed / 1 failed** — signed-out `/index.html` raised one intermittent `EInviteMotion` page error; the same test passed 5/5 in isolation | `logs/webkit-filters-final.log`, `logs/webkit-index-repeat.log` |

Every count above comes from the recorded log; no result is inferred. The original 13 Chromium
failures are accounted for by **11 distinct defects**: D6 and D9 each fail at two viewports and
D12 adds the thirteenth test, while D5 (guest/public contrast) is intermittent. The first
post-fix run (D1, D2, D12) gave **157 passed / 11 failed**. After the accessibility cluster
(D3–D7), the focused `06-a11y` and `17-keyboard` specs passed **28/28** together. The keyboard
cluster (D10/D11) then passed on a clean database: **165 passed / 3 failed**, with only D8 and D9
(two tests) left. A separate check against the accumulated 132-invitation dataset gave
**161 passed / 7 failed**: D8 and D9 plus four dashboard interaction/capture timeouts. All four
pass on the clean baseline; they are recorded under D8's all-row rendering impact. An earlier
141-invitation run gave 147/21; the nine extra failures were dashboard boot/hydration timeouts,
fixed by revealing the shell before the heavy list load. D8 and D9 are now closed: the final
clean-DB Chromium run is **169/169**, the 177-invitation subset is **26/26**, and WebKit route smoke
is **33/33**. D8 removed all-row list fetches; D9 was a test-side selector fix, with the visible
topbar switch already driving the guest renderer.

### Reproduction

```bash
# 1. isolated server (persistent; not the user's 4175 instance)
EINVITE_DATA_DIR="$PWD/artifacts/playwright-e2e/data" \
EINVITE_ALLOW_NO_SCANNER=1 EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP=1 \
EINVITE_ADMIN_EMAIL="admin@einvite.test" PYTHONPATH=src/python:. \
.venv/bin/python src/python/server.py --port 4310

# 2. suite
npx playwright test --config=e2e/playwright.config.ts --project=chromium
```

Global setup waits for `/api/health`, creates three accounts (owner, second tenant, admin), a
per-run throwaway account for login-failure tests, a published invitation, a second tenant's
published invitation, an unpublished draft, and writes storage states under
`artifacts/playwright-e2e/auth/`. Login-failure tests never consume a real account's
five-attempt lockout budget.

---

## 2. Coverage

### Routes (16 shipped pages + guest deep link + aliases)

`/index.html` editor · `/dashboard.html` · `/templates.html` · `/guests.html` ·
`/responses.html` · `/analytics.html` · `/materials.html` · `/checkin.html` · `/account.html` ·
`/billing.html` · `/admin.html` · `/public.html` · `/privacy.html` · `/reset.html` ·
`/verify.html` · `/designer.html` · `/i/<slug>` · aliases `/dashboard`, `/templates`, `/guests`,
`/designer`, `/account` (`src/python/server.py:271`).

### Spec matrix

| Spec | Tags | What it proves |
|---|---|---|
| `01-smoke-routes` | `@smoke` | Each route returns 200, renders a non-empty main, no console error/page error/failed request; unknown route is 404 |
| `02-auth` | `@auth @smoke` | Empty/invalid input, wrong password, valid sign-in, sign-out, cookie flags, signed-out account/admin posture |
| `03-dashboard` | `@smoke` | Card metadata, both open paths, create flow + server row |
| `04-editor` | `@smoke` | Deep-link hydration, field edit + undo, command palette, publish → public page |
| `05-guest-rsvp` | `@smoke` | Guest render, RSVP + wishes write-through, empty/double submit, unpublished 404 |
| `06-a11y` | `@a11y` | axe WCAG 2.0/2.1 A/AA scans on 12 screens + dialog |
| `07-visual` | `@visual` | 11 deterministic screenshot baselines |
| `08-responsive` | `@responsive` | 320/390/768/1440 overflow, guest and editor usability |
| `09-network` | `@network` | 500, aborted and offline dependencies degrade without page errors |
| `10-api` | `@api` | Status/JSON contracts, tenant isolation, revision conflict, CSRF, RSVP validation, pagination |
| `11-forms` | `@forms` | Boundaries: 7-char and 240-char passwords, unicode email/title, 120-char limit |
| `12-i18n` | `@i18n` | Shell EN↔KM, persistence, guest switcher, Khmer date, 320 px layout |
| `13-security` | `@security` | Anonymous mutation, cross-tenant read, XSS title, cookie flags |
| `14-navigation` | `@navigation` | Aliases, 404, history, refresh, two tabs, deep link |
| `15-persistence` | `@persistence` | Theme and server row survive reload; sign-out clears session; clean profile |
| `16-performance` | `@performance` | DCL/LCP/requests/transfer budgets per route |
| `17-keyboard` | `@a11y` | Skip link, tab order, focus rings, labels, heading hierarchy |
| `18-ux` | `@ux` | Screenshot inventory, empty-state guidance, error quality, overflow menu |

### Capability matrix

| Capability | Status | Evidence |
|---|---|---|
| Register / login / logout / session flags | PASS | `02-auth`; cookie `einvite_session` HttpOnly, SameSite=Lax |
| Invitation create / list / publish | PASS (with editor defect D2) | `04-editor` publish test, `10-api` lifecycle |
| Guest page + RSVP + wishes | PASS | `05-guest-rsvp`, `10-api` valid RSVP/wish |
| Cross-tenant isolation | PASS | `10-api` 404 on foreign id; list excludes tenant B |
| CSRF gate | PASS | `10-api` missing token 403/401; cookie-derived token 201 |
| Pagination (`limit`/`offset`) | PASS | `10-api`: `limit=1` returns exactly one row and `offset=1` a different row; `status` and `q` filter before paging and an unknown status is a 400; dashboard requests 25-row batches and offers Load more |
| Guest language switching | PASS | `12-i18n`: visible topbar switch changes copy, `lang` and Khmer date at 1440 and 320; `lt_4_1` contract **1/1** |
| Keyboard bypass (skip link) | PASS | `17-keyboard`: skip link is first Tab stop; Enter moves focus to `#main` (D10 fixed) |
| Guest page top-level heading | PASS | `17-keyboard`: exactly one `h1` inside `#publicRoot` (D11 fixed) |
| WCAG AA on 6 screens/dialog | **FAIL** | axe (D3–D7) |
| File uploads / materials | NOT TESTED | page renders; no upload journey exercised |
| Admin mutations | NOT TESTED | admin console access checked only |
| Check-in scanning | NOT TESTED | server runs with `EINVITE_ALLOW_NO_SCANNER=1` |
| Email verification / password reset delivery | NOT TESTED | no SMTP in this environment; page load only |
| Payments / billing provider | NOT APPLICABLE | no payment integration is present |
| RTL (Arabic/Hebrew) | NOT APPLICABLE | product ships EN/KM only |
| AI generation | NOT APPLICABLE | no AI capability in this build |

---

## 3. Methodology and anti-flake measures

- Every test gets a fresh browser context; signed-in suites reuse a storage state created once by
  global setup. Per-test API logins were removed after they exhausted the server's
  **30 logins / 600 s / IP** limit; the API fixture now reuses the stored `einvite_csrf` cookie as
  `X-CSRF-Token` (verified: header = cookie value → 201, absent → 403).
- Zero `waitForTimeout` in specs; waits are on observable state (`expect`, `waitForFunction`,
  `expect.poll`). The only explicit waits are inside the performance observer poll.
- Chromium runs 3 workers. Publishing and other global mutations use
  `test.describe.configure({ lock: '-exclusive-' })`.
- Local retries are **0**; the flake audit ran the smoke spec three times and passed 99/99.
- Visual baselines are committed under `e2e/__screenshots__/`; a second run passed all 11 with
  `maxDiffPixelRatio: 0.02`.
- Mutating editor tests use private invitations. An earlier revision edited the shared seed and
  its autosave raced every title assertion in the run; that was a harness bug, not a product one.
- `trace: 'on-first-retry'`, `video: 'retain-on-failure'`, `screenshot: 'only-on-failure'`;
  reporters: `failures`, HTML (failures only), JSON, JUnit.

---

## 4. Defects

Severity uses impact × reachability for a hosting customer. Each defect has a failing spec line
plus a second signal (probe result, DOM state, or a second viewport).

### D1 — Dashboard card cover is a dead control (P1) — FIXED 2026-11-06

- **Spec:** `e2e/specs/03-dashboard.spec.ts:27`
- **Expected:** clicking the invitation cover opens that invitation's editor.
- **Actual:** URL stays `dashboard.html`; no navigation after 15 s.
- **Second signal:** `artifacts/playwright-e2e/dom-probe2.mjs` — cover click → `dashboard.html`;
  the overflow menu's Edit → `/invitations/<id>/editor` (works). So the data and route exist; the
  cover's click handler/affordance does not.
- **Artifact:** `artifacts/playwright-e2e/test-results/03-dashboard--smoke-dashbo-f4ff5-card-cover-opens-the-editor-chromium/`
  (screenshot, video, error context).
- **Impact:** the largest, most obvious target on every card does nothing; users must discover the
  overflow menu.
- **Fix (2026-11-06):** the cover handler in `src/js/final-polish.js` targeted `.actions [data-edit]`,
  but the card markup has no `.actions`; the Edit button lives in `.invite-overflow__menu`. The
  handler now clicks that button (`.actions` kept as fallback), and the same one-line patch was
  applied to the served bundles. `e2e/specs/03-dashboard.spec.ts:27` passes post-fix (1/1 focused
  and in the full run); the final clean-DB run is `artifacts/playwright-e2e/logs/chromium-final-clean.log`.

### D2 — Editor's Event pane is not initialized from the loaded document; Undo restores the placeholder (P1) — FIXED 2026-11-06

- **Spec:** `e2e/specs/04-editor.spec.ts:12`
- **Expected:** after editing `#names` to `QA Edited Names`, Undo returns to the document's stored
  names (`QA Editor …`).
- **Actual:** Undo returns `Sophea & Dara`, the static placeholder from `src/html/index.html:109`,
  while `#documentTitle` shows the correct document title.
- **Second signal:** the API stores the document with `fields.names = "QA Editor …"` (verified via
  `GET /api/invitations/{id}`), so the value exists server-side; the editor's form/undo state is
  what diverges.
- **Artifact:** `artifacts/playwright-e2e/test-results/04-editor--smoke-editor-lo-c9caa--document-and-edits-a-field-chromium/`
  (video + error context).
- **Impact:** host names could silently revert to placeholder text after an undo; a publish from
  that state would ship the wrong names.
- **Root cause:** the field edit updated `state` immediately, but `save()` pushed history only after
  a 260 ms debounce. Undo clicked before that push popped the loaded-document snapshot (the stack
  top) and restored the pre-load placeholder baseline.
- **Fix (2026-11-06):** `undo()` now flushes any coalesced command and pushes the visible pending
  state before stepping back, so the edit is undone to the loaded document.
- **Verified:** `04-editor` **3/3**; full clean-DB Chromium **157/11**, D2 passing.

### D3 — Templates: accessible name does not contain visible text (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/06-a11y.spec.ts:41` (`/templates.html`)
- **axe:** `label-content-name-mismatch`, serious — 5 template buttons
  (`button[data-pack-template="wd-royal-maroon-gold"]`, `wd-ivory-kbach-frame`,
  `wd-lotus-watercolour`, `wd-midnight-navy-gold`, `wd-temple-arch`).
- **Root cause:** the pack card supplied an `aria-label` built from the primary name, canvas and
  page count, while the visible secondary-language name was `aria-hidden`. The accessible name
  therefore did not contain all of the visible text.
- **Fix:** removed the overriding `aria-label` and the `aria-hidden`; the button's name now derives
  from its visible primary and secondary names plus the meta line.
- **Verified:** focused `06-a11y` **20/20**; full clean-DB Chromium **163/5**.
- **Artifact:** `test-results/06-a11y--a11y-axe-scans-templates-html-has-no-axe-violations-chromium/`.

### D4 — Account: sign-in control below the 24 px target size (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/06-a11y.spec.ts:41` (`/account.html`)
- **axe:** `target-size`, serious — `.account-sign-in`.
- **Root cause:** the sign-in anchor wrapped a separate `<button>`, leaving the anchor without a
  reliably sized target of its own.
- **Fix:** the anchor is now the single control (`button-link primary`, visible text, no nested
  button); the shared `.button-link` rule supplies the 44 px minimum.
- **Impact:** hard to hit on touch and for motor-impaired users.
- **Verified:** focused `06-a11y` **20/20**; full clean-DB Chromium **163/5**.

### D5 — Guest/public colour contrast and scan timing (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/06-a11y.spec.ts:41` (`/public.html`), plus the guest desktop/mobile scans.
- **axe:** `color-contrast`, serious — `.event-type` and the public fallback's RSVP labels.
- **Root cause:** two independent causes. `.event-type` was faded to 68%, giving 4.14:1 on the
  guest page and 1.49:1 on public; the scanner also ran while `#rsvp.reveal` was mid-`fadeUp` at
  opacity 0.741, so its settled `#666655` labels were measured at 1.53:1.
- **Fix:** `.event-type` no longer fades (`opacity:1`), and `scan()` waits for finite animations to
  finish before axe runs, so it audits the settled state rather than a transient frame.
- **Impact:** low-vision readers lose the affected copy while the page is faded.
- **Verified:** focused `06-a11y` **20/20** (public, guest desktop/mobile); full **163/5**.

### D6 — Guest invitation: accessible-name mismatch, desktop and mobile (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/06-a11y.spec.ts:49` and `:57`
- **axe:** `label-content-name-mismatch`, serious — `.guest-journey-current` at 1440 and Pixel 7.
- **Root cause:** the journey menu button carried a fixed `aria-label` that did not include the
  visible current-step title, so voice control could not activate it by the text on screen.
- **Fix:** removed the fixed label; the accessible name now derives from the visible step title.
- **Impact:** the current-step control cannot be operated by its visible label via voice control.
- **Verified:** focused `06-a11y` **20/20** desktop + mobile; full **163/5**.

### D7 — Create-invitation dialog: contrast and target size (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/06-a11y.spec.ts:70`
- **axe:** `color-contrast` (`.mini-title` inside `gold` and `birthday-pop` template previews) and
  `target-size` (template action controls).
- **Root cause:** thumbnail titles used the decorative accent alone on pale backgrounds (as low as
  3.01:1), while the select action inherited `height:100%!important` and pushed the Preview action
  outside the clipped card.
- **Fix:** thumbnail titles blend the accent with body text; cards have a 262 px minimum, the
  select action is auto-height, and the Preview action is 36 px.
- **Impact:** template choice is the first decision a host makes; both issues sit on it.
- **Verified:** focused `06-a11y` **20/20** create dialog; full **163/5**.

### D8 — Invitation list ignores `limit`/`offset` (P2) — FIXED 2026-11-07

- **Spec:** `e2e/specs/10-api.spec.ts:127`
- **Expected:** `GET /api/invitations?limit=1` returns exactly one row; `offset=1` returns a different row.
- **Actual:** the handler executed the owner/collaborator query with no `LIMIT`/`OFFSET`, so every
  request transferred the full list (7 rows clean, 106 in the accumulated-data run, 144 in the
  volume recheck).
- **Root cause:** `list_invitations()` ignored the query string.
- **Fix:** `src/python/server.py` parses `limit`/`offset`, rejects non-integers with 400, clamps
  `limit` to 1–100 and `offset` to ≥0, and applies SQL `LIMIT ? OFFSET ?`. Omitting both preserves
  the existing full-list response for API clients. The dashboard now requests 25-row batches,
  renders 24 cards plus a bilingual **Load more invitations** button, and the reachability probe
  asks for `limit=1` instead of the full list. Status and title/slug search are also applied
  server-side (`status=published|draft|archived`, `q=…`) before paging, so a filter or search covers
  every row rather than the first loaded page; an unknown status is a 400. The dashboard debounces
  search, resets to offset 0 on every filter change and ignores stale responses. The route in
  `09-network.spec.ts` matches the new query string.
- **Verified:** focused `03-dashboard` + `10-api` + `12-i18n` **24/24** (Load more, the
  `status=published` request, the no-results state and the invalid-status 400); clean-DB Chromium
  **169/169** (`logs/chromium-filters-full.log`); the 177-invitation (144 owner rows)
  dashboard/UX/API subset **26/26** (`logs/chromium-filters-volume.log`); WebKit route smoke
  **33/33** on the D8/D9 run and **32/33** on the final-tree rerun, with one intermittent
  signed-out `/index.html` page error that passed 5/5 in isolation (`logs/webkit-filters-final.log`,
  `logs/webkit-index-repeat.log`).
- **Impact:** large accounts no longer download or render their entire board on first paint, and
  the four dashboard interaction/capture timeouts seen at 132 invitations no longer reproduce.

### D9 — Guest language test targeted the hidden duplicate (P2) — TEST FIXED 2026-11-07

- **Spec:** `e2e/specs/12-i18n.spec.ts:56` and `:82`
- **Expected:** a guest can switch the invitation to Khmer.
- **Actual:** the in-page `[data-guest-lang]` control is intentionally hidden. The visible control
  is the i18n-injected `header.guest-topbar .language-switch`; it is reachable at 1440 and 320 and
  drives the guest renderer. The original test searched only inside `#publicRoot`, so it measured
  the hidden duplicate at 0×0 and reported the feature as unreachable.
- **Second signal:** `tests/lt_4_1_language_switch_test.py` explicitly asserts the topbar switch is
  visible, `.guest-topbar__lang` is hidden and `.guest-layout-content .language-switch` stays
  hidden. It passes.
- **Fix:** both Playwright guest tests now target the visible topbar control. No product change:
  showing the in-page copy would create two language switchers and contradict the Python contract.
- **Verified:** both `12-i18n` guest tests pass at 1440 and 320; the Python contract is **1/1**; full
  Chromium **169/169**; WebKit **33/33**.

### D10 — Skip link did not move focus (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/17-keyboard.spec.ts:8`
- **Expected:** first Tab reaches `a.skip-link`, Enter moves focus to `#main`.
- **Root cause:** Chromium performed the fragment navigation (`location.hash` became `#main`)
  but left `document.activeElement` on `<body>`; no handler focused the target. The original
  assertion also read the hash before the fragment navigation settled.
- **Fix:** `src/js/modern-ui.js` now captures `.skip-link` activation, prevents the default,
  updates the hash, focuses `#main`, and scrolls it into view.
- **Verified:** `17-keyboard` 8/8 and `06-a11y` 20/20; clean-DB full run **165 passed / 3 failed**
  (only D8 and D9).
- **Impact:** keyboard and screen-reader users can bypass the header; WCAG 2.4.1.

### D11 — Guest invitation had no `h1` (P2) — FIXED 2026-11-06

- **Spec:** `e2e/specs/17-keyboard.spec.ts:131`
- **Actual:** `#publicRoot h1` count was 0; the page's top-level text was not a heading.
- **Fix:** `src/js/public-page.js` now prepends a screen-reader-only `<h1 data-guest-title>` to
  `#publicRoot`, populated from the guest-language invitation names and updated by `setLanguage`
  when the guest switches language. The visible topbar title is unchanged.
- **Verified:** `17-keyboard` 8/8; clean-DB full run **165 passed / 3 failed** (only D8 and D9).
- **Impact:** screen-reader heading navigation now finds the invitation's primary heading.

### D12 — Dashboard loses its signed-in view on reload / second tab (P2, intermittent) — FIXED 2026-11-06

- **Spec:** `e2e/specs/14-navigation.spec.ts:42` (refresh) and `:52` (two tabs)
- **Expected:** after a reload or a second tab, `#dashboardView` is visible with the stored session.
- **Actual:** `#dashboardView` remains `hidden` for the 10 s assertion while the editor deep link
  with the same storage state loads the owner's document. Reproduced in an isolated
  `14-navigation` run (refresh + two tabs, 2 failed) after the full run failed the two-tab case.
- **Impact:** a host can land on a hidden/blank workspace despite a valid session cookie; reload
  and multi-tab behaviour was unreliable. The boot's full list/template load could exceed the
  10 s assertion while both views were still hidden.
- **Artifact:** `artifacts/playwright-e2e/test-results/14-navigation--navigation--5269f-without-breaking-each-other-chromium/`
- **Root cause:** `detect()` awaited `/api/auth/me` **and** the full invitations/templates load before
  calling `show()`. With the accumulated 141-row list the 10 s assertion expired while both views
  were still hidden.
- **Fix (2026-11-06):** reveal the authenticated shell as soon as `me` resolves (`show(false)`),
  then load and re-render. A failed list keeps the session and shows the existing error state
  instead of signing the user out.
- **Verified:** `02-auth` stored session **5/5**; `03-dashboard` **4/4**; the later clean-DB
  Chromium run is **163/5**, with the D12 specs passing.

### Non-failing UX observations (recorded, not asserted as release blockers)

1. **Sign-out is hidden on the dashboard header.** `css/final-polish.css` sets
   `body[data-page="dashboard"]>header>#logoutBtn{display:none}`; the working path is the profile
   popover → `[data-signout]`. Both sign-out tests use it successfully, but the direct control is
   invisible on the main workspace.
2. **Document-level venue is not rendered on the guest page.** The seeded document's
   `fields.venue` ("The Riverside Ballroom, Phnom Penh") never appears in `#publicRoot` text;
   the event's own venue ("Royal Hall") does. If the intent is to show the main venue, it is
   missing; the test now asserts the rendered event venue only.
3. **First-run editor tour is modal and intercepts pointer events.** `dialog.final-tour` blocks
   `#publishBtn` until dismissed by its button; Escape did not reliably close it in automation.
4. **API/UI mismatch:** `GET /api/invitations/{id}/responses` → 404 while the UI reads
   `/api/invitations/{id}/rsvps`. The documented/guessed path is wrong; the shipped path works.
5. **Seed accumulation:** global setup creates a fresh published/draft invitation per run
   (intentional isolation), so the owner list grows; this is why D8's row count rises.
6. **Dashboard signed-out heading order:** earlier runs observed an `h2` before the `h1`; the
   stabilized scan now passes the no-skip check. Not counted as a defect.

---

## 5. Blocked and not tested (negative space)

WebKit is no longer blocked: after `libavif16` was installed, WebKit 27.2 launched and passed
**33/33** route-smoke tests (`logs/webkit-retry.log`) and **33/33** again after the D8/D9 close-out
(`logs/webkit-d8-d9-final.log`). A final-tree rerun passed **32/33**: signed-out `/index.html`
raised one `TypeError: undefined is not an object (evaluating
'window.EInviteMotion.createFrameBatcher')`. The motion core and every direct caller live in the
same parser-blocking bundle with the definition first, so it is not a deterministic ordering
defect; the same test passed **5/5** repeats in isolation (`logs/webkit-index-repeat.log`). The
remaining gaps are below.

| Item | Status | Why |
|---|---|---|
| Real Safari/iOS behaviour | NOT TESTED | Playwright WebKit is desktop automation, not a real Safari/iOS device; the device checklist remains unrun. |
| RTL layouts | N/A | product supports EN/KM only, no RTL locale |
| File upload / materials library | NOT TESTED | no upload journey in this pass |
| Admin user management mutations | NOT TESTED | access posture only |
| Check-in scanner | NOT TESTED | server started with `EINVITE_ALLOW_NO_SCANNER=1` |
| Email delivery (verify/reset) | NOT TESTED | no SMTP; page load only |
| Payments | N/A | no payment provider in the build |
| Load/soak beyond 3 workers | NOT TESTED | 3 workers, one origin, one SQLite file |
| Login rate-limit boundary | NOT TESTED deliberately | would lock the shared origin for 10 minutes; the limit itself (30/600 s) was observed during harness development |

---

## 6. Artifacts

- JSON/JUnit: `artifacts/playwright-e2e/results.json`, `artifacts/playwright-e2e/junit.xml`
- HTML report (failures only): `artifacts/playwright-e2e/html-report/index.html`
- Per-test traces/videos/screenshots: `artifacts/playwright-e2e/test-results/`
- UX screenshots (16 routes + inventory): `artifacts/playwright-e2e/screenshots/ux/`
- Guest/network/i18n screenshots: `artifacts/playwright-e2e/screenshots/{guest,network,i18n}/`
- Performance metrics: `artifacts/playwright-e2e/perf/*.json`
- Visual baselines: `e2e/__screenshots__/07-visual.spec.ts/`
- Raw logs: `artifacts/playwright-e2e/logs/` (`chromium-final3.log`, `firefox-smoke.log`,
  `mobile.log`, `tablet.log`, `visual-verify.log`, `flake.log`, `webkit.log`, `webkit-retry.log`,
  `chromium-d8-d9-final.log`, `chromium-d8-volume.log`, `chromium-d8-paging-final.log`,
  `chromium-d8-paging-volume.log`, `chromium-filters-focused.log`, `chromium-filters-full.log`,
  `chromium-filters-volume.log`, `webkit-d8-d9-final.log`)
- Discovery evidence: `artifacts/playwright-e2e/api-probe.json`, `dom-probe{,2..7}.mjs`

`artifacts/` is gitignored; baselines are committed. Post-pass fixes edited `src/` for D1–D8; D9
was a test-side selector correction.

---

## Phase 6 — Extended autonomous test suites (non-browser)

**Run:** 2026-11-07
**Entry point:** `npm run verify` → `python3 tools/verify.py`
**Environment:** Linux, Python 3 in `.venv`, Node/npm, Chrome 157 at `/usr/bin/google-chrome`, local SQLite app.
**Verdict:** **FAIL**. E13 failed with 109 findings; 16 suites were BLOCKED on absent tooling or
absent inputs; E18 and E19 passed; the E20 aggregate failed. This is not a green gate.

Two runs are recorded because the Lighthouse suite exceeds the synchronous command window:

| Run | Command | Exit | Stopping point | Summary |
|---|---|---:|---|---|
| Full evidence | `npm run verify -- --no-stop` | 1 | E13 (continued) | `reports/verify-summary-nostop.json` |
| Gate | `npm run verify -- --from E13 --resume` | 1 | E13 | `reports/verify-summary.json` |

The gate run reuses the fresh E1–E12 results and stops at the first blocking FAIL, as specified;
E14–E19 are marked `BLOCKED — gate stopped at E13` in that summary. The no-stop run attempted
every suite; its statuses are used below. Suites are listed by ID, not execution order; the runner
executes the 6.0 cheapest-first sequence (E1–E5, E12, E7, E8, E6, E9, E10, E11, E13, E15, E14,
E16–E20). The recorded no-stop summary predates that final reorder; its suite statuses are
unchanged. The section numbers 9–13 follow the Phase 6 report-additions specification.

### 9. Extended suite table

| Suite | Area | Status | Findings | Duration | Report artifact |
|---|---|---|---:|---:|---|
| E1 | Python static analysis | BLOCKED | 0 | 15 ms | `reports/logs/E1-*.log` |
| E2 | Frontend static analysis | BLOCKED | 0 | 114 ms | `reports/logs/E2-*.log` |
| E3 | Software composition analysis | BLOCKED | 0 | 14.7 s | `reports/pip-audit.json`, `reports/npm-audit.json` |
| E4 | Secret scanning | BLOCKED | 0 | 4 ms | `reports/logs/E4-gitleaks.log` |
| E5 | Unit tests + coverage | BLOCKED | 0 | 477 ms | `reports/logs/E5-pytest-coverage.log` |
| E6 | API property-based fuzzing | BLOCKED | 0 | 7.4 s | `reports/logs/E6-schemathesis.log` |
| E7 | Contract / breaking-change diff | BLOCKED | 0 | 6 ms | `reports/logs/E7-oasdiff.log` |
| E8 | Database migrations | BLOCKED | 0 | 445 ms | `reports/logs/E8-migrations.log` |
| E9 | Accessibility CLI sweep | BLOCKED | 0 | 7 ms | `reports/logs/E9-*.log` |
| E10 | Performance / Core Web Vitals | BLOCKED | 0 | 278.1 s | `.lighthouseci/reports/`, `reports/e10-cwv.json` |
| E11 | Site-wide link crawl | BLOCKED | 0 | 1 ms | `reports/logs/E11-linkinator.log` |
| E12 | HTML / CSS validity | BLOCKED | 0 | 49 ms | `reports/logs/E12-*.log` |
| E13 | Headers, robots, sitemap, meta, JSON-LD | **FAIL** | 109 | 6.8 s | `reports/headers-meta.json` |
| E14 | Dynamic application security testing | BLOCKED | 0 | 2 ms | `reports/logs/E14-*.log` |
| E15 | Pseudo-localization | BLOCKED | 0 | 1 ms | `reports/logs/E15-pseudo-i18n.log` |
| E16 | Mutation testing (nightly) | BLOCKED | 0 | 27.3 s | `reports/logs/E16-targeted-harness.log` |
| E17 | Agentic exploratory pass | BLOCKED | 0 | 10 ms | `reports/logs/E17-agentic.log` |
| E18 | SBOM generation | **PASS** | 0 | 7.8 s | `reports/sbom.cdx.json` |
| E19 | Build / bundle check | **PASS** | 0 | 5.1 s | `reports/logs/E19-build-check.log` |
| E20 | Aggregate Phase 6 gate | **FAIL** | 109 | 348.3 s | `reports/verify-summary.json` |

E20's 109 findings are E13's findings; it is an aggregate row, not another scan. E16's targeted
harness is seam-level evidence, not a module-wide mutation score (§11). E18 and E19 pass in the
no-stop run; the canonical gate never reached them because it stopped at E13.

#### 9.1 Blocked-suite commands and exact errors

Commands are shown as specified in the Phase 6 brief; the runner resolves Python tools through
`.venv/bin/python` and records the resolved argv in `reports/logs/<suite>-*.log`. `command not
found` means the executable is absent from `PATH`; it is not a product failure.

- **E1** — `ruff check src/`; `ruff format --check src/`; `mypy --strict src/`;
  `bandit -r src/ -f json -o reports/bandit.json`.
  Error: `command not found ([Errno 2] No such file or directory: 'ruff')`; the same for `mypy`
  and `bandit`. No static-analysis report was produced.
- **E2** — `eslint --max-warnings 0`; `stylelint "src/**/*.css"`; `design-token-lint`.
  Error: `bash: line 1: eslint: command not found`; `stylelint` and `design-token-lint` fail the
  same way. No design-token rule set exists in the repo.
- **E3** — `osv-scanner scan source -r . --format json`.
  Error: `osv-scanner scan source -r . --format json: command not found ([Errno 2] No such file or
  directory: 'osv-scanner')`. `pip-audit` and `npm audit` did run; see §10.
- **E4** — `gitleaks git . --no-banner --report-format json --report-path reports/gitleaks.json`.
  Error: `command not found ([Errno 2] No such file or directory: 'gitleaks')`. Git history was
  not scanned.
- **E5** — `pytest -n auto --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=80`.
  Error: `python -m pytest: error: unrecognized arguments: -n --cov=src --cov-report=xml
  --cov-report=term-missing --cov-fail-under=80`. `.venv` lacks `pytest-cov` and `pytest-xdist`.
- **E6** — `schemathesis run http://localhost:<port>/openapi.json --checks all
  --hypothesis-max-examples=200 --report junit --report-dir reports/`.
  Error: `command not found ([Errno 2] No such file or directory: 'schemathesis')`. The repository
  also has no OpenAPI document to serve.
- **E7** — `oasdiff breaking contracts/openapi/current.yaml contracts/openapi/proposed.yaml`.
  Error: `command not found ([Errno 2] No such file or directory: 'oasdiff')`. `contracts/openapi/`
  does not exist.
- **E8** — `pytest tests/migrations --migrations -q`.
  Error: `python -m pytest: error: unrecognized arguments: --migrations`. `tests/migrations/` does
  not exist and `pytest-mrt` is not installed.
- **E9** — `axe http://localhost:<port>/index.html --exit`; `pa11y-ci --sitemap
  http://localhost:<port>/sitemap.xml`.
  Error: `command not found ([Errno 2] No such file or directory: 'axe')`; the same for
  `pa11y-ci`. There is also no `sitemap.xml`. The Playwright axe run remains the only axe evidence
  (Phase 5, 20/20 focused).
- **E10** — `npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js`;
  `.venv/bin/python tests/v55_route_weight_budget_test.py`; `npx --no-install size-limit`.
  Lighthouse ran **16/16 routes**, exited 0, and printed `All results processed!`; the v55 budget
  test passed 6/6 pages. `size-limit` then failed with `npm error npx canceled due to missing
  packages and no YES option: ["size-limit@14.3.0"]` (exit 1), so the suite is BLOCKED rather than
  PASS. The assertions that ran are the committed **byte** budgets, not CWV thresholds; see §9.2.
- **E11** — `linkinator http://localhost:<port> --recurse --skip "^(?!http://localhost)"`.
  Error: `command not found ([Errno 2] No such file or directory: 'linkinator')`. No sitemap exists
  to seed a crawl.
- **E12** — `html-validate "src/**/*.html"`; `java -jar vnu.jar --errors-only src/`.
  Error: `bash: line 1: html-validate: command not found`; `java -jar vnu.jar ...: command not
  found ([Errno 2] No such file or directory: 'java')`.
- **E14** — `zap-baseline.py -t http://localhost:<port> -J reports/zap.json`; `nuclei -u
  http://localhost:<port> -severity critical,high -json -o reports/nuclei.json`.
  Error: `command not found ([Errno 2] No such file or directory: 'zap-baseline.py')`; the same for
  `nuclei`. No disposable DAST target was started; running either tool without one would violate
  the isolation requirement.
- **E15** — `pseudo-localize --strategies expand40,accents,cjk,rtl,unicode,brackets --routes all
  --viewport 320`.
  Error: `command not found ([Errno 2] No such file or directory: 'pseudo-localize')`. The product
  ships `en` and `km` only; no pseudo-locale bundles exist.
- **E16** — `mutmut run --paths-to-mutate src/`; `npx --no-install stryker run`.
  Error: `command not found ([Errno 2] No such file or directory: 'mutmut')`; `npm error npx
  canceled due to missing packages and no YES option: ["stryker@1.0.1"]` (exit 1). The targeted
  harness did run: `MUTATIONS 3/3 killed`.
- **E17** — capability probe `true` (exit 0). No MCP browser server is exposed to this runner and
  the preview tools are not a walk API, so the agentic journey pass is BLOCKED by capability, not
  by a failed command.

#### 9.2 Performance metrics (E10)

Lighthouse CI ran one desktop-preset audit per route against `tools/serve-gzip.py` on
`http://127.0.0.1:8124` (gzip on the wire), Chrome 157, `numberOfRuns: 1`, default simulated
throttling (1350×940, DPR 1, simulated 40 ms RTT / 10.24 Mbps, CPU ×1). These are lab numbers,
not field data.

| Route | Perf score | LCP (ms) | INP (ms) | CLS | TBT (ms) | Transferred (bytes) | Requests |
|---|---:|---:|---:|---:|---:|---:|---:|
| `account.html` | 100 | 505.6 | n/a | 0.0 | 0 | 216203 | 11 |
| `admin.html` | 100 | 545.9 | n/a | 0.0 | 0 | 227168 | 13 |
| `analytics.html` | 100 | 518.6 | n/a | 0.0 | 0 | 209640 | 11 |
| `billing.html` | 100 | 512.8 | n/a | 0.0 | 0 | 209815 | 11 |
| `checkin.html` | 100 | 463.9 | n/a | 0.0 | 0 | 143829 | 12 |
| `dashboard.html` | 100 | 701.1 | n/a | 0.0 | 1.5 | 315306 | 17 |
| `designer.html` | 100 | 530.3 | n/a | 0.0 | 0 | 206183 | 14 |
| `guests.html` | 100 | 556.0 | n/a | 0.0 | 0 | 219401 | 11 |
| `index.html` | 79 | 1199.8 | n/a | 0.1 | 348.5 | 861942 | 80 |
| `materials.html` | 100 | 545.3 | n/a | 0.0 | 0 | 230132 | 13 |
| `privacy.html` | 100 | 420.9 | n/a | 0.0 | 0 | 141731 | 8 |
| `public.html` | 100 | 601.9 | n/a | 0.0 | 0 | 202225 | 11 |
| `reset.html` | 100 | 503.1 | n/a | 0.0 | 0 | 206596 | 11 |
| `responses.html` | 100 | 548.0 | n/a | 0.0 | 0 | 211894 | 12 |
| `templates.html` | 97 | 823.9 | n/a | 0.1 | 82 | 1007019 | 66 |
| `verify.html` | 100 | 514.9 | n/a | 0.0 | 0 | 205304 | 11 |

All 16 routes passed the committed byte budgets in `docs/perf/lighthouse-budgets.json`
(`resourceSizes` only; the file has no CWV thresholds). `index.html` and `templates.html` are the
heaviest and slowest: index is 1199.8 ms LCP, 348.5 ms TBT, 861,942 bytes and 80 requests;
templates is 823.9 ms LCP, 82 ms TBT, 1,007,019 bytes and 66 requests. No S2 performance
regression can be asserted from a CWV threshold because none is committed; the byte gate passed.
INP is not measured by this Lighthouse lab run (`n/a`), so no INP claim is made — field INP
requires CrUX/RUM and TBT is only a lab proxy. CLS 0.1 on index/templates is the highest observed.
Raw metrics: `reports/e10-cwv.json`; route reports are in `.lighthouseci/reports/` (16 route
reports plus the LHCI manifest).

#### 9.3 E13 findings and what they mean

E13 started its own app on `http://127.0.0.1:58143` (isolated data directory; the pre-existing
`4175` development server was not used) and fetched all 16 shipped routes plus `/robots.txt` and
`/sitemap.xml`.

| Kind | Detail | Count | Routes |
|---|---|---:|---|
| header | `Strict-Transport-Security` | 16 | all 16 routes |
| meta | `canonical` | 15 | all except `public.html` |
| opengraph | `og:title`, `og:description`, `og:image` | 45 | 15 pages × 3 |
| twitter | `twitter:card` | 15 | all except `public.html` |
| jsonld | `missing` | 16 | all 16 routes |
| discovery | `status 404` | 2 | `/robots.txt`, `/sitemap.xml` |

`public.html` is the only page with canonical, OpenGraph and Twitter metadata; it is missing HSTS
and JSON-LD. The other 15 pages are missing all seven metadata/header checks. The remaining
required headers were present on every route: CSP, `X-Content-Type-Options`, `Referrer-Policy`,
`Permissions-Policy`, and `X-Frame-Options` or a CSP `frame-ancestors` directive.

Severity: missing canonical/OpenGraph/Twitter/JSON-LD/robots/sitemap is **S3** (SEO and discovery,
not rendering); missing HSTS is **NEEDS-VERIFICATION** because this run is plain HTTP on loopback
and browsers ignore HSTS over HTTP — re-check at the TLS terminator before calling it a product
defect. E13 is a header/metadata check, not a DAST scan; it makes no injection or auth-bypass
finding.

### 10. Dependency and secret findings

| Source | Scope | Result | Artifact |
|---|---|---|---|
| `pip-audit -r requirements.txt` | 22 resolved Python dependencies | **0 vulnerabilities** | `reports/pip-audit.json` |
| `npm audit --audit-level=high --json` | installed npm tree / lockfile | **0** (info 0, low 0, moderate 0, high 0, critical 0) | `reports/npm-audit.json` |
| `osv-scanner scan source -r .` | source + lockfiles | BLOCKED — executable absent | `reports/logs/E3-osv.log` |
| `gitleaks git .` | Git history | BLOCKED — executable absent | `reports/logs/E4-gitleaks.log` |

There is no CVE ID, package, installed/fixed version, or reachability row to report: both audits
that completed returned zero findings. The npm result is lockfile-based SCA and does not cover OS
packages, containers or the Python runtime. The Python result is limited to `requirements.txt`;
`osv-scanner` would have covered the wider source tree and did not run.

No secret finding is reported, but **the Git history was not scanned**. A secret anywhere in
history would be S1 with a commit SHA and a rotation instruction; `gitleaks` did not run, so this
report must not be read as evidence that no secret exists.

### 11. Mutation score by module

`mutmut` and `stryker` are not installed, so there is **no mutation score per module**, no
surviving-mutant list and no defensible "three weakest modules" ranking. The only mutation evidence
is the targeted harness in `tools/phase6-flag-mutations.py`, which mutates the three assertion
seams of the analytics feature-flag test:

| Mutation | Result |
|---|---|
| admin PUT returns 500 | KILLED |
| admin PUT flips `ai_agent_enabled` instead | KILLED |
| user is never promoted to admin | KILLED |

`MUTATIONS 3/3 killed` (100% at this seam; module: analytics feature-flag endpoint). This is
seam-level evidence that those assertions bite, **not** a module mutation score, and it must not be
extrapolated to the rest of `src/`. A nightly `mutmut`/`stryker` run is still required; a module
below 60% is test-quality debt, not a product defect.

### 12. Internationalisation findings

| Locale | Routes rendered | Overflow | Hardcoded strings | Tofu | Status |
|---|---:|---:|---:|---:|---|
| `en` (real) | 16 routes in Phase 5 | not measured | not measured | not measured | layout/switch covered; pseudo metrics absent |
| `km` (real) | 16 routes in Phase 5 | not measured | not measured | not measured | layout/switch covered; pseudo metrics absent |
| pseudo-locale (expansion +40%, accents, CJK, RTL markers, unicode stress, brackets) | 0 | unknown | unknown | unknown | **BLOCKED** — generator absent |

The "not measured" entries are not zeros. Phase 5 covered real-locale layout and switching:
`12-i18n` passed inside the 24/24 focused run and the 169/169 full Chromium run, including the
visible topbar switch and Khmer date at 1440 and 320 px; `08-responsive` covered 320 px overflow.
Phase 5 did not record a per-locale number/currency formatting matrix, and this phase could not
generate pseudo-locales, so overflow/hardcoded/tofu counts and the 320 px pseudo-locale check
remain unproven.

Translation accuracy is **NEEDS-NATIVE-REVIEW**. Pseudo-localization proves layout and plumbing
only. Real RTL is N/A because the product ships `en`/`km`; the RTL-marker pseudo strategy was not
run because the generator is absent.

### 13. Static-analysis debt

No linter, type checker or SAST tool ran, so the debt numbers the brief asks for are **unknown**:

- **Total violations:** unknown. The `0` finding counts on E1/E2 mean "no analyzer ran", not
  "clean". No `reports/bandit.json`, ruff, mypy, eslint or stylelint output exists.
- **New-on-changed-lines violations:** unknown. The uncommitted worktree changes under review are in
  `src/python/server.py`, `src/js/dashboard.js`, `src/js/dashboard-polish.js` and the e2e specs;
  without a linter or a diff-aware baseline there is no S2-on-changed-lines determination.
- **Top five rule IDs:** unavailable — no rule engine produced findings.
- **Coverage-diff:** unavailable. E5 is BLOCKED, so there is no `coverage.xml` and no uncovered
  changed-line ranges; the 80% threshold was not evaluated.

The 109 E13 runtime findings in §9.3 are header/metadata findings, not lint debt, and are not
counted in this section. Until the pinned toolchain (ruff, mypy, bandit, eslint, stylelint,
coverage/pytest-xdist, gitleaks, osv-scanner, schemathesis, oasdiff, pytest-mrt, axe/pa11y,
linkinator, html-validate/vnu, size-limit, mutmut/stryker, pseudo-locale generator, zap/nuclei) is
installed, E1–E12 and E14–E17 remain BLOCKED and the aggregate gate cannot pass.

**What this phase does not claim (6.16).** No screen-reader conformance (NVDA, JAWS or
VoiceOver) was tested; no subjective visual or copy quality was judged; the laptop Lighthouse run
is not production load or capacity evidence; no header, scanner or scripted test in this phase
proves business-logic authorisation correctness; and pseudo-localization, which did not run,
proves layout and plumbing only, never translation accuracy. Translation accuracy remains
**NEEDS-NATIVE-REVIEW**.

Phase 6 changed no product code. Its only source changes are the gate runner (`tools/verify.py`),
its `npm run verify` entry in `package.json`, the generated `reports/` artifacts and this report.
The worktree remains dirty and no commit was made.
