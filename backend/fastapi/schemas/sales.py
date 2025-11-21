"""
Sales Pydantic schemas for request/response validation.

This module defines the data validation schemas for Sales-related
API operations using Pydantic models.
"""

from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, validator


class SalesBase(BaseModel):
    """Base Sales schema with common fields."""
    
    closure_date: date = Field(
        ...,
        description="Date the sales are being registered for"
    )
    
    closure_number: int = Field(
        ...,
        ge=1,
        description="Sequential closure number"
    )
    
    payments_nbr: int = Field(
        ...,
        ge=0,
        description="Number of individual payments processed"
    )
    
    sales_total: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        description="Total amount registered for the day"
    )
    
    # Card payment fields
    card_itpv: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Card amount according to ITPV system"
    )
    
    card_refund: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Amount refunded to cards"
    )
    
    card_kiwi: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Amount paid by card using Kiwi terminal"
    )
    
    transfer_amt: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Amount paid via bank transfer"
    )
    
    # Cash payment fields
    cash_amt: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Amount paid with cash"
    )
    
    cash_refund: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Cash returned to customers"
    )
    
    # Fee fields
    kiwi_fee_total: Decimal = Field(
        ...,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Total fees deducted from Kiwi card payments"
    )
    
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the closure"
    )


class SalesCreate(SalesBase):
    """Schema for creating a new sales record."""
    
    worker_id: UUID = Field(
        ...,
        description="ID of the worker who processed the sales"
    )
    
    branch_id: UUID = Field(
        ...,
        description="ID of the branch where sales occurred"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "closure_date": "2025-11-12",
                "closure_number": 1,
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "branch_id": "456e7890-e89b-12d3-a456-426614174000",
                "payments_nbr": 25,
                "sales_total": "1250.50",
                "card_itpv": "800.00",
                "card_refund": "25.00",
                "card_kiwi": "300.00",
                "transfer_amt": "50.00",
                "cash_amt": "500.00",
                "cash_refund": "24.50",
                "kiwi_fee_total": "12.50",
                "notes": "Regular daily closure"
            }
        }
    )


class SalesUpdate(BaseModel):
    """Schema for updating an existing sales record."""
    
    closure_date: Optional[date] = Field(
        None,
        description="Updated closure date"
    )
    
    closure_number: Optional[int] = Field(
        None,
        ge=1,
        description="Updated closure number"
    )
    
    worker_id: Optional[UUID] = Field(
        None,
        description="Updated worker ID"
    )
    
    branch_id: Optional[UUID] = Field(
        None,
        description="Updated branch ID"
    )
    
    payments_nbr: Optional[int] = Field(
        None,
        ge=0,
        description="Updated number of payments"
    )
    
    sales_total: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        description="Updated sales total"
    )
    
    card_itpv: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated card ITPV amount"
    )
    
    card_refund: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated card refund amount"
    )
    
    card_kiwi: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated Kiwi card amount"
    )
    
    transfer_amt: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated transfer amount"
    )
    
    cash_amt: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated cash amount"
    )
    
    cash_refund: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated cash refund amount"
    )
    
    kiwi_fee_total: Optional[Decimal] = Field(
        None,
        decimal_places=2,
        max_digits=14,
        ge=0,
        description="Updated Kiwi fee total"
    )
    
    notes: Optional[str] = Field(
        None,
        description="Updated notes"
    )


class SalesRead(SalesBase):
    """Schema for reading sales information."""
    
    id: UUID = Field(
        ...,
        description="Unique identifier of the sales record"
    )
    
    worker_id: UUID = Field(
        ...,
        description="ID of the worker"
    )
    
    branch_id: UUID = Field(
        ...,
        description="ID of the branch"
    )
    
    # Calculated fields
    card_total: Decimal = Field(
        ...,
        description="Calculated card total (card_itpv - card_refund + transfer_amt)"
    )
    
    cash_total: Decimal = Field(
        ...,
        description="Calculated cash total (cash_amt - cash_refund)"
    )
    
    discrepancy: Decimal = Field(
        ...,
        description="Difference between payment totals and sales total"
    )
    
    avg_sale: Decimal = Field(
        ...,
        description="Average sale amount"
    )
    
    card_kiwi_minus_fee: Decimal = Field(
        ...,
        description="Kiwi card amount minus fees"
    )
    
    revenue_total: Decimal = Field(
        ...,
        description="Final revenue (sales_total - kiwi_fee_total)"
    )
    
    created_at: datetime = Field(
        ...,
        description="When the sales record was created"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "789e0123-e89b-12d3-a456-426614174000",
                "closure_date": "2025-11-12",
                "closure_number": 1,
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "branch_id": "456e7890-e89b-12d3-a456-426614174000",
                "payments_nbr": 25,
                "sales_total": "1250.50",
                "card_itpv": "800.00",
                "card_refund": "25.00",
                "card_kiwi": "300.00",
                "transfer_amt": "50.00",
                "card_total": "825.00",
                "cash_amt": "500.00",
                "cash_refund": "24.50",
                "cash_total": "475.50",
                "discrepancy": "50.00",
                "avg_sale": "50.02",
                "kiwi_fee_total": "12.50",
                "card_kiwi_minus_fee": "287.50",
                "revenue_total": "1238.00",
                "notes": "Regular daily closure",
                "created_at": "2025-11-12T18:30:00Z"
            }
        }
    )


