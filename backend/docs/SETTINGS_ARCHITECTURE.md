# Settings Architecture

## Overview

The settings system has been refactored into a clean, unified architecture using composition. This provides a single entry point while keeping concerns properly separated.

## Architecture

```
SettingsService (Unified Interface)
├── AppConfigManager (JSON-based application config)
│   └── Roles, permissions, feature flags, route permissions
└── CutoffSettingsManager (Database-based business settings)
    └── Cutoff times for EPCs, Clients, Units
```

## Components

### 1. `SettingsService` (Unified Interface)

**Location**: `backend/services/settings_service.py`

The main entry point for all settings operations. Provides:

- Clean, unified API
- Delegates to specialized managers
- Convenience methods combining both sources

**Usage**:

```python
from backend.services.settings_service import SettingsService

service = SettingsService()

# Application config (JSON)
roles = service.app_config.get_roles_config()
feature_enabled = service.is_feature_enabled("meter_logging")

# Business settings (Database)
cutoff = service.get_cutoff_datetime("NEO", "NEO3_0708")
service.set_client_cutoff("NEO", cutoff_day=26)
```

### 2. `AppConfigManager` (Application Configuration)

**Location**: `backend/services/settings_manager.py`

Manages JSON-based static configuration:

- Role definitions and permissions
- Route permissions
- Feature flags
- Default application settings

**Storage**: `backend/config/app_settings.json`

**Usage**:

```python
from backend.services.settings_manager import SettingsManager

config = SettingsManager()
roles = config.get_roles_config()
config.update_feature_flag("meter_logging", True)
```

### 3. `CutoffSettingsManager` (Business Domain Settings)

**Location**: `backend/services/cutoff_settings.py`

Manages database-based runtime settings:

- Cutoff times for EPCs, Clients, Units
- Hierarchy resolution (Unit → Client → EPC → Default)
- Client/tenant configuration

**Storage**: SQLite database (`backend/data/settings.db`)

**Usage**:

```python
from backend.services.cutoff_settings import CutoffSettingsManager

cutoff_mgr = CutoffSettingsManager()
cutoff = cutoff_mgr.get_cutoff_datetime("NEO", "NEO3_0708")
cutoff_mgr.set_client_cutoff("NEO", cutoff_day=26)
```

## Migration Guide

### Before (Separate Files)

```python
# Application config
from backend.services.settings_manager import SettingsManager
config = SettingsManager()
roles = config.get_roles_config()

# Business settings
from backend.services.settings import get_cutoff_datetime
cutoff = get_cutoff_datetime("NEO", "NEO3_0708")
```

### After (Unified Service)

```python
# Unified interface
from backend.services.settings_service import SettingsService
service = SettingsService()

# Application config
roles = service.app_config.get_roles_config()

# Business settings
cutoff = service.get_cutoff_datetime("NEO", "NEO3_0708")
```

## Benefits

### ✅ Separation of Concerns

- **AppConfigManager**: Handles static JSON configuration
- **CutoffSettingsManager**: Handles dynamic database settings
- **SettingsService**: Provides unified interface

### ✅ Clean API

- Single entry point (`SettingsService`)
- Clear delegation to specialized managers
- Consistent method naming

### ✅ Maintainability

- Each manager is focused on one responsibility
- Easy to test in isolation
- Easy to extend with new managers

### ✅ Backward Compatibility

- Old functions in `settings.py` still work (for now)
- Can migrate gradually to new API
- No breaking changes to existing code

## File Structure

```
backend/services/
├── settings_service.py      # Unified interface (NEW)
├── settings_manager.py       # App config (JSON) - renamed from SettingsManager
├── cutoff_settings.py       # Business settings (Database) - NEW class-based
└── settings.py              # Legacy functions (deprecated, kept for compatibility)
```

## Design Decisions

### Why Composition?

Instead of merging everything into one class, we use composition:

- **Single Responsibility**: Each manager has one clear purpose
- **Testability**: Easy to mock individual managers
- **Flexibility**: Can swap implementations without changing interface
- **Clarity**: Clear separation between JSON config and database settings

### Why Keep Legacy Functions?

The old `settings.py` functions are kept for:

- **Backward Compatibility**: Existing code continues to work
- **Gradual Migration**: Can migrate endpoints one at a time
- **No Breaking Changes**: Safe to deploy

## Future Improvements

1. **Deprecate Legacy Functions**: Add deprecation warnings to `settings.py` functions
2. **Add More Managers**: Could add `UserSettingsManager`, `SystemSettingsManager`, etc.
3. **Caching Layer**: Add caching for frequently accessed settings
4. **Validation**: Add schema validation for JSON config
5. **API Endpoints**: Create unified settings API using `SettingsService`

## Examples

### Example 1: Get Role Configuration

```python
from backend.services.settings_service import SettingsService

service = SettingsService()
role_config = service.get_role_config("client_admin")
# Returns: {"name": "Client Admin", "permissions": [...], ...}
```

### Example 2: Set Cutoff Time

```python
from backend.services.settings_service import SettingsService

service = SettingsService()
service.set_client_cutoff("NEO", cutoff_day=26, cutoff_hour=23, cutoff_minute=59)
```

### Example 3: Check Feature Flag

```python
from backend.services.settings_service import SettingsService

service = SettingsService()
if service.is_feature_enabled("meter_logging"):
    # Enable meter logging UI
    pass
```

### Example 4: Get Default Cutoff from Config

```python
from backend.services.settings_service import SettingsService

service = SettingsService()
defaults = service.get_default_cutoff_settings()
# Returns: {"day": 26, "hour": 23, "minute": 59, "second": 59}
```

## Testing

Each component can be tested independently:

```python
# Test AppConfigManager
from backend.services.settings_manager import SettingsManager
config = SettingsManager()
assert config.get_feature_flags()["meter_logging"] == True

# Test CutoffSettingsManager
from backend.services.cutoff_settings import CutoffSettingsManager
cutoff_mgr = CutoffSettingsManager()
cutoff = cutoff_mgr.get_cutoff_datetime("NEO", "NEO3_0708")

# Test SettingsService
from backend.services.settings_service import SettingsService
service = SettingsService()
assert service.is_feature_enabled("meter_logging") == True
```
