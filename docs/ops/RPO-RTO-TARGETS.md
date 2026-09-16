# RPO / RTO Targets per Workload Tier

Phase 1c deliverable. Defines the **Recovery Point Objective** (maximum acceptable data loss measured in time) and the **Recovery Time Objective** (maximum acceptable downtime before service is restored) for each class of data owned by the eInvite platform.

Targets are **commitments to customers and to the on-call engineer**, not best-effort hopes. They drive:

- The PostgreSQL continuous-archiving (WAL) + pgBackRest retention windows — see [`BACKUP-DR.md`](./BACKUP-DR.md).
- The restore procedure an on-call engineer must execute — see [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md).
- The quarterly DR drill that proves they hold — see the *DR Drill Plan* section of [`BACKUP-DR.md`](./BACKUP-DR.md).

## Definitions

- **RPO (Recovery Point Objective).** The worst-case wall-clock gap between *now* and the most recent recoverable state. Any data written inside that window may be lost in a total-primary failure; nothing older is.
- **RTO (Recovery Time Objective).** The worst-case wall-clock duration from *incident declaration* to *service accepting production traffic again* on the restored primary. Includes detection, decision, restore, validation, and cutover.

## Tier matrix

| Tier | Workload class | RPO target | RTO target | Justification |
|------|----------------|------------|------------|----------------|
| **Tier 1** | Guest PII + RSVP answers + invitations | **≤ 5 minutes** | **≤ 30 minutes** | Guest names, phone numbers, RSVP answers, plus the invitation draft itself, are the irreplaceable product. Once a guest submits an RSVP there is no second source for that answer. Treated as regulated PII for retention. |
| **Tier 2** | Analytics, template marketplace, collaboration checkpoints | **≤ 15 minutes** | **≤ 1 hour** | Regenerable or reproducible: analytics events can be replayed from access logs; templates are versioned and re-importable; collaboration checkpoints can be reconstructed from `collaboration_updates`. Losing 15 minutes costs editor convenience, not customer data. |
| **Tier 3** | Internal configuration, feature flags, audit metadata | **≤ 24 hours** | **≤ 4 hours** | Slow-changing operational metadata. A daily base backup is sufficient. Restored from the latest nightly snapshot plus WAL replay; no PITR precision needed. |

> The strictest target on the cluster wins. Because Tier 1 shares the same physical PostgreSQL cluster as Tier 2 and Tier 3, the cluster runs at the **Tier 1 RPO/RTO** (≤ 5 min RPO, ≤ 30 min RTO). Per-tier targets are documented so a future split — e.g. a separate analytics replica — can relax the analytics retention without affecting guest data.

## Tier 1 — guest PII and invitation data (RPO ≤ 5 min, RTO ≤ 30 min)

These tables are the contract with the customer. They hold the answers a guest submitted and the artifact the host authored. They cannot be reconstructed from any other source.

| Table (see `docs/postgres_schema.sql`) | Holds | Why Tier 1 |
|----------------------------------------|-------|------------|
| `users` | email, password hash, MFA secret, passkey credentials | Account recovery; cannot lose or rewrite |
| `sessions` | signed HttpOnly session tokens | Revoking/restoring sessions must be precise |
| `invitations` | invitation slug, draft_json, publication state | The artifact the host authored |
| `publications` | published invitation versions | The artifact the guest actually saw |
| `rsvps` | guest name, status, guest_count, answers_json, note | **Guest PII + their answer** — the canonical reason Tier 1 exists |
| `guests` | name, phone, guest token, token_hash, check-in state | Guest PII and token economy |
| `guest_messages` | inbound guest messages | Guest-authored content |
| `access_tokens` | per-invitation access tokens | Re-issuing invalidates outstanding links |
| `passkeys` | WebAuthn credentials, sign-count | Replay protection depends on monotonic counter |
| `auth_challenges` | MFA challenges | Short-lived but security-critical |
| `audit_events` | hash-chained immutable audit log | Append-only; loss breaks the hash chain |
| `collaboration_updates` | CRDT operation log | Drives editor recovery; PII-adjacent |
| `collaboration_checkpoints` | compacted CRDT state | Authoritative document state |
| `invitation_collaborators` | per-invitation role grants | Authorization truth |
| `workspaces`, `workspace_memberships` | tenant + role model | Authorization truth |
| `billing_orders`, `billing_events` | paid orders | Money record |
| `privacy_requests` | GDPR/CCPA deletion requests | Regulatory deadline-bound |
| `approval_requests`, `invitation_review_policies` | approval gates | Authoring workflow truth |

**Backup mechanism for Tier 1.** PostgreSQL continuous WAL archiving with `archive_timeout = 60s` plus pgBackRest base backups every 6 hours, retained 14 days. PITR granularity is therefore **≤ 60 seconds** of committed transactions (the `archive_timeout`), which is well inside the 5-minute RPO budget and leaves headroom for the WAL ship + replay latency. See [`BACKUP-DR.md`](./BACKUP-DR.md) §pgBackRest.

