"""Application configuration"""

from dataclasses import dataclass, field
from os import getenv


@dataclass
class Config:
    secret_key: str | None = field(default=getenv("REFINANCE_SECRET_KEY", ""))
    telegram_bot_api_token: str | None = field(
        default=getenv("REFINANCE_TELEGRAM_BOT_API_TOKEN", "")
    )

    app_name: str = "refinance"
    app_version: str = "0.1.0"

    @property
    def database_path(self) -> str:
        return f"./data/{self.app_name}.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


def get_config():
    return Config()
