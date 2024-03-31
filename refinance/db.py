from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from refinance.config import config

engine = create_engine(config.database_url, connect_args={"check_same_thread": False})
session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from refinance.models.base import BaseModel

    BaseModel.metadata.create_all(bind=engine)


create_tables()
