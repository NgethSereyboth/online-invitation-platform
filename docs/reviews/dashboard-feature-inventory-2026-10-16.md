# Dashboard feature inventory

**Scope:** the `dashboard` route only (`src/html/dashboard.html` + its route bundle).
**Method:** driven in a real browser (agent-browser → local Edge, CDP) against the local
server at `http://127.0.0.1:4175`, logged in as a demo account, combined with a read of
the page markup, `src/js/dashboard.js`, and the injected app-shell layer in `bundle-dashboard.js`.
**Gathered:** 2026-10-16.

Legend

- **seen** — observed in the rendered browser (accessibility tree, DOM, computed styles).
- **source** — confirmed in source only; not individually exercised in the browser.

Screenshots: `artifacts/dash/01-dashboard-initial.png`, `02-dashboard-auth.png`,
`03-create-dialog.png`, `04-dashboard-populated.png`, `05-dashboard-mobile.png`,
`07-account-menu.png`.

---

## A. Auth view — lives inside dashboard.html

Shown when signed out; `#loginView`, hidden once a session exists.

| # | Feature | Evidence |
|---|---|---|
| 1 | Sign in / Create account segmented tabs (`role="tablist"`, `aria-selected`) | seen |
| 2 | Email field | seen |
| 3 | Password field | seen |
| 4 | Confirm password (`#registerConfirmWrap`, register only) | seen |
| 5 | Primary submit (`#loginBtn`) | seen |
| 6 | "or" divider | seen |
| 7 | **Use a passkey** (WebAuthn, `#passkeyLoginBtn`) | seen |
| 8 | Forgot password → `reset.html` | seen |
| 9 | Privacy → `privacy.html` | seen |
| 10 | `#authStatus` status line (`role="status"`, `aria-live`) | seen |

## B. Global header and the injected UI layer

Items 11–18 are markup in `dashboard.html`. Items 19–26 are created at runtime by
`bundle-dashboard.js` on **every** page that loads it, not just the dashboard.

| # | Feature | Evidence |
|---|---|---|
| 11 | Brand → `dashboard.html` | seen |
| 12 | Breadcrumb "Workspace / My invitations" (`aria-current="page"`) | seen |
| 13 | Account line: `email · role · plan · Server` (`#accountName`) | seen |
| 14 | **Appearance** button (`aria-haspopup="menu"`, `aria-expanded`) → menu **Light / Dark only** | seen |
| 15 | **Account menu** avatar → popover: Account settings, Materials, Plans & usage, Designer workspace *(hidden)*, Administration *(hidden)*, Sign out | seen |
| 16 | EN / ខ្មែរ switch (`role="group"`, "Select interface language") | seen |
| 17 | Sign out (`#logoutBtn`) — hidden on this page by CSS | seen |
| 18 | Skip to content (`a.skip-link`) | seen |
| 19 | Workspace launcher (9-dot, "Open workspace navigation") → Dashboard, Templates, Materials, Designer, Plans, Account | seen |
| 20 | Current-page highlight (`ui-current`) | source |
| 21 | Ripple on every button (`ui-ripple`, global `pointerdown`) | source |
| 22 | Global tooltip system replacing native `title` (`ui-tooltip`, `data-ui-tooltip`) | seen |
| 23 | Toast stack (`ui-toast-stack`, `window.einviteToast`) | source |
| 24 | Route progress bar (`final-route-progress`) | source |
| 25 | Page-leave animation (`ui-page-leaving`, 115 ms delayed navigation) | source |
| 26 | Spotlight hover on ~16 card selectors (`ui-spotlight`, `--mx`/`--my`) | source |
| 27 | Theme controller (`EInviteThemeController`, `localStorage['einvite-theme-mode']`, `theme-transition`) | seen |

## C. Navigation — three overlapping systems

| # | Feature | Evidence |
|---|---|---|
| 28 | Left rail `.app-rail` (`hidden`, `data-rail-auto`): Dashboard, Templates, Materials, Guest list, Responses, Analytics, Plans, Account | seen |
| 29 | Rail collapse `«` (`data-rail-toggle`) | seen |
| 30 | Drawer toggle `☰` (`data-drawer-toggle`) | seen |
| 31 | Rail visible at 390 px alongside the two toggles above | seen |

## D. Page header and quick start

