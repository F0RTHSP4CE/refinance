"""Entity service"""

from sqlalchemy.orm import Query

from refinance.errors.common import NotFoundError
from refinance.models.entity import Entity
from refinance.schemas.entity import EntityFiltersSchema
from refinance.services.base import BaseService
from refinance.services.mixins.taggable_mixin import TaggableServiceMixin


class EntityService(TaggableServiceMixin[Entity], BaseService[Entity]):
    model = Entity

    def delete(self, obj_id):
        """This will break the history, implement it later (maybe)"""
        raise NotImplementedError

    def _apply_filters(
        self, query: Query[Entity], filters: EntityFiltersSchema
    ) -> Query[Entity]:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        if filters.active is not None:
            query = query.filter(self.model.active == filters.active)
        if filters.telegram_id is not None:
            query = query.filter(self.model.telegram_id == filters.telegram_id)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def get_by_telegram_id(self, telegram_id: int) -> Entity:
        db_obj = (
            self.db.query(self.model)
            .filter(self.model.telegram_id == telegram_id)
            .first()
        )
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.{telegram_id=}")
        return db_obj
