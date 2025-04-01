"""Split service with fixed participant amounts"""

from decimal import ROUND_DOWN, Decimal
from typing import Any, Optional

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
from app.models.split import Split, SplitParticipant
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.split import (
    SplitCreateSchema,
    SplitFiltersSchema,
    SplitParticipantAddSchema,
    SplitUpdateSchema,
)
from app.schemas.transaction import TransactionCreateSchema
from app.services.base import BaseService
from app.services.entity import EntityService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
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
        # Prevent editing of a performed split.
        if db_obj.performed is True:
            raise PerformedSplitCanNotBeEdited
        return super().update(obj_id, schema, overrides)

    def delete(self, obj_id: int) -> int:
        db_obj = self.get(obj_id)
        # Prevent deleting of a performed split.
        if db_obj.performed is True:
            raise PerformedSplitCanNotBeDeleted
        return super().delete(obj_id)

    def add_participant(self, obj_id: int, schema: SplitParticipantAddSchema) -> Split:
        """
        Adds a participant to the split.
        Optionally, a fixed_amount (Decimal) can be provided.
        """
        db_obj = self.get(obj_id)
        if db_obj.performed is True:
            raise PerformedSplitParticipantsAreNotEditable
        for assoc in db_obj.participants:
            if assoc.entity_id == schema.entity_id:
                raise SplitParticipantAlreadyAdded
        entity = self._entity_service.get(schema.entity_id)
        new_assoc = SplitParticipant(
            split=db_obj,
            entity=entity,
            fixed_amount=(
                schema.fixed_amount.quantize(Decimal("0.01"))
                if schema.fixed_amount is not None
                else None
            ),
        )
        db_obj.participants.append(new_assoc)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def remove_participant(self, obj_id: int, entity_id: int) -> Split:
        db_obj = self.get(obj_id)
        if db_obj.performed is True:
            raise PerformedSplitParticipantsAreNotEditable
        assoc_to_remove = None
        for assoc in db_obj.participants:
            if assoc.entity_id == entity_id:
                assoc_to_remove = assoc
                break
        if assoc_to_remove is None:
            raise SplitParticipantAlreadyRemoved
        db_obj.participants.remove(assoc_to_remove)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    @staticmethod
    def _calculate_split(
        amount: Decimal, fixed: dict[int, Decimal], non_fixed: list[int]
    ) -> dict[int, Decimal]:
        """
        Calculates the split amounts for all participants.
        Participants with a fixed amount are assigned that amount.
        The remaining balance (amount minus the sum of fixed amounts)
        is split equally among participants without a fixed amount.
        """
        amount = amount.quantize(Decimal("0.01"))
        total_fixed = sum(fixed.values()) if fixed else Decimal("0.00")
        if total_fixed > amount:
            raise ValueError("Total fixed amounts exceed split amount")
        remaining = amount - total_fixed
        non_fixed_shares = {}
        if non_fixed:
            num_non_fixed = len(non_fixed)
            base_share = (remaining / num_non_fixed).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            total_base = base_share * num_non_fixed
            remainder = remaining - total_base
            extra_count = int(
                (remainder / Decimal("0.01")).to_integral_value(rounding=ROUND_DOWN)
            )
            for i, uid in enumerate(non_fixed):
                share = base_share + (
                    Decimal("0.01") if i < extra_count else Decimal("0.00")
                )
                non_fixed_shares[uid] = share.quantize(Decimal("0.01"))
        splits = {}
        # Fixed amounts are used as provided.
        for uid in fixed:
            splits[uid] = fixed[uid].quantize(Decimal("0.01"))
        # Non-fixed participants get their calculated share.
        for uid, share in non_fixed_shares.items():
            splits[uid] = share
        return splits

    def perform(self, obj_id: int, actor_entity: Entity) -> list[Transaction]:
        """
        Executes the split by creating transactions.
        For each participant, if a fixed amount is provided that amount is used;
        otherwise, the remaining amount is split equally among the non-fixed participants.
        Transactions with 0 amount are skipped.
        """
        db_obj = self.get(obj_id)
        total_participants = len(db_obj.participants)
        if total_participants < 2:
            raise MinimalNumberOfParticipantsRequired

        fixed: dict[int, Decimal] = {}
        non_fixed: list[int] = []
        for assoc in db_obj.participants:
            if assoc.fixed_amount is not None:
                fixed[assoc.entity_id] = assoc.fixed_amount.quantize(Decimal("0.01"))
            else:
                non_fixed.append(assoc.entity_id)

        shares: dict[int, Decimal] = self._calculate_split(
            amount=db_obj.amount, fixed=fixed, non_fixed=non_fixed
        )

        tx_list: list[Transaction] = []
        for participant_id, participant_amount in shares.items():
            if participant_amount > Decimal("0.00"):
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
