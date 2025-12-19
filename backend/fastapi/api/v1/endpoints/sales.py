"""
Sales API endpoints.

This module provides REST API endpoints for sales and cash register closure management.
Includes create, delete, list (paginated), and search (filtered) operations.
"""

from uuid import UUID
from typing import List, Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.security.dependencies import get_current_admin, get_current_admin_or_user
from backend.fastapi.models.admin import Admin
from backend.fastapi.models.user import User
from backend.fastapi.schemas.sales import (
    SalesCreate,
    SalesUpdate,
    SalesRead,
    SalesWithDetails,
    SalesSummary,
    SalesListResponse,
    SalesPeriodReport,
    DiscrepancyReport,
    SalesReviewUpdate,
    SalesReviewSummary
)
from backend.fastapi.crud import sales as sales_crud

router = APIRouter()


@router.post(
    "/",
    response_model=SalesRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Sales Record",
    description="Create a new sales/cash register closure record with automatic calculations."
)
async def create_sales_record(
    *,
    db: Session = Depends(get_sync_db),
    sales_in: SalesCreate,
    current_user: Admin | User = Depends(get_current_admin_or_user)
) -> SalesRead:
    """
    Create a new sales record.
    
    - **Admins and users** can create sales records
    - Validates worker and branch existence
    - Prevents duplicate closure numbers for same date/branch
    - Automatically calculates totals and discrepancies
    
    Returns the created sales record with calculated fields.
    """
    try:
        sales_record = sales_crud.create_sales(db=db, sales_data=sales_in)
        return sales_record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sales record: {str(e)}"
        )


