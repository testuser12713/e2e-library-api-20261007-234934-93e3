"""Tests for the member CRUD endpoints."""

from fastapi.testclient import TestClient

_MEMBER = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "member_since": "2020-01-01",
}


def _create(client: TestClient, auth_headers: dict[str, str], **overrides: str) -> dict:
    payload = {**_MEMBER, **overrides}
    response = client.post("/members", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


def test_create_member_returns_201(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/members", json=_MEMBER, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == _MEMBER["name"]
    assert body["email"] == _MEMBER["email"]
    assert body["member_since"] == _MEMBER["member_since"]


def test_create_member_duplicate_email_returns_409(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create(client, auth_headers)

    response = client.post("/members", json=_MEMBER, headers=auth_headers)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "duplicate_email"
    assert len(client.get("/members").json()) == 1


def test_create_member_invalid_input_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/members",
        json={"name": "No mail", "email": "no-mail@example.com"},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_member_crud_path(client: TestClient, auth_headers: dict[str, str]) -> None:
    member_id = _create(client, auth_headers)["id"]

    listed = client.get("/members")
    assert listed.status_code == 200
    assert [member["id"] for member in listed.json()] == [member_id]

    fetched = client.get(f"/members/{member_id}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == _MEMBER["email"]

    updated = client.put(f"/members/{member_id}", json={"name": "Ada Byron"}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Ada Byron"
    assert updated.json()["email"] == _MEMBER["email"]

    patched = client.patch(
        f"/members/{member_id}",
        json={"email": "ada.byron@example.com"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["email"] == "ada.byron@example.com"

    deleted = client.delete(f"/members/{member_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/members/{member_id}").status_code == 404


def test_get_unknown_member_returns_404_uniform_body(client: TestClient) -> None:
    response = client.get("/members/9999")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}


def test_update_unknown_member_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.put("/members/9999", json={"name": "X"}, headers=auth_headers).status_code == 404
    assert (
        client.patch("/members/9999", json={"name": "X"}, headers=auth_headers).status_code == 404
    )


def test_delete_unknown_member_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.delete("/members/9999", headers=auth_headers).status_code == 404


def test_update_to_duplicate_email_returns_409(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _create(client, auth_headers)
    second = _create(client, auth_headers, email="grace@example.com", name="Grace Hopper")

    response = client.put(
        f"/members/{second['id']}",
        json={"email": first["email"]},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"
    assert client.get(f"/members/{second['id']}").json()["email"] == "grace@example.com"


def test_update_invalid_input_returns_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    member_id = _create(client, auth_headers)["id"]

    response = client.patch(
        f"/members/{member_id}", json={"member_since": "not-a-date"}, headers=auth_headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_write_routes_require_valid_api_key(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.post("/members", json=_MEMBER).status_code == 401
    assert (
        client.post("/members", json=_MEMBER, headers={"X-API-Key": "wrong-key"}).status_code == 401
    )
    assert client.get("/members").json() == []
