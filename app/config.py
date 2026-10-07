"""Application configuration read from the environment.

The settings are constructed lazily so that importing this module never fails
when a variable is missing. ``LIBRARY_API_KEY`` is optional: the app boots and
serves reads without it, while write routes answer 503 until a key is set.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the library API."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    library_api_key: str | None = None
    database_url: str = "sqlite:///./library.db"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
