# Language Switch — Implementation & Gap Report (v0.68.4 / ROADMAP-V2 §3.10)

Status: **MECHANISM IMPLEMENTED & VERIFIED; TRANSLATION GAPS REMAIN.** All hard CI gates
green; Puppeteer end-to-end toggle verified on 6 pages (index, guests, admin × en/km)
plus the admin Feature flags tab. This update corrects the prior v0.68.3 draft, whose
"stale bundles / H1 CONFIRMED" and per-file gap counts were NOT re-verified from source.
All numbers below are derived from the current working tree (git HEAD `133d364`).

## 1. Scope & hard constraints

- One language at a time, user-selectable, persisted. Source of truth = `<html lang>`;
  persisted to `localStorage` key `einvite-lang` (`'en' | 'km'`).
- Vanilla JS + plain CSS only — no Tailwind, no npm, no framework.
- All bilingual `en`/`km` source strings kept intact (only the rendered one changes).
  CI scripts `scripts/check-bilingual-consistency.py`,
  `python3 src/python/build/build_route_bundles.py --check`, and
  `tests/build_integrity_test.py` must still pass.
- Khmer line-height ≥ 1.6 (enforced in `styles.css`).
- Four i18n shapes **coexist by design (not unified)**:

| Shape | Call site | Modules |
|---|---|---|
| `t()+STRINGS` (per-locale `STRINGS={en:{k},km:{k}}`) | 28 page/editor modules | admin ×9, sessions, editor chrome, chart, collaboration-presence-v52, crdt-yjs-×3, dashboard/analytics, **feature-flags.js** |
| `EInviteI18n.langText('en','km')` | public-page.js + 7 helpers | public-page, signup-sheets, polls, album, invitation-edit-history, host-signup-sheets, host-polls, delivery-dialog |
| `COPY={en,km}` | guest-journey.js | guest-journey |
| page-module `_txt(en,km)`/`_html(en,km)`/`b(en,km)` → dual `.i18n-en/.i18n-km` spans | the 11 page modules + dashboard | account, analytics, billing, designer, checkin-v13, guests, materials, reset, responses, templates, verify, dashboard |

> The fourth shape (page-module `_txt`/`_html`/`b` dual-string helpers emitting
> `.i18n-en/.i18n-km` spans) was added by the v0.68.x pass and is intentionally **not**
> unified with the other three (per ROADMAP-V2 constraint). `subscribe(render)` wires
> live re-render on `EInviteI18n` language change.

## 2. Resolver: `src/js/core/i18n.js`

