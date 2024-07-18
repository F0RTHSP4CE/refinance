"""Database connection and initialization"""

import os

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Config, get_config
from app.models.base import BaseModel


class DatabaseConnection:
    engine: Engine
    session_local: sessionmaker[Session]

    def __init__(self, config: Config = Depends(get_config)) -> None:
        os.makedirs(config.database_path.parent, exist_ok=True)
        self.engine = create_engine(
            config.database_url, connect_args={"check_same_thread": False}
        )
        self.session_local = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.create_tables()

    def get_session(self):
        return self.session_local()

    def create_tables(self):
        BaseModel.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        BaseModel.metadata.drop_all(bind=self.engine)


def get_db(db_conn: DatabaseConnection = Depends()):
    # return session to be used in services, tests
    db_session = db_conn.get_session()
    try:
        yield db_session
    finally:
        db_session.close()
