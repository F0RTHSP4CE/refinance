"""Repository for Entity model"""

from sqlalchemy.orm import Query

from refinance.models.entity import Entity
from refinance.repository.base import BaseRepository
from refinance.repository.mixins.taggable_mixin import TaggableRepositoryMixin
from refinance.schemas.entity import EntityFiltersSchema


class EntityRepository(TaggableRepositoryMixin, BaseRepository[Entity]):
    model = Entity

    def delete(self, obj_id):
        """This will break the history, implement it later (maybe)"""
        raise NotImplementedError

    def _apply_filters(self, query: Query, filters: EntityFiltersSchema) -> Query:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        if filters.active is not None:
            query = query.filter(self.model.active == filters.active)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query
