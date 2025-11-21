"""
TimeEntry CRUD operations.

This module provides database operations for time entries including
clock-in/out tracking, time reports, and attendance management.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, date, time as time_type
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, cast, Date
from fastapi import HTTPException, status

from backend.fastapi.models.time_entry import TimeEntry, TimeEntryType
from backend.fastapi.models.user import User
from backend.fastapi.schemas.time_entry import TimeEntryCreate, TimeEntryUpdate


class TimeEntryCRUD:
    """CRUD operations for TimeEntry model."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def create_time_entry(self, user_id: UUID, entry_data: TimeEntryCreate) -> TimeEntry:
        """
        Create a new time entry.
        
        Args:
            user_id: User UUID
            entry_data: Time entry creation data
            
        Returns:
            Created TimeEntry instance
            
        Raises:
            HTTPException: If user not found or validation fails
        """
        # Verify user exists and is active
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        # Validate clock-in/out logic
        current_status = self.get_user_clock_status(user_id)
        
        if entry_data.entry_type == TimeEntryType.CLOCK_IN and current_status == "clocked_in":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already clocked in"
            )
        
        if entry_data.entry_type == TimeEntryType.CLOCK_OUT and current_status == "clocked_out":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not currently clocked in"
            )
        
        # Create time entry
        db_entry = TimeEntry(
            user_id=user_id,
            entry_type=entry_data.entry_type,
            timestamp=entry_data.timestamp or datetime.utcnow(),
            method=entry_data.method or "manual",
            notes=entry_data.notes
        )
        
        self.db.add(db_entry)
        self.db.commit()
        self.db.refresh(db_entry)
        
        return db_entry
    
    def get_time_entry(self, entry_id: UUID) -> Optional[TimeEntry]:
        """
        Get time entry by ID.
        
        Args:
            entry_id: TimeEntry UUID
            
        Returns:
            TimeEntry instance or None if not found
        """
        return self.db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    
    def get_user_time_entries(self, user_id: UUID, 
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None,
                            limit: int = 100) -> List[TimeEntry]:
        """
        Get time entries for a user with optional date filtering.
        
        Args:
            user_id: User UUID
            start_date: Filter entries from this date
            end_date: Filter entries to this date
            limit: Maximum number of entries to return
            
        Returns:
            List of TimeEntry instances
        """
        query = self.db.query(TimeEntry).filter(TimeEntry.user_id == user_id)
        
        if start_date:
            query = query.filter(cast(TimeEntry.timestamp, Date) >= start_date)
        
        if end_date:
            query = query.filter(cast(TimeEntry.timestamp, Date) <= end_date)
        
        return query.order_by(desc(TimeEntry.timestamp)).limit(limit).all()
    
    def get_user_clock_status(self, user_id: UUID) -> str:
        """
        Get user's current clock status.
        
        Args:
            user_id: User UUID
            
        Returns:
            "clocked_in" or "clocked_out"
        """
        # Get the most recent time entry
        latest_entry = (self.db.query(TimeEntry)
                       .filter(TimeEntry.user_id == user_id)
                       .order_by(desc(TimeEntry.timestamp))
                       .first())
        
        if not latest_entry:
            return "clocked_out"
        
        return "clocked_in" if latest_entry.entry_type == TimeEntryType.CLOCK_IN else "clocked_out"
    
    def get_latest_entries(self, user_id: UUID) -> tuple[Optional[TimeEntry], Optional[TimeEntry]]:
        """
        Get user's latest clock-in and clock-out entries.
        
        Args:
            user_id: User UUID
            
        Returns:
            tuple of (latest_clock_in, latest_clock_out)
        """
        latest_clock_in = (self.db.query(TimeEntry)
                          .filter(and_(TimeEntry.user_id == user_id,
                                     TimeEntry.entry_type == TimeEntryType.CLOCK_IN))
                          .order_by(desc(TimeEntry.timestamp))
                          .first())
        
        latest_clock_out = (self.db.query(TimeEntry)
                           .filter(and_(TimeEntry.user_id == user_id,
                                      TimeEntry.entry_type == TimeEntryType.CLOCK_OUT))
                           .order_by(desc(TimeEntry.timestamp))
                           .first())
        
        return latest_clock_in, latest_clock_out
    
    def get_current_session_duration(self, user_id: UUID) -> Optional[int]:
        """
        Get current session duration in minutes if user is clocked in.
        
        Args:
            user_id: User UUID
            
        Returns:
            Duration in minutes, or None if not clocked in
        """
        if self.get_user_clock_status(user_id) != "clocked_in":
            return None
        
        latest_clock_in, _ = self.get_latest_entries(user_id)
        if not latest_clock_in:
            return None
        
        duration = datetime.utcnow() - latest_clock_in.timestamp
        return int(duration.total_seconds() / 60)
    
    def get_daily_entries(self, user_id: UUID, target_date: date) -> List[TimeEntry]:
        """
        Get all time entries for a specific date.
        
        Args:
            user_id: User UUID
            target_date: Date to get entries for
            
        Returns:
            List of TimeEntry instances for the date
        """
        return (self.db.query(TimeEntry)
               .filter(and_(TimeEntry.user_id == user_id,
                          cast(TimeEntry.timestamp, Date) == target_date))
               .order_by(TimeEntry.timestamp)
               .all())
    
    def calculate_daily_hours(self, user_id: UUID, target_date: date) -> float:
        """
        Calculate total hours worked for a specific date.
        
        Args:
            user_id: User UUID
            target_date: Date to calculate hours for
            
        Returns:
            Total hours worked as float
        """
        entries = self.get_daily_entries(user_id, target_date)
        
        total_minutes = 0
        current_clock_in = None
        
        for entry in entries:
            if entry.entry_type == TimeEntryType.CLOCK_IN:
                current_clock_in = entry.timestamp
            elif entry.entry_type == TimeEntryType.CLOCK_OUT and current_clock_in:
                duration = entry.timestamp - current_clock_in
                total_minutes += int(duration.total_seconds() / 60)
                current_clock_in = None
        
        return total_minutes / 60.0  # Convert to hours
    
    def get_clocked_in_users(self, branch: Optional[str] = None) -> List[UUID]:
        """
        Get list of user IDs currently clocked in.
        
        Args:
            branch: Filter by branch (optional)
            
        Returns:
            List of user UUIDs currently clocked in
        """
        # Subquery to get latest entry for each user
        latest_entries = (self.db.query(
            TimeEntry.user_id,
            func.max(TimeEntry.timestamp).label('max_timestamp')
        ).group_by(TimeEntry.user_id).subquery())
        
        # Join with actual entries to get entry types
        query = (self.db.query(TimeEntry.user_id)
                .join(latest_entries, 
                     and_(TimeEntry.user_id == latest_entries.c.user_id,
                         TimeEntry.timestamp == latest_entries.c.max_timestamp))
                .filter(TimeEntry.entry_type == TimeEntryType.CLOCK_IN))
        
        # Add branch filter if specified
        if branch:
            query = query.join(User).filter(User.branch == branch)
        
        return [row[0] for row in query.all()]
    
    def update_time_entry(self, entry_id: UUID, entry_data: TimeEntryUpdate) -> Optional[TimeEntry]:
        """
        Update time entry information.
        
        Args:
            entry_id: TimeEntry UUID to update
            entry_data: Updated entry data
            
        Returns:
            Updated TimeEntry instance or None if not found
        """
        db_entry = self.get_time_entry(entry_id)
        if not db_entry:
            return None
        
        # Update fields if provided
        update_data = entry_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_entry, field, value)
        
        self.db.commit()
        self.db.refresh(db_entry)
        
        return db_entry
    
    def delete_time_entry(self, entry_id: UUID) -> bool:
        """
        Delete time entry by ID.
        
        Args:
            entry_id: TimeEntry UUID to delete
            
        Returns:
            True if deleted, False if not found
        """
        db_entry = self.get_time_entry(entry_id)
        if not db_entry:
            return False
        
        self.db.delete(db_entry)
        self.db.commit()
        return True


