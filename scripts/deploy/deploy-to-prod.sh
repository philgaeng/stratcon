#!/bin/bash
# Deploy latest prod branch to AWS server
# Usage: ./scripts/deploy-to-prod.sh

set -e

AWS_SERVER_IP="52.221.59.184"
SSH_KEY="${HOME}/.ssh/aws-key.pem"
PROJECT_DIR="~/stratcon"

echo "🚀 Deploying to AWS production server..."
echo "=========================================="
echo ""

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: SSH key not found at $SSH_KEY"
    exit 1
fi

echo "📥 Pulling latest changes from prod branch on AWS server..."
ssh -i "$SSH_KEY" ubuntu@$AWS_SERVER_IP << EOFSSH
set -e
cd $PROJECT_DIR

echo "Current branch: \$(git branch --show-current)"
echo "Fetching latest changes..."
git fetch origin prod

echo "Checking out prod branch..."
git checkout prod

echo "Pulling latest changes..."
git pull origin prod

echo "Restarting stratcon-api service..."
sudo systemctl restart stratcon-api.service

echo "Checking service status..."
sudo systemctl status stratcon-api.service --no-pager -l | head -20

echo ""
echo "✅ Deployment complete!"
EOFSSH

echo ""
echo "✅ Successfully deployed to production!"
