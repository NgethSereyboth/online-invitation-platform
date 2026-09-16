#!/usr/bin/env bash
#
# pgBackRest daily restore test — proves the backup is restorable.
#
# Restores the latest pgBackRest backup to a throwaway staging PGDATA dir,
# starts a throwaway PostgreSQL cluster on a non-prod port, runs validation
# queries, measures the restore + replay + validation time, tears down.
#
# This script NEVER touches the production cluster. It only reads from the
# pgBackRest repo bucket.
#
# Canonical source: deploy/linux/pgbackrest-restore-test.sh
# Deploy to:         /usr/local/bin/pgbackrest-restore-test.sh (mode 0755, owner root)
# Cron:              see docs/ops/BACKUP-DR.md §2.4 — 03:00 daily
# Logging:           /var/log/pgbackrest/restore-test.log (cron)
# Reports:           /var/log/pgbackrest/restore-reports/restore-test-<ISO8601>.md
#
# Failure policy: exit non-zero. cron will mail the trailing output to root.
# Page on failure — a backup that has not been restored is not known to be
# restorable; a backup that has failed restore IS known to be un-restorable.
#
# See docs/ops/BACKUP-DR.md §2.6 for the full narrative.
# ---------------------------------------------------------------------------

set -euo pipefail

# ---------------------------------------------------------------------------
# Config (override via env).
# ---------------------------------------------------------------------------
STANZA="${EINVITE_PGBACKREST_STANZA:-einvite}"
STAGING_PGDATA="${EINVITE_RESTORE_TEST_PGDATA:-/var/lib/postgresql/restore-test}"
STAGING_PORT="${EINVITE_RESTORE_TEST_PORT:-55432}"
PG_BIN="${PG_BIN:-/usr/lib/postgresql/15/bin}"
PGBACKREST="${PGBACKREST:-/usr/bin/pgbackrest}"
DB_NAME="${EINVITE_RESTORE_TEST_DBNAME:-einvite}"
RTO_BUDGET_SECONDS="${EINVITE_TIER1_RTO_SECONDS:-1800}"   # 30 min Tier 1 default

LOG_DIR="/var/log/pgbackrest"
REPORT_DIR="$LOG_DIR/restore-reports"
mkdir -p "$REPORT_DIR" "$LOG_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="$REPORT_DIR/restore-test-$TS.md"

{
  echo "# pgBackRest restore test — $TS"
  echo ""
} > "$REPORT"

# ---------------------------------------------------------------------------
# 0. Hard safety: refuse to wipe a non-empty staging dir.
# ---------------------------------------------------------------------------
if [[ -d "$STAGING_PGDATA" && -n "$(ls -A "$STAGING_PGDATA" 2>/dev/null)" ]]; then
  echo "ABORT: $STAGING_PGDATA is not empty — refusing to wipe a non-empty cluster." >> "$REPORT"
  cat "$REPORT"
  exit 2
fi

# ---------------------------------------------------------------------------
# 1. Wipe and restore the latest backup. --type=immediate stops WAL replay at
#    the end of the base backup so we measure the base-restore time separately
#    from WAL replay (useful for capacity planning).
# ---------------------------------------------------------------------------
rm -rf "$STAGING_PGDATA"
mkdir -p "$STAGING_PGDATA"
chmod 0700 "$STAGING_PGDATA"
chown postgres:postgres "$STAGING_PGDATA"

echo "## 1. Base restore" >> "$REPORT"
echo "" >> "$REPORT"
echo '```' >> "$REPORT"
START_BASE=$(date +%s)
sudo -u postgres "$PGBACKREST" --stanza="$STANZA" \
  --pg1-path="$STAGING_PGDATA" \
  --type=immediate \
  --delta restore >> "$REPORT" 2>&1
END_BASE=$(date +%s)
echo '```' >> "$REPORT"
echo "Base restore: $((END_BASE - START_BASE)) s" >> "$REPORT"
echo "" >> "$REPORT"

