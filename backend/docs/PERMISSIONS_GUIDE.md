# Permission System Guide

This document explains how to use the permission system in this FastAPI application.

## Overview

We've built a lightweight permission system similar to Django's, but tailored for FastAPI. It provides:

- **Role-based access control (RBAC)**: 7 user roles
- **Permission decorators**: Easy-to-use decorators for route protection
- **Middleware**: Automatic user role extraction from requests

## User Roles

The system supports 7 roles (in hierarchy order):

1. `super_admin` - Full system access
2. `client_admin` - Manage assigned clients
3. `client_manager` - View/manage assigned clients (no user creation)
4. `viewer` - Read-only access in reports
5. `tenant_user` - Tenant-specific access
6. `encoder` - Can submit meter readings
7. `tenant_approver` - Can approve meter readings

## Usage

### 1. Using Permission Decorators

#### Require Specific Roles

```python
from backend.services.permissions import require_roles, UserRole

@app.get("/admin-only")
@require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN)
async def admin_endpoint(request: Request):
    return {"message": "Admin access granted"}
```

#### Require Minimum Role

```python
from backend.services.permissions import require_minimum_role, UserRole

@app.get("/manager-and-above")
@require_minimum_role(UserRole.CLIENT_MANAGER)
async def manager_endpoint(request: Request):
    return {"message": "Manager or above access granted"}
```

### 2. Manual Permission Checking

```python
from backend.services.permissions import get_user_role_from_request, has_role, UserRole

@app.get("/custom-check")
async def custom_endpoint(request: Request):
    user_role = get_user_role_from_request(request)

    if not has_role(user_role, {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN}):
        raise HTTPException(status_code=403, detail="Access denied")

    return {"message": "Access granted"}
```

### 3. Accessing User Info in Endpoints

After authentication middleware runs, user info is available in `request.state`:

```python
@app.get("/user-info")
async def get_user_info(request: Request):
    user_id = request.state.user_id  # int or None
    user_role = request.state.user_role  # UserRole enum or None
    authenticated = request.state.authenticated  # bool

    return {
        "user_id": user_id,
        "role": user_role.value if user_role else None,
        "authenticated": authenticated
    }
```

## How It Works

1. **AuthMiddleware** (runs on every request):

   - Extracts `user_id` from `x-user-id` header or `user_id` query param
   - Fetches user role from database
   - Stores in `request.state` for use by decorators/endpoints

2. **Permission Decorators**:

   - Check `request.state.user_role`
   - Raise 403 if permission denied
   - Allow request to proceed if permission granted

3. **Route Permissions Mapping**:
   - Defined in `backend/services/permissions.py`
   - Maps routes to allowed roles
   - Used by `check_permission()` utility

## Migration from Current Code

### Before (Manual Checking)

```python
@app.get("/buildings")
async def list_buildings(request: Request):
    scope = _get_user_scope(request)
    if scope.user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # ... rest of code
```

### After (With Decorators)

```python
@app.get("/buildings")
@require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.CLIENT_MANAGER, UserRole.VIEWER)
async def list_buildings(request: Request):
    user_id = request.state.user_id  # Already validated by decorator
    # ... rest of code
```

## Benefits Over Manual Implementation

✅ **Consistent**: All endpoints use same permission system  
✅ **Type-safe**: UserRole enum prevents typos  
✅ **Declarative**: Decorators make permissions obvious  
✅ **Reusable**: Easy to add new roles/permissions  
✅ **Testable**: Can easily mock user roles in tests

## Comparison to Django

| Feature        | Django   | Our System                    |
| -------------- | -------- | ----------------------------- |
| User model     | Built-in | Custom (SQLite)               |
| Authentication | Built-in | Custom (Cognito + middleware) |
| Permissions    | Built-in | Custom (decorators)           |
| Groups         | Built-in | Not needed (simple roles)     |
| Admin panel    | Built-in | Not needed (custom frontend)  |
| Flexibility    | Lower    | Higher (full control)         |
| Performance    | Good     | Better (async FastAPI)        |

## Next Steps

1. Gradually migrate existing endpoints to use decorators
2. Add permission checks to frontend routes
3. Consider adding object-level permissions if needed
4. Add permission tests
