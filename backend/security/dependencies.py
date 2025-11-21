"""
Authentication dependencies for FastAPI.

This module provides dependency functions for protecting FastAPI routes
and extracting authenticated user information.
"""

from typing import Optional, Union, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.admin import Admin
from backend.fastapi.models.user import User
from backend.fastapi.crud.admin import get_admin
from backend.fastapi.crud.user import get_user
from backend.security.auth import verify_access_token


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and validate JWT token from Authorization header.
    
    Args:
        credentials: HTTP Bearer credentials from request header
        
    Returns:
        Dictionary containing decoded token payload
        
    Raises:
        HTTPException: If token is invalid or missing
        
    Usage:
        @app.get("/protected")
        async def protected_route(token_data: dict = Depends(get_current_user_token)):
            return {"user_id": token_data["sub"]}
    """
    return verify_access_token(credentials.credentials)


async def get_current_admin(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_sync_db)
) -> Admin:
    """
    Get current authenticated admin user.
    
    Args:
        token_data: Decoded JWT token payload
        db: Database session
        
    Returns:
        Admin instance for the authenticated user
        
    Raises:
        HTTPException: If admin not found, inactive, or not an admin role
        
    Usage:
        @app.get("/admin-only")
        async def admin_route(current_admin: Admin = Depends(get_current_admin)):
            return {"admin": current_admin.username}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract user ID from token
    user_id = token_data.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Check if user has admin role
    user_role = token_data.get("role")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    
    # Get admin from database
    admin = get_admin(db, user_id)
    if admin is None:
        raise credentials_exception
    
    # Check if admin is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated"
        )
    
    return admin


async def get_current_active_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """
    Get current active admin (alias for get_current_admin).
    
    This is a convenience dependency that ensures the admin is active.
    The get_current_admin already checks for active status.
    
    Args:
        current_admin: Current admin from get_current_admin
        
    Returns:
        Active Admin instance
        
    Usage:
        @app.get("/admin-dashboard")
        async def dashboard(admin: Admin = Depends(get_current_active_admin)):
            return {"welcome": f"Hello {admin.username}!"}
    """
    return current_admin


async def get_optional_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_sync_db)
) -> Optional[Admin]:
    """
    Get current admin if authenticated, None otherwise.
    
    This dependency doesn't raise an error if no token is provided,
    making it useful for optional authentication.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        Admin instance if authenticated, None otherwise
        
    Usage:
        @app.get("/maybe-protected")
        async def maybe_protected(admin: Optional[Admin] = Depends(get_optional_current_admin)):
            if admin:
                return {"message": f"Hello admin {admin.username}"}
            else:
                return {"message": "Hello anonymous user"}
    """
    if credentials is None:
        return None
    
    try:
        token_data = verify_access_token(credentials.credentials)
        user_id = token_data.get("sub")
        user_role = token_data.get("role")
        
        if user_id and user_role == "admin":
            admin = get_admin(db, user_id)
            if admin and admin.is_active:
                return admin
    except HTTPException:
        pass
    
    return None


async def get_current_user(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_sync_db)
) -> User:
    """
    Get current authenticated staff user.
    
    Args:
        token_data: Decoded JWT token payload
        db: Database session
        
    Returns:
        User instance for the authenticated staff member
        
    Raises:
        HTTPException: If user not found, inactive, or not a staff user role
        
    Usage:
        @app.get("/staff-only")
        async def staff_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username, "branch": current_user.branch}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract user ID from token
    user_id = token_data.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Check if user has staff role
    user_role = token_data.get("role")
    if user_role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Staff access required."
        )
    
    # Get user from database with branch loaded
    from sqlalchemy.orm import joinedload
    from backend.fastapi.models.user import User
    user = db.query(User).options(joinedload(User.branch)).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active staff user (alias for get_current_user).
    
    This is a convenience dependency that ensures the user is active.
    The get_current_user already checks for active status.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Active User instance
        
    Usage:
        @app.get("/user-dashboard")
        async def dashboard(user: User = Depends(get_current_active_user)):
            return {"welcome": f"Hello {user.username}!", "branch": user.branch}
    """
    return current_user


async def get_current_admin_or_user(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_sync_db)
) -> Tuple[Union[Admin, User], str]:
    """
    Get current authenticated user (admin or staff) with role information.
    
    Args:
        token_data: Decoded JWT token payload
        db: Database session
        
    Returns:
        Tuple of (user_instance, role) where role is "admin" or "user"
        
    Raises:
        HTTPException: If user not found or inactive
        
    Usage:
        @app.get("/any-authenticated")
        async def mixed_route(user_info: tuple = Depends(get_current_admin_or_user)):
            user, role = user_info
            return {"username": user.username, "role": role}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract user info from token
    user_id = token_data.get("sub")
    user_role = token_data.get("role")
    
    if user_id is None or user_role is None:
        raise credentials_exception
    
    # Get user based on role
    if user_role == "admin":
        user = get_admin(db, user_id)
        if user is None or not user.is_active:
            raise credentials_exception
        return user, "admin"
    
    elif user_role == "user":
        from sqlalchemy.orm import joinedload
        from backend.fastapi.models.user import User
        user = db.query(User).options(joinedload(User.branch)).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return user, "user"
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user role"
        )


# Convenience dependencies for different permission levels
RequireAuth = Depends(get_current_user_token)
RequireAdmin = Depends(get_current_admin)
RequireActiveAdmin = Depends(get_current_active_admin)
RequireUser = Depends(get_current_user)
RequireActiveUser = Depends(get_current_active_user)
RequireAnyAuth = Depends(get_current_admin_or_user)
OptionalAdmin = Depends(get_optional_current_admin)