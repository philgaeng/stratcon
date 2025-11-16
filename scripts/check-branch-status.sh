#!/bin/bash
# Check status of main and prod branches
# Shows commits ahead/behind between branches

set -e

echo "📊 Branch Status Report"
echo "======================"
echo ""

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Current branch: $CURRENT_BRANCH"
echo ""

# Fetch latest from remote
echo "🔄 Fetching latest from remote..."
git fetch origin main prod 2>/dev/null || true
echo ""

# Check main branch
echo "🌿 Main branch:"
MAIN_AHEAD=$(git rev-list --left-right --count origin/main...origin/prod 2>/dev/null | awk '{print $1}' || echo "0")
MAIN_BEHIND=$(git rev-list --left-right --count origin/main...origin/prod 2>/dev/null | awk '{print $2}' || echo "0")

if [ "$MAIN_AHEAD" != "0" ] || [ "$MAIN_BEHIND" != "0" ]; then
    echo "   Main is $MAIN_AHEAD commits ahead of prod"
    echo "   Main is $MAIN_BEHIND commits behind prod"
else
    echo "   ✅ Main and prod are in sync"
fi

# Show recent commits on main
echo ""
echo "📝 Recent commits on main (not in prod):"
git log origin/prod..origin/main --oneline -5 2>/dev/null || echo "   (none)"
echo ""

# Show recent commits on prod
echo "📝 Recent commits on prod (not in main):"
git log origin/main..origin/prod --oneline -5 2>/dev/null || echo "   (none)"
echo ""

# Recommendations
if [ "$MAIN_AHEAD" != "0" ] && [ "$MAIN_AHEAD" != "0" ]; then
    echo "💡 Recommendation:"
    echo "   Run ./scripts/sync-to-prod.sh to sync main → prod"
fi

