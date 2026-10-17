# WCAG 2.2 AA Delta Audit — eInvite Platform

> **Documentation-only pass.** This file changes no source file, no CSS and no bundle. Every
> finding that needs code work is listed in §5 as a named follow-up and is *not* applied here.
>
> Companion to [WCAG-AA-AUDIT.md](WCAG-AA-AUDIT.md), which audits all 16 pages in `src/html/`
> against **WCAG 2.1 AA**. That document stays authoritative for the 2.1 criteria and is not
> superseded; this one covers only what WCAG 2.2 adds or removes.
>
> **Reference:** <https://www.w3.org/TR/WCAG22/> and
> <https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/>.

---

## 1. Scope and method

WCAG 2.2 has been a W3C Recommendation since 5 October 2023, so the "WCAG 2.1 AA" label this
project carries in `docs/a11y/WCAG-AA-AUDIT.md` and in `README.md` is one revision behind.

Same method as the 2.1 audit — **static code evidence, not a dynamic pass**. Each verdict cites
a real `file:line` in the source tree (`src/css/`, `src/js/`, `src/html/`), never a generated
`bundle-*` file. Where a verdict rests on a search rather than a measurement, the search is
quoted so it can be re-run.

### Status legend

- **pass** — criterion met; the evidence cites the rule or handler that meets it.
- **partial** — the criterion is met in part; the evidence names what is missing.
- **fail** — criterion not met.
- **na** — criterion does not apply to this product (per the criterion's own conditional wording).

### What this pass did *not* do

Named up front, because a delta audit that hides its limits is worse than none:

1. **No keyboard traversal was run.** 2.4.11 in particular asks whether a *focused* component is
   hidden by author-created content, which is a rendered behaviour. §3.1 therefore lands on
   `partial` with the unmeasured part named, not on `pass`.
2. **No screen-reader testing.** Same limitation the 2.1 audit records in its §9.
3. **No rendered 16-route sweep.** The target-size verdict in §3.3 is a static-CSS reading. A
   rendered sweep measuring every interactive box would be stronger evidence and is still owed.
4. **No Lighthouse/axe run.** Automated tools are explicitly distrusted for Khmer-specific
   issues by this project (`docs/ROADMAP.md` §2b).

---

## 2. What WCAG 2.2 changes

| Change | Criterion | Level | Relevant to eInvite? |
| --- | --- | --- | --- |
| Added | 2.4.11 Focus Not Obscured (Minimum) | AA | **Yes** — sticky topbar, sticky toolbar, sticky `thead`, 12000-z popovers |
| Added | 2.4.12 Focus Not Obscured (Enhanced) | AAA | Out of scope (AA target) |
| Added | 2.4.13 Focus Appearance | AAA | Out of scope (AA target) |
| Added | 2.5.7 Dragging Movements | AA | **Yes** — canvas move/resize, page reorder, asset drag |
| Added | 2.5.8 Target Size (Minimum) | AA | **Yes** — all 16 pages; one 10px canvas resize handle found |
| Added | 3.2.6 Consistent Help | A | Checked — no help mechanism, so **n/a** |
| Added | 3.3.7 Redundant Entry | A | **Yes** — guest page repeats name/email |
| Added | 3.3.8 Accessible Authentication (Minimum) | AA | **Yes** — sign-in, reset, MFA, passkeys |
| Added | 3.3.9 Accessible Authentication (Enhanced) | AAA | Out of scope (AA target) |
| **Removed** | 4.1.1 Parsing | A | Removed as obsolete. No eInvite work; it can only *raise* conformance, never lower it |

A note on the "3 reworded criteria" framing that circulates in third-party 2.2 summaries: the
official *What's New in WCAG 2.2* page lists the above nine additions and the single removal of
4.1.1. No Level A or AA criterion from 2.1 was weakened in 2.2, so nothing this project's 2.1
audit already marked `pass` becomes a failure by moving the target revision. That claim is
carried from the W3C pages above rather than measured here — flagged as **UNVERIFIED** against
the workspace, since no copy of the spec is vendored.

---

## 3. Delta audit — the six new A/AA criteria

### 3.1 2.4.11 Focus Not Obscured (Minimum) — AA — **partial**

*"When a user interface component receives keyboard focus, the component is not entirely hidden
due to author-created content."*

**What is in place:**

| Mitigation | Evidence |
| --- | --- |
| Global scroll padding reserves space for the sticky chrome when the browser scrolls a focused element into view | `src/css/stabilized.css:2` — `scroll-padding:18px 12px calc(90px + env(safe-area-inset-bottom))` |
| Visible focus indicator on every interactive element | `src/css/modern-ui.css:9` — `button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid …;outline-offset:2px}` |
| Per-component focus ring where the global one would be clipped | `src/css/page-experience.css:16` — `.v22-page-card:focus-visible{outline:3px solid …;outline-offset:2px}` |
| Skip-link becomes a real, focused control at the top of the stacking order | `src/css/accessibility.css:4` — `.skip-link:focus,.skip-link:focus-visible{position:fixed;left:12px;top:12px;z-index:99999}` |

**Sticky / overlay layers that can hide a focused element:**

| Layer | Evidence |
| --- | --- |
| App topbar | `src/css/canvas-plus.css:28` — `body:not(.guest) > header{position:sticky;top:0;z-index:2000}` |
| Second sticky band, 68px down | `src/css/canvas-plus.css:170` — `.toolbar{position:sticky;top:68px;z-index:15}` |
| Admin sticky table head | `src/css/admin-page.css:38` — `thead th{position:sticky;top:var(--app-topbar-h)}` |
| Check-in header | `src/css/checkin.css:2` — `.checkin-header{position:sticky;top:0;z-index:10}` |
| Shell rails | `src/css/app-shell.css:877` (z 50), `:959` (z 40) |
| Editor tool rail | `src/css/editor-pro.css:2` — `.ei-tool-rail{position:sticky;…}` |
| The `•••` popover | `src/css/canvas-plus.css:237` — `z-index:12000` |

**Why `partial`, not `pass`:** the mitigation is a single global `scroll-padding` with no per-layer
compensation. On the editor route two sticky bands stack (header `min-height:64px` at
`canvas-plus.css:28`, toolbar at `top:68px` at `canvas-plus.css:170`), so up to roughly 130px of
chrome can cover the scroll-into-view target, and `scroll-padding` is declared once for the whole
document rather than per scroll container. `scroll-margin` **is** used in the codebase, but only in
two places and neither covers the editor's stacked bands:
`grep -rn "scroll-margin" src/css/*.css | grep -v bundle-` → 2 matches,
`src/css/guest-journey.css:2` (`.guest [data-guest-waypoint]{scroll-margin-top:76px}`, the
guest-facing waypoints) and `src/css/stabilized.css:2` (`.dash{scroll-margin-top:0}`, which zeroes
it). The popover at `z-index:12000`
(`canvas-plus.css:237`) paints above the topbar at `z-index:2000` (`canvas-plus.css:28`), so an
open popover can fully cover a focused control beneath it; that case is only bounded by the
popover's own dismissal, not by any focus-reveal rule.

**Follow-up (not applied):** add a keyboard-traversal measurement to the browser harness that
tabs through each route and asserts no focused element is `elementFromPoint`-covered; then decide
whether per-container `scroll-padding` is needed. Owner file if a fix is chosen:
`src/css/stabilized.css` (the existing declaration) — **no CSS was changed in this pass**.

### 3.2 2.5.7 Dragging Movements — AA — **partial**

*"All functionality that uses a dragging movement for operation can be achieved by a single
pointer without dragging, unless dragging is essential."*

**Drag operations present:** page reorder (`src/css/page-experience.css:14`
`.v22-page-drag-handle`, `:35` `.v22-dock-drag-handle`), canvas element move/resize, and
drag-from-library asset insertion (`src/js/asset-workflow.js`).

**Non-drag alternatives that exist:**

| Function | Single-pointer / keyboard alternative | Evidence |
| --- | --- | --- |
| Move a canvas element | On-screen nudge buttons `↑ ← → ↓` | `src/html/index.html:374`, wired at `src/js/app.js:3343`, implemented `src/js/app.js:3316` |
| Resize a canvas element | `− Size` / `+ Size` buttons, same row | `src/html/index.html:374` |
| Move a selection | Arrow keys (1px, Shift = 10px) | `src/js/editor-command-system.js:111` |
| Resize a selection | `Alt+Arrow` | `src/js/professional-workflow.js:68-71` |
| Reposition an image inside its frame | `Mod+Shift+Arrow` | `src/js/professional-workflow.js:90-93` |
| Reorder a page (to the ends) | Menu items *Move to first page* / *Move to last page*, reached from the card's action buttons, with a full Arrow/Home/End/Escape keyboard model | `src/js/page-experience.js:387`, `:339`; buttons styled `src/css/page-experience.css:14` |

**Why `partial`, not `pass`:** the page-reorder alternative only reaches the **first and last**
positions. There is no "move one step earlier / later" control — `grep -n "Move " src/js/page-experience.js`
returns only `Move to first page` and `Move to last page` (`:387`). Moving a page to an arbitrary
index therefore still requires a drag, and the two keyboard paths found are Transform nudges, not
page reorder. Dragging is not *essential* to arbitrary reordering — a step-wise command would
satisfy the criterion.

**Follow-up (not applied):** add `Move earlier` / `Move later` entries to the page context menu
in `src/js/page-experience.js:387`, reusing the existing `reorderPage` helper already called
at `:404`. That is a `src/js/` change and would require `python3 build.py all`.

### 3.3 2.5.8 Target Size (Minimum) — AA — **partial**

*"The size of the target for pointer inputs is at least 24 × 24 CSS pixels"*, with exceptions for
spacing, equivalent, inline and essential targets.

| Floor enforced | Evidence |
| --- | --- |
| Buttons, links-as-buttons, checkboxes, radios, selects ≥ 44px tall | `src/css/accessibility.css:2` — `:where(button,.button-link,…){min-height:44px}` |
| Icon buttons and labelled buttons ≥ 44 × 44 | `src/css/accessibility.css:2` — `:where(.icon-button,button[aria-label]){min-width:44px;min-height:44px}` |
| Count of `44px` declarations across the hand-written CSS | 73 (excluding generated `bundle-*` files) |

**Small interactive targets that stay above the floor:**

| Component | Size | Evidence |
| --- | --- | --- |
| Element-library category chips | 28px tall | `src/css/final-polish.css:2` — `.final-library-cats button{min-height:28px!important}` |
| Page-card action buttons | 30 × 30 | `src/css/page-experience.css:2` — `.v22-page-actions button{min-width:30px;min-height:30px}` |
| Template-card favourite/preview buttons | 30 × 30 | `src/css/dashboard-page.css:5` — `.template-choice-actions button{width:30px;height:30px}` |
| Agent attachment chips | 32 × 32 | `src/css/ai-creative-agent.css:1` — `.ei-agent-attachment-chip button{min-width:32px;min-height:32px}` |
| Project ⋯ / material close | 34 × 34 | `src/css/final-polish.css:2` |
| Template dialog controls | 36px tall | `src/css/adaptive-templates.css:2` — `.v25-template-dialog button,select{min-height:36px}` |

Note the interaction that makes those values win: `accessibility.css:2` uses `:where(...)`, which
contributes **zero specificity**, so any later `min-height` on a button overrides the 44px floor.
The 44px floor is a default, not a guarantee.

**One interactive target is below the floor.** Sweeping every `min-height` in the hand-written CSS
(`grep -rhoE "min-height: *[0-9]+px" $(ls src/css/*.css | grep -v bundle-) | sort -u`) returns
values down to 2px. Almost all of them are not targets — status-text placeholders sized to avoid
layout shift (`.account-card .status`, `.v13-status`, `.ei-ai-target-meta`, `.canvas-auth-status`),
a progress `i` bar, a 4px decorative dot in `.ui-app-launcher-button i`, and so on. **One is a real
pointer target:**

| Element | Size | Evidence |
| --- | --- | --- |
| Canvas object resize handle | **10 × 10** | `src/css/typography-system.css:2` — `.object>.resize-handle,.object>i{width:10px!important;height:10px!important;min-width:10px!important;min-height:10px!important}` |

**Why the verdict is `partial` rather than `fail` or an unqualified `pass`:** an undersized target
is permitted when the *Equivalent* exception holds — the same function is achievable through a
different control on the same page that does meet the criterion. The same route does ship 44px
`− Size` / `+ Size` buttons (`src/html/index.html:374`) and `Alt+Arrow` resize
(`src/js/professional-workflow.js:68-71`), so the exception plausibly applies. But that is an
argument, not a measurement: this pass did not render the editor and confirm the buttons are
reachable in the same context as the handle. The *Spacing* exception is likewise unmeasured. So the
honest verdict is `partial`, pending either a rendered check of the equivalence or a bump of the
handle.

**Follow-up (not applied):** raise the resize handle in `src/css/typography-system.css:2` to at
least 24 × 24 while keeping the visual affordance small (a larger hit area with a smaller painted
grip), or record the measured equivalent-control evidence that makes the exception hold.

### 3.4 3.2.6 Consistent Help — A — **na**

*"If a web page contains any of the following help mechanisms, and those mechanisms are repeated
on multiple web pages within a set of web pages, they occur in the same relative order…"*

The criterion is explicitly conditional. Two searches establish the condition is not met:

1. **No help/support/contact affordance in page chrome.** `grep -rniE 'href="[^"]*(help|support|contact|docs|faq|guide)[^"]*"' src/html/*.html`
   returns exactly one hit — `src/html/privacy.html:50`, a link to the analytics Event Model and
   Privacy documents *inside the privacy notice body*. That is a citation in one page's prose,
   not a help mechanism repeated across pages.
2. **The one help-like surface exists on a single route.** The keyboard-shortcuts help button
   (`.ui-shortcut-help`, styled at `src/css/modern-ui.css:9`) is created only by
   `src/js/editor-command-system.js:165`, and appears in exactly one built bundle:
   `bundle-index.js` has 1 occurrence; the other 15 route bundles have 0
   (`for b in index dashboard admin account …; do grep -c 'ui-shortcut-help' src/js/bundle-$b.js; done`).

Because no help mechanism is repeated across pages, there is no order for the criterion to
constrain. Verdict `na`, with the search quoted so it can be re-run if a help affordance is ever
added to the shared header — at which point this becomes a real requirement on all 16 routes.

### 3.5 3.3.7 Redundant Entry — A — **partial**

*"Information previously entered by or provided to the user that is required to be entered again
in the same process is either auto-populated or available for the user to select."*

**Where the same information is asked for more than once:** the guest-facing page renders up to
three independent forms, and **two of them ask for the same two fields**:

| Form | Fields | Evidence |
| --- | --- | --- |
| Sign-up-sheet claim | `name`, `email`, `quantity` | `src/js/signup-sheets.js:130-132` |
| Poll vote | `name`, `email` | `src/js/polls.js:109-110` |

A guest who claims a sign-up slot and then votes in a poll types their name and email twice in one
visit.

**The auto-population half is absent here:** `grep -n "autocomplete" src/js/polls.js src/js/signup-sheets.js src/js/guest-journey.js`
returns **no matches**. The project does use `autocomplete` where it matters most — sign-in
(`src/html/dashboard.html:46-48`), password reset (`src/html/reset.html:20,29,30`), account
security (`src/html/account.html:32-33`), check-in (`src/html/checkin.html:12`) — but not on the
guest-facing repeated fields.

**Why `partial` rather than `fail`:** whether the two widgets are "the same process" under the
criterion's definition is genuinely arguable — they are separate guest activities on one page, not
sequential steps of one transaction. The weaker but indisputable reading is that the repeated
fields carry no `autocomplete`, so even the browser's own re-offer is unavailable, which is the
cheapest available mitigation and is simply missing.

**Follow-up (not applied):** add `autocomplete="name"` and `autocomplete="email"` to
`src/js/signup-sheets.js:130-131` and `src/js/polls.js:109-110`, and consider prefilling the
second form from the first submission. Files: `src/js/signup-sheets.js`, `src/js/polls.js`
(both feed `bundle-public.js`; regenerate with `python3 build.py all`).

### 3.6 3.3.8 Accessible Authentication (Minimum) — AA — **pass**

*"A cognitive function test (such as remembering a password or solving a puzzle) is not required
for any step in an authentication process unless that step provides… a mechanism to assist… or a
mechanism to recognize the user."*

| Requirement | Finding | Evidence |
| --- | --- | --- |
| No puzzle / CAPTCHA | **Absent** — `grep -rni "captcha\|recaptcha\|hcaptcha\|turnstile" src/html/*.html src/js/*.js src/python/server.py` → no matches | — |
| No blocked paste into credential fields | The only two `paste` handlers in the app explicitly bail out on `INPUT`/`TEXTAREA` — `if(['INPUT','TEXTAREA'].includes(document.activeElement?.tagName))return` — so paste into a password field is untouched | `src/js/canvas-plus.js:135`, `src/js/rich-text-editing.js:37` |
| Password managers / autofill supported | `autocomplete="email"`, `"current-password"`, `"new-password"` on the sign-in and registration fields | `src/html/dashboard.html:46-48` |
| Reset flow supports autofill | `autocomplete="email"`, `"new-password"` ×2 | `src/html/reset.html:20,29,30` |
| MFA code field is autofill-addressable | `autocomplete="one-time-code"` | `src/html/account.html:33` |
| A non-cognitive alternative actually ships | Passkeys via WebAuthn — `navigator.credentials.create({publicKey})` against `/api/account/passkeys/register/options` | `src/js/account-security.js:24` |
| Account password change is autofill-aware | `"current-password"`, `"new-password"` ×2 | `src/html/account.html:32` |

**Named gap (does not overturn the `pass`):** `src/html/index.html:394` — the invitation access
password field `#accessPassword` has `minlength="8"` but **no `autocomplete` attribute**. It gates
a published invitation rather than authenticating a user account, so it is outside the criterion's
authentication process; it is listed here because it is the one credential field in the product
without autofill metadata. Follow-up file: `src/html/index.html`.

---

## 4. 2.5.5 vs 2.5.8 — a correction to the existing audit's wording

`docs/a11y/WCAG-AA-AUDIT.md` and the `ux-8` mobile pass both describe the project's target-size
work as satisfying **2.5.5 Target Size (Enhanced), 44 × 44**, which is a **Level AAA** criterion.
The Level AA requirement in both 2.1 and 2.2 is **2.5.8 Target Size (Minimum), 24 × 24**.

This is not a defect — 44 × 44 exceeds 24 × 24, so a project that enforces 44 × 44 satisfies
2.5.8 too. It is a *labelling* correction: the AA conformance claim should cite 2.5.8, and 2.5.5
belongs in an AAA claim, not an AA one. Recorded here so the AA claim in the audit trail names the
criterion that was actually audited. The enforcing rules are at `src/css/accessibility.css:2`.

---

## 5. Findings requiring a code change

Listed, per this pass's scope, and **none applied**:

| # | Criterion | Verdict | File to change | Change |
| --- | --- | --- | --- | --- |
| 1 | 2.4.11 Focus Not Obscured (Minimum) | partial | `src/css/stabilized.css` (+ a new harness measurement) | Decide whether per-scroll-container `scroll-padding` is needed for the editor's two stacked sticky bands; measure before changing |
| 2 | 2.5.7 Dragging Movements | partial | `src/js/page-experience.js:387` | Add *Move earlier* / *Move later* menu entries reusing the existing `reorderPage` helper |
| 3 | 3.3.7 Redundant Entry | partial | `src/js/signup-sheets.js:130-131`, `src/js/polls.js:109-110` | Add `autocomplete="name"` / `autocomplete="email"`; consider cross-form prefill |
| 4 | 3.3.8 Accessible Authentication (Minimum) | pass (gap noted) | `src/html/index.html:394` | Add an `autocomplete` value to `#accessPassword` |
| 5 | 2.5.8 Target Size (Minimum) | partial | `src/css/typography-system.css:2` | Canvas resize handle is 10 × 10; raise the hit area to ≥ 24 × 24, or measure and record the Equivalent-exception evidence |
| 6 | 2.5.5 vs 2.5.8 labelling | — | `docs/a11y/WCAG-AA-AUDIT.md` | Restate the AA target-size claim against 2.5.8 |

Each of 1–3 would need `python3 build.py all` afterwards for 2 and 3, since both touch files that
feed route bundles. Nothing in this table has been started.

---

## 6. Honest caveats

1. **Static, not rendered.** §3.1 and §3.3 rest on stylesheet reads. Neither a keyboard traversal
   (2.4.11) nor a rendered target-size sweep (2.5.8) has been run; both are named as owed above.
2. **The 2.2 spec is not vendored in this repository.** The criterion texts and levels in §2 are
   carried from <https://www.w3.org/TR/WCAG22/> rather than verified against a local copy —
   **UNVERIFIED** against the workspace.
3. **The "3 reworded criteria" framing is not reproduced.** The W3C pages list nine additions and
   the removal of 4.1.1. No 2.1 A/AA criterion was weakened. Stated in §2 with the same caveat.
4. **Khmer is out of scope for this delta.** `docs/i18n/KHMER-TYPOGRAPHY.md` and §6 of the 2.1
   audit remain the authority; several 2.2 criteria would interact with Khmer line-height and
   clipping, and no Khmer-specific measurement was added here.
5. **No source file was modified by this pass.** Confirmed by the pass report
   ([next-pass-2026-10-15.md](../reviews/next-pass-2026-10-15.md)), which records that the only
   files touched were this document, the inventory and a new test.

---

## 7. Change history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-15 | Created | Delta audit against WCAG 2.2 AA; the 2.1 audit at [WCAG-AA-AUDIT.md](WCAG-AA-AUDIT.md) predates the 2.2 Recommendation and the project's AA claim needed the four new AA / two new A criteria checked. Documentation-only; no source change. |

---

*Cross-references: [WCAG-AA-AUDIT.md](WCAG-AA-AUDIT.md), [RESPONSIVE-AUDIT.md](RESPONSIVE-AUDIT.md),
[KHMER-TYPOGRAPHY.md](../i18n/KHMER-TYPOGRAPHY.md), `src/css/accessibility.css`, `src/css/modern-ui.css`,
`src/css/stabilized.css`, `src/css/canvas-plus.css`, `src/js/page-experience.js`,
`src/js/signup-sheets.js`, `src/js/polls.js`, `src/js/account-security.js`.*
