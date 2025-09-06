"""Entity service"""

import datetime

from app.errors.common import NotFoundError
from app.models.entity import Entity
from app.schemas.base import BaseFilterSchema
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
        if filters.auth_telegram_id is not None:
            query = query.filter(
                cast(cast(self.model.auth["telegram_id"], Text), Integer)
                == filters.auth_telegram_id
            )
        if filters.auth_card_hash is not None:
            # Use json_extract for portability (SQLite/MySQL) while avoiding raw text SQL
            query = query.filter(
                func.json_extract(self.model.auth, "$.card_hash")
                == filters.auth_card_hash
            )
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

    def get_by_card_hash(self, card_hash: str) -> Entity:
        db_obj = (
            self.db.query(self.model)
            .filter(func.json_extract(self.model.auth, "$.card_hash") == card_hash)
            .first()
        )
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.auth.{card_hash=}")
        return db_obj

    def update(self, obj_id: int, schema: EntityUpdateSchema, overrides: dict = {}):  # type: ignore[override]
        """Update entity with special handling for auth.card_hash.

        If schema.auth.card_hash is None (explicitly provided), we DO NOT overwrite
        an existing stored card_hash. Other auth fields are merged.
        """
        obj = self.get(obj_id)
        data = schema.dump()

        tag_ids = data.pop("tag_ids", None)
        data = {**data, **overrides}

        auth_update = data.pop("auth", None)

        # Set simple (non-auth) attributes
        for key, value in data.items():
            setattr(obj, key, value)

        if auth_update is not None:
            # Merge with existing auth instead of replacing wholesale
            existing_auth = obj.auth or {}
            # Skip card_hash update if explicitly None
            if "card_hash" in auth_update and auth_update["card_hash"] is None:
                auth_update.pop("card_hash")
            merged_auth = {**existing_auth, **auth_update}
            obj.auth = merged_auth

        # Handle tags if supported and provided (keep parity with BaseService)
        if tag_ids is not None and hasattr(self, "set_tags"):
            self.set_tags(obj, tag_ids)  # type: ignore

        setattr(obj, "modified_at", datetime.datetime.now())
        self.db.flush()
        self.db.refresh(obj)
        return obj
