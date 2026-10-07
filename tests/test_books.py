"""Tests for the book CRUD, search and pagination endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings

_BOOK = {
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "9780132350884",
    "year": 2008,
    "copies": 3,
}


def _create_book(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {**_BOOK, **overrides}
    response = client.post("/books", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _error_code(response) -> str:
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    return body["error"]["code"]


def test_crud_path(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create_book(client, auth_headers)
    assert created["id"] > 0
    assert created["title"] == _BOOK["title"]
    assert created["author"] == _BOOK["author"]
    assert created["isbn"] == _BOOK["isbn"]
    assert created["year"] == _BOOK["year"]
    assert created["copies"] == _BOOK["copies"]

    book_id = created["id"]
    fetched = client.get(f"/books/{book_id}")
    assert fetched.status_code == 200
    assert fetched.json() == created

    updated = client.put(
        f"/books/{book_id}",
        json={"title": "Clean Architecture", "copies": 5},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Clean Architecture"
    assert updated.json()["copies"] == 5

    patched = client.patch(
        f"/books/{book_id}",
        json={"author": "R. C. Martin"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["author"] == "R. C. Martin"
    assert patched.json()["title"] == "Clean Architecture"

    deleted = client.delete(f"/books/{book_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_get_unknown_id_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/books/9999")
    assert response.status_code == 404
    assert _error_code(response) == "not_found"


def test_duplicate_isbn_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create_book(client, auth_headers)
    duplicate = client.post(
        "/books",
        json={**_BOOK, "title": "Another Title"},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409
    assert _error_code(duplicate) == "conflict"
    assert client.get("/books").json()["total"] == 1


def test_put_duplicate_isbn_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = _create_book(client, auth_headers)
    second = _create_book(client, auth_headers, title="Refactoring", isbn="9780134757599")
    conflict = client.put(
        f"/books/{second['id']}",
        json={"isbn": first["isbn"]},
        headers=auth_headers,
    )
    assert conflict.status_code == 409
    assert _error_code(conflict) == "conflict"


def test_invalid_body_returns_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/books", json={"title": "Missing"}, headers=auth_headers)
    assert response.status_code == 422
    assert _error_code(response) == "validation_error"


def test_search_across_title_and_author_case_insensitive(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_book(client, auth_headers, title="The Pragmatic Programmer", isbn="9780201616224")
    _create_book(client, auth_headers, title="Clean Code", isbn="9780132350884")

    by_title = client.get("/books", params={"q": "CLEAN"})
    assert by_title.status_code == 200
    assert [book["title"] for book in by_title.json()["items"]] == ["Clean Code"]

    by_author = client.get("/books", params={"q": "pragmatic"})
    assert by_author.status_code == 200
    titles = [book["title"] for book in by_author.json()["items"]]
    assert titles == ["The Pragmatic Programmer"]

    no_match = client.get("/books", params={"q": "nonexistent"})
    assert no_match.status_code == 200
    assert no_match.json()["total"] == 0
    assert no_match.json()["items"] == []


def test_pagination_reports_total_and_respects_limit_offset(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for index in range(3):
        _create_book(
            client,
            auth_headers,
            title=f"Book {index}",
            author=f"Author {index}",
            isbn=f"isbn-{index}",
        )

    first_page = client.get("/books", params={"limit": 2, "offset": 0})
    assert first_page.status_code == 200
    body = first_page.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2

    second_page = client.get("/books", params={"limit": 2, "offset": 2})
    assert second_page.status_code == 200
    body = second_page.json()
    assert body["total"] == 3
    assert body["offset"] == 2
    assert len(body["items"]) == 1

    invalid_limit = client.get("/books", params={"limit": 101})
    assert invalid_limit.status_code == 422
    assert _error_code(invalid_limit) == "validation_error"


def test_write_without_key_returns_401(client: TestClient, auth_headers: dict[str, str]) -> None:
    missing = client.post("/books", json=_BOOK)
    assert missing.status_code == 401
    assert _error_code(missing) == "unauthorized"

    wrong = client.post("/books", json=_BOOK, headers={"X-API-Key": "wrong-key"})
    assert wrong.status_code == 401
    assert _error_code(wrong) == "unauthorized"
    assert client.get("/books").json()["total"] == 0


def test_write_without_configured_key_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIBRARY_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        response = client.post("/books", json=_BOOK)
        assert response.status_code == 503
        assert _error_code(response) == "api_key_not_configured"
        assert client.get("/books").json()["total"] == 0
    finally:
        get_settings.cache_clear()
