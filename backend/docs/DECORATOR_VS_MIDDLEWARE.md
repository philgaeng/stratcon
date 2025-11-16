# Decorator vs Middleware: When to Use Each

## Quick Answer

**You don't need decorators on every endpoint!** The middleware already protects all routes automatically.

## How It Works

### 1. Middleware (Automatic Protection)

The `AuthMiddleware` automatically checks **all routes** against the `ROUTE_PERMISSIONS` mapping:

```python
# In backend/services/permissions.py
ROUTE_PERMISSIONS = {
    "/meters/v1/buildings": APP_PERMISSIONS["meters"],  # Auto-protected!
    "/meters/v1/tenants": APP_PERMISSIONS["meters"],     # Auto-protected!
    # ... etc
}
```

**This means:**

- ✅ All routes in `ROUTE_PERMISSIONS` are automatically protected
- ✅ No decorators needed for standard app-level permissions
- ✅ Works for all HTTP methods (GET, POST, PUT, DELETE)

### 2. Decorators (Optional, for Special Cases)

Decorators are useful when:

- You need **different permissions** for a specific endpoint
- You want **explicit documentation** in the code
- You want **defense in depth** (extra layer of protection)

## When to Use Decorators

### ✅ Use Decorator When:

1. **Different permissions than app default:**

   ```python
   # Most meters routes allow: super_admin, client_admin, encoder
   # But approvals need tenant_approver too
   @meter_router.post("/approvals")
   @require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.TENANT_APPROVER)
   async def attach_approval(...):
       ...
   ```

2. **Explicit documentation:**

   ```python
   # Makes it clear what permissions are needed
   @require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN)
   async def admin_only_endpoint(...):
       ...
   ```

3. **Defense in depth:**
   - Extra protection if middleware is bypassed
   - Useful for critical endpoints

### ❌ Don't Use Decorator When:

1. **Route already in ROUTE_PERMISSIONS:**

   ```python
   # This is already protected by middleware!
   # Decorator is redundant
   @meter_router.get("/buildings")
   @require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.ENCODER)  # ❌ Not needed
   async def list_buildings(...):
       ...
   ```

2. **Standard app-level permissions:**
   - If endpoint uses `APP_PERMISSIONS["meters"]` or `APP_PERMISSIONS["reports"]`
   - Middleware handles it automatically

## Current State

### Meters App Routes

All these routes are **automatically protected** by middleware:

```python
# All protected via ROUTE_PERMISSIONS mapping
"/meters/v1/buildings"                    # ✅ Auto-protected
"/meters/v1/buildings/{building_id}/tenants"  # ✅ Auto-protected
"/meters/v1/tenants"                       # ✅ Auto-protected
"/meters/v1/tenants/{tenant_id}/floors"   # ✅ Auto-protected
"/meters/v1/tenants/{tenant_id}/meters"   # ✅ Auto-protected
"/meters/v1/records"                      # ✅ Auto-protected
"/meters/v1/meter-records"                # ✅ Auto-protected
"/meters/v1/user-id"                      # ✅ Auto-protected
"/meters/v1/user-info"                    # ✅ Auto-protected
```

**Only `/meters/v1/approvals` needs special handling** because it allows `TENANT_APPROVER` in addition to meters app roles.

## Recommendation

### Option 1: Rely on Middleware (Simpler) ✅ Recommended

**Pros:**

- Less code
- Centralized permission management
- Easier to maintain

**Cons:**

- Permissions not visible in endpoint code
- Need to update `ROUTE_PERMISSIONS` when adding routes

**Best for:** Most endpoints with standard app-level permissions

### Option 2: Use Decorators (More Explicit)

**Pros:**

- Permissions visible in code
- Self-documenting
- Defense in depth

**Cons:**

- More code to maintain
- Can be redundant with middleware

**Best for:** Endpoints with special permission requirements

## Best Practice

**Hybrid Approach:**

1. **Use middleware for standard routes** (most endpoints)
2. **Use decorators only for special cases:**
   - Different permissions than app default
   - Critical endpoints needing extra protection
   - When you want explicit documentation

## Example: Current Meters App

```python
# Standard endpoint - middleware handles it
@meter_router.get("/buildings")
async def list_buildings(...):
    # Protected by middleware via ROUTE_PERMISSIONS
    ...

# Special case - needs different permissions
@meter_router.post("/approvals")
@require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.TENANT_APPROVER)
async def attach_approval(...):
    # Needs tenant_approver in addition to meters app roles
    ...
```

## Summary

**Answer: No, you don't need decorators on all endpoints.**

- ✅ Middleware automatically protects all routes in `ROUTE_PERMISSIONS`
- ✅ Only add decorators for special cases (different permissions)
- ✅ Current setup is correct - middleware handles most routes
