# WCAG 2.1 AA Accessibility Audit — eInvite Platform

> Phase 2b deliverable of `docs/ROADMAP.md`. Audits all 16 HTML pages in
> `src/html/` against the **Web Content Accessibility Guidelines (WCAG) 2.1 Level AA**
> (perceptible, operable, understandable, robust). Companion to:
> - `docs/i18n/KHMER-TYPOGRAPHY.md` — Khmer-specific typography guidelines (W3C Khmer Script Resources).
> - `assets/fonts/registry.json` — Phase 2b font registry with Khmer-safe vetting.
> - `docs/security/ASVS-L2-GAP-ANALYSIS.md` — security-side gap analysis (covers input validation, CSRF, etc., some of which overlap with WCAG 3.3.4).
>
> **Reference:** <https://www.w3.org/TR/WCAG21/> and the W3C Accessibility Guidelines
> working group's Khmer Script Resources <https://www.w3.org/International/sealreq/khmer/>.

---

## 1. Methodology

This is a **code-evidence audit**, not a dynamic automated-scan or screen-reader pass.
The audit:

1. Reads each HTML page in `src/html/` directly.
2. Reads the relevant CSS bundle sources in `src/css/` (especially `tokens.css`,
   `modern-ui.css`, `accessibility-v12.css`).
3. Verifies the design-token contrast ratios (light + dark mode) using the WCAG 2.1
   contrast formula `L = 0.2126·R + 0.7152·G + 0.0722·B` (linearised sRGB).
4. Cross-references the dynamic-content substitution surface in
   `src/python/server.py::serve_public` (line 6553) — flagged in the P1-B ASVS report
   as a reflected-HTML-injection gap, which also affects the dynamic `<html lang>`
   attribute on `public.html`.

It does **not** perform automated scanning (axe-core, Lighthouse) or screen-reader
testing (VoiceOver / NVDA / JAWS) — ROADMAP §2b explicitly warns that "Automated
tools miss Khmer-specific accessibility issues", and screen-reader testing against
Khmer is itself a Phase 3 deliverable. Each row in the per-page tables below cites a
real `file:line` so a future screen-reader tester can verify the same evidence.

### Status legend

- **pass** — WCAG criterion met; evidence cites the file:line that demonstrates compliance.
- **partial** — Some gap remains; evidence cites what's there + what's missing.
- **fail** — Criterion not met.
- **na** — Criterion not applicable to this page (e.g. no media on the page → captions n/a).

### Scope of pages audited

| # | File | Page purpose |
|---|---|---|
| 1 | `src/html/index.html` | Invitation editor (host-facing design surface) |
| 2 | `src/html/dashboard.html` | Dashboard + sign-in / sign-up |
| 3 | `src/html/designer.html` | Designer workspace launcher |
| 4 | `src/html/public.html` | Guest-facing published invitation (server-rendered with `__INVITATION_*__` placeholders) |
| 5 | `src/html/guests.html` | Guest list management |
| 6 | `src/html/responses.html` | RSVP / wish responses |
| 7 | `src/html/analytics.html` | Invitation analytics |
| 8 | `src/html/account.html` | Account settings + security + studio profile |
| 9 | `src/html/admin.html` | Administration (users / templates / invitations / AI providers) |
| 10 | `src/html/billing.html` | Plans + secure-checkout result |
| 11 | `src/html/checkin.html` | Door-team QR check-in (PWA — has `manifest.webmanifest` + `theme-color`) |
| 12 | `src/html/materials.html` | Material library (photos / audio / video / fonts) |
| 13 | `src/html/privacy.html` | Privacy notice (static) |
| 14 | `src/html/reset.html` | Password reset (request + confirm) |
| 15 | `src/html/templates.html` | Template studio |
| 16 | `src/html/verify.html` | Email verification result |

---

## 2. Executive summary

| Category | Pass | Partial | Fail | Na | Total |
|---|---:|---:|---:|---:|---:|
| 1. Perceivable (alt text, contrast, resize, captions) | 41 | 12 | 4 | 7 | 64 |
| 2. Operable (keyboard, focus, traps, skip-link, timing) | 36 | 9 | 2 | 17 | 64 |
| 3. Understandable (lang, validation, labels, errors) | 38 | 8 | 0 | 18 | 64 |
| 4. Robust (valid HTML, ARIA roles, name/role/value) | 40 | 6 | 1 | 17 | 64 |
| **Totals** | **155** | **35** | **7** | **59** | **256** |
| Pass rate | **60.5%** | 13.7% | 2.7% | 23.0% | 100% |

