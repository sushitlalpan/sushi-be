"""
Admin CRUD operations.

This module provides database operations for admin users including
creation, retrieval, updating, and deletion.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.fastapi.models.admin import Admin
from backend.fastapi.schemas.admin import AdminCreate, AdminUpdate
from backend.security.password import hash_password


class AdminCRUD:
    """CRUD operations for Admin model."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def create_admin(self, admin_data: AdminCreate) -> Admin:
        """
        Create a new admin user.
        
        Args:
            admin_data: Admin creation data with username and password
            
        Returns:
            Created Admin instance
            
        Raises:
            HTTPException: If username already exists
        """
        # Check if username already exists
        existing_admin = self.get_admin_by_username(admin_data.username)
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Hash the password
        hashed_password = hash_password(admin_data.password)
        
        # Create admin instance
        db_admin = Admin(
            username=admin_data.username,
            password_hash=hashed_password,
            is_active=admin_data.is_active
        )
        
        # Save to database
        self.db.add(db_admin)
        self.db.commit()
        self.db.refresh(db_admin)
        
        return db_admin
    
    def get_admin(self, admin_id: UUID) -> Optional[Admin]:
        """
        Get admin by ID.
        
        Args:
            admin_id: Admin UUID
            
        Returns:
            Admin instance or None if not found
        """
        return self.db.query(Admin).filter(Admin.id == admin_id).first()
    
    def get_admin_by_username(self, username: str) -> Optional[Admin]:
        """
        Get admin by username.
        
        Args:
            username: Admin username
            
        Returns:
            Admin instance or None if not found
        """
        return self.db.query(Admin).filter(Admin.username == username).first()
    
    def get_admins(self, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[Admin]:
        """
        Get list of admins with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive admins
            
        Returns:
            List of Admin instances
        """
        query = self.db.query(Admin)
        
        if not include_inactive:
            query = query.filter(Admin.is_active == True)
        
        return query.offset(skip).limit(limit).all()
    
    def update_admin(self, admin_id: UUID, admin_update: AdminUpdate) -> Optional[Admin]:
        """
        Update admin information.
        
        Args:
            admin_id: Admin UUID
            admin_update: Update data
            
        Returns:
            Updated Admin instance or None if not found
            
        Raises:
            HTTPException: If new username already exists
        """
        db_admin = self.get_admin(admin_id)
        if not db_admin:
            return None
        
        update_data = admin_update.model_dump(exclude_unset=True)
        
        # Check username uniqueness if being updated
        if "username" in update_data:
            existing_admin = self.get_admin_by_username(update_data["username"])
            if existing_admin and existing_admin.id != admin_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
        
        # Hash password if being updated
        if "password" in update_data:
            update_data["password_hash"] = hash_password(update_data.pop("password"))
        
        # Apply updates
        for field, value in update_data.items():
            setattr(db_admin, field, value)
        
        self.db.commit()
        self.db.refresh(db_admin)
        
        return db_admin
    
    def delete_admin(self, admin_id: UUID) -> bool:
        """
        Delete admin by ID.
        
        Args:
            admin_id: Admin UUID
            
        Returns:
            True if deleted, False if not found
        """
        db_admin = self.get_admin(admin_id)
        if not db_admin:
            return False
        
        self.db.delete(db_admin)
        self.db.commit()
        
        return True
    
    def deactivate_admin(self, admin_id: UUID) -> Optional[Admin]:
        """
        Deactivate admin (soft delete).
        
        Args:
            admin_id: Admin UUID
            
        Returns:
            Updated Admin instance or None if not found
        """
        db_admin = self.get_admin(admin_id)
        if not db_admin:
            return None
        
        db_admin.is_active = False
        self.db.commit()
        self.db.refresh(db_admin)
        
        return db_admin
    
    def count_admins(self, include_inactive: bool = False) -> int:
        """
        Count total number of admins.
        
        Args:
            include_inactive: Whether to include inactive admins
            
        Returns:
            Total count of admins
        """
        query = self.db.query(Admin)
        
        if not include_inactive:
            query = query.filter(Admin.is_active == True)
        
        return query.count()


class AsyncAdminCRUD:
    """Async CRUD operations for Admin model."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with async database session."""
        self.db = db
    
    async def get_admin_by_username(self, username: str) -> Optional[Admin]:
        """
        Get admin by username (async).
        
        Args:
            username: Admin username
            
        Returns:
            Admin instance or None if not found
        """
        result = await self.db.execute(
            select(Admin).where(Admin.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_admin(self, admin_id: UUID) -> Optional[Admin]:
        """
        Get admin by ID (async).
        
        Args:
            admin_id: Admin UUID
            
        Returns:
            Admin instance or None if not found
        """
        result = await self.db.execute(
            select(Admin).where(Admin.id == admin_id)
        )
        return result.scalar_one_or_none()


# Convenience functions
def create_admin(db: Session, admin_data: AdminCreate) -> Admin:
    """Create a new admin."""
    return AdminCRUD(db).create_admin(admin_data)


def get_admin_by_username(db: Session, username: str) -> Optional[Admin]:
    """Get admin by username."""
    return AdminCRUD(db).get_admin_by_username(username)


def get_admin(db: Session, admin_id: UUID) -> Optional[Admin]:
    """Get admin by ID."""
    return AdminCRUD(db).get_admin(admin_id)


def get_admins(db: Session, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[Admin]:
    """Get list of admins."""
    return AdminCRUD(db).get_admins(skip=skip, limit=limit, include_inactive=include_inactive)


def update_admin(db: Session, admin_id: UUID, admin_data: AdminUpdate) -> Optional[Admin]:
    """Update admin by ID."""
    return AdminCRUD(db).update_admin(admin_id, admin_data)


def delete_admin(db: Session, admin_id: UUID) -> bool:
    """Delete admin by ID."""
    return AdminCRUD(db).delete_admin(admin_id)


def get_admin_count(db: Session, include_inactive: bool = False) -> int:
    """Get total count of admins."""
    return AdminCRUD(db).count_admins(include_inactive=include_inactive)


async def get_admin_by_username_async(db: AsyncSession, username: str) -> Optional[Admin]:
    """Get admin by username (async)."""
    return await AsyncAdminCRUD(db).get_admin_by_username(username)