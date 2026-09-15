# Hosted-Tier Onboarding Flow (Phase 5)

> **Goal (ROADMAP §8 acceptance):** *A host can sign up, pick a tier, and
> send an invitation without touching a server.*

This document specifies the 6-step onboarding flow for the hosted tier,
with bilingual EN+KH strings for every user-facing label. It reuses the
existing `/api/auth/register` + `/api/auth/passkeys/*` routes (V54), the
existing `/api/billing/checkout` route (V12, extended for Stripe in V54.8),
the existing workspace routes (`/api/workspaces`, V32), the existing
template picker (`src/js/template-picker-v22.js`), the existing editor
(`src/js/editor-core.js`), and the existing delivery abstraction
(`src/python/delivery_channels/`, V54.3).

Cross-references:
* `docs/ROADMAP.md` §8 — Phase 5 source of truth.
* `docs/hosted/STORAGE-TIERS.md` — tier limits + pricing.
* `docs/hosted/BILLING-INTEGRATION.md` — Stripe Checkout flow.
* `docs/hosted/CANVA-BRIDGE.md` — Canva import (optional step 4.5).

---

## 1. The six steps

```
┌─────────┐   ┌──────────┐   ┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
│ Step 1  │ → │ Step 2   │ → │ Step 3      │ → │ Step 4       │ → │ Step 5       │ → │ Step 6       │
│ Sign up │   │ Choose   │   │ Workspace   │   │ First        │   │ Send first   │   │ Custom       │
│         │   │ tier     │   │ creation    │   │ invitation   │   │ invitation   │   │ domain       │
└─────────┘   └──────────┘   └─────────────┘   └──────────────┘   └───────────────┘   └──────────────┘
   required     required        required         required           required            optional
```

Step 6 is optional and gated to Standard + Pro tiers (Free tier cannot use
custom domains — see `docs/hosted/STORAGE-TIERS.md` §1).

---

## 2. Step-by-step with bilingual labels

Every user-facing string has EN + KH variants per ROADMAP ground rule 5
(bilingual EN+KH). The frontend reads the user's `Accept-Language` header
or `localStorage.locale` to pick the variant at render time.

### Step 1 — Sign up

| Label | EN | KH |
|---|---|---|
| Page title | Create your account | បង្កើតគណនីរបស់អ្នក |
| Email field | Email address | អាសយដ្ឋានអ៊ីមែល |
| Password field | Password | ពាក្យសម្ងាត់ |
| Passkey button | Continue with passkey | បន្តជាមួយ Passkey |
| Submit | Create account | បង្កើតគណនី |
| Already have account | Already have an account? Sign in | មានគណនីរួចហើយ? ចូល |
| Terms | By creating an account you agree to the Terms of Service | ដោយបង្កើតគណនី អ្នកយល់ព្រមនឹងលក្ខខណ្ឌប្រើប្រាស់ |

**Backend (existing, no changes):** `POST /api/auth/register` (V54), or
`POST /api/auth/passkeys/login/complete` for passkey signup.

**Onboarding metric:** `signup.completed` — fired when `/api/auth/register`
returns 200 with `{user:{id, ...}}`.

### Step 2 — Choose tier

| Label | EN | KH |
|---|---|---|
| Page title | Choose your plan | ជ្រើសរើសគម្រោងរបស់អ្នក |
| Free card title | Free | ដោយឥតគិតថ្លៃ |
| Free card description | For trying out eInvite | សម្រាប់សាកល្បង eInvite |
| Free price | $0 / month | $0 / ខែ |
| Standard card title | Standard | ស្តង់ដារ |
| Standard card description | For hosts sending their first invitations | សម្រាប់ម្ចាស់ផ្ទះដែលផ្ញើការអញ្ជើញដំបូង |
| Standard price | $19 / month or $190 / year | $19 / ខែ ឬ $190 / ឆ្នាំ |
| Pro card title | Pro | Pro |
| Pro card description | For wedding planners and studios | សម្រាប់អ្នករៀបចំការអាពាហ៍ពិពាហ៍ និងស្ទូឌីយោ |
| Pro price | $99 / month or $990 / year | $99 / ខែ ឬ $990 / ឆ្នាំ |
| Nonprofit link | Are you a nonprofit? | តើអ្នកជាអង្គការមិនរកប្រាក់ចំណេញឬទេ? |
| Nonprofit tooltip | Verified nonprofits get 50% off Standard or Pro | អង្គការមិនរកប្រាក់ចំណេញដែលបានផ្ទៀងផ្ទាត់ ទទួលបាន 50% នៃ Standard ឬ Pro |
| Continue button (Free) | Continue with Free | បន្តជាមួយដោយឥតគិតថ្លៃ |
| Continue button (paid) | Continue to billing | បន្តទៅការទូទាត់ |
| No per-guest fees callout | No per-guest fees, ever. | គ្មានថ្លៃសិទ្ធិភ្ញៀវ គ្រប់ពេលវេលា។ |

