# Billing Integration Design (Phase 5)

> **Reuses the existing billing adapter** at `src/python/server.py` L184–L193
> (config: `BILLING_WEBHOOK_SECRET`, `BILLING_CHECKOUT_ENDPOINT`,
> `BILLING_API_KEY`, `BILLING_PROVIDER_NAME`, `BILLING_CURRENCY`,
> `BILLING_PLAN_PRICES`) and the existing routes `/api/billing/status`,
> `/api/billing/checkout`, `/api/billing/webhook` (L3767–L3864).
>
> Phase 5 extends this adapter with Stripe-specific subscription + metered
> billing. The existing provider-neutral routes are kept for backwards
> compatibility (the V12 design allowed any payment processor behind a
> generic HMAC-signed webhook contract).

Cross-references:
* `docs/ROADMAP.md` §8 — Phase 5 source of truth.
* `docs/hosted/STORAGE-TIERS.md` — tier limits + pricing + overage rate.
* `docs/hosted/ONBOARDING-FLOW.md` — where the checkout flow sits in signup.
* `src/python/server.py` — existing `/api/billing/*` (V12) + new
  `/api/account/tier/*` + `/api/billing/webhook/stripe` (V54.8).

---

## 1. Why Stripe

| Requirement | Stripe support |
|---|---|
| Subscriptions with monthly + annual cadence | ✅ `stripe.Subscription` with `interval: 'month' \| 'year'` |
| Webhooks (signed, idempotent) | ✅ `Stripe-Signature` header, `t=...,v1=...` HMAC-SHA256, idempotent via event ID |
| Metered billing (storage overage) | ✅ `stripe.Subscription` with `billing_scheme: 'per_unit'` + `Usage Record API` |
| Tier upgrades + downgrades mid-cycle | ✅ `stripe.Subscription.modify` with `proration_behavior` |
| Customer portal (let users self-cancel) | ✅ `stripe.BillingPortal.Session` |
| Coupons (for nonprofit 50 % off) | ✅ `stripe.Coupon` + `stripe.PromotionCode` |
| Tax compliance (Stripe Tax, optional) | ✅ available, not required for V54.8 |
| Webhook signature verification in Python | ✅ `stripe.Webhook.construct_event` (official `stripe` Python SDK) |

Alternatives considered:
* **Paddle** — merchant-of-record (handles VAT/sales tax globally), but
  per-transaction fee is higher and the metered-billing story is weaker.
  Suitable if tax-compliance burden becomes the bottleneck.
* **Lemon Squeezy** — same merchant-of-record model; smaller plugin
  ecosystem. Suitable for very-small-scale launches.
