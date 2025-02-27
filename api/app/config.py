"""Application configuration"""

from dataclasses import dataclass, field
from os import getenv
from pathlib import Path


@dataclass
class Config:
    secret_key: str | None = field(default=getenv("REFINANCE_SECRET_KEY", ""))
    telegram_bot_api_token: str | None = field(
        default=getenv("REFINANCE_TELEGRAM_BOT_API_TOKEN", "")
    )
    ui_url: str | None = field(default=getenv("REFINANCE_UI_URL", ""))

    app_name: str = "refinance"
    app_version: str = "0.1.0"

    @property
    def database_path(self) -> Path:
        return Path("./data/") / Path(f"{self.app_name}.db")

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


def get_config():
    return Config()
