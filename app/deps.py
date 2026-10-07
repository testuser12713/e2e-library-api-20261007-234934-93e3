"""Shared FastAPI dependencies."""

from fastapi import Header

from app.config import get_settings
from app.errors import ApiError


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard a write route with the configured API key.

    - 503 when no key is configured at all, so the app keeps running and reads
      stay available.
    - 401 when a key is configured but the request is missing it or sends the
      wrong one.
    """

    configured = get_settings().library_api_key
    if not configured:
        raise ApiError(
            503,
            "api_key_not_configured",
            "No API key is configured; write operations are disabled",
        )
    if x_api_key != configured:
        raise ApiError(401, "unauthorized", "Missing or invalid API key")
