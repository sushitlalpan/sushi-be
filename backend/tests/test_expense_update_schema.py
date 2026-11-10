from uuid import uuid4

from backend.fastapi.schemas.expense import ExpenseUpdate


def test_expense_update_allows_omitting_worker_and_branch():
    update = ExpenseUpdate(expense_description="Corrected description")

    assert update.model_dump(exclude_unset=True) == {
        "expense_description": "Corrected description"
    }


def test_expense_update_includes_worker_and_branch_when_provided():
    worker_id = uuid4()
    branch_id = uuid4()

    update = ExpenseUpdate(worker_id=worker_id, branch_id=branch_id)

    assert update.model_dump(exclude_unset=True) == {
        "worker_id": worker_id,
        "branch_id": branch_id,
    }