Pre-existing (mtime 2026-09-28 10:24, before the i18n agent's 20:05 start). Vanilla
IIFE, second `earlyScripts` entry. Verified API: `get()/set/langText/t/subscribe`.
Its own Node shim tests pass (see §4). **Not modified this pass.**

## 3. First-visit / FOIL init

`<head>` of every bilingual page runs an inline FOIL script that seeds
`<html lang>` from `localStorage['einvite-lang']` → `navigator.language`
(`km*` → `km`) **before first paint**, so the CSS hide rules take effect with no flash.
Note: `admin.html`'s `<head>` loads `core/theme.js` + the inline FOIL script +
`backend-mode-v14.js` (the manifest `earlyScripts` list still documents `core/safe-dom.js`
+ `core/i18n.js` + `backend-mode-v14.js`; `core/i18n.js` is also concatenated into
`bundle-*.v15.js` and initializes at end-of-body, so the header language switch appears
after load — a pre-existing timing property, not changed this pass).

## 4. CSS (pre-existing, migration)

`src/css/organized/styles.css` already defines the toggle rules — `.i18n-en{display:none}`
under `[lang="km"]` and `.i18n-km{display:none}` under `[lang="en"]`, `.khmer-text`
Khmer font stack + `line-height:1.6`, and the sticky `.language-switch`.
mtime 2026-09-28 06:36; i18n-en occurrence count unchanged (HEAD→working = 1).
The served `bundle-admin-v15.css` carries these rules. **Not modified this pass.**

## 5. Verified toggles (Puppeteer, Chrome headless-shell, session 2026-09-29 19:07)

Captured into `screenshots/{admin,guests,index}-{en,km}.png`. Method: load page, set
`localStorage['einvite-lang']`, reload, count live `.i18n-en`/`.i18n-km` spans by
computed `display`, screenshot.

| Page | lang=en | lang=km | toggle verified |
|---|---|---|---|
| index | enVis 3/3 | enVis 0/3, kmVis 3/3 | yes — "អក្សរ​ភាសាខ្មែរ…" visible in km |
| guests | enVis 22/22 | enVis 0/22, kmVis 22/22 | yes — 13 spans carry real KM (e.g. "បញ្ជីភ្ញៀវ") |
| admin | enVis 10, kmVis 0 | enVis 0, kmVis 10 | yes; feature-flags tab open, panel renders |

Feature flags tab (admin-en captured with tab open): `button[data-admin-tab="feature-flags"]`
label reads `"Feature flagsទងជម្រើសសមុខងារ"`, `#featureFlagsPanel` innerHTML length **1176**
(non-blank), visible text = "FEATURE FLAGS / Toggle platform features on or off…".

## 6. Feature flags tab — VERDICT (was claimed "stale bundles")

**The "stale bundles" root cause is NOT accurate.**

- `HEAD:` `admin.html` had **no** feature-flags tab (only Users/Templates/Invitations/AI);
  `HEAD` `route-bundle-sources-v15.json` did **not** list `feature-flags.js`;
  `HEAD` `bundle-admin-v15.js` (70,798 B) contained **0** `feature-flags` symbols.
- Working tree: `admin.html` adds the `feature-flags` tab + bilingual spans; `admin.js`
  mounts `feature-flags.js`; `feature-flags.js` v65 defines `STRINGS` (en/km) +
  `EInviteI18n.t` + `subscribe(render)`; `docs/route-bundle-sources-v15.json` lists it;
  `bundle-admin-v15.js` was **rebuilt** (138,080 B) and now contains
  `EInviteAdminFeatureFlags` (×4) + `featureFlagsPanel` (×1).
- The `/api/admin/feature-flags` and `/api/admin/settings` backend routes in
  `src/python/server.py` are **pre-existing migration debt** (mtime 2026-09-28 06:36,
  absent at HEAD) — not authored by the i18n agent, and **not** a build-sync output.

Correct explanation: the feature-flags surface was **newly implemented end-to-end**
(HTML + feature-flags.js + admin.js mount + manifest entry + bundle rebuild). The blank
panel before the rebuild was simply the expected consequence of editing bundle source
without recompiling — i.e. normal build hygiene, **not** a stale-bundle defect.
"Staled bundles" would imply a pre-existing, working feature that silently broke; here
no such pre-existing feature existed at `HEAD`. The panel now renders and toggles
([BROWSER]).

## 7. The 11 known gap modules — confirmed against current source

Each was English-only at `HEAD`. The v0.68.x pass added bilingual infrastructure
(`_isKm` + `_txt`/`_html`/`b` helpers + `.i18n-en/.i18n-km` spans + `subscribe`) to all 11,
**plus `dashboard.js`** (12th, was omitted from the original claim and from the gap list).
Most page-module strings are **English-fallback** (`en==km`) because no verified Khmer
translation exists — this is the intentional fallback, logged here as gaps, not fabricated.

Counts = unique bilingual literal pairs from `src/js/<module>.js` (helper shape) +
unique `.i18n-en/.i18n-km` span pairs from `src/html/<module>.html` (static).
"Switch" = `en!=km` (carries real Khmer); "Stuck EN" = `en==km` (English fallback).

| Module | HTML spans (switch/stuck) | JS helper pairs (switch/stuck) | Total | Switch | Stuck EN | Pages affected | High-traffic? |
|---|---|---|---|---|---|---|---|
| account.js | 70 (0/70) | 17 (0/17) | 87 | 0 | 87 | account.html | **HIGH** |
| analytics.js | 7 (0/7) | 23 (0/23) | 30 | 0 | 30 | analytics.html | medium |
| billing.js | 12 (0/12) | 28 (1/27) | 40 | 1 | 39 | billing.html | medium |
| checkin-v13.js | 9 (0/9) | 9 (0/9) | 18 | 0 | 18 | checkin.html | **HIGH** |
| dashboard.js | 47 (9/38) | 10 (0/10) | 57 | 9 | 48 | dashboard.html | **HIGH** |
| designer.js | 17 (0/17) | 6 (3/3) | 23 | 3 | 20 | designer.html | low |
| guests.js | 17 (13/4) | 63 (0/63) | 80 | 13 | 67 | guests.html | **HIGH** |
| materials.js | 33 (4/29) | 11 (7/4) | 44 | 11 | 33 | materials.html | medium |
| reset.js | 19 (0/19) | 8 (0/8) | 27 | 0 | 27 | reset.html | medium |
| responses.js | 6 (2/4) | 18 (2/16) | 24 | 4 | 20 | responses.html | medium |
| templates.js | 7 (4/3) | 57 (1/56) | 64 | 5 | 59 | templates.html | medium |
| verify.js | 8 (0/8) | 0 | 8 | 0 | 8 | verify.html | medium |

Notes:
- `guests.js` "34 strings, subscribe(render) hook" claim: **subscribe(render) = TRUE**
  ([SOURCE] `src/js/guests.js` line 37). "34 strings" is not borne out by the JS module:
  measured **83 helper calls / 63 unique bilingual pairs / 0 switch** (all English-fallback).
  The figure 34 matches `guests.html`'s 17 span pairs counted as 34 en+km markup instances
  (17 en + 17 km), i.e. it describes the HTML, not the JS module.
- `guests.html` itself DOES switch (13 real-Khmer labels, verified in-browser: enVis 22 →
  kmVis 0 and back; "បញ្ជីភ្ញៀវ" = Guest list appears in km). The page-level switch works; the
  `guests.js` *module* strings remain English-fallback.

## 8. Known gaps (English-fallback / untranslated)

### 8a. Byte-identical `t()` keys (STRINGS tables) — listed explicitly

Source-level scan of **all** `src/js/**/*.js` (excluding generated `bundle-*.js`),
brace-balanced, including the `pages/admin/` subtree that the CI checker skips.
Total **16** identical `en==km` keys:

| File | key | value | Verdict |
|---|---|---|---|
| pages/admin/feature-flags.js | flag | 'Flag' | PLACEHOLDER |
| pages/admin/feature-flags.js | noFlags | 'No flags defined.' | PLACEHOLDER |
| pages/admin/feature-flags.js | tier | 'Tier' | PLACEHOLDER |
| pages/admin/feature-flags.js | confirmSave | 'Save this flag value?' | PLACEHOLDER |
| pages/admin/feature-flags.js | requireSuperAdmin | 'Super-admin access required to modify flags.' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicyTitle | 'Non-admin session idle window' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicyDesc | 'How long a non-admin session may sit idle…' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicyLabel | 'Idle window (days)' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicySave | 'Save idle window' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicyConfirm | 'Change the non-admin session idle window to {days} days?' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicySaved | 'Idle window updated to {days} days.' | PLACEHOLDER |
| pages/admin/feature-flags.js | sessionPolicyError | 'Failed to update idle window: {error}' | PLACEHOLDER |
| pages/admin/invitations.js | slug | 'Slug' | PLACEHOLDER |
| components/chart.js | rsvps | 'RSVPs' | legit (RSVP acronym, in exception list) |
| pages/admin/invitations.js | rsvps | 'RSVPs' | legit (RSVP acronym) |
| pages/admin/audit-log.js | ip | 'IP' | legit (IP acronym) |

The top-level files the CI checker scans contain **0** byte-identical pairs
(`identical_pairs: 0`); every identical pair is in the unscanned `pages/admin/` subtree
(`feature-flags.js` ×12, `invitations.js` ×2, `audit-log.js` ×1) or `components/chart.js`.

### 8b. English-fallback helper strings (`_txt`/`_html`/`b` en==km) — order of magnitude

These are the page-module `_txt(en,en)`/`_html(en,en)`/`b(en,en)` fallbacks (the 4th shape),
not `t()` keys. They are intentional pending-translation placeholders (English fallback),
**not** "Khmer replaced by English" corruption — `en` always equals the source English.

| Module | unique bilingual helper pairs | Stuck EN (en==km) | Real Khmer (en!=km) |
|---|---|---|---|
| account.js | 17 | 17 | 0 |
| analytics.js | 23 | 23 | 0 |
| billing.js | 28 | 27 | 1 |
| dashboard.js | 10 | 10 | 0 |
| designer.js | 6 | 3 | 3 |
| guests.js | 63 | 63 | 0 |
| materials.js | 11 | 4 | 7 |
| reset.js | 8 | 8 | 0 |
| responses.js | 18 | 16 | 2 |
| templates.js | 57 | 56 | 1 |
| verify.js | 0 | 0 | 0 (relies on HTML spans) |
| checkin-v13.js | 9 | 9 | 0 |

## 9. V2 checker gap (KNOWN GAP — must fix)

`scripts/check-bilingual-consistency.py` scans **only top-level `src/js/*.js`**
(`js_dir.glob("*.js")` — NOT recursive) for the two STRINGS-table patterns:

- Pattern A: `key: { en: '…', km: '…' }`
- Pattern B: `en: { key:'…' }, km: { key:'…' }`

It does **not** recognize:
1. the page-module helper shape `_txt(en,km)` / `_html(en,km)` / `b(en,km)`;
2. `.i18n-en` / `i18n-km` HTML spans;
3. `EInviteI18n.langText(…)`, `COPY={en,km}`;
4. **any file under `src/js/pages/admin/`** (feature-flags.js, admin.js, users.js,
   invitations.js, audit-log.js, system-health.js, reports.js) and `src/js/components/*`.

Consequence: the unchanged **239 en / 239 km, 0 missing, 0 identical** result is NOT
evidence that the 11 modules gained bilingual strings — those additions use the helper
shape, which the checker never inspects. The checker is therefore **blind to 16
byte-identical `t()` keys** (§8a) and to the hundreds of English-fallback helper strings
(§8b). Recommend extending the scan to `src/js/**/*.js` and adding helper-shape detection.

## 10. Cleanup status

- `.gitignore`: **updated** — added `node_modules/` (git diff confirms). [GIT]
- `package.json` / `package-lock.json`: **absent** at repo root (npm ran with `--no-save`),
  consistent with the cleanup note. [GIT]
- The three prior-session debris scripts (`test_ff_bidi.py`, `test_ff_screenshots.py`,
  `test_bidi_screenshots.py`) are **absent** from the working tree — they were never tracked
  by git and are not present on disk. (They were NOT deleted by this session.)
- Remaining prior-session debris screenshots in `screenshots/` (e.g. `async-test.png`,
  `dom-test.png`, `ff-profile-test.png`, `i18n-*.png`, `test-*.png`, `dashboard-*.png`)
  were intentionally **left untouched** — per the hard rule, deletion of existing
  `screenshots/*.png` requires explicit user confirmation. They are listed under §14
  "Found but out of scope."

## 11. Feature flags tab verdict

See §6. Root cause is **NOT "stale bundles"**; it is a newly-implemented feature that
required a bundle recompile (normal build sync). UNRESOLVED-as-a-bug: no pre-existing
tab existed at `HEAD` to be "stale," so the defect description does not hold. The tab now
renders and toggles ([BROWSER]).

## 12. Out-of-scope findings carried into §14

`src/python/server.py` (+168 ins / −3 del, `-w`), `src/python/build/build_route_bundles.py`
(+8/−7) and `src/python/build/sync_frontend_assets.py` (+2/−1) are **hand edits to
`src/python/`** (not build-sync outputs — build scripts do not self-modify, and `server.py`
is source, never generated). All three predate the i18n agent (mtimes 2026-09-26 15:52,
2026-09-28 06:36 and 08:47; agent started 2026-09-28 20:05). They are migration debt and
were **not** created by this verification pass; they are left in place (no revert) pending
user confirmation — see §14.

---

## 13. Checker fixes (A2) — completed 2026-09-29

`scripts/check-bilingual-consistency.py` was updated with three changes:

1. **Regex-literal awareness in `_find_object_literals()`** — The brace-balanced
   scanner now detects JavaScript regex literals (e.g. `/[&<>"']/g` in `esc()` helpers)
   and correctly skips them. Without this fix, the `"` inside a regex is mistaken for a
   string start, causing the scanner to swallow the rest of the file. This also fixes
   the original checker's missed STRINGS tables in admin subdirectory files (e.g.
   `pages/admin/feature-flags.js`, `pages/admin/admin.js`, `pages/admin/users.js`,
   `pages/admin/invitations.js`, `pages/admin/audit-log.js`, `pages/admin/system-health.js`,
   `pages/admin/reports.js`, `components/chart.js`).

