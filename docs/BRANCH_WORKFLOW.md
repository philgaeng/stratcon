# Branch Workflow

## Overview

This project uses a **two-branch strategy**:

- **`main`**: Development branch (WSL) - where you fix things and iterate
- **`prod`**: Production branch (AWS) - stable demo environment

## Workflow

### Daily Development (on `main`)

```bash
git checkout main
git pull origin main

# Make your changes
# ... edit files ...

git add .
git commit -m "Fix: ..."
git push origin main
```

### Syncing to Production (main → prod)

When ready to update production:

```bash
# Use the sync script (recommended)
./scripts/sync-to-prod.sh

# Or manually
git checkout prod
git merge main
git push origin prod
```

### Checking Branch Status

```bash
# See what's different
git log prod..main --oneline
git log main..prod --oneline
```

## Best Practices

### ✅ Do:
- Keep `main` as your working branch
- Sync `main` → `prod` when features are stable
- Use environment variables for config differences
- Test on `main` before syncing to `prod`
- Commit frequently on `main`

### ❌ Don't:
- Don't develop directly on `prod`
- Don't make production-specific code changes (use env vars)
- Don't let `prod` get too far behind `main`
- Don't force push to `prod` (unless absolutely necessary)

## Sync Frequency

**Recommended:** Sync `main` → `prod` when:
- A feature is complete and tested
- Bug fixes are ready for demo
- Before important client demos
- Weekly (to keep branches reasonably in sync)

## Troubleshooting

### Merge Conflicts

```bash
git checkout prod
git merge main
# Resolve conflicts manually
git add .
git commit
git push origin prod
```

### Accidentally Committed to `prod`

```bash
# Cherry-pick to main, then sync back
git checkout main
git cherry-pick <commit-hash>
git checkout prod
git merge main
```

