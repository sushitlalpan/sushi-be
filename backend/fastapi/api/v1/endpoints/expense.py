"""
Expense API endpoints.

This module provides REST API endpoints for expense management including
business purchases, operational costs, and reimbursement tracking.
"""

from uuid import UUID
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.security.dependencies import get_current_admin, get_current_admin_or_user, get_current_super_admin, RequireSuperAdmin
from backend.fastapi.models.admin import Admin
from backend.fastapi.models.user import User
from backend.fastapi.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseRead,
    ExpenseWithDetails,
    ExpenseSummary,
    ExpenseListResponse,
    ExpensePeriodReport,
    ReimbursementReport,
    ExpenseReviewUpdate,
    ExpenseReviewSummary,
    BulkLockRequest,
    BulkLockResponse
)
from backend.fastapi.crud import expense as expense_crud

router = APIRouter()


@router.post(
    "/",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Expense Record",
    description="Create a new expense record with automatic unit cost calculation."
)
async def create_expense_record(
    *,
    db: Session = Depends(get_sync_db),
    expense_in: ExpenseCreate,
    current_user: Admin | User = Depends(get_current_admin_or_user)
) -> ExpenseRead:
    """
    Create a new expense record.
    
    - **Admins and users** can create expenses for any worker
    - Validates worker and branch existence
    - Automatically calculates unit cost based on total amount and quantity
    
    Returns the created expense record with calculated fields.
    """
    try:
        expense_record = expense_crud.create_expense(db=db, expense_data=expense_in)
        return expense_record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create expense record: {str(e)}"
        )


@router.delete(
    "/{expense_id}",
    summary="Delete Expense Record",
    description="Delete an expense record by ID. Users can delete their own expenses, admins can delete any."
)
async def delete_expense_record(
    *,
    db: Session = Depends(get_sync_db),
    expense_id: UUID,
    current_user: Admin | User = Depends(get_current_admin_or_user)
):
    """
    Delete an expense record.
    
    - **Admins** can delete any expense record
    - **Users** can only delete their own expense records
    - Returns 404 if expense record doesn't exist
    """
    # Check if expense exists and user has permission
    expense_record = expense_crud.get_expense(db=db, expense_id=expense_id)
    if not expense_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense record with ID {expense_id} not found"
        )
    
    # Check permissions
    if isinstance(current_user, User) and expense_record.worker_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own expense records"
        )
    
    success = expense_crud.delete_expense(db=db, expense_id=expense_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense record"
        )
    
    return {"message": "Expense deleted successfully", "expense_id": str(expense_id)}
    
    return {"message": "Expense deleted successfully", "expense_id": str(expense_id)}


@router.get(
    "/",
    response_model=ExpenseListResponse,
    summary="List Expense Records",
    description="Get paginated list of expense records with optional filtering."
)
async def list_expense_records(
    *,
    db: Session = Depends(get_sync_db),
    user_info: tuple = Depends(get_current_admin_or_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    branch_id: Optional[UUID] = Query(None, description="Filter by branch ID"),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    order_by: str = Query(
        "date_desc",
        pattern="^(date_desc|date_asc|amount_desc|amount_asc|category|vendor)$",
        description="Sort order: date_desc, date_asc, amount_desc, amount_asc, category, vendor"
    )
) -> ExpenseListResponse:
    """
    Get paginated list of expense records.
    
    - **Admins** see all expense records
    - **Users** see only their own expense records
    - Supports pagination with skip/limit
    - Supports multiple sorting options
    - Supports filtering by branch, start date, and end date
    
    Returns paginated list with metadata.
    """
    # Unpack user info
    current_user, role = user_info
    
    # Filter by worker if user is not admin
    worker_id = None
    if isinstance(current_user, User):
        worker_id = current_user.id
    
    # Exclude locked records for non-super-admins
    exclude_locked = not (isinstance(current_user, Admin) and current_user.is_super_admin)
    
    # Get expense records
    expense_records = expense_crud.get_expenses(
        db=db,
        skip=skip,
        limit=limit,
        worker_id=worker_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
        order_by=order_by,
        exclude_locked=exclude_locked
    )
    
    # Convert Expense objects to ExpenseWithDetails by adding worker_username and branch_name
    expenses_with_details = []
    for expense in expense_records:
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
            "review_state": expense.review_state,
            "review_observations": expense.review_observations,
            "worker_id": expense.worker_id,
            "branch_id": expense.branch_id,
            "unit_cost": expense.unit_cost,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
            "is_locked": expense.is_locked,
            "locked_at": expense.locked_at,
            "worker_username": expense.worker.username if expense.worker else "",
            "branch_name": expense.branch.name if expense.branch else "",
            "net_amount": expense.total_amount - (expense.tax_amount or Decimal("0")),
            "has_receipt": bool(expense.receipt_number and expense.receipt_number.strip()),
            "is_pending_reimbursement": expense.is_reimbursable == "pending"
        }
        expenses_with_details.append(ExpenseWithDetails(**expense_dict))
    
    # Get total count for pagination
    total_count = expense_crud.get_expenses_count(
        db=db,
        worker_id=worker_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
        exclude_locked=exclude_locked
    )
    
    return ExpenseListResponse(
        expenses=expenses_with_details,
        total_count=total_count,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total_count
    )


