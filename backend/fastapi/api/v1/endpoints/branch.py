"""
Branch management API endpoints.

This module provides FastAPI endpoints for branch management operations
including creating, reading, updating, and deleting branches.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.admin import Admin
from backend.fastapi.schemas.branch import (
    BranchCreate, BranchRead, BranchUpdate, BranchWithStats, BranchListResponse
)
from backend.fastapi.crud.branch import (
    create_branch, get_branch, get_branches, get_branches_count,
    update_branch, delete_branch, get_branch_with_stats,
    get_branches_with_stats, search_branches
)
from backend.security.dependencies import RequireActiveAdmin


router = APIRouter(tags=["branch-management"])


@router.post("/", response_model=BranchRead, summary="Create New Branch")
async def create_new_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Create a new branch (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **name**: Unique branch name (2-100 characters)
    
    **Returns:**
    - Branch information with generated ID
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **409**: Branch name already exists
    - **422**: Validation errors
    """
    try:
        branch = create_branch(db, branch_data)
        return BranchRead.model_validate(branch)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create branch: {str(e)}"
        )


@router.get("/", response_model=BranchListResponse, summary="List All Branches")
async def list_branches(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    search: Optional[str] = Query(None, description="Search term for branch names"),
    include_stats: bool = Query(False, description="Include user and payroll statistics"),
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get list of all branches (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Optional search term for branch names
    - **include_stats**: Whether to include user and payroll counts
    
    **Returns:**
    - Paginated list of branches with total count
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    """
    try:
        if search:
            branches = search_branches(db, search, skip=skip, limit=limit)
            total = len(search_branches(db, search, skip=0, limit=1000))  # Get total for searched results
        elif include_stats:
            branch_data = get_branches_with_stats(db, skip=skip, limit=limit)
            branches = [BranchWithStats.model_validate(branch) for branch in branch_data]
            total = get_branches_count(db)
        else:
            branches = get_branches(db, skip=skip, limit=limit)
            total = get_branches_count(db)
            branches = [BranchRead.model_validate(branch) for branch in branches]
        
        return BranchListResponse(
            branches=branches,
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve branches: {str(e)}"
        )


@router.get("/{branch_id}", response_model=BranchWithStats, summary="Get Branch by ID")
async def get_branch_by_id(
    branch_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get specific branch by ID with statistics (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **branch_id**: UUID of the branch
    
    **Returns:**
    - Branch information with user and payroll statistics
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Branch not found
    - **422**: Invalid UUID format
    """
    branch_data = get_branch_with_stats(db, branch_id)
    if not branch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )
    
    return BranchWithStats.model_validate(branch_data)


@router.put("/{branch_id}", response_model=BranchRead, summary="Update Branch")
async def update_branch_by_id(
    branch_id: UUID,
    branch_update: BranchUpdate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Update branch information (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **branch_id**: UUID of branch to update
    - **name**: New branch name (optional)
    
    **Returns:**
    - Updated branch information
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Branch not found
    - **409**: Branch name already exists
    - **422**: Invalid data format
    """
    try:
        updated_branch = update_branch(db, branch_id, branch_update)
        if not updated_branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
        
        return BranchRead.model_validate(updated_branch)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update branch: {str(e)}"
        )


@router.delete("/{branch_id}", summary="Delete Branch")
async def delete_branch_by_id(
    branch_id: UUID,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Delete branch (admin-only endpoint).
    
    **Permissions:** Requires active admin authentication
    
    **Security Notes:**
    - Cannot delete branches with assigned users
    - Cannot delete branches with payroll records
    - Consider archiving instead of deleting
    
    **Parameters:**
    - **branch_id**: UUID of branch to delete
    
    **Returns:**
    - Success message with deleted branch ID
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: Branch not found
    - **409**: Branch has associated users or payroll records
    """
    try:
        success = delete_branch(db, branch_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
        
        return {"message": "Branch deleted successfully", "branch_id": str(branch_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete branch: {str(e)}"
        )


# Read-only endpoint for users to see available branches
@router.get("/public/list", response_model=List[BranchRead], summary="List Branches (Read-Only)")
async def list_branches_public(
    db: Session = Depends(get_sync_db)
):
    """
    Get list of all branches (public read-only endpoint).
    
    **Note:** This is a public endpoint that doesn't require authentication.
    It's useful for user registration forms and other public interfaces
    where users need to see available branches.
    
    **Returns:**
    - List of all branches (name and ID only)
    
    **Errors:**
    - **500**: Server error
    """
    try:
        branches = get_branches(db, skip=0, limit=1000)  # Get all branches
        return [BranchRead.model_validate(branch) for branch in branches]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve branches: {str(e)}"
        )