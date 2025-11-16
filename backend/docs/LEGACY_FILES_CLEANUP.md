# Legacy Files Cleanup Plan

## Legacy Files to Remove

These files have been moved to the new organized structure and are no longer needed:

### Core Files (moved to `core/`)

- ✅ `base.py` → `core/base.py`
- ✅ `config.py` → `core/config.py`
- ✅ `utils.py` → `core/utils.py`

### Auth Files (moved to `auth/`)

- ✅ `permissions.py` → `auth/permissions.py`

### Settings Files (moved to `settings/`)

- ✅ `settings_manager.py` → `settings/app_config.py`
- ✅ `settings_service.py` → `settings/service.py`
- ✅ `cutoff_settings.py` → `settings/cutoff.py`
- ✅ `settings.py` → `settings/legacy.py` (kept for backward compatibility)

### Business Services (moved to `services/`)

- ✅ `email_service.py` → `services/email.py`
- ✅ `visualization.py` → `services/visualization.py`

### Other

- `test_imports.py` - Test file, can be removed
- `backup/` - Backup folder, can be removed

## Verification

Before removing, verify:

1. No imports reference old paths (except via backward compatibility)
2. All new imports work correctly
3. Tests pass

## Removal Commands

```bash
cd /home/philg/projects/stratcon/backend/services

# Remove legacy files
rm base.py config.py utils.py permissions.py
rm settings_manager.py settings_service.py cutoff_settings.py
rm email_service.py visualization.py
rm test_imports.py

# Remove backup folder (if safe)
rm -rf backup/
```

## Backward Compatibility

The old `settings.py` file is kept as `settings/legacy.py` for backward compatibility with scripts that might still reference it. This can be removed after all scripts are updated.
