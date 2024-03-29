from typing import Iterable

from fastapi import Depends

from refinance.models.entity import Entity
from refinance.repository.entity import EntityRepository
from refinance.schemas.entity import EntityCreateSchema, EntityUpdateSchema
from refinance.services.base import BaseService


class EntityService(BaseService[Entity]):
    model = Entity

    def __init__(self, repo: EntityRepository = Depends()):
        super().__init__(repo=repo)

    def create(self, schema: EntityCreateSchema) -> Entity:
        new_obj = self.model(**schema.dump())
        db_obj = self.repo.create(new_obj)
        return db_obj

    def get(self, entity_id: int) -> Entity | None:
        return self.repo.get(entity_id)

    def get_all(self, skip=0, limit=10) -> Iterable[Entity]:
        return self.repo.get_all(skip, limit)

    def update(self, entity_id, entity_update: EntityUpdateSchema) -> Entity:
        return self.repo.update(entity_id, entity_update.dump())
