# Restore Runbook

Phase 1c deliverable. **Short, explicit, executable at 02:00 AM by an on-call engineer who is tired and has not seen this codebase in 90 days.**

Companion documents:

- [`BACKUP-DR.md`](./BACKUP-DR.md) — what is backed up and where; the retention config that makes this runbook work.
- [`RPO-RTO-TARGETS.md`](./RPO-RTO-TARGETS.md) — what we are allowed to lose.

> **The single most important rule.** Never recover directly onto production. Always restore to a staging instance, validate, then cutover. See §5 (Cutover) and §6 (Rollback) below.

## 0. Preflight (read this BEFORE you need it)

Before an incident, confirm:

```bash
# 0.1 You have the pgBackRest repo credentials and they work.
#     These are SEPARATE from the application's EINVITE_OBJECT_STORAGE_* creds.
sudo -u postgres pgbackrest --stanza=einvite check
# Expected: "check command end: completed successfully"

# 0.2 The S3/R2/MinIO repo bucket is reachable from the restore host.
sudo -u postgres pgbackrest --stanza=einvite info
# Expected: lists full + diff backups and the latest WAL segment archived.

# 0.3 The staging cluster host is known and has the same PostgreSQL major version as production.
psql --version      # on staging host
psql --version      # on production host
# MUST match major version (e.g., both 15.x). Minor version differences are OK.

# 0.4 The staging cluster has enough disk: 2× the production DB size (room for restore + WAL replay).
df -h /var/lib/postgresql
```

If any preflight fails, **stop and fix it before an incident happens**. These are the exact things you cannot debug at 02:00.

## 1. Incident declaration

| Field | Value |
|-------|-------|
| Trigger | Production `/api/health/ready` returns HTTP 503 for > 60 s; OR primary PostgreSQL is unreachable; OR disk failure on the primary's host; OR data corruption detected (e.g., `audit_events` hash-chain broken, OR query results that contradict each other). |
| Declare | On-call engineer opens a P1 incident in the incident channel. Names an Incident Commander (IC). The IC owns all decisions below; everyone else executes. |
| Page | On-call rotation. If no response in 5 minutes, escalate. |
| Time zero | The clock for the RTO (30 min for Tier 1) starts at incident declaration, NOT at the first failure. |
| Comms | Status page updated within 5 minutes of declaration, even if "investigating." |

> **Do NOT attempt to "fix" the live primary.** A corrupted primary that is still accepting writes is worse than a dead primary — every additional write widens the RPO. If you suspect corruption, take the primary out of rotation FIRST, then restore.

## 2. Target selection

### 2.1 Choose the recovery point

You need a target timestamp for PITR (point-in-time recovery). The latest available WAL segment defines your upper bound. Aim for:

- **The latest committed transaction you trust.** If the corruption started at 02:00, target 01:59:55.
- **Never target "now".** If you target beyond the corruption, you replay the corruption. If you target a moment before the corruption, you lose at most the RPO window (≤ 5 min for Tier 1).

Find the latest WAL segment in the archive:

```bash
sudo -u postgres pgbackrest --stanza=einvite info
# Look at "wal archive minimum" and "prior" / "current" for the latest stanza.
# The latest available timestamp is the end of the most-recently-archived WAL segment.
```

Convert the WAL segment name to a timestamp (or pick a known-good time based on logs):

```bash
# A WAL segment named 0000000100000003/0000000C looks like timeline 1, log 3, seg 0x0C.
# To translate to wall-clock: find the last write in the WAL using pg_waldump:
sudo -u postgres pg_waldump /var/lib/postgresql/15/main/pg_wal/00000001000000030000000C | tail -5
# Look for the last "COMMIT" record; its timestamp is your latest recoverable instant.
```

Record the chosen PITR target as ISO 8601 UTC, e.g., `2026-09-14 01:59:55.000000+00`.

### 2.2 Choose the base backup

Pick the most recent **full** backup that is older than your PITR target. pgBackRest will replay WAL forward from there.

