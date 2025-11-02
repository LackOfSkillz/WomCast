#!/bin/bash
# Automated database backup script for WomCast
# Runs nightly via cron to create and maintain backups

set -euo pipefail

# Configuration
DB_PATH="${DB_PATH:-/opt/womcast/data/womcast.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/womcast/backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-7}"
LOG_FILE="${LOG_FILE:-/var/log/womcast/backup.log}"
PYTHON_BIN="${PYTHON_BIN:-/opt/womcast/.venv/bin/python}"

# Create directories
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $*" >&2
}

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    error "Database not found: $DB_PATH"
    exit 1
fi

log "=== Starting database backup ==="
log "Database: $DB_PATH"
log "Backup directory: $BACKUP_DIR"

# Create backup
log "Creating backup..."
if $PYTHON_BIN -m common.backup backup "$DB_PATH" "$BACKUP_DIR" >> "$LOG_FILE" 2>&1; then
    log "Backup created successfully"
else
    error "Backup creation failed"
    exit 1
fi

# Verify backup integrity
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "womcast_backup_*.db" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)
if [ -n "$LATEST_BACKUP" ]; then
    log "Verifying backup: $(basename "$LATEST_BACKUP")"
    if $PYTHON_BIN -m common.backup verify "$LATEST_BACKUP" >> "$LOG_FILE" 2>&1; then
        log "Backup verification passed"
    else
        error "Backup verification failed"
        exit 1
    fi
else
    error "No backup file found after creation"
    exit 1
fi

# Cleanup old backups
log "Cleaning up old backups (keeping $KEEP_BACKUPS most recent)..."
if $PYTHON_BIN -m common.backup cleanup "$BACKUP_DIR" "$KEEP_BACKUPS" >> "$LOG_FILE" 2>&1; then
    log "Cleanup completed"
else
    error "Cleanup failed"
    exit 1
fi

# List remaining backups
log "Current backups:"
ls -lh "$BACKUP_DIR"/womcast_backup_*.db 2>/dev/null | tee -a "$LOG_FILE" || log "No backups found"

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "unknown")
log "Total backup size: $BACKUP_SIZE"

log "=== Backup completed successfully ==="

exit 0
