# Settings Management Guide

## Overview

This application uses a **hybrid approach** for managing settings, similar to modern applications like Cursor:

- **JSON files** for static configuration (role definitions, permissions, defaults)
- **SQLite database** for runtime data (users, assignments, dynamic settings)

This approach provides:

- ✅ Version control for configuration changes
- ✅ Easy editing of role/permission definitions
- ✅ Efficient querying of user data
- ✅ Support for relationships and foreign keys
- ✅ Audit trails for user changes

## Architecture

### JSON Configuration (`backend/config/app_settings.json`)

Contains **static** configuration that rarely changes:

```json
{
  "version": "1.0.0",
  "roles": {
    "super_admin": {
      "name": "Super Admin",
      "description": "Full system access",
      "hierarchy": 7,
      "permissions": ["*"]
    },
    ...
  },
  "route_permissions": {
    "/clients": ["super_admin", "client_admin", ...],
    ...
  },
  "default_settings": {
    "cutoff": { "day": 26, "hour": 23, ... },
    "pagination": { "default_limit": 100, ... },
    "features": { "meter_logging": true, ... }
  }
}
```

**What goes in JSON:**

- Role definitions and hierarchies
- Permission strings (e.g., `"clients.view"`, `"users.create"`)
- Route-to-role mappings
- Default application settings
- Feature flags

**What does NOT go in JSON:**

- User records (use database)
- User-client assignments (use database)
- Runtime settings (cutoff times per client/tenant - use database)

### Database (`backend/data/settings.db`)

Contains **runtime** data that changes frequently:

**Tables:**

- `users` - User accounts with `user_group` (references JSON role)
- `user_client_assignments` - Which users can access which clients
- `clients` - Client settings (cutoff times, etc.)
- `entities` - Generic entity catalog
- `entity_user_assignments` - Entity-to-user mappings

**What goes in Database:**

- User records (email, name, user_group, etc.)
- User-client assignments
- Client/tenant-specific settings (cutoff times)
- Historical data (assignment history, etc.)

## Usage

### Managing Users

Use the User Management API (`/settings/users/*`):

```python
# List users
GET /settings/users?active_only=true&user_group=client_admin

# Create user
POST /settings/users
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "user_group": "client_admin",
  ...
}

# Update user
PUT /settings/users/{user_id}
{
  "user_group": "client_manager",
  "active": false
}

# Get roles
GET /settings/users/roles
GET /settings/users/roles/client_admin
```

### Managing Roles & Permissions

**Option 1: Edit JSON directly** (recommended for development)

Edit `backend/config/app_settings.json`:

```json
{
  "roles": {
    "client_admin": {
      "permissions": [
        "clients.view",
        "clients.manage",
        "users.create", // Add new permission
        "users.manage"
      ]
    }
  }
}
```

**Option 2: Use SettingsManager API** (for programmatic updates)

```python
from backend.services.settings_manager import SettingsManager

manager = SettingsManager()
manager.update_role_permissions(
    role_name="client_admin",
    permissions=["clients.view", "clients.manage", "users.create", "users.manage"]
)
```

### Managing Route Permissions

Edit `app_settings.json`:

```json
{
  "route_permissions": {
    "/new-endpoint": ["super_admin", "client_admin"]
  }
}
```

Or use the API:

```python
manager.update_route_permission(
    route="/new-endpoint",
    allowed_roles=["super_admin", "client_admin"]
)
```

### Managing Feature Flags

```python
manager.update_feature_flag("meter_logging", enabled=False)
```

Or edit JSON:

```json
{
  "default_settings": {
    "features": {
      "meter_logging": false
    }
  }
}
```

## SettingsManager Service

The `SettingsManager` class provides a programmatic interface to JSON settings:

```python
from backend.services.settings_manager import SettingsManager

manager = SettingsManager()

# Get role config
roles = manager.get_roles_config()
client_admin = manager.get_role_config("client_admin")

# Get route permissions
routes = manager.get_route_permissions()

# Get defaults
defaults = manager.get_default_settings()
features = manager.get_feature_flags()

# Update settings
manager.update_role_permissions("client_admin", ["clients.view", ...])
manager.update_route_permission("/clients", ["super_admin", ...])
manager.update_feature_flag("meter_logging", True)
```

## Permission System Integration

The permission system (`backend/services/permissions.py`) reads from both:

1. **JSON config** - Role definitions and route permissions
2. **Database** - User records and their `user_group` values

When a user makes a request:

1. Auth middleware extracts user from JWT token
2. User's `user_group` is read from database
3. Permission decorators check against JSON role definitions
4. Route access is validated against `route_permissions` in JSON

## Best Practices

### ✅ DO

- Edit JSON for role/permission changes (version controlled)
- Use database for user data (supports relationships)
- Use API endpoints for user CRUD operations
- Keep JSON config simple and declarative
- Document permission strings clearly

### ❌ DON'T

- Store user records in JSON
- Store runtime settings in JSON
- Hardcode role checks (use `UserRole` enum)
- Duplicate permission logic (use decorators)
- Mix static and dynamic data

## Migration Path

If you need to migrate settings from JSON to database (or vice versa):

1. **JSON → Database**: Use migration script to read JSON and insert into DB
2. **Database → JSON**: Export role definitions to JSON (one-time)

For user data, always use database. JSON is only for role/permission definitions.

## Example: Adding a New Role

1. **Add to JSON** (`app_settings.json`):

```json
{
  "roles": {
    "new_role": {
      "name": "New Role",
      "description": "Description here",
      "hierarchy": 4,
      "permissions": ["clients.view"]
    }
  }
}
```

2. **Add to database schema** (if needed):

```sql
-- Update CHECK constraint in users table
ALTER TABLE users ... -- (SQLite limitations may require table rebuild)
```

3. **Add to Python enum** (`permissions.py`):

```python
class UserRole(str, Enum):
    ...
    NEW_ROLE = "new_role"
```

4. **Update route permissions** (if needed):

```json
{
  "route_permissions": {
    "/new-route": ["new_role", "super_admin"]
  }
}
```

## API Endpoints Summary

### User Management

- `GET /settings/users` - List users
- `GET /settings/users/{user_id}` - Get user
- `POST /settings/users` - Create user
- `PUT /settings/users/{user_id}` - Update user
- `DELETE /settings/users/{user_id}` - Delete user (soft)

### Role Management

- `GET /settings/users/roles` - List all roles
- `GET /settings/users/roles/{role_name}` - Get role info

All endpoints require appropriate permissions (see `api_user_management.py`).
