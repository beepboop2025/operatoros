#!/usr/bin/env bash
#
# backup.sh - Dump OperatorOS PostgreSQL database and upload to S3
#
# Usage:
#   ./scripts/backup.sh
#   S3_BUCKET=my-bucket RETENTION_DAYS=14 ./scripts/backup.sh
#
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
TIMESTAMP=$(date -u +"%Y-%m-%dT%H%M%SZ")
BACKUP_DIR="${BACKUP_DIR:-/tmp/operatoros-backups}"
S3_BUCKET="${S3_BUCKET:-operatoros-backups}"
S3_PREFIX="${S3_PREFIX:-db}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-operatoros}"
DB_USER="${DB_USER:-operatoros}"

DUMP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

# ── Pre-flight checks ────────────────────────────────────────────────────────
for cmd in pg_dump gzip aws; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: Required command '$cmd' not found in PATH." >&2
        exit 1
    fi
done

mkdir -p "$BACKUP_DIR"

# ── Dump ──────────────────────────────────────────────────────────────────────
echo "[$(date -u +%H:%M:%S)] Starting database dump: ${DB_NAME}@${DB_HOST}:${DB_PORT}"

pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --verbose 2>/dev/null \
    | gzip > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "[$(date -u +%H:%M:%S)] Dump complete: $DUMP_FILE ($DUMP_SIZE)"

# ── Upload to S3 ─────────────────────────────────────────────────────────────
S3_KEY="s3://${S3_BUCKET}/${S3_PREFIX}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date -u +%H:%M:%S)] Uploading to $S3_KEY"

aws s3 cp "$DUMP_FILE" "$S3_KEY" \
    --storage-class STANDARD_IA \
    --only-show-errors

echo "[$(date -u +%H:%M:%S)] Upload complete."

# ── Clean up old remote backups ───────────────────────────────────────────────
echo "[$(date -u +%H:%M:%S)] Removing remote backups older than ${RETENTION_DAYS} days..."

CUTOFF_DATE=$(date -u -d "-${RETENTION_DAYS} days" +"%Y-%m-%d" 2>/dev/null || \
              date -u -v-${RETENTION_DAYS}d +"%Y-%m-%d")

aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    if [[ -n "$FILE_NAME" && "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
        echo "  Deleting: $FILE_NAME"
        aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${FILE_NAME}" --only-show-errors
    fi
done

# ── Clean up local dump ──────────────────────────────────────────────────────
rm -f "$DUMP_FILE"

echo "[$(date -u +%H:%M:%S)] Backup pipeline complete."
