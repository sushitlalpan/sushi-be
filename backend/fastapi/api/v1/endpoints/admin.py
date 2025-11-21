"""
Admin authentication and management endpoints.

This module provides FastAPI endpoints for admin authentication,
registration, and user management.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.admin import Admin
from backend.fastapi.schemas.admin import (
    AdminCreate, AdminRead, AdminUpdate, AdminLogin,
    Token, TokenResponse
)
from backend.fastapi.crud.admin import (
    create_admin, get_admin, get_admin_by_username,
    get_admins, update_admin, delete_admin
)
from backend.security.password import verify_password
from backend.security.auth import create_admin_token
from backend.security.dependencies import RequireAdmin, RequireActiveAdmin


router = APIRouter(tags=["authentication"])
admin_router = APIRouter(tags=["admin"])


@router.post("/login", response_model=TokenResponse, summary="Admin Login")
async def login(
    admin_login: AdminLogin,
    db: Session = Depends(get_sync_db)
):
    """
    Authenticate admin user and return JWT access token.
    
    **Process:**
    1. Validate username and password
    2. Check if admin account is active
    3. Generate JWT access token with admin role
    4. Return token with user information
    
    **Parameters:**
    - **username**: Admin username
    - **password**: Admin password (plain text, will be hashed)
    
    **Returns:**
    - **access_token**: JWT token for authenticated requests
    - **token_type**: Bearer token type
    - **expires_in**: Token expiration time in seconds
    - **admin**: Admin user information (without password)
    
    **Errors:**
    - **401**: Invalid credentials or inactive account
    """
    # Get admin by username
    admin = get_admin_by_username(db, admin_login.username)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(admin_login.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if admin is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated",
        )
    
    # Create access token
    access_token = create_admin_token(str(admin.id), admin.username)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes
        admin=AdminRead.model_validate(admin)
    )


@router.post("/bootstrap", response_model=AdminRead, summary="Bootstrap First Admin (Public)")
async def bootstrap_admin(
    admin_create: AdminCreate,
    db: Session = Depends(get_sync_db)
):
    """
    Bootstrap the first admin user (public endpoint).
    
    **WARNING: This endpoint is only for initial setup and should be disabled in production!**
    
    This endpoint allows creating the first admin user without authentication.
    It will only work if there are no existing admin users in the database.
    
    **Parameters:**
    - **username**: Unique admin username (3-50 chars)
    - **password**: Admin password (8+ chars)
    - **is_active**: Whether account is active (default: true)
    
    **Returns:**
    - Admin user information (without password)
    
    **Errors:**
    - **403**: Admin users already exist (bootstrap not allowed)
    - **409**: Username already exists
    - **422**: Validation errors
    """
    # Check if any admin users already exist
    existing_admins = get_admins(db, limit=1)
    if existing_admins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap not allowed - admin users already exist. Use /register endpoint with admin authentication."
        )
    
    try:
        admin = create_admin(db, admin_create)
        return AdminRead.model_validate(admin)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bootstrap admin: {str(e)}"
        )


@router.post("/register", response_model=AdminRead, summary="Register New Admin")
async def register(
    admin_create: AdminCreate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Register a new admin user (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Process:**
    1. Validate admin data
    2. Check username uniqueness
    3. Hash password securely
    4. Create admin account
    5. Return admin information
    
    **Parameters:**
    - **username**: Unique admin username (3-50 chars)
    - **password**: Admin password (8+ chars)
    - **is_active**: Whether account is active (default: true)
    
    **Returns:**
    - Admin user information (without password)
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated  
    - **409**: Username already exists
    - **422**: Validation errors (username/password format)
    """
    try:
        admin = create_admin(db, admin_create)
        return AdminRead.model_validate(admin)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin: {str(e)}"
        )


@admin_router.get("/me", response_model=AdminRead, summary="Get Current Admin")
async def get_me(current_admin: Admin = RequireActiveAdmin):
    """
    Get current authenticated admin information.
    
    **Permissions:** Requires active admin authentication
    
    **Returns:**
    - Current admin user information (without password)
    
    **Errors:**
    - **401**: Not authenticated or invalid token
    - **403**: Admin account deactivated
    """
    return AdminRead.model_validate(current_admin)


@admin_router.get("/", response_model=List[AdminRead], summary="List All Admins")
async def list_admins(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get list of all admin users (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    
    **Returns:**
    - List of admin users (without passwords)
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    """
    admins = get_admins(db, skip=skip, limit=limit)
    return [AdminRead.model_validate(admin) for admin in admins]


@admin_router.get("/{admin_id}", response_model=AdminRead, summary="Get Admin by ID")
async def get_admin_by_id(
    admin_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get specific admin user by ID (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **admin_id**: UUID of the admin user
    
    **Returns:**
    - Admin user information (without password)
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Admin not found
    - **422**: Invalid UUID format
    """
    admin = get_admin(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return AdminRead.model_validate(admin)


@admin_router.put("/{admin_id}", response_model=AdminRead, summary="Update Admin")
async def update_admin_by_id(
    admin_id: UUID,
    admin_update: AdminUpdate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Update admin user information (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Process:**
    1. Validate admin exists
    2. Check username uniqueness (if changing)
    3. Hash new password (if provided)
    4. Update admin information
    5. Return updated admin data
    
    **Parameters:**
    - **admin_id**: UUID of admin to update
    - **username**: New username (optional)
    - **password**: New password (optional)
    - **is_active**: New active status (optional)
    
    **Returns:**
    - Updated admin information (without password)
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Admin not found
    - **409**: Username already exists (if changing username)
    - **422**: Invalid data format
    """
    admin = get_admin(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    try:
        updated_admin = update_admin(db, admin_id, admin_update)
        return AdminRead.model_validate(updated_admin)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update admin: {str(e)}"
        )


@admin_router.delete("/{admin_id}", summary="Delete Admin")
async def delete_admin_by_id(
    admin_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Delete admin user (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Security Notes:**
    - Admins cannot delete themselves
    - Consider soft deletion for audit trails
    
    **Parameters:**
    - **admin_id**: UUID of admin to delete
    
    **Returns:**
    - Success message with deleted admin ID
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated or trying to delete self
    - **404**: Admin not found
    """
    # Check if admin exists
    admin = get_admin(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Prevent self-deletion
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own admin account"
        )
    
    # Delete admin
    success = delete_admin(db, admin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete admin"
        )
    
    return {"message": "Admin deleted successfully", "admin_id": str(admin_id)}


# Test endpoint for authentication
@admin_router.get("/test/protected", summary="Test Protected Route")
async def test_protected_route(current_admin: Admin = RequireActiveAdmin):
    """
    Test endpoint to verify authentication works correctly.
    
    **Permissions:** Requires active admin authentication
    
    This is a dummy protected route for testing JWT authentication.
    Use this endpoint to verify that:
    1. JWT tokens are properly validated
    2. Admin role checking works
    3. Active status is enforced
    
    **Returns:**
    - Success message with admin information
    - Current timestamp
    - Token validation confirmation
    
    **Errors:**
    - **401**: Not authenticated or invalid token
    - **403**: Admin account deactivated or not admin role
    """
    from datetime import datetime, timezone
    
    return {
        "message": "Authentication successful! 🎉",
        "admin": {
            "id": str(current_admin.id),
            "username": current_admin.username,
            "is_active": current_admin.is_active
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route_protection": "This route requires valid JWT token with admin role",
        "test_status": "PASSED - Authentication and authorization working correctly"
    }