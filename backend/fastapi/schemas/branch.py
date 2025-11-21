"""
Branch Pydantic schemas for request/response validation.

This module defines the data validation schemas for Branch-related
API operations using Pydantic models.
"""

from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class BranchBase(BaseModel):
    """Base Branch schema with common fields."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the branch/location",
        examples=["Downtown Store", "Mall Location", "Airport Branch"]
    )


class BranchCreate(BranchBase):
    """Schema for creating a new branch."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Downtown Store"
            }
        }
    )


class BranchUpdate(BaseModel):
    """Schema for updating an existing branch."""
    
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Updated name of the branch/location"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Branch Name"
            }
        }
    )


class BranchRead(BranchBase):
    """Schema for reading branch information."""
    
    id: UUID = Field(
        ...,
        description="Unique identifier of the branch"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Downtown Store"
            }
        }
    )


class BranchWithStats(BranchRead):
    """Schema for branch information with statistics."""
    
    user_count: int = Field(
        ...,
        description="Number of users assigned to this branch"
    )
    
    payroll_records_count: int = Field(
        ...,
        description="Number of payroll records for this branch"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Downtown Store",
                "user_count": 15,
                "payroll_records_count": 120
            }
        }
    )


class BranchListResponse(BaseModel):
    """Schema for paginated branch listing."""
    
    branches: List[BranchRead] = Field(
        ...,
        description="List of branches"
    )
    
    total: int = Field(
        ...,
        description="Total number of branches"
    )
    
    skip: int = Field(
        ...,
        description="Number of records skipped"
    )
    
    limit: int = Field(
        ...,
        description="Maximum number of records returned"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "branches": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Downtown Store"
                    },
                    {
                        "id": "456e7890-e89b-12d3-a456-426614174000",
                        "name": "Mall Location"
                    }
                ],
                "total": 2,
                "skip": 0,
                "limit": 10
            }
        }
    )