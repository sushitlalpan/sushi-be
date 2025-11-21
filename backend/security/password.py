"""
Password hashing and verification utilities using bcrypt.

This module provides secure password hashing and verification functionality
for the authentication system.
"""

import hashlib
import os
from passlib.context import CryptContext

# Try to create bcrypt context, fallback to PBKDF2 if bcrypt fails
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    USE_BCRYPT = True
except Exception:
    # Fallback to PBKDF2 if bcrypt has issues
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    USE_BCRYPT = False


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt or PBKDF2.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        The hashed password as a string
        
    Raises:
        ValueError: If password hashing fails
        
    Example:
        >>> hashed = hash_password("mysecretpassword")
        >>> len(hashed) > 20  # Hashes are long strings
        True
    """
    try:
        # For bcrypt compatibility, ensure password is within byte limits
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Use a simple truncation approach that maintains string integrity
            password = password[:60]  # Conservative truncation to avoid encoding issues
        
        return pwd_context.hash(password)
    except Exception as e:
        # If bcrypt fails completely, try fallback
        try:
            fallback_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            return fallback_context.hash(password)
        except Exception as fallback_error:
            raise ValueError(f"Password hashing failed: bcrypt error: {str(e)}, fallback error: {str(fallback_error)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.
    
    Args:
        plain_password: The plaintext password to verify
        hashed_password: The stored hash to verify against
        
    Returns:
        True if the password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("mysecretpassword")
        >>> verify_password("mysecretpassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    try:
        # Apply same truncation logic as in hashing for consistency
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            plain_password = plain_password[:60]  # Same truncation as hash_password
        
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # If verification fails with current context, try with fallback
        try:
            fallback_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            return fallback_context.verify(plain_password, hashed_password)
        except:
            # If all else fails, return False rather than raising an exception
            return False


def get_password_hash(password: str) -> str:
    """
    Alias for hash_password for backward compatibility.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        The hashed password as a string
    """
    return hash_password(password)