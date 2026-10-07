"""Tests for loan creation, listing and the borrowing rules."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, Member

BOOK_URL = "/loans"


def _book(db: Session, *, isbn: str = "isbn-1", copies: int = 1, title: str = "Title") -> Book:
    book = Book(title=title, author="Author", isbn=isbn, year=2000, copies=copies)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _member(db: Session, *, email: str = "member@example.com") -> Member:
    member = Member(name="Member", email=email, member_since=date(2020, 1, 1))
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def test_create_loan_sets_today_and_due_date(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _book(db_session, copies=1)
    member = _member(db_session)

    response = client.post(
        BOOK_URL,
        json={"book_id": book.id, "member_id": member.id},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    today = date.today()
    assert body["book_id"] == book.id
    assert body["member_id"] == member.id
    assert body["loaned_on"] == today.isoformat()
    assert body["due_on"] == (today + timedelta(days=14)).isoformat()
    assert body["returned_on"] is None


def test_fourth_open_loan_is_rejected(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _book(db_session, copies=10)
    member = _member(db_session)
    for _ in range(3):
        assert (
            client.post(
                BOOK_URL,
                json={"book_id": book.id, "member_id": member.id},
                headers=auth_headers,
            ).status_code
            == 201
        )

    conflict = client.post(
        BOOK_URL,
        json={"book_id": book.id, "member_id": member.id},
        headers=auth_headers,
    )

    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "loan_limit_reached"
    listed = client.get(BOOK_URL, params={"member_id": member.id}).json()
    assert len(listed) == 3


def test_loan_on_exhausted_copies_is_rejected(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _book(db_session, copies=1)
    first = _member(db_session, email="first@example.com")
    second = _member(db_session, email="second@example.com")

    assert (
        client.post(
            BOOK_URL,
            json={"book_id": book.id, "member_id": first.id},
            headers=auth_headers,
        ).status_code
        == 201
    )

    conflict = client.post(
        BOOK_URL,
        json={"book_id": book.id, "member_id": second.id},
        headers=auth_headers,
    )

    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "no_free_copy"
    assert len(client.get(BOOK_URL, params={"book_id": book.id}).json()) == 1


def test_unknown_book_id_returns_404(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    member = _member(db_session)

    response = client.post(
        BOOK_URL,
        json={"book_id": 999999, "member_id": member.id},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "book_not_found"


def test_unknown_member_id_returns_404(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _book(db_session)

    response = client.post(
        BOOK_URL,
        json={"book_id": book.id, "member_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "member_not_found"


def test_list_loans_filters_by_member_and_book(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book_a = _book(db_session, isbn="isbn-a", copies=5, title="A")
    book_b = _book(db_session, isbn="isbn-b", copies=5, title="B")
    member_a = _member(db_session, email="a@example.com")
    member_b = _member(db_session, email="b@example.com")

    client.post(
        BOOK_URL, json={"book_id": book_a.id, "member_id": member_a.id}, headers=auth_headers
    )
    client.post(
        BOOK_URL, json={"book_id": book_b.id, "member_id": member_b.id}, headers=auth_headers
    )

    by_member = client.get(BOOK_URL, params={"member_id": member_a.id}).json()
    assert len(by_member) == 1
    assert by_member[0]["member_id"] == member_a.id
    assert by_member[0]["book_id"] == book_a.id

    by_book = client.get(BOOK_URL, params={"book_id": book_b.id}).json()
    assert len(by_book) == 1
    assert by_book[0]["book_id"] == book_b.id

    all_loans = client.get(BOOK_URL).json()
    assert len(all_loans) == 2


def test_get_loan_by_id_and_unknown_id(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _book(db_session)
    member = _member(db_session)
    created = client.post(
        BOOK_URL,
        json={"book_id": book.id, "member_id": member.id},
        headers=auth_headers,
    ).json()

    found = client.get(f"{BOOK_URL}/{created['id']}")
    assert found.status_code == 200
    assert found.json()["id"] == created["id"]

    assert client.get(f"{BOOK_URL}/999999").status_code == 404


def test_create_loan_requires_api_key(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _book(db_session)
    member = _member(db_session)

    response = client.post(BOOK_URL, json={"book_id": book.id, "member_id": member.id})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
