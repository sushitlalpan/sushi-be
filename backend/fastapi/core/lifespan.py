from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.fastapi.dependencies.database import init_db, AsyncSessionLocal, get_sync_db
from backend.fastapi.crud.message import create_message_dict_async
from backend.fastapi.crud.admin import create_admin, get_admin_count
from backend.fastapi.schemas.admin import AdminCreate
from backend.data.init_data import models_data
import os

# Import all models to ensure they're registered with Base.metadata
from backend.fastapi.models import Message, Admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database connection
    init_db()

    # Insert the initial data
    async with AsyncSessionLocal() as db:
        try:
            for raw_data in models_data:
                await create_message_dict_async(db, raw_data)
        finally:
            await db.close()

    # Create initial admin if none exists
    sync_db = next(get_sync_db())
    try:
        admin_count = get_admin_count(sync_db)
        if admin_count == 0:
            # Get admin credentials from environment or use defaults
            admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123456")
            
            admin_data = AdminCreate(
                username=admin_username,
                password=admin_password,
                is_active=True
            )
            
            admin = create_admin(sync_db, admin_data)
            print(f"🚀 Created initial admin user: {admin.username}")
            print(f"🔑 Default password: {admin_password}")
            print("⚠️  Please change the password after first login!")
        else:
            print(f"✅ Found {admin_count} existing admin(s)")
    except Exception as e:
        print(f"❌ Error creating initial admin: {e}")
    finally:
        sync_db.close()

    yield