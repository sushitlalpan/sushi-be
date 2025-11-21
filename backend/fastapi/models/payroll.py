"""
Payroll model for tracking employee payments.

This model stores payroll information including worker details,
branch assignment, work period, and payment calculations.
"""

from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.fastapi.dependencies.database import Base


class Payroll(Base):
    """
    Payroll model for tracking employee payments.
    
    This model tracks all payroll entries including regular wages,
    overtime, bonuses, deductions, and advances. Each entry is
    associated with a specific user and branch.
    
    Attributes:
        id: Unique identifier for the payroll record
        date: Date of the payroll entry/payment
        worker_id: Foreign key to User model (the employee)
        branch_id: Foreign key to Branch model (work location)
        days_worked: Number of days worked in the period
        amount: Payment amount (can be negative for deductions)
        payroll_type: Type of payroll entry (regular, overtime, etc.)
        notes: Additional notes about the payment
        created_at: Timestamp when record was created
        worker: Relationship to User model
        branch: Relationship to Branch model
    """
    __tablename__ = "payroll"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        doc="Unique identifier for the payroll record"
    )
    
    # Payroll information
    date = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Date of the payroll entry/payment"
    )
    
    # Foreign keys
    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the user/employee"
    )
    
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the branch where work was performed"
    )
    
    # Work and payment details
    days_worked = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of days worked in the period"
    )
    
    amount = Column(
        Numeric(precision=10, scale=2),
        nullable=False,
        doc="Payment amount (can be negative for deductions)"
    )
    
    payroll_type = Column(
        String(50),
        nullable=False,
        default="regular",
        index=True,
        doc="Type of payroll entry (regular, overtime, bonus, etc.)"
    )
    
    notes = Column(
        String(500),
        nullable=True,
        doc="Additional notes about the payment"
    )
    
    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Timestamp when the payroll record was created"
    )
    
    # Relationships
    worker = relationship(
        "User",
        back_populates="payroll_records",
        doc="The employee this payroll record belongs to"
    )
    
    branch = relationship(
        "Branch",
        back_populates="payroll_records",
        doc="The branch where this work was performed"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Payroll(id='{self.id}', "
            f"worker_id='{self.worker_id}', "
            f"amount={self.amount}, "
            f"type={self.payroll_type}, "
            f"date='{self.date.date()}')>"
        )
    
    def __str__(self) -> str:
        return f"Payroll for {self.worker.username if self.worker else self.worker_id} - ${self.amount}"
    
    @property
    def is_deduction(self) -> bool:
        """Check if this payroll entry is a deduction (negative amount)."""
        return self.amount < 0
    
    @property
    def is_bonus_or_commission(self) -> bool:
        """Check if this is a bonus or commission payment."""
        return self.payroll_type in ["bonus", "commission"]