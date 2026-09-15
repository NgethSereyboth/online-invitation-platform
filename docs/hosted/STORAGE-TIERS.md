# Storage-Tier Pricing (Phase 5 — Optional Hosted Tier)

> **Source of truth for tier limits, pricing, and upgrade/downgrade flows.**
> Cross-references: `docs/ROADMAP.md` §8 (Phase 5), `docs/hosted/BILLING-INTEGRATION.md`,
> `docs/hosted/ONBOARDING-FLOW.md`, `docs/hosted/CANVA-BRIDGE.md`.

**Core principle (ROADMAP §8):** *Storage-tier pricing with no per-guest fees.
This is the single clearest wedge against competitors.*

| Competitor | Model | eInvite advantage |
|---|---|---|
| Paperless Post | Per-guest coins ($0.50–$1.44/guest) | **No per-guest fees** |
| Evite | Free + ads; Pro $249.99/yr | **No ads; self-hostable** |
| Zola | Wedding suite; formal invites are print | **True digital invitations** |
| Canva | Design tool; no event management | **Event management included** |

A host can send 10 guests or 10 000 guests and pay the **same storage-tier
price**. The only variable cost is storage overage, billed at cost.

---

## 1. The Three Tiers

| Tier | Storage | Active invitations | Guests / invitation | Watermark | Custom domains | Workspaces | Support | SLA |
|---|---|---|---|---|---|---|---|---|
| **Free** | 1 GB | 5 | 100 | Yes (on exports) | 0 | 1 (personal) | Community | Best-effort |
| **Standard** | 25 GB | 50 | 1 000 | No | 1 | 1 (personal) | Priority (1 business day) | Best-effort |
| **Pro** | 250 GB | Unlimited | 10 000 | No | 10 | 5 (personal + 4 org) | Dedicated (same-day) | 99.9 % monthly uptime |

### Tier semantics

* **Active invitation** — an invitation whose `archived=0` AND `deleted_at IS NULL`
  AND `purge_at IS NULL` in the `invitations` table. Archived invitations do not
  count against the limit (they are read-only history).
* **Guests / invitation** — distinct rows in `guests` for a single
  `invitation_id`. Re-imports that upsert by email/phone do not double-count.
* **Storage used** — `SUM(size)` over `stored_objects` rows where
  `owner_id = users.id` AND `processing_state = 'ready'` AND `ref_count > 0`
  AND `quarantine_state = 'released'`. This matches the existing
  `plan_usage()` helper at `src/python/server.py` L4052.
* **Workspace** — a V32 `workspaces` row where the user has role `owner`.
  Personal workspace is always present. Org workspaces are additional seats.

---

## 2. Pricing

| Tier | Monthly | Annual (2 months free) | Effective monthly (annual) |
|---|---|---|---|
| Free | $0 | $0 | $0 |
| Standard | $19 / mo | $190 / yr | $15.83 / mo |
| Pro | $99 / mo | $990 / yr | $82.50 / mo |

### Storage overage

Any tier may exceed its storage quota. Overage is metered at cost:

> **$0.10 / GB / month** (prorated daily, billed monthly via Stripe Usage
> Records API — see `docs/hosted/BILLING-INTEGRATION.md` §4).

Examples:
* Free user with 1.5 GB = 0.5 GB overage × $0.10 = $0.05 / mo.
* Standard user with 30 GB = 5 GB overage × $0.10 = $0.50 / mo.
* Pro user with 250 GB = no overage. Pro user with 350 GB = 100 GB × $0.10 = $10 / mo.

### No per-guest fees — anywhere