* **Direct card processing via Stripe Elements + PaymentIntents** — more
  control, more PCI surface (we'd handle card data on the server).
  Rejected — Stripe Checkout keeps card data on Stripe's PCI-DSS scope,
  not ours.

**Decision:** Stripe Checkout + Subscriptions + metered Usage Records.
The existing `/api/billing/*` adapter is preserved for any future swap.

---

## 2. Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Browser    │         │  eInvite server  │         │  Stripe      │
│             │         │  (server.py)     │         │              │
└──────┬──────┘         └────────┬─────────┘         └──────┬───────┘
       │                         │                          │
       │ 1. POST /api/account/tier/upgrade                  │
       │    {tier:'standard', billing_return_url}           │
       ├────────────────────────►│                          │
       │                         │ 2. stripe.checkout.Session.create
       │                         │    mode='subscription'   │
       │                         │    line_items=[{price: <STANDARD_PRICE_ID>}]│
       │                         │    metadata.user_id = ...│
       │                         │    metadata.tier = 'standard'│
       │                         ├─────────────────────────►│
       │                         │  3. {url, session_id, expires_at}│
       │                         │◄─────────────────────────┤
       │ 4. {checkout_url, session_id, expires_at}          │
       │◄────────────────────────┤                          │
       │                         │                          │
       │ 5. window.location = checkout_url                  │
       ├──────────────────────────────────────────────────►│
       │                         │                          │
       │ 6. User completes payment on Stripe-hosted page   │
       │                         │                          │
       │ 7. Stripe fires checkout.session.completed webhook │
       │                         │◄──────────────────────────┤
       │                         │ 8. POST /api/billing/webhook/stripe │
       │                         │    signature verification via       │
       │                         │    stripe.Webhook.construct_event    │
       │                         │    UPDATE users SET tier='standard',│
       │                         │    tier_expires_at=<period end>      │
       │                         │                          │
       │ 9. Redirect to billing_return_url?checkout=success  │
       │◄──────────────────────────────────────────────────┤
       │                         │                          │
```

---

## 3. Subscription model

### 3.1 Stripe product + price setup (manual, one-time)

The maintainer creates these in the Stripe Dashboard once:

| Product | Price ID env var | Amount | Currency | Interval |
|---|---|---|---|---|
| eInvite Standard (monthly) | `EINVITE_STRIPE_PRICE_STANDARD_MONTH` | $19.00 | USD | month |
| eInvite Standard (annual) | `EINVITE_STRIPE_PRICE_STANDARD_YEAR` | $190.00 | USD | year |
| eInvite Pro (monthly) | `EINVITE_STRIPE_PRICE_PRO_MONTH` | $99.00 | USD | month |
| eInvite Pro (annual) | `EINVITE_STRIPE_PRICE_PRO_YEAR` | $990.00 | USD | year |
| eInvite Storage Overage | `EINVITE_STRIPE_PRICE_OVERAGE_GB` | $0.10 | USD | month (metered) |

The overage price is a **metered** price (not per-unit). Stripe's metered
subscriptions report usage via the Usage Record API — see §4.

### 3.2 Customer creates an account (existing flow)

`POST /api/auth/register` creates the `users` row with
`tier='free'` (default in the schema) and `tier_expires_at=NULL`. The user
has no Stripe customer ID yet.

On first checkout, `stripe.Customer.create({email: user.email})` is
called and the resulting `stripe_customer_id` is stored in a new
`users.stripe_customer_id` column (Phase 5 schema migration).

### 3.3 Customer picks a tier → Stripe Checkout

`POST /api/account/tier/upgrade {tier, billing_return_url}`:

```python
import stripe  # pip install stripe (deploy-time dependency)

stripe.api_key = EINVITE_STRIPE_SECRET_KEY
price_id = {
    "standard": EINVITE_STRIPE_PRICE_STANDARD_MONTH if annual else EINVITE_STRIPE_PRICE_STANDARD_YEAR,
    "pro":      EINVITE_STRIPE_PRICE_PRO_MONTH      if annual else EINVITE_STRIPE_PRICE_PRO_YEAR,
}[tier]

session = stripe.checkout.Session.create(
    mode="subscription",
    customer=user.stripe_customer_id or None,  # creates new customer if None
    customer_email=user.email if not user.stripe_customer_id else None,
    line_items=[{"price": price_id, "quantity": 1}],
    # metered overage line item — quantity is always 1; Stripe bills on
    # reported usage at period end:
    line_items=[{"price": price_id, "quantity": 1},
                {"price": EINVITE_STRIPE_PRICE_OVERAGE_GB, "quantity": 1}],
    metadata={"user_id": user.id, "tier": tier},
    subscription_data={"metadata": {"user_id": user.id, "tier": tier}},
    success_url=billing_return_url + "?checkout=success&session_id={CHECKOUT_SESSION_ID}",
    cancel_url=billing_return_url + "?checkout=cancelled",
)
return {"checkout_url": session.url, "session_id": session.id, "expires_at": session.expires_at}
```

The frontend redirects to `session.url`.

### 3.4 Stripe webhook → `/api/billing/webhook/stripe`

This is a NEW route (V54.8 scaffolding), separate from the existing
provider-neutral `/api/billing/webhook`. The new route:

1. Reads the raw body + `Stripe-Signature` header.
2. Calls `stripe.Webhook.construct_event(payload, signature, endpoint_secret)`.
   The `endpoint_secret` comes from a new env var
   `EINVITE_STRIPE_WEBHOOK_SECRET` (distinct from
   `EINVITE_BILLING_WEBHOOK_SECRET` which protects the provider-neutral
   route).
3. Stores the event in the existing `billing_events` table (idempotent
   via the Stripe event ID).
4. Dispatches on `event.type`:
   * `checkout.session.completed` → reads `event.data.object.metadata.user_id`
     and `metadata.tier`; updates `users.tier` + `users.tier_expires_at`
     from `event.data.object.subscription`'s `current_period_end`.
   * `customer.subscription.updated` → reads `event.data.object.metadata.user_id`
     + `metadata.tier` (or the price ID lookup); updates
     `users.tier` + `users.tier_expires_at`. **Proration:** if the price
     changed (Pro → Standard), the new tier is applied at the next
     period end (already handled by Stripe via
     `proration_behavior='none'` at subscription modify time).
   * `customer.subscription.deleted` → sets `users.tier='free'` +
     `users.tier_expires_at=<period_end_from_event>`. (Cancellation
     always takes effect at period end per Stripe.)
5. Writes an audit event via `self.audit("billing.plan_changed", ...)` —
   same pattern as the existing route.

### 3.5 Tier downgrade at end of period

`POST /api/account/tier/upgrade` accepts a *lower* tier too. The handler
calls:

```python
stripe.Subscription.modify(
    subscription_id,
    items=[{
        "id": subscription_item_id,
        "price": new_price_id,
    }],
    proration_behavior="none",  # NO refund, change at period end
)
```

Stripe fires `customer.subscription.updated` at period end with the new
price ID. The webhook updates `users.tier` to the new (lower) value.

### 3.6 Cancellation

User clicks "Cancel subscription" in the Stripe Customer Portal (link
generated via `stripe.billing_portal.Session.create(customer=...,
return_url=...)`). Stripe fires `customer.subscription.deleted` at the
end of the current period.

The webhook sets `users.tier='free'` + `users.tier_expires_at=<period_end>`.
At period end, the user is on Free. The **30-day data grace period** (see
`docs/hosted/STORAGE-TIERS.md` §4) starts: oldest archived assets are
deleted at day 30 if the user is over Free's 1 GB quota.

Email warnings are sent at:
* Day 23 (7 days before deletion): "Your data will be deleted in 7 days"
* Day 27 (3 days before): "Your data will be deleted in 3 days"
* Day 29 (1 day before): "Final notice — your data will be deleted tomorrow"

Re-subscribing at any time during the 30-day window cancels the grace
period — no data is deleted.

---

## 4. Metered billing — storage overage

### 4.1 Daily usage computation

A cron job (or APScheduler in long-running server mode) runs daily at
00:30 UTC:

```python
def compute_storage_usage():
    """Sum ObjectStorage usage per workspace, write to users.storage_used_bytes."""
    with connect() as db:
        rows = db.execute("""
            SELECT owner_id, SUM(size) total_bytes
            FROM stored_objects
            WHERE processing_state='ready' AND ref_count>0
              AND quarantine_state='released'
              AND owner_id IS NOT NULL
            GROUP BY owner_id
        """).fetchall()
        for row in rows:
            db.execute(
                "UPDATE users SET storage_used_bytes=? WHERE id=?",
                (int(row["total_bytes"] or 0), row["owner_id"]),
            )
```

The `storage_used_bytes` column (BIGINT, default 0) is added in the V54.8
schema migration.

### 4.2 Monthly Stripe Usage Record submission

At the start of each calendar month (or on the user's subscription
renewal date — the cron aligns with the subscription's `current_period_end`):

```python
def report_storage_overage_to_stripe(user_id):
    user = get_user(user_id)
    if not user.stripe_customer_id or not user.stripe_subscription_id:
        return  # Free tier or no subscription yet
    tier_limit = STORAGE_TIER_LIMITS[user.tier]["storageBytes"]
    overage_bytes = max(0, user.storage_used_bytes - tier_limit)
    overage_gb = overage_bytes / (1024 ** 3)
    # Find the metered subscription item ID (the overage line item from §3.3)
    overage_item_id = find_overage_subscription_item_id(user.stripe_subscription_id)
    stripe.UsageRecord.create(
        subscription_item=overage_item_id,
        quantity=int(overage_gb),  # round down — favors the customer
        timestamp=int(time.time()),
        action="set",  # overwrite any prior record for this period
    )
```

Stripe bills `quantity × $0.10` at the end of the billing period. If
`overage_gb = 0`, Stripe bills $0 for the overage line.

### 4.3 Why per-GB and not per-byte

Stripe's metered billing uses integer quantities. $0.10 / GB / month
with integer-GB granularity is the smallest sensible unit (per-MB would
need 1024× the API calls and still rounds to <$0.01 increments — below
Stripe's minimum billing unit).

---

## 5. Schema migration (V54.8)

### 5.1 New `users` columns

| Column | Type | Default | Notes |
|---|---|---|---|
| `tier` | TEXT NOT NULL | `'free'` | `free` / `standard` / `pro`. Parallel to existing `plan` column (see `STORAGE-TIERS.md` §6). |
| `tier_expires_at` | INTEGER (BIGINT) | NULL | Unix epoch ms when the current tier ends. NULL = no expiry (Free tier). |
| `storage_used_bytes` | INTEGER (BIGINT) | 0 | Updated by daily cron (§4.1). |
| `stripe_customer_id` | TEXT | NULL | Set on first successful checkout. |
| `stripe_subscription_id` | TEXT | NULL | Set when the subscription is created. |
| `tier_scheduled_change` | TEXT | NULL | JSON `{tier, effective_at}` for scheduled downgrades (optional — Stripe's own scheduling is the source of truth; this is a denormalized hint for the dashboard UI). |

### 5.2 SQLite path

```python
# In connect_sqlite() schema block (src/python/server.py ~L1255):
if "tier" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN tier TEXT NOT NULL DEFAULT 'free'")
if "tier_expires_at" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN tier_expires_at INTEGER")
if "storage_used_bytes" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN storage_used_bytes INTEGER NOT NULL DEFAULT 0")
if "stripe_customer_id" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
if "stripe_subscription_id" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT")
```

### 5.3 PostgreSQL path

Additive `ALTER TABLE` in `docs/postgres_schema.sql`:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS tier_expires_at BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS storage_used_bytes BIGINT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT;
```

### 5.4 Reconciliation backfill (one-time)

```python
def backfill_tier_from_plan():
    """V54.8 one-time backfill: copy plan values to tier."""
    mapping = {"free": "free", "creator": "standard", "studio": "pro"}
    with connect() as db:
        for plan, tier in mapping.items():
            db.execute("UPDATE users SET tier=? WHERE tier IS NULL OR tier='' AND plan=?", (tier, plan))
            # Also set tier for users whose tier defaults to 'free' but plan is paid:
            db.execute("UPDATE users SET tier=? WHERE plan=? AND tier='free'", (tier, plan))
```

---

## 6. Nonprofit application route (sketch — Phase 5.1 follow-up)

`POST /api/account/tier/nonprofit-apply`:

* Body: `{organization_name, registration_number, registration_country,
  documentation_url (signed S3 PUT URL or pre-existing upload),
  contact_email}`.
* Stores row in new `nonprofit_applications` table (id, user_id,
  organization_name, registration_number, registration_country,
  documentation_object_key, status='pending', submitted_at, decided_at,
  decided_by, decision_note).
* Notifies the maintainer via email (existing SMTP pipeline).
* Maintainer reviews in admin UI (new route `POST /api/admin/nonprofit-applications/{id}/decide`).
* Approval generates a Stripe coupon (50% off Standard or Pro, forever) via
  `stripe.Coupon.create(percent_off=50, duration='forever')` and emails
  the coupon code to `contact_email`.

This is **out of scope for V54.8 scaffolding** — only the storage-tier
doc designates the discount; the application route is Phase 5.1 work.

---

## 7. Configuration (deploy-time)

Add to `deploy/.env.example`:

```
# ── Phase 5 — Hosted tier (V54.8) ──────────────────────────────────────
# Stripe integration (Stripe SDK required: pip install stripe)
EINVITE_STRIPE_SECRET_KEY=
EINVITE_STRIPE_PUBLISHABLE_KEY=
EINVITE_STRIPE_WEBHOOK_SECRET=
EINVITE_STRIPE_PRICE_STANDARD_MONTH=
EINVITE_STRIPE_PRICE_STANDARD_YEAR=
EINVITE_STRIPE_PRICE_PRO_MONTH=
EINVITE_STRIPE_PRICE_PRO_YEAR=
EINVITE_STRIPE_PRICE_OVERAGE_GB=
# Canva bridge (Phase 5.1) — leave blank to disable URL import
EINVITE_CANVA_CLIENT_ID=
EINVITE_CANVA_CLIENT_SECRET=
EINVITE_CANVA_OAUTH_REDIRECT_URI=
EINVITE_CANVA_API_BASE=https://api.canva.com/rest/v1
# Storage-overage computation cron (daily at 00:30 UTC by default)
EINVITE_STORAGE_USAGE_CRON="30 0 * * *"
```

`production_preflight.py` (V54) is extended to require
`EINVITE_STRIPE_SECRET_KEY` + `EINVITE_STRIPE_WEBHOOK_SECRET` when the
hosted tier is enabled (i.e. when `EINVITE_ENABLE_HOSTED_TIER=1`).

---

## 8. Acceptance criteria (per ROADMAP §8)

* [ ] A host can sign up → pick Standard → pay → send an invitation, all
      without touching a server.
* [ ] No per-guest fees anywhere in the flow.
* [ ] Tier upgrade takes effect immediately.
* [ ] Tier downgrade takes effect at period end (no mid-period data loss).
* [ ] Storage overage is metered daily, billed monthly via Stripe Usage
      Records.
* [ ] Cancellation drops user to Free at period end; 30-day data grace
      period with email warnings at 7/3/1 days before deletion.
* [ ] Nonprofits can apply (Phase 5.1 follow-up) and receive 50% off.
* [ ] Stripe webhook signature verification rejects forged requests.
* [ ] Stripe webhook is idempotent (duplicate event IDs return 200
      `{"received":true,"duplicate":true}`).

## 9. Change history

| Version | Date | Change |
|---|---|---|
| V54.8 | 2026-08-14 | Initial design: Stripe Checkout + Subscriptions + metered Usage Records + 30-day data grace + nonprofit application route sketch. Schema migration: 5 new `users` columns. Backend scaffolding: `GET /api/account/tier`, `POST /api/account/tier/upgrade`, `POST /api/billing/webhook/stripe`. |