2. **Recursive file discovery** — `discover_js_files()` now uses `rglob('*.js')` instead
   of `glob('*.js')`, covering `src/js/pages/admin/*` (9 files), `src/js/editor/*` (10 files),
   `src/js/editor/canvas/*`, `src/js/editor/chrome/*`, `src/js/editor/collab/*`,
   `src/js/editor/history/*`, `src/js/editor/media/*`, `src/js/editor/text/*`,
   `src/js/pages/auth/*`, `src/js/pages/dashboard/*`, `src/js/public/*` — 208 non-bundle
   JS files (vs 169 before).

3. **Helper-span recognition** — Added `HelperPair` dataclass and `scan_helper_calls()`
   matching `_txt(en,km)`, `_html(en,km)`, `b(en,km)`, `langText(en,km)` call shapes.
   These are integrated into `scan_file()`, `find_missing_km()`, `find_identical_pairs()`,
   `render_markdown()`, `render_json()`, and stdout output.

### Checker results (before → after)

| Metric | Before | After |
|---|---|---|
| JS files scanned | 169 (non-recursive) | 208 (recursive) |
| STRINGS-table en:/km: pairs | 239 | 556 |
| Helper-call spans | 0 | 303 |
| Total bilingual strings | 239 | 859 |
| Missing km | 0 | 0 |
| Byte-identical pairs | 0 | 299 |
| Exit code (--strict) | 0 | 0 |

