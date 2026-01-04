#!/usr/bin/env bash
# scripts/maintenance.sh
# Maintenance script for NewsAnalysis system

set -e

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/newsanalysis}"
DB_FILE="${DB_FILE:-$INSTALL_DIR/news.db}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}NewsAnalysis Maintenance${NC}"
echo "========================"
echo ""

# Database statistics before maintenance
echo -e "${BLUE}Database Statistics (Before):${NC}"
sqlite3 "$DB_FILE" <<EOF
.mode column
.headers on
SELECT
    'articles' as table_name,
    COUNT(*) as row_count,
    ROUND(SUM(LENGTH(content)) / 1024.0 / 1024.0, 2) as content_mb
FROM articles
UNION ALL
SELECT
    'api_calls' as table_name,
    COUNT(*) as row_count,
    0 as content_mb
FROM api_calls
UNION ALL
SELECT
    'pipeline_runs' as table_name,
    COUNT(*) as row_count,
    0 as content_mb
FROM pipeline_runs
UNION ALL
SELECT
    'digests' as table_name,
    COUNT(*) as row_count,
    0 as content_mb
FROM digests;
EOF
echo ""

# Vacuum database
echo -e "${YELLOW}Running VACUUM to reclaim space...${NC}"
sqlite3 "$DB_FILE" "VACUUM;"
echo "VACUUM completed"
echo ""

# Analyze database for query optimization
echo -e "${YELLOW}Running ANALYZE for query optimization...${NC}"
sqlite3 "$DB_FILE" "ANALYZE;"
echo "ANALYZE completed"
echo ""

# Clean old articles (optional)
if [ "${CLEANUP_OLD_ARTICLES:-yes}" == "yes" ]; then
    echo -e "${YELLOW}Deleting articles older than $RETENTION_DAYS days...${NC}"
    DELETED=$(sqlite3 "$DB_FILE" "DELETE FROM articles WHERE created_at < datetime('now', '-$RETENTION_DAYS days'); SELECT changes();")
    echo "Deleted $DELETED old article(s)"
    echo ""
fi

# Clean expired cache entries
echo -e "${YELLOW}Cleaning expired cache entries...${NC}"
DELETED_CACHE=$(sqlite3 "$DB_FILE" <<EOF
DELETE FROM classification_cache WHERE created_at < datetime('now', '-30 days');
SELECT changes();
EOF
)
echo "Deleted $DELETED_CACHE expired classification cache entries"

DELETED_CONTENT_CACHE=$(sqlite3 "$DB_FILE" <<EOF
DELETE FROM content_fingerprints WHERE created_at < datetime('now', '-90 days');
SELECT changes();
EOF
)
echo "Deleted $DELETED_CONTENT_CACHE expired content cache entries"
echo ""

# Database statistics after maintenance
echo -e "${BLUE}Database Statistics (After):${NC}"
sqlite3 "$DB_FILE" <<EOF
.mode column
.headers on
SELECT
    'articles' as table_name,
    COUNT(*) as row_count,
    ROUND(SUM(LENGTH(content)) / 1024.0 / 1024.0, 2) as content_mb
FROM articles
UNION ALL
SELECT
    'api_calls' as table_name,
    COUNT(*) as row_count,
    0 as content_mb
FROM api_calls
UNION ALL
SELECT
    'pipeline_runs' as table_name,
    COUNT(*) as row_count,
    0 as content_mb
FROM pipeline_runs
UNION ALL
SELECT
    'digests' as table_name,
    COUNT(*) as row_count,
    0 as content_mb
FROM digests;
EOF
echo ""

# Database file size
DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
echo -e "${GREEN}Database size: $DB_SIZE${NC}"
echo ""

# Integrity check
echo -e "${YELLOW}Running integrity check...${NC}"
INTEGRITY=$(sqlite3 "$DB_FILE" "PRAGMA integrity_check;")
if [ "$INTEGRITY" == "ok" ]; then
    echo -e "${GREEN}✓ Database integrity: OK${NC}"
else
    echo -e "${RED}✗ Database integrity: FAILED${NC}"
    echo "$INTEGRITY"
fi
echo ""

echo -e "${GREEN}Maintenance completed!${NC}"
