from fastapi import FastAPI
from backend.fastapi.api.v1.endpoints import base, doc, message, admin, user, time_entry, branch, payroll, sales, expense, general

def setup_routers(app: FastAPI):
    # Main and documentation routes
    app.include_router(base.router, prefix="", tags=["main"])
    app.include_router(doc.router, prefix="", tags=["doc"])
    
    # API v1 routes
    app.include_router(message.router, prefix="/api/v1", tags=["message"])
    
    # Authentication routes (separate endpoints for different user types)
    app.include_router(admin.router, prefix="/api/v1/auth/admin", tags=["admin-authentication"])
    app.include_router(user.router, prefix="/api/v1/auth/user", tags=["user-authentication"])
    
    # User management routes
    app.include_router(admin.admin_router, prefix="/api/v1/admin", tags=["admin-management"])
    app.include_router(user.user_router, prefix="/api/v1/users", tags=["user-management"])
    
    # Time tracking routes
    app.include_router(time_entry.router, prefix="/api/v1/time", tags=["time-tracking"])
    app.include_router(time_entry.admin_router, prefix="/api/v1/time", tags=["admin-time-management"])
    
    # Branch management routes
    app.include_router(branch.router, prefix="/api/v1/branches", tags=["branch-management"])
    
    # Payroll management routes
    app.include_router(payroll.router, prefix="/api/v1/payroll", tags=["payroll-management"])
    
    # Sales and cash register closure routes
    app.include_router(sales.router, prefix="/api/v1/sales", tags=["sales-management"])
    
    # Expense and reimbursement management routes
    app.include_router(expense.router, prefix="/api/v1/expenses", tags=["expense-management"])
    
    # General combined data routes
    app.include_router(general.router, prefix="/api/v1/general", tags=["general-data"])
