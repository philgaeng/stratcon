#!/usr/bin/env python3
"""
User Management API endpoints.

Provides CRUD operations for users, user groups, and permissions.
Uses JSON config for role definitions, database for user data.
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field

from backend.services.auth.permissions import UserRole, require_roles, get_user_role_from_request, APP_PERMISSIONS
from backend.services.data.db_manager.db_schema import get_db_connection
from backend.services.settings.app_config import AppConfigManager

user_router = APIRouter(prefix="/settings/users", tags=["User Management"])


# ============================================================================
# Request/Response Models
# ============================================================================

class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""
    email: EmailStr
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    company: Optional[str] = None
    position: Optional[str] = None
    mobile_phone: Optional[str] = None
    landline: Optional[str] = None
    user_group: UserRole
    entity_id: Optional[int] = None
    receive_reports_email: bool = False
    active: bool = True


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""
    first_name: Optional[str] = Field(None, min_length=1)
    last_name: Optional[str] = Field(None, min_length=1)
    company: Optional[str] = None
    position: Optional[str] = None
    mobile_phone: Optional[str] = None
    landline: Optional[str] = None
    user_group: Optional[UserRole] = None
    entity_id: Optional[int] = None
    receive_reports_email: Optional[bool] = None
    active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    email: str
    first_name: str
    last_name: str
    company: Optional[str]
    position: Optional[str]
    mobile_phone: Optional[str]
    landline: Optional[str]
    user_group: str
    entity_id: Optional[int]
    receive_reports_email: bool
    active: bool
    created_at: str
    updated_at: str


class UserListResponse(BaseModel):
    """Response model for user list."""
    users: List[UserResponse]
    total: int


class RoleInfoResponse(BaseModel):
    """Response model for role information from JSON config."""
    name: str
    description: str
    hierarchy: int
    permissions: List[str]


class RolesResponse(BaseModel):
    """Response model for all roles."""
    roles: dict[str, RoleInfoResponse]


# ============================================================================
# User CRUD Endpoints
# ============================================================================

@user_router.get("/", response_model=UserListResponse)
@require_roles(*APP_PERMISSIONS["settings"])
async def list_users(
    request: Request,
    active_only: bool = Query(True, description="Filter to active users only"),
    user_group: Optional[UserRole] = Query(None, description="Filter by user group"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
):
    """
    List all users with optional filtering.
    
    Requires: SUPER_ADMIN or CLIENT_ADMIN role.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Build query with filters
        conditions = []
        params = []
        
        if active_only:
            conditions.append("active = ?")
            params.append(1)
        
        if user_group:
            conditions.append("user_group = ?")
            params.append(user_group.value)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM users{where_clause}", params)
        total = cursor.fetchone()[0]
        
        # Get users
        cursor.execute(
            f"""
            SELECT id, email, first_name, last_name, company, position,
                   mobile_phone, landline, user_group, entity_id,
                   receive_reports_email, active, created_at, updated_at
            FROM users
            {where_clause}
            ORDER BY last_name, first_name
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        )
        
        users = [
            UserResponse(
                id=row["id"],
                email=row["email"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                company=row["company"],
                position=row["position"],
                mobile_phone=row["mobile_phone"],
                landline=row["landline"],
                user_group=row["user_group"],
                entity_id=row["entity_id"],
                receive_reports_email=bool(row["receive_reports_email"]),
                active=bool(row["active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]
        
        return UserListResponse(users=users, total=total)
    
    finally:
        conn.close()


@user_router.get("/{user_id}", response_model=UserResponse)
@require_roles(*APP_PERMISSIONS["settings"])
async def get_user(request: Request, user_id: int):
    """
    Get a specific user by ID.
    
    Requires: SUPER_ADMIN or CLIENT_ADMIN role.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, email, first_name, last_name, company, position,
                   mobile_phone, landline, user_group, entity_id,
                   receive_reports_email, active, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        return UserResponse(
            id=row["id"],
            email=row["email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            company=row["company"],
            position=row["position"],
            mobile_phone=row["mobile_phone"],
            landline=row["landline"],
            user_group=row["user_group"],
            entity_id=row["entity_id"],
            receive_reports_email=bool(row["receive_reports_email"]),
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    finally:
        conn.close()


@user_router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@require_roles(*APP_PERMISSIONS["settings"])
async def create_user(request: Request, user_data: UserCreateRequest):
    """
    Create a new user.
    
    Requires: SUPER_ADMIN or CLIENT_ADMIN role.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {user_data.email} already exists"
            )
        
        # Validate entity_id if provided
        if user_data.entity_id:
            cursor.execute("SELECT id FROM entities WHERE id = ?", (user_data.entity_id,))
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entity with ID {user_data.entity_id} not found"
                )
        
        # Insert user
        cursor.execute(
            """
            INSERT INTO users (
                email, first_name, last_name, company, position,
                mobile_phone, landline, user_group, entity_id,
                receive_reports_email, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_data.email,
                user_data.first_name,
                user_data.last_name,
                user_data.company,
                user_data.position,
                user_data.mobile_phone,
                user_data.landline,
                user_data.user_group.value,
                user_data.entity_id,
                1 if user_data.receive_reports_email else 0,
                1 if user_data.active else 0,
            )
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Fetch created user
        cursor.execute(
            """
            SELECT id, email, first_name, last_name, company, position,
                   mobile_phone, landline, user_group, entity_id,
                   receive_reports_email, active, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )
        
        row = cursor.fetchone()
        return UserResponse(
            id=row["id"],
            email=row["email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            company=row["company"],
            position=row["position"],
            mobile_phone=row["mobile_phone"],
            landline=row["landline"],
            user_group=row["user_group"],
            entity_id=row["entity_id"],
            receive_reports_email=bool(row["receive_reports_email"]),
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    finally:
        conn.close()


@user_router.put("/{user_id}", response_model=UserResponse)
@require_roles(*APP_PERMISSIONS["settings"])
async def update_user(request: Request, user_id: int, user_data: UserUpdateRequest):
    """
    Update an existing user.
    
    Requires: SUPER_ADMIN or CLIENT_ADMIN role.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Validate entity_id if provided
        if user_data.entity_id is not None:
            cursor.execute("SELECT id FROM entities WHERE id = ?", (user_data.entity_id,))
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entity with ID {user_data.entity_id} not found"
                )
        
        # Build update query dynamically
        updates = []
        params = []
        
        if user_data.first_name is not None:
            updates.append("first_name = ?")
            params.append(user_data.first_name)
        
        if user_data.last_name is not None:
            updates.append("last_name = ?")
            params.append(user_data.last_name)
        
        if user_data.company is not None:
            updates.append("company = ?")
            params.append(user_data.company)
        
        if user_data.position is not None:
            updates.append("position = ?")
            params.append(user_data.position)
        
        if user_data.mobile_phone is not None:
            updates.append("mobile_phone = ?")
            params.append(user_data.mobile_phone)
        
        if user_data.landline is not None:
            updates.append("landline = ?")
            params.append(user_data.landline)
        
        if user_data.user_group is not None:
            updates.append("user_group = ?")
            params.append(user_data.user_group.value)
        
        if user_data.entity_id is not None:
            updates.append("entity_id = ?")
            params.append(user_data.entity_id)
        
        if user_data.receive_reports_email is not None:
            updates.append("receive_reports_email = ?")
            params.append(1 if user_data.receive_reports_email else 0)
        
        if user_data.active is not None:
            updates.append("active = ?")
            params.append(1 if user_data.active else 0)
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)
        
        cursor.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params
        )
        
        conn.commit()
        
        # Fetch updated user
        cursor.execute(
            """
            SELECT id, email, first_name, last_name, company, position,
                   mobile_phone, landline, user_group, entity_id,
                   receive_reports_email, active, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )
        
        row = cursor.fetchone()
        return UserResponse(
            id=row["id"],
            email=row["email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            company=row["company"],
            position=row["position"],
            mobile_phone=row["mobile_phone"],
            landline=row["landline"],
            user_group=row["user_group"],
            entity_id=row["entity_id"],
            receive_reports_email=bool(row["receive_reports_email"]),
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )
    finally:
        conn.close()


@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_roles(*APP_PERMISSIONS["settings/super_admin"])
async def delete_user(request: Request, user_id: int):
    """
    Delete a user (soft delete by setting active=False).
    
    Requires: SUPER_ADMIN role.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Soft delete (set active=False)
        cursor.execute(
            "UPDATE users SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
    finally:
        conn.close()


# ============================================================================
# Role & Permission Management Endpoints
# ============================================================================

@user_router.get("/roles", response_model=RolesResponse)
@require_roles(*APP_PERMISSIONS["settings/roles"])
async def get_roles(request: Request):
    """
    Get all available roles and their permissions from JSON config.
    
    Requires: SUPER_ADMIN, CLIENT_ADMIN, or CLIENT_MANAGER role.
    """
    settings_manager = AppConfigManager()
    roles_config = settings_manager.get_roles_config()
    
    roles = {
        role_key: RoleInfoResponse(
            name=role_data["name"],
            description=role_data["description"],
            hierarchy=role_data["hierarchy"],
            permissions=role_data["permissions"],
        )
        for role_key, role_data in roles_config.items()
    }
    
    return RolesResponse(roles=roles)


@user_router.get("/roles/{role_name}", response_model=RoleInfoResponse)
@require_roles(*APP_PERMISSIONS["settings/roles"])
async def get_role(request: Request, role_name: str):
    """
    Get information about a specific role.
    
    Requires: SUPER_ADMIN, CLIENT_ADMIN, or CLIENT_MANAGER role.
    """
    settings_manager = AppConfigManager()
    roles_config = settings_manager.get_roles_config()
    
    if role_name not in roles_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )
    
    role_data = roles_config[role_name]
    return RoleInfoResponse(
        name=role_data["name"],
        description=role_data["description"],
        hierarchy=role_data["hierarchy"],
        permissions=role_data["permissions"],
    )