**Backend (V54.8 scaffolding):**
* Free → no API call; frontend proceeds to step 3 with `tier='free'`.
* Standard/Pro → `POST /api/account/tier/upgrade` with
  `{tier:'standard'|'pro', billing_return_url}` → returns
  `{checkout_url, session_id, expires_at}` → redirect to Stripe Checkout
  → return to `/onboarding.html?step=3&session_id=...`.

**Onboarding metrics:**
* `tier.viewed` — when the user lands on step 2.
* `tier.selected` — fired with `{tier}` when the user clicks any continue
  button.
* `tier.checkout_started` — fired when `/api/account/tier/upgrade` returns
  the Stripe Checkout URL.
* `tier.checkout_completed` — fired when the Stripe webhook updates
  `users.tier` (server-side metric, joins with the client metric via
  `session_id`).

### Step 3 — Workspace creation

| Label | EN | KH |
|---|---|---|
| Page title | Set up your workspace | រៀបចំតំបន់ការងារ |
| Personal workspace label | Personal workspace | តំបន់ការងារផ្ទាល់ខ្លួន |
| Personal workspace description | Your private invitation workspace | តំបន់ការងារការអញ្ជើញផ្ទាល់ខ្លួន |
| Organization workspace label | Organization workspace (optional) | តំបន់ការងារស្ថាប័ន (ស្រេចចិត្ត) |
| Organization workspace description | For teams — share templates, guests, and analytics | សម្រាប់ក្រុម — ចែករំលែកគំរូ ភ្ញៀវ និងការវិភាគ |
| Org name field | Organization name | ឈ្មោះស្ថាប័ន |
| Org name placeholder | Acme Events | Acme Events |
| Skip org link | Skip — I'll add this later | រំលង — ខ្ញុំនឹងបន្ថែមពេលក្រោយ |
| Continue button | Continue | បន្ត |

**Backend (existing, V32):** `POST /api/workspaces` with `{name, plan}`.

The personal workspace is created automatically during `/api/auth/register`
(V54) — if it doesn't exist, this step creates it. The org workspace is
optional.

**Onboarding metric:** `workspace.created` with `{type: 'personal' | 'org'}`.

### Step 4 — First invitation

| Label | EN | KH |
|---|---|---|
| Page title | Create your first invitation | បង្កើតការអញ្ជើញដំបូងរបស់អ្នក |
| Template picker heading | Pick a template | ជ្រើសរើសគំរូ |
| Template picker subheading | Or start from blank | ឬចាប់ផ្តើមពីទទេ |
| Categories | Wedding · Birthday · Corporate · Holiday · Other | អាពាហ៍ពិពាហ៍ · ថ្ងៃកំណើត · ក្រុមហ៊ុន · ថ្ងៃឈប់សម្រាក · ផ្សេងៗ |
| Continue button (template picked) | Use this template | ប្រើគំរូនេះ |
| Continue button (blank) | Start blank | ចាប់ផ្តើមទទេ |
| Editor hint | Tip: use Cmd/Ctrl+S to save your work | គន្លឹះ៖ ប្រើ Cmd/Ctrl+S ដើម្បីរក្សាទុកការងារ |
| Save success toast | Saved | បានរក្សាទុក |
| Continue to send button | Continue to send | បន្តដើម្បីផ្ញើ |