@router.get(
    "/search",
    response_model=ExpenseListResponse,
    summary="Search Expense Records",
    description="Search expense records with advanced filtering options."
)
async def search_expense_records(
    *,
    db: Session = Depends(get_sync_db),
    user_info: tuple = Depends(get_current_admin_or_user),
    worker: Optional[UUID] = Query(None, description="Filter by worker ID"),
    branch: Optional[UUID] = Query(None, description="Filter by branch ID"),
    start_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter until this date (YYYY-MM-DD)"),
    expense_category: Optional[str] = Query(None, description="Filter by expense category"),
    vendor_payee: Optional[str] = Query(None, description="Filter by vendor/payee (partial match)"),
    is_reimbursable: Optional[str] = Query(
        None,
        pattern="^(yes|no|pending)$",
        description="Filter by reimbursable status"
    ),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    has_receipt: Optional[bool] = Query(None, description="Filter by receipt presence"),
    min_amount: Optional[Decimal] = Query(None, ge=0, description="Minimum expense amount"),
    max_amount: Optional[Decimal] = Query(None, ge=0, description="Maximum expense amount"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    order_by: str = Query(
        "date_desc",
        pattern="^(date_desc|date_asc|amount_desc|amount_asc|category|vendor)$",
        description="Sort order"
    )
) -> ExpenseListResponse:
    """
    Search expense records with advanced filtering.
    
    - **Admins** can filter by any worker
    - **Users** can only see their own records (worker filter ignored)
    - Supports filtering by multiple criteria
    - Supports pagination and sorting
    
    Available filters:
    - worker: Filter by specific worker ID
    - branch: Filter by specific branch ID
    - start_date: Records from this date onwards
    - end_date: Records until this date
    - expense_category: Filter by expense category (partial match)
    - vendor_payee: Filter by vendor/payee (partial match)
    - is_reimbursable: Filter by reimbursement status (yes/no/pending)
    - payment_method: Filter by payment method
    - has_receipt: Filter by receipt presence
    - min_amount: Minimum expense amount
    - max_amount: Maximum expense amount
    """
    # Unpack user info
    current_user, role = user_info
    
    # Apply user restrictions
    worker_id = worker
    if isinstance(current_user, User):
        worker_id = current_user.id  # Users can only see their own records
    
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    # Validate amount range
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_amount must be less than or equal to max_amount"
        )
    
    # Exclude locked records for non-super-admins
    exclude_locked = not (isinstance(current_user, Admin) and current_user.is_super_admin)
    
    # Get filtered expense records
    expense_records = expense_crud.get_expenses(
        db=db,
        skip=skip,
        limit=limit,
        worker_id=worker_id,
        branch_id=branch,
        start_date=start_date,
        end_date=end_date,
        expense_category=expense_category,
        vendor_payee=vendor_payee,
        is_reimbursable=is_reimbursable,
        payment_method=payment_method,
        has_receipt=has_receipt,
        min_amount=min_amount,
        max_amount=max_amount,
        order_by=order_by,
        exclude_locked=exclude_locked
    )
    
    # Convert Expense objects to ExpenseWithDetails by adding worker_username and branch_name
    expenses_with_details = []
    for expense in expense_records:
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
            "review_state": expense.review_state,
            "review_observations": expense.review_observations,
            "worker_id": expense.worker_id,
            "branch_id": expense.branch_id,
            "unit_cost": expense.unit_cost,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
            "is_locked": expense.is_locked,
            "locked_at": expense.locked_at,
            "worker_username": expense.worker.username if expense.worker else "",
            "branch_name": expense.branch.name if expense.branch else "",
            "net_amount": expense.total_amount - (expense.tax_amount or Decimal("0")),
            "has_receipt": bool(expense.receipt_number and expense.receipt_number.strip()),
            "is_pending_reimbursement": expense.is_reimbursable == "pending"
        }
        expenses_with_details.append(ExpenseWithDetails(**expense_dict))
    
    # Get total count with same filters
    total_count = expense_crud.get_expenses_count(
        db=db,
        worker_id=worker_id,
        branch_id=branch,
        start_date=start_date,
        end_date=end_date,
        expense_category=expense_category,
        vendor_payee=vendor_payee,
        is_reimbursable=is_reimbursable,
        payment_method=payment_method,
        has_receipt=has_receipt,
        min_amount=min_amount,
        max_amount=max_amount,
        exclude_locked=exclude_locked
    )
    
    return ExpenseListResponse(
        expenses=expenses_with_details,
        total_count=total_count,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total_count
    )


