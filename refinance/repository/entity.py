"""Repository for Entity model"""

from sqlalchemy.orm import Query

from refinance.models.entity import Entity
from refinance.repository.base import BaseRepository
from refinance.schemas.entity import EntityFiltersSchema


class EntityRepository(BaseRepository[Entity]):
    model = Entity

    def delete(self, obj_id):
        """This will break the history, implement it later (maybe)"""
        raise NotImplementedError

    def _apply_filters(self, query: Query, filters: EntityFiltersSchema) -> Query:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        if filters.active is not None:
            query = query.filter(self.model.active == filters.active)
        return query
