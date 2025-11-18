#!/bin/bash
# Import database on AWS EC2
# This script should be run on AWS after transferring the database file

set -e

DB_SOURCE="/tmp/settings.db"
DB_DEST="/var/lib/stratcon/data/settings.db"

echo "📥 Importing database on AWS..."
echo ""

# Check if source file exists
if [ ! -f "$DB_SOURCE" ]; then
    echo "❌ Database file not found at: $DB_SOURCE"
    echo "   Please transfer the database first using transfer-database-to-aws.sh"
    exit 1
fi

# Stop the service
echo "🛑 Stopping stratcon-api service..."
sudo systemctl stop stratcon-api || true

# Backup existing database if it exists
if [ -f "$DB_DEST" ]; then
    BACKUP_FILE="${DB_DEST}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "💾 Backing up existing database to: $BACKUP_FILE"
    sudo cp "$DB_DEST" "$BACKUP_FILE"
    echo "✅ Backup created"
fi

# Ensure destination directory exists
sudo mkdir -p "$(dirname "$DB_DEST")"

# Copy database
echo "📋 Copying database to: $DB_DEST"
sudo cp "$DB_SOURCE" "$DB_DEST"

# Set permissions
echo "🔐 Setting permissions..."
sudo chown ubuntu:ubuntu "$DB_DEST"
sudo chmod 644 "$DB_DEST"

# Verify database
echo "✅ Verifying database..."
if sqlite3 "$DB_DEST" "SELECT COUNT(*) FROM sqlite_master;" > /dev/null 2>&1; then
    TABLE_COUNT=$(sqlite3 "$DB_DEST" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    echo "   ✅ Database is valid"
    echo "   📊 Tables found: $TABLE_COUNT"
else
    echo "   ❌ Database verification failed!"
    exit 1
fi

# Start the service
echo ""
echo "🚀 Starting stratcon-api service..."
sudo systemctl start stratcon-api
sleep 2

# Check service status
if sudo systemctl is-active --quiet stratcon-api; then
    echo "✅ Service started successfully"
else
    echo "⚠️  Service may have issues. Check status:"
    echo "   sudo systemctl status stratcon-api"
fi

echo ""
echo "✅ Database import complete!"
echo ""
echo "📋 Database location: $DB_DEST"
echo "📋 Backup location: ${DB_DEST}.backup.*"


