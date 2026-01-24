#!/bin/bash
# Restore the paranormal tracker database from a dump file
# Run this after switching machines (after docker-compose up -d)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DUMP_FILE="$REPO_ROOT/data/paranormal_tracker.sql.gz"

if [ ! -f "$DUMP_FILE" ]; then
    echo "Error: Dump file not found at $DUMP_FILE"
    echo "Run ./scripts/db_dump.sh on the source machine first."
    exit 1
fi

echo "Restoring database from $DUMP_FILE..."

# Check if container is running
if ! docker ps | grep -q paranormal-tracker-db; then
    echo "Error: Database container not running. Run 'docker-compose up -d' first."
    exit 1
fi

# Drop and recreate database to ensure clean state
echo "Resetting database..."
docker exec paranormal-tracker-db psql -U paranormal -d postgres -c "DROP DATABASE IF EXISTS paranormal_tracker;"
docker exec paranormal-tracker-db psql -U paranormal -d postgres -c "CREATE DATABASE paranormal_tracker;"

# Restore from dump
echo "Importing data..."
gunzip -c "$DUMP_FILE" | docker exec -i paranormal-tracker-db psql -U paranormal -d paranormal_tracker

# Verify
COUNT=$(docker exec paranormal-tracker-db psql -U paranormal -d paranormal_tracker -t -c "SELECT COUNT(*) FROM stories;")
echo ""
echo "Done! Restored $COUNT stories."