## Tier 2 — analytics, templates, marketplace (RPO ≤ 15 min, RTO ≤ 1 hour)

Reproducible or replayable. Loss is an inconvenience, not a regulatory event.

| Table | Holds | Why Tier 2 |
|-------|-------|------------|
| `view_events` | per-publication view analytics | Regenerable from access logs if needed |
| `bandwidth_events` | bandwidth accounting | Regenerable from object-storage logs |
| `user_templates`, `template_versions` | user-saved + marketplace templates | Versioned; authors hold the original |
| `user_page_templates`, `user_components` | reusable design fragments | Re-importable |
| `stored_objects` (metadata row) | object metadata pointer | The bytes themselves are in object storage (Tier 1 for the *file*, but the *metadata* is Tier 2 because it can be rebuilt from bucket listings) |
| `assets` | per-invitation asset references | Rebuildable from `stored_objects` |
| `studio_resources`, `studio_governance`, `studio_releases` | editor studio state | Authoring convenience |
| `marketplace_templates_v36` and related V36 tables | marketplace listings | Re-publishable from author's original |
| `event_tasks_v52`, `event_automations_v52`, `automation_runs_v52` | event-ecosystem tasks | Re-runnable automation state |
| `data_merge_jobs_v47`, `data_merge_variants_v47` | bulk-generation jobs | Re-runnable from source |
| `animation_projects_v44`, `animation_export_jobs_v44` | animation exports | Re-exportable from project |
| `ai_conversations`, `ai_messages`, `ai_plans`, `ai_jobs`, `ai_design_blueprints` | AI agent history | Convenience history, not the artifact |

**Backup mechanism for Tier 2.** Same physical cluster as Tier 1, so the cluster runs at Tier 1 RPO. If a future split happens (analytics replica), Tier 2 may run on a separate cluster with `archive_timeout = 300s` and base backups every 12 hours, retained 7 days.

## Tier 3 — internal config (RPO ≤ 24 h, RTO ≤ 4 h)

Slow-changing operational metadata. A daily base backup is sufficient.

| Table | Holds | Why Tier 3 |
|-------|-------|------------|
| `platform_schema_migrations` | migration log | Append-only; reconstructed from code |
| `studio_backup_policies` | per-invitation backup policy rows | Re-issuable from defaults |
| `upload_sessions`, `upload_sessions_v32` | in-flight uploads | Ephemeral; TTL-bound |
| `idempotency_records` | dedup keys | 24-hour TTL |
| `platform_backups`, `backup_runs` | backup-of-backup bookkeeping | Operational metadata |
| `operational_metrics` | sampled metrics | Regenerable from Prometheus/observability |
| `ai_preferences`, `ai_model_capabilities`, `ai_local_provider_configs` | admin-tunable knobs | Re-settable |
| `plugin_installations_v48`, `plugin_manifests_v48` | plugin registry | Re-installable |
| `custom_domains_v45` | custom-domain bindings | Re-settable from DNS |

**Backup mechanism for Tier 3.** Captured by the same cluster backup (Tier 1 RPO applies since they share storage). If split, daily `pg_dump --format=custom` snapshot is sufficient; no PITR needed.

## Object storage is its own tier

Object storage (user-uploaded media: photos, design assets, raster documents) is **not** covered by the PostgreSQL backup tier. It is covered by bucket versioning + cross-region replication in S3/R2/MinIO. See [`BACKUP-DR.md`](./BACKUP-DR.md) §MinIO/S3 Backup Strategy.

Object-storage data loss target: **RPO = 0** (versioning makes accidental deletes recoverable), **RTO = minutes** (replica is already warm). The `ObjectStorage` abstraction in `platform_v32/storage.py` enforces SSE-S3 encryption-at-rest on every PUT — that is *encryption*, not *backup*. Backup = versioning + replication.

## Redis is below all tiers

Redis in eInvite is **optional** and holds only rate-limit counters and presence heartbeats. The application has an in-process fallback (`RATE_BUCKETS` dict + `PRESENCE_STATE` dict) that keeps the service correct without Redis.

Redis data loss = degraded UX (rate-limit counters reset, presence blinks), **not customer data loss**. There is no RPO/RTO commitment for Redis; persistence config exists only to make Redis restart faster. See [`BACKUP-DR.md`](./BACKUP-DR.md) §Redis Persistence.

## Acceptance gates

A target is met only when *all* of these hold:

1. The retention window in `pgbackrest.conf` (full + diff + WAL archive) covers the RPO with at least 2× margin.
2. At least one restore drill has been performed end-to-end in staging and the measured restore + validation time fits inside the RTO. See *DR Drill Plan* in [`BACKUP-DR.md`](./BACKUP-DR.md).
3. The on-call rotation has acknowledged the runbook in [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md) within the last 90 days.
4. The drill report for the most recent quarter is filed under `docs/ops/drill-reports/`.

## Change history

| Date | Change |
|------|--------|
| 2026-09-14 | Initial Phase 1c deliverable. Three-tier model mapped to actual tables in `docs/postgres_schema.sql`. |
