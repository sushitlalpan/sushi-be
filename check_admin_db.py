"""
Quick script to check admin data directly from database.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.fastapi.dependencies.database import SyncSessionLocal
from backend.fastapi.models.admin import Admin

def check_admin_in_db(username: str = None):
    """Check admin records in database."""
    db = SyncSessionLocal()
    
    try:
        if username:
            admins = db.query(Admin).filter(Admin.username == username).all()
            print(f"\n🔍 Searching for admin: {username}")
        else:
            admins = db.query(Admin).all()
            print(f"\n🔍 All admins in database:")
        
        if not admins:
            print(f"❌ No admins found")
            return
        
        print(f"\n{'='*80}")
        for admin in admins:
            print(f"ID:             {admin.id}")
            print(f"Username:       {admin.username}")
            print(f"Is Active:      {admin.is_active}")
            print(f"Is Super Admin: {admin.is_super_admin} (Python type: {type(admin.is_super_admin).__name__})")
            print(f"Created:        {admin.created_at}")
            print(f"Updated:        {admin.updated_at}")
            print(f"{'='*80}")
            
            # Also check the raw value
            print(f"\nRaw column access test:")
            print(f"   admin.is_super_admin = {repr(admin.is_super_admin)}")
            print(f"   bool(admin.is_super_admin) = {bool(admin.is_super_admin)}")
            print(f"   str(admin.is_super_admin) = {str(admin.is_super_admin)}")
            print(f"{'='*80}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    # Hardcode username here to avoid argparse conflicts
    USERNAME_TO_CHECK = "admin"  # <-- CHANGE THIS or set to None to see all admins
    
    if USERNAME_TO_CHECK:
        print(f"Checking specific admin: {USERNAME_TO_CHECK}")
    else:
        print("Checking all admins in database")
    
    check_admin_in_db(USERNAME_TO_CHECK)
