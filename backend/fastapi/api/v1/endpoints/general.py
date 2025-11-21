"""
General API endpoints for combined data operations.

This module provides endpoints that combine data from multiple modules
like payroll, sales, and expenses for comprehensive reporting.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from backend.fastapi.dependencies.database import get_sync_db
from backend.security.dependencies import get_current_admin, get_current_admin_or_user
from backend.fastapi.models.admin import Admin
from backend.fastapi.models.user import User
from backend.fastapi.crud import payroll as payroll_crud
from backend.fastapi.crud import sales as sales_crud
from backend.fastapi.crud import expense as expense_crud
from backend.fastapi.schemas.payroll import PayrollWithDetails
from backend.fastapi.schemas.sales import SalesWithDetails
from backend.fastapi.schemas.expense import ExpenseWithDetails

router = APIRouter()


class CombinedDataResponse(BaseModel):
    """Schema for combined payroll, sales, and expenses data."""
    
    start_date: date = Field(
        ...,
        description="Start date of the data range"
    )
    
    end_date: date = Field(
        ...,
        description="End date of the data range"
    )
    
    payroll_records: List[PayrollWithDetails] = Field(
        ...,
        description="Payroll records in the date range"
    )
    
    sales_records: List[SalesWithDetails] = Field(
        ...,
        description="Sales records in the date range"
    )
    
    expense_records: List[ExpenseWithDetails] = Field(
        ...,
        description="Expense records in the date range"
    )
    
    summary: Dict[str, Any] = Field(
        ...,
        description="Summary statistics for the period"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2025-11-01",
                "end_date": "2025-11-30",
                "payroll_records": [],
                "sales_records": [],
                "expense_records": [],
                "summary": {
                    "total_payroll": "15000.00",
                    "total_sales": "45000.00",
                    "total_expenses": "8000.00",
                    "payroll_count": 25,
                    "sales_count": 120,
                    "expense_count": 15,
                    "net_profit": "22000.00"
                }
            }
        }
    )


@router.get(
    "/combined-data",
    response_model=CombinedDataResponse,
    summary="Get Combined Business Data",
    description="Get payroll, sales, and expenses data for a specific date range with summary statistics."
)
async def get_combined_data(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin = Depends(get_current_admin),
    start_date: date = Query(..., description="Start date for data range (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for data range (YYYY-MM-DD)"),
    branch_id: Optional[str] = Query(None, description="Filter by specific branch ID"),
    worker_id: Optional[str] = Query(None, description="Filter by specific worker ID")
) -> CombinedDataResponse:
    """
    Get combined business data for a specific date range. **Admin access only.**
    
    - **Admin-only endpoint** for comprehensive business reporting
    - **No pagination** - returns all records in the specified date range
    - **All data types**: payroll, sales, and expense records with summary statistics
    
    **Parameters:**
    - **start_date**: Start date of the reporting period
    - **end_date**: End date of the reporting period  
    - **branch_id**: Filter by specific branch (optional)
    - **worker_id**: Filter by specific worker (optional)
    
    **Returns:**
    - Combined payroll, sales, and expense records with summary statistics
    
    **Errors:**
    - **400**: Invalid date range
    - **401**: Not authenticated
    - **403**: Not an admin user
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    # Parse worker_id if provided (admins can specify any worker_id)
    effective_worker_id = None
    if worker_id:
        try:
            from uuid import UUID
            effective_worker_id = UUID(worker_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid worker_id format"
            )
    
    # Parse branch_id if provided
    effective_branch_id = None
    if branch_id:
        try:
            from uuid import UUID
            effective_branch_id = UUID(branch_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid branch_id format"
            )
    
    try:
        # Get payroll records
        payroll_records = payroll_crud.get_payrolls(
            db=db,
            skip=0,
            limit=10000,  # Large limit to get all records
            worker_id=effective_worker_id,
            branch_id=effective_branch_id,
            start_date=start_date,
            end_date=end_date,
            order_by="date_desc"
        )
        
        # Convert payroll records to detailed format
        payroll_details = []
        for payroll in payroll_records:
            payroll_details.append(PayrollWithDetails(
                **payroll.__dict__,
                worker_username=payroll.worker.username if payroll.worker else "",
                branch_name=payroll.branch.name if payroll.branch else ""
            ))
        
        # Get sales records - both admins and users can see all sales (sales are business data)
        # Sales are NOT filtered by worker_id since they represent business operational data
        sales_data = sales_crud.get_sales_records(
            db=db,
            skip=0,
            limit=10000,  # Large limit to get all records
            worker_id=None,  # Don't filter by worker - all users can see all sales
            branch_id=effective_branch_id,
            start_date=start_date,
            end_date=end_date,
            order_by="date_desc"
        )
            
        # Convert Sales objects to SalesWithDetails
        sales_records = []
        for sales in sales_data:
            sales_dict = {
                "id": sales.id,
                "closure_date": sales.closure_date,
                "closure_number": sales.closure_number,
                "worker_id": sales.worker_id,
                "branch_id": sales.branch_id,
                "payments_nbr": sales.payments_nbr,
                "sales_total": sales.sales_total,
                "card_itpv": sales.card_itpv,
                "card_refund": sales.card_refund,
                "card_kiwi": sales.card_kiwi,
                "transfer_amt": sales.transfer_amt,
                "card_total": sales.card_total,
                "cash_amt": sales.cash_amt,
                "cash_refund": sales.cash_refund,
                "cash_total": sales.cash_total,
                "discrepancy": sales.discrepancy,
                "avg_sale": sales.avg_sale,
                "kiwi_fee_total": sales.kiwi_fee_total,
                "card_kiwi_minus_fee": sales.card_kiwi_minus_fee,
                "revenue_total": sales.revenue_total,
                "notes": sales.notes,
                "created_at": sales.created_at,
                "worker_username": sales.worker.username if sales.worker else "",
                "branch_name": sales.branch.name if sales.branch else ""
            }
            sales_records.append(SalesWithDetails(**sales_dict))
        
        # Get expense records
        expense_data = expense_crud.get_expenses(
            db=db,
            skip=0,
            limit=10000,  # Large limit to get all records
            worker_id=effective_worker_id,
            branch_id=effective_branch_id,
            start_date=start_date,
            end_date=end_date,
            order_by="date_desc"
        )
        
        # Convert Expense objects to ExpenseWithDetails
        expense_records = []
        for expense in expense_data:
            expense_dict = {
                "id": expense.id,
                "expense_date": expense.expense_date,
                "expense_description": expense.expense_description,
                "vendor_payee": expense.vendor_payee,
                "expense_category": expense.expense_category,
                "quantity": expense.quantity,
                "unit_of_measure": expense.unit_of_measure,
                "total_amount": expense.total_amount,
                "tax_amount": expense.tax_amount,
                "receipt_number": expense.receipt_number,
                "payment_method": expense.payment_method,
                "is_reimbursable": expense.is_reimbursable,
                "notes": expense.notes,
                "worker_id": expense.worker_id,
                "branch_id": expense.branch_id,
                "unit_cost": expense.unit_cost,
                "created_at": expense.created_at,
                "updated_at": expense.updated_at,
                "worker_username": expense.worker.username if expense.worker else "",
                "branch_name": expense.branch.name if expense.branch else "",
                "net_amount": expense.total_amount - (expense.tax_amount or Decimal("0")),
                "has_receipt": bool(expense.receipt_number and expense.receipt_number.strip()),
                "is_pending_reimbursement": expense.is_reimbursable == "pending"
            }
            expense_records.append(ExpenseWithDetails(**expense_dict))
        
        # Calculate summary statistics
        total_payroll = sum(record.amount for record in payroll_details)
        total_sales = sum(record.sales_total for record in sales_records)
        total_expenses = sum(record.total_amount for record in expense_records)
        
        # Calculate net profit (sales revenue - payroll - expenses)
        net_profit = total_sales - total_payroll - total_expenses
        
        summary = {
            "total_payroll": str(total_payroll),
            "total_sales": str(total_sales),
            "total_expenses": str(total_expenses),
            "payroll_count": len(payroll_details),
            "sales_count": len(sales_records),
            "expense_count": len(expense_records),
            "net_profit": str(net_profit),
            "date_range_days": (end_date - start_date).days + 1,
            "filters_applied": {
                "worker_id": str(effective_worker_id) if effective_worker_id else None,
                "branch_id": str(effective_branch_id) if effective_branch_id else None,
                "user_type": "admin",
                "date_range": f"{start_date} to {end_date}",
                "sales_worker_filter": "None (all sales visible)"
            }
        }
        
        return CombinedDataResponse(
            start_date=start_date,
            end_date=end_date,
            payroll_records=payroll_details,
            sales_records=sales_records,
            expense_records=expense_records,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve combined data: {str(e)}"
        )