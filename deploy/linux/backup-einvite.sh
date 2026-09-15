#!/usr/bin/env bash
#
# eInvite local/laptop backup wrapper.
#
# Delegates to src/python/backup_restore.py — a portable, verified local ZIP
# backup helper that supports both SQLite (default dev DB) and PostgreSQL
# (when EINVITE_DATABASE_URL is set, via pg_dump --format=custom).
#
# This wrapper is the supported entry point for laptop / single-host / dev
# deployments (see docs/LINUX_LAPTOP_HOSTING.md). For production PostgreSQL
# clusters, this script is NOT the primary backup — pgBackRest + continuous
# WAL archiving is (see docs/ops/BACKUP-DR.md). This script may still be used
# for ad-hoc logical exports on a production cluster.
#
# ---------------------------------------------------------------------------
# Bug history (fixed 2026-09-14, Phase 1c):
#
#   Prior version had three wrong paths:
#     DB_PATH="$PROJECT_ROOT/data/einvite.db"   # wrong name; actual file is invites.db
#     MEDIA_DIR="$PROJECT_ROOT/media"           # wrong dir; actual is $EINVITE_DATA_DIR/uploads
#     $PROJECT_ROOT/server/config.py            # does not exist; no such file in the repo
#
#   And it used `cp` to copy the SQLite file, which can capture a half-written
#   WAL state. The current version delegates to backup_restore.py which uses
#   sqlite3.backup() (online, consistent snapshot) and verifies the result.
#
# ---------------------------------------------------------------------------

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths.
# ---------------------------------------------------------------------------

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# EINVITE_DATA_DIR is the canonical env var (see src/python/server.py and
# src/python/backup_restore.py). Default to ./data for laptop installs.
DATA_DIR="${EINVITE_DATA_DIR:-$PROJECT_ROOT/data}"

# Output directory and retention. Both overridable via env for cron use.
BACKUP_DIR="${EINVITE_BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETENTION_DAYS="${EINVITE_BACKUP_RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="$BACKUP_DIR/einvite-backup-$STAMP.zip"

# ---------------------------------------------------------------------------
# Run the Python helper.
# ---------------------------------------------------------------------------
# backup_restore.py reads EINVITE_DATABASE_URL + EINVITE_DATA_DIR itself, so we
# just pass it the output path. It writes a manifest with per-file SHA-256
# and runs PRAGMA integrity_check (SQLite) or pg_restore --list (PostgreSQL).

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON not found on PATH." >&2
  exit 127
fi

# PYTHONPATH mirrors the runtime layout used by src/python/server.py
# (see docs/PRODUCTION_DEPLOYMENT.md and the quickstart in README.md).
export PYTHONPATH="src/python:.${PYTHONPATH:+:$PYTHONPATH}"

echo "[backup-einvite] creating verified backup: $ARCHIVE"
"$PYTHON" src/python/backup_restore.py create "$ARCHIVE"

# ---------------------------------------------------------------------------
# Verify the backup immediately. A backup that has not been restored-verified
# is not known to be restorable (see docs/ops/BACKUP-DR.md §2.6).
# ---------------------------------------------------------------------------
echo "[backup-einvite] verifying backup integrity…"
"$PYTHON" src/python/backup_restore.py verify "$ARCHIVE"

# ---------------------------------------------------------------------------
# Prune old backups. Only delete files matching our naming pattern to avoid
# wiping user-managed files in $BACKUP_DIR.
# ---------------------------------------------------------------------------
if [[ "$RETENTION_DAYS" -gt 0 ]]; then
  echo "[backup-einvite] pruning backups older than $RETENTION_DAYS day(s)…"
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'einvite-backup-*.zip' \
    -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
fi

echo "[backup-einvite] done: $ARCHIVE"
echo "[backup-einvite] to test-restore, run:"
echo "  PYTHONPATH=src/python:. $PYTHON src/python/backup_restore.py restore $ARCHIVE /tmp/einvite-restore-test --force"
