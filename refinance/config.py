"""Application configuration"""

from dataclasses import dataclass


@dataclass
class Config:
    app_name: str
    app_version: str

    def __init__(self) -> None:
        self.app_name = "refinance"
        self.app_version = "0.1.0"

    @property
    def database_path(self):
        return f"./{self.app_name}.db"

    @property
    def database_url(self):
        return f"sqlite:///{self.database_path}"


config = Config()
