# Khmer gap — round 5 inventory (2026-10-24)

**Purpose.** After LT-1.2 applied the main map, ADDENDUM and ADDENDUM-2, this file records every
**English UI string still visible in Khmer mode** at 375 px that has **no map row**. Per rule R3
nothing here is translated; Claude drafts the next addendum from this list.

**Method.** `artifacts/next-work/lt-1-2/gap-probe.py` signs in with the FB-35 seed account, sets
`einvite-lang=km`, walks the ten routes named in the plan at 375×667, and collects visible
leaf-level text and accessible-name attributes containing Latin letters
(`artifacts/next-work/lt-1-2/gap-probe.json`). Excluded from the tables below, because they are
**not UI copy**:

- seeded invitation content (titles, messages, dates, venue, guest names, RSVP answers);
- built-in template names, descriptions and tags (`Royal Khmer Gold`, `Modern Cambodian Luxury`, …);
- account/session/audit values (email, role, plan id, user agent, timestamps, IP, storage numbers);
- deliberate Latin tokens from the map's §0 allowlist (`RSVP`, `CSV`, `QR`, `Visa`, `Mastercard`,
  `Passkey`, `OKID`, `px`, units, card brands) and the language names in the switch;
- `English` in the language switch (a language name, shown in its own language by convention).

**Counts.** 25 unique visible strings on dashboard, 25 on guests, 30 on templates, 11 on materials,
15 on responses, 13 on analytics, 270 on account, 33 on billing, 7 on admin, 62 in the editor
chrome. The account figure is dominated by audit/session data; the UI-copy subset is in the table.

## Dashboard — `src/html/dashboard.html` + `src/js/dashboard.js` / `final-polish.js`

| EN | Where seen | Key / source |
|---|---|---|
| Draft, Published | card overlay `span.fp-project-status` (white-on-white today, LT-1.4) | template literal `${status}` |
| 0 views / 135 views | card meta `div.stats > span` | `${i.views||0} views` |
| 0 RSVPs / 1 RSVPs | card meta `div.stats > span` | `${i.rsvps||0} RSVPs` |
| Wedding (event tag) | thumbnail meta (seed content type) | document `eventType` |
| customer · free · Server | `span#accountName` | role/plan/host joined in JS |
| Workspace | launcher menu `header > strong` (open the grid menu) | `src/js/app.js` (shared, outside `.i18n-km`) |
| Open workspace navigation, Account menu, Filter invitations, Select interface language, Switch to English, Text overflow, Open … | `aria-label` only | shared header / card renderer |

## Guests — `src/html/guests.html` + `src/js/guests.js`

| EN | Where seen | Key / source |
|---|---|---|
| Add guest | `form#addForm > button.primary` | static HTML, no i18n pair |
| · not-sent | `div.guest-meta` on each row | JS status suffix |
| Guest name, Phone number, Email, Group, Household, Table, Seat, Tags, comma separated | `input#addName`, `#addPhone`, `#addEmail`, `#addGroup`, `#addHousehold`, `#addTable`, `#addSeat`, `#addTags` placeholders | static HTML attributes |

## Templates — `src/html/templates.html` + `src/js/templates.js`

| EN | Where seen | Key / source |
|---|---|---|
| Template Studio | `div.studio-head h1` | static HTML |
| Manage reusable invitation designs, versions, favorites, and editable copies. | `div.studio-head p` | static HTML |
| Favorites only | `label.toggle-row span` | static HTML |
| Built-in, Premium, Wedding, Birthday, Business | card tag/version spans | JS template metadata |
| Open workspace navigation, Open navigation, Appearance, Select interface language, Switch to English, Workspace navigation | `aria-label` only | shared header |

## Materials — `src/html/materials.html` + `src/js/materials.js`

| EN | Where seen | Key / source |
|---|---|---|
| Material Library | `div.library-head h1` | static HTML |
| Your account-wide collection of photos, music, and invitation videos. | `div.library-head p.library-hint` | static HTML |
| Folder | `input#folderFilter` placeholder | static HTML attribute |
| (mixed Khmer + Latin `s`) | `div#summary > span` — the favorites count mixes Khmer with a Latin plural suffix; rule-4 style damage, not a translation gap | `src/js/materials.js` summary render |

