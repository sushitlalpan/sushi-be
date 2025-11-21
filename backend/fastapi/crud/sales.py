"""
Sales CRUD operations.

This module provides Create, Read, Update, Delete operations
for Sales model management and comprehensive sales reporting.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc, asc, or_
from fastapi import HTTPException, status

from backend.fastapi.models.sales import Sales
from backend.fastapi.models.user import User
from backend.fastapi.models.branch import Branch
from backend.fastapi.schemas.sales import SalesCreate, SalesUpdate


def create_sales(db: Session, sales_data: SalesCreate) -> Sales:
    """
    Create a new sales record with automatic calculations.
    
    Args:
        db: Database session
        sales_data: Sales creation data
        
    Returns:
        Created sales instance with calculated totals
        
    Raises:
        HTTPException: If worker or branch doesn't exist, or duplicate closure number
    """
    # Validate worker exists
    worker = db.query(User).filter(User.id == sales_data.worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {sales_data.worker_id} not found"
        )
    
    # Validate branch exists
    branch = db.query(Branch).filter(Branch.id == sales_data.branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch with ID {sales_data.branch_id} not found"
        )
    
    # Check for duplicate closure number on the same date and branch
    existing_closure = (
        db.query(Sales)
        .filter(
            and_(
                Sales.closure_date == sales_data.closure_date,
                Sales.closure_number == sales_data.closure_number,
                Sales.branch_id == sales_data.branch_id
            )
        )
        .first()
    )
    
    if existing_closure:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Closure number {sales_data.closure_number} already exists for {sales_data.closure_date} at this branch"
        )
    
    # Create new sales record
    db_sales = Sales(
        worker_id=sales_data.worker_id,
        closure_date=sales_data.closure_date,
        closure_number=sales_data.closure_number,
        branch_id=sales_data.branch_id,
        payments_nbr=sales_data.payments_nbr,
        sales_total=sales_data.sales_total,
        card_itpv=sales_data.card_itpv,
        card_refund=sales_data.card_refund,
        card_kiwi=sales_data.card_kiwi,
        transfer_amt=sales_data.transfer_amt,
        cash_amt=sales_data.cash_amt,
        cash_refund=sales_data.cash_refund,
        kiwi_fee_total=sales_data.kiwi_fee_total,
        notes=sales_data.notes
    )
    
    # Calculate derived fields
    db_sales.calculate_totals()
    
    db.add(db_sales)
    db.commit()
    db.refresh(db_sales)
    
    return db_sales


def get_sales(db: Session, sales_id: UUID) -> Optional[Sales]:
    """
    Get a sales record by ID.
    
    Args:
        db: Database session
        sales_id: Sales unique identifier
        
    Returns:
        Sales instance if found, None otherwise
    """
    return (
        db.query(Sales)
        .options(joinedload(Sales.worker), joinedload(Sales.branch))
        .filter(Sales.id == sales_id)
        .first()
    )


def get_sales_records(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    worker_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    closure_number: Optional[int] = None,
    has_discrepancy: Optional[bool] = None,
    order_by: str = "date_desc"
) -> List[Sales]:
    """
    Get a list of sales records with filtering and pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        worker_id: Filter by specific worker
        branch_id: Filter by specific branch
        start_date: Filter records from this date
        end_date: Filter records until this date
        closure_number: Filter by closure number
        has_discrepancy: Filter by discrepancy presence
        order_by: Sorting order
        
    Returns:
        List of sales instances
    """
    query = (
        db.query(Sales)
        .options(joinedload(Sales.worker), joinedload(Sales.branch))
    )
    
    # Apply filters
    if worker_id:
        query = query.filter(Sales.worker_id == worker_id)
    
    if branch_id:
        query = query.filter(Sales.branch_id == branch_id)
    
    if start_date:
        query = query.filter(Sales.closure_date >= start_date)
    
    if end_date:
        query = query.filter(Sales.closure_date <= end_date)
    
    if closure_number:
        query = query.filter(Sales.closure_number == closure_number)
    
    if has_discrepancy is not None:
        if has_discrepancy:
            query = query.filter(func.abs(Sales.discrepancy) > 0.01)
        else:
            query = query.filter(func.abs(Sales.discrepancy) <= 0.01)
    
    # Apply ordering
    if order_by == "date_desc":
        query = query.order_by(desc(Sales.closure_date), desc(Sales.closure_number))
    elif order_by == "date_asc":
        query = query.order_by(asc(Sales.closure_date), asc(Sales.closure_number))
    elif order_by == "sales_desc":
        query = query.order_by(desc(Sales.sales_total))
    elif order_by == "sales_asc":
        query = query.order_by(asc(Sales.sales_total))
    elif order_by == "discrepancy_desc":
        query = query.order_by(desc(func.abs(Sales.discrepancy)))
    else:
        query = query.order_by(desc(Sales.closure_date), desc(Sales.closure_number))
    
    return query.offset(skip).limit(limit).all()


def get_sales_count(
    db: Session,
    worker_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    closure_number: Optional[int] = None,
    has_discrepancy: Optional[bool] = None
) -> int:
    """
    Get total count of sales records with same filters.
    
    Args:
        db: Database session
        Same filters as get_sales_records
        
    Returns:
        Total number of matching sales records
    """
    query = db.query(Sales)
    
    # Apply same filters as get_sales_records
    if worker_id:
        query = query.filter(Sales.worker_id == worker_id)
    
    if branch_id:
        query = query.filter(Sales.branch_id == branch_id)
    
    if start_date:
        query = query.filter(Sales.closure_date >= start_date)
    
    if end_date:
        query = query.filter(Sales.closure_date <= end_date)
    
    if closure_number:
        query = query.filter(Sales.closure_number == closure_number)
    
    if has_discrepancy is not None:
        if has_discrepancy:
            query = query.filter(func.abs(Sales.discrepancy) > 0.01)
        else:
            query = query.filter(func.abs(Sales.discrepancy) <= 0.01)
    
    return query.count()


def update_sales(db: Session, sales_id: UUID, sales_update: SalesUpdate) -> Optional[Sales]:
    """
    Update an existing sales record.
    
    Args:
        db: Database session
        sales_id: Sales unique identifier
        sales_update: Sales update data
        
    Returns:
        Updated sales instance if found, None otherwise
        
    Raises:
        HTTPException: If worker or branch doesn't exist, or duplicate closure number
    """
    # Get existing sales record
    db_sales = get_sales(db, sales_id)
    if not db_sales:
        return None
    
    # Validate worker if being updated
    if sales_update.worker_id:
        worker = db.query(User).filter(User.id == sales_update.worker_id).first()
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID {sales_update.worker_id} not found"
            )
    
    # Validate branch if being updated
    if sales_update.branch_id:
        branch = db.query(Branch).filter(Branch.id == sales_update.branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch with ID {sales_update.branch_id} not found"
            )
    
    # Check for duplicate closure number if being updated
    if sales_update.closure_number or sales_update.closure_date or sales_update.branch_id:
        new_closure_date = sales_update.closure_date or db_sales.closure_date
        new_closure_number = sales_update.closure_number or db_sales.closure_number
        new_branch_id = sales_update.branch_id or db_sales.branch_id
        
        existing_closure = (
            db.query(Sales)
            .filter(
                and_(
                    Sales.closure_date == new_closure_date,
                    Sales.closure_number == new_closure_number,
                    Sales.branch_id == new_branch_id,
                    Sales.id != sales_id
                )
            )
            .first()
        )
        
        if existing_closure:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Closure number {new_closure_number} already exists for {new_closure_date} at this branch"
            )
    
    # Update fields
    update_data = sales_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_sales, field, value)
    
    # Recalculate derived fields
    db_sales.calculate_totals()
    
    db.commit()
    db.refresh(db_sales)
    
    return db_sales


def delete_sales(db: Session, sales_id: UUID) -> bool:
    """
    Delete a sales record.
    
    Args:
        db: Database session
        sales_id: Sales unique identifier
        
    Returns:
        True if sales record was deleted, False if not found
    """
    db_sales = get_sales(db, sales_id)
    if not db_sales:
        return False
    
    db.delete(db_sales)
    db.commit()
    
    return True


def get_sales_period_summary(
    db: Session,
    start_date: date,
    end_date: date,
    branch_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Get comprehensive sales summary for a period.
    
    Args:
        db: Database session
        start_date: Start date of the period
        end_date: End date of the period
        branch_id: Filter by specific branch (optional)
        worker_id: Filter by specific worker (optional)
        
    Returns:
        Dictionary with comprehensive summary data
    """
    # Base query with date filters
    query = db.query(Sales).filter(
        and_(
            Sales.closure_date >= start_date,
            Sales.closure_date <= end_date
        )
    )
    
    if branch_id:
        query = query.filter(Sales.branch_id == branch_id)
    
    if worker_id:
        query = query.filter(Sales.worker_id == worker_id)
    
    # Get aggregated totals
    totals = (
        query.with_entities(
            func.sum(Sales.sales_total).label("total_sales"),
            func.sum(Sales.payments_nbr).label("total_payments"),
            func.sum(Sales.discrepancy).label("total_discrepancy"),
            func.sum(Sales.revenue_total).label("total_revenue"),
            func.sum(Sales.kiwi_fee_total).label("total_fees"),
            func.sum(Sales.card_total).label("total_card"),
            func.sum(Sales.cash_total).label("total_cash"),
            func.count(Sales.id).label("total_records")
        )
        .first()
    )
    
    # Calculate percentages
    total_sales = totals.total_sales or Decimal("0")
    total_card = totals.total_card or Decimal("0")
    total_cash = totals.total_cash or Decimal("0")
    total_payments_amt = total_card + total_cash
    
    card_percentage = (total_card / total_payments_amt * 100) if total_payments_amt > 0 else Decimal("0")
    cash_percentage = (total_cash / total_payments_amt * 100) if total_payments_amt > 0 else Decimal("0")
    
    # Calculate average sale
    total_payments = totals.total_payments or 0
    average_sale = (total_sales / total_payments) if total_payments > 0 else Decimal("0")
    
    return {
        "total_sales": totals.total_sales or Decimal("0"),
        "total_payments": total_payments,
        "total_discrepancy": totals.total_discrepancy or Decimal("0"),
        "average_sale": average_sale,
        "total_revenue": totals.total_revenue or Decimal("0"),
        "total_fees": totals.total_fees or Decimal("0"),
        "card_percentage": card_percentage,
        "cash_percentage": cash_percentage
    }


