#!/bin/bash

# PostgreSQL to Supabase Automated Backup Script
# This script backs up PostgreSQL database and restores it to Supabase daily

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/root/backups"
LOG_FILE="/var/log/postgres_backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=30

# Database connection details
LOCAL_HOST="localhost"
LOCAL_PORT="5432"
LOCAL_USER="postgres"
LOCAL_DB="postgres"

# Supabase connection details
SUPABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"

# Create directories if they don't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Error handling function
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "postgres_backup_*.sql" -type f -mtime +$RETENTION_DAYS -delete
    local deleted_count=$(find "$BACKUP_DIR" -name "postgres_backup_*.sql" -type f -mtime +$RETENTION_DAYS | wc -l)
    if [ "$deleted_count" -gt 0 ]; then
        log "Deleted $deleted_count old backup files"
    else
        log "No old backup files to delete"
    fi
}

# Main backup function
perform_backup() {
    log "Starting PostgreSQL backup process..."

    # Step 1: Create backup from local PostgreSQL
    log "Creating backup from local PostgreSQL..."
    if ! pg_dump -h "$LOCAL_HOST" -p "$LOCAL_PORT" -U "$LOCAL_USER" -d "$LOCAL_DB" > "$BACKUP_FILE"; then
        error_exit "Failed to create backup from local PostgreSQL"
    fi

    # Check if backup file was created and has content
    if [ ! -s "$BACKUP_FILE" ]; then
        error_exit "Backup file is empty or was not created"
    fi

    local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created successfully: $BACKUP_FILE (Size: $backup_size)"

    # Step 2: Restore to Supabase
    log "Restoring backup to Supabase..."
    if ! psql "$SUPABASE_URL" -f "$BACKUP_FILE"; then
        error_exit "Failed to restore backup to Supabase"
    fi

    log "Backup restored to Supabase successfully"
}

# Main execution
main() {
    log "=== PostgreSQL to Supabase Backup Started ==="

    # Perform backup
    perform_backup

    # Cleanup old backups
    cleanup_old_backups

    log "=== PostgreSQL to Supabase Backup Completed Successfully ==="
    log "Backup file: $BACKUP_FILE"
    log "Next cleanup will remove files older than $RETENTION_DAYS days"
}

# Run main function
main "$@"
