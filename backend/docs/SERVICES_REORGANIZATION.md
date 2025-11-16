# Services Folder Reorganization Plan

## Current Problems

- Too many files at root level (config.py, utils.py, permissions.py, settings\*.py, etc.)
- Unclear separation between core utilities, business logic, and domain services
- Hard to find related functionality
- Mixing concerns (auth, config, utilities, services)

## Proposed Structure

```
backend/services/
├── __init__.py                    # Main exports (keep lazy loading)
├── core/                          # Core utilities and base classes
│   ├── __init__.py
│   ├── base.py                    # ServiceContext, base classes
│   ├── config.py                  # Constants, ReportStyle, PlotlyStyle
│   └── utils.py                   # ReportLogger, helper functions
│
├── auth/                          # Authentication & authorization
│   ├── __init__.py
│   └── permissions.py             # UserRole, decorators, permission checks
│
├── settings/                      # All settings management
│   ├── __init__.py
│   ├── service.py                 # SettingsService (unified interface)
│   ├── app_config.py              # AppConfigManager (JSON config)
│   ├── cutoff.py                  # CutoffSettingsManager (database)
│   └── legacy.py                  # Old settings.py functions (deprecated)
│
├── services/                      # Business services
│   ├── __init__.py
│   ├── email.py                   # Email service
│   └── visualization.py           # Chart/visualization service
│
├── domain/                        # Domain-specific business logic
│   ├── __init__.py
│   ├── data_preparation/          # Data preparation orchestrator
│   ├── electricity_analysis/      # Electricity analysis orchestrator
│   └── reporting/                 # Reporting orchestrator
│
└── data/                          # Data management
    ├── __init__.py
    ├── db_manager/                # Database queries and schema
    └── extract/                    # Data extraction and compilation
        └── (rename data_extract_and_compilation/)
```

## Migration Strategy

### Phase 1: Create New Structure (Non-Breaking)

1. Create new directories
2. Move files with updated imports
3. Update `__init__.py` files to maintain backward compatibility
4. Keep old files temporarily with deprecation warnings

### Phase 2: Update Imports (Gradual)

1. Update internal imports first
2. Update API imports
3. Update documentation

### Phase 3: Cleanup (After All Imports Updated)

1. Remove old files
2. Remove deprecation warnings
3. Update documentation

## Detailed File Mapping

### Core Utilities

```
services/core/
├── base.py          # ServiceContext (from services/base.py)
├── config.py        # Constants, ReportStyle (from services/config.py)
└── utils.py         # ReportLogger, helpers (from services/utils.py)
```

**New imports:**

```python
from backend.services.core import ReportLogger, ReportStyle
from backend.services.core.base import ServiceContext
```

**Backward compatibility:**

```python
# services/__init__.py maintains old imports
from backend.services.core.utils import ReportLogger
from backend.services.core.config import ReportStyle
```

### Authentication

```
services/auth/
└── permissions.py   # UserRole, decorators (from services/permissions.py)
```

**New imports:**

```python
from backend.services.auth import UserRole, require_roles
```

### Settings

```
services/settings/
├── service.py       # SettingsService (from services/settings_service.py)
├── app_config.py    # AppConfigManager (from services/settings_manager.py)
├── cutoff.py        # CutoffSettingsManager (from services/cutoff_settings.py)
└── legacy.py        # Old functions (from services/settings.py)
```

**New imports:**

```python
from backend.services.settings import SettingsService
from backend.services.settings.app_config import AppConfigManager
from backend.services.settings.cutoff import CutoffSettingsManager
```

### Business Services

```
services/services/
├── email.py         # Email service (from services/email_service.py)
└── visualization.py # Visualization (from services/visualization.py)
```

**New imports:**

```python
from backend.services.services.email import send_report_email
from backend.services.services.visualization import generate_charts
```

### Domain Logic

```
services/domain/
├── data_preparation/    # (keep as is)
├── electricity_analysis/ # (keep as is)
└── reporting/           # (keep as is)
```

### Data Management

```
services/data/
├── db_manager/         # (keep as is)
└── extract/            # (rename from data_extract_and_compilation/)
```

## Benefits

### ✅ Clear Organization

- Related files grouped together
- Easy to find functionality
- Clear separation of concerns

### ✅ Scalability

- Easy to add new services
- Clear where new code belongs
- Domain logic separated from infrastructure

### ✅ Maintainability

- Smaller, focused modules
- Easier to test
- Clearer dependencies

### ✅ Backward Compatibility

- Old imports still work (via **init**.py)
- Gradual migration possible
- No breaking changes

## Example: Before vs After

### Before

```python
from backend.services.utils import ReportLogger
from backend.services.config import ReportStyle
from backend.services.permissions import UserRole
from backend.services.settings_service import SettingsService
from backend.services.email_service import send_report_email
```

### After

```python
from backend.services.core import ReportLogger, ReportStyle
from backend.services.auth import UserRole
from backend.services.settings import SettingsService
from backend.services.services.email import send_report_email
```

Or with backward compatibility:

```python
# Old imports still work
from backend.services import ReportLogger, ReportStyle
from backend.services.permissions import UserRole
from backend.services.settings_service import SettingsService
```

## Implementation Checklist

- [ ] Create new directory structure
- [ ] Move files to new locations
- [ ] Update internal imports in moved files
- [ ] Create **init**.py files with exports
- [ ] Update services/**init**.py for backward compatibility
- [ ] Add deprecation warnings to old locations
- [ ] Update API imports
- [ ] Update documentation
- [ ] Test all imports work
- [ ] Remove old files after migration period
