# Database Migrations

## Running Migrations in Production (Railway)

### Option 1: Using Migration Runner (Recommended)
```bash
# Connect to Railway
railway ssh

# Run migration using the runner script
python run_migration.py add_review_fields
```

### Option 2: Manual Migration
```bash
# Connect to Railway
railway ssh

# Set Python path and run migration
PYTHONPATH=/app python migrations/add_review_fields.py
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