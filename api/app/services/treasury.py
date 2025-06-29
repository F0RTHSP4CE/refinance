"""Treasury service"""

from decimal import Decimal

from app.errors.common import NotFoundError
from app.errors.treasury import TreasuryDeletionError
from app.models.transaction import Transaction, TransactionStatus
from app.models.treasury import Treasury
from app.schemas.balance import BalanceSchema
from app.schemas.base import PaginationSchema  # for type hints
from app.schemas.base import CurrencyDecimal
from app.schemas.treasury import (
    TreasuryCreateSchema,
    TreasuryFiltersSchema,
    TreasurySchema,
    TreasuryUpdateSchema,
)
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class TreasuryService(BaseService[Treasury]):
    model = Treasury

    def __init__(
        self,
        db: Session = Depends(get_uow),
        balance_service: BalanceService = Depends(),
    ):
        self.db = db
        self._balance_service = balance_service

    def get(self, obj_id: int) -> Treasury:  # type: ignore[override]
        treasury = super().get(obj_id)
        # attach balances as raw dict for serialization
        balances = self._balance_service.get_treasury_balances(treasury.id)
        setattr(treasury, "balances", balances.dump())
        return treasury

    def get_all(  # type: ignore[override]
        self, filters: TreasuryFiltersSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[Treasury]:
        # fetch paginated treasuries
        pagination = super().get_all(filters, skip, limit)
        # attach balances as raw dict for each treasury
        for treasury in pagination.items:
            balances = self._balance_service.get_treasury_balances(treasury.id)
            setattr(treasury, "balances", balances.dump())
        return pagination

    def delete(self, obj_id: int) -> int:  # type: ignore[override]
        """Delete a treasury if it is not in use by any transaction."""
        # check if treasury is used in any transaction
        count = (
            self.db.query(Transaction)
            .filter(
                (Transaction.from_treasury_id == obj_id)
                | (Transaction.to_treasury_id == obj_id)
            )
            .count()
        )
        if count > 0:
            raise TreasuryDeletionError(f"Treasury.id={obj_id}")
        return super().delete(obj_id)

    def transaction_will_overdraft_treasury(self, tx_id: int) -> bool:
        """
        Check if a draft transaction will overdraft the treasury balance when applied.
        """
        tx = self.db.query(Transaction).filter(Transaction.id == tx_id).first()
        if not tx:
            raise NotFoundError(f"Transaction id={tx_id}")
        if tx.from_treasury_id is None or tx.status == TransactionStatus.COMPLETED:
            return False
        # get completed balances for treasury
        # get balances; converted to raw Decimal values
        balances = self._balance_service.get_treasury_balances(tx.from_treasury_id)
        # get current balance; may be CurrencyDecimal or Decimal
        current_val = balances.completed.get(tx.currency, Decimal(0))
        # ensure Decimal type: unwrap CurrencyDecimal or accept Decimal
        if isinstance(current_val, CurrencyDecimal):
            current_decimal: Decimal = current_val.to_decimal()  # type: ignore
        else:
            current_decimal: Decimal = current_val  # type: ignore
        # simulate applying tx
        return current_decimal - tx.amount < 0
