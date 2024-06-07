"""Application configuration"""

from dataclasses import dataclass, field
from os import getenv


@dataclass
class Config:
    app_name: str = "refinance"
    app_version: str = "0.1.0"

    api_tokens: list[str] = field(default_factory=list)

    @property
    def database_path(self) -> str:
        return f"./data/{self.app_name}.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


def get_config():
    return Config(
        api_tokens=getenv("REFINANCE_API_TOKENS", "").split(","),
    )