@router.get(
    "/export/excel",
    summary="Export Expense Records to Excel",
    description="Export expense records to Excel file with optional filtering by date range and branch (admin-only)."
)
async def export_expenses_to_excel(
    *,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = Depends(get_current_admin),
    branch_id: Optional[UUID] = Query(None, description="Filter by branch ID"),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    order_by: str = Query("date_desc", pattern="^(date_desc|date_asc|amount_desc|amount_asc|category|vendor)$")
):
    """
    Export expense records to Excel file (admin-only endpoint).
    
    - **Admins only** can export expense records
    - Supports filtering by branch, start date, and end date
    - Super admins see all records including locked ones
    - Regular admins only see unlocked records
    
    Returns an Excel file for download.
    """
    # Exclude locked records for non-super-admins
    exclude_locked = not current_admin.is_super_admin
    
    try:
        # Get all expense records (no pagination for export)
        expense_records = expense_crud.get_expenses(
            db=db,
            skip=0,
            limit=10000,  # Large limit for export
            worker_id=None,
            branch_id=branch_id,
            start_date=start_date,
            end_date=end_date,
            order_by=order_by,
            exclude_locked=exclude_locked
        )
        
        if not expense_records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No expense records found for the specified criteria"
            )
        
        # Convert to list of dictionaries for DataFrame
        data = []
        for expense in expense_records:
            data.append({
                "Fecha": expense.expense_date.strftime("%Y-%m-%d") if expense.expense_date else "",
                "Colaborador": expense.worker.username if expense.worker else "",
                "Sucursal": expense.branch.name if expense.branch else "",
                "Categoría": expense.expense_category or "",
                "Proveedor/Beneficiario": expense.vendor_payee or "",
                "Descripción": expense.expense_description or "",
                "Cantidad": expense.quantity or "",
                "UDM": expense.unit_of_measure or "",
                "Monto": float(expense.total_amount),
                "IVA": float(expense.tax_amount) if expense.tax_amount else 0,
                "Método de Pago": expense.payment_method or "",
                "Reembolsable": expense.is_reimbursable or "",
                "Tiene Recibo": "Sí" if expense.receipt_number else "No",
                "Notas": expense.notes or "",
                "Bloqueado": "Sí" if expense.is_locked else "No",
                "Fecha de Bloqueo": expense.locked_at.strftime("%Y-%m-%d %H:%M:%S") if expense.locked_at else ""
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Egresos')
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Egresos']
            
            # Format header
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#ED7D31',
                'font_color': 'white',
                'border': 1
            })
            
            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"egresos_export_{timestamp}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Excel export: {str(e)}"
        )