### Exit-code contract

The checker still exits 0 as long as there are no **missing** km translations
(`en` exists but `km` is empty/null). Byte-identical `(en, km)` pairs are reported
as `PLACEHOLDER` (or `legitimate` if on the exception list) in the output but are
**not** treated as failures — the user has explicitly accepted `en==km` English
fallback as a transitional state pending hand translation. The `--strict` flag and
the exception list (`DEFAULT_EXCEPTION_STRINGS`, `EXCEPTION_PATTERNS`) are unchanged.

### TRANSLATIONS.csv (A1) — single-file hand-edit source of truth

`docs/i18n/TRANSLATIONS.csv` is generated by an inline Python scanner (run via
`python3 << 'PYEOF'` heredoc, since the sandbox blocks temporary-file
writes for the heredoc writer but Python `open()` succeeds). It covers all four
i18n shapes:

1. **STRINGS-table pairs** (Pattern A: `key: { en: '…', km: '…' }` and Pattern B:
   `en: { k:'…' }, km: { k:'…' }`) — 556 pairs
2. **Helper-call spans** (`_txt(en,km)`, `_html(en,km)`, `b(en,km)`, `langText(en,km)`) —
   303 pairs
3. **Inline HTML spans** (`.i18n-en` / `.i18n-km` dual spans) — across `src/html/*`
4. **`data-en`/`data-km` attributes** on form fields — across `src/html/*`

