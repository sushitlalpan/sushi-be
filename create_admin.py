"""
Create initial admin user for testing.

This script creates the first admin user directly in the database
so we can test the authentication system.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.crud.admin import create_admin
from backend.fastapi.schemas.admin import AdminCreate


def create_initial_admin():
    """Create the initial admin user."""
    
    # Admin credentials
    admin_data = AdminCreate(
        username="admin",
        password="admin123",  # Change this in production!
        is_active=True
    )
    
    # Get database session
    db = next(get_sync_db())
    
    try:
        # Create admin
        admin = create_admin(db, admin_data)
        print(f"✅ Successfully created admin user:")
        print(f"   ID: {admin.id}")
        print(f"   Username: {admin.username}")
        print(f"   Active: {admin.is_active}")
        print(f"   Created: {admin.created_at}")
        
        print(f"\n🔑 Login credentials:")
        print(f"   Username: {admin.username}")
        print(f"   Password: admin123456")
        
        print(f"\n🚀 Test authentication at:")
        print(f"   Login: POST http://localhost:8000/api/v1/auth/login")
        print(f"   Protected: GET http://localhost:8000/api/v1/admin/test/protected")
        print(f"   Docs: http://localhost:8000/docs")
        
        return admin
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return None
        
    finally:
        db.close()


if __name__ == "__main__":
    print("Creating initial admin user...")
    admin = create_initial_admin()
    
    if admin:
        print("\n✅ Setup complete! You can now test the authentication system.")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")