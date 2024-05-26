"""Application configuration"""

from dataclasses import dataclass


@dataclass
class Config:
    app_name: str = "refinance"
    app_version: str = "0.1.0"

    @property
    def database_path(self):
        return f"./data/{self.app_name}.db"

    @property
    def database_url(self):
        return f"sqlite:///{self.database_path}"


def get_config():
    return Config()