CSV columns: `text, key, en, km, status, file, line`. Status values:
`translated` (en≠km), `fallback` (en==km), `missing` (km empty). Sorted by file, line.

**Totals: 1121 rows — 603 translated, 518 fallback, 0 missing.**

### Feature flags tab verdict (Part D — verified via Puppeteer)

Puppeteer computed-style verification on `bundle-admin-v15.css`:

- **EN state** (`html lang="en"`): `.i18n-km` inside `[data-admin-tab="feature-flags"]`
  has `display: none` ✅ — Khmer text correctly hidden.
- **KM state** (`html lang="km"`): `.i18n-en` inside the same tab has
  `display: none` ✅ — English text correctly hidden.
- **Toggle back to EN**: `.i18n-km` returns to `display: none` ✅.

Bundle CSS grep (`bundle-admin-v15.css`) for `[lang="en"] .i18n-km` rules:
- `[lang="en"] .i18n-km{display:none}` — active on admin page (no `!important`)
- `[lang="km"] .i18n-km{display:inline}` — active on admin page
- `.guest[data-language="en"] .i18n-km{display:none!important}` — higher specificity +
  `!important`, but **only applies within `.guest` context** (not present on admin page).

**Verdict: PASS. No conflicting rules. The feature flags tab correctly toggles
between EN and KM. The "stale bundles" claim was not the root cause — the tab was
newly implemented and required a bundle recompile (normal build sync).**
