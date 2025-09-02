#!/bin/bash

# PostgreSQL to Supabase Automated Backup Script (with Clean Restore)
# This script backs up PostgreSQL database and performs a clean restore to Supabase

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
LOCAL_PASSWORD="password"
LOCAL_DB="postgres"

# Supabase connection details
# Local Supabase password (default "password" unless overridden in ENV_FILE)
SUPABASE_LOCAL_PASSWORD=postgres
SUPABASE_LOCAL_URL="postgresql://postgres:${SUPABASE_LOCAL_PASSWORD}@127.0.0.1:54322/postgres"
# Optional: set to your Supabase Cloud DSN (full URL), e.g.,
# postgresql://postgres:YOUR_URL_ENCODED_PASSWORD@db.your-project.supabase.co:5432/postgres
SUPABASE_CLOUD_URL="${SUPABASE_CLOUD_URL:-}"

# Set environment variables for password-less connections (for local pg_dump)
export PGPASSWORD="$LOCAL_PASSWORD"

# Create directories if they don't exist
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Error handling function
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Function to clear a target database (by URL)
clear_database() {
    local target_url="$1"
    local target_label="${2:-Target}"
    log "Clearing ${target_label} database..."

    # SQL commands to drop all tables, sequences, and constraints
    local CLEAR_SQL="
    -- Drop all tables in reverse dependency order
    DROP TABLE IF EXISTS patent_tech_sectors CASCADE;
    DROP TABLE IF EXISTS patent_departments CASCADE;
    DROP TABLE IF EXISTS patent_assignees CASCADE;
    DROP TABLE IF EXISTS patents_list_demo CASCADE;
    DROP TABLE IF EXISTS patents_list CASCADE;
    DROP TABLE IF EXISTS search_logs CASCADE;
    DROP TABLE IF EXISTS voiceprint_library CASCADE;
    DROP TABLE IF EXISTS ai_meeting_app_owner_control CASCADE;
    DROP TABLE IF EXISTS department_dictionary CASCADE;
    DROP TABLE IF EXISTS departments CASCADE;
    DROP TABLE IF EXISTS assignees CASCADE;
    DROP TABLE IF EXISTS tech_sectors CASCADE;

    -- Drop sequences
    DROP SEQUENCE IF EXISTS ai_meeting_app_owner_control_sys_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS assignees_assignee_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS department_dictionary_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS departments_department_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS patents_list_demo_sys_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS patents_list_sys_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS search_logs_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS techsectors_tech_sector_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS voiceprint_library_sys_id_seq CASCADE;
    "

    # Execute the clear commands
    if ! echo "$CLEAR_SQL" | psql "$target_url" -q; then
        error_exit "Failed to clear ${target_label} database"
    fi

    log "${target_label} database cleared successfully"
}

# Function to restore the backup into a target database (by URL)
restore_to_database() {
    local target_url="$1"
    local target_label="${2:-Target}"
    log "Restoring backup to ${target_label}..."
    if ! psql "$target_url" -f "$BACKUP_FILE"; then
        error_exit "Failed to restore backup to ${target_label}"
    fi
    log "Backup restored to ${target_label} successfully"
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

    # Step 2: Clear and restore to local Supabase
    clear_database "$SUPABASE_LOCAL_URL" "Supabase Local"
    restore_to_database "$SUPABASE_LOCAL_URL" "Supabase Local"

    # Step 3: If configured, also clear and restore to Supabase Cloud
    if [ -n "$SUPABASE_CLOUD_URL" ]; then
        clear_database "$SUPABASE_CLOUD_URL" "Supabase Cloud"
        restore_to_database "$SUPABASE_CLOUD_URL" "Supabase Cloud"
    else
        log "Supabase Cloud URL not set; skipping cloud restore"
    fi
}

# Main execution
main() {
    log "=== PostgreSQL to Supabase Clean Backup Started ==="

    # Perform backup
    perform_backup

    # Cleanup old backups
    cleanup_old_backups

    log "=== PostgreSQL to Supabase Clean Backup Completed Successfully ==="
    log "Backup file: $BACKUP_FILE"
    log "Next cleanup will remove files older than $RETENTION_DAYS days"
}

# Run main function
main "$@"
