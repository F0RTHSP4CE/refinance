"""Transaction service"""

from typing import TYPE_CHECKING

from app.errors.transaction import (
    CompletedTransactionNotDeletable,
    CompletedTransactionNotEditable,
    TransactionWillOverdraftTreasury,
)
from app.models.entity import Entity
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import (
    TransactionCreateSchema,
    TransactionFiltersSchema,
    TransactionUpdateSchema,
)
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.services.treasury import TreasuryService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

if TYPE_CHECKING:
    from app.services.stats import StatsService


class TransactionService(TaggableServiceMixin[Transaction], BaseService[Transaction]):
    model = Transaction

    def __init__(
        self,
        db: Session = Depends(get_uow),
        balance_service: BalanceService = Depends(),
        tag_service: TagService = Depends(),
        treasury_service: TreasuryService = Depends(),
    ):
        self.db = db
        self._balance_service = balance_service
        self._tag_service = tag_service
        self._treasury_service = treasury_service

    def _invalidate_related_caches(
        self,
        from_entity_id: int | None,
        to_entity_id: int | None,
        *treasury_ids: int | None,
        invalidate_stats: bool = False,
    ) -> None:
        """Invalidate cache entries for affected entities and treasuries."""

        entity_ids: set[int] = set()
        for entity_id in (from_entity_id, to_entity_id):
            if entity_id is None:
                continue
            self._balance_service.invalidate_cache_entry(entity_id)
            entity_ids.add(entity_id)

        for tid in treasury_ids:
            if tid is not None:
                self._balance_service.invalidate_treasury_cache_entry(tid)

        if invalidate_stats and entity_ids:
            from app.services.stats import StatsService

            StatsService.invalidate_entity_cache(*entity_ids)

    def _apply_filters(  # type: ignore[override]
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
        if filters.status is not None:
            query = query.filter(self.model.status == filters.status)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def create(  # type: ignore[override]
        self, schema: TransactionCreateSchema, overrides: dict = {}
    ) -> Transaction:
        # invalidate caches for creation
        self._invalidate_related_caches(
            schema.from_entity_id,
            schema.to_entity_id,
            schema.from_treasury_id,
            schema.to_treasury_id,
            invalidate_stats=True,
        )
        return super().create(schema, overrides)

    def update(  # type: ignore[override]
        self, obj_id: int, schema: TransactionUpdateSchema, overrides: dict = {}
    ) -> Transaction:
        tx = self.get(obj_id)
        # prevent editing of a completed transaction
        if tx.status == TransactionStatus.COMPLETED:
            raise CompletedTransactionNotEditable
        # prevent overdrafting treasury on confirmation
        if (
            schema.status == TransactionStatus.COMPLETED
            and self._treasury_service.transaction_will_overdraft_treasury(obj_id)
        ):
            raise TransactionWillOverdraftTreasury
        # invalidate caches for update
        self._invalidate_related_caches(
            tx.from_entity_id,
            tx.to_entity_id,
            tx.from_treasury_id,
            tx.to_treasury_id,
            schema.from_treasury_id,
            schema.to_treasury_id,
            invalidate_stats=schema.status == TransactionStatus.COMPLETED
            or tx.status == TransactionStatus.COMPLETED,
        )
        updated_tx = super().update(obj_id, schema, overrides)
        return updated_tx

    def delete(self, obj_id: int) -> int:  # type: ignore[override]
        tx = self.get(obj_id)
        # prevent deleting of a completed transaction
        if tx.status == TransactionStatus.COMPLETED:
            raise CompletedTransactionNotDeletable
        # invalidate caches for deletion
        self._invalidate_related_caches(
            tx.from_entity_id,
            tx.to_entity_id,
            tx.from_treasury_id,
            tx.to_treasury_id,
            invalidate_stats=tx.status == TransactionStatus.COMPLETED,
        )
        return super().delete(obj_id)
