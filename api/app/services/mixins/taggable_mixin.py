"""Mixin for taggable models, for example: Entities, Transactions"""

from typing import Generic, Iterable, TypeVar

from app.errors.tag import TagAlreadyAdded, TagAlreadyRemoved, TagsNotSupported
from app.models.base import BaseModel
from app.models.tag import Tag
from app.services.base import BaseService
from app.services.tag import TagService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Query, Session

_M = TypeVar("_M", bound=BaseModel)


class TaggableServiceMixin(BaseService[_M], Generic[_M]):
    model: type[_M]
    db: Session
    _tag_service: TagService

    def add_tag(self, obj_id: int, tag_id: int) -> Tag:
        db_obj = self.get(obj_id)
        if not hasattr(db_obj, "tags"):
            raise TagsNotSupported
        tag = self._tag_service.get(tag_id)
        if tag not in db_obj.tags:  # type: ignore
            db_obj.tags.append(tag)  # type: ignore
            self.db.flush()
        else:
            raise TagAlreadyAdded
        return tag

    def remove_tag(self, obj_id: int, tag_id: int) -> Tag:
        db_obj = self.get(obj_id)
        if not hasattr(db_obj, "tags"):
            raise TagsNotSupported
        tag = self._tag_service.get(tag_id)
        if tag in db_obj.tags:  # type: ignore
            db_obj.tags.remove(tag)  # type: ignore
            self.db.flush()
        else:
            raise TagAlreadyRemoved
        return tag

    def _apply_tag_filters(
        self, query: Query[_M], tags_ids: Iterable[int]
    ) -> Query[_M]:
        tags = [self._tag_service.get(tag_id) for tag_id in tags_ids]
        return query.filter(*[self.model.tags.any(id=tag.id) for tag in tags])  # type: ignore
