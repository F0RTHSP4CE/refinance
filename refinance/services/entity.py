"""Entity service"""

from fastapi import Depends
from sqlalchemy.orm import Session

from refinance.db import get_db
from refinance.models.entity import Entity
from refinance.repository.entity import EntityRepository
from refinance.schemas.base import PaginationSchema
from refinance.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntityUpdateSchema,
)
from refinance.services.base import BaseService
from refinance.services.mixins.taggable_mixin import TaggableServiceMixin


class EntityService(TaggableServiceMixin, BaseService[Entity]):
    model = Entity

    def __init__(
        self, repo: EntityRepository = Depends(), db: Session = Depends(get_db)
    ):
        super().__init__(repo=repo, db=db)

    def create(self, schema: EntityCreateSchema) -> Entity:
        new_obj = self.model(**schema.dump())
        db_obj = self.repo.create(new_obj)
        return db_obj

    def get(self, entity_id: int) -> Entity:
        return self.repo.get(entity_id)

    def get_all(
        self, filters: EntityFiltersSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[Entity]:
        return self.repo.get_all(filters, skip, limit)

    def update(self, entity_id, entity_update: EntityUpdateSchema) -> Entity:
        return self.repo.update(entity_id, entity_update.dump())
