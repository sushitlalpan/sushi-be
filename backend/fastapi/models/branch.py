"""
Branch model for organizing users by location/branch.

This model represents different branches/locations where users work.
Each user is assigned to a branch, and payroll records are associated
with specific branches.
"""

from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.fastapi.dependencies.database import Base


class Branch(Base):
    """
    Branch model representing different work locations.
    
    A branch is a location where staff members work. Each user
    is assigned to a specific branch, and payroll calculations
    can be done per branch.
    
    Attributes:
        id: Unique identifier for the branch
        name: Human-readable name of the branch/location
        users: List of users assigned to this branch
        payroll_records: List of payroll records for this branch
    """
    __tablename__ = "branches"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        doc="Unique identifier for the branch"
    )
    
    # Branch information
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Name of the branch/location (e.g., 'Downtown Store', 'Mall Location')"
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Branch creation timestamp"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Last branch update timestamp"
    )
    
    deleted_at = Column(
        DateTime,
        nullable=True,
        default=None,
        index=True,
        doc="Soft delete timestamp (NULL if not deleted)"
    )
    
    # Relationships
    users = relationship(
        "User",
        back_populates="branch",
        doc="List of users assigned to this branch"
    )
    
    payroll_records = relationship(
        "Payroll",
        back_populates="branch",
        doc="List of payroll records for this branch"
    )
    
    sales_records = relationship(
        "Sales",
        back_populates="branch",
        doc="List of sales records for this branch"
    )
    
    expense_records = relationship(
        "Expense",
        back_populates="branch",
        doc="List of expense records for this branch"
    )
    
    def __repr__(self) -> str:
        return f"<Branch(id='{self.id}', name='{self.name}')>"
    
    def __str__(self) -> str:
        return self.name