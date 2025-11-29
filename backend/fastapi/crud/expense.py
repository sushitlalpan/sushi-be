"""
Expense CRUD operations.

This module provides Create, Read, Update, Delete operations
for Expense model management and comprehensive expense reporting.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc, asc, or_
from fastapi import HTTPException, status

from backend.fastapi.models.expense import Expense
from backend.fastapi.models.user import User
from backend.fastapi.models.branch import Branch
from backend.fastapi.schemas.expense import ExpenseCreate, ExpenseUpdate


def create_expense(db: Session, expense_data: ExpenseCreate) -> Expense:
    """
    Create a new expense record with automatic calculations.
    
    Args:
        db: Database session
        expense_data: Expense creation data
        
    Returns:
        Created expense instance with calculated unit cost
        
    Raises:
        HTTPException: If worker or branch doesn't exist
    """
    # Validate worker exists
    worker = db.query(User).filter(User.id == expense_data.worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {expense_data.worker_id} not found"
        )
    
    # Validate branch exists
    branch = db.query(Branch).filter(Branch.id == expense_data.branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch with ID {expense_data.branch_id} not found"
        )
    
    # Create new expense record
    db_expense = Expense(
        worker_id=expense_data.worker_id,
        branch_id=expense_data.branch_id,
        expense_date=expense_data.expense_date,
        expense_description=expense_data.expense_description,
        vendor_payee=expense_data.vendor_payee,
        expense_category=expense_data.expense_category,
        quantity=expense_data.quantity,
        unit_of_measure=expense_data.unit_of_measure,
        total_amount=expense_data.total_amount,
        tax_amount=expense_data.tax_amount,
        receipt_number=expense_data.receipt_number,
        payment_method=expense_data.payment_method,
        is_reimbursable=expense_data.is_reimbursable,
        notes=expense_data.notes,
        review_state=expense_data.review_state,
        review_observations=expense_data.review_observations
    )
    
    # Calculate unit cost
    db_expense.calculate_unit_cost()
    
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    
    return db_expense


def get_expense(db: Session, expense_id: UUID) -> Optional[Expense]:
    """
    Get an expense record by ID.
    
    Args:
        db: Database session
        expense_id: Expense unique identifier
        
    Returns:
        Expense instance if found, None otherwise
    """
    return (
        db.query(Expense)
        .options(joinedload(Expense.worker), joinedload(Expense.branch))
        .filter(Expense.id == expense_id)
        .first()
    )


def get_expenses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    worker_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    expense_category: Optional[str] = None,
    vendor_payee: Optional[str] = None,
    is_reimbursable: Optional[str] = None,
    payment_method: Optional[str] = None,
    has_receipt: Optional[bool] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    order_by: str = "date_desc"
) -> List[Expense]:
    """
    Get a list of expense records with filtering and pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        worker_id: Filter by specific worker
        branch_id: Filter by specific branch
        start_date: Filter records from this date
        end_date: Filter records until this date
        expense_category: Filter by expense category
        vendor_payee: Filter by vendor/payee (partial match)
        is_reimbursable: Filter by reimbursable status
        payment_method: Filter by payment method
        has_receipt: Filter by receipt presence
        min_amount: Filter by minimum amount
        max_amount: Filter by maximum amount
        order_by: Sorting order
        
    Returns:
        List of expense instances
    """
    query = (
        db.query(Expense)
        .options(joinedload(Expense.worker), joinedload(Expense.branch))
    )
    
    # Apply filters
    if worker_id:
        query = query.filter(Expense.worker_id == worker_id)
    
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    if expense_category:
        query = query.filter(Expense.expense_category.ilike(f"%{expense_category.lower()}%"))
    
    if vendor_payee:
        query = query.filter(Expense.vendor_payee.ilike(f"%{vendor_payee}%"))
    
    if is_reimbursable:
        query = query.filter(Expense.is_reimbursable == is_reimbursable.lower())
    
    if payment_method:
        query = query.filter(Expense.payment_method.ilike(f"%{payment_method}%"))
    
    if has_receipt is not None:
        if has_receipt:
            query = query.filter(and_(
                Expense.receipt_number.isnot(None),
                Expense.receipt_number != ""
            ))
        else:
            query = query.filter(or_(
                Expense.receipt_number.is_(None),
                Expense.receipt_number == ""
            ))
    
    if min_amount is not None:
        query = query.filter(Expense.total_amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(Expense.total_amount <= max_amount)
    
    # Apply ordering
    if order_by == "date_desc":
        query = query.order_by(desc(Expense.expense_date), desc(Expense.created_at))
    elif order_by == "date_asc":
        query = query.order_by(asc(Expense.expense_date), asc(Expense.created_at))
    elif order_by == "amount_desc":
        query = query.order_by(desc(Expense.total_amount))
    elif order_by == "amount_asc":
        query = query.order_by(asc(Expense.total_amount))
    elif order_by == "category":
        query = query.order_by(asc(Expense.expense_category), desc(Expense.expense_date))
    elif order_by == "vendor":
        query = query.order_by(asc(Expense.vendor_payee), desc(Expense.expense_date))
    else:
        query = query.order_by(desc(Expense.expense_date), desc(Expense.created_at))
    
    return query.offset(skip).limit(limit).all()


def get_expenses_count(
    db: Session,
    worker_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    expense_category: Optional[str] = None,
    vendor_payee: Optional[str] = None,
    is_reimbursable: Optional[str] = None,
    payment_method: Optional[str] = None,
    has_receipt: Optional[bool] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None
) -> int:
    """
    Get total count of expense records with same filters.
    
    Args:
        db: Database session
        Same filters as get_expenses
        
    Returns:
        Total number of matching expense records
    """
    query = db.query(Expense)
    
    # Apply same filters as get_expenses
    if worker_id:
        query = query.filter(Expense.worker_id == worker_id)
    
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    if expense_category:
        query = query.filter(Expense.expense_category.ilike(f"%{expense_category.lower()}%"))
    
    if vendor_payee:
        query = query.filter(Expense.vendor_payee.ilike(f"%{vendor_payee}%"))
    
    if is_reimbursable:
        query = query.filter(Expense.is_reimbursable == is_reimbursable.lower())
    
    if payment_method:
        query = query.filter(Expense.payment_method.ilike(f"%{payment_method}%"))
    
    if has_receipt is not None:
        if has_receipt:
            query = query.filter(and_(
                Expense.receipt_number.isnot(None),
                Expense.receipt_number != ""
            ))
        else:
            query = query.filter(or_(
                Expense.receipt_number.is_(None),
                Expense.receipt_number == ""
            ))
    
    if min_amount is not None:
        query = query.filter(Expense.total_amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(Expense.total_amount <= max_amount)
    
    return query.count()


def update_expense(db: Session, expense_id: UUID, expense_update: ExpenseUpdate) -> Optional[Expense]:
    """
    Update an existing expense record.
    
    Args:
        db: Database session
        expense_id: Expense unique identifier
        expense_update: Expense update data
        
    Returns:
        Updated expense instance if found, None otherwise
        
    Raises:
        HTTPException: If worker or branch doesn't exist
    """
    # Get existing expense record
    db_expense = get_expense(db, expense_id)
    if not db_expense:
        return None
    
    # Validate worker if being updated
    if expense_update.worker_id:
        worker = db.query(User).filter(User.id == expense_update.worker_id).first()
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID {expense_update.worker_id} not found"
            )
    
    # Validate branch if being updated
    if expense_update.branch_id:
        branch = db.query(Branch).filter(Branch.id == expense_update.branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch with ID {expense_update.branch_id} not found"
            )
    
    # Update fields
    update_data = expense_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_expense, field, value)
    
    # Recalculate unit cost if amount or quantity changed
    if 'total_amount' in update_data or 'quantity' in update_data:
        db_expense.calculate_unit_cost()
    
    db.commit()
    db.refresh(db_expense)
    
    return db_expense


def get_expenses_by_review_state(
    db: Session, 
    review_state: str, 
    skip: int = 0, 
    limit: int = 100,
    branch_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None
) -> List[Expense]:
    """
    Get expenses filtered by review state.
    
    Args:
        db: Database session
        review_state: Review state to filter by (pending, approved, rejected)
        skip: Number of records to skip
        limit: Maximum number of records to return
        branch_id: Optional branch filter
        worker_id: Optional worker filter
        
    Returns:
        List of expense records matching the review state
    """
    query = (
        db.query(Expense)
        .options(joinedload(Expense.worker), joinedload(Expense.branch))
        .filter(Expense.review_state == review_state.lower())
        .order_by(desc(Expense.created_at))
    )
    
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    if worker_id:
        query = query.filter(Expense.worker_id == worker_id)
    
    return query.offset(skip).limit(limit).all()


def count_expenses_by_review_state(
    db: Session, 
    review_state: str,
    branch_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None
) -> int:
    """
    Count expenses by review state.
    
    Args:
        db: Database session
        review_state: Review state to count (pending, approved, rejected)
        branch_id: Optional branch filter
        worker_id: Optional worker filter
        
    Returns:
        Number of expense records matching the review state
    """
    query = db.query(Expense).filter(Expense.review_state == review_state.lower())
    
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    if worker_id:
        query = query.filter(Expense.worker_id == worker_id)
    
    return query.count()


def get_expenses_by_review_state(db: Session, review_state: str, skip: int = 0, limit: int = 100) -> List[Expense]:
    """
    Get expenses filtered by review state.
    
    Args:
        db: Database session
        review_state: Review state to filter by (pending, approved, rejected)
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of expense records with the specified review state
    """
    return (
        db.query(Expense)
        .options(joinedload(Expense.worker), joinedload(Expense.branch))
        .filter(Expense.review_state == review_state.lower())
        .order_by(desc(Expense.expense_date))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_expenses_pending_review(db: Session, skip: int = 0, limit: int = 100) -> List[Expense]:
    """
    Get expenses that are pending review.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of expense records pending review
    """
    return get_expenses_by_review_state(db, "pending", skip, limit)


def update_expense_review_status(db: Session, expense_id: UUID, review_state: str, review_observations: Optional[str] = None) -> Optional[Expense]:
    """
    Update the review status of an expense.
    
    Args:
        db: Database session
        expense_id: Expense unique identifier
        review_state: New review state (pending, approved, rejected)
        review_observations: Optional review observations
        
    Returns:
        Updated expense instance if found, None otherwise
    """
    db_expense = get_expense(db, expense_id)
    if not db_expense:
        return None
    
    db_expense.review_state = review_state.lower()
    if review_observations is not None:
        db_expense.review_observations = review_observations
    
    db.commit()
    db.refresh(db_expense)
    
    return db_expense


def delete_expense(db: Session, expense_id: UUID) -> bool:
    """
    Delete an expense record.
    
    Args:
        db: Database session
        expense_id: Expense unique identifier
        
    Returns:
        True if expense record was deleted, False if not found
    """
    db_expense = get_expense(db, expense_id)
    if not db_expense:
        return False
    
    db.delete(db_expense)
    db.commit()
    
    return True


def get_expenses_period_summary(
    db: Session,
    start_date: date,
    end_date: date,
    branch_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Get comprehensive expense summary for a period.
    
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
    query = db.query(Expense).filter(
        and_(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        )
    )
    
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    if worker_id:
        query = query.filter(Expense.worker_id == worker_id)
    
    # Get aggregated totals
    totals = (
        query.with_entities(
            func.sum(Expense.total_amount).label("total_expenses"),
            func.sum(Expense.tax_amount).label("total_tax"),
            func.count(Expense.id).label("total_count"),
            func.avg(Expense.total_amount).label("average_expense")
        )
        .first()
    )
    
    # Get reimbursable amounts
    reimbursable_totals = (
        query.filter(Expense.is_reimbursable.in_(['yes', 'pending']))
        .with_entities(
            func.sum(Expense.total_amount).label("total_reimbursable")
        )
        .first()
    )
    
    pending_reimbursement = (
        query.filter(Expense.is_reimbursable == 'pending')
        .with_entities(
            func.sum(Expense.total_amount).label("pending_reimbursement")
        )
        .first()
    )
    
    # Get breakdown by category
    by_category = {}
    category_results = (
        query.with_entities(
            Expense.expense_category,
            func.sum(Expense.total_amount).label("category_total")
        )
        .group_by(Expense.expense_category)
        .all()
    )
    
    for category_result in category_results:
        by_category[category_result.expense_category] = category_result.category_total
    
    # Get breakdown by payment method
    by_payment_method = {}
    payment_results = (
        query.with_entities(
            Expense.payment_method,
            func.sum(Expense.total_amount).label("payment_total")
        )
        .group_by(Expense.payment_method)
        .all()
    )
    
    for payment_result in payment_results:
        by_payment_method[payment_result.payment_method or 'unknown'] = payment_result.payment_total
    
    return {
        "total_expenses": totals.total_expenses or Decimal("0"),
        "total_count": totals.total_count or 0,
        "total_tax": totals.total_tax or Decimal("0"),
        "total_reimbursable": reimbursable_totals.total_reimbursable or Decimal("0"),
        "pending_reimbursement": pending_reimbursement.pending_reimbursement or Decimal("0"),
        "average_expense": totals.average_expense or Decimal("0"),
        "by_category": by_category,
        "by_payment_method": by_payment_method
    }


def get_expenses_period_report(
    db: Session,
    start_date: date,
    end_date: date,
    branch_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive expense report for a period.
    
    Args:
        db: Database session
        start_date: Start date of the period
        end_date: End date of the period
        branch_id: Filter by specific branch (optional)
        
    Returns:
        Dictionary with comprehensive report data
    """
    # Get overall summary
    summary = get_expenses_period_summary(db, start_date, end_date, branch_id)
    
    # Base query for breakdowns
    base_query = db.query(Expense).filter(
        and_(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        )
    )
    
    if branch_id:
        base_query = base_query.filter(Expense.branch_id == branch_id)
    
    # Get breakdown by branch
    by_branch = {}
    if not branch_id:  # Only get branch breakdown if not filtering by branch
        branch_results = (
            base_query.join(Branch)
            .with_entities(
                Branch.name,
                func.sum(Expense.total_amount).label("branch_total")
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
            func.sum(Expense.total_amount).label("worker_total")
        )
        .group_by(User.username)
        .all()
    )
    
    for worker_result in worker_results:
        by_worker[worker_result.username] = str(worker_result.worker_total)
    
    # Get breakdown by category
    by_category = {}
    for category, amount in summary["by_category"].items():
        by_category[category] = str(amount)
    
    # Get daily totals
    daily_totals = []
    daily_results = (
        base_query.with_entities(
            Expense.expense_date,
            func.sum(Expense.total_amount).label("daily_total")
        )
        .group_by(Expense.expense_date)
        .order_by(Expense.expense_date)
        .all()
    )
    
    for daily_result in daily_results:
        daily_totals.append({
            "date": daily_result.expense_date.isoformat(),
            "total": str(daily_result.daily_total)
        })
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "by_branch": by_branch,
        "by_worker": by_worker,
        "by_category": by_category,
        "daily_totals": daily_totals
    }


