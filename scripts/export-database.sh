#!/bin/bash
# Export database from WSL and prepare for transfer to AWS
# Usage: ./scripts/export-database.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$PROJECT_ROOT/backend/data/settings.db"
EXPORT_DIR="$PROJECT_ROOT/backend/data/export"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPORT_FILE="$EXPORT_DIR/settings_${TIMESTAMP}.db"

echo "📦 Exporting database from WSL..."
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at: $DB_PATH"
    exit 1
fi

# Create export directory
mkdir -p "$EXPORT_DIR"

# Copy database file
echo "📋 Copying database file..."
cp "$DB_PATH" "$EXPORT_FILE"

# Get file size
FILE_SIZE=$(du -h "$EXPORT_FILE" | cut -f1)
echo "✅ Database exported to: $EXPORT_FILE"
echo "   Size: $FILE_SIZE"
echo ""

# Also create SQL dump as backup
SQL_DUMP="$EXPORT_DIR/settings_${TIMESTAMP}.sql"
echo "📋 Creating SQL dump..."
sqlite3 "$DB_PATH" .dump > "$SQL_DUMP"
echo "✅ SQL dump created: $SQL_DUMP"
echo ""

echo "📤 Ready to transfer to AWS!"
echo ""
echo "To transfer, run:"
echo "  scp -i ~/.ssh/aws-key.pem $EXPORT_FILE ubuntu@52.221.59.184:/tmp/settings.db"
echo ""
echo "Or use the transfer script:"
echo "  ./scripts/transfer-database-to-aws.sh"