@router.delete(
    "/{sales_id}",
    summary="Delete Sales Record",
    description="Delete a sales record by ID. Only admins can delete sales records."
)
async def delete_sales_record(
    *,
    db: Session = Depends(get_sync_db),
    sales_id: UUID,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Delete a sales record.
    
    - **Only admins** can delete sales records
    - Returns 404 if sales record doesn't exist
    """
    success = sales_crud.delete_sales(db=db, sales_id=sales_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales record with ID {sales_id} not found"
        )
    
    return {"message": "Sales record deleted successfully", "sales_id": str(sales_id)}


@router.get(
    "/",
    response_model=SalesListResponse,
    summary="List Sales Records",
    description="Get paginated list of sales records with optional filtering."
)
async def list_sales_records(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin | User = Depends(get_current_admin_or_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    order_by: str = Query(
        "date_desc",
        regex="^(date_desc|date_asc|sales_desc|sales_asc|discrepancy_desc)$",
        description="Sort order: date_desc, date_asc, sales_desc, sales_asc, discrepancy_desc"
    )
) -> SalesListResponse:
    """
    Get paginated list of sales records.
    
    - **Admins** see all sales records
    - **Users** see only their own sales records
    - Supports pagination with skip/limit
    - Supports multiple sorting options
    
    Returns paginated list with metadata.
    """
    # Filter by worker if user is not admin
    worker_id = None
    if isinstance(current_user, User):
        worker_id = current_user.id
    
    # Get sales records
    sales_records = sales_crud.get_sales_records(
        db=db,
        skip=skip,
        limit=limit,
        worker_id=worker_id,
        order_by=order_by
    )
    
    # Convert Sales objects to SalesWithDetails by adding worker_username and branch_name
    sales_with_details = []
    for sales in sales_records:
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
            "review_state": sales.review_state,
            "review_observations": sales.review_observations,
            "created_at": sales.created_at,
            "worker_username": sales.worker.username if sales.worker else "",
            "branch_name": sales.branch.name if sales.branch else ""
        }
        sales_with_details.append(SalesWithDetails(**sales_dict))
    
    # Get total count for pagination
    total_count = sales_crud.get_sales_count(
        db=db,
        worker_id=worker_id
    )
    
    return SalesListResponse(
        sales=sales_with_details,
        total_count=total_count,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total_count
    )


@router.get(
    "/search",
    response_model=SalesListResponse,
    summary="Search Sales Records",
    description="Search sales records with advanced filtering options."
)
async def search_sales_records(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin | User = Depends(get_current_admin_or_user),
    worker: Optional[UUID] = Query(None, description="Filter by worker ID"),
    branch: Optional[UUID] = Query(None, description="Filter by branch ID"),
    start_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter until this date (YYYY-MM-DD)"),
    closure_number: Optional[int] = Query(None, ge=1, description="Filter by closure number"),
    has_discrepancy: Optional[bool] = Query(None, description="Filter by discrepancy presence"),
    min_discrepancy: Optional[Decimal] = Query(None, ge=0, description="Minimum discrepancy amount"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    order_by: str = Query(
        "date_desc",
        regex="^(date_desc|date_asc|sales_desc|sales_asc|discrepancy_desc)$",
        description="Sort order"
    )
) -> SalesListResponse:
    """
    Search sales records with advanced filtering.
    
    - **Admins** can filter by any worker
    - **Users** can only see their own records (worker filter ignored)
    - Supports filtering by multiple criteria
    - Supports pagination and sorting
    
    Available filters:
    - worker: Filter by specific worker ID
    - branch: Filter by specific branch ID
    - start_date: Records from this date onwards
    - end_date: Records until this date
    - closure_number: Specific closure number
    - has_discrepancy: Records with/without discrepancies
    - min_discrepancy: Minimum discrepancy amount
    """
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
    
    # Apply discrepancy filtering logic
    if min_discrepancy is not None:
        has_discrepancy = True  # If min_discrepancy is set, only show records with discrepancies
    
    # Get filtered sales records
    sales_records = sales_crud.get_sales_records(
        db=db,
        skip=skip,
        limit=limit,
        worker_id=worker_id,
        branch_id=branch,
        start_date=start_date,
        end_date=end_date,
        closure_number=closure_number,
        has_discrepancy=has_discrepancy,
        order_by=order_by
    )
    
    # Apply additional filtering for min_discrepancy (since CRUD doesn't support this directly)
    if min_discrepancy is not None:
        sales_records = [
            record for record in sales_records
            if abs(record.discrepancy) >= min_discrepancy
        ]
    
    # Convert Sales objects to SalesWithDetails by adding worker_username and branch_name
    sales_with_details = []
    for sales in sales_records:
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
            "review_state": sales.review_state,
            "review_observations": sales.review_observations,
            "created_at": sales.created_at,
            "worker_username": sales.worker.username if sales.worker else "",
            "branch_name": sales.branch.name if sales.branch else ""
        }
        sales_with_details.append(SalesWithDetails(**sales_dict))
    
    # Get total count with same filters
    total_count = sales_crud.get_sales_count(
        db=db,
        worker_id=worker_id,
        branch_id=branch,
        start_date=start_date,
        end_date=end_date,
        closure_number=closure_number,
        has_discrepancy=has_discrepancy
    )
    
    # Adjust total count for min_discrepancy filtering
    if min_discrepancy is not None:
        # Note: This is approximate since we're filtering post-query
        # For exact counts, we'd need to modify the CRUD function
        total_count = len(sales_with_details) if skip == 0 else total_count
    
    return SalesListResponse(
        sales=sales_with_details,
        total_count=total_count,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total_count
    )


@router.get(
    "/{sales_id}",
    response_model=SalesWithDetails,
    summary="Get Sales Record",
    description="Get a specific sales record with worker and branch details."
)
async def get_sales_record(
    *,
    db: Session = Depends(get_sync_db),
    sales_id: UUID,
    current_user: Admin | User = Depends(get_current_admin_or_user)
) -> SalesWithDetails:
    """
    Get a specific sales record with details.
    
    - **Admins** can view any sales record
    - **Users** can only view their own sales records
    - Returns detailed information including worker and branch names
    """
    sales_record = sales_crud.get_sales(db=db, sales_id=sales_id)
    if not sales_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales record with ID {sales_id} not found"
        )
    
    # Check access permissions
    if isinstance(current_user, User) and sales_record.worker_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own sales records"
        )
    
    # Get detailed record
    detailed_record = sales_crud.get_sales_with_details(db=db, sales_id=sales_id)
    if not detailed_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales record details not found for ID {sales_id}"
        )
    
    return SalesWithDetails(**detailed_record)


@router.put(
    "/{sales_id}",
    response_model=SalesRead,
    summary="Update Sales Record",
    description="Update a sales record. Only admins can update sales records."
)
async def update_sales_record(
    *,
    db: Session = Depends(get_sync_db),
    sales_id: UUID,
    sales_update: SalesUpdate,
    current_user: Admin = Depends(get_current_admin)
) -> SalesRead:
    """
    Update a sales record.
    
    - **Only admins** can update sales records
    - Validates worker and branch existence if being updated
    - Prevents duplicate closure numbers
    - Automatically recalculates totals and discrepancies
    
    Returns the updated sales record.
    """
    try:
        updated_sales = sales_crud.update_sales(
            db=db,
            sales_id=sales_id,
            sales_update=sales_update
        )
        
        if not updated_sales:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales record with ID {sales_id} not found"
            )
        
        return updated_sales
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sales record: {str(e)}"
        )


@router.get(
    "/reports/period",
    response_model=SalesPeriodReport,
    summary="Get Sales Period Report",
    description="Generate comprehensive sales report for a specific period."
)
async def get_sales_period_report(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin = Depends(get_current_admin),
    start_date: date = Query(..., description="Report start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Report end date (YYYY-MM-DD)"),
    branch_id: Optional[UUID] = Query(None, description="Filter by specific branch")
) -> SalesPeriodReport:
    """
    Generate comprehensive sales report for a period.
    
    - **Only admins** can access reports
    - Provides detailed breakdown by branch, worker, and daily totals
    - Includes summary statistics and percentages
    
    Returns comprehensive period analysis.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        report_data = sales_crud.get_sales_period_report(
            db=db,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_id
        )
        
        return SalesPeriodReport(**report_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate period report: {str(e)}"
        )


@router.get(
    "/reports/discrepancies",
    response_model=DiscrepancyReport,
    summary="Get Discrepancy Report",
    description="Generate report of sales records with discrepancies for analysis."
)
async def get_discrepancy_report(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin = Depends(get_current_admin),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    branch_id: Optional[UUID] = Query(None, description="Filter by specific branch"),
    min_discrepancy: Optional[Decimal] = Query(
        None,
        ge=0,
        description="Minimum discrepancy amount to include"
    )
) -> DiscrepancyReport:
    """
    Generate discrepancy analysis report.
    
    - **Only admins** can access discrepancy reports
    - Shows sales records with cash register discrepancies
    - Provides statistics and top discrepancy records
    - Helps identify patterns and issues
    
    Returns comprehensive discrepancy analysis.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        report_data = sales_crud.get_discrepancy_report(
            db=db,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_id,
            min_discrepancy=min_discrepancy
        )
        
        # Convert Sales objects to SalesWithDetails in discrepancy_records
        sales_with_details = []
        for sales in report_data["discrepancy_records"]:
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
            sales_with_details.append(SalesWithDetails(**sales_dict))
        
        # Replace discrepancy_records with converted objects
        report_data["discrepancy_records"] = sales_with_details
        
        return DiscrepancyReport(**report_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate discrepancy report: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=SalesSummary,
    summary="Get Sales Summary",
    description="Get sales summary for current user or specified period."
)
async def get_sales_summary(
    *,
    db: Session = Depends(get_sync_db),
    current_user: Admin | User = Depends(get_current_admin_or_user),
    start_date: Optional[date] = Query(None, description="Summary start date"),
    end_date: Optional[date] = Query(None, description="Summary end date"),
    branch_id: Optional[UUID] = Query(None, description="Filter by branch (admins only)")
) -> SalesSummary:
    """
    Get sales summary information.
    
    - **Admins** can get summary for any worker/branch
    - **Users** get summary for their own sales only
    - Provides aggregated totals and statistics
    
    Returns sales summary with key metrics.
    """
    # Apply user restrictions
    worker_id = None
    if isinstance(current_user, User):
        worker_id = current_user.id
        branch_id = None  # Users cannot filter by branch
    
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        # Use period summary if dates provided, otherwise get basic summary
        if start_date and end_date:
            summary_data = sales_crud.get_sales_period_summary(
                db=db,
                start_date=start_date,
                end_date=end_date,
                branch_id=branch_id,
                worker_id=worker_id
            )
        else:
            # Get basic summary (recent records)
            recent_records = sales_crud.get_sales_records(
                db=db,
                skip=0,
                limit=50,  # Last 50 records for summary
                worker_id=worker_id,
                branch_id=branch_id,
                order_by="date_desc"
            )
            
            if recent_records:
                total_sales = sum(record.sales_total for record in recent_records)
                total_payments = sum(record.payments_nbr for record in recent_records)
                total_discrepancy = sum(record.discrepancy for record in recent_records)
                avg_sale = total_sales / total_payments if total_payments > 0 else Decimal("0")
                
                summary_data = {
                    "total_sales": total_sales,
                    "total_payments": total_payments,
                    "total_discrepancy": total_discrepancy,
                    "average_sale": avg_sale,
                    "total_revenue": sum(record.revenue_total for record in recent_records),
                    "total_fees": sum(record.kiwi_fee_total for record in recent_records),
                    "card_percentage": Decimal("0"),
                    "cash_percentage": Decimal("0")
                }
            else:
                summary_data = {
                    "total_sales": Decimal("0"),
                    "total_payments": 0,
                    "total_discrepancy": Decimal("0"),
                    "average_sale": Decimal("0"),
                    "total_revenue": Decimal("0"),
                    "total_fees": Decimal("0"),
                    "card_percentage": Decimal("0"),
                    "cash_percentage": Decimal("0")
                }
        
        return SalesSummary(**summary_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sales summary: {str(e)}"
        )


@router.patch(
    "/{sales_id}/review",
    response_model=SalesRead,
    summary="Update Sales Review Status",
    description="Update the review state and observations for a sales record. Admin only."
)
async def update_sales_review(
    *,
    db: Session = Depends(get_sync_db),
    sales_id: UUID,
    review_update: SalesReviewUpdate,
    current_admin: Admin = Depends(get_current_admin)
) -> SalesRead:
    """
    Update sales review status and observations.
    
    Only admins can update review status.
    
    - **review_state**: pending, approved, or rejected
    - **review_observations**: Optional comments from reviewer
    """
    try:
        sales = sales_crud.update_sales_review_status(
            db=db,
            sales_id=sales_id,
            review_state=review_update.review_state,
            review_observations=review_update.review_observations
        )
        
        if not sales:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales record with ID {sales_id} not found"
            )
        
        return sales
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sales review: {str(e)}"
        )


@router.get(
    "/pending-review",
    response_model=List[SalesWithDetails],
    summary="Get Sales Records Pending Review",
    description="Get all sales records that are pending review. Admin only."
)
async def get_sales_pending_review(
    *,
    db: Session = Depends(get_sync_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_admin: Admin = Depends(get_current_admin)
) -> List[SalesWithDetails]:
    """
    Get all sales records that are pending review.
    
    Only admins can view pending reviews.
    """
    try:
        sales_records = sales_crud.get_sales_pending_review(db=db, skip=skip, limit=limit)
        
        # Convert to SalesWithDetails format
        result = []
        for sales in sales_records:
            sales_dict = {
                "id": sales.id,
                "worker_id": sales.worker_id,
                "branch_id": sales.branch_id,
                "closure_date": sales.closure_date,
                "closure_number": sales.closure_number,
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
                "review_state": sales.review_state,
                "review_observations": sales.review_observations,
                "created_at": sales.created_at,
                "worker_username": sales.worker.username if sales.worker else "Unknown",
                "branch_name": sales.branch.name if sales.branch else "Unknown"
            }
            result.append(SalesWithDetails(**sales_dict))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending sales records: {str(e)}"
        )


@router.get(
    "/review/{review_state}",
    response_model=List[SalesWithDetails],
    summary="Get Sales Records by Review State",
    description="Get sales records filtered by review state. Admin only."
)
async def get_sales_by_review_state(
    *,
    db: Session = Depends(get_sync_db),
    review_state: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_admin: Admin = Depends(get_current_admin)
) -> List[SalesWithDetails]:
    """
    Get sales records filtered by review state.
    
    - **review_state**: pending, approved, or rejected
    
    Only admins can view sales records by review state.
    """
    if review_state.lower() not in ['pending', 'approved', 'rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="review_state must be 'pending', 'approved', or 'rejected'"
        )
    
    try:
        sales_records = sales_crud.get_sales_by_review_state(
            db=db, 
            review_state=review_state.lower(), 
            skip=skip, 
            limit=limit
        )
        
        # Convert to SalesWithDetails format
        result = []
        for sales in sales_records:
            sales_dict = {
                "id": sales.id,
                "worker_id": sales.worker_id,
                "branch_id": sales.branch_id,
                "closure_date": sales.closure_date,
                "closure_number": sales.closure_number,
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
                "review_state": sales.review_state,
                "review_observations": sales.review_observations,
                "created_at": sales.created_at,
                "worker_username": sales.worker.username if sales.worker else "Unknown",
                "branch_name": sales.branch.name if sales.branch else "Unknown"
            }
            result.append(SalesWithDetails(**sales_dict))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sales records by review state: {str(e)}"
        )
