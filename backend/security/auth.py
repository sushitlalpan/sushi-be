"""
JWT authentication utilities for the FastAPI application.

This module provides functions for creating, validating, and decoding JWT tokens
for user authentication and authorization.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status

from backend.fastapi.core.init_settings import global_settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing token payload data (user_id, username, etc.)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token as string
        
    Example:
        >>> token_data = {"sub": "user_id", "username": "admin"}
        >>> token = create_access_token(token_data)
        >>> len(token) > 100  # JWT tokens are long strings
        True
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=global_settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Add expiration and issued at timestamps
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    # Create and return encoded JWT
    encoded_jwt = jwt.encode(
        to_encode, 
        global_settings.JWT_SECRET_KEY, 
        algorithm=global_settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Dictionary containing decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or malformed
        
    Example:
        >>> token = create_access_token({"sub": "user_id"})
        >>> payload = verify_access_token(token)
        >>> "sub" in payload
        True
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token,
            global_settings.JWT_SECRET_KEY,
            algorithms=[global_settings.JWT_ALGORITHM]
        )
        
        # Check if token has required claims
        if payload.get("sub") is None:
            raise credentials_exception
            
        return payload
        
    except JWTError:
        raise credentials_exception


def get_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    Get token payload without raising exceptions.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing token payload, or None if invalid
        
    Example:
        >>> token = create_access_token({"sub": "user_id"})
        >>> payload = get_token_payload(token)
        >>> payload is not None
        True
    """
    try:
        return verify_access_token(token)
    except HTTPException:
        return None


def create_admin_token(admin_id: str, username: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token specifically for admin users.
    
    Args:
        admin_id: Admin user ID (UUID as string)
        username: Admin username
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token for admin user
        
    Example:
        >>> token = create_admin_token("123e4567-e89b-12d3-a456-426614174000", "admin")
        >>> payload = verify_access_token(token)
        >>> payload["role"] == "admin"
        True
    """
    token_data = {
        "sub": admin_id,
        "username": username,
        "role": "admin"
    }
    
    return create_access_token(token_data, expires_delta)


def create_user_token(user_id: str, username: str, branch: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token specifically for staff users.
    
    Args:
        user_id: User ID (UUID as string)
        username: User username
        branch: User's branch/location
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token for staff user
        
    Example:
        >>> token = create_user_token("123e4567-e89b-12d3-a456-426614174000", "john_doe", "downtown")
        >>> payload = verify_access_token(token)
        >>> payload["role"] == "user"
        True
    """
    token_data = {
        "sub": user_id,
        "username": username,
        "branch": branch,
        "role": "user"
    }
    
    return create_access_token(token_data, expires_delta)


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired without raising exceptions.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is expired, False if valid or malformed
    """
    try:
        payload = jwt.decode(
            token,
            global_settings.JWT_SECRET_KEY,
            algorithms=[global_settings.JWT_ALGORITHM]
        )
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None:
            return True
            
        return datetime.utcnow() > datetime.fromtimestamp(exp)
        
    except JWTError:
        return True