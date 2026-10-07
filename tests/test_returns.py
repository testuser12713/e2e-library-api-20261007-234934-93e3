"""Tests for loan return and the overdue list."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, Loan, Member


def _create_book(db: Session, isbn: str) -> Book:
    book = Book(title="Testbuch", author="Testautor", isbn=isbn, year=2020, copies=3)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _create_member(db: Session, email: str) -> Member:
    member = Member(name="Testmitglied", email=email, member_since=date(2020, 1, 1))
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def _create_loan(
    db: Session,
    book: Book,
    member: Member,
    due_on: date,
    returned_on: date | None = None,
) -> Loan:
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_on=date.today(),
        due_on=due_on,
        returned_on=returned_on,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def test_return_open_loan_sets_today(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _create_book(db_session, "isbn-return-1")
    member = _create_member(db_session, "return1@example.com")
    loan = _create_loan(db_session, book, member, date.today() + timedelta(days=14))

    response = client.post(f"/loans/{loan.id}/return", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == loan.id
    assert body["returned_on"] == date.today().isoformat()

    db_session.refresh(loan)
    assert loan.returned_on == date.today()


def test_return_twice_is_conflict(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _create_book(db_session, "isbn-return-2")
    member = _create_member(db_session, "return2@example.com")
    loan = _create_loan(db_session, book, member, date.today() + timedelta(days=14))

    first = client.post(f"/loans/{loan.id}/return", headers=auth_headers)
    assert first.status_code == 200

    second = client.post(f"/loans/{loan.id}/return", headers=auth_headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "loan_already_returned"


def test_return_unknown_id_is_not_found(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    response = client.post("/loans/999999/return", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "loan_not_found"


def test_overdue_lists_only_open_past_due_loans(client: TestClient, db_session: Session) -> None:
    book = _create_book(db_session, "isbn-overdue-1")
    member = _create_member(db_session, "overdue1@example.com")

    overdue = _create_loan(db_session, book, member, date.today() - timedelta(days=1))
    returned = _create_loan(
        db_session,
        book,
        member,
        date.today() - timedelta(days=5),
        returned_on=date.today() - timedelta(days=2),
    )
    future = _create_loan(db_session, book, member, date.today() + timedelta(days=3))

    response = client.get("/loans/overdue")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert overdue.id in ids
    assert returned.id not in ids
    assert future.id not in ids


def test_return_requires_api_key(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _create_book(db_session, "isbn-return-3")
    member = _create_member(db_session, "return3@example.com")
    loan = _create_loan(db_session, book, member, date.today() + timedelta(days=14))

    response = client.post(f"/loans/{loan.id}/return")

    assert response.status_code == 401
