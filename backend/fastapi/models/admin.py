"""
Admin model for the authentication system.

This module defines the Admin table structure and provides the SQLAlchemy model
for admin user management.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from backend.fastapi.dependencies.database import Base


class Admin(Base):
    """
    Admin user model for authentication and authorization.
    
    This model represents admin users who have elevated privileges
    in the system. Passwords are stored as bcrypt hashes.
    """
    
    __tablename__ = "admins"

    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the admin"
    )
    
    # Authentication fields
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Unique username for admin login"
    )
    
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    # Status field
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Whether the admin account is active"
    )
    
    # Timestamps
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        comment="When the admin account was created"
    )
    
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False,
        comment="When the admin account was last updated"
    )

    def __repr__(self) -> str:
        """String representation of the Admin model."""
        return f"<Admin(id={self.id}, username='{self.username}', is_active={self.is_active})>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Admin: {self.username}"