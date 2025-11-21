"""
Time entry endpoints for clock-in/out functionality.

This module provides FastAPI endpoints for time tracking, including
clock-in/out operations, time reports, and attendance management.
"""

from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User
from backend.fastapi.models.admin import Admin
from backend.fastapi.schemas.time_entry import (
    TimeEntryRead, TimeEntryCreate, TimeEntryUpdate,
    ClockAction, ClockActionResponse, UserTimeStatus,
    TimeEntryListResponse, DailyTimeReport
)
from backend.fastapi.crud.time_entry import (
    create_time_entry, get_time_entry, get_user_time_entries,
    get_user_clock_status, get_current_session_duration,
    get_clocked_in_users, calculate_daily_hours,
    TimeEntryCRUD
)
from backend.fastapi.crud.user import get_user
from backend.security.dependencies import RequireActiveUser, RequireActiveAdmin


router = APIRouter(tags=["time-tracking"])


@router.post("/clock", response_model=ClockActionResponse, summary="Clock In/Out")
async def clock_action(
    clock_data: ClockAction,
    db: Session = Depends(get_sync_db),
    current_user: User = RequireActiveUser
):
    """
    Clock in or clock out for the authenticated user.
    
    **Permissions:** Requires active staff user authentication
    
    **Process:**
    1. Validates clock action (prevents double clock-in/out)
    2. Creates time entry record for audit trail
    3. Returns current status and entry details
    
    **Parameters:**
    - **action**: "clock_in" or "clock_out"
    - **method**: How the clock action is performed (optional)
    - **notes**: Optional notes for the entry
    - **timestamp**: Custom timestamp (defaults to current time)
    
    **Returns:**
    - Success status and operation details
    - Created time entry record
    - User's current clock status
    
    **Errors:**
    - **400**: Already clocked in/out or invalid action
    - **401**: Not authenticated
    - **403**: User account deactivated
    """
    try:
        # Create time entry data
        entry_data = TimeEntryCreate(
            entry_type=clock_data.action,
            timestamp=clock_data.timestamp,
            method=clock_data.method,
            notes=clock_data.notes
        )
        
        # Create the time entry
        time_entry = create_time_entry(db, current_user.id, entry_data)
        
        # Get current status
        current_status = get_user_clock_status(db, current_user.id)
        
        # Generate success message
        action_word = "in" if clock_data.action.value == "clock_in" else "out"
        message = f"Successfully clocked {action_word} at {time_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return ClockActionResponse(
            success=True,
            message=message,
            time_entry=TimeEntryRead.model_validate(time_entry),
            current_status=current_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clock operation failed: {str(e)}"
        )


@router.get("/status", response_model=UserTimeStatus, summary="Get Clock Status")
async def get_clock_status(
    db: Session = Depends(get_sync_db),
    current_user: User = RequireActiveUser
):
    """
    Get current clock status for authenticated user.
    
    **Permissions:** Requires active staff user authentication
    
    **Returns:**
    - Current clock-in/out status
    - Last clock-in and clock-out times
    - Current session duration (if clocked in)
    - Scheduled shift times
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: User account deactivated
    """
    # Get clock status and latest entries
    crud = TimeEntryCRUD(db)
    current_status = crud.get_user_clock_status(current_user.id)
    latest_clock_in, latest_clock_out = crud.get_latest_entries(current_user.id)
    
    # Calculate current session duration if clocked in
    session_duration = None
    if current_status == "clocked_in":
        session_duration = crud.get_current_session_duration(current_user.id)
    
    return UserTimeStatus(
        user_id=current_user.id,
        username=current_user.username,
        branch=current_user.branch,
        is_clocked_in=current_status == "clocked_in",
        last_clock_in=latest_clock_in.timestamp if latest_clock_in else None,
        last_clock_out=latest_clock_out.timestamp if latest_clock_out else None,
        current_session_duration=session_duration,
        scheduled_start=current_user.shift_start_time.strftime('%H:%M:%S') if current_user.shift_start_time else None,
        scheduled_end=current_user.shift_end_time.strftime('%H:%M:%S') if current_user.shift_end_time else None
    )


@router.get("/entries", response_model=TimeEntryListResponse, summary="Get Time Entries")
async def get_my_time_entries(
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter to this date"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    db: Session = Depends(get_sync_db),
    current_user: User = RequireActiveUser
):
    """
    Get time entries for authenticated user.
    
    **Permissions:** Requires active staff user authentication
    
    **Parameters:**
    - **start_date**: Filter entries from this date (optional)
    - **end_date**: Filter entries to this date (optional)  
    - **limit**: Maximum number of entries to return (1-1000)
    
    **Returns:**
    - List of user's time entries
    - Total count of entries
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: User account deactivated
    """
    entries = get_user_time_entries(db, current_user.id, start_date, end_date, limit)
    
    return TimeEntryListResponse(
        entries=[TimeEntryRead.model_validate(entry) for entry in entries],
        total=len(entries),
        user_id=current_user.id,
        date_range=f"{start_date} to {end_date}" if start_date and end_date else None
    )


