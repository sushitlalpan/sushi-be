"""
User model for restaurant staff members.

This module defines the SQLAlchemy model for non-admin staff users
who will use the restaurant management system.
"""

from datetime import datetime, time
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.fastapi.dependencies.database import Base


class User(Base):
    """
    User model for restaurant staff members.
    
    This model represents non-admin staff users such as waiters, cashiers,
    kitchen staff, and managers who need access to the restaurant system
    but don't require full administrative privileges.
    
    Attributes:
        id: Unique identifier (UUID)
        username: Unique username for login
        password_hash: Bcrypt hashed password
        branch: Restaurant branch/location identifier
        phone_number: Staff member's phone number
        fingerprint_id: Biometric fingerprint identifier (optional)
        shift_start_time: When staff member clocked in for current shift
        shift_end_time: When staff member clocked out from current shift
        is_active: Whether the user account is active
        created_at: Account creation timestamp
        updated_at: Last account update timestamp
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        doc="Unique user identifier"
    )
    
    # Authentication fields
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username for login (3-50 characters)"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password"
    )
    
    # Staff information
    branch_id = Column(
        "branch",  # Map to actual database column name 'branch'
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Foreign key to the branch where this user works"
    )
    
    phone_number = Column(
        String(20),
        nullable=True,
        doc="Staff member's phone number"
    )
    
    fingerprint_id = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        doc="Biometric fingerprint identifier for clock-in system"
    )
    
    # Scheduled shift times (not actual clock-in/out)
    shift_start_time = Column(
        Time,
        nullable=True,
        doc="Scheduled shift start time (e.g., 09:00:00)"
    )
    
    shift_end_time = Column(
        Time,
        nullable=True,
        doc="Scheduled shift end time (e.g., 17:00:00)"
    )
    
    # Account status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the user account is active"
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Account creation timestamp"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Last account update timestamp"
    )
    
    # Relationships
    branch = relationship("Branch", back_populates="users", doc="Branch where this user works")
    time_entries = relationship("TimeEntry", back_populates="user", cascade="all, delete-orphan")
    payroll_records = relationship("Payroll", back_populates="worker", cascade="all, delete-orphan")
    sales_records = relationship("Sales", back_populates="worker", cascade="all, delete-orphan")
    expense_records = relationship("Expense", back_populates="worker", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation of User."""
        branch_name = self.branch.name if self.branch else f"Branch ID: {self.branch_id}"
        return f"<User(id={self.id}, username='{self.username}', branch='{branch_name}', active={self.is_active})>"
    
    def get_scheduled_shift_duration(self) -> int:
        """
        Get scheduled shift duration in minutes.
        
        Returns:
            Duration in minutes, or 0 if no shift times set
        """
        if not self.shift_start_time or not self.shift_end_time:
            return 0
        
        # Convert time objects to datetime for calculation
        start_dt = datetime.combine(datetime.today(), self.shift_start_time)
        end_dt = datetime.combine(datetime.today(), self.shift_end_time)
        
        # Handle overnight shifts
        if end_dt < start_dt:
            end_dt = end_dt.replace(day=end_dt.day + 1)
        
        duration = end_dt - start_dt
        return int(duration.total_seconds() / 60)