```bash
sudo -u postgres pgbackrest --stanza=einvite info --output=json | jq '.[0].backup | map(select(.type == "full")) | sort_by(.timestamp.start) | last'
```

Record the backup label, e.g., `20260914-000000F`.

## 3. Base restore to staging

**Target host:** the staging PostgreSQL cluster (NOT the production host — see §0.4). The staging host must have:

- Same PostgreSQL major version as production.
- Empty `$PGDATA` (or a `--delta` restore into a stopped cluster that will be wiped).
- Network access to the pgBackRest S3/R2/MinIO repo bucket.
- 2× the production DB size in free disk.

### 3.1 Stop the staging cluster (if running)

```bash
# If staging is up, stop it. NEVER run a restore against a running cluster.
sudo systemctl stop postgresql@15-restore_test 2>/dev/null || true
sudo -u postgres /usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/restore-test stop -m fast -w || true
```

### 3.2 Wipe the staging data directory

```bash
# SAFETY: refuse to wipe a non-empty dir. This guards against accidentally targeting production.
STAGING_PGDATA=/var/lib/postgresql/restore-test
if [[ -d "$STAGING_PGDATA" && -n "$(ls -A "$STAGING_PGDATA" 2>/dev/null)" ]]; then
  if [[ "${EINVITE_RESTORE_I_KNOW_THIS_WIPES_STAGING:-}" != "yes" ]]; then
    echo "ABORT: $STAGING_PGDATA is not empty. Set EINVITE_RESTORE_I_KNOW_THIS_WIPES_STAGING=yes to proceed."
    exit 2
  fi
fi
sudo -u postgres rm -rf "$STAGING_PGDATA"
sudo -u postgres mkdir -p "$STAGING_PGDATA"
sudo -u postgres chmod 0700 "$STAGING_PGDATA"
```

### 3.3 Restore the base backup

```bash
# Restore the most recent full backup, ready for WAL replay.
# --type=immediate stops WAL replay at the end of the base backup — we will replay forward next.
# (Alternatively, combine base + PITR in one step; see §3.4.)
sudo -u postgres pgbackrest --stanza=einvite \
  --pg1-path="$STAGING_PGDATA" \
  --type=immediate \
  --delta restore
```

### 3.4 (One-step alternative) Restore directly to the PITR target

If you already know your PITR target timestamp from §2.1, you can combine base restore + WAL replay in one command:

```bash
PITR_TARGET="2026-09-14 01:59:55.000000+00"

sudo -u postgres pgbackrest --stanza=einvite \
  --pg1-path="$STAGING_PGDATA" \
  --type=time \
  --target="$PITR_TARGET" \
  --target-action=promote \
  --delta restore
```

| Flag | Meaning |
|------|---------|
| `--type=time` | Recover to a wall-clock timestamp (PITR). |
| `--target="2026-09-14 01:59:55.000000+00"` | The chosen recovery point from §2.1. |
| `--target-action=promote` | After reaching the target, promote the cluster to a primary (accepts writes). Use `pause` if you want to inspect before promoting. |
| `--delta` | Skip blocks that already match (useful for re-running after a partial failure). |

The cluster is now restored but **not running**. Bring it up next.

## 4. WAL replay

If you used §3.3 (two-step), replay WAL forward to your target:

```bash
# Create recovery.signal so PostgreSQL enters recovery mode on start.
sudo -u postgres touch "$STAGING_PGDATA/recovery.signal"

# Configure recovery target in postgresql.auto.conf (overrides postgresql.conf).
sudo -u postgres tee -a "$STAGING_PGDATA/postgresql.auto.conf" <<EOF
restore_command = '/usr/bin/pgbackrest --stanza=einvite archive-get %f %p'
recovery_target_time = '$PITR_TARGET'
recovery_target_action = 'promote'
recovery_target_inclusive = true
EOF

# Start the staging cluster — it will enter recovery and replay WAL until the target.
sudo -u postgres /usr/lib/postgresql/15/bin/pg_ctl -D "$STAGING_PGDATA" -l /tmp/restore-replay.log start

# Tail the log. Recovery is done when you see:
#   "recovery stopping before commit of transaction N at time T"
#   "database system is ready to accept connections"
tail -f /tmp/restore-replay.log
```

