#!/usr/bin/env python3
"""
Authentication middleware for FastAPI.

Extracts user information from request and stores it in request.state
for use by permission decorators.
"""

from typing import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.services.data.db_manager.db_schema import get_db_connection
from backend.services.auth.permissions import UserRole, check_permission


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate user authentication.
    
    Looks for user_id in:
    1. x-user-id header
    2. user_id query parameter
    
    Then fetches user role from database and stores in request.state.
    Also enforces route-level permissions.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip auth for public endpoints
        public_paths = [
            "/", 
            "/docs", 
            "/openapi.json", 
            "/redoc", 
            "/meters/v1/meta",
            "/meters/v1/user-info",  # Public - used to get user info by email during login
            "/meters/v1/user-id",    # Public - used to get user ID by email during login
        ]
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Extract user_id from header or query param
        user_id = None
        header_user_id = request.headers.get("x-user-id") or request.headers.get("x-userid")
        if header_user_id:
            try:
                user_id = int(header_user_id.strip())
            except ValueError:
                pass
        
        if user_id is None:
            query_user_id = request.query_params.get("user_id")
            if query_user_id:
                try:
                    user_id = int(query_user_id.strip())
                except ValueError:
                    pass
        
        # If no user_id, allow request but mark as unauthenticated
        if user_id is None:
            request.state.user_id = None
            request.state.user_role = None
            request.state.authenticated = False
            return await call_next(request)
        
        # Fetch user role from database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_group, active FROM users WHERE id = ? LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row is None or not row["active"]:
                request.state.user_id = None
                request.state.user_role = None
                request.state.authenticated = False
            else:
                request.state.user_id = user_id
                try:
                    request.state.user_role = UserRole(row["user_group"])
                except ValueError:
                    # Invalid role, treat as unauthenticated
                    request.state.user_role = None
                request.state.authenticated = True
        except Exception:
            # Database error, allow request but mark as unauthenticated
            request.state.user_id = None
            request.state.user_role = None
            request.state.authenticated = False
        
        # Check route permissions if user is authenticated
        if request.state.authenticated and request.state.user_role:
            user_role = request.state.user_role
            route_path = request.url.path
            
            # Check if user has permission for this route
            if not check_permission(user_role, route_path):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": f"Access denied. Role '{user_role.value}' does not have permission to access '{route_path}'"
                    }
                )
        
        return await call_next(request)

