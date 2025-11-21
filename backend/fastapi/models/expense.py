"""
Expense model for tracking business expenses.

This model represents business expense records including purchases,
services, and other operational costs with detailed tracking.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, String, Text, Date, DateTime, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from backend.fastapi.dependencies.database import Base

if TYPE_CHECKING:
    from backend.fastapi.models.user import User
    from backend.fastapi.models.branch import Branch


class Expense(Base):
    """
    Expense model for tracking business expenses and purchases.
    
    Tracks all business expenses including supplies, services, equipment,
    and operational costs with detailed information about quantities,
    units of measurement, and associated branch/worker.
    """
    
    __tablename__ = "expenses"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
        doc="Unique identifier for the expense record"
    )
    
    # Foreign keys
    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the user who incurred or reported the expense"
    )
    
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the branch where the expense was incurred"
    )
    
    # Expense information
    expense_date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date when the expense was incurred"
    )
    
    expense_description = Column(
        Text,
        nullable=False,
        doc="Brief description of the expense or purchase"
    )
    
    vendor_payee = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Vendor, store, or payee where expense was made or who received payment"
    )
    
    expense_category = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Category or type of expense (supplies, equipment, services, etc.)"
    )
    
    # Quantity and measurement
    quantity = Column(
        Numeric(precision=12, scale=3),
        nullable=True,
        default=Decimal("1.000"),
        doc="Number of units or quantity purchased"
    )
    
    unit_of_measure = Column(
        String(50),
        nullable=True,
        default="each",
        doc="Unit of measurement (pieces, kilograms, hours, etc.)"
    )
    
    unit_cost = Column(
        Numeric(precision=12, scale=2),
        nullable=True,
        default=Decimal("0.00"),
        doc="Cost per unit (calculated from total_amount / quantity)"
    )
    
    # Financial information
    total_amount = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Total expense amount including all units and applicable taxes"
    )
    
    tax_amount = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Tax amount included in total (if applicable)"
    )
    
    # Additional details
    receipt_number = Column(
        String(100),
        nullable=True,
        doc="Receipt or invoice number for tracking"
    )
    
    payment_method = Column(
        String(50),
        nullable=True,
        default="cash",
        doc="Method of payment (cash, card, transfer, etc.)"
    )
    
    is_reimbursable = Column(
        String(10),  # Using string instead of boolean for flexibility
        nullable=False,
        default="no",
        doc="Whether expense is reimbursable to employee (yes/no/pending)"
    )
    
    notes = Column(
        Text,
        nullable=True,
        doc="Additional notes or comments about the expense"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when the expense record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when the expense record was last updated"
    )
    
    # Relationships
    worker = relationship(
        "User",
        back_populates="expense_records",
        doc="User who incurred or reported this expense"
    )
    
    branch = relationship(
        "Branch",
        back_populates="expense_records",
        doc="Branch where this expense was incurred"
    )
    
    # Validation methods
    @validates('total_amount', 'tax_amount', 'quantity', 'unit_cost')
    def validate_amounts(self, key, value):
        """Validate that monetary amounts and quantities are non-negative."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('is_reimbursable')
    def validate_reimbursable(self, key, value):
        """Validate reimbursable status."""
        if value and value.lower() not in ['yes', 'no', 'pending']:
            raise ValueError("is_reimbursable must be 'yes', 'no', or 'pending'")
        return value.lower() if value else 'no'
    
    @validates('expense_category')
    def validate_category(self, key, value):
        """Validate and normalize expense category."""
        if not value or not value.strip():
            raise ValueError("expense_category cannot be empty")
        return value.strip().lower()
    
    def calculate_unit_cost(self):
        """
        Calculate unit cost based on total amount and quantity.
        Should be called before saving to ensure consistency.
        """
        if self.quantity and self.quantity > 0 and self.total_amount:
            self.unit_cost = self.total_amount / self.quantity
        else:
            self.unit_cost = self.total_amount or Decimal("0.00")
    
    @property
    def net_amount(self) -> Decimal:
        """Calculate net amount (total - tax)."""
        return (self.total_amount or Decimal("0.00")) - (self.tax_amount or Decimal("0.00"))
    
    @property
    def has_receipt(self) -> bool:
        """Check if expense has receipt number."""
        return bool(self.receipt_number and self.receipt_number.strip())
    
    @property
    def is_pending_reimbursement(self) -> bool:
        """Check if expense is pending reimbursement."""
        return self.is_reimbursable == 'pending'
    
    def __repr__(self):
        return (
            f"<Expense(id={self.id}, date={self.expense_date}, "
            f"amount=${self.total_amount}, category='{self.expense_category}', "
            f"vendor='{self.vendor_payee}')>"
        )