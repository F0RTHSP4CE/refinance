"""Entity service"""

import datetime

from app.dependencies.services import get_tag_service
from app.errors.common import NotFoundError
from app.models.entity import Entity
from app.models.entity_card import EntityCard
from app.models.transaction import TransactionStatus
from app.schemas.base import PaginationSchema
from app.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntityUpdateSchema,
)
from app.services.balance_queries import build_entity_balance_subqueries
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
        tag_service: TagService = Depends(get_tag_service),
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
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def get_all(
        self, filters: EntityFiltersSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[Entity]:
        query = self.db.query(self.model)
        if filters:
            query = self._apply_base_filters(query, filters)
            query = self._apply_filters(query, filters)

            if filters.balance_currency:
                status = filters.balance_status or TransactionStatus.COMPLETED
                order = (filters.balance_order or "desc").lower()

                credit_subq, debit_subq, balance_expr = build_entity_balance_subqueries(
                    currency=filters.balance_currency,
                    status=status,
                )

                query = query.outerjoin(
                    credit_subq, credit_subq.c.entity_id == self.model.id
                ).outerjoin(debit_subq, debit_subq.c.entity_id == self.model.id)

                if order == "asc":
                    query = query.order_by(balance_expr.asc(), self.model.id.desc())
                else:
                    query = query.order_by(balance_expr.desc(), self.model.id.desc())
            else:
                query = query.order_by(self.model.id.desc())
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return PaginationSchema[Entity](
            items=items, total=total, skip=skip, limit=limit
        )

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
        """Resolve entity by card_hash using EntityCard table."""
        entity = (
            self.db.query(self.model)
            .join(EntityCard, EntityCard.entity_id == self.model.id)
            .filter(EntityCard.card_hash == card_hash)
            .first()
        )
        if not entity:
            raise NotFoundError(f"{self.model.__name__}.card_hash={card_hash}")
        return entity

    def update(self, obj_id: int, schema: EntityUpdateSchema, overrides: dict = {}):  # type: ignore[override]
        """Update entity with special handling for auth.card_hash.

        Card management moved to EntityCard, so auth.card_hash is ignored.
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
            # Explicitly drop any card_hash remnants in payload
            auth_update.pop("card_hash", None)
            merged_auth = {**existing_auth, **auth_update}
            obj.auth = merged_auth

        # Handle tags if supported and provided (keep parity with BaseService)
        if tag_ids is not None and hasattr(self, "set_tags"):
            self.set_tags(obj, tag_ids)  # type: ignore

        setattr(obj, "modified_at", datetime.datetime.now())
        self.db.flush()
        self.db.refresh(obj)
        return obj

    # ---- Card management -------------------------------------------------
    def list_cards(self, entity_id: int) -> list[EntityCard]:
        entity = self.get(entity_id)
        # Ensure relationship is loaded
        return list(entity.cards)

    def add_card(
        self, entity_id: int, *, card_hash: str, comment: str | None = None
    ) -> EntityCard:
        # Ensure entity exists
        _ = self.get(entity_id)
        card = EntityCard(entity_id=entity_id, card_hash=card_hash, comment=comment)
        self.db.add(card)
        self.db.flush()
        self.db.refresh(card)
        return card

    def remove_card(self, entity_id: int, card_id: int) -> int:
        # Delete by primary key and ensure ownership by entity
        card = (
            self.db.query(EntityCard)
            .filter(EntityCard.entity_id == entity_id, EntityCard.id == card_id)
            .first()
        )
        if not card:
            raise NotFoundError(f"EntityCard entity_id={entity_id}, card_id={card_id}")
        self.db.delete(card)
        self.db.flush()
        return card.id
