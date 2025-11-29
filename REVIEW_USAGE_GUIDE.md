# Review Endpoint Usage Guide

## Issue Resolution

The 422 Unprocessable Content error you encountered was due to two issues:

1. **Required vs Optional Fields**: The `review_state` field was set as required in base schemas, causing validation errors for existing records
2. **Missing Enum Validation**: The API wasn't properly validating the accepted review state values

## Fixed Issues

✅ **Made review fields optional**: `review_state` is now optional in base schemas with default value "pending"  
✅ **Added proper enum validation**: Created `ReviewState` enum with accepted values  
✅ **Updated all three modules**: expense, payroll, and sales now use consistent validation

## Accepted Review State Values

The `review_state` field accepts exactly these three values:
- `"pending"` (default for new records)
- `"approved"` 
- `"rejected"`

## API Usage Examples

### Update Expense Review Status
```bash
# Approve an expense
curl -X PATCH "http://localhost:5000/api/v1/expenses/{expense_id}/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "review_state": "approved",
    "review_observations": "Purchase approved - receipt verified"
  }'

# Reject an expense  
curl -X PATCH "http://localhost:5000/api/v1/expenses/{expense_id}/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "review_state": "rejected",
    "review_observations": "Missing receipt - please resubmit with documentation"
  }'
```

### Update Payroll Review Status
```bash
# Approve payroll
curl -X PATCH "http://localhost:5000/api/v1/payroll/{payroll_id}/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "review_state": "approved",
    "review_observations": "Hours verified with timesheet"
  }'
```

### Update Sales Review Status
```bash
# Reject sales record
curl -X PATCH "http://localhost:5000/api/v1/sales/{sales_id}/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "review_state": "rejected", 
    "review_observations": "Discrepancy too large - please recheck calculations"
  }'
```

### Get Records by Review State
```bash
# Get pending expenses
curl -X GET "http://localhost:5000/api/v1/expenses/pending-review" \
  -H "Authorization: Bearer {admin_token}"

# Get approved payroll records
curl -X GET "http://localhost:5000/api/v1/payroll/review/approved?limit=50" \
  -H "Authorization: Bearer {admin_token}"

# Get rejected sales records
curl -X GET "http://localhost:5000/api/v1/sales/review/rejected" \
  -H "Authorization: Bearer {admin_token}"
```

## Error Handling

### 422 Validation Errors
If you get a 422 error, check:
- `review_state` must be exactly: `"pending"`, `"approved"`, or `"rejected"`
- Case matters - use lowercase values
- `review_observations` is optional but if provided should be a string

### 400 Bad Request  
- Invalid review_state values in URL path parameters
- Example: `/api/v1/expenses/review/invalid_state` will return 400

### 404 Not Found
- Record with specified ID doesn't exist
- Check that the expense/payroll/sales ID is correct

### 403 Forbidden
- Only admins can update review status
- Ensure you're using an admin token, not a regular user token

## Schema Validation

The schemas now include proper enum validation:

```python
from enum import Enum

class ReviewState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"  
    REJECTED = "rejected"
```

This ensures that only valid values are accepted and provides better API documentation in the OpenAPI/Swagger interface.

## Testing

You can test the endpoints are working by:

1. **Create a test record** (expense/payroll/sales)
2. **Check it has default review_state="pending"**  
3. **Update review status** using the PATCH endpoints
4. **Verify the change** by fetching the record again

All records created going forward will have `review_state="pending"` by default, and existing records will show `review_state="pending"` due to the database migration default values.