@router.get(
    "/{expense_id}",
    response_model=ExpenseWithDetails,
    summary="Get Expense Record",
    description="Get a specific expense record with worker and branch details."
)
async def get_expense_record(
    *,
    db: Session = Depends(get_sync_db),
    expense_id: UUID,
    current_user: Admin | User = Depends(get_current_admin_or_user)
) -> ExpenseWithDetails:
    """
    Get a specific expense record with details.
    
    - **Admins** can view any expense record
    - **Users** can only view their own expense records
    - Returns detailed information including worker and branch names
    """
    expense_record = expense_crud.get_expense(db=db, expense_id=expense_id)
    if not expense_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense record with ID {expense_id} not found"
        )
    
    # Check access permissions
    if isinstance(current_user, User) and expense_record.worker_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own expense records"
        )
    
    # Get detailed record
    detailed_record = expense_crud.get_expense_with_details(db=db, expense_id=expense_id)
    if not detailed_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense record details not found for ID {expense_id}"
        )
    
    return ExpenseWithDetails(**detailed_record)


@router.put(
    "/{expense_id}",
    response_model=ExpenseRead,
    summary="Update Expense Record",
    description="Update an expense record. Users can update their own expenses, admins can update any."
)
async def update_expense_record(
    *,
    db: Session = Depends(get_sync_db),
    expense_id: UUID,
    expense_update: ExpenseUpdate,
    current_user: Admin | User = Depends(get_current_admin_or_user)
) -> ExpenseRead:
    """
    Update an expense record.
    
    - **Admins** can update any expense record
    - **Users** can only update their own expense records
    - Validates worker and branch existence if being updated
    - Automatically recalculates unit cost if amount or quantity changed
    
    Returns the updated expense record.
    """
    # Check if expense exists and user has permission
    expense_record = expense_crud.get_expense(db=db, expense_id=expense_id)
    if not expense_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense record with ID {expense_id} not found"
        )
    
    # Check permissions
    if isinstance(current_user, User) and expense_record.worker_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own expense records"
        )
    
    try:
        updated_expense = expense_crud.update_expense(
            db=db,
            expense_id=expense_id,
            expense_update=expense_update
        )
        
        if not updated_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense record with ID {expense_id} not found"
            )
        
        return updated_expense
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update expense record: {str(e)}"
        )


