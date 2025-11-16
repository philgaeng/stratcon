# Route Protection Guide

This guide explains how route protection works for both the Reports and Meters apps.

## Overview

The system protects routes at two levels:

1. **Backend API routes** - Protected by middleware and decorators
2. **Frontend routes** - Protected by React hooks

## App-Level Permissions

### Reports App

**Allowed roles:**

- `super_admin`
- `client_admin`
- `client_manager`
- `viewer`

### Meters App

**Allowed roles:**

- `super_admin`
- `client_admin`
- `encoder`

## Backend Protection

### 1. Authentication Middleware

The `AuthMiddleware` automatically:

- Extracts `user_id` from `x-user-id` header or `user_id` query parameter
- Fetches user role from database
- Checks route permissions
- Returns 403 if user doesn't have access

**Location:** `backend/middleware/auth_middleware.py`

### 2. Permission Decorators

You can also use decorators on individual endpoints:

```python
from backend.services.permissions import require_roles, UserRole

@meter_router.get("/buildings")
@require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.ENCODER)
async def list_buildings(...):
    ...
```

### 3. Route Permissions Mapping

Routes are mapped to allowed roles in `backend/services/permissions.py`:

```python
APP_PERMISSIONS = {
    "reports": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.CLIENT_MANAGER, UserRole.VIEWER},
    "meters": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.ENCODER},
}

ROUTE_PERMISSIONS = {
    "/clients": APP_PERMISSIONS["reports"],
    "/meters/v1/buildings": APP_PERMISSIONS["meters"],
    # ... etc
}
```

## Frontend Protection

### 1. Route Guard Hook

Use the `useRouteGuard` hook in your page components:

```typescript
import { useRouteGuard } from "@/lib/hooks/useRouteGuard";

export default function MetersPage() {
  // Protect route - only allow super_admin, client_admin, encoder
  useRouteGuard("meters");

  // ... rest of component
}
```

**Location:** `website/lib/hooks/useRouteGuard.ts`

### 2. How It Works

1. Hook checks if user is authenticated
2. Fetches user info (including role) from `useUserInfo()` hook
3. Checks if user role is in allowed roles for the app
4. Redirects to login if access denied

### 3. Conditional Access Check

For conditional rendering (e.g., showing/hiding navigation links):

```typescript
import { hasAppAccess } from "@/lib/hooks/useRouteGuard";
import { useUserInfo } from "@/lib/hooks/useUserInfo";

export default function Navigation() {
  const { userInfo } = useUserInfo();

  const canAccessReports = hasAppAccess(userInfo?.role, "reports");
  const canAccessMeters = hasAppAccess(userInfo?.role, "meters");

  return (
    <nav>
      {canAccessReports && <Link href="/reports">Reports</Link>}
      {canAccessMeters && <Link href="/meters">Meters</Link>}
    </nav>
  );
}
```

## Testing Access Control

### Test Backend

```bash
# Test with encoder (should have access to meters)
curl -H "x-user-id: 1" http://localhost:8000/meters/v1/buildings?user_id=1

# Test with viewer (should NOT have access to meters)
curl -H "x-user-id: 2" http://localhost:8000/meters/v1/buildings?user_id=2
# Expected: 403 Forbidden
```

### Test Frontend

1. Login as different user roles
2. Try accessing `/meters` and `/reports`
3. Verify redirects work correctly

## Adding New Routes

### Backend

1. Add route to `ROUTE_PERMISSIONS` in `backend/services/permissions.py`:

   ```python
   "/new/route": APP_PERMISSIONS["meters"],  # or "reports"
   ```

2. Optionally add decorator to endpoint:
   ```python
   @require_roles(UserRole.SUPER_ADMIN, UserRole.ENCODER)
   ```

### Frontend

1. Add `useRouteGuard("meters")` or `useRouteGuard("reports")` to page component

## Troubleshooting

### 403 Forbidden on Backend

- Check if `x-user-id` header is set
- Verify user role in database matches expected format
- Check route is in `ROUTE_PERMISSIONS` mapping
- Verify route pattern matching (for routes with path parameters)

### Frontend Redirect Loop

- Ensure `useUserInfo()` hook is working
- Check user role format matches `UserRole` enum
- Verify `APP_PERMISSIONS` includes the user's role

### Role Not Recognized

- Check database: `SELECT id, email, role FROM users WHERE id = ?`
- Verify role string matches exactly (case-sensitive)
- Check `UserRole` enum in `backend/services/permissions.py`
