"""Transaction service"""

from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db import get_db
from app.models.entity import Entity
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreateSchema,
    TransactionFiltersSchema,
    TransactionUpdateSchema,
)
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin


class TransactionService(TaggableServiceMixin[Transaction], BaseService[Transaction]):
    model = Transaction

    def __init__(
        self, db: Session = Depends(get_db), balance_service: BalanceService = Depends()
    ):
        self.db = db
        self._balance_service = balance_service

    def _apply_filters(
        self, query: Query[Transaction], filters: TransactionFiltersSchema
    ) -> Query[Transaction]:
        if filters.entity_id is not None:
            query = query.filter(
                or_(
                    self.model.from_entity_id == filters.entity_id,
                    self.model.to_entity_id == filters.entity_id,
                    self.model.actor_entity_id == filters.actor_entity_id,
                )
            )
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.from_entity_id is not None:
            query = query.filter(self.model.from_entity_id == filters.from_entity_id)
        if filters.to_entity_id is not None:
            query = query.filter(self.model.to_entity_id == filters.to_entity_id)
        if filters.amount_min is not None:
            query = query.filter(self.model.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(self.model.amount <= filters.amount_max)
        if filters.currency is not None:
            query = query.filter(self.model.currency == filters.currency)
        if filters.comment is not None:
            query = query.filter(self.model.comment.ilike(f"%{filters.comment}%"))
        if filters.confirmed is not None:
            query = query.filter(self.model.confirmed == filters.confirmed)
        return query

    def create(
        self, schema: TransactionCreateSchema, actor_entity: Entity
    ) -> Transaction:
        # invalidate balance cache
        self._balance_service.invalidate_cache_entry(schema.from_entity_id)
        self._balance_service.invalidate_cache_entry(schema.to_entity_id)
        # create tx
        return super().create(schema, overrides={"actor_entity_id": actor_entity.id})

    def update(
        self, obj_id: int, schema: TransactionUpdateSchema, overrides: dict = {}
    ) -> Transaction:
        # invalidate balance cache
        tx = self.get(obj_id)
        self._balance_service.invalidate_cache_entry(tx.from_entity_id)
        self._balance_service.invalidate_cache_entry(tx.to_entity_id)
        # update tx
        return super().update(obj_id, schema, overrides)

    def delete(self, obj_id: int) -> int:
        # invalidate balance cache
        tx = self.get(obj_id)
        self._balance_service.invalidate_cache_entry(tx.from_entity_id)
        self._balance_service.invalidate_cache_entry(tx.to_entity_id)
        # delete tx
        return super().delete(obj_id)
