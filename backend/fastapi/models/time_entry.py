"""
TimeEntry model for tracking staff clock-in/out records.

This module defines the SQLAlchemy model for recording actual
clock-in and clock-out events for audit and payroll purposes.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum

from backend.fastapi.dependencies.database import Base


class TimeEntryType(str, Enum):
    """Enum for time entry types."""
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"


class TimeEntry(Base):
    """
    Time entry model for tracking staff clock-in/out records.
    
    This model records actual clock-in and clock-out events for each
    staff member, providing an audit trail for attendance and payroll.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to User model
        entry_type: Type of entry (clock_in or clock_out)
        timestamp: When the clock-in/out occurred
        method: How the entry was recorded (manual, fingerprint, etc.)
        notes: Optional notes about the entry
        created_at: Record creation timestamp
        
    Relationships:
        user: The staff user this entry belongs to
    """
    
    __tablename__ = "time_entries"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        doc="Unique time entry identifier"
    )
    
    # Foreign key to User
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the staff user"
    )
    
    # Entry details
    entry_type = Column(
        SQLEnum(TimeEntryType),
        nullable=False,
        doc="Type of time entry (clock_in or clock_out)"
    )
    
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="When the clock-in/out occurred"
    )
    
    method = Column(
        String(50),
        nullable=True,
        default="manual",
        doc="How the entry was recorded (manual, fingerprint, card, etc.)"
    )
    
    notes = Column(
        String(500),
        nullable=True,
        doc="Optional notes about the time entry"
    )
    
    # Audit timestamp
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Record creation timestamp"
    )
    
    # Relationship
    user = relationship("User", back_populates="time_entries")
    
    def __repr__(self) -> str:
        """String representation of TimeEntry."""
        return f"<TimeEntry(id={self.id}, user_id={self.user_id}, type={self.entry_type}, time={self.timestamp})>"
    
    @property
    def is_clock_in(self) -> bool:
        """Check if this is a clock-in entry."""
        return self.entry_type == TimeEntryType.CLOCK_IN
    
    @property
    def is_clock_out(self) -> bool:
        """Check if this is a clock-out entry."""
        return self.entry_type == TimeEntryType.CLOCK_OUT