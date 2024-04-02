"""Repository for Entity model"""

from typing import Any, TypeVar

from sqlalchemy.orm import Query

from refinance.models.entity import Entity
from refinance.repository.base import BaseRepository
from refinance.schemas.entity import EntityFiltersSchema

_Q = TypeVar("_Q", bound=Query[Any])


class EntityRepository(BaseRepository[int, Entity, EntityFiltersSchema]):
    model = Entity

    def delete(self, obj_id: int) -> int:
        """This will break the history, implement it later (maybe)"""
        raise NotImplementedError

    def _apply_filters(self, query: _Q, filters: EntityFiltersSchema) -> _Q:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        if filters.active is not None:
            query = query.filter(self.model.active == filters.active)
        return query
