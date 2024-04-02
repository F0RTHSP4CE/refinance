"""Base service with repository"""

from typing import Generic, Type, TypeVar

from sqlalchemy.orm import Session

from refinance.models.base import BaseModel
from refinance.repository.base import BaseRepository
from refinance.schemas.base import BaseFilterSchema

_K = TypeVar("_K", int, str)  # primary key
_M = TypeVar("_M", bound=BaseModel)  # model
_F = TypeVar("_F", bound=BaseFilterSchema)  # filters


class BaseService(Generic[_K, _M, _F]):
    model: Type[_M]
    repo: BaseRepository[_K, _M, _F]
    db: Session

    def __init__(self, repo: BaseRepository[_K, _M, _F], db: Session) -> None:
        self.repo = repo
        self.db = db
