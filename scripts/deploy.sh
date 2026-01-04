#!/usr/bin/env bash
# scripts/deploy.sh
# Deployment script for NewsAnalysis system

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="newsanalysis"
INSTALL_DIR="${INSTALL_DIR:-/opt/newsanalysis}"
USER="${USER:-newsanalysis}"
PYTHON_VERSION="3.11"

echo -e "${GREEN}NewsAnalysis Deployment Script${NC}"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Step 1: Create user if doesn't exist
echo -e "${YELLOW}Step 1: Creating system user${NC}"
if id "$USER" &>/dev/null; then
    echo "User $USER already exists"
else
    useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$USER"
    echo "Created user: $USER"
fi

# Step 2: Install system dependencies
echo -e "${YELLOW}Step 2: Installing system dependencies${NC}"
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    apt-get update
    apt-get install -y python${PYTHON_VERSION} python3-pip python3-venv sqlite3 cron
elif command -v yum &> /dev/null; then
    # RHEL/CentOS
    yum install -y python${PYTHON_VERSION} python3-pip python3-virtualenv sqlite crontabs
else
    echo -e "${RED}Error: Unsupported package manager${NC}"
    exit 1
fi

# Step 3: Create directory structure
echo -e "${YELLOW}Step 3: Creating directory structure${NC}"
mkdir -p "$INSTALL_DIR"/{config,out,logs,backups}
chown -R "$USER:$USER" "$INSTALL_DIR"

# Step 4: Copy application files
echo -e "${YELLOW}Step 4: Copying application files${NC}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Copy source code
cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
cp -r "$PROJECT_ROOT/config" "$INSTALL_DIR/"
cp "$PROJECT_ROOT/pyproject.toml" "$INSTALL_DIR/"
cp "$PROJECT_ROOT/.env.example" "$INSTALL_DIR/.env"

chown -R "$USER:$USER" "$INSTALL_DIR"

# Step 5: Create virtual environment
echo -e "${YELLOW}Step 5: Creating Python virtual environment${NC}"
cd "$INSTALL_DIR"
sudo -u "$USER" python3 -m venv venv
sudo -u "$USER" venv/bin/pip install --upgrade pip
sudo -u "$USER" venv/bin/pip install -e .

# Install Playwright browsers
sudo -u "$USER" venv/bin/playwright install chromium

# Step 6: Initialize database
echo -e "${YELLOW}Step 6: Initializing database${NC}"
if [ ! -f "$INSTALL_DIR/news.db" ]; then
    sudo -u "$USER" venv/bin/python "$INSTALL_DIR/src/newsanalysis/database/init_db.py"
    echo "Database initialized"
else
    echo "Database already exists, skipping initialization"
fi

# Step 7: Install systemd service
echo -e "${YELLOW}Step 7: Installing systemd service${NC}"
cat > /etc/systemd/system/newsanalysis.service <<EOF
[Unit]
Description=NewsAnalysis Daily Pipeline
After=network.target

[Service]
Type=oneshot
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/newsanalysis run
StandardOutput=append:$INSTALL_DIR/logs/pipeline.log
StandardError=append:$INSTALL_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

# Install systemd timer
cat > /etc/systemd/system/newsanalysis.timer <<EOF
[Unit]
Description=Run NewsAnalysis daily at 6 AM
Requires=newsanalysis.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable newsanalysis.timer
echo "Systemd service and timer installed"

# Step 8: Setup log rotation
echo -e "${YELLOW}Step 8: Configuring log rotation${NC}"
cat > /etc/logrotate.d/newsanalysis <<EOF
$INSTALL_DIR/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 $USER $USER
    sharedscripts
}
EOF
echo "Log rotation configured"

# Step 9: Setup backup cron job
echo -e "${YELLOW}Step 9: Setting up automated backups${NC}"
cat > /etc/cron.daily/newsanalysis-backup <<EOF
#!/bin/bash
# Daily backup of NewsAnalysis database

BACKUP_DIR="$INSTALL_DIR/backups"
DB_FILE="$INSTALL_DIR/news.db"
DATE=\$(date +%Y%m%d)
BACKUP_FILE="\$BACKUP_DIR/news_backup_\$DATE.db"

# Create backup
sqlite3 "\$DB_FILE" ".backup '\$BACKUP_FILE'"
gzip "\$BACKUP_FILE"

# Keep only last 30 days of backups
find "\$BACKUP_DIR" -name "news_backup_*.db.gz" -mtime +30 -delete

echo "\$(date): Database backup completed" >> $INSTALL_DIR/logs/backup.log
EOF

chmod +x /etc/cron.daily/newsanalysis-backup
chown root:root /etc/cron.daily/newsanalysis-backup

# Step 10: Configure environment
echo -e "${YELLOW}Step 10: Environment configuration${NC}"
echo ""
echo "Please edit $INSTALL_DIR/.env with your configuration:"
echo "  - Set OPENAI_API_KEY"
echo "  - Configure other settings as needed"
echo ""

# Step 11: Display next steps
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit configuration: sudo nano $INSTALL_DIR/.env"
echo "  2. Start the timer: sudo systemctl start newsanalysis.timer"
echo "  3. Check timer status: sudo systemctl status newsanalysis.timer"
echo "  4. Run manually: sudo -u $USER $INSTALL_DIR/venv/bin/newsanalysis run"
echo "  5. View logs: tail -f $INSTALL_DIR/logs/pipeline.log"
echo ""
echo "Backup location: $INSTALL_DIR/backups"
echo "Output location: $INSTALL_DIR/out"
echo ""
