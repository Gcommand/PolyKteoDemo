#!/bin/bash

# Setup Cron Job for PostgreSQL to Supabase Backup
# This script sets up a daily cron job to run the backup script

set -e

# Configuration
SCRIPT_PATH="/root/postgres_backup_supabase_clean.sh"
CRON_TIME="0 2 * * *"  # Daily at 2:00 AM
CRON_JOB="$CRON_TIME $SCRIPT_PATH"

# Function to add cron job
add_cron_job() {
    echo "Setting up daily PostgreSQL backup cron job..."

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
        echo "Cron job already exists. Updating..."
        # Remove existing cron job
        crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | crontab -
    fi

    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

    echo "Cron job added successfully!"
    echo "Backup will run daily at 2:00 AM"
}

# Function to list current cron jobs
list_cron_jobs() {
    echo "Current cron jobs:"
    crontab -l
}

# Function to test the backup script
test_backup_script() {
    echo "Testing backup script..."
    if [ -x "$SCRIPT_PATH" ]; then
        echo "Script is executable"
    else
        echo "Making script executable..."
        chmod +x "$SCRIPT_PATH"
    fi

    echo "Running test backup (this will create a backup, clear Supabase, and restore)..."
    bash "$SCRIPT_PATH"
}

# Function to remove cron job
remove_cron_job() {
    echo "Removing PostgreSQL backup cron job..."
    crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | crontab -
    echo "Cron job removed"
}

# Main menu
show_menu() {
    echo "=== PostgreSQL to Supabase Backup Setup ==="
    echo "1. Add daily cron job (2:00 AM)"
    echo "2. Test backup script now"
    echo "3. List current cron jobs"
    echo "4. Remove cron job"
    echo "5. Exit"
    echo ""
    read -p "Choose an option (1-5): " choice

    case $choice in
        1)
            add_cron_job
            ;;
        2)
            test_backup_script
            ;;
        3)
            list_cron_jobs
            ;;
        4)
            remove_cron_job
            ;;
        5)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option. Please choose 1-5."
            show_menu
            ;;
    esac
}

# Run menu if no arguments provided
if [ $# -eq 0 ]; then
    show_menu
else
    # Allow direct commands
    case $1 in
        add)
            add_cron_job
            ;;
        test)
            test_backup_script
            ;;
        list)
            list_cron_jobs
            ;;
        remove)
            remove_cron_job
            ;;
        *)
            echo "Usage: $0 [add|test|list|remove]"
            exit 1
            ;;
    esac
fi
