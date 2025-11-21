"""
Sales model for cash register closure and daily sales tracking.

This model represents daily sales reconciliation records that track
all payment methods, refunds, discrepancies, and revenue calculations
for each worker at each branch.
"""

from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from backend.fastapi.dependencies.database import Base


class Sales(Base):
    """
    Sales model for daily cash register closure tracking.
    
    This model tracks daily sales reconciliation for each worker at each branch,
    including detailed breakdown of payment methods, refunds, fees, and
    automatic calculation of discrepancies and totals.
    
    Attributes:
        id: Unique identifier for the sales record
        worker_id: Foreign key to User model (the cashier/worker)
        closure_date: Date the sales are being registered for
        closure_number: Sequential closure number (separate from ID)
        branch_id: Foreign key to Branch model (location)
        payments_nbr: Number of individual payments processed
        
        Sales amounts:
        sales_total: Total amount registered for the day
        
        Card payment tracking:
        card_itpv: Card amount according to ITPV system
        card_refund: Amount refunded to cards
        card_kiwi: Amount paid by card using Kiwi terminal
        transfer_amt: Amount paid via bank transfer
        card_total: Calculated total (card_itpv - card_refund + transfer_amt)
        
        Cash payment tracking:
        cash_amt: Amount paid with cash
        cash_refund: Cash returned to customers
        cash_total: Calculated total (cash_amt - cash_refund)
        
        Analysis fields:
        discrepancy: Difference between (card_total + cash_total) and sales_total
        avg_sale: Average sale amount (sales_total / payments_nbr)
        
        Fee tracking:
        kiwi_fee_total: Total fees deducted from Kiwi card payments
        card_kiwi_minus_fee: Kiwi card amount minus fees
        revenue_total: Final revenue (sales_total - kiwi_fee_total)
        
        Audit fields:
        notes: Additional notes about the closure
        created_at: When the record was created
    """
    __tablename__ = "sales"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        doc="Unique identifier for the sales record"
    )
    
    # Foreign keys
    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the user/worker who processed the sales"
    )
    
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the branch where sales occurred"
    )
    
    # Closure information
    closure_date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date the sales are being registered for"
    )
    
    closure_number = Column(
        Integer,
        nullable=False,
        index=True,
        doc="Sequential closure number (unrelated to ID)"
    )
    
    payments_nbr = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of individual payments processed"
    )
    
    # Sales total
    sales_total = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Total amount registered for the day"
    )
    
    # Card payment fields
    card_itpv = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Card amount according to ITPV system"
    )
    
    card_refund = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Amount refunded to cards"
    )
    
    card_kiwi = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Amount paid by card using Kiwi terminal"
    )
    
    transfer_amt = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Amount paid via bank transfer"
    )
    
    card_total = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Calculated total: card_itpv + card_kiwi + transfer_amt - card_refund"
    )
    
    # Cash payment fields
    cash_amt = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Amount paid with cash"
    )
    
    cash_refund = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Cash returned to customers"
    )
    
    cash_total = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Calculated total: cash_amt - cash_refund"
    )
    
    # Analysis fields
    discrepancy = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Difference between (card_total + cash_total) and sales_total"
    )
    
    avg_sale = Column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Average sale amount (sales_total / payments_nbr)"
    )
    
    # Fee and revenue fields
    kiwi_fee_total = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Total fees deducted from Kiwi card payments"
    )
    
    card_kiwi_minus_fee = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Kiwi card amount minus fees"
    )
    
    revenue_total = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Final revenue: sales_total - kiwi_fee_total"
    )
    
    # Additional information
    notes = Column(
        Text,
        nullable=True,
        doc="Additional notes about the closure"
    )
    
    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="When the sales record was created"
    )
    
    # Relationships
    worker = relationship(
        "User",
        back_populates="sales_records",
        doc="The worker who processed these sales"
    )
    
    branch = relationship(
        "Branch",
        back_populates="sales_records",
        doc="The branch where these sales occurred"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Sales(id='{self.id}', "
            f"worker_id='{self.worker_id}', "
            f"closure_date='{self.closure_date}', "
            f"closure_number={self.closure_number}, "
            f"sales_total={self.sales_total})>"
        )
    
    def __str__(self) -> str:
        worker_name = self.worker.username if self.worker else f"Worker {self.worker_id}"
        return f"Sales Closure #{self.closure_number} - {worker_name} ({self.closure_date})"
    
    @validates('card_itpv', 'card_refund', 'card_kiwi', 'transfer_amt')
    def validate_card_amounts(self, key, value):
        """Validate that card amounts are non-negative."""
        if value is not None and value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value
    
    @validates('cash_amt', 'cash_refund')
    def validate_cash_amounts(self, key, value):
        """Validate that cash amounts are non-negative."""
        if value is not None and value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value
    
    @validates('payments_nbr')
    def validate_payments_number(self, key, value):
        """Validate that payments number is non-negative."""
        if value is not None and value < 0:
            raise ValueError("payments_nbr must be non-negative")
        return value
    
    def calculate_totals(self):
        """
        Calculate derived fields based on input values.
        This should be called before saving to ensure consistency.
        """
        # Calculate card total
        self.card_total = self.card_itpv + self.card_kiwi + self.transfer_amt - self.card_refund
        
        # Calculate cash total
        self.cash_total = self.cash_amt - self.cash_refund
        
        # Calculate discrepancy
        payment_total = self.card_total + self.cash_total
        self.discrepancy = payment_total - self.sales_total
        
        # Calculate average sale
        if self.payments_nbr > 0:
            self.avg_sale = self.sales_total / self.payments_nbr
        else:
            self.avg_sale = Decimal("0.00")
        
        # Calculate Kiwi amount minus fees
        self.card_kiwi_minus_fee = self.card_kiwi - self.kiwi_fee_total
        
        # Calculate revenue total
        self.revenue_total = self.sales_total - self.kiwi_fee_total
    
    @property
    def has_discrepancy(self) -> bool:
        """Check if there's a discrepancy in the closure."""
        return abs(self.discrepancy) > Decimal("0.01")  # Allow for small rounding differences
    
    @property
    def payment_methods_summary(self) -> dict:
        """Get a summary of payment methods used."""
        return {
            "card_total": float(self.card_total),
            "cash_total": float(self.cash_total),
            "transfer_amount": float(self.transfer_amt),
            "total_payments": float(self.card_total + self.cash_total)
        }
    
    @property
    def financial_summary(self) -> dict:
        """Get a financial summary of the closure."""
        return {
            "gross_sales": float(self.sales_total),
            "total_fees": float(self.kiwi_fee_total),
            "net_revenue": float(self.revenue_total),
            "discrepancy": float(self.discrepancy),
            "avg_transaction": float(self.avg_sale)
        }