@router.get("/daily-report", response_model=DailyTimeReport, summary="Get Daily Report")
async def get_daily_report(
    target_date: date = Query(..., description="Date to generate report for"),
    db: Session = Depends(get_sync_db),
    current_user: User = RequireActiveUser
):
    """
    Get daily time tracking report for authenticated user.
    
    **Permissions:** Requires active staff user authentication
    
    **Parameters:**
    - **target_date**: Date to generate report for (YYYY-MM-DD)
    
    **Returns:**
    - Complete daily time report
    - Total hours worked
    - Scheduled vs actual hours
    - All clock-in/out entries for the day
    
    **Errors:**
    - **401**: Not authenticated
    - **403**: User account deactivated
    """
    crud = TimeEntryCRUD(db)
    
    # Get all entries for the day
    daily_entries = crud.get_daily_entries(current_user.id, target_date)
    
    # Separate clock-ins and clock-outs
    clock_ins = [entry for entry in daily_entries if entry.is_clock_in]
    clock_outs = [entry for entry in daily_entries if entry.is_clock_out]
    
    # Calculate hours
    total_hours = crud.calculate_daily_hours(current_user.id, target_date)
    scheduled_hours = current_user.get_scheduled_shift_duration() / 60.0 if current_user.shift_start_time and current_user.shift_end_time else 0.0
    
    # Check if all entries are properly paired
    is_complete = len(clock_ins) == len(clock_outs)
    
    return DailyTimeReport(
        user_id=current_user.id,
        username=current_user.username,
        date=target_date.strftime('%Y-%m-%d'),
        clock_ins=[TimeEntryRead.model_validate(entry) for entry in clock_ins],
        clock_outs=[TimeEntryRead.model_validate(entry) for entry in clock_outs],
        total_hours=total_hours,
        scheduled_hours=scheduled_hours,
        overtime_hours=max(0.0, total_hours - scheduled_hours),
        is_complete=is_complete
    )


# Admin endpoints for time management
admin_router = APIRouter(prefix="/admin", tags=["admin-time-management"])


@admin_router.get("/clocked-in", response_model=List[UserTimeStatus], summary="Get Clocked-In Users")
async def get_clocked_in_users_admin(
    branch: Optional[str] = Query(None, description="Filter by branch"),
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get list of users currently clocked in (admin-only).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **branch**: Filter by specific branch (optional)
    
    **Returns:**
    - List of users currently clocked in with their status
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    """
    clocked_in_user_ids = get_clocked_in_users(db, branch)
    
    user_statuses = []
    crud = TimeEntryCRUD(db)
    
    for user_id in clocked_in_user_ids:
        user = get_user(db, user_id)
        if not user:
            continue
            
        latest_clock_in, latest_clock_out = crud.get_latest_entries(user_id)
        session_duration = crud.get_current_session_duration(user_id)
        
        user_statuses.append(UserTimeStatus(
            user_id=user.id,
            username=user.username,
            branch=user.branch,
            is_clocked_in=True,
            last_clock_in=latest_clock_in.timestamp if latest_clock_in else None,
            last_clock_out=latest_clock_out.timestamp if latest_clock_out else None,
            current_session_duration=session_duration,
            scheduled_start=user.shift_start_time.strftime('%H:%M:%S') if user.shift_start_time else None,
            scheduled_end=user.shift_end_time.strftime('%H:%M:%S') if user.shift_end_time else None
        ))
    
    return user_statuses


@admin_router.get("/entries/{user_id}", response_model=TimeEntryListResponse, summary="Get User Time Entries")
async def get_user_time_entries_admin(
    user_id: UUID,
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter to this date"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Get time entries for specific user (admin-only).
    
    **Permissions:** Requires active admin authentication
    
    **Parameters:**
    - **user_id**: UUID of user to get entries for
    - **start_date**: Filter entries from this date (optional)
    - **end_date**: Filter entries to this date (optional)
    - **limit**: Maximum number of entries to return (1-1000)
    
    **Returns:**
    - List of user's time entries
    - Total count of entries
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: User not found
    """
    # Verify user exists
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    entries = get_user_time_entries(db, user_id, start_date, end_date, limit)
    
    return TimeEntryListResponse(
        entries=[TimeEntryRead.model_validate(entry) for entry in entries],
        total=len(entries),
        user_id=user_id,
        date_range=f"{start_date} to {end_date}" if start_date and end_date else None
    )


@admin_router.post("/entries/{user_id}", response_model=TimeEntryRead, summary="Create Time Entry for User")
async def create_time_entry_admin(
    user_id: UUID,
    entry_data: TimeEntryCreate,
    db: Session = Depends(get_sync_db),
    current_admin: Admin = RequireActiveAdmin
):
    """
    Create time entry for specific user (admin-only).
    
    **Permissions:** Requires active admin authentication
    
    This allows admins to manually create time entries for users,
    useful for corrections or manual time tracking.
    
    **Parameters:**
    - **user_id**: UUID of user to create entry for
    - **entry_type**: "clock_in" or "clock_out"
    - **timestamp**: When the entry occurred (optional, defaults to now)
    - **method**: How entry was recorded (optional)
    - **notes**: Optional notes
    
    **Returns:**
    - Created time entry record
    
    **Errors:**
    - **401**: Not authenticated or not admin
    - **403**: Admin account deactivated
    - **404**: User not found
    - **400**: Invalid time entry (e.g., double clock-in)
    """
    try:
        time_entry = create_time_entry(db, user_id, entry_data)
        return TimeEntryRead.model_validate(time_entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create time entry: {str(e)}"
        )