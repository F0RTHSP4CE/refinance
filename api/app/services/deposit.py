"""Deposit service"""

from typing import Any
from uuid import UUID

from app.errors.common import NotFoundError
from app.errors.deposit import DepositAlreadyCompleted, DepositCannotBeEdited
from app.models.deposit import Deposit, DepositStatus
from app.models.transaction import TransactionStatus
from app.schemas.deposit import DepositFiltersSchema, DepositUpdateSchema
from app.schemas.transaction import TransactionCreateSchema
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session


class DepositService(TaggableServiceMixin[Deposit], BaseService[Deposit]):
    model = Deposit

    def __init__(
        self,
        db: Session = Depends(get_uow),
        transaction_service: TransactionService = Depends(),
        tag_service: TagService = Depends(),
    ):
        self.db = db
        self._transaction_service = transaction_service
        self._tag_service = tag_service

    def _apply_filters(
        self, query: Query[Deposit], filters: DepositFiltersSchema
    ) -> Query[Deposit]:
        if filters.entity_id is not None:
            query = query.filter(
                or_(
                    self.model.to_entity_id == filters.entity_id,
                    self.model.actor_entity_id == filters.actor_entity_id,
                )
            )
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.to_entity_id is not None:
            query = query.filter(self.model.to_entity_id == filters.to_entity_id)
        if filters.amount_min is not None:
            query = query.filter(self.model.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(self.model.amount <= filters.amount_max)
        if filters.currency is not None:
            query = query.filter(self.model.currency == filters.currency)
        if filters.status is not None:
            query = query.filter(self.model.status == filters.status)
        return query

    def get_by_uuid(self, uuid: UUID) -> Deposit:
        db_obj = self.db.query(self.model).filter(self.model.uuid == uuid).first()
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} uuid={uuid}")
        return db_obj

    def delete(self, obj_id: int):
        """Deposits should not be deleted. They can either be cancelled or completed."""
        raise NotImplementedError

    def complete(self, obj_id: int):
        # change deposit status to completed and create transaction to top-up user balane
        db_obj = self.get(obj_id)
        if db_obj.status == DepositStatus.PENDING:
            tx = self._transaction_service.create(
                TransactionCreateSchema(
                    amount=db_obj.amount,
                    currency=db_obj.currency,
                    from_entity_id=db_obj.from_entity_id,
                    to_entity_id=db_obj.to_entity_id,
                    status=TransactionStatus.COMPLETED,
                ),
                overrides={"actor_entity_id": db_obj.actor_entity_id},
            )
            self.update(obj_id, DepositUpdateSchema(status=DepositStatus.COMPLETED))
            return tx
        else:
            raise DepositAlreadyCompleted

    def update(
        self, obj_id: int, schema: DepositUpdateSchema, overrides: dict = {}
    ) -> Deposit:
        db_obj = self.get(obj_id)
        if db_obj.status in (
            DepositStatus.FAILED,
            DepositStatus.COMPLETED,
            DepositStatus.CANCELLED,
        ):
            raise DepositCannotBeEdited
        return super().update(obj_id, schema, overrides)