**Backend (existing):**
* `POST /api/invitations` — creates the invitation with the picked
  template's `document_json` (or a blank document).
* `PUT /api/invitations/{id}` — autosave (debounced 1.5 s in the editor
  UI; the existing V23 command system).
* `POST /api/invitations/{id}/publish` — required before send (creates a
  V32 immutable publication row).

**Onboarding metrics:**
* `invitation.created` — fired on `POST /api/invitations` 201.
* `invitation.first_save` — fired on the first successful `PUT` (not the
  initial POST).
* `invitation.published` — fired on `POST /api/invitations/{id}/publish`.

#### Optional Step 4.5 — Canva import

If the host picks the "Import from Canva" template (only visible if
`EINVITE_CANVA_CLIENT_ID` is configured), the editor opens a Canva
import dialog instead of the template picker. See `docs/hosted/CANVA-BRIDGE.md`
§2.

| Label | EN | KH |
|---|---|---|
| Dialog title | Import from Canva | នាំចូលពី Canva |
| URL input | Canva design URL | URL រចនាសម្ព័ន្ធ Canva |
| URL placeholder | https://www.canva.com/design/DAE…/edit | https://www.canva.com/design/DAE…/edit |
| Upload alternative | Or upload a Canva export | ឬបង្ហោះការនាំចេញ Canva |
| Submit | Import | នាំចូល |

### Step 5 — Send first invitation

| Label | EN | KH |
|---|---|---|
| Page title | Send your invitation | ផ្ញើការអញ្ជើញរបស់អ្នក |
| Delivery channel label | How should we deliver it? | តើយើងគួរផ្ញើវាដោយរបៀបណា? |
| Email option | Email (default) | អ៊ីមែល (លំនាំដើម) |
| SMS option | SMS (requires configuration) | SMS (ត្រូវការការកំណត់) |
| WhatsApp option | WhatsApp (requires configuration) | WhatsApp (ត្រូវការការកំណត់) |
| Telegram option | Telegram (requires configuration) | Telegram (ត្រូវការការកំណត់) |
| Guest import heading | Add guests | បន្ថែមភ្ញៀវ |
| Guest import paste | Paste emails or phone numbers (one per line) | បិទភ្ជាប់អ៊ីមែល ឬលេខទូរស័ព្ទ (មួយក្នុងមួយបន្ទាត់) |
| Guest import file | Or upload a CSV | ឬបង្ហោះ CSV |
| Send button | Send invitation | ផ្ញើការអញ្ជើញ |
| Send success toast | Sent! | បានផ្ញើ! |
| Send success detail | Your invitation is on its way to {N} guests. | ការអញ្ជើញរបស់អ្នកកំពុងធ្វើដំណើរទៅ {N} ភ្ញៀវ។ |

**Backend (existing):**
* `POST /api/invitations/{id}/guests` (one or many) — creates guest rows
  with token hashes (V54).
* `POST /api/invitations/{id}/campaigns` — creates a delivery campaign
  with `channel='email'|'sms'|'whatsapp'|'telegram'` (V54.3 multi-channel
  delivery abstraction).
* `POST /api/invitations/{id}/campaigns/{cid}/dispatch` — fans out the
  invitation per channel.

**Onboarding metrics:**
* `send.guests_added` — fired with `{count}` when the first guest is
  created.
* `send.campaign_created` — fired with `{channel}`.
* `send.dispatched` — fired when `dispatch` returns 200. This is the
  terminal onboarding metric — the user has completed the core flow.

### Step 6 — (Optional) Custom domain setup