If you used §3.4 (one-step), WAL replay already happened inside `pgbackrest restore`. Just start the cluster:

```bash
sudo -u postgres /usr/lib/postgresql/15/bin/pg_ctl -D "$STAGING_PGDATA" -l /tmp/restore-replay.log start
```

## 5. Validation

Run on the staging cluster, NOT production. Treat the staging cluster as the source of truth for the next 30 minutes.

### 5.1 Connection sanity

```bash
STAGING_PORT=55432   # use a non-prod port so it can run alongside prod
psql -p $STAGING_PORT -U postgres -d einvite -c 'SELECT version();'
# Expected: PostgreSQL 15.x on x86_64-pc-linux-gnu
```

### 5.2 Row counts (Tier 1 canary)

Compare against the most recent known-good snapshot. The daily restore-test (see `BACKUP-DR.md` §2.6) writes the most recent row counts to `/var/log/pgbackrest/restore-reports/restore-test-<stamp>.md` — use the latest one as the expected baseline.

```bash
psql -p $STAGING_PORT -U postgres -d einvite <<'SQL'
\echo == Tier 1 row counts ==
SELECT 'users' AS tbl, COUNT(*) FROM users
UNION ALL SELECT 'invitations', COUNT(*) FROM invitations
UNION ALL SELECT 'publications', COUNT(*) FROM publications
UNION ALL SELECT 'rsvps', COUNT(*) FROM rsvps
UNION ALL SELECT 'guests', COUNT(*) FROM guests
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events;

\echo == latest rsvp + invitation timestamps (operational canary) ==
SELECT MAX(created_at) AS latest_rsvp_unix_ms FROM rsvps;
SELECT MAX(updated_at) AS latest_invitation_unix_ms, COUNT(*) FILTER (WHERE archived = 0) AS active_invitations FROM invitations;
SQL
```

### 5.3 Hash-chain integrity (audit_events)

The `audit_events` table is hash-chained (`previous_hash + event_hash`, with BEFORE UPDATE/DELETE triggers that raise ABORT — see `src/python/server.py` lines 1137/1206-1207). Any restore that breaks the chain is a sign of corruption.

```sql
SELECT
  COUNT(*) AS total_events,
  COUNT(*) FILTER (WHERE previous_hash <> COALESCE(LAG(event_hash) OVER (ORDER BY created_at, id), '')) AS broken_links
FROM audit_events;
-- Expected: broken_links = 0. If not zero, the restore is corrupt — do not cutover.
```

### 5.4 Object-storage canary

The DB holds references to objects in S3/R2/MinIO; the objects themselves must still be present.

```sql
SELECT
  COUNT(*) AS total_asset_rows,
  COUNT(*) FILTER (WHERE object_id IS NOT NULL) AS rows_with_object_pointer
FROM assets;
```

Then sample a few `object_id`s and confirm they exist in the bucket:

```bash
# Pick 5 random object_ids from the assets table and verify each one resolves.
for OID in $(psql -p $STAGING_PORT -U postgres -d einvite -tA \
  -c "SELECT object_id FROM assets WHERE object_id IS NOT NULL ORDER BY RANDOM() LIMIT 5"); do
  aws s3api head-object --bucket "$EINVITE_OBJECT_STORAGE_BUCKET" \
    --key "$(psql -p $STAGING_PORT -U postgres -d einvite -tA \
      -c "SELECT path FROM stored_objects WHERE id = '$OID'")" \
    --query 'ContentLength' --output text || echo "MISSING: $OID"
done
```

### 5.5 Functional canary

Run the most recent smoke test against the staging cluster:

```bash
# Point a throwaway instance of the app at the staging DB and run smoke tests.
EINVITE_DATABASE_URL="postgresql://postgres@127.0.0.1:$STAGING_PORT/einvite" \
EINVITE_OBJECT_STORAGE_BUCKET="$EINVITE_OBJECT_STORAGE_BUCKET" \
EINVITE_COOKIE_SECURE=0 \
EINVITE_ALLOW_NO_SCANNER=1 \
PYTHONPATH=src/python:. \
python3 tests/smoke_test.py
```

Pass criteria: zero failures. A single flaky failure may be acceptable; investigate. Two or more = block cutover.

### 5.6 Validation gate

**Only proceed to cutover (§6) if ALL of the following hold:**

- [ ] §5.1 staging cluster is up and reachable.
- [ ] §5.2 row counts match the most recent restore-test baseline ±0 (Tier 1 tables MUST match exactly).
- [ ] §5.3 audit_events hash-chain has zero broken links.
- [ ] §5.4 sampled objects all exist in the bucket.
- [ ] §5.5 smoke tests pass.
- [ ] Measured RPO (time between PITR target and incident declaration) ≤ 5 minutes.
- [ ] Measured RTO (time from §1 declaration to now) ≤ 30 minutes — or about to exceed with a documented exception from the IC.

If any gate fails, **stop**. Re-evaluate the PITR target (§2.1). If the target was wrong, restart from §3.2 (wipe + restore). Do not patch around a failed gate.

## 6. Cutover

Once validation passes, the IC decides whether to cutover. **Cutover is the only step that touches production.** Everything above this line runs against staging.

### 6.1 Quiesce writes on the old primary (if it is still alive)

```bash
# Take the application out of the load balancer. Stop writes from reaching the old primary.
# (On a Kubernetes deployment: scale the deployment to 0, or change the service selector.)
sudo systemctl stop einvite.service   # or equivalent
```

### 6.2 Capture the old primary's tail WAL (if reachable)

If the old primary is still reachable and not corrupt, capture its final WAL segments so they can be archived into the pgBackRest repo, closing the RPO gap:

```bash
sudo -u postgres psql -c "SELECT pg_switch_wal();"
sudo -u postgres pgbackrest --stanza=einvite archive-push /var/lib/postgresql/15/main/pg_wal/<latest-wal-segment>
```

If the old primary is unreachable, skip this step. The RPO gap is whatever was in-flight between the last archived WAL segment and the failure.

### 6.3 Promote the staging cluster to production

The staging cluster was already promoted by `--target-action=promote` (§3.4) or by `recovery_target_action = 'promote'` (§4). It is now a writable primary.

### 6.4 Re-point the application at the restored primary

Update the production application's environment:

```bash
# Point the app at the restored cluster.
# Either: (a) re-IP the staging host to the production host's address (preferred if networking allows),
#     or (b) update EINVITE_DATABASE_URL to the staging host's connection string.

# Example (b):
export EINVITE_DATABASE_URL="postgresql://einvite_app:****@restored-host.internal:5432/einvite"

# Start the app.
sudo systemctl start einvite.service

# Health check.
curl -fsS https://invite.example.com/api/health/ready && echo OK || echo FAIL
```

### 6.5 Announce

- Status page: update from "investigating" to "resolved — restored from backup at <timestamp>, measured RPO <X>, measured RTO <Y>."
- Incident channel: post the timeline.
- Within 24 hours: file the postmortem (template in `BACKUP-DR.md` §5.4).

## 7. Rollback to previous primary

