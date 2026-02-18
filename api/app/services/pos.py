"""POS Service for processing point-of-sale payments.

Creates a completed transaction from a payer entity (resolved by exact name)
to a target entity, tagging the transaction with the `pos` tag. Returns the payer
entity and its updated balance after the transaction.
"""

from decimal import Decimal
from typing import Tuple

from app.dependencies.services import (
    get_balance_service,
    get_entity_service,
    get_transaction_service,
)
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
        entity_service: EntityService = Depends(get_entity_service),
        transaction_service: TransactionService = Depends(get_transaction_service),
        balance_service: BalanceService = Depends(get_balance_service),
    ):
        self._entity_service = entity_service
        self._transaction_service = transaction_service
        self._balance_service = balance_service

    def pos(
        self,
        *,
        entity_name: str,
        amount: Decimal,
        currency: str,
        to_entity_id: int,
        comment: str | None = None,
    ) -> Tuple[Entity, BalanceSchema]:
        """Process a POS payment.

        Steps:
        1. Resolve paying entity by exact name.
        2. Create a COMPLETED transaction from that entity to the target entity,
           tagged with the `pos` tag.
        3. Return (payer entity, payer balance schema) after cache invalidation done by TransactionService.
        """
        payer = self._entity_service.get_by_name(entity_name)

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

        balances = self._balance_service.get_balances(payer.id)
        return payer, balances
