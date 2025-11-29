"""
Staff user authentication and management endpoints.

This module provides FastAPI endpoints for staff user authentication,
registration, clock-in/out, and user management.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User
from backend.fastapi.models.admin import Admin
from backend.fastapi.schemas.user import (
    UserCreate, UserRead, UserUpdate, UserLogin,
    UserTokenResponse, UnifiedProfileRead
)
from backend.fastapi.crud.user import (
    create_user, get_user, get_user_by_username,
    get_users, update_user, delete_user
)
from backend.security.password import verify_password
from backend.security.auth import create_user_token
from backend.security.dependencies import RequireAdmin, RequireActiveAdmin, RequireActiveUser, get_current_admin_or_user
from backend.fastapi.core.init_settings import global_settings


router = APIRouter(tags=["user-authentication"])
user_router = APIRouter(tags=["users"])


@router.post("/login", response_model=UserTokenResponse, summary="Staff User Login")
async def user_login(
    user_login: UserLogin,
    db: Session = Depends(get_sync_db)
):
    """
    Authenticate staff user and return JWT access token.
    
    **Process:**
    1. Validate username and password
    2. Check if user account is active
    3. Generate JWT access token with user role
    4. Return token with user information
    
    **Parameters:**
    - **username**: Staff username
    - **password**: Staff password (plain text, will be hashed)
    
    **Returns:**
    - **access_token**: JWT token for authenticated requests
    - **token_type**: Bearer token type
    - **expires_in**: Token expiration time in seconds
    - **user**: Staff user information (without password)
    
    **Errors:**
    - **401**: Invalid credentials or inactive account
    """
    # Get user by username
    user = get_user_by_username(db, user_login.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(user_login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
        )
    
    # Create access token
    # Convert branch_id UUID to string for the token
    access_token = create_user_token(str(user.id), user.username, str(user.branch_id))
    
    return UserTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=global_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
        user=UserRead(
            id=user.id,
            username=user.username,
            branch_name=user.branch.name if user.branch else "Unknown Branch",
            phone_number=user.phone_number,
            fingerprint_id=user.fingerprint_id,
            shift_start_time=user.shift_start_time,
            shift_end_time=user.shift_end_time,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    )


@router.post("/register", response_model=UserRead, summary="Register New Staff User")
async def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Register a new staff user (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Process:**
    1. Validate user data
    2. Check username uniqueness
    3. Hash password securely
    4. Create user account
    5. Return user information
    
    **Parameters:**
    - **username**: Unique staff username (3-50 chars)
    - **password**: Staff password (8+ chars)
    - **branch_id**: Restaurant branch UUID (from branches table)
    - **phone_number**: Phone number (optional)
    - **fingerprint_id**: Biometric ID (optional)
    - **is_active**: Whether account is active (default: true)
    
    **Returns:**
    - Staff user information (without password)
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated  
    - **409**: Username already exists
    - **422**: Validation errors (username/password format)
    """
    try:
        user = create_user(db, user_create)
        # Refresh to load branch relationship
        from sqlalchemy.orm import joinedload
        user_with_branch = db.query(User).options(joinedload(User.branch)).filter(User.id == user.id).first()
        return UserRead(
            id=user_with_branch.id,
            username=user_with_branch.username,
            branch_name=user_with_branch.branch.name if user_with_branch.branch else "Unknown Branch",
            phone_number=user_with_branch.phone_number,
            fingerprint_id=user_with_branch.fingerprint_id,
            shift_start_time=user_with_branch.shift_start_time,
            shift_end_time=user_with_branch.shift_end_time,
            is_active=user_with_branch.is_active,
            created_at=user_with_branch.created_at,
            updated_at=user_with_branch.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )



@user_router.get("/me", response_model=UnifiedProfileRead, summary="Get Current User Profile")
async def get_me(
    current_user_info: tuple = Depends(get_current_admin_or_user)
):
    """
    Get current authenticated user profile (works for both admins and staff users).
    
    **Permissions:** Requires authentication (admin or user)
    
    **Returns:**
    - Current user profile information (without password)
    - **is_admin**: Boolean indicating if user is admin
    - **branch_name**: Only populated for staff users
    - **User-specific fields**: Only populated for staff users
    
    **Errors:**
    - **401**: Not authenticated or invalid token
    - **403**: Account deactivated
    """
    user, role = current_user_info
    
    if role == "admin":
        return UnifiedProfileRead(
            id=user.id,
            username=user.username,
            is_admin=True,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            # Admin-specific fields are None
            branch_id=None,
            branch_name=None,
            phone_number=None,
            fingerprint_id=None,
            shift_start_time=None,
            shift_end_time=None
        )
    else:  # role == "user"
        return UnifiedProfileRead(
            id=user.id,
            username=user.username,
            is_admin=False,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            # User-specific fields
            branch_id=user.branch_id,
            branch_name=user.branch.name if user.branch else "Unknown Branch",
            phone_number=user.phone_number,
            fingerprint_id=user.fingerprint_id,
            shift_start_time=user.shift_start_time,
            shift_end_time=user.shift_end_time
        )


@user_router.get("/", response_model=List[UserRead], summary="List All Staff Users")
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    include_inactive: bool = Query(False, description="Include inactive users"),
    db: Session = Depends(get_sync_db),
    current_user: Admin | User = Depends(get_current_admin_or_user)
):
    """
    Get list of all staff users.
    
    **Permissions:** Requires authentication (admin or user)
    
    **Parameters:**
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (1-1000)
    - **branch**: Filter by specific branch (optional)
    - **include_inactive**: Include deactivated users (admins only)
    
    **Returns:**
    - List of staff users (without passwords)
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: Account deactivated
    """
    # Users cannot see inactive users, only admins can
    if not isinstance(current_user, Admin):
        include_inactive = False
        
    users = get_users(db, skip=skip, limit=limit, branch=branch, include_inactive=include_inactive)
    return [
        UserRead(
            id=user.id,
            username=user.username,
            branch_name=user.branch.name if user.branch else "Unknown Branch",
            phone_number=user.phone_number,
            fingerprint_id=user.fingerprint_id,
            shift_start_time=user.shift_start_time,
            shift_end_time=user.shift_end_time,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        for user in users
    ]




@user_router.get("/{user_id}", response_model=UserRead, summary="Get User by ID")
async def get_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_sync_db),
    current_user: Admin | User = Depends(get_current_admin_or_user)
):
    """
    Get specific staff user by ID.
    
    **Permissions:** Requires authentication (admin or user)
    
    **Parameters:**
    - **user_id**: UUID of the staff user
    
    **Returns:**
    - Staff user information (without password)
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: Account deactivated
    - **404**: User not found
    - **422**: Invalid UUID format
    """
    from sqlalchemy.orm import joinedload
    user = db.query(User).options(joinedload(User.branch)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserRead(
        id=user.id,
        username=user.username,
        branch_name=user.branch.name if user.branch else "Unknown Branch",
        phone_number=user.phone_number,
        fingerprint_id=user.fingerprint_id,
        shift_start_time=user.shift_start_time,
        shift_end_time=user.shift_end_time,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@user_router.put("/{user_id}", response_model=UserRead, summary="Update User")
async def update_user_by_id(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Update staff user information (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **user_id**: UUID of user to update
    - **username**: New username (optional)
    - **password**: New password (optional)
    - **branch**: New branch assignment (optional)
    - **phone_number**: New phone number (optional)
    - **fingerprint_id**: New fingerprint ID (optional)
    - **is_active**: New active status (optional)
    
    **Returns:**
    - Updated user information (without password)
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: User not found
    - **409**: Username already exists (if changing username)
    - **422**: Invalid data format
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        updated_user = update_user(db, user_id, user_update)
        # Refresh to load branch relationship
        from sqlalchemy.orm import joinedload
        user_with_branch = db.query(User).options(joinedload(User.branch)).filter(User.id == updated_user.id).first()
        return UserRead(
            id=user_with_branch.id,
            username=user_with_branch.username,
            branch_name=user_with_branch.branch.name if user_with_branch.branch else "Unknown Branch",
            phone_number=user_with_branch.phone_number,
            fingerprint_id=user_with_branch.fingerprint_id,
            shift_start_time=user_with_branch.shift_start_time,
            shift_end_time=user_with_branch.shift_end_time,
            is_active=user_with_branch.is_active,
            created_at=user_with_branch.updated_at,
            updated_at=user_with_branch.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@user_router.delete("/{user_id}", summary="Delete User")
async def delete_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Delete staff user (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Security Notes:**
    - Consider soft deletion for audit trails
    - Ensure user is clocked out before deletion
    
    **Parameters:**
    - **user_id**: UUID of user to delete
    
    **Returns:**
    - Success message with deleted user ID
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: User not found
    """
    # Check if user exists
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Delete user
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
    
    return {"message": "User deleted successfully", "user_id": str(user_id)}


# Test endpoint for staff authentication
@user_router.get("/test/protected", summary="Test Staff Protected Route")
async def test_staff_protected_route(current_user: User = RequireActiveUser):
    """
    Test endpoint to verify staff user authentication works correctly.
    
    **Permissions:** Requires active staff user authentication
    
    This is a dummy protected route for testing JWT authentication for staff.
    Use this endpoint to verify that:
    1. JWT tokens are properly validated for staff users
    2. User role checking works
    3. Active status is enforced
    
    **Returns:**
    - Success message with user information
    - Current timestamp
    - Token validation confirmation
    
    **Errors:**
    - **401**: Not authenticated or invalid token
    - **403**: User account deactivated or not staff role
    """
    from datetime import datetime, timezone
    
    return {
        "message": "Staff authentication successful! 👨‍🍳",
        "user": {
            "id": str(current_user.id),
            "username": current_user.username,
            "branch": current_user.branch,
            "is_active": current_user.is_active,
            "scheduled_shift": f"{current_user.shift_start_time} - {current_user.shift_end_time}" if current_user.shift_start_time and current_user.shift_end_time else None
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route_protection": "This route requires valid JWT token with staff user role",
        "test_status": "PASSED - Staff authentication and authorization working correctly"
    }
