"""Application configuration"""


class Config:
    app_name: str
    app_version: str

    data_dir: str
    database_url: str

    def __init__(self) -> None:
        self.app_name = "refinance"
        self.app_version = "0.1.1"
        self.database_url = f"sqlite:///./{self.app_name}.db"


config = Config()
