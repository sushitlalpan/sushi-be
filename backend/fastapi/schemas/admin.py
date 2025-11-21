"""
Admin schemas for request/response validation.

This module defines Pydantic models for admin-related API operations,
including creation, reading, and updating admin accounts.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class AdminBase(BaseModel):
    """Base admin schema with common fields."""
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Admin username (3-50 characters)",
        examples=["admin", "manager", "supervisor"]
    )


class AdminCreate(AdminBase):
    """Schema for creating a new admin account."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Admin password (minimum 8 characters)",
        examples=["SecurePassword123!"]
    )
    
    is_active: bool = Field(
        default=True,
        description="Whether the admin account should be active"
    )


class AdminRead(AdminBase):
    """Schema for reading admin account information."""
    
    id: UUID = Field(..., description="Unique identifier for the admin")
    is_active: bool = Field(..., description="Whether the admin account is active")
    created_at: datetime = Field(..., description="When the admin account was created")
    updated_at: datetime = Field(..., description="When the admin account was last updated")

    model_config = ConfigDict(from_attributes=True)


class AdminUpdate(BaseModel):
    """Schema for updating admin account information."""
    
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="New username (optional)"
    )
    
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="New password (optional)"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="Update active status (optional)"
    )


class AdminInDB(AdminRead):
    """Schema for admin data as stored in database (internal use)."""
    
    password_hash: str = Field(..., description="Bcrypt hashed password")


# Login-related schemas
class AdminLogin(BaseModel):
    """Schema for admin login request."""
    
    username: str = Field(
        ...,
        description="Admin username",
        examples=["admin"]
    )
    
    password: str = Field(
        ...,
        description="Admin password",
        examples=["SecurePassword123!"]
    )


class AdminLoginResponse(BaseModel):
    """Schema for admin login response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    admin: AdminRead = Field(..., description="Admin account information")


# JWT Token schemas
class Token(BaseModel):
    """Base JWT token schema."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenResponse(Token):
    """Extended token response with expiration and user info."""
    
    expires_in: int = Field(..., description="Token expiration time in seconds")
    admin: AdminRead = Field(..., description="Admin account information")


# Response schemas
class AdminCreateResponse(BaseModel):
    """Schema for admin creation response."""
    
    success: bool = Field(default=True, description="Whether the operation was successful")
    message: str = Field(default="Admin created successfully", description="Response message")
    admin: AdminRead = Field(..., description="Created admin information")


class AdminListResponse(BaseModel):
    """Schema for listing multiple admins."""
    
    admins: list[AdminRead] = Field(..., description="List of admin accounts")
    total: int = Field(..., description="Total number of admin accounts")