@router.get(
    "/reports/period",
    response_model=ExpensePeriodReport,
    summary="Get Expense Period Report",
    description="Generate comprehensive expense report for a specific period."
)
async def get_expense_period_report(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin = Depends(get_current_admin),
    start_date: date = Query(..., description="Report start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Report end date (YYYY-MM-DD)"),
    branch_id: Optional[UUID] = Query(None, description="Filter by specific branch")
) -> ExpensePeriodReport:
    """
    Generate comprehensive expense report for a period.
    
    - **Only admins** can access reports
    - Provides detailed breakdown by branch, worker, category, and daily totals
    - Includes summary statistics and reimbursement analysis
    
    Returns comprehensive period analysis.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        report_data = expense_crud.get_expenses_period_report(
            db=db,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_id
        )
        
        return ExpensePeriodReport(**report_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate period report: {str(e)}"
        )


@router.get(
    "/reports/reimbursements",
    response_model=ReimbursementReport,
    summary="Get Reimbursement Report",
    description="Generate report of expenses requiring reimbursement analysis."
)
async def get_reimbursement_report(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin = Depends(get_current_admin),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    branch_id: Optional[UUID] = Query(None, description="Filter by specific branch"),
    status_filter: Optional[str] = Query(
        None,
        pattern="^(yes|pending)$",
        description="Filter by reimbursement status (yes or pending)"
    )
) -> ReimbursementReport:
    """
    Generate reimbursement analysis report.
    
    - **Only admins** can access reimbursement reports
    - Shows expenses requiring reimbursement by worker and status
    - Provides statistics and pending reimbursement records
    - Helps manage employee expense reimbursements
    
    Returns comprehensive reimbursement analysis.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        report_data = expense_crud.get_reimbursement_report(
            db=db,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_id,
            status_filter=status_filter
        )
        
        # Convert Expense objects to ExpenseWithDetails in expense_records
        expenses_with_details = []
        for expense in report_data["expense_records"]:
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
                "review_state": expense.review_state,
                "review_observations": expense.review_observations,
                "worker_id": expense.worker_id,
                "branch_id": expense.branch_id,
                "unit_cost": expense.unit_cost,
                "created_at": expense.created_at,
                "updated_at": expense.updated_at,                "is_locked": expense.is_locked,
                "locked_at": expense.locked_at,                "worker_username": expense.worker.username if expense.worker else "",
                "branch_name": expense.branch.name if expense.branch else "",
                "net_amount": expense.total_amount - (expense.tax_amount or Decimal("0")),
                "has_receipt": bool(expense.receipt_number and expense.receipt_number.strip()),
                "is_pending_reimbursement": expense.is_reimbursable == "pending"
            }
            expenses_with_details.append(ExpenseWithDetails(**expense_dict))
        
        # Replace expense_records with converted objects
        report_data["expense_records"] = expenses_with_details
        
        return ReimbursementReport(**report_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reimbursement report: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=ExpenseSummary,
    summary="Get Expense Summary",
    description="Get expense summary for current user or specified period."
)
async def get_expense_summary(
    *,
    db: Session = Depends(get_sync_db),
    user_info: tuple = Depends(get_current_admin_or_user),
    start_date: Optional[date] = Query(None, description="Summary start date"),
    end_date: Optional[date] = Query(None, description="Summary end date"),
    branch_id: Optional[UUID] = Query(None, description="Filter by branch (admins only)")
) -> ExpenseSummary:
    """
    Get expense summary information.
    
    - **Admins** can get summary for any worker/branch
    - **Users** get summary for their own expenses only
    - Provides aggregated totals and statistics
    
    Returns expense summary with key metrics.
    """
    # Unpack user info
    current_user, role = user_info
    
    # Apply user restrictions
    worker_id = None
    if isinstance(current_user, User):
        worker_id = current_user.id
        branch_id = None  # Users cannot filter by branch
    
    # Exclude locked records for non-super-admins
    exclude_locked = not (isinstance(current_user, Admin) and current_user.is_super_admin)
    
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        # Use period summary if dates provided, otherwise get basic summary
        if start_date and end_date:
            summary_data = expense_crud.get_expenses_period_summary(
                db=db,
                start_date=start_date,
                end_date=end_date,
                branch_id=branch_id,
                worker_id=worker_id
            )
        else:
            # Get basic summary (recent records)
            recent_records = expense_crud.get_expenses(
                db=db,
                skip=0,
                limit=50,  # Last 50 records for summary
                worker_id=worker_id,
                branch_id=branch_id,
                order_by="date_desc",
                exclude_locked=exclude_locked
            )
            
            if recent_records:
                total_expenses = sum(record.total_amount for record in recent_records)
                total_tax = sum(record.tax_amount for record in recent_records)
                total_reimbursable = sum(
                    record.total_amount for record in recent_records 
                    if record.is_reimbursable in ['yes', 'pending']
                )
                pending_reimbursement = sum(
                    record.total_amount for record in recent_records 
                    if record.is_reimbursable == 'pending'
                )
                avg_expense = total_expenses / len(recent_records) if recent_records else Decimal("0")
                
                # Group by category
                by_category = {}
                for record in recent_records:
                    category = record.expense_category
                    by_category[category] = by_category.get(category, Decimal("0")) + record.total_amount
                
                # Group by payment method
                by_payment_method = {}
                for record in recent_records:
                    method = record.payment_method or 'unknown'
                    by_payment_method[method] = by_payment_method.get(method, Decimal("0")) + record.total_amount
                
                summary_data = {
                    "total_expenses": total_expenses,
                    "total_count": len(recent_records),
                    "total_tax": total_tax,
                    "total_reimbursable": total_reimbursable,
                    "pending_reimbursement": pending_reimbursement,
                    "average_expense": avg_expense,
                    "by_category": by_category,
                    "by_payment_method": by_payment_method
                }
            else:
                summary_data = {
                    "total_expenses": Decimal("0"),
                    "total_count": 0,
                    "total_tax": Decimal("0"),
                    "total_reimbursable": Decimal("0"),
                    "pending_reimbursement": Decimal("0"),
                    "average_expense": Decimal("0"),
                    "by_category": {},
                    "by_payment_method": {}
                }
        
        return ExpenseSummary(**summary_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate expense summary: {str(e)}"
        )


