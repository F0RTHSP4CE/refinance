"""Split service"""

from decimal import ROUND_DOWN, Decimal
from typing import Any

from app.errors.split import (
    MinimalNumberOfParticipantsRequired,
    PerformedSplitCanNotBeDeleted,
    PerformedSplitCanNotBeEdited,
    PerformedSplitParticipantsAreNotEditable,
    SplitDoesNotHaveParticipants,
    SplitParticipantAlreadyAdded,
    SplitParticipantAlreadyRemoved,
)
from app.models.entity import Entity
from app.models.split import Split
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.split import SplitCreateSchema, SplitFiltersSchema, SplitUpdateSchema
from app.schemas.transaction import TransactionCreateSchema
from app.services.base import BaseService
from app.services.entity import EntityService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session


class SplitService(TaggableServiceMixin[Split], BaseService[Split]):
    model = Split

    def __init__(
        self,
        db: Session = Depends(get_uow),
        transaction_service: TransactionService = Depends(),
        entity_service: EntityService = Depends(),
    ):
        self.db: Session = db
        self._transaction_service = transaction_service
        self._entity_service = entity_service

    def _apply_filters(
        self, query: Query[Split], filters: SplitFiltersSchema
    ) -> Query[Split]:
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.recipient_entity_id is not None:
            query = query.filter(
                self.model.recipient_entity_id == filters.recipient_entity_id
            )
        if filters.amount_min is not None:
            query = query.filter(self.model.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(self.model.amount <= filters.amount_max)
        if filters.currency is not None:
            query = query.filter(self.model.currency == filters.currency)
        if filters.performed is not None:
            query = query.filter(self.model.performed == filters.performed)
        return query

    def create(self, schema: SplitCreateSchema, overrides: dict = {}) -> Split:
        return super().create(schema, overrides)

    def update(
        self, obj_id: int, schema: SplitUpdateSchema, overrides: dict = {}
    ) -> Split:
        db_obj = self.get(obj_id)
        # prevent editing of a performed split
        if db_obj.performed is True:
            raise PerformedSplitCanNotBeEdited
        return super().update(obj_id, schema, overrides)

    def delete(self, obj_id: int) -> int:
        db_obj = self.get(obj_id)
        # prevent deleting of a performed split
        if db_obj.performed is True:
            raise PerformedSplitCanNotBeDeleted
        return super().delete(obj_id)

    def add_participant(self, obj_id: int, entity_id: int) -> Split:
        db_obj = self.get(obj_id)
        if db_obj.performed is True:
            raise PerformedSplitParticipantsAreNotEditable
        entity = self._entity_service.get(entity_id)
        if entity not in db_obj.participants:
            db_obj.participants.append(entity)
            self.db.flush()
        else:
            raise SplitParticipantAlreadyAdded
        return db_obj

    def remove_participant(self, obj_id: int, entity_id: int) -> Split:
        db_obj = self.get(obj_id)
        if db_obj.performed is True:
            raise PerformedSplitParticipantsAreNotEditable
        entity = self._entity_service.get(entity_id)
        if entity not in db_obj.participants:
            db_obj.participants.remove(entity)
            self.db.flush()
        else:
            raise SplitParticipantAlreadyRemoved
        return db_obj

    @staticmethod
    def _calculate_split(amount: Decimal, users: list[Any]) -> dict[Any, Decimal]:
        """
        Splits a total amount among the provided users.

        Parameters:
        amount (Decimal): The total amount to be split. It will be rounded to two decimal places.
        users (list): A list of users (can be any hashable identifiers).

        Returns:
        dict: A dictionary mapping each user to their calculated share as a Decimal with exactly 2 decimal places.

        Raises:
        ValueError: If `amount` is not a Decimal or if the users list is empty.
        """
        # Convert amount to exactly two decimal places.
        amount = amount.quantize(Decimal("0.01"))

        if not users:
            raise ValueError("Users list must not be empty.")

        num_users = len(users)
        # Calculate the base share by dividing equally and rounding down to 2 decimals.
        base_share = (amount / num_users).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        total_base = base_share * num_users
        remainder = amount - total_base
        # Determine the number of extra cents (as whole numbers).
        extra_count = int(
            (remainder / Decimal("0.01")).to_integral_value(rounding=ROUND_DOWN)
        )

        # Create the split dictionary by adding an extra cent to the first `extra_count` users.
        splits = {}
        for i, user in enumerate(users):
            share = base_share + (
                Decimal("0.01") if i < extra_count else Decimal("0.00")
            )
            # Ensure each share is exactly two decimals.
            splits[user] = share.quantize(Decimal("0.01"))
        return splits

    def perform(self, obj_id: int, actor_entity: Entity) -> list[Transaction]:
        db_obj = self.get(obj_id)
        if len(db_obj.participants) < 2:
            raise MinimalNumberOfParticipantsRequired
        participants_ids = [x.id for x in db_obj.participants]
        shares: dict[int, Decimal] = self._calculate_split(
            amount=db_obj.amount, users=participants_ids
        )
        if shares:
            tx_list: list[Transaction] = []
            for participant_id, participant_amount in shares.items():
                tx = self._transaction_service.create(
                    TransactionCreateSchema(
                        amount=participant_amount,
                        from_entity_id=participant_id,
                        to_entity_id=db_obj.recipient_entity_id,
                        currency=db_obj.currency,
                        status=TransactionStatus.COMPLETED,
                        comment=f"{db_obj.comment} (split #{db_obj.id})",
                    ),
                    overrides={"actor_entity_id": actor_entity.id},
                )
                tx_list.append(tx)
            self.update(obj_id, SplitUpdateSchema(performed=True))
            return tx_list
        else:
            raise SplitDoesNotHaveParticipants