def get_sales_period_report(
    db: Session,
    start_date: date,
    end_date: date,
    branch_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive sales report for a period.
    
    Args:
        db: Database session
        start_date: Start date of the period
        end_date: End date of the period
        branch_id: Filter by specific branch (optional)
        
    Returns:
        Dictionary with comprehensive report data
    """
    # Get overall summary
    summary = get_sales_period_summary(db, start_date, end_date, branch_id)
    
    # Base query for breakdowns
    base_query = db.query(Sales).filter(
        and_(
            Sales.closure_date >= start_date,
            Sales.closure_date <= end_date
        )
    )
    
    if branch_id:
        base_query = base_query.filter(Sales.branch_id == branch_id)
    
    # Get breakdown by branch
    by_branch = {}
    if not branch_id:  # Only get branch breakdown if not filtering by branch
        branch_results = (
            base_query.join(Branch)
            .with_entities(
                Branch.name,
                func.sum(Sales.sales_total).label("branch_total")
            )
            .group_by(Branch.name)
            .all()
        )
        
        for branch_result in branch_results:
            by_branch[branch_result.name] = str(branch_result.branch_total)
    
    # Get breakdown by worker
    by_worker = {}
    worker_results = (
        base_query.join(User)
        .with_entities(
            User.username,
            func.sum(Sales.sales_total).label("worker_total")
        )
        .group_by(User.username)
        .all()
    )
    
    for worker_result in worker_results:
        by_worker[worker_result.username] = str(worker_result.worker_total)
    
    # Get daily totals
    daily_totals = []
    daily_results = (
        base_query.with_entities(
            Sales.closure_date,
            func.sum(Sales.sales_total).label("daily_total")
        )
        .group_by(Sales.closure_date)
        .order_by(Sales.closure_date)
        .all()
    )
    
    for daily_result in daily_results:
        daily_totals.append({
            "date": daily_result.closure_date.isoformat(),
            "total": str(daily_result.daily_total)
        })
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "by_branch": by_branch,
        "by_worker": by_worker,
        "daily_totals": daily_totals
    }


def get_discrepancy_report(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    branch_id: Optional[UUID] = None,
    min_discrepancy: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    Generate report of sales records with discrepancies.
    
    Args:
        db: Database session
        start_date: Filter from this date (optional)
        end_date: Filter until this date (optional)
        branch_id: Filter by specific branch (optional)
        min_discrepancy: Minimum discrepancy amount to include (optional)
        
    Returns:
        Dictionary with discrepancy analysis
    """
    # Base query for discrepancies
    query = db.query(Sales).filter(func.abs(Sales.discrepancy) > 0.01)
    
    if start_date:
        query = query.filter(Sales.closure_date >= start_date)
    
    if end_date:
        query = query.filter(Sales.closure_date <= end_date)
    
    if branch_id:
        query = query.filter(Sales.branch_id == branch_id)
    
    if min_discrepancy:
        query = query.filter(func.abs(Sales.discrepancy) >= min_discrepancy)
    
    # Get discrepancy statistics
    discrepancy_stats = (
        query.with_entities(
            func.count(Sales.id).label("total_discrepancies"),
            func.sum(Sales.discrepancy).label("total_discrepancy_amount"),
            func.max(func.abs(Sales.discrepancy)).label("largest_discrepancy"),
            func.avg(func.abs(Sales.discrepancy)).label("average_discrepancy")
        )
        .first()
    )
    
    # Get actual discrepancy records
    discrepancy_records = (
        query.options(joinedload(Sales.worker), joinedload(Sales.branch))
        .order_by(desc(func.abs(Sales.discrepancy)))
        .limit(50)  # Limit to prevent huge responses
        .all()
    )
    
    return {
        "total_discrepancies": discrepancy_stats.total_discrepancies or 0,
        "total_discrepancy_amount": discrepancy_stats.total_discrepancy_amount or Decimal("0"),
        "largest_discrepancy": discrepancy_stats.largest_discrepancy or Decimal("0"),
        "average_discrepancy": discrepancy_stats.average_discrepancy or Decimal("0"),
        "discrepancy_records": discrepancy_records
    }


def get_sales_with_details(db: Session, sales_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Get sales record with worker and branch details.
    
    Args:
        db: Database session
        sales_id: Sales unique identifier
        
    Returns:
        Dictionary with sales and related details or None if not found
    """
    result = (
        db.query(Sales, User.username, Branch.name)
        .join(User, Sales.worker_id == User.id)
        .join(Branch, Sales.branch_id == Branch.id)
        .filter(Sales.id == sales_id)
        .first()
    )
    
    if not result:
        return None
    
    sales, worker_username, branch_name = result
    
    # Convert to dictionary with all fields
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
        "worker_username": worker_username,
        "branch_name": branch_name
    }
    
    return sales_dict