@router.patch(
    "/{expense_id}/review",
    response_model=ExpenseRead,
    summary="Update Expense Review Status",
    description="Update the review state and observations for an expense record. Admin only."
)
async def update_expense_review(
    *,
    db: Session = Depends(get_sync_db),
    expense_id: UUID,
    review_update: ExpenseReviewUpdate,
    current_admin: Admin = Depends(get_current_admin)
) -> ExpenseRead:
    """
    Update expense review status and observations.
    
    Only admins can update review status.
    
    - **review_state**: pending, approved, or rejected
    - **review_observations**: Optional comments from reviewer
    """
    try:
        expense = expense_crud.update_expense_review_status(
            db=db,
            expense_id=expense_id,
            review_state=review_update.review_state,
            review_observations=review_update.review_observations
        )
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found"
            )
        
        return expense
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update expense review: {str(e)}"
        )


@router.get(
    "/pending-review",
    response_model=List[ExpenseWithDetails],
    summary="Get Expenses Pending Review",
    description="Get all expenses that are pending review. Admin only."
)
async def get_expenses_pending_review(
    *,
    db: Session = Depends(get_sync_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_admin: Admin = Depends(get_current_admin)
) -> List[ExpenseWithDetails]:
    """
    Get all expenses that are pending review.
    
    Only admins can view pending reviews.
    """
    try:
        expenses = expense_crud.get_expenses_pending_review(db=db, skip=skip, limit=limit)
        
        # Convert to ExpenseWithDetails format
        result = []
        for expense in expenses:
            expense_dict = {
                "id": expense.id,
                "worker_id": expense.worker_id,
                "branch_id": expense.branch_id,
                "expense_date": expense.expense_date,
                "expense_description": expense.expense_description,
                "vendor_payee": expense.vendor_payee,
                "expense_category": expense.expense_category,
                "quantity": expense.quantity,
                "unit_of_measure": expense.unit_of_measure,
                "unit_cost": expense.unit_cost,
                "total_amount": expense.total_amount,
                "tax_amount": expense.tax_amount,
                "receipt_number": expense.receipt_number,
                "payment_method": expense.payment_method,
                "is_reimbursable": expense.is_reimbursable,
                "notes": expense.notes,
                "review_state": expense.review_state,
                "review_observations": expense.review_observations,
                "created_at": expense.created_at,
                "updated_at": expense.updated_at,
                "is_locked": expense.is_locked,
                "locked_at": expense.locked_at,
                "worker_username": expense.worker.username if expense.worker else "Unknown",
                "branch_name": expense.branch.name if expense.branch else "Unknown",
                "net_amount": expense.net_amount,
                "has_receipt": expense.has_receipt,
                "is_pending_reimbursement": expense.is_pending_reimbursement
            }
            result.append(ExpenseWithDetails(**expense_dict))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending expenses: {str(e)}"
        )


@router.get(
    "/review/{review_state}",
    response_model=List[ExpenseWithDetails],
    summary="Get Expenses by Review State",
    description="Get expenses filtered by review state. Admin only."
)
async def get_expenses_by_review_state(
    *,
    db: Session = Depends(get_sync_db),
    review_state: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_admin: Admin = Depends(get_current_admin)
) -> List[ExpenseWithDetails]:
    """
    Get expenses filtered by review state.
    
    - **review_state**: pending, approved, or rejected
    
    Only admins can view expenses by review state.
    """
    if review_state.lower() not in ['pending', 'approved', 'rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="review_state must be 'pending', 'approved', or 'rejected'"
        )
    
    try:
        expenses = expense_crud.get_expenses_by_review_state(
            db=db, 
            review_state=review_state.lower(), 
            skip=skip, 
            limit=limit
        )
        
        # Convert to ExpenseWithDetails format
        result = []
        for expense in expenses:
            expense_dict = {
                "id": expense.id,
                "worker_id": expense.worker_id,
                "branch_id": expense.branch_id,
                "expense_date": expense.expense_date,
                "expense_description": expense.expense_description,
                "vendor_payee": expense.vendor_payee,
                "expense_category": expense.expense_category,
                "quantity": expense.quantity,
                "unit_of_measure": expense.unit_of_measure,
                "unit_cost": expense.unit_cost,
                "total_amount": expense.total_amount,
                "tax_amount": expense.tax_amount,
                "receipt_number": expense.receipt_number,
                "payment_method": expense.payment_method,
                "is_reimbursable": expense.is_reimbursable,
                "notes": expense.notes,
                "review_state": expense.review_state,
                "review_observations": expense.review_observations,
                "created_at": expense.created_at,
                "updated_at": expense.updated_at,
                "is_locked": expense.is_locked,
                "locked_at": expense.locked_at,
                "worker_username": expense.worker.username if expense.worker else "Unknown",
                "branch_name": expense.branch.name if expense.branch else "Unknown",
                "net_amount": expense.net_amount,
                "has_receipt": expense.has_receipt,
                "is_pending_reimbursement": expense.is_pending_reimbursement
            }
            result.append(ExpenseWithDetails(**expense_dict))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get expenses by review state: {str(e)}"
        )