class SalesWithDetails(SalesRead):
    """Schema for sales information with worker and branch details."""
    
    worker_username: str = Field(
        ...,
        description="Username of the worker"
    )
    
    branch_name: str = Field(
        ...,
        description="Name of the branch"
    )
    
    model_config = ConfigDict(
        from_attributes=True
    )


class SalesSummary(BaseModel):
    """Schema for sales summary statistics."""
    
    total_sales: Decimal = Field(
        ...,
        description="Total sales amount"
    )
    
    total_payments: int = Field(
        ...,
        description="Total number of payments"
    )
    
    total_discrepancy: Decimal = Field(
        ...,
        description="Total discrepancy amount"
    )
    
    average_sale: Decimal = Field(
        ...,
        description="Average sale amount across all records"
    )
    
    total_revenue: Decimal = Field(
        ...,
        description="Total revenue after fees"
    )
    
    total_fees: Decimal = Field(
        ...,
        description="Total fees deducted"
    )
    
    card_percentage: Decimal = Field(
        ...,
        description="Percentage of sales paid by card"
    )
    
    cash_percentage: Decimal = Field(
        ...,
        description="Percentage of sales paid by cash"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_sales": "15000.00",
                "total_payments": 300,
                "total_discrepancy": "25.50",
                "average_sale": "50.00",
                "total_revenue": "14850.00",
                "total_fees": "150.00",
                "card_percentage": "65.50",
                "cash_percentage": "34.50"
            }
        }
    )


class SalesListResponse(BaseModel):
    """Schema for paginated sales listing."""
    
    sales: List[SalesWithDetails] = Field(
        ...,
        description="List of sales records"
    )
    
    total_count: int = Field(
        ...,
        description="Total number of sales records"
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


class SalesPeriodReport(BaseModel):
    """Schema for sales period reporting."""
    
    start_date: date = Field(
        ...,
        description="Start date of the reporting period"
    )
    
    end_date: date = Field(
        ...,
        description="End date of the reporting period"
    )
    
    summary: SalesSummary = Field(
        ...,
        description="Summary statistics for the period"
    )
    
    by_branch: dict = Field(
        ...,
        description="Breakdown by branch"
    )
    
    by_worker: dict = Field(
        ...,
        description="Breakdown by worker"
    )
    
    daily_totals: List[dict] = Field(
        ...,
        description="Daily sales totals"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2025-11-01",
                "end_date": "2025-11-30",
                "summary": {
                    "total_sales": "45000.00",
                    "total_payments": 900,
                    "total_discrepancy": "125.50",
                    "average_sale": "50.00",
                    "total_revenue": "44550.00",
                    "total_fees": "450.00",
                    "card_percentage": "65.50",
                    "cash_percentage": "34.50"
                },
                "by_branch": {
                    "Downtown Store": "25000.00",
                    "Mall Location": "20000.00"
                },
                "by_worker": {
                    "john.doe": "15000.00",
                    "jane.smith": "18000.00",
                    "bob.wilson": "12000.00"
                },
                "daily_totals": [
                    {"date": "2025-11-01", "total": "1500.00"},
                    {"date": "2025-11-02", "total": "1650.00"}
                ]
            }
        }
    )


class DiscrepancyReport(BaseModel):
    """Schema for discrepancy analysis report."""
    
    total_discrepancies: int = Field(
        ...,
        description="Number of sales records with discrepancies"
    )
    
    total_discrepancy_amount: Decimal = Field(
        ...,
        description="Total amount of discrepancies"
    )
    
    largest_discrepancy: Decimal = Field(
        ...,
        description="Largest single discrepancy"
    )
    
    average_discrepancy: Decimal = Field(
        ...,
        description="Average discrepancy amount"
    )
    
    discrepancy_records: List[SalesWithDetails] = Field(
        ...,
        description="Sales records with discrepancies"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_discrepancies": 5,
                "total_discrepancy_amount": "125.50",
                "largest_discrepancy": "50.00",
                "average_discrepancy": "25.10",
                "discrepancy_records": []
            }
        }
    )