"""
Payroll management API endpoints.

This module provides FastAPI endpoints for payroll management operations
including creating, reading, updating, and deleting payroll records,
as well as generating payroll reports and summaries.
"""

from typing import List, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.admin import Admin
from backend.fastapi.models.user import User
from backend.fastapi.schemas.payroll import (
    PayrollCreate, PayrollRead, PayrollUpdate, PayrollWithDetails,
    PayrollListResponse, PayrollSummary, PayrollPeriodReport
)
from backend.fastapi.crud.payroll import (
    create_payroll, get_payroll, get_payrolls, get_payrolls_count,
    update_payroll, delete_payroll, get_worker_payroll_summary,
    get_payroll_period_report, get_payroll_with_details
)
from backend.security.dependencies import RequireActiveAdmin, RequireActiveUser


router = APIRouter(tags=["payroll-management"])


@router.post("/", response_model=PayrollRead, summary="Create New Payroll Record")
async def create_payroll_record(
    payroll_data: PayrollCreate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Create a new payroll record (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **date**: Date of the payroll entry/payment
    - **worker_id**: ID of the worker/user
    - **branch_id**: ID of the branch
    - **days_worked**: Number of days worked (0-31)
    - **amount**: Payment amount (can be negative for deductions)
    - **payroll_type**: Type of payroll entry (e.g., "regular", "overtime")
    - **notes**: Additional notes (optional)
    
    **Returns:**
    - Payroll record information
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Worker or branch not found
    - **422**: Validation errors
    """
    try:
        payroll = create_payroll(db, payroll_data)
        return PayrollRead.model_validate(payroll)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payroll record: {str(e)}"
        )


@router.get("/", response_model=PayrollListResponse, summary="List Payroll Records")
async def list_payroll_records(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    worker_id: Optional[UUID] = Query(None, description="Filter by worker ID"),
    branch_id: Optional[UUID] = Query(None, description="Filter by branch ID"),
    payroll_type: Optional[str] = Query(None, description="Filter by payroll type"),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    order_by: str = Query("date_desc", description="Sort order (date_desc, date_asc, amount_desc, amount_asc)"),
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get list of payroll records with filtering (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **worker_id**: Filter by specific worker (optional)
    - **branch_id**: Filter by specific branch (optional)
    - **payroll_type**: Filter by payroll type (optional)
    - **start_date**: Filter records from this date (optional)
    - **end_date**: Filter records until this date (optional)
    - **order_by**: Sorting order
    
    **Returns:**
    - Paginated list of payroll records with details
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    """
    try:
        # Get payroll records with details
        payrolls = get_payrolls(
            db,
            skip=skip,
            limit=limit,
            worker_id=worker_id,
            branch_id=branch_id,
            payroll_type=payroll_type,
            start_date=start_date,
            end_date=end_date,
            order_by=order_by
        )
        
        # Convert to detailed format
        payroll_details = []
        for payroll in payrolls:
            payroll_details.append(PayrollWithDetails(
                **payroll.__dict__,
                worker_username=payroll.worker.username,
                branch_name=payroll.branch.name
            ))
        
        # Get total count with same filters
        total = get_payrolls_count(
            db,
            worker_id=worker_id,
            branch_id=branch_id,
            payroll_type=payroll_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return PayrollListResponse(
            payroll_records=payroll_details,
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payroll records: {str(e)}"
        )


@router.get("/{payroll_id}", response_model=PayrollWithDetails, summary="Get Payroll Record by ID")
async def get_payroll_record(
    payroll_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get specific payroll record by ID (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **payroll_id**: UUID of the payroll record
    
    **Returns:**
    - Payroll record with worker and branch details
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Payroll record not found
    - **422**: Invalid UUID format
    """
    payroll_data = get_payroll_with_details(db, payroll_id)
    if not payroll_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    return PayrollWithDetails.model_validate(payroll_data)


@router.put("/{payroll_id}", response_model=PayrollRead, summary="Update Payroll Record")
async def update_payroll_record(
    payroll_id: UUID,
    payroll_update: PayrollUpdate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Update payroll record (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **payroll_id**: UUID of payroll record to update
    - **date**: Updated date (optional)
    - **worker_id**: Updated worker ID (optional)
    - **branch_id**: Updated branch ID (optional)
    - **days_worked**: Updated days worked (optional)
    - **amount**: Updated amount (optional)
    - **payroll_type**: Updated payroll type (optional)
    - **notes**: Updated notes (optional)
    
    **Returns:**
    - Updated payroll record information
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Payroll record, worker, or branch not found
    - **422**: Invalid data format
    """
    try:
        updated_payroll = update_payroll(db, payroll_id, payroll_update)
        if not updated_payroll:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll record not found"
            )
        
        return PayrollRead.model_validate(updated_payroll)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payroll record: {str(e)}"
        )


@router.delete("/{payroll_id}", summary="Delete Payroll Record")
async def delete_payroll_record(
    payroll_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Delete payroll record (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Security Notes:**
    - This permanently deletes the payroll record
    - Consider creating an audit trail before deletion
    
    **Parameters:**
    - **payroll_id**: UUID of payroll record to delete
    
    **Returns:**
    - Success message with deleted payroll ID
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Payroll record not found
    """
    success = delete_payroll(db, payroll_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    return {"message": "Payroll record deleted successfully", "payroll_id": str(payroll_id)}


@router.get("/worker/{worker_id}/summary", response_model=PayrollSummary, summary="Get Worker Payroll Summary")
async def get_worker_summary(
    worker_id: UUID,
    start_date: Optional[date] = Query(None, description="Summary from this date"),
    end_date: Optional[date] = Query(None, description="Summary until this date"),
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get payroll summary for a specific worker (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **worker_id**: UUID of the worker
    - **start_date**: Start date for summary period (optional)
    - **end_date**: End date for summary period (optional)
    
    **Returns:**
    - Worker payroll summary with totals and statistics
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Worker not found
    """
    summary = get_worker_payroll_summary(db, worker_id, start_date, end_date)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    return PayrollSummary.model_validate(summary)


@router.get("/reports/period", response_model=PayrollPeriodReport, summary="Generate Period Report")
async def generate_period_report(
    start_date: date = Query(..., description="Start date of reporting period"),
    end_date: date = Query(..., description="End date of reporting period"),
    branch_id: Optional[UUID] = Query(None, description="Filter by specific branch"),
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Generate payroll report for a specific period (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **start_date**: Start date of the reporting period
    - **end_date**: End date of the reporting period
    - **branch_id**: Filter by specific branch (optional)
    
    **Returns:**
    - Comprehensive payroll report with breakdowns by type and branch
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **422**: Invalid date range
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Start date must be before or equal to end date"
        )
    
    try:
        report = get_payroll_period_report(db, start_date, end_date, branch_id)
        return PayrollPeriodReport.model_validate(report)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate payroll report: {str(e)}"
        )


# User endpoint to view their own payroll records
@router.get("/my/records", response_model=List[PayrollRead], summary="Get My Payroll Records")
async def get_my_payroll_records(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    db: Session = Depends(get_sync_db),
    current_user: User = RequireActiveUser
):
    """
    Get current user's own payroll records (user endpoint).
    
    **Permissions:** Requires active user authentication
    
    **Parameters:**
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **start_date**: Filter records from this date (optional)
    - **end_date**: Filter records until this date (optional)
    
    **Returns:**
    - List of user's payroll records
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: User account deactivated
    """
    try:
        payrolls = get_payrolls(
            db,
            skip=skip,
            limit=limit,
            worker_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            order_by="date_desc"
        )
        
        return [PayrollRead.model_validate(payroll) for payroll in payrolls]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payroll records: {str(e)}"
        )


@router.get("/my/summary", response_model=PayrollSummary, summary="Get My Payroll Summary")
async def get_my_payroll_summary(
    start_date: Optional[date] = Query(None, description="Summary from this date"),
    end_date: Optional[date] = Query(None, description="Summary until this date"),
    db: Session = Depends(get_sync_db),
    current_user: User = RequireActiveUser
):
    """
    Get current user's payroll summary (user endpoint).
    
    **Permissions:** Requires active user authentication
    
    **Parameters:**
    - **start_date**: Start date for summary period (optional)
    - **end_date**: End date for summary period (optional)
    
    **Returns:**
    - User's payroll summary with totals and statistics
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: User account deactivated
    """
    try:
        summary = get_worker_payroll_summary(db, current_user.id, start_date, end_date)
        return PayrollSummary.model_validate(summary)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payroll summary: {str(e)}"
        )