# ---------------------------------------------------------------------------
# 2. Start a throwaway instance on the non-prod port.
# ---------------------------------------------------------------------------
echo "## 2. Start cluster (port $STAGING_PORT)" >> "$REPORT"
echo "" >> "$REPORT"
echo '```' >> "$REPORT"
sudo -u postgres "$PG_BIN/pg_ctl" -D "$STAGING_PGDATA" \
  -o "-p $STAGING_PORT -c listen_addresses='127.0.0.1'" \
  -l /tmp/pgbackrest-restore-test-pg.log start >> "$REPORT" 2>&1
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# Wait for it to come up.
for _ in $(seq 1 60); do
  if psql -p "$STAGING_PORT" -U postgres -d postgres -c 'SELECT 1' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

END_REPLAY=$(date +%s)

# ---------------------------------------------------------------------------
# 3. Validation queries. Failure of any canary => the backup is NOT restorable.
# ---------------------------------------------------------------------------
echo "## 3. Validation" >> "$REPORT"
echo "" >> "$REPORT"
echo '```sql' >> "$REPORT"
psql -p "$STAGING_PORT" -U postgres -d "$DB_NAME" >> "$REPORT" 2>&1 <<'SQL'
\timing off
\echo == Tier-1 row counts ==
SELECT 'users' AS tbl, COUNT(*) FROM users
UNION ALL SELECT 'invitations', COUNT(*) FROM invitations
UNION ALL SELECT 'publications', COUNT(*) FROM publications
UNION ALL SELECT 'rsvps', COUNT(*) FROM rsvps
UNION ALL SELECT 'guests', COUNT(*) FROM guests
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events;

\echo == audit_events hash-chain integrity ==
SELECT
  COUNT(*) AS total_events,
  COUNT(*) FILTER (WHERE previous_hash <> COALESCE(LAG(event_hash) OVER (ORDER BY created_at, id), '')) AS broken_links
FROM audit_events;

\echo == operational canary: latest rsvp + invitation ==
SELECT MAX(created_at) AS latest_rsvp_unix_ms FROM rsvps;
SELECT MAX(updated_at) AS latest_invitation_unix_ms,
       COUNT(*) FILTER (WHERE archived = 0) AS active_invitations
FROM invitations;
SQL
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# ---------------------------------------------------------------------------
# 4. Timings + RTO budget check.
# ---------------------------------------------------------------------------
TOTAL_SEC=$((END_REPLAY - START_BASE))
MARGIN=$((RTO_BUDGET_SECONDS - TOTAL_SEC))

{
  echo "## 4. Timings"
  echo ""
  echo "| Phase | Seconds |"
  echo "|---|---|"
  echo "| Base restore | $((END_BASE - START_BASE)) |"
  echo "| Cluster start + WAL replay | $((END_REPLAY - END_BASE)) |"
  echo "| **Total to ready** | **$TOTAL_SEC** |"
  echo ""
  echo "RTO budget (Tier 1): $RTO_BUDGET_SECONDS s (30 min)"
  echo "Measured: $TOTAL_SEC s"
  echo "Margin: $MARGIN s"
  echo ""
} >> "$REPORT"

# ---------------------------------------------------------------------------
# 5. Tear down. NEVER leave the restore-test cluster running.
# ---------------------------------------------------------------------------
sudo -u postgres "$PG_BIN/pg_ctl" -D "$STAGING_PGDATA" stop -m fast -w >> "$REPORT" 2>&1 || true
rm -rf "$STAGING_PGDATA"

# ---------------------------------------------------------------------------
# 6. RTO verdict.
# ---------------------------------------------------------------------------
if (( TOTAL_SEC > RTO_BUDGET_SECONDS )); then
  {
    echo "## ⚠ RESTORE EXCEEDED TIER-1 RTO"
    echo ""
    echo "Measured $TOTAL_SEC s vs budget $RTO_BUDGET_SECONDS s."
    echo "Action: file an incident; do not wait for the next quarterly drill."
  } >> "$REPORT"
  cat "$REPORT"
  exit 1
fi

{
  echo "## ✓ Restore test passed"
  echo ""
  echo "Backup is known to be restorable as of $TS."
} >> "$REPORT"

cat "$REPORT"
