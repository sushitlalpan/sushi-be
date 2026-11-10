"""
Migration script to add audit fields.

Adds to sales, expenses, payroll and time_entries (all nullable, existing rows are left NULL):
- create_user: VARCHAR(100) - role-qualified creator (e.g. "admin:alice", "user:bob")
- last_updated_at: TIMESTAMP WITH TIME ZONE
- last_updated_user: VARCHAR(100) - role-qualified last updater

Adds only create_user to branches, users and admins (database traceability only).

Usage: python run_migration.py add_audit_fields
Rollback: PYTHONPATH=. python migrations/add_audit_fields.py rollback
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import create_engine, inspect, text
from backend.fastapi.core.config import get_settings

TABLES = ["sales", "expenses", "payroll", "time_entries"]
COLUMNS = {
    "create_user": "VARCHAR(100)",
    "last_updated_at": "TIMESTAMP WITH TIME ZONE",
    "last_updated_user": "VARCHAR(100)",
}
# Traceability-only: just create_user, not exposed in API responses
TABLE_COLUMNS = {
    **{table: COLUMNS for table in TABLES},
    "branches": {"create_user": "VARCHAR(100)"},
    "users": {"create_user": "VARCHAR(100)"},
    "admins": {"create_user": "VARCHAR(100)"},
}


def get_engine():
    settings = get_settings(os.getenv("ENV_MODE", "dev"))
    database_url = settings.DB_URL
    if not database_url:
        print("❌ Error: Could not get database URL")
        return None
    return create_engine(database_url)


def run_migration():
    """Add the audit columns to each table when missing."""
    engine = get_engine()
    if engine is None:
        return False

    try:
        print("🚀 Starting migration: Adding audit fields...")
        inspector = inspect(engine)

        with engine.begin() as conn:
            for table, columns in TABLE_COLUMNS.items():
                existing = {col["name"] for col in inspector.get_columns(table)}
                for column, column_type in columns.items():
                    if column in existing:
                        print(f"⊘ {table}.{column} already exists")
                        continue
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
                    print(f"✓ Added {table}.{column}")

        print("✅ Migration completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    finally:
        engine.dispose()


def rollback_migration():
    """Remove the audit columns from each table."""
    engine = get_engine()
    if engine is None:
        return False

    try:
        print("🔄 Starting rollback: Removing audit fields...")
        inspector = inspect(engine)

        with engine.begin() as conn:
            for table, columns in TABLE_COLUMNS.items():
                existing = {col["name"] for col in inspector.get_columns(table)}
                for column in columns:
                    if column not in existing:
                        continue
                    conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
                    print(f"✓ Removed {table}.{column}")

        print("✅ Rollback completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error during rollback: {e}")
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_migration()
    else:
        success = run_migration()

    sys.exit(0 if success else 1)
