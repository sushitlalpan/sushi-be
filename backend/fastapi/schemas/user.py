"""
Pydantic schemas for User model validation and serialization.

This module defines the data validation schemas for user-related
API operations including creation, updates, and responses.
"""

from datetime import datetime, time
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    """Base User schema with common fields."""
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Unique username (3-50 chars, alphanumeric + underscore/hyphen)",
        examples=["john_doe", "waiter-01", "chef123"]
    )
    
    branch_id: UUID = Field(
        ...,
        description="UUID of the branch where this user works",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    
    phone_number: Optional[str] = Field(
        None,
        max_length=20,
        pattern=r"^[+]?[0-9\s\-\(\)]+$",
        description="Phone number (optional)",
        examples=["+1-555-0123", "555-123-4567", "(555) 123-4567"]
    )
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty string to None for optional phone number field."""
        if v == '' or (isinstance(v, str) and not v.strip()):
            return None
        return v
    
    fingerprint_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Biometric fingerprint ID for clock-in system (optional)",
        examples=["FP_001_ABC123", "bio_id_12345"]
    )
    
    shift_start_time: Optional[time] = Field(
        None,
        description="Scheduled shift start time (optional)",
        examples=["09:00:00", "14:30:00"]
    )
    
    shift_end_time: Optional[time] = Field(
        None,
        description="Scheduled shift end time (optional)",
        examples=["17:00:00", "22:30:00"]
    )


class UserCreate(UserBase):
    """Schema for creating a new user account."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (minimum 8 characters)",
        examples=["SecureStaffPass123!"]
    )
    
    is_active: bool = Field(
        default=True,
        description="Whether the user account should be active"
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="New username (optional)"
    )
    
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="New password (optional)"
    )
    
    branch_id: Optional[UUID] = Field(
        None,
        description="New branch assignment UUID (optional)"
    )
    
    phone_number: Optional[str] = Field(
        None,
        max_length=20,
        pattern=r"^[+]?[0-9\s\-\(\)]+$",
        description="New phone number (optional)"
    )
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty string to None for optional phone number field."""
        if v == '' or (isinstance(v, str) and not v.strip()):
            return None
        return v
    
    fingerprint_id: Optional[str] = Field(
        None,
        max_length=255,
        description="New fingerprint ID (optional)"
    )
    
    shift_start_time: Optional[time] = Field(
        None,
        description="New scheduled shift start time (optional)"
    )
    
    shift_end_time: Optional[time] = Field(
        None,
        description="New scheduled shift end time (optional)"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="New active status (optional)"
    )


class UserRead(BaseModel):
    """Schema for reading user information (excludes sensitive data)."""
    
    id: UUID = Field(..., description="User unique identifier")
    username: str = Field(..., description="Username")
    branch_id: UUID = Field(..., description="Branch ID where user works")
    branch_name: str = Field(..., description="Branch name where user works")
    phone_number: Optional[str] = Field(None, description="Phone number")
    fingerprint_id: Optional[str] = Field(None, description="Fingerprint ID")
    shift_start_time: Optional[time] = Field(None, description="Scheduled shift start time")
    shift_end_time: Optional[time] = Field(None, description="Scheduled shift end time")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login requests."""
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username for login",
        examples=["john_doe", "waiter-01"]
    )
    
    password: str = Field(
        ...,
        min_length=1,
        description="User password",
        examples=["SecureStaffPass123!"]
    )


class UserToken(BaseModel):
    """Base JWT token schema for users."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserTokenResponse(UserToken):
    """Extended token response with expiration and user info."""
    
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserRead = Field(..., description="User account information")





# Response schemas for bulk operations
class UserCreateResponse(BaseModel):
    """Schema for user creation response."""
    
    success: bool = Field(default=True, description="Whether the operation was successful")
    message: str = Field(default="User created successfully", description="Response message")
    user: UserRead = Field(..., description="Created user information")


class UnifiedProfileRead(BaseModel):
    """Schema for unified user/admin profile information."""
    
    id: UUID = Field(..., description="User unique identifier")
    username: str = Field(..., description="Username")
    is_admin: bool = Field(..., description="Whether this user is an admin")
    is_active: bool = Field(..., description="Whether the account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # User-specific fields (optional for admins)
    branch_id: Optional[UUID] = Field(None, description="Branch ID (users only)")
    branch_name: Optional[str] = Field(None, description="Branch name (users only)")
    phone_number: Optional[str] = Field(None, description="Phone number (users only)")
    fingerprint_id: Optional[str] = Field(None, description="Fingerprint ID (users only)")
    shift_start_time: Optional[time] = Field(None, description="Scheduled shift start time (users only)")
    shift_end_time: Optional[time] = Field(None, description="Scheduled shift end time (users only)")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for listing multiple users."""
    
    users: list[UserRead] = Field(..., description="List of user accounts")
    total: int = Field(..., description="Total number of user accounts")
    branch: Optional[str] = Field(None, description="Branch filter applied")