#!/usr/bin/env bash
# scripts/backup.sh
# Manual backup script for NewsAnalysis database

set -e

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/newsanalysis}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"
DB_FILE="${DB_FILE:-$INSTALL_DIR/news.db}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/news_backup_$DATE.db"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}NewsAnalysis Database Backup${NC}"
echo "============================="
echo ""

# Create backup directory if doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}Error: Database file not found: $DB_FILE${NC}"
    exit 1
fi

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"

# Compress backup
echo -e "${YELLOW}Compressing backup...${NC}"
gzip "$BACKUP_FILE"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# Display results
FILE_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo -e "${GREEN}Backup completed successfully!${NC}"
echo "File: $COMPRESSED_FILE"
echo "Size: $FILE_SIZE"
echo ""

# Optional: Clean old backups (keep last 30 days)
if [ "${CLEANUP:-yes}" == "yes" ]; then
    echo -e "${YELLOW}Cleaning old backups (>30 days)...${NC}"
    DELETED=$(find "$BACKUP_DIR" -name "news_backup_*.db.gz" -mtime +30 -delete -print | wc -l)
    echo "Deleted $DELETED old backup(s)"
fi

echo ""
echo "Backup complete!"
