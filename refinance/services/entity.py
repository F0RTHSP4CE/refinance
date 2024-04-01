"""Entity service"""

from typing import Iterable

from fastapi import Depends
from sqlalchemy.orm import Session

from refinance.db import get_db
from refinance.models.entity import Entity
from refinance.repository.entity import EntityRepository
from refinance.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntityUpdateSchema,
)
from refinance.services.base import BaseService


class EntityService(BaseService[Entity]):
    model = Entity

    def __init__(
        self, repo: EntityRepository = Depends(), db: Session = Depends(get_db)
    ):
        super().__init__(repo=repo, db=db)

    def create(self, schema: EntityCreateSchema) -> Entity:
        new_obj = self.model(**schema.dump())
        db_obj = self.repo.create(new_obj)
        return db_obj

    def get(self, entity_id: int) -> Entity | None:
        return self.repo.get(entity_id)

    def get_all(
        self, filters: EntityFiltersSchema | None = None, skip=0, limit=10
    ) -> Iterable[Entity]:
        return self.repo.get_all(filters, skip, limit)

    def update(self, entity_id, entity_update: EntityUpdateSchema) -> Entity:
        return self.repo.update(entity_id, entity_update.dump())
