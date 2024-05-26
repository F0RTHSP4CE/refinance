"""Mixin for taggable models, for example: Entities, Transactions"""

from typing import Generic, Iterable, TypeVar

from fastapi import Depends
from sqlalchemy.orm import Query, Session

from refinance.db import get_db
from refinance.errors.tag import TagAlreadyAdded, TagAlreadyRemoved, TagsNotSupported
from refinance.models.base import BaseModel
from refinance.models.tag import Tag
from refinance.repository.base import BaseRepository
from refinance.repository.tag import TagRepository

_M = TypeVar("_M", bound=BaseModel)


class TaggableRepositoryMixin(BaseRepository[_M], Generic[_M]):
    model: type[_M]
    tag_repository: TagRepository

    def __init__(
        self, db: Session = Depends(get_db), tag_repository: TagRepository = Depends()
    ):
        super().__init__(db)
        self.tag_repository = tag_repository

    def add_tag(self, obj_id: int, tag_id: int) -> Tag:
        db_obj = self.get(obj_id)
        if not hasattr(db_obj, "tags"):
            raise TagsNotSupported
        tag = self.tag_repository.get(tag_id)
        if tag not in db_obj.tags:  # type: ignore
            db_obj.tags.append(tag)  # type: ignore
            self.db.commit()
        else:
            raise TagAlreadyAdded
        return tag

    def remove_tag(self, obj_id: int, tag_id: int) -> Tag:
        db_obj = self.get(obj_id)
        if not hasattr(db_obj, "tags"):
            raise TagsNotSupported
        tag = self.tag_repository.get(tag_id)
        if tag in db_obj.tags:  # type: ignore
            db_obj.tags.remove(tag)  # type: ignore
            self.db.commit()
        else:
            raise TagAlreadyRemoved
        return tag

    def _apply_tag_filters(
        self, query: Query[_M], tags_ids: Iterable[int]
    ) -> Query[_M]:
        tags = [self.tag_repository.get(tag_id) for tag_id in tags_ids]
        return query.filter(*[self.model.tags.any(id=tag.id) for tag in tags])  # type: ignore
