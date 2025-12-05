"""
Payroll CRUD operations.

This module provides Create, Read, Update, Delete operations
for Payroll model management and payroll reporting.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc, asc
from fastapi import HTTPException, status

from backend.fastapi.models.payroll import Payroll
from backend.fastapi.models.user import User
from backend.fastapi.models.branch import Branch
from backend.fastapi.schemas.payroll import PayrollCreate, PayrollUpdate


def create_payroll(db: Session, payroll_data: PayrollCreate) -> Payroll:
    """
    Create a new payroll record.
    
    Args:
        db: Database session
        payroll_data: Payroll creation data
        
    Returns:
        Created payroll instance
        
    Raises:
        HTTPException: If worker or branch doesn't exist
    """
    # Validate worker exists
    worker = db.query(User).filter(
        User.id == payroll_data.worker_id,
        User.deleted_at.is_(None)
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {payroll_data.worker_id} not found"
        )
    
    # Validate branch exists
    branch = db.query(Branch).filter(
        Branch.id == payroll_data.branch_id,
        Branch.deleted_at.is_(None)
    ).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch with ID {payroll_data.branch_id} not found"
        )
    
    # Create new payroll record
    db_payroll = Payroll(
        date=payroll_data.date,
        worker_id=payroll_data.worker_id,
        branch_id=payroll_data.branch_id,
        days_worked=payroll_data.days_worked,
        amount=payroll_data.amount,
        payroll_type=payroll_data.payroll_type,
        notes=payroll_data.notes,
        review_state=payroll_data.review_state,
        review_observations=payroll_data.review_observations
    )
    
    db.add(db_payroll)
    db.commit()
    db.refresh(db_payroll)
    
    return db_payroll


def get_payroll(db: Session, payroll_id: UUID) -> Optional[Payroll]:
    """
    Get a payroll record by ID.
    
    Args:
        db: Database session
        payroll_id: Payroll unique identifier
        
    Returns:
        Payroll instance if found, None otherwise
    """
    return (
        db.query(Payroll)
        .options(joinedload(Payroll.worker), joinedload(Payroll.branch))
        .filter(Payroll.id == payroll_id)
        .first()
    )


def get_payrolls(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    worker_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    payroll_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    order_by: str = "date_desc"
) -> List[Payroll]:
    """
    Get a list of payroll records with filtering and pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        worker_id: Filter by specific worker
        branch_id: Filter by specific branch
        payroll_type: Filter by payroll type
        start_date: Filter records from this date
        end_date: Filter records until this date
        order_by: Sorting order (date_desc, date_asc, amount_desc, amount_asc)
        
    Returns:
        List of payroll instances
    """
    query = (
        db.query(Payroll)
        .options(joinedload(Payroll.worker), joinedload(Payroll.branch))
    )
    
    # Apply filters
    if worker_id:
        query = query.filter(Payroll.worker_id == worker_id)
    
    if branch_id:
        query = query.filter(Payroll.branch_id == branch_id)
    
    if payroll_type:
        query = query.filter(Payroll.payroll_type == payroll_type)
    
    if start_date:
        query = query.filter(func.date(Payroll.date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Payroll.date) <= end_date)
    
    # Apply ordering
    if order_by == "date_desc":
        query = query.order_by(desc(Payroll.date))
    elif order_by == "date_asc":
        query = query.order_by(asc(Payroll.date))
    elif order_by == "amount_desc":
        query = query.order_by(desc(Payroll.amount))
    elif order_by == "amount_asc":
        query = query.order_by(asc(Payroll.amount))
    else:
        query = query.order_by(desc(Payroll.date))  # Default
    
    return query.offset(skip).limit(limit).all()


def get_payrolls_count(
    db: Session,
    worker_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    payroll_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> int:
    """
    Get total count of payroll records with same filters.
    
    Args:
        db: Database session
        worker_id: Filter by specific worker
        branch_id: Filter by specific branch
        payroll_type: Filter by payroll type
        start_date: Filter records from this date
        end_date: Filter records until this date
        
    Returns:
        Total number of matching payroll records
    """
    query = db.query(Payroll)
    
    # Apply same filters as get_payrolls
    if worker_id:
        query = query.filter(Payroll.worker_id == worker_id)
    
    if branch_id:
        query = query.filter(Payroll.branch_id == branch_id)
    
    if payroll_type:
        query = query.filter(Payroll.payroll_type == payroll_type)
    
    if start_date:
        query = query.filter(func.date(Payroll.date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Payroll.date) <= end_date)
    
    return query.count()


def update_payroll(db: Session, payroll_id: UUID, payroll_update: PayrollUpdate) -> Optional[Payroll]:
    """
    Update an existing payroll record.
    
    Args:
        db: Database session
        payroll_id: Payroll unique identifier
        payroll_update: Payroll update data
        
    Returns:
        Updated payroll instance if found, None otherwise
        
    Raises:
        HTTPException: If worker or branch doesn't exist
    """
    # Get existing payroll
    db_payroll = get_payroll(db, payroll_id)
    if not db_payroll:
        return None
    
    # Validate worker if being updated
    if payroll_update.worker_id:
        worker = db.query(User).filter(
            User.id == payroll_update.worker_id,
            User.deleted_at.is_(None)
        ).first()
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID {payroll_update.worker_id} not found"
            )
    
    # Validate branch if being updated
    if payroll_update.branch_id:
        branch = db.query(Branch).filter(
            Branch.id == payroll_update.branch_id,
            Branch.deleted_at.is_(None)
        ).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch with ID {payroll_update.branch_id} not found"
            )
    
    # Update fields
    update_data = payroll_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_payroll, field, value)
    
    db.commit()
    db.refresh(db_payroll)
    
    return db_payroll


def get_payroll_by_review_state(
    db: Session, 
    review_state: str, 
    skip: int = 0, 
    limit: int = 100,
    branch_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None
) -> List[Payroll]:
    """
    Get payroll records filtered by review state.
    
    Args:
        db: Database session
        review_state: Review state to filter by (pending, approved, rejected)
        skip: Number of records to skip
        limit: Maximum number of records to return
        branch_id: Optional branch filter
        worker_id: Optional worker filter
        
    Returns:
        List of payroll records matching the review state
    """
    query = (
        db.query(Payroll)
        .options(joinedload(Payroll.worker), joinedload(Payroll.branch))
        .filter(Payroll.review_state == review_state.lower())
        .order_by(desc(Payroll.created_at))
    )
    
    if branch_id:
        query = query.filter(Payroll.branch_id == branch_id)
    
    if worker_id:
        query = query.filter(Payroll.worker_id == worker_id)
    
    return query.offset(skip).limit(limit).all()


def count_payroll_by_review_state(
    db: Session, 
    review_state: str,
    branch_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None
) -> int:
    """
    Count payroll records by review state.
    
    Args:
        db: Database session
        review_state: Review state to count (pending, approved, rejected)
        branch_id: Optional branch filter
        worker_id: Optional worker filter
        
    Returns:
        Number of payroll records matching the review state
    """
    query = db.query(Payroll).filter(Payroll.review_state == review_state.lower())
    
    if branch_id:
        query = query.filter(Payroll.branch_id == branch_id)
    
    if worker_id:
        query = query.filter(Payroll.worker_id == worker_id)
    
    return query.count()


def get_payroll_by_review_state(db: Session, review_state: str, skip: int = 0, limit: int = 100) -> List[Payroll]:
    """
    Get payroll records filtered by review state.
    
    Args:
        db: Database session
        review_state: Review state to filter by (pending, approved, rejected)
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of payroll records with the specified review state
    """
    return (
        db.query(Payroll)
        .options(joinedload(Payroll.worker), joinedload(Payroll.branch))
        .filter(Payroll.review_state == review_state.lower())
        .order_by(desc(Payroll.date))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_payroll_pending_review(db: Session, skip: int = 0, limit: int = 100) -> List[Payroll]:
    """
    Get payroll records that are pending review.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of payroll records pending review
    """
    return get_payroll_by_review_state(db, "pending", skip, limit)


def update_payroll_review_status(db: Session, payroll_id: UUID, review_state: str, review_observations: Optional[str] = None) -> Optional[Payroll]:
    """
    Update the review status of a payroll record.
    
    Args:
        db: Database session
        payroll_id: Payroll unique identifier
        review_state: New review state (pending, approved, rejected)
        review_observations: Optional review observations
        
    Returns:
        Updated payroll instance if found, None otherwise
    """
    db_payroll = get_payroll(db, payroll_id)
    if not db_payroll:
        return None
    
    db_payroll.review_state = review_state.lower()
    if review_observations is not None:
        db_payroll.review_observations = review_observations
    
    db.commit()
    db.refresh(db_payroll)
    
    return db_payroll


def delete_payroll(db: Session, payroll_id: UUID) -> bool:
    """
    Delete a payroll record.
    
    Args:
        db: Database session
        payroll_id: Payroll unique identifier
        
    Returns:
        True if payroll was deleted, False if not found
    """
    db_payroll = get_payroll(db, payroll_id)
    if not db_payroll:
        return False
    
    db.delete(db_payroll)
    db.commit()
    
    return True


def get_worker_payroll_summary(
    db: Session,
    worker_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Get payroll summary for a specific worker.
    
    Args:
        db: Database session
        worker_id: Worker unique identifier
        start_date: Filter records from this date
        end_date: Filter records until this date
        
    Returns:
        Dictionary with payroll summary or None if worker not found
    """
    # Check if worker exists
    worker = db.query(User).filter(
        User.id == worker_id,
        User.deleted_at.is_(None)
    ).first()
    if not worker:
        return None
    
    # Build query with filters
    query = db.query(Payroll).filter(Payroll.worker_id == worker_id)
    
    if start_date:
        query = query.filter(func.date(Payroll.date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Payroll.date) <= end_date)
    
    # Get aggregated data
    result = (
        query.with_entities(
            func.sum(Payroll.amount).label("total_amount"),
            func.sum(Payroll.days_worked).label("total_days"),
            func.count(Payroll.id).label("record_count"),
            func.max(Payroll.date).label("last_payment_date")
        )
        .first()
    )
    
    return {
        "worker_id": worker_id,
        "worker_username": worker.username,
        "total_amount": result.total_amount or Decimal("0.00"),
        "total_days": result.total_days or 0,
        "record_count": result.record_count or 0,
        "last_payment_date": result.last_payment_date
    }