@router.post(
    "/bulk-lock",
    response_model=BulkLockResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk Lock Expenses",
    description="Lock multiple expense records to prevent editing. Super admin only.",
    dependencies=[RequireSuperAdmin]
)
async def bulk_lock_expenses(
    *,
    db: Session = Depends(get_sync_db),
    lock_request: BulkLockRequest,
    current_admin: Admin = Depends(get_current_admin)
) -> BulkLockResponse:
    """
    Lock expense records in bulk based on filters.
    
    Supports filtering by:
    - record_ids: List of specific expense IDs
    - date_range: Date range for expense_date
    - branch_id: Filter by branch
    """
    try:
        locked_ids = expense_crud.bulk_lock_expenses(
            db=db,
            record_ids=lock_request.record_ids,
            date_range=lock_request.date_range,
            branch_id=lock_request.branch_id
        )
        
        return BulkLockResponse(
            success=True,
            locked_count=len(locked_ids),
            message=f"Successfully locked {len(locked_ids)} expense record(s)",
            locked_ids=locked_ids
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lock expenses: {str(e)}"
        )


@router.post(
    "/bulk-unlock",
    response_model=BulkLockResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk Unlock Expenses",
    description="Unlock multiple expense records. Super admin only.",
    dependencies=[RequireSuperAdmin]
)
async def bulk_unlock_expenses(
    *,
    db: Session = Depends(get_sync_db),
    unlock_request: BulkLockRequest,
    current_admin: Admin = Depends(get_current_admin)
) -> BulkLockResponse:
    """
    Unlock expense records in bulk by IDs.
    
    Requires record_ids to be provided.
    """
    try:
        if not unlock_request.record_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="record_ids must be provided for unlock operation"
            )
        
        unlocked_ids = expense_crud.bulk_unlock_expenses(
            db=db,
            record_ids=unlock_request.record_ids
        )
        
        return BulkLockResponse(
            success=True,
            locked_count=len(unlocked_ids),
            message=f"Successfully unlocked {len(unlocked_ids)} expense record(s)",
            locked_ids=unlocked_ids
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlock expenses: {str(e)}"
        )


@router.patch(
    "/{expense_id}/branch",
    response_model=ExpenseRead,
    summary="Update Expense Branch",
    description="Update the branch associated with an expense record. Super admin only."
)
async def update_expense_branch(
    *,
    db: Session = Depends(get_sync_db),
    expense_id: UUID,
    branch_id: UUID = Body(..., description="New branch ID to assign", embed=True),
    current_admin: Admin = Depends(get_current_super_admin)
) -> ExpenseRead:
    """
    Update the branch_id for an expense record.
    
    - **Super admins only** can update branch for any record (including locked)
    - Validates that the new branch exists
    
    Returns the updated expense record.
    """
    try:
        updated_expense = expense_crud.update_expense_branch(
            db=db,
            expense_id=expense_id,
            new_branch_id=branch_id,
            is_super_admin=True
        )
        
        if not updated_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense record with ID {expense_id} not found"
            )
        
        return updated_expense
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update expense branch: {str(e)}"
        )