If the cutover has a problem (validation missed something, application doesn't start against the restored data, customer reports of broken invitations within 10 minutes of cutover), the IC may decide to roll back to the *previous* primary.

Rollback is only possible if:

- The previous primary is still alive and was not corrupted (just degraded).
- OR: a second pgBackRest restore target is available (e.g., the pre-incident state — though this would lose the post-incident writes that did make it).

### 7.1 Quiesce writes on the restored (current) primary

```bash
sudo systemctl stop einvite.service
```

### 7.2 Re-point the application at the previous primary

```bash
# Revert EINVITE_DATABASE_URL to the pre-cutover value.
export EINVITE_DATABASE_URL="postgresql://einvite_app:****@old-primary.internal:5432/einvite"

# Start the app.
sudo systemctl start einvite.service

# Health check.
curl -fsS https://invite.example.com/api/health/ready && echo OK || echo FAIL
```

### 7.3 Risk acknowledgement

Rollback loses any writes that landed on the restored (current) primary between cutover and rollback. The IC must decide whether the lost writes are acceptable. If a Tier 1 table (e.g., `rsvps`) lost writes, the customers affected must be identified and contacted.

### 7.4 Document

A rollback MUST trigger a postmortem regardless of outcome. The fact that rollback was needed means validation (§5) missed something. File an action item to strengthen the validation step.

## 8. Common failures (and what to do)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pgbackrest restore` fails with "WAL segment X not found in archive" | WAL retention expired before the base backup it belongs to (the #1 failure mode). | Pick an earlier base backup from §2.2 whose WAL segments are still in archive. If none exists, escalate — you have lost data. |
| `psql: FATAL: database "einvite" does not exist` | The DB name in `EINVITE_DATABASE_URL` does not match the cluster's DB name. | The cluster DB name is whatever `pgbackrest restore` produces (it matches the source cluster). Update `EINVITE_DATABASE_URL` to match, or `CREATE DATABASE einvite; pg_restore --dbname=einvite ...` if needed (rare with pgBackRest, which restores the cluster as-is). |
| Restore finishes in 1 minute but no rows in `rsvps` | PITR target was set to before the last `TRUNCATE`/`DELETE`. | Pick a later PITR target. The `audit_events` table will show the offending DDL — query `SELECT * FROM audit_events WHERE action LIKE 'rsvp.%' ORDER BY created_at DESC LIMIT 20;` |
| Staging cluster runs out of disk during restore | `--delta` was not used and the staging PGDATA is on a small volume. | Provision 2× production DB size on the staging host. Add an action item to the preflight (§0). |
| `pgbackrest check` returns "no backup command" | `archive_command` was never set on the primary, so no WAL was archived. | This is a pre-incident failure. Stop everything, fix `archive_command` and `archive_mode = on`, restart the primary, take a new full backup. The current backups are NOT usable for PITR — only for snapshot recovery to the time of the base backup. |
| Application fails `EINVITE_COOKIE_SECURE=1` check on restored host | The restored host's TLS termination is not configured. | Run behind a TLS-terminating reverse proxy (Caddy/Nginx) before enabling `EINVITE_COOKIE_SECURE=1`. |
| Object-storage canary (§5.4) reports missing objects | Objects were deleted from the bucket between the DB backup and now. | Restore from bucket versioning (delete-marker roll-back). See `BACKUP-DR.md` §4.1. |

## 9. Quick reference (one screen)

```text
1. DECLARE     On-call opens P1, names IC, starts RTO clock (target 30 min, Tier 1).
2. SELECT      pgbackrest info → pick latest full + latest WAL → choose PITR target ≤5 min before incident.
3. RESTORE     pgbackrest --type=time --target=<ts> --target-action=promote --delta restore
                     to STAGING PGDATA (never production).
4. REPLAY      pg_ctl start → tail recovery log → wait for "ready to accept connections".
5. VALIDATE    row counts match baseline; audit_events hash-chain intact; objects exist; smoke tests pass.
6. CUTOVER     (IC decision) stop old primary; point EINVITE_DATABASE_URL at restored; start app; health check.
7. ROLLBACK    (IC decision) revert EINVITE_DATABASE_URL; start old primary; file postmortem.
```

## 10. Change history

| Date | Change |
|------|--------|
| 2026-09-14 | Initial Phase 1c deliverable. 8-step runbook with explicit pgBackRest commands, validation gates, and rollback procedure. |
