"""
Pydantic schemas for TimeEntry model validation and serialization.

This module defines the data validation schemas for time entry
operations including clock-in/out and time tracking.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from backend.fastapi.models.time_entry import TimeEntryType


class TimeEntryBase(BaseModel):
    """Base TimeEntry schema with common fields."""
    
    entry_type: TimeEntryType = Field(
        ...,
        description="Type of time entry (clock_in or clock_out)",
        examples=["clock_in", "clock_out"]
    )
    
    method: Optional[str] = Field(
        default="manual",
        max_length=50,
        description="How the entry was recorded",
        examples=["manual", "fingerprint", "card", "biometric"]
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes about the time entry",
        examples=["Late due to traffic", "Early departure approved by manager"]
    )


class TimeEntryCreate(TimeEntryBase):
    """Schema for creating a new time entry."""
    
    timestamp: Optional[datetime] = Field(
        None,
        description="Time of the entry (defaults to current time if not provided)"
    )


class TimeEntryRead(TimeEntryBase):
    """Schema for reading time entry information."""
    
    id: UUID = Field(..., description="Time entry unique identifier")
    user_id: UUID = Field(..., description="User who made this entry")
    timestamp: datetime = Field(..., description="When the entry was made")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class TimeEntryUpdate(BaseModel):
    """Schema for updating time entry information."""
    
    timestamp: Optional[datetime] = Field(
        None,
        description="New timestamp for the entry"
    )
    
    method: Optional[str] = Field(
        None,
        max_length=50,
        description="New method"
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="New notes"
    )


class ClockAction(BaseModel):
    """Schema for clock-in/out requests."""
    
    action: TimeEntryType = Field(
        ...,
        description="Clock action to perform",
        examples=["clock_in", "clock_out"]
    )
    
    method: Optional[str] = Field(
        default="manual",
        max_length=50,
        description="How the clock action is being performed",
        examples=["manual", "fingerprint", "card"]
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes for this clock action"
    )
    
    timestamp: Optional[datetime] = Field(
        None,
        description="Custom timestamp (admin only, defaults to current time)"
    )


class ClockActionResponse(BaseModel):
    """Response schema for clock-in/out operations."""
    
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    time_entry: TimeEntryRead = Field(..., description="Created time entry record")
    current_status: str = Field(
        ..., 
        description="User's current clock status",
        examples=["clocked_in", "clocked_out"]
    )


class TimeEntryListResponse(BaseModel):
    """Schema for listing multiple time entries."""
    
    entries: List[TimeEntryRead] = Field(..., description="List of time entries")
    total: int = Field(..., description="Total number of entries")
    user_id: Optional[UUID] = Field(None, description="User filter applied")
    date_range: Optional[str] = Field(None, description="Date range filter applied")


class UserTimeStatus(BaseModel):
    """Schema for user's current time tracking status."""
    
    user_id: UUID = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    branch: str = Field(..., description="User's branch")
    is_clocked_in: bool = Field(..., description="Whether user is currently clocked in")
    last_clock_in: Optional[datetime] = Field(None, description="Last clock-in time")
    last_clock_out: Optional[datetime] = Field(None, description="Last clock-out time")
    current_session_duration: Optional[int] = Field(
        None, 
        description="Current session duration in minutes (if clocked in)"
    )
    scheduled_start: Optional[str] = Field(None, description="Scheduled shift start time")
    scheduled_end: Optional[str] = Field(None, description="Scheduled shift end time")


class DailyTimeReport(BaseModel):
    """Schema for daily time tracking report."""
    
    user_id: UUID = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    date: str = Field(..., description="Report date (YYYY-MM-DD)")
    clock_ins: List[TimeEntryRead] = Field(..., description="All clock-in entries for the day")
    clock_outs: List[TimeEntryRead] = Field(..., description="All clock-out entries for the day")
    total_hours: float = Field(..., description="Total hours worked")
    scheduled_hours: float = Field(..., description="Scheduled hours for the day")
    overtime_hours: float = Field(default=0.0, description="Overtime hours (if any)")
    is_complete: bool = Field(..., description="Whether all clock-in/outs are paired")