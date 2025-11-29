# Review System API Endpoints

This document describes the new review system endpoints added to the expense, payroll, and sales modules.

## Overview

The review system allows administrators to approve, reject, or leave pending any expense, payroll, or sales record. Each record has:
- `review_state`: `pending` (default), `approved`, or `rejected`
- `review_observations`: Optional text comments from the reviewer

## Expense Review Endpoints

### Update Expense Review Status
- **PATCH** `/api/v1/expenses/{expense_id}/review`
- **Permission**: Admin only
- **Body**: `ExpenseReviewUpdate`
  ```json
  {
    "review_state": "approved|rejected|pending",
    "review_observations": "Optional reviewer comments"
  }
  ```
- **Response**: Updated `ExpenseRead` object

### Get Expenses Pending Review
- **GET** `/api/v1/expenses/pending-review`
- **Permission**: Admin only
- **Query Parameters**: `skip`, `limit`
- **Response**: List of `ExpenseWithDetails`

### Get Expenses by Review State
- **GET** `/api/v1/expenses/review/{review_state}`
- **Permission**: Admin only
- **Path Parameter**: `review_state` (pending|approved|rejected)
- **Query Parameters**: `skip`, `limit`
- **Response**: List of `ExpenseWithDetails`

## Payroll Review Endpoints

### Update Payroll Review Status
- **PATCH** `/api/v1/payroll/{payroll_id}/review`
- **Permission**: Admin only
- **Body**: `PayrollReviewUpdate`
  ```json
  {
    "review_state": "approved|rejected|pending",
    "review_observations": "Optional reviewer comments"
  }
  ```
- **Response**: Updated `PayrollRead` object

### Get Payroll Records Pending Review
- **GET** `/api/v1/payroll/pending-review`
- **Permission**: Admin only
- **Query Parameters**: `skip`, `limit`
- **Response**: List of `PayrollWithDetails`

### Get Payroll Records by Review State
- **GET** `/api/v1/payroll/review/{review_state}`
- **Permission**: Admin only
- **Path Parameter**: `review_state` (pending|approved|rejected)
- **Query Parameters**: `skip`, `limit`
- **Response**: List of `PayrollWithDetails`

## Sales Review Endpoints

### Update Sales Review Status
- **PATCH** `/api/v1/sales/{sales_id}/review`
- **Permission**: Admin only
- **Body**: `SalesReviewUpdate`
  ```json
  {
    "review_state": "approved|rejected|pending",
    "review_observations": "Optional reviewer comments"
  }
  ```
- **Response**: Updated `SalesRead` object

### Get Sales Records Pending Review
- **GET** `/api/v1/sales/pending-review`
- **Permission**: Admin only
- **Query Parameters**: `skip`, `limit`
- **Response**: List of `SalesWithDetails`

### Get Sales Records by Review State
- **GET** `/api/v1/sales/review/{review_state}`
- **Permission**: Admin only
- **Path Parameter**: `review_state` (pending|approved|rejected)
- **Query Parameters**: `skip`, `limit`
- **Response**: List of `SalesWithDetails`

## Usage Examples

### Approve an Expense
```bash
curl -X PATCH "http://localhost:5000/api/v1/expenses/{expense_id}/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "review_state": "approved",
    "review_observations": "Expense looks good, receipt verified"
  }'
```

### Reject a Payroll Entry
```bash
curl -X PATCH "http://localhost:5000/api/v1/payroll/{payroll_id}/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "review_state": "rejected",
    "review_observations": "Hours worked seem excessive, please verify"
  }'
```

### Get Pending Sales Reviews
```bash
curl -X GET "http://localhost:5000/api/v1/sales/pending-review?limit=50" \
  -H "Authorization: Bearer {admin_token}"
```

### Get Approved Expenses
```bash
curl -X GET "http://localhost:5000/api/v1/expenses/review/approved?skip=0&limit=100" \
  -H "Authorization: Bearer {admin_token}"
```

## Database Changes

The following columns were added to the database:

### expenses table
- `review_state` VARCHAR(20) NOT NULL DEFAULT 'pending' (indexed)
- `review_observations` TEXT

### payroll table  
- `review_state` VARCHAR(20) NOT NULL DEFAULT 'pending' (indexed)
- `review_observations` VARCHAR(1000)

### sales table
- `review_state` VARCHAR(20) NOT NULL DEFAULT 'pending' (indexed)
- `review_observations` TEXT

## CRUD Functions Added

Each module now includes these new functions:
- `get_{module}_by_review_state()` - Filter by review status
- `get_{module}_pending_review()` - Get records needing review
- `update_{module}_review_status()` - Update review status and observations

## Schema Updates

New Pydantic schemas:
- `ExpenseReviewUpdate` / `PayrollReviewUpdate` / `SalesReviewUpdate`
- `ExpenseReviewSummary` / `PayrollReviewSummary` / `SalesReviewSummary`

All base schemas now include:
- `review_state` field with validation
- `review_observations` field
- Validators to ensure proper review state values

## Migration

The database migration script `migrations/add_review_fields.py` was created and executed successfully to add the new columns and indexes.

## Security

- Only administrators can update review statuses
- Only administrators can view review-filtered lists
- Regular users can see their own record's review status but cannot modify it
- All review operations are logged through the standard audit trail