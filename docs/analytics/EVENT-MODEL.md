# Analytics Event Model — v0.67.0+

**Roadmap:** [`ROADMAP-v0.54-to-v1.0.md` §6](../../upload/ROADMAP-v0.54-to-v1.0.md)
**Part 6 — Creator analytics & insights.**

This document is the single source of truth for which events the
E-invitation-website platform emits from the public invitation page, what
each event's payload contains, and how the data flows from the browser to
the dashboard.

---

## Design principles

1. **Privacy first.** No third-party trackers. No tracking cookies. All
   data is collected first-party and stored on the operator's own
   infrastructure.
2. **Honest numbers.** Unique opens are unique per recipient link (or per
   `session_id` for public links). Session duration is measured (from
   `invitation.view` to `invitation.view.end`), not estimated.
3. **No PII in event payloads.** `recipient_id` is an opaque guest id
   (not an email). The IP address is used to derive a coarse
   `country_code` and `device_type` and is **discarded immediately** —
   never stored.
4. **Bilingual reports.** Every metric label has EN + KH variants.
5. **Exportable.** Hosts can download their raw event data as CSV or JSON.
6. **Retention-limited.** Analytics events auto-prune after
   `EINVITE_ANALYTICS_RETENTION_DAYS` (default 365).

---

## Tables

### `analytics_sessions`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PRIMARY KEY | 128-bit hex (`session_id`) |
| `invitation_id` | TEXT NOT NULL | FK to `invitations.id` |
| `recipient_id` | TEXT | Nullable; opaque guest id |
| `started_at` | INTEGER NOT NULL | Unix ms |
| `ended_at` | INTEGER | NULL until `invitation.view.end` |
| `duration_ms` | INTEGER | `ended_at - started_at` |
| `max_scroll_pct` | INTEGER | 0..100 |
| `country_code` | TEXT | Coarse IP-derived, never raw IP |
| `referrer_domain` | TEXT | Normalized, NULL if direct |
| `device_type` | TEXT | `'mobile' \| 'tablet' \| 'desktop'` |
| `created_at` | INTEGER NOT NULL | Unix ms |

**Indexes:** `(invitation_id, started_at DESC)`, `(recipient_id)`.

### `analytics_events`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `session_id` | TEXT NOT NULL | FK to `analytics_sessions.id` |
| `invitation_id` | TEXT NOT NULL | Denormalized for fast per-invitation queries |
| `event_type` | TEXT NOT NULL | One of the 11 types below |
| `payload_json` | TEXT | Small JSON; capped at 1 KB |
| `created_at` | INTEGER NOT NULL | Unix ms |

**Indexes:** `(session_id)`, `(invitation_id, event_type, created_at DESC)`.

### `analytics_summary_daily`

Aggregated per-day rollup, built by the background job every 5 min.

| Column | Type |
|---|---|
| `invitation_id` | TEXT NOT NULL |
| `day` | TEXT NOT NULL (`'YYYY-MM-DD'` UTC) |
| `unique_sessions` | INTEGER NOT NULL |
| `total_views` | INTEGER NOT NULL |
| `avg_duration_ms` | INTEGER NOT NULL |
| `p95_duration_ms` | INTEGER NOT NULL |
| `rsvp_submitted` | INTEGER NOT NULL |
| `rsvp_abandoned` | INTEGER NOT NULL |
| `gallery_opens` | INTEGER NOT NULL |
| `album_uploads` | INTEGER NOT NULL |

**Primary key:** `(invitation_id, day)`.

---

## The 11 event types

| Event | When fired | Payload |
|---|---|---|
| `invitation.view` | The public page loads | `{invitation_id, recipient_id (nullable), session_id, referrer, viewport}` |
| `invitation.view.end` | Page unload or 30s of inactivity | `{session_id, duration_ms, scroll_depth_pct, max_scroll_pct}` |
| `invitation.gallery.open` | Guest opens the photo gallery | `{session_id}` |
| `invitation.rsvp.open` | Guest opens the RSVP form | `{session_id}` |
| `invitation.rsvp.submit` | Guest submits RSVP | `{session_id, status (yes/no/maybe)}` |
| `invitation.rsvp.abandon` | Guest opens RSVP but doesn't submit within session | `{session_id, last_field_touched}` |
| `invitation.link.click` | Guest clicks an external link | `{session_id, href (normalized domain only)}` |
| `invitation.signup.claim` | Guest claims a sign-up slot | `{session_id, sheet_id}` |
| `invitation.poll.vote` | Guest votes in a poll | `{session_id, poll_id}` |
| `invitation.album.upload` | Guest uploads a photo | `{session_id, size_bytes}` |
| `invitation.gift.claim` | Guest claims a gift | `{session_id, item_id}` |

