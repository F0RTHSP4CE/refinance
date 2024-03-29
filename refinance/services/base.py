from typing import Generic, Type, TypeVar

from refinance.models.base import BaseModel
from refinance.repository.base import BaseRepository

M = TypeVar("M", bound=BaseModel)  # model


class BaseService(Generic[M]):
    model: Type[M]
    repo: BaseRepository[M]

    def __init__(self, repo: BaseRepository):
        self.repo = repo
