"""Tag service"""

from fastapi import Depends
from sqlalchemy.orm import Session

from refinance.db import get_db
from refinance.errors.tag import TagIsBusy
from refinance.models.tag import Tag
from refinance.repository.tag import TagRepository
from refinance.schemas.base import PaginationSchema
from refinance.schemas.entity import EntityFiltersSchema
from refinance.schemas.tag import TagCreateSchema, TagFiltersSchema, TagUpdateSchema
from refinance.services.base import BaseService
from refinance.services.entity import EntityService


class TagService(BaseService[Tag]):
    model = Tag

    entity_service: EntityService

    def __init__(
        self,
        repo: TagRepository = Depends(),
        db: Session = Depends(get_db),
        entity_service: EntityService = Depends(),
    ):
        super().__init__(repo=repo, db=db)
        self.entity_service = entity_service

    def create(self, schema: TagCreateSchema) -> Tag:
        new_obj = self.model(**schema.dump())
        db_obj = self.repo.create(new_obj)
        return db_obj

    def get(self, tag_id: int) -> Tag:
        return self.repo.get(tag_id)

    def get_all(
        self, filters: TagFiltersSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[Tag]:
        return self.repo.get_all(filters, skip, limit)

    def update(self, tag_id, tag_update: TagUpdateSchema) -> Tag:
        return self.repo.update(tag_id, tag_update.dump())

    def delete(self, tag_id) -> int:
        if self.entity_service.get_all(
            filters=EntityFiltersSchema(tags_ids=[tag_id]), limit=1
        ).items:
            raise TagIsBusy
        return self.repo.delete(tag_id)
