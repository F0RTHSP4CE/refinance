"""Split service with fixed participant amounts"""

from decimal import ROUND_DOWN, Decimal

from app.errors.split import (
    EitherEntityOrTagIdRequired,
    MinimalNumberOfParticipantsRequired,
    PerformedSplitCanNotBeDeleted,
    PerformedSplitCanNotBeEdited,
    PerformedSplitParticipantsAreNotEditable,
    SplitParticipantAlreadyRemoved,
)
from app.models.entity import Entity
from app.models.split import Split, SplitParticipant
from app.models.tag import Tag
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
from app.services.tag import TagService
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
        tag_service: TagService = Depends(),
    ):
        self.db: Session = db
        self._transaction_service = transaction_service
        self._entity_service = entity_service
        self._tag_service = tag_service

    def get(self, obj_id: int) -> Split:
        db_obj = super().get(obj_id)
        return db_obj

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
        if filters.participant_entity_id is not None:
            query = query.filter(
                self.model.participants.any(entity_id=filters.participant_entity_id)
            )
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
        Adds a participant in the split.
        If the participant is already added, it is skipped.
        Otherwise, a new participant association is created.
        """
        db_obj = self.get(obj_id)
        if db_obj.performed is True:
            raise PerformedSplitParticipantsAreNotEditable

        try:
            assert schema.entity_id is not None or schema.entity_tag_id is not None
            assert not (schema.entity_id and schema.entity_tag_id)
        except AssertionError:
            raise EitherEntityOrTagIdRequired

        # If entity_tag_id is provided, fetch all entities by tag.
        if schema.entity_tag_id is not None:
            entities = (
                self.db.query(Entity)
                .join(Entity.tags)
                .filter(Tag.id == schema.entity_tag_id)
                .all()
            )
            existing_entity_ids = {assoc.entity_id for assoc in db_obj.participants}
            for entity in entities:
                if entity.id not in existing_entity_ids:
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
        else:
            # Original logic using entity_id.
            for assoc in db_obj.participants:
                if assoc.entity_id == schema.entity_id:
                    return db_obj  # Skip if participant already exists.

            # Otherwise, add a new participant association.
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
        amount: Decimal,
        fixed: dict[int, Decimal],
        non_fixed: list[int],
    ) -> dict[int, Decimal]:
        """
        Calculates the split amounts for all participants.
        Participants with a fixed amount are assigned that amount.
        The remaining balance (amount minus the sum of fixed amounts)
        is split equally among participants without a fixed amount.

        Params:
            amount: total amount to be split
            fixed: dictionary containing fixes shares along with user ids
            non_fixed: list of user ids to be split equally between

        """
        amount = amount.quantize(Decimal("0.01"))
        total_fixed = sum(fixed.values()) if fixed else Decimal("0.00")
        remaining = amount - total_fixed
        non_fixed_shares = {}
        if remaining > 0:
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

    def perform(self, obj_id: int, actor_entity: Entity) -> Split:
        """
        Executes the split by creating transactions.
        For each participant, if a fixed amount is provided that amount is used;
        otherwise, the remaining amount is split equally among the non-fixed participants.
        Transactions with 0 amount are skipped.
        """
        db_obj = self.get(obj_id)
        total_participants = len(db_obj.participants)
        if total_participants < 1:
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
        # convert shares to transactions
        tx_list: list[Transaction] = []
        for participant_id, participant_amount in shares.items():
            if participant_amount > Decimal("0.00"):
                if (
                    participant_id != db_obj.recipient_entity_id
                ):  # don't create transaction to self
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
        # save all transactions to split info
        db_obj.performed_transactions = tx_list
        # the one who performed the split is the actor now
        db_obj.actor_entity_id = actor_entity.id
        db_obj.performed = True
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj
