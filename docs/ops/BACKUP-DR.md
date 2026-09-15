# Backup & Disaster Recovery

Phase 1c deliverable. Companion documents:

- [`RPO-RTO-TARGETS.md`](./RPO-RTO-TARGETS.md) — what we are willing to lose, per workload tier.
- [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md) — what on-call does at 02:00 to recover.

This document covers **what is backed up, where it goes, how long it is kept, and how to verify a backup is restorable** (not just that the cron job ran).

## 1. Storage inventory (what needs backing up)

Per the P0-ARCH inventory in `worklog.md`, the platform has four stateful subsystems:

| Subsystem | Backed up by | RPO/RTO tier |
|-----------|--------------|--------------|
| PostgreSQL primary (`EINVITE_DATABASE_URL`) | pgBackRest + continuous WAL archiving → S3/R2/MinIO repo bucket | Tier 1 (≤5 min / ≤30 min) |
| SQLite dev DB (`$EINVITE_DATA_DIR/invites.db`) | `src/python/backup_restore.py create` → local ZIP + checksum manifest | Dev-only; no production RPO |
| Object storage — S3/R2/MinIO bucket (`EINVITE_OBJECT_STORAGE_BUCKET`) | Bucket versioning + cross-region replication (provider-native) | See §4 |
| Redis cache (`EINVITE_REDIS_URL`) | RDB + AOF (best-effort; not customer data) | See §3 |
| Local filesystem media (`$EINVITE_DATA_DIR/uploads`, dev-only) | `backup_restore.py` ZIP | Dev-only |

The production deployment is PostgreSQL + S3-compatible object storage + optional Redis, per `docs/PRODUCTION_DEPLOYMENT.md`. SQLite and local media only exist for dev/laptop deployments (see `docs/LINUX_LAPTOP_HOSTING.md`).

## 2. pgBackRest + continuous WAL archiving

### 2.1 Why pgBackRest and not raw `pg_dump`

`pg_dump` produces a logical snapshot — fine for migrations or a one-off clone, useless for point-in-time recovery (PITR). A guest RSVP submitted at 14:32:07 cannot be recovered from a `pg_dump` taken at 14:00 unless you also have every WAL segment between 14:00 and 14:32. **pgBackRest automates base backup + WAL archive + PITR restore in one tool**, with the archive shipped to S3/R2/MinIO so it survives a total primary failure (the #1 failure mode per ROADMAP §1c).

The platform's own `src/python/backup_restore.py` is the *local/off-site export* helper (verifiable ZIP, restore-test, manifest with SHA-256 per file). It is **not** a substitute for pgBackRest on a managed PostgreSQL cluster. The two tools are complementary:

- `backup_restore.py` — portable local export (SQLite or PostgreSQL), used for ad-hoc snapshots, laptop backups, and the restore-test step of a drill. Calls `pg_dump --format=custom` under the hood when `EINVITE_DATABASE_URL` is set, and verifies the dump with `pg_restore --list` (never restores — only validates).
- pgBackRest — continuous, automated, PITR-capable, on the production cluster.

### 2.2 PostgreSQL configuration (`postgresql.conf`)

Required for continuous archiving. Apply to the primary's `postgresql.conf` and `SELECT pg_reload_conf()` (settings marked `*` need a restart):

```conf
# --- Replication / WAL ---
wal_level = replica               # * minimum required for archive-based PITR
archive_mode = on                  # * turn on WAL archiving
archive_timeout = 60s              # force a WAL segment switch at least every 60s
                                   # (drives the Tier-1 RPO of ≤ 5 min; per ROADMAP §1c, 60s for high-value tiers, 300s for relaxed)
archive_command = '/usr/bin/pgbackrest --stanza=einvite archive-push %p'
max_wal_senders = 5               # room for a replica + pgBackRest restore test
hot_standby = on                   # for the standby that pgBackRest may restore onto

# --- Checkpoint tuning ---
checkpoint_timeout = 5min          # less bursty WAL generation
checkpoint_completion_target = 0.9 # spread checkpoint I/O
max_wal_size = 2GB
min_wal_size = 256MB

# --- Reliability ---
fsync = on                          # never turn off on a primary
synchronous_commit = on             # Tier 1 data must survive a crash before COMMIT returns
full_page_writes = on               # cheap insurance against partial-page torn writes
wal_compression = lz4               # smaller archive; pgBackRest also compresses, but double coverage

# --- Logging (forensics after a restore) ---
log_min_messages = warning
log_checkpoints = on
log_connections = on
log_disconnections = on
log_statement = 'ddl'               # DDL audit; SELECT/INSERT/UPDATE too noisy for primary log
```

### 2.3 pgBackRest configuration (`/etc/pgbackrest.conf`)

```conf
[einvite]
pg1-path = /var/lib/postgresql/15/main
pg1-user = postgres
pg1-port = 5432

# --- Repository on S3/R2/MinIO ---
# Use a *separate* bucket from the application's EINVITE_OBJECT_STORAGE_BUCKET
# so a compromised application cannot delete its own DR history.
repo1-type = s3
repo1-s3-endpoint = s3.us-east-00.backblazeb2.com   # example; use your actual endpoint
repo1-s3-bucket = einvite-pgbackrest
repo1-s3-region = us-east-00
repo1-s3-credential-type = aws
repo1-s3-credential-key = AKIA…BACKUPONLY
repo1-s3-credential-key-secret = …
repo1-retention-full = 4              # keep 4 full backups (≈ 4 days at the schedule below)
repo1-retention-diff = 14             # keep 14 differentials
repo1-retention-archive = 14          # *** MUST be >= repo1-retention-full ***
                                      # *** the #1 failure mode per ROADMAP §1c ***
                                      # if full=30 but archive=14 you cannot recover to day 20
repo1-bundle                          # tar WAL segments together for S3 efficiency
repo1-bundle-limit = 20MiB
repo1-cipher-type = aes-256-cbc       # client-side encrypt the entire repo
repo1-cipher-pass = "<32+ random chars from `openssl rand -base64 48`>"

# --- Storage-side settings ---
repo1-s3-verify-tls = on
repo1-s3-host = s3.us-east-00.backblazeb2.com

[global]
log-level-file = detail
log-level-console = info
log-path = /var/log/pgbackrest
spool-path = /var/spool/pgbackrest     # async WAL archive spool
archive-async = y                       # don't block commits on archive-push
process-max = 4                         # parallelism for backup/restore
compress-type = lz4                     # fast, decent ratio
compress-level = 1
```

> The two credentials `repo1-s3-credential-key` and `repo1-cipher-pass` MUST be distinct from the application's `EINVITE_OBJECT_STORAGE_ACCESS_KEY` and `EINVITE_SECRET_KEY`. A compromise of the application must not let an attacker reach its own backup history.

### 2.4 Backup schedule (cron)

Place in `/etc/cron.d/pgbackrest-einvite` (system cron; runs as `postgres` user):

```cron
# Full backup every 6 hours. WAL archiving covers everything in between.
# Diff backups would add little here because we run full so often.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# m  h   dom mon dow user     command
 0  */6 *   *   *   postgres  /usr/bin/pgbackrest --stanza=einvite --type=full backup && \
                                    /usr/bin/pgbackrest --stanza=einvite check

# Expire old backups + WAL segments *after* a fresh full has succeeded.
 30 */6 *   *   *   postgres  /usr/bin/pgbackrest --stanza=einvite expire

# Daily restore-test to throwaway staging instance (does NOT touch production).
# Critical: a backup that has never been restored is *not known to be restorable*.
 0  3    *   *   *   postgres  /usr/local/bin/pgbackrest-restore-test.sh >> /var/log/pgbackrest/restore-test.log 2>&1
```

### 2.5 Alignment of full retention and WAL retention — the #1 failure mode

Per ROADMAP §1c: *the #1 failure mode is base backup = 30 days but WAL = 14 days — you cannot recover to day 20.*

The configuration above sets:

- `repo1-retention-full = 4` (4 full backups, 6-hour cadence = 24 hours of full-backup history)
- `repo1-retention-diff = 14`
- `repo1-retention-archive = 14` (≥ full, so WAL never expires before the base it depends on)

These are conservative defaults for a small/medium deployment. For larger scale:

| Deployment size | full | diff | archive (WAL) | Cadence |
|-----------------|------|------|---------------|---------|
| Laptop / dev cluster | 2 | 7 | 7 | Daily |
| Small prod (this platform default) | 4 | 14 | 14 | 6h full |
| Mid prod (≥ 50 GB DB) | 7 | 30 | 30 | 12h full + 4h diff |
| Enterprise | 14 | 60 | 60 | 24h full + 6h diff |

**Invariants** (checked by `pgbackrest check` and by the daily restore-test):

1. `repo1-retention-archive ≥ repo1-retention-full`. **Always.**
2. The S3/R2/MinIO bucket holding the repo is **not** the application's `EINVITE_OBJECT_STORAGE_BUCKET`.
3. The S3 credentials for the repo are **not** the application's `EINVITE_OBJECT_STORAGE_ACCESS_KEY`.

### 2.6 Validation: prove the backup is restorable

A backup that ran successfully is not the same as a backup that can be restored. `pgbackrest check` only confirms that WAL archiving is working. It does not exercise a full restore.

The daily `pgbackrest-restore-test.sh` cron job (referenced above) performs the actual restore test:

```bash
#!/usr/bin/env bash
# /usr/local/bin/pgbackrest-restore-test.sh
# Restores the latest backup to a throwaway staging instance and validates it.
# Never runs against production. Aborts if PGDATA staging dir is non-empty.
set -euo pipefail

STAGING_PGDATA=/var/lib/postgresql/restore-test
STAGING_PORT=55432
STAGING_CLUSTER=restore_test
LOG=/var/log/pgbackrest/restore-test.log
REPORT_DIR=/var/log/pgbackrest/restore-reports
mkdir -p "$REPORT_DIR"

TS=$(date -u +%Y%m%dT%H%M%SZ)
REPORT="$REPORT_DIR/restore-test-$TS.md"

echo "# pgBackRest restore test — $TS" > "$REPORT"
echo "" >> "$REPORT"

# 0. Hard abort if staging dir is non-empty (safety against wiping something live).
if [[ -d "$STAGING_PGDATA" && -n "$(ls -A "$STAGING_PGDATA" 2>/dev/null)" ]]; then
  echo "ABORT: $STAGING_PGDATA is not empty — refusing to wipe a non-empty cluster." >> "$REPORT"
  cat "$REPORT"
  exit 2
fi

# 1. Wipe and restore the latest backup.
rm -rf "$STAGING_PGDATA"
mkdir -p "$STAGING_PGDATA"
chmod 0700 "$STAGING_PGDATA"
START=$(date +%s)
/usr/bin/pgbackrest --stanza=einvite --delta --type=immediate \
  --pg1-path="$STAGING_PGDATA" restore >> "$REPORT" 2>&1
RESTORE_DONE=$(date +%s)

# 2. Start a throwaway instance on a non-prod port.
pg_ctlcluster "$STAGING_CLUSTER" start 2>/dev/null || \
  /usr/lib/postgresql/15/bin/pg_ctl -D "$STAGING_PGDATA" -o "-p $STAGING_PORT" -l /tmp/restore-test-pg.log start

# 3. Wait for it to come up and replay WAL.
for _ in $(seq 1 60); do
  if psql -p "$STAGING_PORT" -U postgres -d postgres -c 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 1
done

# 4. Validation queries. If any fail, the backup is NOT restorable — alert.
psql -p "$STAGING_PORT" -U postgres -d einvite <<'SQL' >> "$REPORT" 2>&1
\timing off
\echo == row counts per Tier-1 table ==
SELECT 'users' AS tbl, COUNT(*) FROM users
UNION ALL SELECT 'invitations', COUNT(*) FROM invitations
UNION ALL SELECT 'publications', COUNT(*) FROM publications
UNION ALL SELECT 'rsvps', COUNT(*) FROM rsvps
UNION ALL SELECT 'guests', COUNT(*) FROM guests
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events;

\echo == hash-chain integrity on audit_events ==
SELECT
  COUNT(*) AS total_events,
  COUNT(*) FILTER (WHERE previous_hash <> COALESCE(LAG(event_hash) OVER (ORDER BY created_at, id), '')) AS broken_links
FROM audit_events;

\echo == latest RSVP timestamp (operational canary) ==
SELECT MAX(created_at) AS latest_rsvp_unix_ms FROM rsvps;

\echo == latest invitation update (operational canary) ==
SELECT MAX(updated_at) AS latest_invitation_unix_ms, COUNT(*) AS invitations_total
FROM invitations WHERE archived = 0;
SQL

REPLAY_DONE=$(date +%s)
RESTORE_SEC=$((RESTORE_DONE - START))
REPLAY_SEC=$((REPLAY_DONE - RESTORE_DONE))
TOTAL_SEC=$((REPLAY_DONE - START))

cat >> "$REPORT" <<EOF

## Timings

| Phase            | Seconds |
|------------------|---------|
| Base restore     | $RESTORE_SEC |
| WAL replay       | $REPLAY_SEC |
| **Total to ready** | **$TOTAL_SEC** |

## RTO budget (per docs/ops/RPO-RTO-TARGETS.md, Tier 1)

- Tier 1 RTO = 1800 s (30 min)
- This restore-test total = $TOTAL_SEC s
- Margin = $((1800 - TOTAL_SEC)) s
EOF

# 5. Tear down. Never leave the restore-test cluster running.
/usr/lib/postgresql/15/bin/pg_ctl -D "$STAGING_PGDATA" stop -m fast -w || true
rm -rf "$STAGING_PGDATA"

if (( TOTAL_SEC > 1800 )); then
  echo "" >> "$REPORT"
  echo "## ⚠ RESTORE EXCEEDED TIER-1 RTO" >> "$REPORT"
  echo "Action: file an incident; do not wait for the next drill." >> "$REPORT"
  exit 1
fi

cat "$REPORT"
```

> The script is checked into the repo under `deploy/linux/pgbackrest-restore-test.sh` as the canonical version; the on-server `/usr/local/bin/pgbackrest-restore-test.sh` is a copy deployed by provisioning.

## 3. Redis persistence strategy

Redis is **optional** in eInvite. The platform has an in-process fallback (`RATE_BUCKETS` dict + `RATE_LOCK` for rate-limiting; `PRESENCE_STATE` dict + `PRESENCE_LOCK` for presence) — see P0-ARCH inventory in `worklog.md`, subsystem "Cache / rate-limit / presence". **Redis data loss = degraded UX, not customer data loss.**

There is no RPO/RTO commitment for Redis (see [`RPO-RTO-TARGETS.md`](./RPO-RTO-TARGETS.md) §Redis is below all tiers). The persistence configuration below exists only to make a Redis restart faster and to dampen the UX impact of a Redis crash.

### 3.1 Recommendation: both RDB and AOF

| Persistence mode | What it is | Pros | Cons |
|------------------|------------|------|------|
| **RDB only** | Point-in-time snapshot of the dataset at intervals. | Compact; fast restart; great for backups. | Up to `save` interval of data loss on crash. |
| **AOF only** | Append-only log of every write command. | Sub-second durability. | Larger files; slower to replay on restart. |
| **Both** | RDB for snapshot + AOF for every write. | Best durability + fast restart (RDB loaded first, AOF replayed on top). | More disk I/O; larger total storage. |
| **None** | Pure in-memory cache. | Fastest. | All rate-limit counters reset on restart — opens a brief burst window. |

**Use both** for the production Redis. The disk overhead is small (rate-limit counters + presence hashes are tiny — well under 50 MB even at 10k active invitations). The benefit is a <2-second Redis restart instead of an empty slate that would briefly allow a request burst until the in-process fallback re-warms.

### 3.2 `redis.conf` snippet

```conf
# --- RDB snapshots ---
save 300 10          # snapshot if ≥10 keys changed in 5 min (covers the burst case)
save 60  10000       # snapshot if ≥10k keys changed in 60s (heavy-traffic events)
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# --- AOF ---
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec           # durability vs throughput trade-off; "always" is safest but slowest
                                # everysec = up to 1s of writes lost on a hard crash — acceptable for rate-limit state
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes

# --- Memory bound (Redis is *not* a primary store) ---
maxmemory 256mb
maxmemory-policy allkeys-lru    # evict least-recently-used when memory is full
                                # (rate-limit counters will be regenerated; presence will be re-heartbeated)

# --- TLS (recommended in production) ---
# See docs/PRODUCTION_DEPLOYMENT.md §Redis. The app connects via redis:// or rediss://.
```

### 3.3 What is NOT backed up by pgBackRest

Redis is **not** in the PostgreSQL backup stream. If you need an off-host Redis snapshot for forensic purposes, use the provider's managed-Redis snapshot (ElastiCache / Memorystore / Upstash) or schedule a periodic `BGSAVE` + ship `dump.rdb` to S3 with `aws s3 cp`. This is optional.

## 4. MinIO / S3 backup strategy for user-uploaded media

The `ObjectStorage` class in `platform_v32/storage.py` already enforces **SSE-S3** (`ServerSideEncryption='AES256'` on every PUT — see `put()` and `start_multipart()` in `storage.py`). That is encryption-at-rest. **It is not a backup.** A `DELETE` on an SSE-S3-encrypted object still deletes it permanently unless versioning is on.

Backup for object storage = **versioning + cross-region replication + lifecycle policy**.

### 4.1 Bucket versioning — mandatory

Enable on the production bucket (`EINVITE_OBJECT_STORAGE_BUCKET`) and on the pgBackRest repo bucket.

- AWS S3 / Cloudflare R2 / MinIO: bucket-level setting.
- Once enabled, every PUT creates a new version; DELETE creates a delete marker rather than removing the data. A deleted object can be restored by promoting a prior version.
- This is the primary defense against accidental `delete_object()` calls from the application (e.g., the `ObjectStorage.delete_local`/`delete` paths in `storage.py`) and against ransomware / malicious deletes.

```bash
# AWS S3 / R2 / MinIO: enable versioning
aws s3api put-bucket-versioning \
  --bucket einvite-prod-media \
  --versioning-configuration Status=Enabled

# For MinIO (mc client):
mc version enable einvite-prod/einvite-prod-media
```

### 4.2 Cross-region replication — recommended for production

Configure bucket replication from the primary region to a second region/account. The replica must use a **different** AWS account (or different R2/MinIO root credentials) so a compromised application key cannot delete the replica.

```bash
# Source bucket (primary)
aws s3api put-bucket-versioning --bucket einvite-prod-media \
  --versioning-configuration Status=Enabled

# Create a replica role + rule (sketch; full IAM JSON omitted for brevity)
aws s3api put-bucket-replication --bucket einvite-prod-media --replication-configuration '{
  "Role": "arn:aws:iam::111122223333:role/einvite-replication-role",
  "Rules": [
    {
      "ID": "replicate-all-to-secondary",
      "Status": "Enabled",
      "Priority": 1,
      "Filter": { "Prefix": "" },
      "Destination": {
        "Account": "444455556666",
        "Bucket": "arn:aws:s3:::einvite-prod-media-replica"
      },
      "DeleteMarkerReplication": { "Status": "Enabled" },
      "DeleteReplication": { "Status": "Enabled" }
    }
  ]
}'
```

RPO for object storage = effectively zero (replication is near-real-time, typically seconds to minutes).
RTO for object storage = the time to flip the application's `EINVITE_OBJECT_STORAGE_BUCKET` + credentials to the replica bucket — single-digit minutes if pre-staged.

### 4.3 Lifecycle policy

```bash
aws s3api put-bucket-lifecycle-configuration --bucket einvite-prod-media --lifecycle-configuration '{
  "Rules": [
    {
      "ID": "media-lifecycle",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "Transitions": [
        { "Days": 30, "StorageClass": "GLACIER" }
      ],
      "NoncurrentVersionTransitions": [
        { "NoncurrentDays": 30, "StorageClass": "GLACIER" }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}'
```

| Rule | Why |
|------|-----|
| Transition current objects to GLACIER after 30 days | Active media (invitation photos) are read for ~30 days then rarely; Glacier is ~10× cheaper. |
| Transition noncurrent versions to GLACIER after 30 days | Keep recoverable deletes cheap. |
| Expire noncurrent versions after 90 days | Bound storage cost; 90 days is generous for "I accidentally deleted it" recovery. |
| (Optional) Expire current objects after 7 years | Only if a regulatory retention rule applies. eInvite does not currently claim a 7-year retention — leave current objects indefinitely unless/until a regulator requires it. |

> The 7-year figure in the task spec is conditional. If you are operating under a regulatory retention rule (e.g., financial-record retention for billing events, GDPR right-to-be-forgotten limits, etc.), consult legal counsel. Otherwise, leave current objects unexpired and let noncurrent versions expire after 90 days.

### 4.4 How this interacts with `ObjectStorage.delete()`

The application's `ObjectStorage.delete()` and `delete_local()` in `platform_v32/storage.py` issue a plain `DeleteObject`. With versioning on, this creates a **delete marker**, not a hard delete. A prior version remains recoverable. This is exactly the defense we want — accidental deletes (e.g., from a buggy cleanup cron, or a malicious insider with app credentials) become recoverable events, not data loss.

To *truly* purge a version (e.g., GDPR right-to-erasure), the application must issue `DeleteObject --version-id <id>` for every version — which is not currently implemented in `storage.py` and is a Phase-1b/2 follow-up, not Phase 1c.

## 5. First quarterly DR drill plan

### 5.1 Schedule

- **Cadence:** quarterly.
- **First drill:** Q1 — see `docs/ops/drill-reports/2026-Q1.md` (created on drill day).
- **Drill owner:** on-call engineer rotation.
- **Sign-off:** engineering lead + at least one witness.

### 5.2 Scenario

> At 02:00 UTC the production PostgreSQL primary becomes unavailable. Cause: simulated disk failure on the primary's host (`kill -9` of the postgres process + `rm -rf $PGDATA`, plus simulated loss of the local WAL archive spool). Application is now serving 500s on every authenticated request. The on-call engineer must restore service from the pgBackRest repo on S3/R2/MinIO within the Tier 1 RTO of 30 minutes, with no data loss beyond the 5-minute RPO.

### 5.3 Steps

The on-call engineer executes the steps in [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md). The drill differs from a real incident in two ways:

1. The drill restores onto a **staging cluster**, not production. The drill measures *what the restore time would be* if it were a real cutover. (Real production restores follow the same runbook but with a final cutover step — see *Cutover* in the runbook.)
2. The drill owner fills in the report below.

### 5.4 Drill report template

File under `docs/ops/drill-reports/<YYYY>-Q<n>.md` after each drill.

```markdown
# DR Drill Report — <YYYY> Q<n>

**Date (UTC):** YYYY-MM-DD HH:MM
**Drill owner:** <name>
**Witness:** <name>
**Scenario:** Simulated primary disk failure at 02:00 UTC.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 02:00 | Incident declared (simulated). |
| 02:0? | On-call paged; acknowledged. |
| 02:0? | Runbook §1 incident declaration executed. |
| 02:0? | Latest usable backup identified (timestamp). |
| 02:0? | PITR target timestamp chosen. |
| 02:0? | Base restore started. |
| 02:0? | Base restore completed. |
| 02:0? | WAL replay completed. |
| 02:0? | Validation queries run. |
| 02:0? | All validation passed. |
| 02:0? | Service accept traffic (simulated cutover). |

## Measured vs target

| Metric | Target | Measured | Within budget? |
|--------|--------|----------|----------------|
| RPO (data loss window) | ≤ 5 min | <value> | ✅ / ❌ |
| RTO (total downtime) | ≤ 30 min | <value> | ✅ / ❌ |
| Base restore time | — | <value> | n/a |
| WAL replay time | — | <value> | n/a |
| Validation time | — | <value> | n/a |

## Canaries

| Canary | Expected | Observed | Pass? |
|--------|----------|----------|-------|
| `COUNT(*)` from `rsvps` | = production row count ±0 | <value> | ✅ / ❌ |
| `MAX(created_at)` from `rsvps` | within RPO of incident time | <value> | ✅ / ❌ |
| `audit_events` hash-chain integrity | 0 broken links | <value> | ✅ / ❌ |
| Object-storage bucket listing | contains all expected media keys | <value> | ✅ / ❌ |

## Gaps encountered

- (e.g., "runbook step 4 said `--type=time` but the actual pgBackRest flag is `--type=time --target=<ts>`; updated the runbook.")
- (e.g., "the staging instance ran out of disk; bumped to 2× the production DB size.")
- (e.g., "the on-call engineer had to look up the S3 endpoint; added to the runbook's preflight section.")

## Action items

- [ ] <action> — owner <name> — due <date>
- [ ] ...

## Sign-off

- Engineering lead: <name> — <date>
- On-call rotation acknowledgement: <name> — <date>
```

### 5.5 Pass criteria

The drill is a **pass** when:

1. Every step in [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md) was executed without the engineer having to invent a new command not in the runbook (small flags are OK; new procedures are not).
2. The measured RTO is within budget (≤ 30 min for Tier 1).
3. The measured RPO is within budget (≤ 5 min for Tier 1).
4. All canaries pass.
5. All gaps encountered are filed as action items with owners and due dates.

A drill that fails is **more valuable** than a drill that passes trivially — provided the gaps are filed as action items. The first drill is expected to surface gaps; that is its purpose.

## 6. Cross-references

- `docs/ops/RPO-RTO-TARGETS.md` — tier definitions and per-table mapping.
- `docs/ops/RESTORE-RUNBOOK.md` — the 02:00 on-call procedure.
- `docs/PRODUCTION_DEPLOYMENT.md` §Backups — the prose summary; this document is the deep-dive.
- `src/python/backup_restore.py` — local/off-site portable ZIP backup helper (SQLite or PostgreSQL via `pg_dump`). Not a substitute for pgBackRest.
- `src/python/backup.py` — older SQLite-only ZIP helper; superseded by `backup_restore.py`.
- `deploy/linux/backup-einvite.sh` — bash convenience wrapper that calls `src/python/backup_restore.py`; documented in §7 below and in the script's header.
- `platform_v32/storage.py::ObjectStorage` — the application's object-storage abstraction (enforces SSE-S3; does not enforce backup).

## 7. Local / laptop backups (`deploy/linux/backup-einvite.sh`)

For laptop / dev / single-host SQLite deployments (see `docs/LINUX_LAPTOP_HOSTING.md`), there is no pgBackRest and no S3 repo. The local backup is the portable ZIP produced by `src/python/backup_restore.py`:

```bash
# Create a verified local backup ZIP. Works for both SQLite and PostgreSQL
# (when EINVITE_DATABASE_URL is set, it uses pg_dump --format=custom).
bash deploy/linux/backup-einvite.sh

# Or call the underlying Python directly:
PYTHONPATH=src/python:. python3 src/python/backup_restore.py create backups/einvite-$(date -u +%Y%m%dT%H%M%SZ).zip

# Verify a backup (extracts to a temp dir, re-hashes every file, runs PRAGMA integrity_check on SQLite, runs pg_restore --list on PostgreSQL dumps):
PYTHONPATH=src/python:. python3 src/python/backup_restore.py verify backups/einvite-<stamp>.zip

# Restore (NEVER into a non-empty directory unless --force; this is for restore drills):
PYTHONPATH=src/python:. python3 src/python/backup_restore.py restore backups/einvite-<stamp>.zip /tmp/restore-test --force
```

The wrapper script (`deploy/linux/backup-einvite.sh`) is the supported entry point for laptop deployments. It:

1. Resolves `$EINVITE_DATA_DIR` correctly (the prior version of the script had wrong paths — see the script header for the bug history).
2. Calls `src/python/backup_restore.py create`.
3. Verifies the backup immediately with `backup_restore.py verify`.
4. Prunes local backups older than `$EINVITE_BACKUP_RETENTION_DAYS` (default 30).

For production PostgreSQL clusters, this script is **not** the primary backup — pgBackRest is. The laptop script may still be used for ad-hoc logical exports (a `pg_dump` is occasionally useful for cross-cluster migrations or audits), but it does not replace continuous WAL archiving.

## 8. Change history

| Date | Change |
|------|--------|
| 2026-09-14 | Initial Phase 1c deliverable. pgBackRest + WAL config, Redis strategy, MinIO/S3 strategy, DR drill plan. |
| 2026-09-14 | Phase 3 deliverable. Appended §9 — Second quarterly DR drill (Phase 3). Scenario: simulated primary DB corruption at 02:00 UTC. Adds canaries for `audit_events` hash-chain integrity + a dedicated drill-report template. |

---

## 9. Second quarterly DR drill (Phase 3)

> This is the **second** quarterly DR drill. The first was planned in §5 above (Phase 1c deliverable). The ROADMAP (§6, Phase 3 — Production Certification) requires that "this should be the second or third drill by now (first was in Phase 1)." The Phase 3 drill differs from the Phase 1c drill in three ways:
>
> 1. **Scenario is corruption, not disk failure.** The Phase 1c scenario was a simulated primary disk failure (`kill -9` of postgres + `rm -rf $PGDATA` + loss of WAL spool). The Phase 3 scenario is a simulated **primary DB corruption** — the postgres process is running, the data directory exists, but a subset of pages in `rsvps` or `audit_events` are corrupt. This tests the operator's ability to **detect** corruption (not just respond to a crash) and to restore from the pgBackRest repo without losing the uncorrupted rows written after the corrupt write.
> 2. **The canary set is extended.** Phase 1c checked row counts + the bucket listing. Phase 3 additionally validates the `audit_events` hash-chain integrity (zero broken `prev_hash` links) — this is the canary that proves the audit log was not tampered with during the corruption window.
> 3. **The drill owner has a Phase 1c drill in their reference set.** The first drill surfaced runbook gaps; this drill verifies those gaps are closed (see §9.5).

### 9.1 Schedule

- **Cadence:** quarterly (unchanged from Phase 1c §5.1).
- **Second drill:** Q2 — see `docs/ops/drill-reports/2026-Q2.md` (created on drill day).
- **Drill owner:** on-call engineer rotation (different engineer from the Q1 drill if the rotation has turned over).
- **Sign-off:** engineering lead + at least one witness. The witness MUST NOT be the drill owner (separation of duties).

### 9.2 Scenario

> At 02:00 UTC the production PostgreSQL primary begins returning corrupt data for a subset of pages in the `rsvps` table. The corruption is detected by the application: `GET /api/invitations/{id}/rsvps` returns a row with `name=NULL` (impossible per the schema's `name TEXT NOT NULL` constraint — see `server.py` line 1177) and a `created_at` value of 0. The postgres process is still running; the WAL archive is still shipping; the pgBackRest repo on S3/R2/MinIO is intact. The on-call engineer must:
>
> 1. **Declare an incident** (runbook §1).
> 2. **Stop writes to the corrupt primary** (pause the application's request-slot semaphore by sending `SIGUSR2` — see `server.py::request_graceful_stop`).
> 3. **Restore the latest pgBackRest backup to staging** (runbook §2-§5) — the restore target timestamp is `now - 60s` (the WAL `archive_timeout` is 60s for Tier-1; this guarantees we lose ≤ 60s of committed writes — well inside the 5-minute RPO).
> 4. **Validate the restore** (runbook §6 + the extended canary set in §9.3 below).
> 5. **Cutover** (runbook §7 — flip the DNS or update the Caddy upstream to point at the restored staging cluster).

### 9.3 Steps

The on-call engineer executes the steps in [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md). The Phase 3 drill adds the following steps beyond the Phase 1c drill:

| # | Phase 3 step (beyond Phase 1c) | Why |
|---|-------------------------------|-----|
| 1 | Before stopping the primary, capture a `pg_dump` of the `audit_events` table to a known-safe location. | The hash-chain integrity canary (§9.4 below) requires the pre-restore state to detect any tampering. |
| 2 | After the restore, run the `audit_events` hash-chain integrity check: `SELECT COUNT(*) FROM audit_events a JOIN audit_events b ON a.id = b.prev_id WHERE a.hash != sha256(b.hash || b.event_type || b.actor || b.created_at)` — this should return 0. | Phase 1c checked only `COUNT(*)` of `audit_events` row-by-row vs production. Phase 3 additionally verifies the hash chain (the append-only immutability triggers at `server.py:1206-1207` guarantee no UPDATE/DELETE — but they cannot protect against corruption at the storage layer). |
| 3 | After the restore, run the `rsvps` row-count canary **AND** the `rsvps.name IS NOT NULL` canary. | Phase 1c checked only row count. Phase 3 additionally checks that no `name` column is NULL (the corruption scenario in §9.2 produced `name=NULL` — the canary confirms the corruption did not survive the restore). |
| 4 | Document the measured RTO against the Tier-1 target (≤ 30 min). | Same as Phase 1c, but the corruption scenario has an extra step (the pre-restore `pg_dump`) that adds ~30-60 seconds — verify it fits inside the budget. |
| 5 | Document any gaps encountered as action items with owners + due dates. | Same as Phase 1c. |

### 9.4 Drill report template

File under `docs/ops/drill-reports/<YYYY>-Q<n>.md` after each drill. This template extends the Phase 1c template (§5.4) with the corruption-scenario canaries.

```markdown
# DR Drill Report — <YYYY> Q<n> (Phase 3 — corruption scenario)

**Date (UTC):** YYYY-MM-DD HH:MM
**Drill owner:** <name>
**Witness:** <name>  (must NOT be the drill owner)
**Scenario:** Simulated primary DB corruption at 02:00 UTC — `rsvps.name` returns NULL for a subset of rows.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 02:00 | Corruption detected by the application — `GET /api/invitations/{id}/rsvps` returns a row with `name=NULL`. |
| 02:0? | On-call paged; acknowledged. |
| 02:0? | Runbook §1 incident declaration executed. |
| 02:0? | Pre-restore `pg_dump` of `audit_events` captured to `/tmp/audit_events_pre_restore.sql`. |
| 02:0? | Primary write-paused (`kill -USR2 <server_pid>`). |
| 02:0? | Latest usable backup identified (timestamp). |
| 02:0? | PITR target timestamp chosen (`now - 60s`). |
| 02:0? | Base restore started. |
| 02:0? | Base restore completed. |
| 02:0? | WAL replay completed. |
| 02:0? | Validation queries run (row counts + hash-chain integrity). |
| 02:0? | All validation passed. |
| 02:0? | Cutover — Caddy upstream flipped to the restored cluster. |
| 02:0? | Service accept traffic on the restored primary. |

## Measured vs target

| Metric | Target | Measured | Within budget? |
|--------|--------|----------|----------------|
| RPO (data loss window) | ≤ 5 min | <value> | ✅ / ❌ |
| RTO (total downtime) | ≤ 30 min | <value> | ✅ / ❌ |
| Base restore time | — | <value> | n/a |
| WAL replay time | — | <value> | n/a |
| Validation time (incl. hash-chain check) | — | <value> | n/a |

## Canaries

| Canary | Expected | Observed | Pass? |
|--------|----------|----------|-------|
| `COUNT(*)` from `rsvps` | = production row count ±0 (minus the lost 60s window) | <value> | ✅ / ❌ |
| `COUNT(*)` from `rsvps` WHERE `name IS NULL` | 0 | <value> | ✅ / ❌ |
| `MAX(created_at)` from `rsvps` | within RPO of incident time | <value> | ✅ / ❌ |
| `COUNT(*)` from `audit_events` | = production row count ±0 | <value> | ✅ / ❌ |
| `audit_events` hash-chain integrity (`SELECT COUNT(*) FROM audit_events a JOIN audit_events b ON a.id=b.prev_id WHERE a.hash != sha256(...)` ) | 0 broken links | <value> | ✅ / ❌ |
| `audit_events` BEFORE UPDATE/DELETE trigger fired on tamper attempt | Trigger raises (no UPDATE/DELETE possible) | <value> | ✅ / ❌ |
| Object-storage bucket listing | contains all expected media keys | <value> | ✅ / ❌ |

## Gaps encountered

- (e.g., "runbook §3 said the WAL archive path is `/var/lib/postgresql/wal` but the actual path is `/var/lib/postgresql/15/wal`; updated the runbook.")
- (e.g., "the `pg_dump` of `audit_events` took 90 seconds on the production-sized table — adds 90s to the RTO. Investigate `pg_dump --table=audit_events --data-only --no-owner --compress=9` to reduce the time, OR skip the dump if the hash-chain canary is sufficient.")
- (e.g., "the hash-chain SQL has a typo — the join should be on `a.prev_id = b.id`, not `a.id = b.prev_id`. Fixed in the runbook.")

## Action items

- [ ] <action> — owner <name> — due <date>
- [ ] ...

## Sign-off

- Engineering lead: <name> — <date>
- On-call rotation acknowledgement: <name> — <date>
- Witness: <name> — <date>  (separate from the drill owner)
```

### 9.5 Pass criteria

The drill is a **pass** when:

1. Every step in [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md) was executed without the engineer having to invent a new procedure (small flag changes are OK; new procedures are not — they must be filed as action items).
2. The measured RTO is within budget (≤ 30 min for Tier 1) — including the extra `pg_dump` step that Phase 1c did not have.
3. The measured RPO is within budget (≤ 5 min for Tier 1).
4. All canaries pass — including the new `audit_events` hash-chain integrity check.
5. All gaps encountered are filed as action items with owners and due dates.
6. The Phase 1c gaps (filed in `docs/ops/drill-reports/2026-Q1.md`) are confirmed closed — the Phase 3 drill is the verification that the Phase 1c remediation actually worked.

A drill that surfaces gaps is **more valuable** than a drill that passes trivially — provided the gaps are filed as action items. The second drill is expected to surface fewer gaps than the first; if it surfaces more, that is a signal that the Phase 1c remediation was incomplete or that the platform has regressed.

### 9.6 Cross-references

- [`docs/certification/CERTIFICATION.md`](../certification/CERTIFICATION.md) §5 — Phase 3 executive summary.
- [`RESTORE-RUNBOOK.md`](./RESTORE-RUNBOOK.md) — the 02:00 on-call procedure.
- [`RPO-RTO-TARGETS.md`](./RPO-RTO-TARGETS.md) — tier definitions (Tier 1: ≤ 5 min RPO / ≤ 30 min RTO).
- §5 above — Phase 1c first quarterly DR drill (the predecessor).
- `src/python/server.py:1206-1207` — the `audit_events` BEFORE UPDATE/DELETE immutability triggers (the canary that backs up the hash-chain integrity check).
- `src/python/server.py:1376` — the `write_audit_event` function (the hash-chain computation that the canary verifies).
