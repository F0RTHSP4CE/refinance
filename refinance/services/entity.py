"""Entity service"""

from fastapi import Depends
from sqlalchemy.orm import Session

from refinance.db import get_db
from refinance.models.entity import Entity
from refinance.repository.entity import EntityRepository
from refinance.schemas.base import PaginationSchema
from refinance.schemas.entity import EntityCreateSchema, EntityFiltersSchema, EntitySchema, EntityUpdateSchema
from refinance.services.base import BaseService


class EntityService(BaseService[int, Entity, EntityFiltersSchema]):
    model = Entity

    def __init__(self, repo: EntityRepository = Depends(), db: Session = Depends(get_db)) -> None:
        super().__init__(repo=repo, db=db)

    def create_model(self, schema: EntityCreateSchema) -> Entity:
        new_obj = self.model(**schema.model_dump(exclude_unset=True))
        db_obj = self.repo.create(new_obj)
        return db_obj

    def create(self, schema: EntityCreateSchema) -> EntitySchema:
        db_obj = self.create_model(schema)
        return EntitySchema.model_construct(**db_obj.model_dump())

    def get(self, entity_id: int) -> EntitySchema:
        result = self.repo.get(entity_id)
        return EntitySchema.model_construct(**result.model_dump())

    def get_all(
        self,
        filters: EntityFiltersSchema | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> PaginationSchema[EntitySchema]:
        results = self.repo.get_all(filters, skip, limit)
        return PaginationSchema(
            items=[EntitySchema.model_construct(**model.model_dump()) for model in results.items],
            total=results.total,
            skip=skip,
            limit=limit,
        )

    def update(self, entity_id: int, entity_update: EntityUpdateSchema) -> EntitySchema:
        result = self.repo.update(entity_id, entity_update.model_dump(exclude_unset=True))
        return EntitySchema.model_construct(**result.model_dump())