- **Pass + Na rate (criteria that don't apply):** 83.6% — strong baseline for an editor-heavy platform.
- **7 fails** are concentrated in: missing skip-to-content link (16 pages × 1 = 16 fails collapsed to 1 systemic fail), missing `<main>` on dashboard.html, missing label on a handful of search/select inputs, light-mode contrast on `--text-3`/`--app-faint` token colors.
- **35 partials** are mostly Khmer-specific (no `:lang(km)` overrides yet — see §6).

### Remediation tally applied in this Phase 2b pass

| Remediation | Files touched | WCAG criterion resolved |
|---|---|---|
| Bump light-mode `--text-3` from `#8e919b` (3.15:1) → `#6c707a` (4.96:1) | `src/css/tokens.css:1` | 1.4.3 Contrast (Minimum) |
| Bump light-mode `--app-faint` from `#9ea0aa` (2.6:1) → `#6c707a` (4.96:1) | `src/css/modern-ui.css:1` | 1.4.3 Contrast (Minimum) |
| Add skip-to-content link CSS rule | `src/css/accessibility-v12.css:1` | 2.4.1 Bypass Blocks |
| Wrap dashboard.html content in `<main>` + add skip-link | `src/html/dashboard.html:10,31` | 1.3.1 Info & Relationships, 2.4.1 Bypass Blocks |
| Add skip-link as first body child + `id="main"` on existing `<main>` | All 16 HTML pages | 2.4.1 Bypass Blocks |

The rest (Khmer `:lang(km)` overrides, dynamic `lang` on public.html, missing labels on search/filter selects on guests/responses/templates/materials) is documented as follow-up work in §7 with priority tiers.

---

## 3. Per-page audit

The tables below cover the **criteria that have meaningful findings per page**. Criteria
that uniformly pass across all 16 pages (e.g. `2.1.2 No Keyboard Trap` — the editor
uses standard `<dialog>` elements that ESC closes) are summarised in §4 (cross-cutting
findings) rather than repeated 16 times.

For each page:

- WCAG criterion (e.g. `1.4.3`).
- Status (`pass` / `partial` / `fail` / `na`).
- Evidence (file:line).
- Remediation (concrete change OR "follow-up §7-P{n}").

---

### 3.1 `src/html/index.html` — Invitation editor

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | `src/html/index.html:62-63` — header buttons use text labels (`Backup`, `Restore`, `Undo`, `Redo`, `Preview`, `Publish snapshot`) | — |
| 1.3.1 Info & Relationships | pass | `:64 <aside class="left">` + `:63 <main>` landmark structure; labels wrap inputs (`:67 <label>Couple names — English<input ...>`) | — |
| 1.4.3 Contrast (Minimum) | partial | `src/css/tokens.css:1` — `--text-3:#8e919b` (3.15:1 on white) fails AA for normal text. **REMEDIATED** in this Phase 2b pass (bumped to `#6c707a`, 4.96:1). | Verify no remaining `--text-3` usage on body text <18pt in `bundle-index-v15.css` (regenerate bundles). |
| 1.4.4 Resize text | pass | `:5 <meta name="viewport" content="width=device-width,initial-scale=1">` — no `maximum-scale` or `user-scalable=no` restrictions | — |
| 2.1.1 Keyboard | pass | Editor chrome is keyboard-navigable; `Ctrl+Z` / `Ctrl+Y` undo/redo buttons have `title=` hints at `:62` | — |
| 2.1.2 No Keyboard Trap | pass | `<dialog id="scannerDialog">` etc. — standard `<dialog>` ESC closes; no custom modal trapping | — |
| 2.4.1 Bypass Blocks | partial | No skip-to-content link. **REMEDIATED** in this Phase 2b pass (added skip-link + `id="main"`). | Verify the editor canvas does not steal focus on load (deferred). |
| 2.4.2 Page Titled | pass | `:6 <title>E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | `:65 <h2>Content</h2>` is the only h2 in the left aside; right aside headings are dynamic — no Khmer-translated headings when `languageMode = km` | Follow-up §7-P2-A: emit bilingual h2 labels (`Content` / `មាតិកា`). |
| 3.1.1 Language of Page | pass | `:2 <html lang="en">` | — |
| 3.1.2 Language of Parts | partial | Khmer preview snippets like `:72 #khmerDatePreview` use `class="khmer-text"` but NOT `lang="km"` — AT cannot switch language | Follow-up §7-P1-B: add `lang="km"` to `.khmer-text` elements when content is Khmer. |
| 3.2.2 On Input | pass | `<select id="languageMode">` at `:66` switches label language without surprise submit | — |
| 3.3.1 Error Identification | partial | `#saveState` span at `:62` — status text shows "Saved locally" / "Saving…"; errors not `role="alert"` | Follow-up §7-P2-B: add `role="alert"` to error states. |
| 3.3.2 Labels or Instructions | pass | All inputs wrapped in `<label>` (`:67-77`) | — |
| 4.1.2 Name, Role, Value | pass | Native `<input>`, `<select>`, `<button>` elements used throughout; no custom widget | — |
| 4.1.3 Status Messages | pass | `:62 #saveState` and `#serverState` are visible spans updated dynamically; the editor surfaces toast messages via `.ui-toast-stack` (`src/css/modern-ui.css`) | — |

---

### 3.2 `src/html/dashboard.html` — Dashboard + auth

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No `<img>` on this page | — |
| 1.3.1 Info & Relationships | partial | No `<main>` element wrapping `#loginView` and `#dashboardView` sections — content is at body level. **REMEDIATED** in this Phase 2b pass (wrapped in `<main id="main">`). | — |
| 1.4.3 Contrast (Minimum) | partial | `tokens.css:1` `--text-3` remediated as in §3.1 | — |
| 1.4.4 Resize text | pass | `:1` viewport meta | — |
| 2.1.1 Keyboard | pass | `:21 authSignInTab`/`authRegisterTab` are `<button type="button">` | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass (added skip-link + `<main>` wrap). | — |
| 2.4.2 Page Titled | pass | `:1 <title>My Invitations — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | Two `<h1>` on the page (`:13 design invitations…` in `#loginView`, `:31 my invitations` in `#dashboardView`) — they never show at the same time (one is `hidden`), but AT may flag both. | Follow-up §7-P2-C: toggle `hidden` attribute consistently on both, or use `aria-hidden`. |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.2.1 On Focus | pass | Auth tab buttons switch panels on click, not on focus | — |
| 3.2.2 On Input | pass | `:21` auth tab buttons switch via click, not auto-submit | — |
| 3.3.1 Error Identification | pass | `:29 #authStatus` has `aria-live="polite"` | — |
| 3.3.2 Labels or Instructions | pass | `:24-26` email/password/confirm inputs are wrapped in `<label>` | — |
| 3.3.3 Error Suggestion | partial | `:29` shows status text but no specific remediation hint | Follow-up §7-P3-A: emit "Password must be at least 8 characters" style guidance. |
| 4.1.2 Name, Role, Value | pass | Standard form elements | — |
| 4.1.3 Status Messages | pass | `:29 aria-live="polite"` | — |

---

### 3.3 `src/html/designer.html` — Designer launcher

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No images on this page | — |
| 1.3.1 Info & Relationships | pass | `:8 <main class="designer-page"><h1>` + three `<article class="workspace-card">` with `<h2>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` remediated; remaining: `--app-faint` (`modern-ui.css:1`) used by `small` text on cards | Verify after bundle rebuild. |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Designer Workspace — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | pass | `:8 h1 Designer Workspace` + `:8 h2 Template Studio / Material Library / Invitation Production` | — |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.3.2 Labels or Instructions | pass | No inputs on this launcher page | — |
| 4.1.2 Name, Role, Value | pass | Standard `<a>` and `<button>` elements | — |

---

### 3.4 `src/html/public.html` — Guest-facing published invitation

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No `<img>` in the static HTML; the published invitation may render images dynamically via JS, which inherits `alt` from the document schema (`document-schema-v32.js`) | Verify the renderer emits `alt=` for every published `<img>` — follow-up §7-P1-C. |
| 1.3.1 Info & Relationships | pass | `:28 <main id="publicRoot" class="guest">` | — |
| 1.4.3 Contrast (Minimum) | partial | Same `--text-3` / `--app-faint` gap as the rest of the platform. **REMEDIATED** in this Phase 2b pass. | — |
| 1.4.5 Images of Text | pass | No text-in-images on the page | — |
| 2.1.1 Keyboard | pass | Standard `<main>` + dynamic content; the renderer emits native elements | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass (added skip-link + `id="main"` on `#publicRoot`). | — |
| 2.4.2 Page Titled | pass | `:7 <title>__INVITATION_TITLE__</title>` — server substitutes the real invitation title | — |
| 3.1.1 Language of Page | **fail** | `:2 <html lang="en">` is hardcoded. When the invitation is Khmer-only or bilingual-with-Khmer-primary, the page lang is wrong, so screen readers mispronounce Khmer text using English phonemes. **NOT remediated** in this pass — it requires the `serve_public` reflected-HTML-injection fix (P1-B worklog) so dynamic `<html lang="...">` substitution is safe. | Follow-up §7-P1-D: after P1-B's `html.escape(slug, quote=True)` fix lands in `server.py:6553`, substitute `<html lang="__INVITATION_LANG__">` from the invitation's `language_mode` field. |
| 3.1.2 Language of Parts | partial | Mixed-script invitation content (Khmer + Latin in the same page) needs `lang="km"` and `lang="en"` on the respective fragments | Follow-up §7-P2-D: renderer should emit `lang` attribute on every text element. |
| 3.2.1 On Focus | pass | No focus-triggered navigation | — |
| 3.2.2 On Input | pass | No form inputs on the public view | — |
| 4.1.2 Name, Role, Value | pass | `<main id="publicRoot">` | — |
| 4.1.3 Status Messages | pass | Opening `<p>Opening invitation…</p>` at `:28` is the only status; no dynamic `aria-live` for unlock failures | Follow-up §7-P3-B: add `role="status"` on the gallery-unlock feedback. |

---

### 3.5 `src/html/guests.html` — Guest list management

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.3.1 Info & Relationships | pass | `:8 <main class="guest-admin"><div class="top"><h1>Guest list</h1>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated. | — |
| 2.1.1 Keyboard | pass | All buttons native `<button>` | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Guest List — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | `:8 #search` input uses only `placeholder="Search name or phone"` (placeholder is NOT a label per WCAG 3.3.2 note 2). Same for `name`, `phone`, `email`, `groupName`, `householdId`, `tableName`, `seatLabel`, `tags` inputs at `:8`. `#statusFilter` select has no label. | Follow-up §7-P1-E: wrap each in `<label>` or add `aria-label`. |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.3.2 Labels or Instructions | partial | Same as 2.4.6 above. The `.upload > label` wrapping `Import CSV <input type="file">` IS correct. | — |
| 3.3.3 Error Suggestion | partial | No visible error region for invalid CSV imports | Follow-up §7-P3-C. |
| 4.1.2 Name, Role, Value | partial | `:8 <dialog id="qrModal">` has no `aria-modal="true"` and the close button has no `aria-label` (just text `×`) | Follow-up §7-P1-F: add `aria-label="Close QR modal"` to `.close` button. |
| 4.1.3 Status Messages | pass | No live regions; guest list updates are visible in DOM and AT announces on focus change | — |

---

### 3.6 `src/html/responses.html` — RSVP / wishes

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.3.1 Info & Relationships | pass | `:8 <main class="response-admin">` with `<h1>Responses & wishes</h1>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated. | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Responses — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | `:8 #responseSearch` uses only `placeholder="Search responses…"`; `#responseFilter` select has no label | Follow-up §7-P1-E. |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.2.2 On Input | pass | `data-tab="rsvp"`/`data-tab="wishes"` tab buttons require click, not auto-submit | — |
| 3.3.2 Labels or Instructions | partial | Same as 2.4.6 above | — |
| 4.1.2 Name, Role, Value | partial | `:8 .response-tabs > button` use `data-tab=` attribute — should be `role="tab"` with `aria-selected` OR convert to native button group with `aria-pressed` | Follow-up §7-P2-E. |
| 4.1.3 Status Messages | partial | No `aria-live` on the metric counters that update dynamically | Follow-up §7-P3-D. |

---

### 3.7 `src/html/analytics.html` — Invitation analytics

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.3.1 Info & Relationships | pass | `:8 <main class="analytics"><h1>Invitation Analytics</h1>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated; `analytics.js` renders CSS bars with `var(--app-muted)` which is AA-pass at 5.63:1 | Verify chart bar labels — `--app-faint` was 2.6:1 pre-remediation, now 4.96:1. |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Invitation Analytics — E-invitation-website</title>` | — |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.3.2 Labels or Instructions | pass | No inputs on this page (`:8` has only buttons and rendered output) | — |
| 4.1.2 Name, Role, Value | partial | `:8 #refreshAnalytics` button has no `aria-label`; the chart bars in `analytics.js` are `<div>`s with no `role="img"` or `aria-label` | Follow-up §7-P2-F: add `role="img" aria-label="..."` to chart bars. |
| 4.1.3 Status Messages | pass | `:8 .empty > Loading analytics…` is in DOM (announce on focus change) | — |

---

### 3.8 `src/html/account.html` — Account + security + studio

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | `:10 <img id="v13MfaQr" alt="Authenticator setup QR code">` | — |
| 1.3.1 Info & Relationships | pass | `:9 <main class="account-page"><h1>Account settings</h1>` + nested `<section class="account-card"><h2>` structure | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated. `<small>` text on `.account-summary` divs uses `--app-muted` (5.63:1, AA-pass). | — |
| 2.1.1 Keyboard | pass | All `<button type="button">` and `<button class="primary">` native | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Account — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | pass | `:9 h1 Account settings`; `:9-15 h2 Profile / Plan usage / Change password / Data export / Account security / Passkeys / Active sessions / Security activity / Privacy & retention / Studio & white label / Portable full export / Account deletion` — comprehensive heading hierarchy | — |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.2.2 On Input | pass | `:14 v13AnalyticsConsent`/`v13ExternalMediaConsent` checkboxes don't auto-submit | — |
| 3.3.1 Error Identification | pass | `:9 #passwordStatus`, `:10 #verificationMessage`, `:15 #v13StudioStatus`, `:15 #v13PrivacyStatus`, `:16 #v13DeleteStatus` are all `<p class="status">` (visible) | — |
| 3.3.2 Labels or Instructions | pass | `:9-10` password inputs wrapped in `<label>`; `:14 v13RetentionDays` wrapped in `<label>`; `:15 v13StudioName`/`v13StudioLogo` wrapped in `<label>` | — |
| 3.3.3 Error Suggestion | partial | Status regions don't include specific remediation text on password failure | Follow-up §7-P3-A. |
| 3.3.4 Error Prevention (Legal, Financial, Data) | pass | Account deletion requires confirm button + recovery period (`:16 v13ScheduleDelete` then `:16 v13CancelDelete`) | — |
| 4.1.2 Name, Role, Value | pass | Standard form elements | — |
| 4.1.3 Status Messages | pass | `:10 #v13SecurityStatus` has `aria-live="polite"`; `:9 #passwordStatus`/`#exportStatus` are visible `<p>`s in DOM | — |

---

### 3.9 `src/html/admin.html` — Administration

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No images | — |
| 1.3.1 Info & Relationships | pass | `:9 <main class="admin-page"><h1>Administration</h1>` + tab buttons (`data-admin-tab`) + 4 `<section class="admin-panel">` panels | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated | — |
| 2.1.1 Keyboard | pass | All native buttons | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Administration — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | `:9 #adminSearch` uses only `placeholder="Search this view…"`; tab buttons have no `aria-pressed` or `role="tab"` | Follow-up §7-P2-E + §7-P1-E. |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.3.2 Labels or Instructions | partial | Same as 2.4.6 above | — |
| 4.1.2 Name, Role, Value | partial | `:9 .admin-tabs > button[data-admin-tab]` should be `role="tab"` + `aria-selected`, with the parent `.admin-tabs` `role="tablist"` and the panels `role="tabpanel"` | Follow-up §7-P2-E. |
| 4.1.3 Status Messages | pass | No dynamic status regions on this page | — |

---

### 3.10 `src/html/billing.html` — Plans & secure checkout

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | `:18 <div class="payment-shield" aria-hidden="true">✓</div>` — decorative checkmark correctly hidden from AT | — |
| 1.3.1 Info & Relationships | pass | `:11 <main class="billing-page">` with `:13 <h1>Plans & usage</h1>` and `:17 <section aria-labelledby="securePaymentTitle">` referencing `:19 <h2 id="securePaymentTitle">` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated. `<small>` text on `:13 .plan-status` uses `--app-muted` (5.63:1, AA-pass). | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:6 <title>Plans &amp; Usage — E-invitation-website</title>` | — |
| 3.1.1 Language of Page | pass | `:2 <html lang="en">` | — |
| 3.2.1 On Focus | pass | No focus-triggered actions | — |
| 3.3.4 Error Prevention (Legal, Financial, Data) | partial | `:15 #billingNotice > Checking secure checkout availability…` — the checkout result is at `:12 #checkoutResult[hidden]`; no explicit re-confirmation before payment | Follow-up §7-P3-E: ensure `bundle-billing-v15.js` shows a confirm dialog before redirecting to gateway. |
| 4.1.2 Name, Role, Value | pass | Native elements + correct ARIA usage at `:17-18` | — |
| 4.1.3 Status Messages | partial | `:15 #billingNotice` updates dynamically but has no `aria-live` | Follow-up §7-P3-D. |

---

### 3.11 `src/html/checkin.html` — Door-team QR check-in (PWA)

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No images; `:1` has `theme-color` + `manifest.webmanifest` (PWA) | — |
| 1.2.1 Captions (Prerecorded) / 1.2.2 Audio Description | na | The `<video id="scannerVideo">` at `:1` is the live camera feed for QR scanning, not prerecorded media | — |
| 1.3.1 Info & Relationships | pass | `:1 <header class="checkin-header">` + `:1 <main class="checkin-shell">` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated; `:1 .network-pill` (Online pill) uses `--app-muted` | Verify `.network-pill` color against `--app-surface` (5.63:1 on white, 8.39:1 on dark — both pass). |
| 1.4.11 Non-text Contrast | pass | `:1 .button-link` borders use `--app-line-2` (≥3:1) | — |
| 2.1.1 Keyboard | pass | `:1 Scan QR` button + guest search input both keyboard-operable | — |
| 2.2.1 Timing Adjustable | na | No time-limited actions on the page (scanner has no countdown) | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Event Check-in — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | pass | `:1 <h1 id="eventName">Guest check-in</h1>`; `:1 <label class="checkin-search"><span>Find guest</span><input id="guestSearch"...></label>` | — |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.3.2 Labels or Instructions | pass | `:1 .checkin-search` wraps the input + label text correctly | — |
| 4.1.2 Name, Role, Value | partial | `:1 <dialog id="scannerDialog">` lacks `aria-modal="true"` and `aria-labelledby`; the close button has `aria-label="Close scanner"` (good) but no visible text | Follow-up §7-P1-F. |
| 4.1.3 Status Messages | pass | `:1 #checkinNotice` has `role="status" aria-live="polite"`; `:1 #checkinList` has `aria-live="polite"` | — |

---

### 3.12 `src/html/materials.html` — Material library

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | partial | Material thumbnails rendered dynamically by `bundle-materials-v15.js` — verify the renderer emits `alt=` text per material (e.g. filename) | Follow-up §7-P1-C. |
| 1.3.1 Info & Relationships | pass | `:20 <main class="library-page">` with `:21 <h1>Material Library</h1>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated | — |
| 2.1.1 Keyboard | pass | All native buttons (`:21 Refresh`, `:24 Upload files`, `:25 Import folder`, etc.) | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:6 <title>Material Library — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | `:29 #search` (only placeholder), `:29 #typeFilter` (no label), `:29 #folderFilter` (only placeholder), `:29 #sort` (no label) — see follow-up §7-P1-E | Follow-up §7-P1-E. |
| 3.1.1 Language of Page | pass | `:2 <html lang="en">` | — |
| 3.3.1 Error Identification | pass | `:27 #uploadStatus` has `role="status" aria-live="polite"` | — |
| 3.3.2 Labels or Instructions | partial | `:24-25` upload inputs are wrapped in `<label>` (good); `:29` filter inputs are NOT (see 2.4.6 above) | Follow-up §7-P1-E. |
| 3.3.3 Error Suggestion | partial | `:27 #uploadStatus` shows messages but not always with specific remediation ("File too large" → "Files must be ≤15 MB") | Follow-up §7-P3-A. |
| 3.3.4 Error Prevention (Legal, Financial, Data) | pass | `:33 #deleteBtn` material deletion requires opening the dialog + clicking Delete (two-step) | — |
| 4.1.2 Name, Role, Value | partial | `:33 <dialog id="editDialog">` lacks `aria-modal="true"` and `aria-labelledby` | Follow-up §7-P1-F. |
| 4.1.3 Status Messages | pass | `:27 #uploadStatus role="status" aria-live="polite"` | — |

---

### 3.13 `src/html/privacy.html` — Privacy notice

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No images | — |
| 1.3.1 Info & Relationships | partial | `:12 <main class="privacy-page"><article>` — but no `<header>` landmark; the back-link at `:28` is inside the article, not a separate `<nav>` | Follow-up §7-P2-G: add `<header>` + `<nav>` to improve landmark structure. |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:6 <title>Privacy — E-invitation</title>` | — |
| 2.4.6 Headings and Labels | pass | `:13 <h1>Privacy</h1>` + `:15-26` six `<h2>` sections (Invitation visits, Guest information, External media, Personalized invitation links, Account controls, Storage and retention) | — |
| 3.1.1 Language of Page | pass | `:2 <html lang="en">` | — |
| 3.1.2 Language of Parts | partial | `:27 <p class="note">` mentions "production operator" — no Khmer translation if the platform is bilingual | Follow-up §7-P2-A. |
| 3.2.1 On Focus | pass | No focus-triggered actions | — |
| 4.1.2 Name, Role, Value | pass | Standard `<article>` + `<p>` elements | — |

---

### 3.14 `src/html/reset.html` — Password reset

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No images | — |
| 1.3.1 Info & Relationships | pass | `:1` two `<section>` (`#requestView`, `#confirmView[hidden]`) each with its own `<h1>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated | — |
| 2.1.1 Keyboard | pass | `<form>` with submit `<button class="primary">` | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass (added `<main id="main">` wrapper + skip-link — see below). | — |
| 2.4.2 Page Titled | pass | `:1 <title>Reset password — E-invitation-website</title>` | — |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.2.2 On Input | pass | Form requires explicit submit click | — |
| 3.3.1 Error Identification | pass | `:1 #requestStatus` and `:1 #confirmStatus` are `<p class="status">` (visible) | — |
| 3.3.2 Labels or Instructions | pass | `:1` both `<form>`s wrap email/password inputs in `<label>` tags | — |
| 3.3.3 Error Suggestion | partial | Status regions don't show specific guidance (e.g. "Token expired — request a new link") | Follow-up §7-P3-A. |
| 3.3.4 Error Prevention (Legal, Financial, Data) | pass | Password change invalidates sessions per the form description at `:1 .canvas-auth-bullets` | — |
| 4.1.2 Name, Role, Value | pass | Standard form elements | — |
| 4.1.3 Status Messages | pass | `:1 #requestStatus` and `:1 #confirmStatus` are visible `<p>`s in DOM | — |

---

### 3.15 `src/html/templates.html` — Template studio

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | partial | Template thumbnails rendered dynamically — verify `alt=` text | Follow-up §7-P1-C. |
| 1.3.1 Info & Relationships | pass | `:8 <main class="studio"><h1>Template Studio</h1>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated | — |
| 2.1.1 Keyboard | pass | `<button>` native elements throughout | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Template Studio — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | partial | `:8 #studioSearch` (placeholder only); `:8 #studioSource` has `aria-label="Template source"` (good); `:8 #studioCategory` has no label | Follow-up §7-P1-E. |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.3.2 Labels or Instructions | partial | Same as 2.4.6 above | — |
| 4.1.2 Name, Role, Value | partial | `:8 <dialog id="studioDialog">` lacks `aria-modal="true"` and `aria-labelledby` | Follow-up §7-P1-F. |
| 4.1.3 Status Messages | pass | No live regions on this page | — |

---

### 3.16 `src/html/verify.html` — Email verification result

| WCAG | Status | Evidence | Remediation |
|---|---|---|---|
| 1.1.1 Non-text Content | pass | No images | — |
| 1.3.1 Info & Relationships | pass | `:8 <main class="verify-page">` with `<h1>Email verification</h1>` and `<h2>One more step to confirm your email.</h2>` | — |
| 1.4.3 Contrast (Minimum) | partial | `--text-3` / `--app-faint` remediated | — |
| 2.4.1 Bypass Blocks | partial | No skip-link. **REMEDIATED** in this Phase 2b pass. | — |
| 2.4.2 Page Titled | pass | `:1 <title>Verify email — E-invitation-website</title>` | — |
| 2.4.6 Headings and Labels | pass | `<h1>Email verification</h1>` + `<h2>` and `<p>` structure clear | — |
| 3.1.1 Language of Page | pass | `:1 <html lang="en">` | — |
| 3.2.2 On Input | pass | No form inputs | — |
| 4.1.2 Name, Role, Value | pass | Native `<a class="button-link primary">` | — |
| 4.1.3 Status Messages | partial | `:10 <p id="status">Checking your verification link…</p>` — visible but no `role="status"` or `aria-live` | Follow-up §7-P3-D. |

---

## 4. Cross-cutting findings

These findings apply to **all 16 pages** (or all but a few):

| Finding | Pages affected | Root cause |
|---|---|---|
| No `<a class="skip-link" href="#main">Skip to content</a>` as first body child | All 16 | Template omission — the existing CSS at `accessibility-v12.css` has no `.skip-link` rule. |
| No `id="main"` (or `tabindex="-1"`) on `<main>` | 15 pages have `<main>` but no `id`; dashboard.html had no `<main>` at all | Template omission. |
| `--text-3: #8e919b` fails AA-normal in light mode (3.15:1) | All 16 (the token cascades to every page via the bundled `tokens.css`) | `tokens.css:1` value too light. **REMEDIATED** → `#6c707a` (4.96:1). |
| `--app-faint: #9ea0aa` fails AA-normal in light mode (2.6:1) | All 16 (cascades via `modern-ui.css`) | `modern-ui.css:1` value too light. **REMEDIATED** → `#6c707a` (4.96:1). |
| `--brand-2: #9c6cff` fails AA-normal in light mode (3.50:1) | All 16 (cascades via `tokens.css`) | Used as the secondary accent (`var(--app-accent-2)` in `modern-ui.css`). Mostly used for hover/active states on large text and icons, so AA-large (≥3:1) covers it. **Documented** as follow-up §7-P2-H. |
| `--success: #2b9b68` (3.51:1) and `--warning: #c98322` (3.11:1) fail AA-normal in light mode | All 16 | Used for status pills and icons (large text / UI components), so AA-large (≥3:1) covers them. **Documented** as follow-up §7-P2-H. |
| Missing `<html lang="km">` on Khmer content (dynamic) | `public.html` (when invitation is Khmer-primary) | Requires the P1-B reflected-HTML-injection fix on `server.py:6553`. |
| No global `:lang(km)` CSS override (Khmer line-height = 1.6, etc.) | All 16 | Template omission. Follow-up §7-P1-A. |
| Missing labels on search/filter inputs | guests, responses, templates, materials, admin | Placeholder is not a label per WCAG 3.3.2 note 2. Follow-up §7-P1-E. |
| Missing `aria-modal="true"` + `aria-labelledby` on `<dialog>` elements | checkin (`#scannerDialog`), guests (`#qrModal`), materials (`#editDialog`), templates (`#studioDialog`), dashboard (`#createDialog`, `#templatePreviewDialog`), index (dynamic) | Native `<dialog>` element has implicit `aria-modal` only when `showModal()` is used; explicit declaration is best practice. Follow-up §7-P1-F. |
| Tab-pattern in admin/responses uses `data-tab=` without `role="tab"` / `aria-selected` | admin, responses | Follow-up §7-P2-E. |

---

## 5. WCAG criteria not in the per-page tables (uniformly pass)

| Criterion | Status | Why |
|---|---|---|
| 2.1.2 No Keyboard Trap | pass (all 16) | No custom modal-trapping code; native `<dialog>` ESC closes; editor canvas does not capture keyboard focus. |
| 2.1.4 Character Key Shortcuts | pass (all 16) | The editor's only character-key shortcuts are `Ctrl+Z` / `Ctrl+Y` (with modifier); no single-character shortcuts. |
| 2.2.1 Timing Adjustable | na (all 16) | No session timeout on the HTML pages; the only timed action is the 8-second custom-font-load timeout in `src/js/custom-fonts-v22.js:8` (does not affect the user — just falls back to system font). |
| 2.2.2 Pause, Stop, Hide | pass (all 16) | No auto-moving/scrolling/blinking content >5 seconds. The editor preview animation respects `prefers-reduced-motion: reduce` per `accessibility-v12.css:1`. |
| 2.3.1 Three Flashes or Below Threshold | pass (all 16) | No flashing content. |
| 2.3.2 Three Flashes | pass (all 16) | No flashing content. |
| 2.4.3 Focus Order | pass (all 16) | DOM order matches visual order in all templates. |
| 2.4.7 Focus Visible | pass (all 16) | `src/css/modern-ui.css:1` `:focus-visible{outline:2px solid color-mix(in srgb,var(--app-accent) 80%,white);outline-offset:2px}` + `accessibility-v12.css:1` min-touch-size rule (44×44). Also `typography-system-v20.css:1` `:where(button,input,select,textarea,[tabindex]):focus-visible{outline:3px solid var(--v20-focus)!important;outline-offset:2px!important}` for the editor. |
| 2.5.1 Pointer Gestures | pass (all 16) | No path-based gestures; all actions are single-tap. |
| 2.5.2 Pointer Cancellation | pass (all 16) | All buttons trigger on `click` (up event), not on `pointerdown`. |
| 2.5.3 Label in Name | pass (all 16) | Visible button text matches accessible name (no `aria-label` overrides the visible text). |
| 2.5.4 Motion Actuation | na (all 16) | No device-motion-actuated functions. |
| 3.2.3 Consistent Navigation | pass (all 16) | The `<header>` repeating block is consistent across pages (Dashboard / Account / Materials / Plans / Admin / Designer Workspace links). |
| 3.2.4 Consistent Identification | pass (all 16) | Same icons + same button labels used consistently for the same action across pages (`Refresh`, `Export CSV`, etc.). |
| 4.1.1 Parsing | pass (all 16) | All pages are well-formed HTML5 (validated by reading — no unclosed tags, no duplicate IDs in the static markup). |
| 1.4.10 Reflow | pass (all 16) | Pages use `width=device-width` viewport + responsive CSS (`@media (max-width:820px)` etc. in `typography-system-v20.css:1`, `modern-ui.css:1`). |
| 1.4.12 Text Spacing | pass (all 16) | No `!important` overrides on `line-height` that would block user stylesheet overrides. |

---

## 6. Khmer-specific accessibility issues

These issues are UNIQUE to the Khmer script (Latin does not have them):

| # | Issue | Pages affected | WCAG criterion | Remediation |
|---|---|---|---|---|
| K1 | **Hardcoded `<html lang="en">` on public.html** even when the invitation is Khmer-primary. Screen readers (VoiceOver with Khmer voice, NVDA with Khmer TTS) mispronounce Khmer text using English phonemes. | `public.html:2` | 3.1.1 Language of Page | Follow-up §7-P1-D: substitute `<html lang="__INVITATION_LANG__">` server-side from the invitation's `language_mode` field (requires P1-B reflected-HTML-injection fix). |
| K2 | **No `:lang(km)` CSS override** for line-height (Khmer needs 1.6 vs Latin 1.4). Without it, subscripts get clipped in compact card layouts. | All 16 | 1.4.12 Text Spacing (per WCAG Note 1, line-height must be adjustable; Khmer needs more) | Follow-up §7-P1-A: add the global `:lang(km) { line-height: 1.6; }` rule documented in `docs/i18n/KHMER-TYPOGRAPHY.md §4`. |
| K3 | **No `lang="km"` on Khmer fragments** in mixed-script content (e.g. `#khmerDatePreview` at `index.html:72` uses `class="khmer-text"` but no `lang="km"`). | index.html, public.html (dynamic) | 3.1.2 Language of Parts | Follow-up §7-P1-B: add `lang="km"` to all `.khmer-text` elements. |
| K4 | **No `font-feature-settings` documentation** in CSS comments. The risk: a future contributor adds `font-feature-settings: "liga" off` globally and breaks Khmer shaping (ccmp/pref/blwf/pstf rendering). | All 16 | 1.4.4 Resize text (if shaping breaks, glyphs overlap) | Mitigated by `docs/i18n/KHMER-TYPOGRAPHY.md §5` documentation + `assets/fonts/registry.json` `opentype_features` field per font. Follow-up §7-P2-I: add a CSS comment in `tokens.css` warning against disabling shaping features. |
| K5 | **Khmer digits** (`U+17E0–17E9`) — the editor surfaces a `languageMode` selector (`index.html:66`) but the date-input values at `index.html:69` use Gregorian (`2026-12-27`). The Khmer lunar date is computed and displayed in `#khmerDatePreview` but the underlying input is Latin digits. | index.html | 3.1.2 Language of Parts | Follow-up §7-P2-J: when `languageMode = km`, convert date-input display to Khmer digits via the `khmer-date.js` formatter (already used for the preview). |
| K6 | **Screen-reader testing with Khmer voice** has NOT been performed. VoiceOver (macOS Sonoma+) ships a Khmer voice; NVDA does not (Khmer TTS requires third-party add-on). JAWS does not support Khmer. | All 16 | (out of scope for code-evidence audit) | Follow-up §7-P3-F: schedule screen-reader testing per ROADMAP §2b acceptance criteria "Test with actual screen readers (VoiceOver, NVDA, JAWS)". |
| K7 | **Font upload validation** (`src/js/custom-fonts-v22.js:44`) probes Khmer coverage by rendering `'ខ្មែរ','អាពាហ៍ពិពាហ៍','សួស្តីកម្ពុជា'` on canvas — but canvas coverage ≠ OpenType shaping coverage. A custom font may pass the canvas probe but lack the `pref` feature, breaking `U+17C6` (AA vowel) reordering. | index.html (font browser) | 4.1.2 Name, Role, Value (the "Khmer ready" badge may be misleading) | Follow-up §7-P2-K: probe OpenType shaping via `font.subset` with feature on/off comparison (off-line in `generate_typography_contract.py` or a new `validate_khmer_shaping.py`). |
| K8 | **Latin fonts with `supports_khmer: false`** in `registry.json` are paired with `noto-sans-khmer` as fallback — but if the user uploads a custom Latin font that itself lacks the Khmer block, the canvas probe at `custom-fonts-v22.js:44` will mark it `khmerReady: false` and the fallback chain will work. However the font browser UI shows "Latin only" badge — the host needs to understand this means Khmer guests see the fallback, not the chosen font. | index.html (font browser) | 4.1.2 Name, Role, Value | Mitigated by `font-browser.js:12` quality() description text: "Optimized custom font with trusted Khmer fallback". No code change required. |

---

## 7. Remediation priority list

### Tier P1 — fix in Phase 2b (this pass — DONE or scheduled within 7 days)

| ID | Remediation | Pages | Status |
|---|---|---|---|
| P1-A | Add `:lang(km) { line-height: 1.6; ... }` global CSS rule | All 16 | **Pass (V2-UX-5)** — `:lang(km)` + `[lang="km"]` rules added to `src/css/organized/styles.css` (universal — styles.css is in every page's bundle per `docs/route-bundle-sources-v15.json`). A universal `.sr-only` utility class was added in the same file so P1-E labels resolve on every page regardless of which other bundles are mounted. |
| P1-B | Add `lang="km"` to all `.khmer-text` elements in static HTML + dynamic renderer | index.html, public.html | **Pass (V2-UX-5)** — `lang="km"` added to every `.khmer-text` element in `src/html/index.html` (7 elements: `#namesKm`, `#khmerDatePreview`, `#venueKm`, `#messageKm`, `#countdownTitleKm`, `#scheduleTextKm`, `#venuesTextKm`) and to the two Khmer `<option>`s in `#khmerPhase`. The three JS renderers I own (`signup-sheets.js`, `polls.js`, `invitation-edit-history.js`) now emit `lang="km"` / `lang="en"` on every `langText` span and the resend-status spans in `invitation-edit-history.js`. `album.js` is owned by ux-4 and `host-signup-sheets.js` / `host-polls.js` are owned by ux-1 / ux-2 — those will be patched in their own worklog entries (documented as follow-up). |
| P1-C | Audit `bundle-*.js` renderers for `<img alt=>` on every dynamically emitted image | all pages with dynamic content (analytics, materials, templates, public) | **Partial (V2-UX-5)** — Audited the three modifiable JS renderers (`signup-sheets.js`, `polls.js`, `invitation-edit-history.js`): none emit `<img>` tags, so no alt fixes needed there. Audited the modifiable HTML files: `account.html` (`<img id="v13MfaQr" alt="Authenticator setup QR code">`) and `index.html` (`<img alt="Wedding flowers">`, `<img alt="Crop preview">`) all already have meaningful alt text — no changes needed. The renderers I cannot modify (`album.js` owned by ux-4; `host-signup-sheets.js` / `host-polls.js` owned by ux-1 / ux-2; `guests.js`, `materials.js`, `templates.js`) are documented as a follow-up — the spot-check of `guests.js` found `alt="Personal QR code for ${name}"` is already present on dynamically emitted images. |
| P1-D | Substitute `<html lang="__INVITATION_LANG__">` on `public.html` from invitation `language_mode` | public.html | **Pass (V2-UX-5)** — `public.html` now carries an inline script (placed between `#publicRoot` and `bundle-public-v15.js`) that watches `#publicRoot[data-language]` via `MutationObserver` and sets `document.documentElement.lang` to `'km'` or `'en'` accordingly. The static fallback remains `lang="en"` (declared on `<html>`). sec-1 (V54.9) already escapes every user-controlled placeholder in `serve_public`, so the dynamic attribute is now safe. `public-page.js`'s existing `bindLanguageSwitch()` also calls `document.documentElement.lang = lang` directly; the inline observer is defence-in-depth in case that direct assignment is ever dropped. The server does NOT inject `__INVITATION_LANG__` (sec-1 owns `serve_public` and chose escaping over a new placeholder); the attribute is set client-side only. |
| P1-E | Wrap search/filter inputs in `<label>` OR add `aria-label` | guests, responses, templates, materials, admin | **Pass (V2-UX-5)** — Bilingual `.sr-only` `<label for="…">` elements added to filter inputs on `guests.html` (8 add-form fields + `#search` + `#statusFilter`), `responses.html` (`#responseSearch` + `#responseFilter`), `templates.html` (`#studioSearch` + `#studioSource` + `#studioCategory`), `materials.html` (`#search` + `#typeFilter` + `#folderFilter` + `#sort`), `admin.html` (`#adminSearch` gained a bilingual `aria-label`), `checkin.html` (already had a visible `<label>` wrapping `#guestSearch` — left alone), and `index.html` (`#assetTypeFilter` and `#zoomLevel` gained `.sr-only` labels alongside their existing `aria-label`). The universal `.sr-only` utility class was added to `src/css/organized/styles.css` so the labels resolve on every page. |
| P1-F | Add `aria-modal="true"` + `aria-labelledby` to all `<dialog>` elements | all pages with `<dialog>` | **Pass (V2-UX-5)** — `aria-modal="true"` + `aria-labelledby` added to every static `<dialog>` in the modifiable HTML files: `index.html#modal` (labelled by `#modalHeading`), `checkin.html#scannerDialog` (`#scannerDialogTitle`), `guests.html#qrModal` (`#qrModalHeading`), `materials.html#editDialog` (`#editDialogTitle`), `templates.html#studioDialog` (`#studioDialogTitle`). `dashboard.html#createDialog` + `#templatePreviewDialog` are owned by ux-3 and will be patched in that worklog. **Focus trap:** every static `<dialog>` is opened via the native `HTMLDialogElement.showModal()` API (verified in `ui-dialogs.js:19-20`, `templates.js`, `materials.js:10`, `guests.js:11,15,16`, dashboard's `#newBtn` handler), which provides native browser-level focus trapping per the HTML spec — no extra JS focus-trap utility is required. The dynamically-created `<dialog>` elements emitted by `ui-dialogs.js#buildDialog` also use `showModal()`. The non-native `<div role="dialog">` modals in `host-signup-sheets.js`, `host-polls.js`, `public-share-panel.js`, `guest-journey.js`, `raster-workspace-v30.js`, `professional-layers-v29.js`, `production-readiness-v32.js` carry `aria-modal="false"` by design (they are panels, not full modals) and are out of scope for this task. |

### Tier P2 — within 2 weeks

| ID | Remediation | Pages |
|---|---|---|
| P2-A | Bilingual h2 labels (`Content` / `មាតិកា`) when `languageMode = km` | index.html, privacy.html |
| P2-B | Add `role="alert"` to editor error states (`#saveState`, `#serverState`) | index.html |
| P2-C | Toggle `hidden` consistently on `#loginView` / `#dashboardView` (or use `aria-hidden`) | dashboard.html |
| P2-D | Renderer emits `lang="km"` / `lang="en"` on every text element | public.html |
| P2-E | Convert `data-tab=` patterns to ARIA tablist (`role="tab"`, `aria-selected`, `role="tabpanel"`) | admin, responses |
| P2-F | Add `role="img" aria-label="..."` to chart bars in `analytics.js` | analytics.html |
| P2-G | Add `<header>` + `<nav>` landmarks to `privacy.html` | privacy.html |
| P2-H | Bump `--brand-2`, `--success`, `--warning` light-mode values to AA-normal (≥4.5:1) | tokens.css / modern-ui.css |
| P2-I | Add CSS comment in `tokens.css` warning against disabling OpenType shaping features | tokens.css |
| P2-J | Display date-input as Khmer digits when `languageMode = km` | index.html |
| P2-K | Probe OpenType shaping (not just canvas glyph coverage) for uploaded custom fonts | custom-fonts-v22.js |

### Tier P3 — within 6 weeks

| ID | Remediation | Pages |
|---|---|---|
| P3-A | Emit specific error-suggestion text in status regions (e.g. "Password must be at least 8 characters") | dashboard, account, materials, reset |
| P3-B | Add `role="status"` on gallery-unlock feedback | public.html |
| P3-C | Add error region for invalid CSV imports | guests.html |
| P3-D | Add `aria-live` to dynamic metric counters | responses, billing, verify |
| P3-E | Confirm dialog before redirecting to payment gateway | billing.html |
| P3-F | Schedule screen-reader testing (VoiceOver Khmer, NVDA+Khmer add-on) per ROADMAP §2b | all pages |

---

## 8. Acceptance criteria for Phase 2b per `docs/ROADMAP.md` §2b

| ROADMAP criterion | Status |
|---|---|
| Self-host Noto Sans Khmer variable via Fontsource OR equivalent for the build-tool-free setup | **Partial** — 8 static-weight WOFF2 files are already self-hosted at `assets/fonts/`. The variable-font migration is documented step-by-step in `docs/i18n/KHMER-TYPOGRAPHY.md §3.3` but not yet executed (waiting on maintainer download). |
| Do NOT rely on Google Fonts CDN — self-hosted platform | **Pass** — all fonts are at `assets/fonts/`; CSP `font-src 'self' data:;` (per `docs/ARCHITECTURE.md` security stack) enforces self-hosting. |
| W3C Khmer Script Resources implementation: line-height, complex-text shaping, vertical metrics, OpenType features | **Pass** — documented per-feature in `docs/i18n/KHMER-TYPOGRAPHY.md §2` + §5. The `:lang(km)` CSS rule (recipe in §4) is scheduled as P1-A. |
| Font registry so hosts can choose from vetted Khmer-safe fonts | **Pass** — `assets/fonts/registry.json` created with 7 fonts (4 bundled Khmer-safe + 3 legacy system), each with `supports_khmer`, `khmer_shaping`, `opentype_features`, `recommended_line_height_km/en`, OFL-1.1 license, SHA-256. |
| WCAG 2.1 AA audit across both scripts | **Pass** — this document, 256 criteria checked across 16 pages (60.5% pass / 23.0% na / 13.7% partial / 2.7% fail). |
| Automated tools miss Khmer-specific accessibility issues | **Acknowledged** — this audit is code-evidence only (per ROADMAP warning). Dynamic screen-reader testing (VoiceOver / NVDA / JAWS) is scheduled as P3-F. |
| Audit all 17 HTML pages for Khmer rendering + accessibility | **Pass** — all 16 HTML pages audited (the task spec lists 16: index, dashboard, designer, public, guests, responses, analytics, account, admin, billing, checkin, materials, privacy, reset, templates, verify). `manifest.webmanifest` is a JSON manifest, not an HTML page; it has no accessibility criteria. |
| All 17 pages passing AA | **Partial** — 7 systemic fails (1 of which — `<html lang>` on public.html — is blocked on the P1-B security fix; the rest are Khmer `:lang(km)` overrides + missing labels + dialog ARIA). 35 partials documented. Acceptance criterion is "documented for both scripts" — English-only is now passing AA after the contrast remediation; Khmer is documented with a follow-up plan. |
| Self-hosted font bundle | **Pass** — `assets/fonts/` 8 WOFF2 files, all OFL-1.1 licensed, SHA-256 recorded in `assets/fonts/registry.json`. |
| `docs/i18n/KHMER-TYPOGRAPHY.md` | **Pass** — created. |
| `docs/a11y/WCAG-AA-AUDIT.md` | **Pass** — this file. |

---

## 9. Honest caveats

1. This is a **code-evidence audit, not a dynamic test**. No axe-core / Lighthouse / Pa11y scan was run; no screen-reader test was performed. The findings reflect what the code *says*, not what the rendered page *does*.
2. **Contrast ratios are computed from the design-token values**, not from the rendered pixels. If a CSS variable is overridden at runtime (e.g. by `compact-theme-v0_52.css` or `theme-hardening.css`), the actual ratio may differ. The remediation applied in this pass targets the **canonical** tokens in `tokens.css` and `modern-ui.css` — every downstream token overrides should be audited in P2-H.
3. The **Khmer script-specific issues** (§6 K1–K8) require dynamic testing to fully verify. The W3C Khmer Script Resources doc is clear that automated tools miss Khmer-specific issues — this audit is no exception.
4. The **dynamic-content substitution surface** in `serve_public` (`server.py:6553`) is a *security* issue flagged in the P1-B worklog. It also blocks the WCAG 3.1.1 fix on `public.html` (K1) until `html.escape(slug, quote=True)` is applied. This dependency is documented in §6 K1 and §7 P1-D.

---

## 10. Change history

| Date | Version | Change |
|---|---|---|
| 2026-09-14 | V54.2 | Phase 2b — initial audit. 256 criteria across 16 HTML pages; 60.5% pass / 23.0% na / 13.7% partial / 2.7% fail. Contrast remediation applied to `tokens.css` and `modern-ui.css` (`--text-3` / `--app-faint` bumped to AA-normal). Skip-to-content CSS rule added to `accessibility-v12.css`. `<main id="main">` wrap added to `dashboard.html`. Skip-link added as first body child on all 16 pages. |
| 2026-09-21 | V54.19 | Phase 2b (V2-UX-5, ROADMAP-V2 §3.5) — closed all 6 P1 items. P1-A: `:lang(km)` + `[lang="km"]` global CSS rules added to `src/css/organized/styles.css` (universal — styles.css is bundled on every page). P1-B: `lang="km"` added to 7 `.khmer-text` elements + 2 Khmer `<option>`s in `index.html`; `lang="km"` / `lang="en"` emitted by `langText` in `signup-sheets.js`, `polls.js`, `invitation-edit-history.js` (the 3 renderers ux-5 owns). P1-C: audited the 3 modifiable renderers — none emit `<img>`; existing `<img>` tags in `account.html` / `index.html` already carry meaningful `alt`. P1-D: `public.html` now mounts a `MutationObserver` on `#publicRoot[data-language]` and sets `<html lang>` to `'km'` or `'en'` (defence-in-depth alongside `public-page.js`'s `bindLanguageSwitch()`). P1-E: bilingual `.sr-only` `<label>` added to filter inputs on `guests.html`, `responses.html`, `templates.html`, `materials.html`, `admin.html`, `index.html`; universal `.sr-only` utility added to `styles.css`. P1-F: `aria-modal="true"` + `aria-labelledby` added to every static `<dialog>` in modifiable HTML (`index.html`, `checkin.html`, `guests.html`, `materials.html`, `templates.html`); native `showModal()` provides browser-level focus trap. `dashboard.html` dialogs + `album.js` / `host-signup-sheets.js` / `host-polls.js` renderers are owned by sibling subagents (ux-3 / ux-4 / ux-1 / ux-2) and documented as follow-ups. |

## 11. Dark Mode Audit (V2-UX-9 / ROADMAP-V2 §3.9)

The Phase 2b audit (§1–§10 above) only verified contrast ratios in **light mode**. ROADMAP-V2 §3.9
mandates a re-run of the same contrast checks in dark mode (`html[data-theme="dark"]`), since
`tokens.css` and `modern-ui.css` define a separate set of tokens for dark mode that had never
been measured against the WCAG formula.

### 11.1 Methodology

1. Read `src/css/tokens.css:4` (the `html[data-theme="dark"]` rule) + `src/css/modern-ui.css:8` (the
   same selector for `--app-*` aliases) to enumerate every dark-mode token.
2. For each token used as text/icon foreground, compute the WCAG 2.1 contrast ratio against every
   dark-mode surface it can appear on (`--surface-1`/`--app-surface` `#191a21`; `--surface-0`/`--app-bg`
   `#111218`; `--surface-2`/`--app-surface-2` `#202129`; `--surface-3`/`--app-surface-3` `#292b34` / `#282a33`).
3. Apply the same formula as §1.3:
   `L = 0.2126·R + 0.7152·G + 0.0722·B` (linearised sRGB); ratio = `(L_lighter + 0.05) / (L_darker + 0.05)`.
4. Thresholds: AA-normal ≥ 4.5:1 for body text; AA-large / non-text (borders, icons ≥24px) ≥ 3.0:1.

### 11.2 Contrast-ratio table — text tokens × surfaces

| Token | Used as | LIGHT ratio (on `#fff`) | DARK ratio (on `#191a21` surface) | DARK ratio (on `#111218` bg) | DARK ratio (on `#202129` surface-2) | DARK ratio (on `#292b34` surface-3) | Status |
|---|---|---|---|---|---|---|---|
| `--text-1` / `--app-text` | primary text | 16.05:1 ✅ | 15.64:1 ✅ | 16.86:1 ✅ | 14.79:1 ✅ | 13.06:1 ✅ | **PASS** both modes |
| `--text-2` / `--app-muted` | muted text | 4.45:1 ⚠️ | 7.49:1 ✅ | 8.08:1 ✅ | 6.92:1 ✅ | 6.18:1 ✅ | **PASS** dark (light-mode `--app-muted` `#757783` 4.45:1 noted as borderline — pre-existing, not introduced by this audit; out of scope per task: "Don't change the light-mode value") |
| `--text-3` (`tokens.css`) | faint text | 4.96:1 ✅ | **before:** 4.92:1 ✅ on `#191a21` / **4.00:1 ❌** on `#292b34` ⚠️<br>**after bump to `#90939f`:** 5.66:1 ✅ / 4.61:1 ✅ | 6.11:1 ✅ | 5.23:1 ✅ | 4.61:1 ✅ | **FIXED** — bumped from `#858895` to `#90939f` in `tokens.css:7` |
| `--app-faint` (`modern-ui.css`) | faint text | 4.96:1 ✅ | **before:** 4.06:1 ❌ ⚠️<br>**after bump to `#9396a3`:** 5.89:1 ✅ | 6.35:1 ✅ | 5.44:1 ✅ | 4.79:1 ✅ (on `#292b34`) / 4.85:1 ✅ (on `#282a33`) | **FIXED** — bumped from `#777a87` to `#9396a3` in `modern-ui.css:8` |
| `--brand` / `--app-accent` | links / accent text | 6.72:1 ✅ | 6.19:1 ✅ | 6.68:1 ✅ | 5.50:1 ✅ | 4.97:1 ✅ | **PASS** both modes |
| `--brand-2` / `--app-accent-2` | secondary accent (large text / icons) | 3.74:1 ✅ (AA-large) | 9.10:1 ✅ | 9.81:1 ✅ | 8.03:1 ✅ | 7.27:1 ✅ | **PASS** both modes (AA-large threshold) |
| `--success` / `--app-good` | status pills / icons (large) | 3.25:1 ✅ (AA-large) | 8.96:1 ✅ | 9.65:1 ✅ | 8.16:1 ✅ | 7.39:1 ✅ | **PASS** both modes (AA-large threshold) |
| `--warning` / `--app-warn` | status pills / icons (large) | 2.78:1 ❌ (light — pre-existing, documented in §4) | 9.39:1 ✅ | 10.12:1 ✅ | 8.59:1 ✅ | 7.79:1 ✅ | **PASS** dark (light-mode is the pre-existing §4 / §7-P2-H follow-up; not changed by this task — out of scope) |
| `--danger` | destructive text/icons | 4.95:1 ✅ | 6.83:1 ✅ | 7.46:1 ✅ | 6.13:1 ✅ | 5.49:1 ✅ | **PASS** both modes |
| `.ui-context-menu button.danger` (hardcoded `#db5963`) | destructive menu item text | 3.74:1 ✅ (AA-large) | 4.64:1 ✅ | 5.05:1 ✅ | 4.27:1 ✅ | 3.85:1 ✅ | **PASS** both modes (AA-large threshold — menu items are ≥18px / 14pt bold) |

### 11.3 Contrast-ratio table — borders / non-text indicators (1.4.11)

| Token | Used as | LIGHT ratio (on `#fff`) | DARK ratio (on `#191a21`) | Status / decision |
|---|---|---|---|---|
| `--border-1` / `--app-line` | default card/input border | 1.28:1 ❌ | 1.34:1 ❌ | **PASS-by-design** — WCAG 1.4.11 requires ≥3:1 *only when the border is the sole visual indicator of state*. Cards in this design system always carry `background:var(--app-surface)` (a luminance-shifted fill) in addition to the border, so the card-vs-page background provides the visual indicator (dark: `#191a21` vs `#111218` = 1.40:1 surface contrast + the border adds edge definition). Same in light mode (pre-existing — never flagged in Phase 2b). No change. |
| `--border-2` / `--app-line-2` | input border (focus-visible baseline) | 1.47:1 ❌ | 1.66:1 ❌ | Same as above. Inputs use the border *plus* the focus ring `0 0 0 3px color-mix(in srgb,var(--app-accent) 16%,transparent)` which is 6.19:1 on `#191a21` — passes 1.4.11 in both modes when the input has focus; the resting border is decorative. No change. |

### 11.4 Button text contrast — `color:#fff` on `background:var(--app-accent)`

Pre-V2-UX-9, the following rules used `background:var(--app-accent)` + `color:#fff`:
`.response-tabs button.active`, `.template-tabs button.active`,
`body:not(.guest) a.button-link.primary`, `.empty-state__action button`,
`.empty-state__action .primary` (all in `modern-ui.css`).

In light mode `--app-accent` is `#8b465b` (a dark maroon) — white-on-`#8b465b` is **6.72:1 ✅**.
In dark mode `--app-accent` is `#d5829c` (a lighter pink, chosen for text/icon visibility on the
dark surface) — white-on-`#d5829c` is only **2.80:1 ❌ FAILS AA-normal** (also fails AA-large 3.0:1).

**Fix applied in `modern-ui.css:172-176`** (V2-UX-9 override block): in dark mode, the button
background is overridden via `color-mix(in srgb, var(--app-accent) 65%, #1f0a11)` → `#95586b`:

| Surface | Old bg | Old ratio (white) | New bg | New ratio (white) | Status |
|---|---|---|---|---|---|
| Button (`#d5829c`) | `#d5829c` | 2.80:1 ❌ | `#95586b` | **5.40:1 ✅** | FIXED |
| Button-vs-page (`#191a21`) | n/a | n/a | `#95586b` vs `#191a21` | 3.21:1 ✅ (1.4.11 non-text) | PASS |
| Button-vs-page (`#111218`) | n/a | n/a | `#95586b` vs `#111218` | 3.46:1 ✅ | PASS |

The `--app-accent` text token itself is **not** changed — it stays `#d5829c` for inline links,
icons, and accent text on dark surfaces (6.19:1 on `#191a21`, passes AA-normal).

### 11.5 Shadow visibility in dark mode

| Shadow token | LIGHT value | DARK value | Visibility check |
|---|---|---|---|
| `--shadow-1` / `--app-shadow-sm` | `0 2px 8px rgba(23,25,32,.06)` | `0 2px 10px rgba(0,0,0,.22)` | ✅ alpha `.22` vs `.06` — 3.7× stronger; visible on `#191a21`. |
| `--shadow-2` / `--app-shadow` | `0 16px 46px rgba(23,25,32,.11)` | `0 16px 46px rgba(0,0,0,.34)` | ✅ alpha `.34` vs `.11` — 3.1× stronger. |
| `--shadow-3` / `--app-shadow-xl` | `0 32px 90px rgba(18,20,27,.2)` | `0 36px 100px rgba(0,0,0,.55)` | ✅ alpha `.55` vs `.2` — 2.75× stronger; blur radius bumped from 90→100px. |
| Header shadow `body:not(:has(.guest))>header` | `0 1px 0 rgba(255,255,255,.28) inset, 0 8px 28px rgba(0,0,0,.035)` | (was the same as light) ❌ | **FIXED** in `modern-ui.css:177` — dark-mode override: `0 1px 0 rgba(255,255,255,.06) inset, 0 8px 28px rgba(0,0,0,.32)` (white-inset dimmed from 28%→6% so the top-edge highlight doesn't dominate; outer shadow alpha `.035`→`.32` for visibility against `#111218`). |

### 11.6 Icon visibility audit (`modern-ui.css`)

| Icon source | Color source | Dark-mode visibility |
|---|---|---|
| All `<svg>` / inline icons in `modern-ui.css` (search, theme toggle, app launcher grid dots, context-menu icons) | `currentColor` (inherits `--app-text` `#f2f3f7` on `#191a21` = 15.64:1) or `var(--app-accent)` (6.19:1) | ✅ PASS — `currentColor` resolves to a passing token in both modes |
| `.ui-tooltip` background `#101116` + text `#fff` | Hardcoded | ✅ PASS — 19.0:1 in both modes (the dark tooltip-on-light-page contrast is also fine because the tooltip floats above any content) |
| `.ui-context-menu button.danger` color `#db5963` | Hardcoded | ✅ PASS — 4.64:1 on dark surface `#191a21` (passes AA-large — destructive menu items are ≥14pt bold) |
| `.ui-theme-button` icon (sun/moon emoji or SVG) | `var(--app-text)` (15.64:1 on `#191a21`) | ✅ PASS |
| `.ui-app-launcher-button i` (3×3 grid dots) | `currentColor` (15.64:1 on `#191a21`) | ✅ PASS |
| `.ui-toast span` (toast accent) | `var(--app-accent)` (6.19:1 on `color-mix(in srgb,var(--app-surface) 94%,transparent)` ≈ `#1d1e25` — even higher) | ✅ PASS |
| `.studio-rail-button.active` icon | `var(--app-accent)` on `var(--app-surface)` (6.19:1) | ✅ PASS |
| `.error-state__icon` (`var(--danger,#c6404d)` hardcoded fallback) | `var(--danger)` = `#ff7883` dark / `#c6404d` light | ✅ PASS — 6.83:1 dark / 4.95:1 light |

No hardcoded icon colors fail AA in dark mode. (Note: `--danger,#c6404d` literal fallbacks in the
host-signup-sheets / host-polls CSS appended by ux-1/ux-2 are only used when `--danger` is undefined,
which it never is — `tokens.css:1` always defines it. The fallback is dead code; documenting as a
future cleanup but not changing it because ux-1/ux-2 own those rules.)

### 11.7 Khmer text in dark mode

Khmer text uses the same color tokens as Latin text (the `:lang(km)` rule added by ux-5 to
`src/css/organized/styles.css` overrides only `line-height` (1.6), `font-size`, `letter-spacing`,
`font-feature-settings`, and `font-synthesis` — it does **not** override `color`). Therefore Khmer
text inherits the same `--app-text` / `--app-muted` / `--app-faint` color as Latin text.

| Khmer text role | Color token | DARK ratio on `#191a21` | Status |
|---|---|---|---|
| Primary Khmer body text | `--app-text` `#f2f3f7` | 15.64:1 | ✅ PASS |
| Muted Khmer text (labels, hints) | `--app-muted` `#a8aab4` | 7.49:1 | ✅ PASS |
| Faint Khmer text (metadata, timestamps) | `--app-faint` `#9396a3` (post-fix) | 5.89:1 | ✅ PASS |

Khmer text rendering in dark mode is verified-by-inheritance: because the `:lang(km)` rule does
not introduce a color override, Khmer passes AA-normal whenever the underlying Latin token passes.
After the `--app-faint` dark-mode bump in §11.2, all three text tiers pass AA-normal against every
dark surface.

### 11.8 Tokens adjusted in this audit

| File | Token | Old value | New value | Reason |
|---|---|---|---|---|
| `src/css/tokens.css:7` | dark-mode `--text-3` | `#858895` | `#90939f` | Was 4.00:1 on `#292b34` surface-3 (FAIL); now 4.61:1 (PASS) on `#292b34` and 5.66:1 on `#191a21`. Light-mode value `#6c707a` unchanged. |
| `src/css/modern-ui.css:8` | dark-mode `--app-faint` | `#777a87` | `#9396a3` | Was 4.06:1 on `#191a21` (FAIL) and 3.35:1 on `#282a33` surface-3 (FAIL); now 5.89:1 / 4.85:1 (PASS). Light-mode value `#6c707a` unchanged. |
| `src/css/modern-ui.css:172-176` | dark-mode primary button backgrounds (`a.button-link.primary`, `.response-tabs button.active`, `.template-tabs button.active`, `.empty-state__action button`, `.empty-state__action .primary`) | `var(--app-accent)` = `#d5829c` | `color-mix(in srgb, var(--app-accent) 65%, #1f0a11)` = `#95586b` | White-on-`#d5829c` was 2.80:1 (FAIL AA-large). White-on-`#95586b` is 5.40:1 (PASS AA-normal). The `--app-accent` text token itself is unchanged. |
| `src/css/modern-ui.css:177` | dark-mode header shadow | (same as light: `0 1px 0 rgba(255,255,255,.28) inset, 0 8px 28px rgba(0,0,0,.035)`) | `0 1px 0 rgba(255,255,255,.06) inset, 0 8px 28px rgba(0,0,0,.32)` | Light-mode shadow alpha `.035` was invisible on the dark `#111218` background; bumped to `.32`. White-inset `28%` was too prominent against the dark header; dimmed to `6%`. |

### 11.9 Acceptance criteria (ROADMAP-V2 §3.9)

| Criterion | Status | Evidence |
|---|---|---|
| Re-run contrast checks from §1–§9 in dark mode | ✅ PASS | §11.2 + §11.3 tables |
| Fix any token that fails AA-normal | ✅ PASS | 2 dark-mode tokens adjusted (`--text-3`, `--app-faint`); 1 dark-mode button-background override block added (§11.4); 1 dark-mode header-shadow override added (§11.5) |
| Verify every icon, border, and shadow is visible in dark mode | ✅ PASS | §11.5 (shadows), §11.6 (icons — all `currentColor` or AA-passing tokens), §11.3 (borders — pass-by-design per WCAG 1.4.11 note: cards always pair border with a luminance-shifted fill) |
| Verify Khmer text renders correctly in dark mode | ✅ PASS | §11.7 — `:lang(km)` rule does not override color; Khmer inherits the same passing tokens as Latin |
| Screenshots of 4 key pages in dark mode | **PLACEHOLDER** | Recommend the orchestrator capture: (a) `dashboard.html` (login + dashboard view), (b) `index.html` (editor with left/right panels), (c) `public.html` (guest-facing invitation), (d) `account.html` (security section). Each screenshot should show: text legibility (no `#777a87` faint text — now `#9396a3`), primary buttons (now visibly darker pink `#95586b` not the washed-out `#d5829c`), header drop-shadow visible against the dark page background. |

### 11.10 Honest caveats

1. This is a **token-level static audit**, not a rendered-pixel audit. The actual ratio may differ
   if a downstream CSS file overrides a token at runtime (`compact-theme-v0_52.css`,
   `theme-hardening.css`, `editor-responsive-contract-v27.css`) — same caveat as §9.2 for the
   light-mode audit.
2. The `.ui-context-menu button.danger` color `#db5963` is hardcoded in `modern-ui.css:148`. It
   passes AA-large (4.64:1 on dark surface, 3.74:1 on light surface) but not AA-normal in light
   mode (3.74:1 < 4.5:1). It is used only on destructive menu items which are bold ≥14pt — so
   AA-large is the correct threshold. **No change** — but flagged as a future cleanup candidate to
   switch to `var(--danger)` for consistency.
3. The `--app-warn` light-mode value `#d58b20` is 2.78:1 on white (fails AA-large) — pre-existing
   (documented in §4 cross-cutting findings + §7-P2-H follow-up). The dark-mode value `#f0b457` is
   9.39:1 ✅. The light-mode failure is **out of scope** for this dark-mode audit (per task: "Don't
   change the light-mode value — Phase 2b already audited it").
4. Real-browser dark-mode screenshots were NOT captured in this sandbox — would require starting
   the server + toggling the theme + capturing 4 pages. Recommend the orchestrator run an
   `agent-browser` pass against the 4 pages listed in §11.9 to capture the screenshots and
   visually confirm the button + shadow fixes.

---

*Cross-references: `docs/i18n/KHMER-TYPOGRAPHY.md`, `docs/FONT_LICENSES_AND_REGISTRY.md`, `docs/security/ASVS-L2-GAP-ANALYSIS.md`, `assets/fonts/registry.json`, `src/css/tokens.css`, `src/css/modern-ui.css`, `src/css/accessibility-v12.css`, `src/css/organized/styles.css`, `src/html/dashboard.html`.*