## Responses — `src/html/responses.html` + `src/js/responses.js`

| EN | Where seen | Key / source |
|---|---|---|
| Responses & wishes | `div.response-top h1` | static HTML |
| Export RSVP CSV | `button#exportRsvp` | static HTML (CSV is allowlisted; the rest is copy) |
| RSVP responses, Guest wishes | `div.response-tabs button` | static HTML |
| Search responses… | `input#responseSearch` placeholder | static HTML attribute |

## Analytics — `src/html/analytics.html` + `src/js/analytics.js`

| EN | Where seen | Key / source |
|---|---|---|
| Yes, joyfully | `div.status-row span` | RSVP answer value (data), not UI copy |
| (RSVP labels) | metric/summary headings already carry Khmer + the allowlisted `RSVP` token | — |

## Account — `src/html/account.html` + `src/js/account-security.js`

| EN | Where seen | Key / source |
|---|---|---|
| Not enabled | `strong#v13MfaState` | JS fallback |
| No passkeys registered yet. | `div#v13Passkeys p.download-note` | JS render |
| Current | `span.v13-session-current` | JS render |
| Sign out here, Revoke | `div.v13-row button` | JS render |
| customer, Free | `strong#accountRole`, `strong#accountPlan` | role/plan values |
| Passkey | `small > span.i18n-km` — the map keeps the Latin token by design | map row |
| Cannot set properties of null (setting 'hidden') | `p#v13SecurityStatus` | **runtime page error surfaced to the user**; a defect, not a translation gap (recorded for the next account-security pass) |

## Billing — `src/html/billing.html` + `src/js/billing.js`

| EN | Where seen | Key / source |
|---|---|---|
| Free | `strong#currentPlan` | plan id |
| Creator, Studio | `article.plan h2` | plan names (data) |
| Create and publish invitations, Basic templates and editor, RSVP and guest tools, 250 MB material storage, Higher invitation capacity, Large reusable template library, 5 GB material storage, Designed for frequent creators, High-volume invitation production, Designer and studio workflows, 50 GB material storage, Best fit for professional teams | plan feature `li > span.i18n-km` | English in the km slot: `plan.features` rendered through `b(feature, feature)` |
| Secure card checkout | `strong#gatewayName` | JS fallback |
| Online card payment is not available yet. | `div#billingNotice` | JS message |
| (mixed Latin role + Khmer) | `div#planRole` | role value concatenated in JS |

## Admin — `src/html/admin.html`

The signed-in non-admin state (the only one tested) is the English 403 page; its copy belongs to
LT-1.8's empty/error-state item. Remaining Latin here is `aria-label` only: Open workspace
navigation, Open navigation, Appearance, Select interface language, Switch to English, Workspace
navigation.

## Editor chrome — `src/html/index.html` + editor JS

The editor has **no Khmer chrome** yet. Visible at 375:

| EN | Where seen |
|---|---|
| Add, Focus, Flow, Position, Assets, Text | `div.toolbar.studio-canvas-toolbar` buttons |
| Canvas, Tools, Quick Edit, Preview, Publish, Advanced | `nav#mobileEditorV14Bar` buttons |
| Published invitation, Invitation flow, Drag sections and pages to change the order guests see them., Opening / main hero, Fixed opening, Gallery, Invitation section, Featured video, Countdown | `aside#workflowV6Flow` |
| Main hero canvas | `div#workflowV5Status` |
| (plus the panel labels, inspector headings, palette sections and dialogs in `gap-probe.json`) | editor panels |

The editor is Phase 4 work (`LT-4.x`); its chrome strings need a map section of their own before
Phase 4 starts.

## Notes for the next addendum

1. The card status/meta (`Draft`, `Published`, `views`, `RSVPs`) and the materials mixed-string
   are the three items the plan predicted; they are JS template literals with no translation key,
   so the map needs a `key` for each or the renderer needs a bilingual helper first.
2. The editor chrome is the largest block (62 unique strings at 375 alone); do not start Phase 4
   before its map exists.
3. `Cannot set properties of null (setting 'hidden')` on account is a product defect independent of
   language; it should be fixed in the account-security item, not translated.