| # | Feature | Evidence |
|---|---|---|
| 32 | Title "My invitations" | seen |
| 33 | "Template Studio" → `templates.html` (`#studioBtn`) | seen |
| 34 | "+ Create invitation" (`#newBtn`) | seen |
| 35 | Quick start: **✦ New invitation** (`#quickstartNew`) | seen |
| 36 | Quick start: **⌂ Templates** (`#quickstartTemplates`, inline `onclick`) | seen |
| 37 | Quick start: **👥 Guest list** (`#quickstartGuests`) | seen |

## E. List toolbar

| # | Feature | Evidence |
|---|---|---|
| 38 | Search invitations | seen |
| 39 | Filter tabs All / Published / Archive | seen |
| 40 | Empty state + "Create your first invitation" | seen |

## F. Invitation card

| # | Feature | Evidence |
|---|---|---|
| 41 | Rendered thumbnail (390×844 artboard, `--preview-*` vars, `.fp-thumb-fallback`) | seen |
| 42 | Status pill (Draft / Published), `.fp-project-status` | seen |
| 43 | Title | seen |
| 44 | Stats: "0 views · 0 RSVPs", or "Invitation only" | seen |
| 45 | Inline **Edit** button | seen |
| 46 | Inline **Guests** link | seen |
| 47 | Inline **Analytics** link | seen |
| 48 | Overflow ⋮ menu: **Duplicate**, **Archive ↔ Restore**, **Delete** (`.danger`) | seen |
| 49 | Archived cards dimmed and disabled | source |

## G. Create-invitation dialog (`#createDialog`)

| # | Feature | Evidence |
|---|---|---|
| 50 | Invitation name (`#newTitle`, `maxlength=120`) | seen |
| 51 | Event type (`#newType`: Wedding / Birthday / Business event) | seen |
| 52 | Template search (`#templateSearch`) | seen |
| 53 | Filter tabs: All, Wedding, Birthday, Business, My templates, Marketplace, ★ Favorites | seen |
| 54 | Built-in template grid (`#templateChoices`) | seen |
| 55 | Delete-× on your own templates | seen |
| 56 | Selection summary (`#templateSummary`) | seen |
| 57 | Hint text | seen |
| 58 | Cancel / Create from template | seen |

## H. Template preview dialog (`#templatePreviewDialog`)

| # | Feature | Evidence |
|---|---|---|
| 59 | Phone-mock preview body | seen |
| 60 | Close | seen |
| 61 | Use this template | seen |

## I. Edit history

| # | Feature | Evidence |
|---|---|---|
| 62 | **Duplicate headings** — `<h2>` "Edit history" plus the mounted region's own `<h2>` | seen |
| 63 | Explainer paragraph | seen |
| 64 | "Resend update notification" (disabled) | seen |
| 65 | Edit list + "edited after send" badge | seen |
| 66 | `#edit-history-meta` status line | seen |

## J. Hidden markup on this page

| # | Feature | Evidence |
|---|---|---|
| 67 | Sign-up sheets panel (`#signup-sheets-panel`, `hidden`) | source |
| 68 | Polls panel (`#polls-panel`, `hidden`) | source |

---

## Verified defects

1. **`Alt+T` is advertised but not implemented.** `data-ui-tooltip="Appearance (Alt+T)"`
   appears on the theme button in all 14 bundles. No keydown handler binds it — every
   `altKey` hit in the bundles is a link-interception guard — and
   `EInviteThemeController.cycle()` is defined but never called. Pressing it from a clean
   header state left `aria-expanded="false"` and the theme unchanged.
2. **Both theme options announce "✓".** The inactive checkmark is hidden with
   `opacity: 0`, which stays in the accessibility tree; there is no `aria-checked` and the
   items are not `role="menuitemradio"`. A screen reader reads "Light ✓" and "Dark ✓" at once.
3. **The account popover has no menu semantics** — no `role`, and no
   `aria-expanded`/`aria-haspopup` on its trigger, unlike the Appearance button beside it,
   which has both. (Escape does close it; an early "does not close" reading was a timing
   artifact, not a bug.)
4. **Two document-level link interceptors** run on every click — one adds
   `ui-page-leaving` with a 115 ms navigation delay, another adds
   `final-route-progress.active`.
