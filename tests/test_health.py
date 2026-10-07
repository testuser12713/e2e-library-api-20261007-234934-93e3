"""Tests for the health endpoint, error format and API-key guard."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.deps import require_api_key
from app.errors import ApiError


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_works_without_api_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIBRARY_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        get_settings.cache_clear()


def test_unknown_path_uses_uniform_error_format(client: TestClient) -> None:
    response = client.get("/this-path-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)


def test_require_api_key_answers_503_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIBRARY_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ApiError) as exc_info:
            require_api_key(None)
        assert exc_info.value.status_code == 503
    finally:
        get_settings.cache_clear()


def test_require_api_key_rejects_missing_or_wrong_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIBRARY_API_KEY", "configured-key")
    get_settings.cache_clear()
    try:
        with pytest.raises(ApiError) as missing:
            require_api_key(None)
        assert missing.value.status_code == 401

        with pytest.raises(ApiError) as wrong:
            require_api_key("another-key")
        assert wrong.value.status_code == 401

        require_api_key("configured-key")
    finally:
        get_settings.cache_clear()


def test_configured_api_key_is_accepted(
    auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    require_api_key(auth_headers["X-API-Key"])
