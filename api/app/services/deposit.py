"""Deposit service"""

from app.db import get_db
from app.errors.common import NotFoundError
from app.models.deposit import Deposit
from app.schemas.deposit import DepositFiltersSchema
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.services.transaction import TransactionService
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session


class DepositService(TaggableServiceMixin[Deposit], BaseService[Deposit]):
    model = Deposit

    def __init__(
        self,
        db: Session = Depends(get_db),
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

    def get_by_uuid(self, uuid: str) -> Deposit:
        db_obj = self.db.query(self.model).filter(self.model.uuid == uuid).first()
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} uuid={uuid}")
        return db_obj

    def delete(self, obj_id: int):
        """Deposits should not be deleted. They can either be cancelled or completed."""
        raise NotImplementedError
