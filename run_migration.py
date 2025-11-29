#!/usr/bin/env python3
"""
Migration runner script that ensures proper Python path setup.
Usage: python run_migration.py <migration_name>
"""

import os
import sys
import subprocess

def run_migration(migration_name):
    """Run a migration with proper Python path setup."""
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH environment variable
    env = os.environ.copy()
    env['PYTHONPATH'] = project_root
    
    # Migration file path
    migration_path = os.path.join(project_root, 'migrations', f'{migration_name}.py')
    
    if not os.path.exists(migration_path):
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    # Run the migration
    print(f"🚀 Running migration: {migration_name}")
    result = subprocess.run(
        [sys.executable, migration_path],
        env=env,
        cwd=project_root
    )
    
    return result.returncode == 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_migration.py <migration_name>")
        print("Example: python run_migration.py add_review_fields")
        sys.exit(1)
    
    migration_name = sys.argv[1]
    success = run_migration(migration_name)
    sys.exit(0 if success else 1)