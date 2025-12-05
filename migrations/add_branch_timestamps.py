"""
Migration: Add timestamp fields to branches table

This migration adds created_at and updated_at timestamp fields to the branches table
to match the Branch model definition.

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
    """Add created_at and updated_at columns to branches table."""
    print(f"Starting branch timestamps migration at {datetime.utcnow()}")
    print(f"Connecting to database...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        # Check columns in branches table
        print("\n=== Processing branches table ===")
        branches_columns = {col['name'] for col in inspector.get_columns('branches')}
        print(f"Current branches columns: {sorted(branches_columns)}")
        
        # Add created_at if missing
        if 'created_at' not in branches_columns:
            print("Adding created_at column to branches table...")
            connection.execute(text("""
                ALTER TABLE branches
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            """))
            connection.commit()
            print("✓ Added created_at column to branches table")
        else:
            print("⊘ created_at column already exists in branches table")
        
        # Add updated_at if missing
        if 'updated_at' not in branches_columns:
            print("Adding updated_at column to branches table...")
            connection.execute(text("""
                ALTER TABLE branches
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            """))
            connection.commit()
            print("✓ Added updated_at column to branches table")
            
            # Create a trigger to automatically update updated_at
            print("Creating trigger for automatic updated_at updates...")
            
            # First, create the trigger function if it doesn't exist
            connection.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))
            connection.commit()
            
            # Drop trigger if it exists and recreate it
            connection.execute(text("""
                DROP TRIGGER IF EXISTS update_branches_updated_at ON branches;
            """))
            connection.commit()
            
            connection.execute(text("""
                CREATE TRIGGER update_branches_updated_at
                    BEFORE UPDATE ON branches
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """))
            connection.commit()
            print("✓ Created trigger for updated_at column")
        else:
            print("⊘ updated_at column already exists in branches table")
    
    print("\n" + "="*50)
    print("Migration completed successfully!")
    print("="*50)


def rollback_migration():
    """Remove created_at and updated_at columns from branches table."""
    print(f"Starting rollback at {datetime.utcnow()}")
    print(f"Connecting to database...")
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        print("\n=== Reverting branches table ===")
        branches_columns = {col['name'] for col in inspector.get_columns('branches')}
        
        # Drop trigger
        print("Dropping trigger on branches.updated_at...")
        connection.execute(text("""
            DROP TRIGGER IF EXISTS update_branches_updated_at ON branches
        """))
        connection.commit()
        
        # Remove updated_at
        if 'updated_at' in branches_columns:
            print("Removing updated_at column from branches table...")
            connection.execute(text("""
                ALTER TABLE branches
                DROP COLUMN updated_at
            """))
            connection.commit()
            print("✓ Removed updated_at column from branches table")
        else:
            print("⊘ updated_at column doesn't exist in branches table")
        
        # Remove created_at
        if 'created_at' in branches_columns:
            print("Removing created_at column from branches table...")
            connection.execute(text("""
                ALTER TABLE branches
                DROP COLUMN created_at
            """))
            connection.commit()
            print("✓ Removed created_at column from branches table")
        else:
            print("⊘ created_at column doesn't exist in branches table")
    
    print("\n" + "="*50)
    print("Rollback completed successfully!")
    print("="*50)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add branch timestamp fields migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (remove timestamp columns)"
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
