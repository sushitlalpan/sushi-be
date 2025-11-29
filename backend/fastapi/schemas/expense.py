"""
Expense Pydantic schemas for request/response validation.

This module provides comprehensive validation schemas for expense management
including creation, updates, detailed views, and reporting.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict


class ReviewState(str, Enum):
    """Enum for review states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExpenseBase(BaseModel):
    """Base expense model with common fields."""
    
    expense_date: date = Field(
        ...,
        description="Date when the expense was incurred",
        example="2024-11-18"
    )
    
    expense_description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Brief description of the expense or purchase",
        example="Office supplies - printer paper and pens"
    )
    
    vendor_payee: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Vendor, store, or payee where expense was made",
        example="Office Depot"
    )
    
    expense_category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Category or type of expense",
        example="office supplies"
    )
    
    quantity: Optional[Decimal] = Field(
        default=Decimal("1.000"),
        ge=0,
        decimal_places=3,
        description="Number of units or quantity purchased",
        example=5.000
    )
    
    unit_of_measure: Optional[str] = Field(
        default="each",
        max_length=50,
        description="Unit of measurement",
        example="pieces"
    )
    
    total_amount: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Total expense amount including taxes",
        example=45.99
    )
    
    tax_amount: Optional[Decimal] = Field(
        default=Decimal("0.00"),
        ge=0,
        decimal_places=2,
        description="Tax amount included in total",
        example=3.68
    )
    
    receipt_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Receipt or invoice number",
        example="R-2024-001234"
    )
    
    payment_method: Optional[str] = Field(
        default="cash",
        max_length=50,
        description="Method of payment",
        example="card"
    )
    
    is_reimbursable: str = Field(
        default="no",
        pattern="^(yes|no|pending)$",
        description="Whether expense is reimbursable",
        example="yes"
    )
    
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional notes or comments",
        example="Emergency purchase for restaurant operations"
    )
    
    review_state: Optional[str] = Field(
        default="pending",
        pattern="^(pending|approved|rejected)$",
        description="Review status of the expense",
        example="pending"
    )
    
    review_observations: Optional[str] = Field(
        default=None,
        description="Review observations or comments from supervisor",
        example="Approved - necessary purchase for operations"
    )
    
    @validator('expense_category', 'vendor_payee')
    def normalize_text_fields(cls, v):
        """Normalize text fields by stripping whitespace."""
        return v.strip() if v else v
    
    @validator('is_reimbursable')
    def validate_reimbursable_status(cls, v):
        """Validate and normalize reimbursable status."""
        if v:
            return v.lower()
        return 'no'
    
    @validator('review_state')
    def validate_review_state(cls, v):
        """Validate and normalize review state."""
        if v:
            return v.lower()
        return 'pending'


class ExpenseCreate(ExpenseBase):
    """Schema for creating new expense records."""
    
    worker_id: UUID = Field(
        ...,
        description="ID of the user who incurred the expense",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    branch_id: UUID = Field(
        ...,
        description="ID of the branch where expense was incurred",
        example="987fcdeb-51a2-43c1-9f8e-123456789abc"
    )


class ExpenseUpdate(BaseModel):
    """Schema for updating existing expense records."""
    
    expense_date: Optional[date] = Field(
        default=None,
        description="Date when the expense was incurred"
    )
    
    expense_description: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description="Brief description of the expense"
    )
    
    vendor_payee: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Vendor or payee"
    )
    
    expense_category: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Expense category"
    )
    
    quantity: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=3,
        description="Quantity purchased"
    )
    
    unit_of_measure: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Unit of measurement"
    )
    
    total_amount: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Total expense amount"
    )
    
    tax_amount: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Tax amount"
    )
    
    receipt_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Receipt number"
    )
    
    payment_method: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Payment method"
    )
    
    is_reimbursable: Optional[str] = Field(
        default=None,
        pattern="^(yes|no|pending)$",
        description="Reimbursable status"
    )
    
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional notes"
    )
    
    review_state: Optional[str] = Field(
        default=None,
        pattern="^(pending|approved|rejected)$",
        description="Review status update"
    )
    
    review_observations: Optional[str] = Field(
        default=None,
        description="Review observations update"
    )
    
    @validator('expense_category', 'vendor_payee', 'expense_description')
    def normalize_text_fields(cls, v):
        """Normalize text fields by stripping whitespace."""
        return v.strip() if v else v
    
    @validator('is_reimbursable')
    def validate_reimbursable_status(cls, v):
        """Validate and normalize reimbursable status."""
        if v:
            return v.lower()
        return v
    
    @validator('review_state')
    def validate_review_state(cls, v):
        """Validate and normalize review state."""
        if v:
            return v.lower()
        return v