# Convenience functions
def create_time_entry(db: Session, user_id: UUID, entry_data: TimeEntryCreate) -> TimeEntry:
    """Create a new time entry."""
    return TimeEntryCRUD(db).create_time_entry(user_id, entry_data)


def get_time_entry(db: Session, entry_id: UUID) -> Optional[TimeEntry]:
    """Get time entry by ID."""
    return TimeEntryCRUD(db).get_time_entry(entry_id)


def get_user_time_entries(db: Session, user_id: UUID, 
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         limit: int = 100) -> List[TimeEntry]:
    """Get time entries for a user."""
    return TimeEntryCRUD(db).get_user_time_entries(user_id, start_date, end_date, limit)


def get_user_clock_status(db: Session, user_id: UUID) -> str:
    """Get user's current clock status."""
    return TimeEntryCRUD(db).get_user_clock_status(user_id)


def get_current_session_duration(db: Session, user_id: UUID) -> Optional[int]:
    """Get current session duration in minutes."""
    return TimeEntryCRUD(db).get_current_session_duration(user_id)


def get_clocked_in_users(db: Session, branch: Optional[str] = None) -> List[UUID]:
    """Get list of user IDs currently clocked in."""
    return TimeEntryCRUD(db).get_clocked_in_users(branch)


def calculate_daily_hours(db: Session, user_id: UUID, target_date: date) -> float:
    """Calculate total hours worked for a specific date."""
    return TimeEntryCRUD(db).calculate_daily_hours(user_id, target_date)