def get_reimbursement_report(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    branch_id: Optional[UUID] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate reimbursement analysis report.
    
    Args:
        db: Database session
        start_date: Filter from this date (optional)
        end_date: Filter until this date (optional)
        branch_id: Filter by specific branch (optional)
        status_filter: Filter by reimbursement status (optional)
        
    Returns:
        Dictionary with reimbursement analysis
    """
    # Base query for reimbursable expenses
    query = db.query(Expense).filter(Expense.is_reimbursable.in_(['yes', 'pending']))
    
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    if status_filter:
        query = query.filter(Expense.is_reimbursable == status_filter.lower())
    
    # Get reimbursement statistics
    total_reimbursable = (
        query.with_entities(func.sum(Expense.total_amount))
        .scalar() or Decimal("0")
    )
    
    pending_amount = (
        query.filter(Expense.is_reimbursable == 'pending')
        .with_entities(func.sum(Expense.total_amount))
        .scalar() or Decimal("0")
    )
    
    reimbursed_amount = (
        query.filter(Expense.is_reimbursable == 'yes')
        .with_entities(func.sum(Expense.total_amount))
        .scalar() or Decimal("0")
    )
    
    pending_count = (
        query.filter(Expense.is_reimbursable == 'pending')
        .count()
    )
    
    # Get breakdown by worker
    by_worker = {}
    worker_results = (
        query.join(User)
        .with_entities(
            User.username,
            Expense.is_reimbursable,
            func.sum(Expense.total_amount).label("worker_total"),
            func.count(Expense.id).label("expense_count")
        )
        .group_by(User.username, Expense.is_reimbursable)
        .all()
    )
    
    for worker_result in worker_results:
        username = worker_result.username
        status = worker_result.is_reimbursable
        amount = worker_result.worker_total
        count = worker_result.expense_count
        
        if username not in by_worker:
            by_worker[username] = {
                "total_reimbursable": Decimal("0"),
                "pending": Decimal("0"),
                "reimbursed": Decimal("0"),
                "pending_count": 0,
                "total_count": 0
            }
        
        by_worker[username]["total_reimbursable"] += amount
        by_worker[username]["total_count"] += count
        
        if status == 'pending':
            by_worker[username]["pending"] = amount
            by_worker[username]["pending_count"] = count
        elif status == 'yes':
            by_worker[username]["reimbursed"] = amount
    
    # Get recent pending expense records
    expense_records = (
        query.filter(Expense.is_reimbursable == 'pending')
        .options(joinedload(Expense.worker), joinedload(Expense.branch))
        .order_by(desc(Expense.expense_date))
        .limit(50)
        .all()
    )
    
    return {
        "total_reimbursable": total_reimbursable,
        "pending_reimbursement": pending_amount,
        "reimbursed_amount": reimbursed_amount,
        "pending_count": pending_count,
        "by_worker": by_worker,
        "expense_records": expense_records
    }


def get_expense_with_details(db: Session, expense_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Get expense record with worker and branch details.
    
    Args:
        db: Database session
        expense_id: Expense unique identifier
        
    Returns:
        Dictionary with expense and related details or None if not found
    """
    result = (
        db.query(Expense, User.username, Branch.name)
        .join(User, Expense.worker_id == User.id)
        .join(Branch, Expense.branch_id == Branch.id)
        .filter(Expense.id == expense_id)
        .first()
    )
    
    if not result:
        return None
    
    expense, worker_username, branch_name = result
    
    # Convert to dictionary with all fields
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
        "created_at": expense.created_at,
        "updated_at": expense.updated_at,
        "worker_username": worker_username,
        "branch_name": branch_name,
        "net_amount": expense.net_amount,
        "has_receipt": expense.has_receipt,
        "is_pending_reimbursement": expense.is_pending_reimbursement
    }
    
    return expense_dict