class ExpenseRead(ExpenseBase):
    """Schema for reading expense records."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(
        ...,
        description="Unique identifier for the expense record"
    )
    
    worker_id: UUID = Field(
        ...,
        description="ID of the user who incurred the expense"
    )
    
    branch_id: UUID = Field(
        ...,
        description="ID of the branch where expense was incurred"
    )
    
    unit_cost: Optional[Decimal] = Field(
        default=None,
        decimal_places=2,
        description="Calculated cost per unit"
    )
    
    created_at: datetime = Field(
        ...,
        description="Timestamp when expense was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Timestamp when expense was last updated"
    )


class ExpenseWithDetails(ExpenseRead):
    """Schema for expense records with worker and branch details."""
    
    worker_username: str = Field(
        ...,
        description="Username of the worker who incurred the expense"
    )
    
    branch_name: str = Field(
        ...,
        description="Name of the branch where expense was incurred"
    )
    
    net_amount: Decimal = Field(
        ...,
        description="Net amount (total - tax)"
    )
    
    has_receipt: bool = Field(
        ...,
        description="Whether expense has receipt number"
    )
    
    is_pending_reimbursement: bool = Field(
        ...,
        description="Whether expense is pending reimbursement"
    )


class ExpenseSummary(BaseModel):
    """Schema for expense summary information."""
    
    total_expenses: Decimal = Field(
        ...,
        description="Total expense amount"
    )
    
    total_count: int = Field(
        ...,
        description="Total number of expense records"
    )
    
    total_tax: Decimal = Field(
        ...,
        description="Total tax amount"
    )
    
    total_reimbursable: Decimal = Field(
        ...,
        description="Total reimbursable amount"
    )
    
    pending_reimbursement: Decimal = Field(
        ...,
        description="Amount pending reimbursement"
    )
    
    average_expense: Decimal = Field(
        ...,
        description="Average expense amount"
    )
    
    by_category: Dict[str, Decimal] = Field(
        ...,
        description="Breakdown by expense category"
    )
    
    by_payment_method: Dict[str, Decimal] = Field(
        ...,
        description="Breakdown by payment method"
    )


class ExpenseListResponse(BaseModel):
    """Schema for paginated expense list responses."""
    
    expenses: List[ExpenseWithDetails] = Field(
        ...,
        description="List of expense records"
    )
    
    total_count: int = Field(
        ...,
        description="Total number of matching records"
    )
    
    skip: int = Field(
        ...,
        description="Number of records skipped"
    )
    
    limit: int = Field(
        ...,
        description="Maximum number of records returned"
    )
    
    has_next: bool = Field(
        ...,
        description="Whether there are more records available"
    )


class ExpensePeriodReport(BaseModel):
    """Schema for expense period reports."""
    
    start_date: date = Field(
        ...,
        description="Report start date"
    )
    
    end_date: date = Field(
        ...,
        description="Report end date"
    )
    
    summary: ExpenseSummary = Field(
        ...,
        description="Overall expense summary for the period"
    )
    
    by_branch: Dict[str, str] = Field(
        ...,
        description="Expense breakdown by branch"
    )
    
    by_worker: Dict[str, str] = Field(
        ...,
        description="Expense breakdown by worker"
    )
    
    by_category: Dict[str, str] = Field(
        ...,
        description="Expense breakdown by category"
    )
    
    daily_totals: List[Dict[str, Any]] = Field(
        ...,
        description="Daily expense totals"
    )


class ExpenseReviewUpdate(BaseModel):
    """Schema for updating expense review status."""
    
    review_state: ReviewState = Field(
        ...,
        description="New review state"
    )
    
    review_observations: Optional[str] = Field(
        default=None,
        description="Review observations or comments"
    )
    
    @validator('review_state')
    def validate_review_state(cls, v):
        """Validate and normalize review state."""
        return v.lower() if v else v


class ExpenseReviewSummary(BaseModel):
    """Schema for expense review summary statistics."""
    
    pending_count: int = Field(
        ...,
        description="Number of expenses pending review"
    )
    
    approved_count: int = Field(
        ...,
        description="Number of approved expenses"
    )
    
    rejected_count: int = Field(
        ...,
        description="Number of rejected expenses"
    )
    
    pending_amount: Decimal = Field(
        ...,
        description="Total amount of expenses pending review"
    )
    
    approved_amount: Decimal = Field(
        ...,
        description="Total amount of approved expenses"
    )
    
    rejected_amount: Decimal = Field(
        ...,
        description="Total amount of rejected expenses"
    )


class ReimbursementReport(BaseModel):
    """Schema for reimbursement analysis reports."""
    
    total_reimbursable: Decimal = Field(
        ...,
        description="Total amount that is reimbursable"
    )
    
    pending_reimbursement: Decimal = Field(
        ...,
        description="Amount pending reimbursement"
    )
    
    reimbursed_amount: Decimal = Field(
        ...,
        description="Amount already reimbursed (marked as 'no')"
    )
    
    pending_count: int = Field(
        ...,
        description="Number of expenses pending reimbursement"
    )
    
    by_worker: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Reimbursement breakdown by worker"
    )
    
    expense_records: List[ExpenseWithDetails] = Field(
        ...,
        description="List of expenses requiring attention"
    )