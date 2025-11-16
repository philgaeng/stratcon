#!/usr/bin/env python3
"""
Permission system for FastAPI - lightweight alternative to Django's permissions.

Provides:
- Role-based access control (RBAC)
- Permission decorators
- Permission checking utilities
"""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set

from fastapi import HTTPException, Request, status


class UserRole(str, Enum):
    """User roles in the system."""
    SUPER_ADMIN = "super_admin"
    CLIENT_ADMIN = "client_admin"
    CLIENT_MANAGER = "client_manager"
    VIEWER = "viewer"
    TENANT_USER = "tenant_user"
    ENCODER = "encoder"
    TENANT_APPROVER = "tenant_approver"


# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    UserRole.SUPER_ADMIN: 7,
    UserRole.CLIENT_ADMIN: 6,
    UserRole.CLIENT_MANAGER: 5,
    UserRole.VIEWER: 4,
    UserRole.TENANT_USER: 3,
    UserRole.ENCODER: 2,
    UserRole.TENANT_APPROVER: 1,
}


# App-level permissions
APP_PERMISSIONS = {
    "reports": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.CLIENT_MANAGER, UserRole.VIEWER},
    "meters": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.ENCODER},
}

# Route permissions mapping
ROUTE_PERMISSIONS = {
    # Reporting routes (all accessible to reports app roles)
    "/clients": APP_PERMISSIONS["reports"],
    "/buildings": APP_PERMISSIONS["reports"],
    "/tenants": APP_PERMISSIONS["reports"],
    "/reports/tenant": APP_PERMISSIONS["reports"],
    "/reports/client": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN},
    "/reports/generate_last_records": APP_PERMISSIONS["reports"],
    "/reports/generate_billing_info": APP_PERMISSIONS["reports"],
    "/settings/client": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN},
    "/settings/tenant": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN},
    "/settings/cutoff": APP_PERMISSIONS["reports"],
    
    # Meter logging routes (all accessible to meters app roles)
    "/meters/v1/buildings": APP_PERMISSIONS["meters"],
    "/meters/v1/buildings/{building_id}/tenants": APP_PERMISSIONS["meters"],
    "/meters/v1/tenants": APP_PERMISSIONS["meters"],
    "/meters/v1/tenants/{tenant_id}/floors": APP_PERMISSIONS["meters"],
    "/meters/v1/tenants/{tenant_id}/meters": APP_PERMISSIONS["meters"],
    "/meters/v1/records": APP_PERMISSIONS["meters"],
    "/meters/v1/approvals": {UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.TENANT_APPROVER},
    "/meters/v1/meter-records": APP_PERMISSIONS["meters"],
    "/meters/v1/user-id": APP_PERMISSIONS["meters"],  # Used by frontend to get user info
    "/meters/v1/user-info": APP_PERMISSIONS["meters"],  # Used by frontend to get user info
}


def get_user_role_from_request(request: Request) -> Optional[UserRole]:
    """
    Extract user role from request.
    
    This assumes user info is stored in request.state after authentication middleware.
    """
    if not hasattr(request.state, "user_role"):
        return None
    
    role_str = request.state.user_role
    try:
        return UserRole(role_str)
    except ValueError:
        return None


def has_role(user_role: Optional[UserRole], allowed_roles: Set[UserRole]) -> bool:
    """Check if user role is in allowed roles."""
    if user_role is None:
        return False
    return user_role in allowed_roles


def has_minimum_role(user_role: Optional[UserRole], minimum_role: UserRole) -> bool:
    """Check if user role meets minimum hierarchy level."""
    if user_role is None:
        return False
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(minimum_role, 0)


def require_roles(*allowed_roles: UserRole):
    """
    Decorator to require specific roles for an endpoint.
    
    Usage:
        @app.get("/admin")
        @require_roles(UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN)
        async def admin_endpoint(request: Request):
            ...
    """
    allowed_set = set(allowed_roles)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request object in args/kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")
            
            if request is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found",
                )
            
            user_role = get_user_role_from_request(request)
            
            if not has_role(user_role, allowed_set):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_minimum_role(minimum_role: UserRole):
    """
    Decorator to require minimum role hierarchy level.
    
    Usage:
        @app.get("/admin")
        @require_minimum_role(UserRole.CLIENT_ADMIN)
        async def admin_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")
            
            if request is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found",
                )
            
            user_role = get_user_role_from_request(request)
            
            if not has_minimum_role(user_role, minimum_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Minimum role required: {minimum_role.value}",
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_permission(user_role: Optional[UserRole], route: str) -> bool:
    """
    Check if user has permission for a route.
    
    Args:
        user_role: User's role
        route: Route path (e.g., "/meters/v1/buildings" or "/meters/v1/buildings/123/tenants")
    
    Returns:
        True if user has permission, False otherwise
    """
    if user_role is None:
        return False
    
    # Check exact route match
    if route in ROUTE_PERMISSIONS:
        return user_role in ROUTE_PERMISSIONS[route]
    
    # Check pattern matches (for routes with path parameters)
    # e.g., "/meters/v1/buildings/123/tenants" should match "/meters/v1/buildings/{building_id}/tenants"
    import re
    for route_pattern, allowed_roles in ROUTE_PERMISSIONS.items():
        # Convert pattern to regex (replace {param} with \d+)
        pattern = route_pattern.replace("{", "(?P<").replace("}", ">\\d+)")
        pattern = "^" + pattern.replace("/", "\\/") + "$"
        if re.match(pattern, route):
            return user_role in allowed_roles
    
    # Check prefix matches (for nested routes)
    # e.g., "/meters/v1/buildings/123/tenants" should match "/meters/v1/buildings"
    for route_prefix, allowed_roles in ROUTE_PERMISSIONS.items():
        # Remove path parameters for prefix matching
        clean_prefix = route_prefix.split("{")[0].rstrip("/")
        if route.startswith(clean_prefix + "/") or route == clean_prefix:
            return user_role in allowed_roles
    
    # Default: deny access if route not in permissions map
    return False

