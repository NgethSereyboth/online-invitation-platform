# Dogfood report — 2026-10-15

Target: local dev server (`make dev` equivalent) at `http://127.0.0.1:8231`, clean data dir,
Playwright-free [agent-browser](https://www.npmjs.com/package/agent-browser) 0.39.0 session
(Chromium 1280×633). Signed in as `admin@einvite.test` (role `admin`, plan `studio`); one
invitation created through the UI (`Sokha & Dara Wedding`, published as `/i/sokha-dara-wedding`).

## Summary

| Severity | Count | Issues | Status after the fix pass |
|----------|-------|--------|-----------------------------|
| High | 2 | ISSUE-001, ISSUE-004 | fixed, verified in the browser |
| Medium | 1 | ISSUE-002 | fixed, verified end to end |
| Low | 1 | ISSUE-003 | fixed, verified in the browser |

The fix pass, its files, its measurements and its verification are in
[Fix pass — later the same day](#fix-pass--later-the-same-day); ISSUE-004 was found while
verifying the ISSUE-002 fix.

**Load sweep (16 pages) came back clean, and each page is proven to have rendered**: run by
`sweep.py` (re-runnable; `python3 docs/reviews/dogfood-2026-10-15/sweep.py` against a dev server on
port 8232) over `index, dashboard, admin, account, billing, verify, reset, privacy, guests,
responses, analytics, materials, checkin, templates, designer, public`. Every page reported its own
`body[data-page]` marker with non-zero visible text — so "no errors" cannot mean "never loaded" —
and the totals were **16/16 loaded · 0 page errors · 0 console errors · 0 4xx/5xx**, including the
new `bundle-*-deferred-v15.js` chunks. This sweep ran signed-out; the flows below ran signed-in.
Raw logs: `sweep/<page>.txt`, totals: `sweep/SUMMARY.txt`.

Verified as *not* bugs (recorded so nobody re-investigates):

- Onboarding tour re-appearing after sign-in is by design: the seen key is identity-scoped
  (`einvite-final-tour-seen-v2:local-anonymous:studio-v27` → `...:<user-id>:studio-v27`), and it
  records the signed-in identity after the first dismissal.
- Doubled labels in accessibility snapshots (`"Usersអ្នកប្រើ"`) are hidden Khmer spans
  (`display: none`, no `aria-hidden`) — a snapshot artifact, not user-visible.
- `Publish snapshot` fires exactly one `POST /api/invitations/<id>/publish` per click (201).
- The admin impersonate panel loads from the deferred chunk and mounts
  (`window.EInviteAdminImpersonate` is an object; `bundle-admin-deferred-v15.js` is fetched).

---

## ISSUE-001 — Guest cover gate is mouse-only: RSVP can be submitted without opening the invitation

**Severity**: High (integrity bypass + silent failure for mouse users)
**Page**: `/i/<slug>` (public guest route), e.g. `http://127.0.0.1:8231/i/sokha-dara-wedding`
**Screenshots**: `screenshots/issue-001-cover-blocks-form.png` (cover up — it fills the whole
viewport, which is why every frame taken in this state is byte-identical),
`screenshots/issue-001-after-open-form-reachable.png` (the same page after opening: the RSVP form
is there and clickable)

### What happens

While the "opening scene" cover is up, the invitation content behind it is neither `inert` nor
`aria-hidden`. The cover (`#openCover`, `position: fixed; inset: 0; z-index: 9999;
pointer-events: auto`) swallows every **mouse** click aimed at the content underneath, while the
same controls stay reachable by **keyboard and assistive tech** — so the RSVP form can be
submitted without ever opening the invitation, and a mouse user who tries the visible submit
button gets nothing at all: no request, no message, no error.

### Evidence

```
document.elementFromPoint(center of "Send RSVP")
  → STRONG (inside BUTTON#openCover.open-cover opening-scene-silk-curtain)
    BUTTON#openCover ... , SPAN.i18n-en, BUTTON.primary  ← the real submit button, 4th in the stack

#openCover   position: fixed, inset 0/0/0/0, z-index 9999, opacity 1, pointer-events auto
#rsvp        aria-hidden = null, inert = false
  fields     input/select/textarea/button all tabIndex 0, aria-hidden = null
             (only the honeypot field is tabIndex -1 / aria-hidden true)
```

### Steps

1. Open `/i/sokha-dara-wedding` in a fresh session — the cover is up
   (`screenshots/issue-001-cover-blocks-form.png`).
2. Fill "Your name" in the RSVP form (the form is in the DOM and focusable even though it is
   behind the cover).
3. Mouse-click **Send RSVP** → **no network request at all** (request-log delta 527 → 527, and
   `elementsFromPoint` at the button centre returns `BUTTON#openCover` above `BUTTON.primary`).
   Silent no-op, no message, no console error.
4. Scroll the RSVP section into view and mouse-click again → still no request: the button is
   genuinely under the cover, not merely off-screen.
5. Keyboard path: focus **Send RSVP** and press Enter → `POST /api/public/sokha-dara-wedding/rsvps`
   returns **201 while the cover is still visible**. Gate bypassed.
6. Click **Open invitation** → the cover becomes `visibility: hidden; pointer-events: none`
   (`screenshots/issue-001-after-open-form-reachable.png`); the same mouse click now submits
   normally (201). This is the intended flow and it works.

Evidence for steps 3–5 is the request log plus the hit-test data above (the pre-open screenshots
cannot show the difference: the fixed cover covers the entire viewport in every frame).

### Expected

Either the cover should make the content behind it unreachable for *every* input method
(`inert` / `aria-hidden` / `tabindex="-1"` on the guest layout until the invitation is opened), or
the submit path should refuse/short-circuit when the content is not open — not "mouse blocked,
keyboard allowed".

---

## ISSUE-002 — Admin "Templates" and "AI providers" tabs render an empty panel

**Severity**: Medium (dead navigation in the admin console)
**Page**: `/admin.html`
**Screenshot**: `screenshots/E1-admin-templates-blank.png`

### What happens

Both tabs are present and clickable, and switching to them activates the correct panel, but the
panel is completely empty — `innerHTML` length 0, 0 children, and no request is made for either
tab's data. There is no empty state ("No templates found."), no spinner and no console error, so
the tab simply looks broken.

### Evidence

```
#templatesPanel  hidden=false, innerHTML length 0, children 0, innerText length 0   (after 4s)
#aiPanel         innerHTML length 0, children 0, innerText length 0
Tab sweep: users 326 chars · templates 0 · invitations 217 · ai 0 · feature-flags 1250 · system 250
Requests fired on the page: /api/admin/{metrics-v2, system-status, invitations-v2, feature-flags,
settings, metrics} — none for templates or AI providers.
```

`src/js/admin.js` contains the renderers for both panels (`renderTemplates()` with a
"No templates found." empty state, and the AI-provider list), but that monolithic file is **not**
part of `admin.html`'s route bundle — the page ships `pages/admin/*` only, and none of those
modules render `#templatesPanel` or `#aiPanel`.

### Steps

1. Open `/admin.html` as an admin.
2. Click the **Templates** tab → panel area is blank. (`screenshots/E1-admin-templates-blank.png`)
3. Click the **AI providers** tab → blank as well.

### Expected

Either the tab is implemented (data + empty state), or the tab is not offered. A tab that renders
nothing with no message is worse than a disabled one.

---

## ISSUE-003 — Malformed Khmer `aria-label` on the interface language switch

**Severity**: Low (i18n / assistive-tech text)
**Where**: every page with the shell language switch — all 16 routes ship `core/i18n.js`

### What happens

The Khmer button of the interface language switcher announces
`ប្ដូះបើកភាសាខ្មែរ` — "ប្ដូះបើក" is not a Khmer word (the verb is "ប្តូរ"), so a screen reader
reads nonsense instead of "switch to Khmer". The English sibling is fine, and the guest-page
counterpart uses correct Khmer, so this one string is the outlier.

### Evidence

```
src/js/core/i18n.js:147   kmBtn.setAttribute("aria-label", "ប្ដូះបើកភាសាខ្មែរ");
src/js/core/i18n.js:144   enBtn.setAttribute("aria-label", "Switch to English");
src/js/public-page.js:11  ... aria-label="បង្ហាញការអញ្ជើញជាភាសាខ្មែរ"   ← correct Khmer phrasing
a11y snapshot (every page): button "ប្ដូះបើកភាសាខ្មែរ"
```

### Expected

A valid Khmer phrase for "switch to Khmer", e.g. `ប្តូរទៅជាភាសាខ្មែរ`, ideally sourced from the same
translation table as the rest of the bilingual copy.

---

## Fix pass — later the same day

Server: `EINVITE_DATA_DIR=/tmp/einvite-dogfood python3 src/python/server.py --port 8241`, same
browser session and profile as the sweep (`agent-browser` 0.39.0, Chromium). Each fix below was
verified **through the interface a user uses**, not by inspecting code.

### ISSUE-001 — the cover is now a real gate

[opening-scenes.js](../../../src/js/opening-scenes.js) gained `gate(root)`: every sibling of `#openCover`
(and anything a later enhancer appends to that root — a `MutationObserver` keeps it true, which is
why `guest-journey.js`'s dock is caught even though it is appended after the gate runs) is marked
`inert` + `aria-hidden` until the cover is dismissed, and the dismissal moves focus into the
invitation. `enhance()` is wired to it, so the published guest page and the editor's guest-preview
modal ([app.js](../../../src/js/app.js), which renders its own cover and does not load `public-page.js`)
both use the same implementation. `public-page.js` was not modified: it already funnels every
cover click through `#openCover`.

Measured on `/i/sokha-dara-wedding`, gate up:

```
#publicRoot children: DIV[inert] BUTTON#openCover NAV[inert] DIV[inert] P[inert] SECTION[inert] ×3
.guest-layout-shell   inert = true, aria-hidden = "true"
```

| Test | Before | After |
|------|--------|-------|
| `#rsvp button.focus()` | focus accepted | **focus refused** (`activeElement === BODY`) |
| real `Enter` on that button | `POST /api/public/<slug>/rsvps` → **201** | **no request** |
| real mouse click at the same point | silent no-op | the click lands inside `#openCover` (element at point: `STRONG` → `BUTTON#openCover`) and **opens** the invitation; no request |
| keyboard open (`focus #openCover` + `Enter`) | — | gate released, focus lands on the first waypoint section (`SECTION.artistic-hero-section`, `tabindex=-1`, `scrollY` unchanged) |
| RSVP after the cover opens | — | `POST …/rsvps` → 200 (already-RSVP'd guest updates) |

The before/after row is an A/B on one page load, not a reconstruction: the pre-fix state is
reproduced by removing the two attributes from the gated siblings, and the bypass returns the
instant they are gone (`focusedIsButton: true` → 201). That isolates `inert` as the mechanism.

Editor preview (index.html → *Guest preview*): `#modalBody` children are `BUTTON#openCover` +
`DIV[inert]`; clicking the cover releases the gate, clears `aria-hidden`, and focuses
`SECTION.artistic-hero-section` inside the preview. Screenshot:
`fix-editor-preview-gate.png`.

### ISSUE-002 — both panels now render

New deferred modules [templates.js](../../../src/js/pages/admin/templates.js) and
[ai-providers.js](../../../src/js/pages/admin/ai-providers.js) (both version 55) follow the shipped
`users.js`/`feature-flags.js` conventions: their own search input, `ei-admin-table` markup, an
`aria-live="polite"` status line, an explicit empty state, and an error state with a retry button.
They are listed in `deferredScripts` for `admin.html` in
[route-bundle-sources-v15.json](../../route-bundle-sources-v15.json) and registered in the shell's
`mountModule` map, so neither panel costs the admin route any startup bytes: `admin.html` loads
161,482 B of script against the 159 KiB (162,816 B) Lighthouse ceiling, its startup bundle is
151,522 B, and the deferred chunk grows to 21,848 B — a file no page HTML references, so it is not
measured by any route budget. Verified with a real admin account:

- **Templates** — tab click renders 5 columns; one row for the template created through the API
  (`Verification Wedding Template`, owner `fixver@dogfood.test`, v1); `GET /api/admin/templates`
  fires; typing a non-matching query swaps in the empty state, clearing it restores the row.
- **Save path** — selecting *Marketplace* and clicking *Save* → `PUT /api/admin/templates/<id>/visibility`,
  live region reads `Visibility saved for “Verification Wedding Template”.`, the select stays on
  `public`, the database row becomes `visibility=public, marketplace_status=approved`, and the audit
  trail gets `admin.template_visibility_changed {"admin":true,"visibility":"public"}`.
- **AI providers** — renders *Model routing* + *Providers*; on this server (local AI off) it shows
  `Local AI providers are disabled on this server (EINVITE_LOCAL_AI is off).` and fires
  `GET /api/admin/ai/providers`. The populated path was driven with a synthetic payload through the
  shell API: two provider cards (`Healthy`/`Unavailable` tags), `<details>` model list
  (`llama3:8b · text · tools yes · vision no · structured yes · context 8192`), role list
  (`planner=llama3:8b · available`) and the model-directory line.

Screenshots: `fix-admin-templates.png`, `fix-admin-ai-providers.png`.

### ISSUE-003 — Khmer label corrected

[i18n.js](../../../src/js/core/i18n.js) now sets `ប្តូរទៅជាភាសាខ្មែរ` ("switch to Khmer") instead of the
malformed string. Verified in the browser on `dashboard.html`: the switch group still announces
`Select interface language`, the English button `Switch to English`, and the Khmer button
`ប្តូរទៅជាភាសាខ្មែរ` with `lang="km"`.

### ISSUE-004 (new, High) — the admin table header covered the first row

Found while verifying the ISSUE-002 fix: the Save button in the new panel could not be clicked.
`body[data-page="admin"] .admin-panel table { overflow: hidden }` made each table its **own scroll
container**, so the sticky `thead`'s `top: var(--app-topbar-h)` resolved against the table box
instead of the viewport: the header sat a permanent 48–56px below the table top and stayed there
(never pinning under the topbar while scrolling), covering the first row.

| Panel | header bottom vs first row top | hit-test at the first row's button centre |
|-------|-------------------------------|-------------------------------------------|
| Templates (1 row) | overlap **48 px** | `TH` (Save unreachable) |
| Users (3 rows) | overlap **56 px** | `TH` (first row's actions unreachable) |

Fixed in [admin-page.css](../../../src/css/admin-page.css) by using `overflow: clip` instead of `hidden`:
`clip` keeps the rounded-corner clipping but does not create a scrollport, so the header pins under
the topbar while the page scrolls (measured: `thY = 56` with the table top at 20) and never overlaps
a row (measured overlap `0 px`, `elementFromPoint` at the button centre returns the button).
Before/after screenshot: `fix-admin-sticky-overlap-before.png`.

### Verification of the fix pass

- `python3 build.py all` + `python3 build.py check` → `BUILD_OK … (check)` (editor bundle, 16 route
  bundles, page manifests, `src/python/` mirror all current).
- Full suite with the repo's venv: `.venv/bin/python -m pytest tests/ -q` → **86 passed, exit 0**
  (154 s). With the system Python, six browser tests fail to collect (`No module named 'playwright'`)
  — an environment gap, unchanged by this work; the venv runs them.
- Targeted gates re-run after the last edit: `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED`,
  `V16_PERFORMANCE_BUDGET_TEST_PASSED`, `STATIC_INTEGRITY_TEST_PASSED`,
  `V27_3_5_RELEASE_EVIDENCE_TEST_PASSED`, `V28_AGENT_PERFORMANCE_CONTRACT_TEST_PASSED`,
  `V0_52_SELECTED_CAPABILITIES_CONTRACT_TEST_PASSED`,
  `OK: bilingual consistency check passed`.

### Still open (not fixed here)

`#adminSearch` in `admin.html` is still unwired: no shipped module reads it (`users.js` and
`invitations.js` render their own search boxes, and the two new panels do the same), so it is a
dead control. It is deliberately left alone because `docs/a11y/WCAG-AA-AUDIT.md` records it as P1-E
evidence and the fix is a design choice (one global search wired to the active panel vs per-panel
search everywhere), not a cleanup.

---

## Environment limits

- Findings are from the browser only; the issues above were each reproduced at least twice.
- The sweep is reproducible via `sweep.py`; it fails (exit 1) if any page fails to report a marker
  or shows no text, so a silently broken page cannot pass as "clean".
- No Playwright was used; `agent-browser` 0.39.0 drove Chromium over CDP.
- `agent-browser record start` produced no video file in this environment (no output, and
  `record stop` reported "No recording in progress"), so ISSUE-001 carries screenshot + DOM/network
  evidence instead of a repro video.
- The screenshots in this directory are working evidence, not committed assets (see the repository
  note about review screenshots).
