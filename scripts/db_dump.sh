#!/bin/bash
# Dump the paranormal tracker database to a recoverable SQL file
# Run this before switching machines

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DUMP_FILE="$REPO_ROOT/data/paranormal_tracker.sql"

# Create data directory if it doesn't exist
mkdir -p "$REPO_ROOT/data"

echo "Dumping database to $DUMP_FILE..."

docker exec paranormal-tracker-db pg_dump -U paranormal paranormal_tracker > "$DUMP_FILE"

# Compress it
gzip -f "$DUMP_FILE"

echo "Done! Dump saved to ${DUMP_FILE}.gz"
echo "Size: $(du -h "${DUMP_FILE}.gz" | cut -f1)"
echo ""
echo "To restore on another machine:"
echo "  ./scripts/db_restore.sh"
