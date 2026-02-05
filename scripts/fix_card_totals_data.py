"""
Data correction script to fix card_total calculations in Sales records.

The card_total formula was incorrectly including card_itpv. This script
recalculates card_total and discrepancy for all existing sales records.

Corrected formula: card_total = card_kiwi + transfer_amt - card_refund

Run with: python scripts/fix_card_totals_data.py [--dry-run]
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.fastapi.models.sales import Sales
from backend.fastapi.core.config import settings


def calculate_correct_card_total(sale: Sales) -> tuple[Decimal, Decimal]:
    """
    Calculate correct card_total and discrepancy.
    
    Returns:
        Tuple of (new_card_total, new_discrepancy)
    """
    # Correct formula: excludes card_itpv
    card_total = sale.card_kiwi + sale.transfer_amt - sale.card_refund
    
    # Recalculate discrepancy with correct card_total
    cash_total = sale.cash_amt - sale.cash_refund
    payment_total = card_total + cash_total
    discrepancy = payment_total - sale.sales_total
    
    return card_total, discrepancy


def fix_card_totals(dry_run: bool = False):
    """
    Fix card_total and discrepancy for all sales records.
    
    Args:
        dry_run: If True, only show what would be changed without committing
    """
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Query all sales records
        sales_records = db.query(Sales).all()
        total_records = len(sales_records)
        
        print(f"\n{'='*80}")
        print(f"Card Total Data Correction Script")
        print(f"{'='*80}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
        print(f"Total records to process: {total_records}")
        print(f"{'='*80}\n")
        
        # Track changes
        changes = []
        records_with_changes = 0
        
        # Process each record
        for i, sale in enumerate(sales_records, 1):
            # Calculate correct values
            old_card_total = sale.card_total
            old_discrepancy = sale.discrepancy
            
            new_card_total, new_discrepancy = calculate_correct_card_total(sale)
            
            # Check if values changed
            card_total_changed = abs(old_card_total - new_card_total) > Decimal("0.01")
            discrepancy_changed = abs(old_discrepancy - new_discrepancy) > Decimal("0.01")
            
            if card_total_changed or discrepancy_changed:
                records_with_changes += 1
                
                change_info = {
                    "id": str(sale.id),
                    "closure_number": sale.closure_number,
                    "closure_date": sale.closure_date,
                    "worker_id": str(sale.worker_id),
                    "old_card_total": float(old_card_total),
                    "new_card_total": float(new_card_total),
                    "card_total_diff": float(new_card_total - old_card_total),
                    "old_discrepancy": float(old_discrepancy),
                    "new_discrepancy": float(new_discrepancy),
                    "review_state": sale.review_state
                }
                changes.append(change_info)
                
                # Print first 10 changes as sample
                if records_with_changes <= 10:
                    print(f"Record {i}/{total_records} - Closure #{sale.closure_number}")
                    print(f"  Card Total: {old_card_total} → {new_card_total} "
                          f"(diff: {new_card_total - old_card_total:+.2f})")
                    print(f"  Discrepancy: {old_discrepancy} → {new_discrepancy} "
                          f"(diff: {new_discrepancy - old_discrepancy:+.2f})")
                    print()
                
                # Apply changes if not dry run
                if not dry_run:
                    sale.card_total = new_card_total
                    sale.discrepancy = new_discrepancy
        
        # Commit changes if not dry run
        if not dry_run and records_with_changes > 0:
            db.commit()
            print(f"\n✓ Changes committed to database")
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total records processed: {total_records}")
        print(f"Records with changes: {records_with_changes}")
        print(f"Records unchanged: {total_records - records_with_changes}")
        
        if records_with_changes > 0:
            # Calculate statistics
            total_card_diff = sum(c["card_total_diff"] for c in changes)
            avg_card_diff = total_card_diff / records_with_changes
            max_card_diff = max(abs(c["card_total_diff"]) for c in changes)
            
            print(f"\nCard Total Changes:")
            print(f"  Total difference: {total_card_diff:+.2f}")
            print(f"  Average difference: {avg_card_diff:+.2f}")
            print(f"  Max absolute difference: {max_card_diff:.2f}")
            
            # Review state breakdown
            review_states = {}
            for change in changes:
                state = change["review_state"]
                review_states[state] = review_states.get(state, 0) + 1
            
            print(f"\nAffected records by review state:")
            for state, count in sorted(review_states.items()):
                print(f"  {state}: {count}")
        
        print(f"{'='*80}\n")
        
        # Save detailed log
        if changes and not dry_run:
            log_filename = f"card_total_fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_filename, 'w') as f:
                f.write("Card Total Data Correction Log\n")
                f.write(f"Executed: {datetime.now().isoformat()}\n")
                f.write(f"Records changed: {records_with_changes}\n\n")
                
                for change in changes:
                    f.write(f"ID: {change['id']}\n")
                    f.write(f"  Closure #{change['closure_number']} - {change['closure_date']}\n")
                    f.write(f"  Card Total: {change['old_card_total']} → {change['new_card_total']}\n")
                    f.write(f"  Discrepancy: {change['old_discrepancy']} → {change['new_discrepancy']}\n")
                    f.write(f"  Review State: {change['review_state']}\n\n")
            
            print(f"✓ Detailed log saved to: {log_filename}\n")
        
        if dry_run:
            print("⚠ DRY RUN MODE - No changes were made to the database")
            print("  Run without --dry-run to apply changes\n")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    if not dry_run:
        print("\n⚠ WARNING: This will modify database records!")
        print("  Press Ctrl+C to cancel, or Enter to continue...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)
    
    fix_card_totals(dry_run=dry_run)