| Label | EN | KH |
|---|---|---|
| Page title | Set up your custom domain | រៀបចំដមែនផ្ទាល់ខ្លួន |
| Page subtitle | Available on Standard and Pro tiers | មាននៅលើជំនាន់ Standard និង Pro |
| Tier upsell (Free only) | Upgrade to Standard to use a custom domain | ផ្លាស់ប្តូរទៅ Standard ដើម្បីប្រើដមែនផ្ទាល់ខ្លួន |
| Domain input | Your domain | ដមែនរបស់អ្នក |
| Domain placeholder | events.yourname.com | events.yourname.com |
| Verify button | Verify DNS | ផ្ទៀងផ្ទាត់ DNS |
| DNS instructions heading | Add these DNS records | បន្ថែមកំណត់ត្រា DNS ទាំងនេះ |
| DNS record CNAME | CNAME record | កំណត់ត្រា CNAME |
| DNS record TXT | TXT record (verification) | កំណត់ត្រា TXT (ផ្ទៀងផ្ទាត់) |
| Pending state | Waiting for DNS propagation… | កំពុងរង់ចាំការផ្សព្វផ្សាយ DNS… |
| Success state | Verified! Your domain is live. | បានផ្ទៀងផ្ទាត់! ដមែនរបស់អ្នកបានចាប់ផ្តើម។ |
| Skip link | Skip — I'll set this up later | រំលង — ខ្ញុំនឹងរៀបចំពេលក្រោយ |

**Backend (existing V45):** the publishing-domains feature from V45
(`docs/V45_PUBLISHING_DOMAINS_CHANGELOG.md`) handles DNS verification +
custom-domain routing through the existing `invitations.custom_domain`
column. This step just exposes the V45 setup wizard in the onboarding flow.

**Onboarding metrics:**
* `custom_domain.started` — fired when the user enters a domain.
* `custom_domain.verified` — fired when DNS verification succeeds.

---

## 3. Onboarding conversion funnel

The dashboard tracks a 6-stage funnel:

| Stage | Source event | Notes |
|---|---|---|
| 1. Visit `/onboarding.html` | `onboarding.viewed` | Server logs the pageview with `?step=N` query. |
| 2. Sign up | `signup.completed` | Becomes a `users` row. |
| 3. Pick tier | `tier.selected` | Conversion here = picking any tier (Free included). |
| 4. Create workspace | `workspace.created` | Personal workspace auto-created at sign-up, so this fires for the org-workspace optional step. |
| 5. Create first invitation | `invitation.created` | |
| 6. Send first invitation | `send.dispatched` | Terminal metric. |

Funnel target (per ROADMAP §8 acceptance): a host can complete step 1 →
step 5 in under 5 minutes, no server touched.

---

## 4. Skip-and-return behavior

Every step has a "Skip — I'll do this later" exit:
* Skip Step 2 → user lands on Free tier; dashboard shows an "Upgrade your
  plan" callout on first login.
* Skip Step 3 → user gets only the personal workspace (created at signup);
  they can add an org workspace later via `/api/workspaces`.
* Skip Step 4 → user lands on the dashboard with the "Create your first
  invitation" CTA.
* Skip Step 5 → invitation stays in draft state; "Send" button in the
  editor completes step 5 later.
* Skip Step 6 → standard `einvite.local` subdomain is used; the user can
  set up a custom domain later via the dashboard's publishing-domains UI.

A returning user (session resumes) lands on the highest incomplete step.

---

## 5. Implementation notes

* **Frontend:** a new `src/js/onboarding-flow.js` (Phase 5 follow-up — not
  part of this V54.8 design round). It will be a small vanilla-JS module
  that drives the 6 steps via the existing template + dashboard structure
  (no new HTML pages — reuses `dashboard.html` and `editor.html`).
* **Bilingual strings:** all user-facing labels above are stored in
  `src/js/i18n/onboarding-strings.js` (Phase 5 follow-up) with the same
  EN/KH dual-key pattern used by `signup-sheets.js`, `polls.js`, and
  `delivery-dialog.js` (V54.3).
* **Server-side:** the only new endpoints are `GET /api/account/tier` and
  `POST /api/account/tier/upgrade` (both scaffolded in V54.8 — see
  `src/python/server.py`).

## 6. Change history

| Version | Date | Change |
|---|---|---|
| V54.8 | 2026-08-14 | Initial design: 6-step flow with bilingual EN+KH labels + conversion funnel + skip-and-return behavior. |
