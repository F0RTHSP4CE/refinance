"""Base service with repository"""

from typing import Generic, Type, TypeVar

from sqlalchemy.orm import Session

from refinance.models.base import BaseModel
from refinance.repository.base import BaseRepository

M = TypeVar("M", bound=BaseModel)  # model


class BaseService(Generic[M]):
    model: Type[M]
    repo: BaseRepository[M]
    db: Session

    def __init__(self, repo: BaseRepository, db: Session):
        self.repo = repo
        self.db = db
