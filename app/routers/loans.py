"""Loan routes: creation, listing and single lookup with the borrowing rules."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_api_key
from app.errors import ApiError
from app.models import Book, Loan, Member
from app.schemas import LoanCreate, LoanRead

router = APIRouter(prefix="/loans", tags=["loans"])

LOAN_PERIOD_DAYS = 14
MAX_OPEN_LOANS = 3


@router.post("", response_model=LoanRead, status_code=201)
def create_loan(
    payload: LoanCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Loan:
    """Create a loan after checking the member and copy rules."""

    book = db.get(Book, payload.book_id)
    if book is None:
        raise ApiError(404, "book_not_found", f"Book {payload.book_id} does not exist")

    member = db.get(Member, payload.member_id)
    if member is None:
        raise ApiError(404, "member_not_found", f"Member {payload.member_id} does not exist")

    open_loans = db.scalar(
        select(func.count())
        .select_from(Loan)
        .where(Loan.member_id == member.id, Loan.returned_on.is_(None))
    )
    if open_loans >= MAX_OPEN_LOANS:
        raise ApiError(
            409,
            "loan_limit_reached",
            "Member already has 3 open loans",
        )

    open_copies = db.scalar(
        select(func.count())
        .select_from(Loan)
        .where(Loan.book_id == book.id, Loan.returned_on.is_(None))
    )
    if open_copies >= book.copies:
        raise ApiError(
            409,
            "no_free_copy",
            f"All {book.copies} copies of book {book.id} are on loan",
        )

    today = date.today()
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_on=today,
        due_on=today + timedelta(days=LOAN_PERIOD_DAYS),
        returned_on=None,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.get("", response_model=list[LoanRead])
def list_loans(
    member_id: int | None = None,
    book_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Loan]:
    """List loans, optionally filtered by member and/or book."""

    stmt = select(Loan)
    if member_id is not None:
        stmt = stmt.where(Loan.member_id == member_id)
    if book_id is not None:
        stmt = stmt.where(Loan.book_id == book_id)
    return list(db.scalars(stmt.order_by(Loan.id)).all())


@router.get("/{loan_id}", response_model=LoanRead)
def get_loan(loan_id: int, db: Session = Depends(get_db)) -> Loan:
    """Return a single loan or 404 when it does not exist."""

    loan = db.get(Loan, loan_id)
    if loan is None:
        raise ApiError(404, "loan_not_found", f"Loan {loan_id} does not exist")
    return loan
