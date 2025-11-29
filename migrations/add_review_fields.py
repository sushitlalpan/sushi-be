"""
Migration script to add review_state and review_observations fields
to expense, payroll, and sales tables.

This script adds:
- review_state: VARCHAR(20) NOT NULL DEFAULT 'pending' with index
- review_observations: TEXT NULL

To all three tables: expenses, payroll, sales
"""

import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.fastapi.core.config import get_settings


def get_migration_sql():
    """Return the SQL statements for adding review fields."""
    
    # SQL to add review fields to expenses table
    expenses_sql = [
        """
        ALTER TABLE expenses 
        ADD COLUMN review_state VARCHAR(20) NOT NULL DEFAULT 'pending';
        """,
        """
        ALTER TABLE expenses 
        ADD COLUMN review_observations TEXT;
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_expenses_review_state 
        ON expenses (review_state);
        """
    ]
    
    # SQL to add review fields to payroll table
    payroll_sql = [
        """
        ALTER TABLE payroll 
        ADD COLUMN review_state VARCHAR(20) NOT NULL DEFAULT 'pending';
        """,
        """
        ALTER TABLE payroll 
        ADD COLUMN review_observations VARCHAR(1000);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_payroll_review_state 
        ON payroll (review_state);
        """
    ]
    
    # SQL to add review fields to sales table
    sales_sql = [
        """
        ALTER TABLE sales 
        ADD COLUMN review_state VARCHAR(20) NOT NULL DEFAULT 'pending';
        """,
        """
        ALTER TABLE sales 
        ADD COLUMN review_observations TEXT;
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_sales_review_state 
        ON sales (review_state);
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
    """Run the migration to add review fields."""
    
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
        print("🚀 Starting migration: Adding review fields...")
        
        # Check if migration is needed
        tables_to_check = ['expenses', 'payroll', 'sales']
        migration_needed = False
        
        for table in tables_to_check:
            if not check_column_exists(engine, table, 'review_state'):
                migration_needed = True
                break
        
        if not migration_needed:
            print("✅ Migration already applied - review fields already exist")
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
                    if check_column_exists(engine, table, 'review_state'):
                        print(f"  ✅ {table}.review_state - Added")
                    else:
                        print(f"  ❌ {table}.review_state - Failed")
                    
                    if check_column_exists(engine, table, 'review_observations'):
                        print(f"  ✅ {table}.review_observations - Added")
                    else:
                        print(f"  ❌ {table}.review_observations - Failed")
                
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
    """Rollback the migration by removing review fields."""
    
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
        print("🔄 Starting rollback: Removing review fields...")
        
        rollback_sql = [
            # Drop indexes first
            "DROP INDEX IF EXISTS idx_expenses_review_state;",
            "DROP INDEX IF EXISTS idx_payroll_review_state;",
            "DROP INDEX IF EXISTS idx_sales_review_state;",
            
            # Drop columns
            "ALTER TABLE expenses DROP COLUMN IF EXISTS review_state;",
            "ALTER TABLE expenses DROP COLUMN IF EXISTS review_observations;",
            "ALTER TABLE payroll DROP COLUMN IF EXISTS review_state;",
            "ALTER TABLE payroll DROP COLUMN IF EXISTS review_observations;",
            "ALTER TABLE sales DROP COLUMN IF EXISTS review_state;",
            "ALTER TABLE sales DROP COLUMN IF EXISTS review_observations;"
        ]
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                for i, sql in enumerate(rollback_sql, 1):
                    print(f"📝 Executing rollback statement {i}/{len(rollback_sql)}...")
                    conn.execute(text(sql))
                
                trans.commit()
                print("✅ Rollback completed successfully!")
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
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)