def get_payroll_period_report(
    db: Session,
    start_date: date,
    end_date: date,
    branch_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Generate payroll report for a specific period.
    
    Args:
        db: Database session
        start_date: Start date of the period
        end_date: End date of the period
        branch_id: Filter by specific branch (optional)
        
    Returns:
        Dictionary with period report data
    """
    # Base query with date filters
    query = db.query(Payroll).filter(
        and_(
            func.date(Payroll.date) >= start_date,
            func.date(Payroll.date) <= end_date
        )
    )
    
    if branch_id:
        query = query.filter(Payroll.branch_id == branch_id)
    
    # Get total amount and record count
    totals = (
        query.with_entities(
            func.sum(Payroll.amount).label("total_amount"),
            func.count(Payroll.id).label("total_records")
        )
        .first()
    )
    
    # Get breakdown by payroll type
    by_type = {}
    type_results = (
        query.with_entities(
            Payroll.payroll_type,
            func.sum(Payroll.amount).label("type_total")
        )
        .group_by(Payroll.payroll_type)
        .all()
    )
    
    for type_result in type_results:
        by_type[type_result.payroll_type] = str(type_result.type_total)
    
    # Get breakdown by branch
    by_branch = {}
    branch_query = (
        db.query(Payroll)
        .join(Branch)
        .filter(
            and_(
                func.date(Payroll.date) >= start_date,
                func.date(Payroll.date) <= end_date
            )
        )
    )
    
    if branch_id:
        branch_query = branch_query.filter(Payroll.branch_id == branch_id)
    
    branch_results = (
        branch_query.with_entities(
            Branch.name,
            func.sum(Payroll.amount).label("branch_total")
        )
        .group_by(Branch.name)
        .all()
    )
    
    for branch_result in branch_results:
        by_branch[branch_result.name] = str(branch_result.branch_total)
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_amount": totals.total_amount or Decimal("0.00"),
        "total_records": totals.total_records or 0,
        "by_type": by_type,
        "by_branch": by_branch
    }


def get_payroll_with_details(db: Session, payroll_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Get payroll record with worker and branch details.
    
    Args:
        db: Database session
        payroll_id: Payroll unique identifier
        
    Returns:
        Dictionary with payroll and related details or None if not found
    """
    result = (
        db.query(Payroll, User.username, Branch.name)
        .join(User, Payroll.worker_id == User.id)
        .join(Branch, Payroll.branch_id == Branch.id)
        .filter(Payroll.id == payroll_id)
        .first()
    )
    
    if not result:
        return None
    
    payroll, worker_username, branch_name = result
    
    return {
        "id": payroll.id,
        "date": payroll.date,
        "worker_id": payroll.worker_id,
        "branch_id": payroll.branch_id,
        "days_worked": payroll.days_worked,
        "amount": payroll.amount,
        "payroll_type": payroll.payroll_type,
        "notes": payroll.notes,
        "created_at": payroll.created_at,
        "worker_username": worker_username,
        "branch_name": branch_name
    }