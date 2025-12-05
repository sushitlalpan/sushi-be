"""
Migration: Add soft delete support to users and branches tables

This migration adds a deleted_at timestamp field to the users and branches tables
to support soft deletes instead of hard deletes.

Date: 2025-12-04
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from backend.fastapi.core.config import get_settings
    settings = get_settings(os.environ.get("ENV_MODE", "dev"))
    DATABASE_URL = settings.DB_URL
except (ImportError, AttributeError):
    # Fallback to environment variable if settings import fails
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError(
            "Could not determine DATABASE_URL. Please set the DATABASE_URL "
            "environment variable or ensure backend.fastapi.core.config is available."
        )

from sqlalchemy import create_engine, text, inspect


def run_migration():
    """Add deleted_at columns to users and branches tables."""
    print(f"Starting soft delete migration at {datetime.utcnow()}")
    print(f"Connecting to database...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        # Check and add deleted_at to users table
        print("\n=== Processing users table ===")
        users_columns = {col['name'] for col in inspector.get_columns('users')}
        
        if 'deleted_at' not in users_columns:
            print("Adding deleted_at column to users table...")
            connection.execute(text("""
                ALTER TABLE users
                ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL
            """))
            connection.commit()
            print("✓ Added deleted_at column to users table")
            
            # Create index for soft delete queries
            print("Creating index on users.deleted_at...")
            connection.execute(text("""
                CREATE INDEX idx_users_deleted_at ON users(deleted_at)
            """))
            connection.commit()
            print("✓ Created index on users.deleted_at")
        else:
            print("⊘ deleted_at column already exists in users table")
        
        # Check and add deleted_at to branches table
        print("\n=== Processing branches table ===")
        branches_columns = {col['name'] for col in inspector.get_columns('branches')}
        
        if 'deleted_at' not in branches_columns:
            print("Adding deleted_at column to branches table...")
            connection.execute(text("""
                ALTER TABLE branches
                ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL
            """))
            connection.commit()
            print("✓ Added deleted_at column to branches table")
            
            # Create index for soft delete queries
            print("Creating index on branches.deleted_at...")
            connection.execute(text("""
                CREATE INDEX idx_branches_deleted_at ON branches(deleted_at)
            """))
            connection.commit()
            print("✓ Created index on branches.deleted_at")
        else:
            print("⊘ deleted_at column already exists in branches table")
    
    print("\n" + "="*50)
    print("Migration completed successfully!")
    print("="*50)


def rollback_migration():
    """Remove deleted_at columns from users and branches tables."""
    print(f"Starting rollback at {datetime.utcnow()}")
    print(f"Connecting to database...")
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        # Remove from users table
        print("\n=== Reverting users table ===")
        users_columns = {col['name'] for col in inspector.get_columns('users')}
        
        if 'deleted_at' in users_columns:
            print("Dropping index on users.deleted_at...")
            connection.execute(text("""
                DROP INDEX IF EXISTS idx_users_deleted_at
            """))
            connection.commit()
            
            print("Removing deleted_at column from users table...")
            connection.execute(text("""
                ALTER TABLE users
                DROP COLUMN deleted_at
            """))
            connection.commit()
            print("✓ Removed deleted_at column from users table")
        else:
            print("⊘ deleted_at column doesn't exist in users table")
        
        # Remove from branches table
        print("\n=== Reverting branches table ===")
        branches_columns = {col['name'] for col in inspector.get_columns('branches')}
        
        if 'deleted_at' in branches_columns:
            print("Dropping index on branches.deleted_at...")
            connection.execute(text("""
                DROP INDEX IF EXISTS idx_branches_deleted_at
            """))
            connection.commit()
            
            print("Removing deleted_at column from branches table...")
            connection.execute(text("""
                ALTER TABLE branches
                DROP COLUMN deleted_at
            """))
            connection.commit()
            print("✓ Removed deleted_at column from branches table")
        else:
            print("⊘ deleted_at column doesn't exist in branches table")
    
    print("\n" + "="*50)
    print("Rollback completed successfully!")
    print("="*50)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add soft delete support migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (remove deleted_at columns)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.rollback:
            rollback_migration()
        else:
            run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