* No "coins" model (Paperless Post's $0.50–$1.44/guest is explicitly rejected).
* No per-send fees (Evite's ad-supported tier is explicitly rejected).
* No per-RSVP fees.
* No per-template fees (templates are user-owned and unlimited within tier).

---

## 3. Nonprofit discount (50 % off)

Verified nonprofits receive **50 % off** Standard or Pro, indefinitely, on
both monthly and annual billing.

| Tier | Monthly (nonprofit) | Annual (nonprofit) |
|---|---|---|
| Standard | $9.50 / mo | $95 / yr |
| Pro | $49.50 / mo | $495 / yr |

### Verification

A nonprofit submits:

1. **EIN** (US 501(c)(3)) or **registration number** (non-US equivalent —
   e.g. UK Charity Commission number, Australian ACNC, Cambodian Ministry
   of Interior registration).
2. **Supporting documentation** — IRS determination letter (US), Charity
   Commission registration certificate (UK), or equivalent official letter
   on letterhead.

### Review process

* Submission goes to `POST /api/account/tier/nonprofit-apply` (Phase 5.1
  scaffold — out of scope for this design round; see `BILLING-INTEGRATION.md`
  §6 for the route sketch).
* Maintainer reviews within 5 business days. Approved nonprofits receive
  a Stripe coupon code redeemable at checkout.
* Re-verification every 24 months. Lapsed nonprofits revert to full price
  at end of the current billing period (NOT mid-period — see §5 below).
* Self-hosted users (running eInvite on their own infrastructure) receive
  Free-tier limits automatically — this is the ultimate nonprofit escape
  hatch, and it aligns with ROADMAP §8's "self-hosted, community-friendly
  positioning".

---

## 4. Tier upgrade / downgrade flow

### Upgrade (Free → Standard, Free → Pro, Standard → Pro)

1. User clicks "Upgrade" in the dashboard.
2. Frontend calls `POST /api/account/tier/upgrade` with
   `{tier, billing_return_url}`.
3. Backend creates a Stripe Checkout session (mode=`subscription`,
   `line_items` = the target tier's price ID, `metadata.user_id` and
   `metadata.tier` for the webhook to consume).
4. Backend returns `{checkout_url, session_id, expires_at}`.
5. User is redirected to Stripe, completes payment, redirected back to
   `billing_return_url` with `?checkout=success&session_id=...`.
6. Stripe fires `checkout.session.completed` webhook →
   `POST /api/billing/webhook/stripe` → backend updates
   `users.tier = 'standard' | 'pro'` AND `users.tier_expires_at = <period end>`.
7. User's quota is immediately upgraded (no waiting for next period).

### Downgrade (Pro → Standard, Pro → Free, Standard → Free)

1. User calls `POST /api/account/tier/upgrade` with the new (lower) tier.
   The endpoint accepts downgrades too — the name reflects user intent.
2. Backend records the scheduled downgrade in Stripe (via
   `stripe.Subscription.modify(proration_behavior='none')` — no refund for
   unused time, change takes effect at period end).
3. The user keeps Pro limits until `tier_expires_at`.
4. At period end, Stripe fires `customer.subscription.updated` with the new
   price → backend updates `users.tier` AND `users.tier_expires_at`.
5. **Storage preservation guarantee:** if the new tier's storage quota is
   exceeded, the user is NOT immediately blocked. Their existing data is
   preserved. They accrue storage-overage charges at $0.10 / GB / mo until
   they delete content or upgrade again.

### Cancellation

1. User clicks "Cancel subscription" in the dashboard.
2. Backend calls `stripe.Subscription.delete(prorate=False)` — subscription
   ends at the current period's end.
3. Stripe fires `customer.subscription.deleted` webhook → backend sets
   `users.tier = 'free'` AND `users.tier_expires_at = <period end>`.
4. At period end, user is on Free tier. Existing invitations stay accessible
   (read-only if they exceed Free's 5-invitation limit).
5. **30-day data grace period:** if the user is over Free's 1 GB storage
   quota at period end + 30 days, oldest archived assets are deleted until
   usage is within quota. Email warnings are sent at day 23 (7 days before),
   day 27 (3 days before), day 29 (1 day before).
6. User can re-subscribe at any time during the 30-day window and the data
   grace period is cancelled — no data is deleted.

---

## 5. Why this model beats the competitors

| Competitor weakness | eInvite answer |
|---|---|
| Paperless Post: 200-guest wedding = $100–$288 in coins. | eInvite: 200-guest wedding on Standard = **$19 flat**. |
| Evite: free tier is ad-supported; guests see banner ads. | eInvite: free tier is ad-free (with watermark on exports only). |
| Evite Pro: $249.99 / year, no event management beyond invites. | eInvite Pro: $990 / year, includes RSVP, sign-up sheets, polls, photo album, AI agent, plugin marketplace. |
| Canva: per-seat pricing for teams; no event-management primitives. | eInvite Pro: 5 workspaces included; full event management (guests, RSVP, deliveries, analytics). |
| All four: no self-host option. | eInvite: source-open, runs on a $5/month VPS. The ultimate tier-cap escape hatch. |

---

## 6. Relationship to the legacy `users.plan` column

The existing `users.plan` column (added in V12) uses values `free` / `creator` /
`studio`. Phase 5 introduces a parallel `users.tier` column with values
`free` / `standard` / `pro`.

The two columns are reconciled at runtime:

| `users.plan` (legacy) | `users.tier` (Phase 5) | Reconciliation |
|---|---|---|
| `free` | `free` | Free tier — identical. |
| `creator` | `standard` | `creator` users are auto-upgraded to `standard` on first login post-V54.8. |
| `studio` | `pro` | `studio` users are auto-upgraded to `pro` on first login post-V54.8. |

`users.plan` is kept read-only for backwards compatibility (existing admin
tooling, the `admin_update_user_plan` endpoint, the `plan_usage` helper). New
Phase 5 code reads `users.tier` exclusively. The legacy column will be dropped
in V56 (per the deprecation policy in `VERSION_HISTORY.md`).

---

## 7. Acceptance criteria (per ROADMAP §8)

* [ ] A host can sign up, pick a tier, and send an invitation without touching
      a server.
* [ ] No per-guest fees anywhere in the flow.
* [ ] Canva import/export works for at least the common template shapes (see
      `docs/hosted/CANVA-BRIDGE.md`).
* [ ] Tier upgrade takes effect immediately; downgrade takes effect at
      period end (no mid-period data loss).
* [ ] Storage overage is metered daily and billed monthly via Stripe.
* [ ] Verified nonprofits receive 50 % off Standard or Pro.

---

## 8. Cross-references

* `docs/ROADMAP.md` §8 — Phase 5 source of truth.
* `docs/hosted/BILLING-INTEGRATION.md` — Stripe Checkout + Subscription +
  Usage Record API + webhook handling.
* `docs/hosted/ONBOARDING-FLOW.md` — 6-step signup → tier → first-send flow
  with bilingual EN+KH labels.
* `docs/hosted/CANVA-BRIDGE.md` — Import/export design (Phase 5.1 import,
  Phase 5.2 export).
* `src/python/server.py` — `GET /api/account/tier`, `POST /api/account/tier/upgrade`,
  `POST /api/billing/webhook/stripe` (scaffolding added in V54.8).
* `src/python/server.py` `PLAN_LIMITS` map (legacy, kept for `users.plan`)
  and the new `STORAGE_TIER_LIMITS` map (Phase 5, used by `/api/account/tier`).

## 9. Change history

| Version | Date | Change |
|---|---|---|
| V54.8 | 2026-08-14 | Initial design: 3 tiers (Free / Standard / Pro) + nonprofit discount + storage overage + upgrade/downgrade flow. |
