"""Loan return routes.

Included before the loans router so that the static ``/loans/overdue`` path is
matched before the dynamic ``/loans/{loan_id}`` path.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_api_key
from app.errors import ApiError
from app.models import Loan
from app.schemas import LoanRead

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/overdue", response_model=list[LoanRead])
def list_overdue_loans(db: Session = Depends(get_db)) -> list[Loan]:
    """Return every open loan whose due date is before today."""

    today = date.today()
    statement = (
        select(Loan)
        .where(Loan.returned_on.is_(None))
        .where(Loan.due_on < today)
        .order_by(Loan.due_on, Loan.id)
    )
    return list(db.scalars(statement).all())


@router.post(
    "/{loan_id}/return",
    response_model=LoanRead,
    dependencies=[Depends(require_api_key)],
)
def return_loan(loan_id: int, db: Session = Depends(get_db)) -> Loan:
    """Mark an open loan as returned today."""

    loan = db.get(Loan, loan_id)
    if loan is None:
        raise ApiError(404, "loan_not_found", f"Loan {loan_id} does not exist")
    if loan.returned_on is not None:
        raise ApiError(409, "loan_already_returned", "Loan already returned")

    loan.returned_on = date.today()
    db.commit()
    db.refresh(loan)
    return loan
