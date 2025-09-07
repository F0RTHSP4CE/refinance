"""POS Service for processing point-of-sale (card) payments.

Creates a completed transaction from a card-holding entity (resolved by card_hash)
TO a target entity, tagging the transaction with the `pos` tag. Returns the payer
entity and its updated balance after the transaction.
"""

from decimal import Decimal
from typing import Tuple

from app.models.entity import Entity
from app.models.transaction import TransactionStatus
from app.schemas.balance import BalanceSchema
from app.schemas.transaction import TransactionCreateSchema
from app.seeding import pos_tag
from app.services.balance import BalanceService
from app.services.entity import EntityService
from app.services.transaction import TransactionService
from fastapi import Depends


class POSService:
    def __init__(
        self,
        entity_service: EntityService = Depends(),
        transaction_service: TransactionService = Depends(),
        balance_service: BalanceService = Depends(),
    ):
        self._entity_service = entity_service
        self._transaction_service = transaction_service
        self._balance_service = balance_service

    def pos(
        self,
        *,
        card_hash: str,
        amount: Decimal,
        currency: str,
        to_entity_id: int,
        comment: str | None = None,
    ) -> Tuple[Entity, BalanceSchema]:
        """Process a POS payment.

        Steps:
        1. Resolve paying entity by card hash.
        2. Create a COMPLETED transaction from that entity to the target entity,
           tagged with the `pos` tag.
        3. Return (payer entity, payer balance schema) after cache invalidation done by TransactionService.
        """
        payer = self._entity_service.get_by_card_hash(card_hash)

        # Build and create the transaction. actor_entity_id is the same as from_entity.
        self._transaction_service.create(
            TransactionCreateSchema(
                amount=amount,
                currency=currency,
                from_entity_id=payer.id,
                to_entity_id=to_entity_id,
                status=TransactionStatus.COMPLETED,
                tag_ids=[pos_tag.id],
                comment=comment,
            ),
            overrides={"actor_entity_id": payer.id},
        )

        # Fetch updated balances for the payer entity.
        balances = self._balance_service.get_balances(payer.id)
        return payer, balances
