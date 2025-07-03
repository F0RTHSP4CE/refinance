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
    api_url: str | None = field(default=getenv("REFINANCE_API_URL", ""))

    app_name: str = "refinance"
    app_version: str = "0.1.0"

    cryptapi_address_erc20_usdt: str | None = field(
        default=getenv("REFINANCE_CRYPTAPI_ADDRESS_ERC20_USDT", "")
    )
    cryptapi_address_trc20_usdt: str | None = field(
        default=getenv("REFINANCE_CRYPTAPI_ADDRESS_TRC20_USDT", "")
    )
    # Optional database URL for Postgres or other databases
    database_url_env: str | None = field(default=getenv("REFINANCE_DATABASE_URL", None))

    @property
    def database_path(self) -> Path:
        return Path("./data/") / Path(f"{self.app_name}.db")

    @property
    def database_url(self) -> str:
        # Use provided DATABASE_URL if available, else fall back to SQLite file
        if self.database_url_env:
            return self.database_url_env
        return f"sqlite:///{self.database_path}"


def get_config():
    return Config()
