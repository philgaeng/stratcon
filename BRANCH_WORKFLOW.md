# Branch Workflow Guide

## Overview

This project uses a **two-branch strategy** for managing development and production:

- **`main`**: Development branch (WSL) - where you fix things and iterate
- **`prod`**: Production/demo branch (AWS) - stable demo environment

## Branch Strategy

```
main (WSL Development)
  │
  │ [Regular sync]
  │
  └─→ prod (AWS Demo/Production)
```

### When to Use Each Branch

**`main` branch:**
- ✅ All development work
- ✅ Bug fixes
- ✅ Feature development
- ✅ Testing new ideas
- ✅ Local development on WSL

**`prod` branch:**
- ✅ Stable demo environment on AWS
- ✅ Production deployments
- ✅ Client demonstrations
- ✅ Only synced from `main` when ready

## Workflow

### Daily Development (on `main`)

```bash
# Work on main branch
git checkout main
git pull origin main

# Make your changes
# ... edit files ...

# Commit and push
git add .
git commit -m "Fix: ..."
git push origin main
```

### Syncing to Production (main → prod)

When you're ready to update the demo/production environment:

```bash
# Option 1: Use the sync script (recommended)
./scripts/sync-to-prod.sh

# Option 2: Manual sync
git checkout prod
git merge main
git push origin prod
```

### Checking Branch Status

See what's different between branches:

```bash
./scripts/check-branch-status.sh
```

This shows:
- How many commits main is ahead/behind prod
- Recent commits on each branch
- Whether sync is needed

## Environment Configuration

Both branches use the same codebase but different environment variables:

### Development (WSL - `main` branch)
- Uses `env.local` file (gitignored)
- Local database paths
- Development API URLs
- Debug mode enabled

### Production (AWS - `prod` branch)
- Uses AWS environment variables (Parameter Store, Secrets Manager, or EC2 env)
- Production database paths
- Production API URLs
- Debug mode disabled

See `env.local.example` and `DEPLOYMENT_GUIDE.md` for details.

## Best Practices

### ✅ Do:
- Keep `main` as your working branch
- Sync `main` → `prod` when features are stable
- Use environment variables for all config differences
- Test on `main` before syncing to `prod`
- Commit frequently on `main`

### ❌ Don't:
- Don't develop directly on `prod`
- Don't make production-specific code changes (use env vars instead)
- Don't let `prod` get too far behind `main`
- Don't force push to `prod` (unless absolutely necessary)

## Sync Frequency

**Recommended:** Sync `main` → `prod` when:
- A feature is complete and tested
- Bug fixes are ready for demo
- Before important client demos
- Weekly (to keep branches reasonably in sync)

**Avoid:** Syncing every single commit (let `main` be your playground)

## Troubleshooting

### Merge Conflicts

If you get conflicts when syncing:

```bash
git checkout prod
git merge main
# Resolve conflicts manually
git add .
git commit
git push origin prod
```

### Accidentally Committed to `prod`

If you made changes directly on `prod`:

```bash
# Option 1: Cherry-pick to main, then sync back
git checkout main
git cherry-pick <commit-hash>
git checkout prod
git merge main

# Option 2: Reset prod to match main (loses prod-only changes)
git checkout prod
git reset --hard origin/main
git push origin prod --force  # ⚠️ Use with caution
```

### Check What's Different

```bash
# See commits in main but not in prod
git log prod..main --oneline

# See commits in prod but not in main
git log main..prod --oneline

# See file differences
git diff prod..main
```

## Quick Reference

```bash
# Switch to main (development)
git checkout main

# Switch to prod (production)
git checkout prod

# Sync main → prod
./scripts/sync-to-prod.sh

# Check branch status
./scripts/check-branch-status.sh

# See what's different
git log prod..main --oneline
```

## AWS Deployment

AWS should be configured to:
- Pull from `prod` branch (not `main`)
- Use production environment variables
- Deploy automatically on `prod` branch updates (optional)

See `DEPLOYMENT_GUIDE.md` for AWS setup details.

