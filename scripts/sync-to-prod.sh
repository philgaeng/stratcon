#!/bin/bash
# Sync main branch to prod branch
# Usage: ./scripts/sync-to-prod.sh [--force]

set -e

FORCE=false
if [ "$1" == "--force" ]; then
    FORCE=true
fi

echo "🔄 Syncing main → prod branch..."

# Ensure we're on main and up to date
# Always switch to main first (in case we're on prod or another branch)
git checkout main
git pull origin main

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Switch to prod branch
git checkout prod

# Merge main into prod
if [ "$FORCE" == "true" ]; then
    echo "⚠️  Force merging (will overwrite prod changes)..."
    git merge main --no-edit
else
    echo "📥 Merging main into prod..."
    git merge main --no-edit
fi

# Check for conflicts
if [ $? -ne 0 ]; then
    echo "❌ Merge conflicts detected. Please resolve them manually:"
    echo "   1. Resolve conflicts in the files listed above"
    echo "   2. Run: git add ."
    echo "   3. Run: git commit"
    echo "   4. Run: git push origin prod"
    exit 1
fi

# Push to remote
echo "📤 Pushing prod branch to remote..."
git push origin prod

# Switch back to main branch (so we end where we started)
echo "🔄 Switching back to main branch..."
git checkout main

echo "✅ Successfully synced main → prod!"
echo ""
echo "📋 Summary:"
echo "   - Merged latest changes from main"
echo "   - Pushed to origin/prod"
echo "   - Switched back to main branch"
echo ""
echo "🚀 Next steps:"
echo "   - AWS deployment should pull from prod branch"
echo "   - Verify environment variables are set correctly in AWS"

