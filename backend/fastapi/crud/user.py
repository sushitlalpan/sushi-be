"""
User CRUD operations.

This module provides database operations for staff users including
creation, retrieval, updating, deletion, and clock-in/out functionality.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from backend.fastapi.models.user import User
from backend.fastapi.models.branch import Branch
from backend.fastapi.schemas.user import UserCreate, UserUpdate
from backend.security.password import hash_password
from backend.fastapi.core.utils import normalize_username


class UserCRUD:
    """CRUD operations for User model."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new staff user.
        
        Username is automatically normalized:
        - Accents removed (é -> e, ñ -> n)
        - Spaces removed
        - Converted to lowercase
        
        Args:
            user_data: User creation data with username, password, branch, etc.
            
        Returns:
            Created User instance
            
        Raises:
            HTTPException: If username already exists
        """
        # Normalize username (remove accents, spaces, lowercase)
        normalized_username = normalize_username(user_data.username)
        
        # Check if normalized username already exists
        existing_user = self.get_user_by_username(normalized_username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username already registered (normalized to '{normalized_username}')"
            )
        
        # Hash the password
        hashed_password = hash_password(user_data.password)
        
        # Create user instance with normalized username
        db_user = User(
            username=normalized_username,
            password_hash=hashed_password,
            branch_id=user_data.branch_id,
            phone_number=user_data.phone_number,
            fingerprint_id=user_data.fingerprint_id,
            is_active=user_data.is_active
        )
        
        # Add to database
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def get_user(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID (excludes soft-deleted users).
        
        Args:
            user_id: User UUID
            
        Returns:
            User instance or None if not found or deleted
        """
        return self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username (excludes soft-deleted users).
        
        Args:
            username: User username
            
        Returns:
            User instance or None if not found or deleted
        """
        return self.db.query(User).filter(
            User.username == username,
            User.deleted_at.is_(None)
        ).first()
    
    def get_user_by_fingerprint(self, fingerprint_id: str) -> Optional[User]:
        """
        Get user by fingerprint ID (excludes soft-deleted users).
        
        Args:
            fingerprint_id: Fingerprint identifier
            
        Returns:
            User instance or None if not found or deleted
        """
        return self.db.query(User).filter(
            User.fingerprint_id == fingerprint_id,
            User.deleted_at.is_(None)
        ).first()
    
    def get_users(self, skip: int = 0, limit: int = 100, 
                  branch: Optional[str] = None, 
                  include_inactive: bool = False) -> List[User]:
        """
        Get list of users with optional filtering.
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            branch: Filter by branch (optional)
            include_inactive: Whether to include inactive users
            
        Returns:
            List of User instances
        """
        query = self.db.query(User).filter(User.deleted_at.is_(None))
        
        # Filter by active status
        if not include_inactive:
            query = query.filter(User.is_active == True)
        
        # Filter by branch
        if branch:
            query = query.filter(User.branch_id == branch)
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    

    
    def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.
        
        Args:
            user_id: User UUID to update
            user_data: Updated user data
            
        Returns:
            Updated User instance or None if not found
            
        Raises:
            HTTPException: If username already exists (when changing username)
        """
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        
        # Check username uniqueness if changing username
        if user_data.username and user_data.username != db_user.username:
            existing_user = self.get_user_by_username(user_data.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
        
        # Update fields if provided
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Handle password update
        if "password" in update_data:
            hashed_password = hash_password(update_data.pop("password"))
            update_data["password_hash"] = hashed_password
        
        # Apply updates
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        # Update timestamp
        db_user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def delete_user(self, user_id: UUID) -> bool:
        """
        Soft delete user by ID (sets deleted_at timestamp).
        
        Args:
            user_id: User UUID to delete
            
        Returns:
            True if deleted, False if not found
        """
        db_user = self.get_user(user_id)
        if not db_user:
            return False
        
        # Soft delete: set deleted_at timestamp
        db_user.deleted_at = datetime.utcnow()
        self.db.commit()
        return True
    



class AsyncUserCRUD:
    """Async CRUD operations for User model."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with async database session."""
        self.db = db
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username (async).
        
        Args:
            username: User username
            
        Returns:
            User instance or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID (async).
        
        Args:
            user_id: User UUID
            
        Returns:
            User instance or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


# Convenience functions
def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user."""
    return UserCRUD(db).create_user(user_data)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return UserCRUD(db).get_user_by_username(username)


def get_user(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    return UserCRUD(db).get_user(user_id)


def get_users(db: Session, skip: int = 0, limit: int = 100, 
              branch: Optional[str] = None, 
              include_inactive: bool = False) -> List[User]:
    """Get list of users with branch names loaded."""
    from sqlalchemy.orm import joinedload
    
    query = db.query(User).options(joinedload(User.branch))
    
    # Filter by active status
    if not include_inactive:
        query = query.filter(User.is_active == True)
    
    # Filter by branch name
    if branch:
        query = query.join(User.branch).filter(Branch.name.ilike(f"%{branch}%"))
    
    # Apply pagination
    return query.offset(skip).limit(limit).all()


def update_user(db: Session, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
    """Update user by ID."""
    return UserCRUD(db).update_user(user_id, user_data)


def delete_user(db: Session, user_id: UUID) -> bool:
    """Delete user by ID."""
    return UserCRUD(db).delete_user(user_id)


async def get_user_by_username_async(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username (async)."""
    return await AsyncUserCRUD(db).get_user_by_username(username)