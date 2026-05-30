"""
Migration script to add record locking fields to expenses, payroll, and sales tables.

This script adds:
- is_locked: BOOLEAN NOT NULL DEFAULT FALSE with index
- locked_at: TIMESTAMP(timezone=True) NULL

This enables super admins to lock financial records, making them read-only
to prevent editing or deletion while keeping them visible for transparency.
"""

import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.fastapi.core.config import get_settings


def get_migration_sql():
    """Return the SQL statements for adding record locking fields."""
    
    # SQL for expenses table
    expenses_sql = [
        """
        ALTER TABLE expenses 
        ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE;
        """,
        """
        ALTER TABLE expenses 
        ADD COLUMN locked_at TIMESTAMP WITH TIME ZONE;
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_expenses_is_locked 
        ON expenses (is_locked);
        """
    ]
    
    # SQL for payroll table
    payroll_sql = [
        """
        ALTER TABLE payroll 
        ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE;
        """,
        """
        ALTER TABLE payroll 
        ADD COLUMN locked_at TIMESTAMP WITH TIME ZONE;
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_payroll_is_locked 
        ON payroll (is_locked);
        """
    ]
    
    # SQL for sales table
    sales_sql = [
        """
        ALTER TABLE sales 
        ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE;
        """,
        """
        ALTER TABLE sales 
        ADD COLUMN locked_at TIMESTAMP WITH TIME ZONE;
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_sales_is_locked 
        ON sales (is_locked);
        """
    ]
    
    return expenses_sql + payroll_sql + sales_sql


def check_column_exists(engine, table_name, column_name):
    """Check if a column already exists in a table."""
    
    query = text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = :table_name 
            AND column_name = :column_name
        );
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {
            'table_name': table_name, 
            'column_name': column_name
        })
        return result.scalar()


def run_migration():
    """Run the migration to add record locking fields."""
    
    # Get database URL
    env_mode = os.getenv("ENV_MODE", "dev")
    settings = get_settings(env_mode)
    database_url = settings.DB_URL
    
    if not database_url:
        print("❌ Error: Could not get database URL")
        return False
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        print("🚀 Starting migration: Adding record locking fields to expenses, payroll, sales...")
        
        # Check if migration is needed
        tables_to_check = ['expenses', 'payroll', 'sales']
        migration_needed = False
        
        for table in tables_to_check:
            if not check_column_exists(engine, table, 'is_locked'):
                migration_needed = True
                break
        
        if not migration_needed:
            print("✅ Migration already applied - record locking fields already exist")
            return True
        
        # Run migration SQL
        sql_statements = get_migration_sql()
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                for i, sql in enumerate(sql_statements, 1):
                    print(f"📝 Executing statement {i}/{len(sql_statements)}...")
                    conn.execute(text(sql))
                
                # Commit transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
                # Verify the changes
                print("\n🔍 Verifying migration...")
                for table in tables_to_check:
                    if check_column_exists(engine, table, 'is_locked'):
                        print(f"  ✅ {table}.is_locked - Added")
                    else:
                        print(f"  ❌ {table}.is_locked - Failed")
                    
                    if check_column_exists(engine, table, 'locked_at'):
                        print(f"  ✅ {table}.locked_at - Added")
                    else:
                        print(f"  ❌ {table}.locked_at - Failed")
                
                return True
                
            except Exception as e:
                print(f"❌ Error during migration: {e}")
                trans.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False
    
    finally:
        engine.dispose()


def rollback_migration():
    """Rollback the migration by removing record locking fields."""
    
    # Get database URL
    env_mode = os.getenv("ENV_MODE", "dev")
    settings = get_settings(env_mode)
    database_url = settings.DB_URL
    
    if not database_url:
        print("❌ Error: Could not get database URL")
        return False
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        print("🔄 Starting rollback: Removing record locking fields...")
        
        rollback_sql = [
            # Drop indexes first
            "DROP INDEX IF EXISTS idx_expenses_is_locked;",
            "DROP INDEX IF EXISTS idx_payroll_is_locked;",
            "DROP INDEX IF EXISTS idx_sales_is_locked;",
            
            # Drop columns
            "ALTER TABLE expenses DROP COLUMN IF EXISTS is_locked;",
            "ALTER TABLE expenses DROP COLUMN IF EXISTS locked_at;",
            "ALTER TABLE payroll DROP COLUMN IF EXISTS is_locked;",
            "ALTER TABLE payroll DROP COLUMN IF EXISTS locked_at;",
            "ALTER TABLE sales DROP COLUMN IF EXISTS is_locked;",
            "ALTER TABLE sales DROP COLUMN IF EXISTS locked_at;"
        ]
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                for i, sql in enumerate(rollback_sql, 1):
                    print(f"📝 Executing rollback statement {i}/{len(rollback_sql)}...")
                    conn.execute(text(sql))
                
                # Commit transaction
                trans.commit()
                print("✅ Rollback completed successfully!")
                
                # Verify the changes
                print("\n🔍 Verifying rollback...")
                tables_to_check = ['expenses', 'payroll', 'sales']
                for table in tables_to_check:
                    if not check_column_exists(engine, table, 'is_locked'):
                        print(f"  ✅ {table}.is_locked - Column removed")
                    else:
                        print(f"  ❌ {table}.is_locked - Failed to remove column")
                    
                    if not check_column_exists(engine, table, 'locked_at'):
                        print(f"  ✅ {table}.locked_at - Column removed")
                    else:
                        print(f"  ❌ {table}.locked_at - Failed to remove column")
                
                return True
                
            except Exception as e:
                print(f"❌ Error during rollback: {e}")
                trans.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False
    
    finally:
        engine.dispose()


if __name__ == "__main__":
    import sys
    
    # Check for rollback argument
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("=" * 60)
        print("ROLLBACK MODE")
        print("=" * 60)
        success = rollback_migration()
    else:
        print("=" * 60)
        print("MIGRATION: Add record locking fields")
        print("=" * 60)
        success = run_migration()
    
    print("=" * 60)
    
    if success:
        print("✅ Operation completed successfully!")
        sys.exit(0)
    else:
        print("❌ Operation failed!")
        sys.exit(1)
