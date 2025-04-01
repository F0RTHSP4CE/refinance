from contextlib import contextmanager
from typing import Any, Generator, List, Type

from app.db import get_db as get_original_db  # fix for test mocks
from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker


class UnitOfWork:
    def __init__(self, db: Session):
        self.db = db

    def __getattr__(self, attr):
        """
        Delegate attribute access to the underlying session.
        This allows the UoW to be used as if it were a Session.
        """
        return getattr(self.db, attr)

    def __enter__(self):
        # Optionally do setup tasks here.
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Roll back if an exception occurred.
            self.db.rollback()
        else:
            # Otherwise, commit the transaction.
            self.db.commit()
        self.db.close()


def get_uow(
    db: Session = Depends(get_original_db),
) -> Generator[UnitOfWork, None, None]:
    """
    Dependency that yields a UnitOfWork instance.

    When used in a route, FastAPI will call this dependency once per request,
    ensuring that the same UoW (and underlying session) is passed to all services.
    """
    with UnitOfWork(db) as uow:
        yield uow
