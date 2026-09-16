# Analytics Privacy — v0.68.3+

**Roadmap:** [`ROADMAP-v0.54-to-v1.0.md` §6.8](../../upload/ROADMAP-v0.54-to-v1.0.md)

This document explains what the E-invitation-website platform's
first-party analytics feature collects, why it collects it, how long it
keeps it, and what control the host has over the data.

A public, user-facing summary of this policy is served at `/privacy.html`.

---

## What we collect (and what we don't)

### We DO collect

| Data point | Why | Stored as | Retention |
|---|---|---|---|
| Session id | To group events from a single page visit into one session | `analytics_sessions.id` (128-bit random hex) | 365 days (configurable) |
| Invitation id | To attribute the visit to the right invitation | `analytics_sessions.invitation_id` | 365 days |
| Recipient id (opaque) | To count unique opens per recipient link — only when the visitor used a personalized guest link | `analytics_sessions.recipient_id` (opaque; not an email) | 365 days |
| Session start/end time | To measure how long the guest engaged | `started_at`, `ended_at`, `duration_ms` | 365 days |
| Max scroll depth | To measure how far down the page the guest read | `max_scroll_pct` (0..100) | 365 days |
| Country (coarse) | To show "where in the world are my guests" | `country_code` (ISO-3166 alpha-2) | 365 days |
| Referrer domain | To show "where traffic is coming from" | `referrer_domain` (bare hostname; full URL discarded) | 365 days |
| Device type | To show the mobile/tablet/desktop split | `device_type` (`mobile`/`tablet`/`desktop`) | 365 days |
| Event type + small payload | To power the funnel and the engagement metrics | `analytics_events.event_type`, `payload_json` (≤1 KB) | 365 days |

### We DO NOT collect

- **IP addresses.** The IP is used only to derive `country_code` and
  `device_type`, then **discarded immediately** — never persisted, never
  logged alongside the event.
- **Cookies for tracking.** No analytics cookies. No cross-site tracking.
  No third-party trackers. No fingerprinting.
- **Email addresses or names** in event payloads. The `recipient_id` is
  an opaque guest id (a UUID), not an email. The host's guest-list
  (which contains emails) is kept separate from analytics.
- **Precise location.** Country only — never city, never GPS.
- **User behavior on other sites.** The referrer is normalized to a
  bare hostname (e.g. `facebook.com`) and the full URL is discarded.
- **Device serial numbers, advertising IDs, or any other persistent
  cross-site identifier.**

---

## Who can see the data

- The **host** of the invitation (the account that owns it).
- The platform **operator** (server administrator) — for retention,
  backup, and abuse-prevention purposes only.
- **Nobody else.** Data is never sold, shared, or transmitted to third
  parties.

---

## How long we keep it

- **Default:** 365 days from the event timestamp.
- **Configurable:** The operator sets `EINVITE_ANALYTICS_RETENTION_DAYS`
  in the environment. Setting it to `0` is treated as `1` (one day
  minimum) to avoid accidentally deleting the entire table on boot.
- **Auto-prune:** A background job runs every 5 minutes and deletes
  events older than the cutoff. Active sessions (those without an
  `ended_at`) are never pruned — they're closed first by the close-idle
  pass.
- **Prune audit:** The count of rows pruned per pass is written to the
  `audit_events` table so the operator can confirm the policy is
  working.

---

## Host controls

### Turn analytics off per invitation

```
POST /api/invitations/{id}/analytics/disable
```

Body: `{"enabled": false}`. Sets `invitations.analytics_enabled = 0`.
The public invitation page checks this flag before firing any events —
if disabled, the browser SDK does nothing.

Re-enable with `{"enabled": true}`.

### Purge all collected data

```
DELETE /api/invitations/{id}/analytics
```

Deletes every `analytics_sessions` + `analytics_events` +
`analytics_summary_daily` row for the invitation. This is irreversible
and immediate.

The invitation itself is not affected — only its analytics data.

### Export raw data

```
GET /api/invitations/{id}/analytics/export?format=csv|json
GET /api/account/analytics/export?format=csv|json
```

See [`EVENT-MODEL.md`](EVENT-MODEL.md#export) for the export format.

---

## Public privacy page

A user-facing privacy page is served at `/privacy.html`. It explains —
in plain language, bilingual EN + KH — what's tracked and why. The page
is intentionally short and free of legalese.

---

## Bilingual labels (EN + KH)

Every user-facing string the analytics feature surfaces has both an
English and a Khmer (ភាសាខ្មែរ) variant. The active locale is resolved
client-side via `document.documentElement.lang` or
`window.EInviteI18N?.getLocale?.()`, defaulting to English.

Examples:

| EN | KH |
|---|---|
| Total views | ចំនួនមើលសរុប |
| Unique recipients | ភ្ញៀវផ្ទាល់ខ្លួន |
| Average time on page | ពេលវេលាមធ្យមនៅលើទំព័រ |
| RSVP conversion | អត្រាឆ្លើយតប RSVP |
| Drop-off funnel | ស្ថិតិការបោះបង់ |
| Top referrers | ប្រភពដែលនាំមក |
| Scroll depth | ជម្រៅអាន |
| Device split | ប្រភេទឧបករណ៍ |
| Country | ប្រទេស |
| Views — last 30 days | ចំនួនមើល — ៣០ ថ្ងៃចុងក្រោយ |
| RSVP breakdown | ស្ថិតិ RSVP |
| Disable analytics | បិទស្ថិតិ |
| Delete analytics data | លុបទិន្នន័យស្ថិតិ |
| Export as CSV | នាំចេញជា CSV |
| Live activity | សកម្មភាពផ្ទាល់ |
| active sessions | សម័យសកម្ម |
| last activity | សកម្មភាពចុងក្រោយ |
| conversion | អត្រាប្រែប្រួល |
| last activity | សកម្មភាពចុងក្រោយ |

---

## Compliance

This feature is designed to be compliant with:

- **GDPR** — no PII in event payloads; IP discarded; data retention
  bounded; host can delete on request; consent via the public privacy
  page (the host chooses whether to enable analytics per invitation).
- **CCPA** — first-party only; no sale of data; right to delete
  honored via the purge endpoint.
- **PECR (UK)** — no analytics cookies; no third-party trackers.

For deployment-specific compliance questions, contact the operator
hosting your instance.
