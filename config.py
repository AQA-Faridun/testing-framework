from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Run settings: environment variables first, then .env in the project root, then the defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    stand_name: str = "local"
    api_base_url: str = "http://localhost"
    web_base_url: str = "http://localhost"
    api_timeout_s: float = Field(default=60.0, gt=0)
    ui_timeout_ms: int = Field(default=15_000, gt=0)
    web_artifacts: Literal["on-failure", "always"] = "on-failure"


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once per process."""
    return Settings()
