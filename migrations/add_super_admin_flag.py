"""
Migration script to add is_super_admin flag to the admins table.

This script adds:
- is_super_admin: BOOLEAN NOT NULL DEFAULT FALSE with index
- Promotes the first admin (oldest by created_at) to super admin

This enables a two-tier admin hierarchy where super admins have exclusive
privileges for critical operations like admin management, bulk imports,
and financial record deletion.
"""

import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.fastapi.core.config import get_settings


def get_migration_sql():
    """Return the SQL statements for adding is_super_admin flag."""
    
    sql = [
        # Add is_super_admin column with default FALSE
        """
        ALTER TABLE admins 
        ADD COLUMN is_super_admin BOOLEAN NOT NULL DEFAULT FALSE;
        """,
        
        # Add index for performance
        """
        CREATE INDEX IF NOT EXISTS idx_admins_is_super_admin 
        ON admins (is_super_admin);
        """,
        
        # Promote the first admin (oldest by created_at) to super admin
        """
        UPDATE admins 
        SET is_super_admin = TRUE 
        WHERE id = (
            SELECT id 
            FROM admins 
            ORDER BY created_at ASC 
            LIMIT 1
        );
        """
    ]
    
    return sql


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


def count_super_admins(engine):
    """Count the number of super admins."""
    
    query = text("""
        SELECT COUNT(*) 
        FROM admins 
        WHERE is_super_admin = TRUE;
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        return result.scalar()


def run_migration():
    """Run the migration to add is_super_admin flag."""
    
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
        print("🚀 Starting migration: Adding is_super_admin flag to admins table...")
        
        # Check if migration is needed
        if check_column_exists(engine, 'admins', 'is_super_admin'):
            print("✅ Migration already applied - is_super_admin column already exists")
            
            # Verify super admin exists
            super_admin_count = count_super_admins(engine)
            print(f"ℹ️  Current super admins: {super_admin_count}")
            
            if super_admin_count == 0:
                print("⚠️  Warning: No super admins found! You may want to promote an admin manually.")
            
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
                
                if check_column_exists(engine, 'admins', 'is_super_admin'):
                    print(f"  ✅ admins.is_super_admin - Column added")
                else:
                    print(f"  ❌ admins.is_super_admin - Failed to add column")
                    return False
                
                # Count super admins
                super_admin_count = count_super_admins(engine)
                print(f"  ✅ Super admins promoted: {super_admin_count}")
                
                if super_admin_count == 0:
                    print("  ⚠️  Warning: No admins were promoted to super admin (database may be empty)")
                
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
    """Rollback the migration by removing is_super_admin column."""
    
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
        print("🔄 Starting rollback: Removing is_super_admin flag...")
        
        rollback_sql = [
            # Drop index first
            "DROP INDEX IF EXISTS idx_admins_is_super_admin;",
            
            # Drop column
            "ALTER TABLE admins DROP COLUMN IF EXISTS is_super_admin;"
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
                if not check_column_exists(engine, 'admins', 'is_super_admin'):
                    print(f"  ✅ admins.is_super_admin - Column removed")
                else:
                    print(f"  ❌ admins.is_super_admin - Failed to remove column")
                    return False
                
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
        print("MIGRATION: Add is_super_admin flag to admins table")
        print("=" * 60)
        success = run_migration()
    
    print("=" * 60)
    
    if success:
        print("✅ Operation completed successfully!")
        sys.exit(0)
    else:
        print("❌ Operation failed!")
        sys.exit(1)
