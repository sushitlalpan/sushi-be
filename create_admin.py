"""
Create admin user with optional super admin privileges.

This script creates admin users directly in the database with configurable
credentials and role settings via command-line arguments.

Usage:
    python create_admin.py --username admin --password SecurePass123 --super-admin
    python create_admin.py --username regularadmin --password Pass456
"""

import sys
import os
import argparse

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.crud.admin import create_admin
from backend.fastapi.schemas.admin import AdminCreate


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create an admin user with optional super admin privileges",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create a regular admin:
    python create_admin.py --username admin --password MySecurePass123
  
  Create a super admin:
    python create_admin.py --username superadmin --password SuperSecure456 --super-admin
  
  Create with defaults (not recommended for production):
    python create_admin.py
        """
    )
    
    parser.add_argument(
        "--username",
        type=str,
        default="admin",
        help="Admin username (default: admin)"
    )
    
    parser.add_argument(
        "--password",
        type=str,
        default="admin123",
        help="Admin password (default: admin123 - change in production!)"
    )
    
    parser.add_argument(
        "--super-admin",
        action="store_true",
        help="Create as super admin with elevated privileges"
    )
    
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create admin as inactive (default: active)"
    )
    
    return parser.parse_args()


def create_admin_user(username: str, password: str, is_super_admin: bool = False, is_active: bool = True):
    """
    Create an admin user with specified credentials and role.
    
    Args:
        username: Admin username
        password: Admin password (will be hashed)
        is_super_admin: Whether to grant super admin privileges
        is_active: Whether the admin account should be active
        
    Returns:
        Created Admin instance or None if failed
    """
    
    # Admin credentials
    admin_data = AdminCreate(
        username=username,
        password=password,
        is_active=is_active,
        is_super_admin=is_super_admin
    )
    
    # Get database session
    db = next(get_sync_db())
    
    try:
        # Create admin
        admin = create_admin(db, admin_data)
        
        # Success message
        role_label = "SUPER ADMIN" if admin.is_super_admin else "ADMIN"
        print(f"✅ Successfully created {role_label} user:")
        print(f"   ID: {admin.id}")
        print(f"   Username: {admin.username}")
        print(f"   Active: {admin.is_active}")
        print(f"   Super Admin: {admin.is_super_admin}")
        print(f"   Created: {admin.created_at}")
        
        print(f"\n🔑 Login credentials:")
        print(f"   Username: {admin.username}")
        print(f"   Password: {password}")
        
        if admin.is_super_admin:
            print(f"\n⚠️  Super Admin Privileges:")
            print(f"   ✓ Create/update/delete other admins")
            print(f"   ✓ Bulk import operations (sales, expenses, payroll)")
            print(f"   ✓ Create/delete branches")
            print(f"   ✓ Delete financial records (payroll, sales)")
        
        print(f"\n🚀 Test authentication at:")
        print(f"   Login: POST http://localhost:8000/api/v1/auth/login")
        print(f"   Protected: GET http://localhost:8000/api/v1/admin/test/protected")
        print(f"   Docs: http://localhost:8000/docs")
        
        return admin
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        if "already registered" in str(e).lower():
            print(f"💡 Tip: Username '{username}' already exists. Try a different username.")
        return None
        
    finally:
        db.close()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Display what we're creating
    role_label = "SUPER ADMIN" if args.super_admin else "REGULAR ADMIN"
    print(f"Creating {role_label} user...")
    print(f"  Username: {args.username}")
    print(f"  Super Admin: {args.super_admin}")
    print(f"  Active: {not args.inactive}")
    print()
    
    # Create the admin
    admin = create_admin_user(
        username=args.username,
        password=args.password,
        is_super_admin=args.super_admin,
        is_active=not args.inactive
    )
    
    if admin:
        print("\n✅ Setup complete! You can now use this admin account.")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        sys.exit(1)