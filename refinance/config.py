"""Application configuration"""

from logging import getLogger
from os import environ
from typing import Any, Self

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = getLogger(__name__)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", env_nested_delimiter="__", extra="ignore")

    app_name: str = "refinance"
    app_version: str = "0.1.0"

    @property
    def database_path(self) -> str:
        return f"./{self.app_name}.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize config."""
        super().__init__(*args, **kwargs)
        logger.debug(f"Config initialized: {self.model_dump()}")

    @classmethod
    def from_env(cls) -> Self:
        """Create config from environment variables."""
        return cls(
            _env_file=environ.get("ENV_FILE", ".env"),
            _secrets_dir=environ.get("SECRETS_DIR"),
        )


def get_config() -> Config:
    return Config()
