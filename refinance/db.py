"""Database connection and initialization"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from refinance.config import config
from refinance.models.base import BaseModel


class DatabaseConnection:
    engine: Engine
    session_local: sessionmaker[Session]

    def __init__(self) -> None:
        self.engine = create_engine(
            config.database_url, connect_args={"check_same_thread": False}
        )
        self.session_local = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def get_session(self):
        return self.session_local()

    def create_tables(self):
        BaseModel.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        BaseModel.metadata.drop_all(bind=self.engine)


db_conn: DatabaseConnection | None = None


def get_db():
    global db_conn
    if not db_conn:
        # initialize first database connection
        db_conn = DatabaseConnection()
        # populate database with new tables
        db_conn.create_tables()

    # return session to be used in services, repos, tests
    db_session = db_conn.get_session()
    try:
        yield db_session
    finally:
        db_session.close()
        # reset connection information
        db_conn = None