5. **Three navigation entry points at ≤390 px**: rail, workspace launcher, drawer.
6. **No Draft filter**, although Draft is a status shown on cards (filter is All / Published / Archive).
7. **Redundant destinations**: three routes to `templates.html` (header "Template Studio",
   quick start "Templates", rail "Templates"); two create-invitation entry points
   ("+ Create invitation", "✦ New invitation").

## Dead-on-this-page controls suppressed by CSS

Kept in markup, removed visually — they still exist in the DOM and are focusable in
some cases: `#logoutBtn`, `#adminBtn`, `#designerBtn`, `#accountName`, and the header
links to `materials.html`, `billing.html`, `account.html`
(`body[data-page="dashboard"]>header>…{display:none}`).

## File map — who owns what

| Area | File |
|---|---|
| Page markup: auth, header, rail, dashboard view, dialogs, event-section panels | `src/html/dashboard.html` |
| Page behaviour: render, create, duplicate, archive, delete, template chooser | `src/js/dashboard.js` |
| Injected shell: theme control, workspace launcher, profile popover, toast, tooltip, ripple, spotlight, route progress | `src/js/final-polish.js` → bundled into `src/js/bundle-dashboard.js` |
| Page styling | `src/css/dashboard.css` → `bundle-dashboard.css` |
| Route asset manifest / byte budget | `docs/page-assets-v15.json`, `BUDGETS` in `src/python/build/build_page_manifests.py` |

## Coverage limitations

- Screenshots could not be read back by the agent that produced this list, so the
  inventory rests on the accessibility tree, rendered text, DOM/computed styles and
  source — **not** on visual judgement. Spacing, hierarchy and colour were not assessed.
- Only the `dashboard` route was scanned. Items 19–27 are shared by every page that loads
  the route bundle's shell layer and were not re-checked on other routes.
- Items marked **source** were read, not exercised.

---

## What happened to the page (2026-10-16)

After this inventory was written, the dashboard page was emptied on purpose so it can be
rebuilt from scratch. `src/html/dashboard.html` went from 13,784 bytes to 2,452
(2452 is the final size including the explanatory comment that replaced the markup).

**Removed:** the app header (brand, breadcrumb, show-rail toggle, drawer toggle,
`#accountName`, `#adminBtn`, `#designerBtn`, `#logoutBtn`, skip link), the whole
`.app-rail` nav, `#loginView` (the entire sign-in / create-account card), `#dashboardView`
(`.dash-head`, `.dash-quickstart`, `#inviteGrid`), `#createDialog`, `#templatePreviewDialog`,
and the `#edit-history-panel` / `#signup-sheets-panel` / `#polls-panel` event sections.

**Kept as boot infrastructure, not design content:** the whole `<head>`
(`core/theme.js`, `backend-mode.js`, the yjs module preloads, favicon, title,
`bundle-dashboard.css`), `<main id="main" tabindex="-1">`, `#toast-stack`
(`EInviteToast.show()` appends into it and would throw without it), and
`<script src="bundle-dashboard.js">`.

**Consequences observed in the browser after the wipe:**

- The page still serves 200, reaches `readyState: complete`, and reports no page errors
  and no console output.
- Because the page no longer provides the mount points the app shell installs against,
  the shell does **not** re-inject here: the rendered body is exactly `MAIN#main`, the
  route `<script>`, and `#toast-stack`. `final-ui-ready`, `EInviteThemeController` and
  `window.einviteToast` are all absent on this page.
- That absence is a property of the page markup, not of the bundle: on `templates.html`,
  which still has its markup, the same bundle installs the shell
  (`final-ui-ready` set, theme button and toast stack present). **Re-adding markup can
  therefore bring parts of the legacy shell back.**
- The route's asset set is unchanged — still 3 scripts and 1 stylesheet — so it still
  consumes the same route-budget weight; only the HTML document itself got smaller.
- Sign-in is gone from this page along with `#loginView`, so the dashboard route can no
  longer authenticate until an auth view is rebuilt.

The removed markup is backed up at `artifacts/dashboard-page-wip/dashboard.html.orig`,
with the pre-wipe `dashboard.js` at `artifacts/dashboard-page-wip/dashboard.js.orig` and
the uncommitted diff of both at `artifacts/dashboard-page-wip/uncommitted.patch`
(`artifacts/` is gitignored).
