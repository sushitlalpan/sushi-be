"""
Branch CRUD operations.

This module provides Create, Read, Update, Delete operations
for Branch model management.
"""

from uuid import UUID
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from backend.fastapi.models.branch import Branch
from backend.fastapi.models.user import User
from backend.fastapi.models.payroll import Payroll
from backend.fastapi.schemas.branch import BranchCreate, BranchUpdate


def create_branch(db: Session, branch_data: BranchCreate) -> Branch:
    """
    Create a new branch.
    
    Args:
        db: Database session
        branch_data: Branch creation data
        
    Returns:
        Created branch instance
        
    Raises:
        HTTPException: If branch name already exists
    """
    # Check if branch name already exists
    existing_branch = get_branch_by_name(db, branch_data.name)
    if existing_branch:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Branch with name '{branch_data.name}' already exists"
        )
    
    # Create new branch
    db_branch = Branch(
        name=branch_data.name
    )
    
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    
    return db_branch


def get_branch(db: Session, branch_id: UUID) -> Optional[Branch]:
    """
    Get a branch by ID (excludes soft-deleted branches).
    
    Args:
        db: Database session
        branch_id: Branch unique identifier
        
    Returns:
        Branch instance if found and not deleted, None otherwise
    """
    return db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.deleted_at.is_(None)
    ).first()


def get_branch_by_name(db: Session, name: str) -> Optional[Branch]:
    """
    Get a branch by name (excludes soft-deleted branches).
    
    Args:
        db: Database session
        name: Branch name
        
    Returns:
        Branch instance if found and not deleted, None otherwise
    """
    return db.query(Branch).filter(
        Branch.name == name,
        Branch.deleted_at.is_(None)
    ).first()


def get_branches(db: Session, skip: int = 0, limit: int = 100) -> List[Branch]:
    """
    Get a list of branches with pagination (excludes soft-deleted branches).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of branch instances (excluding soft-deleted)
    """
    return db.query(Branch).filter(
        Branch.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()


def get_branches_count(db: Session) -> int:
    """
    Get total count of branches (excludes soft-deleted branches).
    
    Args:
        db: Database session
        
    Returns:
        Total number of non-deleted branches
    """
    return db.query(Branch).filter(
        Branch.deleted_at.is_(None)
    ).count()


def update_branch(db: Session, branch_id: UUID, branch_update: BranchUpdate) -> Optional[Branch]:
    """
    Update an existing branch.
    
    Args:
        db: Database session
        branch_id: Branch unique identifier
        branch_update: Branch update data
        
    Returns:
        Updated branch instance if found, None otherwise
        
    Raises:
        HTTPException: If new branch name already exists
    """
    # Get existing branch
    db_branch = get_branch(db, branch_id)
    if not db_branch:
        return None
    
    # Check if new name conflicts with existing branch
    if branch_update.name and branch_update.name != db_branch.name:
        existing_branch = get_branch_by_name(db, branch_update.name)
        if existing_branch:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Branch with name '{branch_update.name}' already exists"
            )
    
    # Update fields
    update_data = branch_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_branch, field, value)
    
    db.commit()
    db.refresh(db_branch)
    
    return db_branch


def delete_branch(db: Session, branch_id: UUID) -> bool:
    """
    Soft delete a branch (sets deleted_at timestamp).
    
    Args:
        db: Database session
        branch_id: Branch unique identifier
        
    Returns:
        True if branch was soft deleted, False if not found
        
    Raises:
        HTTPException: If branch has associated non-deleted users
    """
    # Get existing branch
    db_branch = get_branch(db, branch_id)
    if not db_branch:
        return False
    
    # Check if branch has non-deleted users
    user_count = db.query(User).filter(
        User.branch_id == branch_id,
        User.deleted_at.is_(None)
    ).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete branch with {user_count} active users. "
                   "Please reassign or delete users first."
        )
    
    # Soft delete branch: set deleted_at timestamp
    db_branch.deleted_at = datetime.utcnow()
    db.commit()
    
    return True


def get_branch_with_stats(db: Session, branch_id: UUID) -> Optional[dict]:
    """
    Get branch with user and payroll statistics.
    
    Args:
        db: Database session
        branch_id: Branch unique identifier
        
    Returns:
        Dictionary with branch info and stats, None if not found
    """
    # Get branch
    branch = get_branch(db, branch_id)
    if not branch:
        return None
    
    # Get statistics
    user_count = db.query(User).filter(
        User.branch_id == branch_id,
        User.deleted_at.is_(None)
    ).count()
    payroll_count = db.query(Payroll).filter(Payroll.branch_id == branch_id).count()
    
    return {
        "id": branch.id,
        "name": branch.name,
        "user_count": user_count,
        "payroll_records_count": payroll_count
    }


def get_branches_with_stats(db: Session, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Get branches with statistics.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of dictionaries with branch info and stats
    """
    # Get branches with user and payroll counts
    results = (
        db.query(
            Branch.id,
            Branch.name,
            func.count(User.id.distinct()).label("user_count"),
            func.count(Payroll.id.distinct()).label("payroll_records_count")
        )
        .outerjoin(User, Branch.id == User.branch_id)
        .outerjoin(Payroll, Branch.id == Payroll.branch_id)
        .group_by(Branch.id, Branch.name)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": result.id,
            "name": result.name,
            "user_count": result.user_count or 0,
            "payroll_records_count": result.payroll_records_count or 0
        }
        for result in results
    ]


def search_branches(db: Session, query: str, skip: int = 0, limit: int = 100) -> List[Branch]:
    """
    Search branches by name (excludes soft-deleted branches).
    
    Args:
        db: Database session
        query: Search query for branch name
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of matching branch instances
    """
    return (
        db.query(Branch)
        .filter(
            Branch.name.ilike(f"%{query}%"),
            Branch.deleted_at.is_(None)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )