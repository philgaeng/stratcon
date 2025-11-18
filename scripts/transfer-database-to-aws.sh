#!/bin/bash
# Transfer database from WSL to AWS
# Usage: ./scripts/transfer-database-to-aws.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$PROJECT_ROOT/backend/data/settings.db"
AWS_HOST="52.221.59.184"
AWS_USER="ubuntu"
AWS_KEY="$HOME/.ssh/aws-key.pem"
AWS_DB_PATH="/var/lib/stratcon/data/settings.db"

echo "📤 Transferring database to AWS..."
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at: $DB_PATH"
    exit 1
fi

# Check if SSH key exists
if [ ! -f "$AWS_KEY" ]; then
    echo "❌ SSH key not found at: $AWS_KEY"
    exit 1
fi

# Get file size
FILE_SIZE=$(du -h "$DB_PATH" | cut -f1)
echo "📋 Database file: $DB_PATH"
echo "   Size: $FILE_SIZE"
echo ""

# Transfer to AWS
echo "🚀 Transferring to AWS..."
scp -i "$AWS_KEY" "$DB_PATH" "$AWS_USER@$AWS_HOST:/tmp/settings.db"

echo ""
echo "✅ Database transferred to AWS!"
echo ""
echo "📋 Next steps on AWS:"
echo "  1. SSH into AWS: ssh -i $AWS_KEY $AWS_USER@$AWS_HOST"
echo "  2. Stop the service: sudo systemctl stop stratcon-api"
echo "  3. Backup existing DB (if any): sudo cp $AWS_DB_PATH $AWS_DB_PATH.backup"
echo "  4. Copy new DB: sudo cp /tmp/settings.db $AWS_DB_PATH"
echo "  5. Set permissions: sudo chown ubuntu:ubuntu $AWS_DB_PATH"
echo "  6. Start the service: sudo systemctl start stratcon-api"
echo ""
echo "Or run the import script on AWS:"
echo "  ssh -i $AWS_KEY $AWS_USER@$AWS_HOST 'bash -s' < scripts/import-database-on-aws.sh"


