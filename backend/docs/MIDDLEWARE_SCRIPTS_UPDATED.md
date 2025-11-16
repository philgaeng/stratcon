# Middleware & Scripts Imports Updated ✅

## Summary

All middleware and scripts have been updated to use the new reorganized services structure.

## Changes Made

### Middleware

#### `auth_middleware.py`

**Before:**

```python
from backend.services.db_manager.db_schema import get_db_connection
from backend.services.permissions import UserRole, check_permission
```

**After:**

```python
from backend.services.data.db_manager.db_schema import get_db_connection
from backend.services.auth.permissions import UserRole, check_permission
```

### Scripts

#### `populate_database.py`

**Before:**

```python
from services.db_manager.db_schema import get_db_connection, init_database, ...
```

**After:**

```python
from services.data.db_manager.db_schema import get_db_connection, init_database, ...
```

#### `migrate_csv_to_db.py`

**Before:**

```python
from services.settings import (
    init_database,
    set_client_settings,
    set_tenant_settings,
    DEFAULT_CLIENT,
)
from services.config import DEFAULT_LOADS_SUMMARY
```

**After:**

```python
from services.settings.cutoff import CutoffSettingsManager
from services.core.config import DEFAULT_CLIENT
from services.data.db_manager.db_schema import init_database

# Uses CutoffSettingsManager with backward-compatible wrapper functions
```

#### `load_meter_matches_csv.py`

**Before:**

```python
from services.db_manager.db_schema import get_db_connection, init_database
from services.utils import ReportLogger
```

**After:**

```python
from services.data.db_manager.db_schema import get_db_connection, init_database
from services.core.utils import ReportLogger
```

#### `generate_reports.py`

**Before:**

```python
from services.reporting.folder_helpers import list_tenant_folders
from services.reporting import (
    generate_reports_for_tenant,
    generate_reports_for_client,
)
```

**After:**

```python
from services.domain.reporting.folder_helpers import list_tenant_folders
from services.domain.reporting import (
    generate_reports_for_tenant,
    generate_reports_for_client,
)
```

#### `verify_emails_in_ses.py`

**Before:**

```python
from services.db_schema import get_db_connection
```

**After:**

```python
from services.data.db_manager.db_schema import get_db_connection
```

#### `populate_entities.py`

**Before:**

```python
from services.db_manager.db_schema import populate_entities
```

**After:**

```python
from services.data.db_manager.db_schema import populate_entities
```

#### `populate_user_entity_ids.py`

**Before:**

```python
from services.db_manager.db_schema import populate_user_entity_ids
```

**After:**

```python
from services.data.db_manager.db_schema import populate_user_entity_ids
```

## Import Mapping Summary

| Old Import                      | New Import                                             |
| ------------------------------- | ------------------------------------------------------ |
| `services.db_manager.db_schema` | `services.data.db_manager.db_schema`                   |
| `services.db_schema`            | `services.data.db_manager.db_schema`                   |
| `services.permissions`          | `services.auth.permissions`                            |
| `services.settings`             | `services.settings.cutoff` (via CutoffSettingsManager) |
| `services.config`               | `services.core.config`                                 |
| `services.utils`                | `services.core.utils`                                  |
| `services.reporting`            | `services.domain.reporting`                            |

## Status

✅ All middleware files updated  
✅ All script files updated  
✅ No linter errors  
✅ Backward compatibility maintained where needed

## Notes

- `migrate_csv_to_db.py` now uses `CutoffSettingsManager` with wrapper functions for backward compatibility
- All scripts maintain their functionality while using the new organized structure
- Middleware continues to work with updated import paths
