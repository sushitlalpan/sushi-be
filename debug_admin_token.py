"""
Debug script to check admin is_super_admin value and JWT token generation.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from backend.fastapi.dependencies.database import SyncSessionLocal
from backend.fastapi.crud.admin import get_admin_by_username
from backend.security.auth import create_admin_token, verify_access_token

def debug_admin_token(username: str):
    """Debug admin token generation."""
    db: Session = SyncSessionLocal()
    
    try:
        # Get admin from database
        admin = get_admin_by_username(db, username)
        
        if not admin:
            print(f"❌ Admin '{username}' not found in database")
            return
        
        print(f"\n{'='*60}")
        print(f"🔍 Admin Debug Information for: {username}")
        print(f"{'='*60}")
        
        # Check database values
        print(f"\n📊 Database Values:")
        print(f"   ID:             {admin.id}")
        print(f"   Username:       {admin.username}")
        print(f"   Is Active:      {admin.is_active}")
        print(f"   Is Super Admin: {admin.is_super_admin}")
        print(f"   Type:           {type(admin.is_super_admin)}")
        
        # Create token
        print(f"\n🔐 Creating JWT Token...")
        access_token = create_admin_token(
            str(admin.id), 
            admin.username, 
            admin.is_super_admin
        )
        print(f"   Token created: {access_token[:50]}...")
        
        # Decode token
        print(f"\n🔓 Decoding JWT Token...")
        payload = verify_access_token(access_token)
        
        print(f"   Payload:")
        for key, value in payload.items():
            if key not in ['exp', 'iat']:  # Skip timestamps for clarity
                print(f"      {key}: {value} (type: {type(value).__name__})")
        
        # Compare
        print(f"\n✅ Comparison:")
        db_value = admin.is_super_admin
        jwt_value = payload.get('is_super_admin')
        
        print(f"   DB value:  {db_value} ({type(db_value).__name__})")
        print(f"   JWT value: {jwt_value} ({type(jwt_value).__name__})")
        
        if db_value == jwt_value:
            print(f"   ✅ Values MATCH")
        else:
            print(f"   ❌ Values DO NOT MATCH!")
            print(f"   This indicates a problem in token creation or serialization")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    # Hardcode username here to avoid argparse conflicts
    USERNAME_TO_CHECK = "admin"  # <-- CHANGE THIS TO YOUR USERNAME
    
    print(f"Checking admin user: {USERNAME_TO_CHECK}")
    print("(Edit the USERNAME_TO_CHECK variable in this file to check a different user)\n")
    
    debug_admin_token(USERNAME_TO_CHECK)