**Validation rules:**

- `session_id` must be a hex string of length ≥ 32 (128-bit minimum). It
  is generated client-side as a random value stored in `sessionStorage`
  so it resets on tab close.
- `invitation_id` must exist in `invitations`.
- `event_type` must be one of the 11 listed above (others are dropped).
- `payload_json` is capped at 1 KB; longer payloads are truncated.

---

## Ingestion

### Route

```
POST /api/analytics/events
Content-Type: application/json
```

### Request body

```json
{
  "session_id": "0123456789abcdef0123456789abcdef",
  "invitation_id": "uuid-of-invitation",
  "recipient_id": "optional-opaque-guest-id",
  "events": [
    {"type": "invitation.view", "ts": 1695000000000,
     "payload": {"referrer": "https://facebook.com", "viewport": "mobile"}},
    {"type": "invitation.rsvp.open", "ts": 1695000012000, "payload": {}}
  ]
}
```

### Behavior

- Rate-limited to **60 batches/min per IP**.
- Validates `session_id` (hex ≥ 32 chars).
- Validates `invitation_id` exists.
- Upserts `analytics_sessions` if an `invitation.view` event is present.
- Inserts all events into `analytics_events`.
- If `invitation.view.end` is present, updates `analytics_sessions.ended_at`
  + `duration_ms` + `max_scroll_pct`.
- Returns **HTTP 204 No Content**.

### Client-side batching

The browser SDK batches events client-side:

- **Max 20 events per batch.**
- **Flush every 10 seconds.**
- **Flush on `visibilitychange` to `hidden`.**
- **Use `navigator.sendBeacon()` on unload** (so the browser doesn't cancel the request).
- **Use `fetch(..., {keepalive: true})` as a fallback** for browsers that don't support `sendBeacon`.

### IP handling

The IP address is used only to derive `country_code` (via the existing
geo-IP lookup, coarse only — country-level) and `device_type` (via
User-Agent parsing). It is then **discarded** — never persisted to disk,
never logged with the event.

---

## Session reconstruction

A background job runs every 5 minutes and:

1. **Closes idle sessions.** Any session whose latest event is older than
   30 minutes has `ended_at` set to `last_event_ts + 30 min` and
   `duration_ms` computed accordingly.
2. **Deletes spam sessions.** Sessions with no events in the last 24 hours
   are deleted. Active sessions (no `ended_at`) are never deleted — they
   fall under the close-idle path first.
3. **Aggregates daily summaries.** Builds / refreshes
   `analytics_summary_daily` rows for the day that just completed.

---

## Retention

Analytics events auto-prune after `EINVITE_ANALYTICS_RETENTION_DAYS`
(default 365). The prune job runs as part of the background session
reconstruction pass:

1. Delete from `analytics_events` older than the cutoff.
2. Delete from `analytics_sessions` older than the cutoff (only sessions
   with `ended_at` set; never delete active sessions).
3. Delete from `analytics_summary_daily` older than the cutoff day.

The prune count is logged to the audit log so the operator can confirm
the retention policy is working.

---

## Privacy controls

Hosts can:

- **Turn analytics off per invitation** (POST `/api/invitations/{id}/analytics/disable`).
  The public page then sends no events.
- **Purge all collected data** for an invitation (DELETE
  `/api/invitations/{id}/analytics`). Deletes every session + event + daily
  summary row.
- **Read the public privacy page** at `/privacy.html` explaining what's
  tracked and why.

See [`PRIVACY.md`](PRIVACY.md) for the full privacy policy.

---

## Export

Hosts can download their raw analytics data:

- `GET /api/invitations/{id}/analytics/export?format=csv|json`
- `GET /api/account/analytics/export?format=csv|json`

- **CSV:** UTF-8 BOM, RFC-4180 quoting. One row per session with joined
  event counts.
- **JSON:** `{invitation, sessions: [...], events: [...]}`.
- Streamed for large exports (chunked transfer encoding).
