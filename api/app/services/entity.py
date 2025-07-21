"""Entity service"""

from app.errors.common import NotFoundError
from app.models.entity import Entity
from app.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntityUpdateSchema,
)
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import Integer, Text, cast
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import func


class EntityService(TaggableServiceMixin[Entity], BaseService[Entity]):
    model = Entity

    def __init__(
        self,
        db: Session = Depends(get_uow),
        tag_service: TagService = Depends(),
    ):
        self.db = db
        self._tag_service = tag_service

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
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def get_by_telegram_id(self, telegram_id: int) -> Entity:
        db_obj = (
            self.db.query(self.model)
            .filter(
                cast(cast(self.model.auth["telegram_id"], Text), Integer) == telegram_id
            )
            .first()
        )
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.auth.{telegram_id=}")
        return db_obj

    def get_by_name(self, name: str) -> Entity:
        db_obj = (
            self.db.query(self.model)
            .filter(func.lower(self.model.name) == func.lower(name))
            .first()
        )
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} {name=}")
        return db_obj

    def get_by_oidc_email(self, email: str) -> Entity:
        # SQLite requires JSON_EXTRACT for JSON column queries
        db_obj = (
            self.db.query(self.model)
            .filter(func.json_extract(self.model.auth, "$.oidc_email") == email)
            .first()
        )
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.auth.oidc_email={email}")
        return db_obj
