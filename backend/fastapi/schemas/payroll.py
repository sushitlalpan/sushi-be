"""
Payroll Pydantic schemas for request/response validation.

This module defines the data validation schemas for Payroll-related
API operations using Pydantic models.
"""

from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, validator


class ReviewState(str, Enum):
    """Enum for review states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PayrollBase(BaseModel):
    """Base Payroll schema with common fields."""
    
    date: datetime = Field(
        ...,
        description="Date of the payroll entry/payment"
    )
    
    days_worked: int = Field(
        ...,
        ge=0,
        le=31,
        description="Number of days worked in the period"
    )
    
    amount: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=12,
        description="Payment amount (can be negative for deductions)"
    )
    
    payroll_type: str = Field(
        ...,
        max_length=50,
        description="Type of payroll entry (regular, overtime, bonus, etc.)"
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional notes about the payment"
    )
    
    review_state: Optional[str] = Field(
        default="pending",
        pattern="^(pending|approved|rejected)$",
        description="Review status of the payroll entry"
    )
    
    review_observations: Optional[str] = Field(
        None,
        max_length=1000,
        description="Review observations or comments from supervisor"
    )
    
    @validator('review_state')
    def validate_review_state(cls, v):
        """Validate review state."""
        if v and v.lower() not in ['pending', 'approved', 'rejected']:
            raise ValueError("review_state must be 'pending', 'approved', or 'rejected'")
        return v.lower() if v else 'pending'


class PayrollCreate(PayrollBase):
    """Schema for creating a new payroll record."""
    
    worker_id: UUID = Field(
        ...,
        description="ID of the worker/user this payroll record belongs to"
    )
    
    branch_id: UUID = Field(
        ...,
        description="ID of the branch where the work was performed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-11-12T00:00:00Z",
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "branch_id": "456e7890-e89b-12d3-a456-426614174000",
                "days_worked": 5,
                "amount": "1500.00",
                "payroll_type": "regular",
                "notes": "Regular weekly payment"
            }
        }
    )


class PayrollUpdate(BaseModel):
    """Schema for updating an existing payroll record."""
    
    date: Optional[datetime] = Field(
        None,
        description="Updated date of the payroll entry/payment"
    )
    
    worker_id: Optional[UUID] = Field(
        None,
        description="Updated worker ID"
    )
    
    branch_id: Optional[UUID] = Field(
        None,
        description="Updated branch ID"
    )
    
    days_worked: Optional[int] = Field(
        None,
        ge=0,
        le=31,
        description="Updated number of days worked"
    )
    
    amount: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=12,
        description="Updated payment amount"
    )
    
    payroll_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Updated payroll type"
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Updated notes"
    )
    
    review_state: Optional[str] = Field(
        None,
        description="Updated review status"
    )
    
    review_observations: Optional[str] = Field(
        None,
        max_length=1000,
        description="Updated review observations"
    )
    
    @validator('review_state')
    def validate_review_state(cls, v):
        """Validate review state."""
        if v and v.lower() not in ['pending', 'approved', 'rejected']:
            raise ValueError("review_state must be 'pending', 'approved', or 'rejected'")
        return v.lower() if v else v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "1600.00",
                "notes": "Updated amount with overtime"
            }
        }
    )


class PayrollRead(PayrollBase):
    """Schema for reading payroll information."""
    
    id: UUID = Field(
        ...,
        description="Unique identifier of the payroll record"
    )
    
    worker_id: UUID = Field(
        ...,
        description="ID of the worker/user"
    )
    
    branch_id: UUID = Field(
        ...,
        description="ID of the branch"
    )
    
    created_at: datetime = Field(
        ...,
        description="When the payroll record was created"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "789e0123-e89b-12d3-a456-426614174000",
                "date": "2025-11-12T00:00:00Z",
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "branch_id": "456e7890-e89b-12d3-a456-426614174000",
                "days_worked": 5,
                "amount": "1500.00",
                "payroll_type": "regular",
                "notes": "Regular weekly payment",
                "created_at": "2025-11-12T10:30:00Z"
            }
        }
    )


class PayrollWithDetails(PayrollRead):
    """Schema for payroll information with worker and branch details."""
    
    worker_username: str = Field(
        ...,
        description="Username of the worker"
    )
    
    branch_name: str = Field(
        ...,
        description="Name of the branch"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "789e0123-e89b-12d3-a456-426614174000",
                "date": "2025-11-12T00:00:00Z",
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "branch_id": "456e7890-e89b-12d3-a456-426614174000",
                "days_worked": 5,
                "amount": "1500.00",
                "payroll_type": "regular",
                "notes": "Regular weekly payment",
                "created_at": "2025-11-12T10:30:00Z",
                "worker_username": "john.doe",
                "branch_name": "Downtown Store"
            }
        }
    )


class PayrollSummary(BaseModel):
    """Schema for payroll summary statistics."""
    
    worker_id: UUID = Field(
        ...,
        description="ID of the worker"
    )
    
    worker_username: str = Field(
        ...,
        description="Username of the worker"
    )
    
    total_amount: Decimal = Field(
        ...,
        description="Total amount paid to this worker"
    )
    
    total_days: int = Field(
        ...,
        description="Total days worked by this worker"
    )
    
    record_count: int = Field(
        ...,
        description="Number of payroll records for this worker"
    )
    
    last_payment_date: Optional[datetime] = Field(
        None,
        description="Date of the last payment"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "worker_username": "john.doe",
                "total_amount": "6000.00",
                "total_days": 20,
                "record_count": 4,
                "last_payment_date": "2025-11-12T00:00:00Z"
            }
        }
    )


class PayrollListResponse(BaseModel):
    """Schema for paginated payroll listing."""
    
    payroll_records: List[PayrollWithDetails] = Field(
        ...,
        description="List of payroll records"
    )
    
    total: int = Field(
        ...,
        description="Total number of payroll records"
    )
    
    skip: int = Field(
        ...,
        description="Number of records skipped"
    )
    
    limit: int = Field(
        ...,
        description="Maximum number of records returned"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "payroll_records": [
                    {
                        "id": "789e0123-e89b-12d3-a456-426614174000",
                        "date": "2025-11-12T00:00:00Z",
                        "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                        "branch_id": "456e7890-e89b-12d3-a456-426614174000",
                        "days_worked": 5,
                        "amount": "1500.00",
                        "payroll_type": "regular",
                        "notes": "Regular weekly payment",
                        "created_at": "2025-11-12T10:30:00Z",
                        "worker_username": "john.doe",
                        "branch_name": "Downtown Store"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 10
            }
        }
    )


class PayrollReviewUpdate(BaseModel):
    """Schema for updating payroll review status."""
    
    review_state: ReviewState = Field(
        ...,
        description="New review state"
    )
    
    review_observations: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Review observations or comments"
    )
    
    @validator('review_state')
    def validate_review_state(cls, v):
        """Validate review state."""
        if v and v.lower() not in ['pending', 'approved', 'rejected']:
            raise ValueError("review_state must be 'pending', 'approved', or 'rejected'")
        return v.lower() if v else v


class PayrollReviewSummary(BaseModel):
    """Schema for payroll review summary statistics."""
    
    pending_count: int = Field(
        ...,
        description="Number of payroll records pending review"
    )
    
    approved_count: int = Field(
        ...,
        description="Number of approved payroll records"
    )
    
    rejected_count: int = Field(
        ...,
        description="Number of rejected payroll records"
    )
    
    pending_amount: Decimal = Field(
        ...,
        description="Total amount of payroll pending review"
    )
    
    approved_amount: Decimal = Field(
        ...,
        description="Total amount of approved payroll"
    )
    
    rejected_amount: Decimal = Field(
        ...,
        description="Total amount of rejected payroll"
    )


class PayrollPeriodReport(BaseModel):
    """Schema for payroll period reporting."""
    
    start_date: date = Field(
        ...,
        description="Start date of the reporting period"
    )
    
    end_date: date = Field(
        ...,
        description="End date of the reporting period"
    )
    
    total_amount: Decimal = Field(
        ...,
        description="Total amount paid in the period"
    )
    
    total_records: int = Field(
        ...,
        description="Total number of payroll records in the period"
    )
    
    by_type: dict = Field(
        ...,
        description="Breakdown by payroll type"
    )
    
    by_branch: dict = Field(
        ...,
        description="Breakdown by branch"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2025-11-01",
                "end_date": "2025-11-30",
                "total_amount": "15000.00",
                "total_records": 10,
                "by_type": {
                    "regular": "12000.00",
                    "overtime": "2000.00",
                    "bonus": "1000.00"
                },
                "by_branch": {
                    "Downtown Store": "8000.00",
                    "Mall Location": "7000.00"
                }
            }
        }
    )