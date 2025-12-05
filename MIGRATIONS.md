# Database Migrations

## Available Migrations

### 1. add_review_fields
Adds `review_state` and `review_observations` fields to expense, payroll, and sales tables.
- Default review_state: 'pending'
- Supports review states: pending, approved, rejected

### 2. add_soft_delete
Adds `deleted_at` timestamp fields to users and branches tables for soft delete support.
- Prevents data loss from user/branch deletions
- Preserves historical records for payroll, sales, and expenses
- Creates indexes on deleted_at for query performance

## Running Migrations in Production (Railway)

### Option 1: Using Migration Runner (Recommended)
```bash
# Connect to Railway
railway ssh

# Run specific migration using the runner script
python run_migration.py add_review_fields
python run_migration.py add_soft_delete
```

### Option 2: Manual Migration
```bash
# Connect to Railway
railway ssh

# Set Python path and run migration
PYTHONPATH=/app python migrations/add_review_fields.py
PYTHONPATH=/app python migrations/add_soft_delete.py
```

## Creating New Migrations

1. Create migration file in `migrations/` directory
2. Follow the pattern of existing migrations
3. Include proper path setup at the beginning:
```python
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

## Migration Checklist

- [ ] Test migration locally first
- [ ] Back up production database before running
- [ ] Run migration during low traffic period
- [ ] Verify migration success in logs
- [ ] Test application endpoints after migration
- [ ] Monitor for any errors post-migration