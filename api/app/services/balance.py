"""Balance service"""

from decimal import Decimal

from app.models.transaction import Transaction, TransactionStatus
from app.schemas.balance import BalanceSchema
from app.services.entity import EntityService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func, select


class BalanceService:
    _cache = {}
    # cache for treasury balances
    _treasury_cache = {}

    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(),
    ):
        self.db = db
        self.entity_service = entity_service

    def invalidate_cache_entry(self, entity_id: int):
        self._cache.pop(entity_id, None)

    def invalidate_treasury_cache_entry(self, treasury_id: int):
        self._treasury_cache.pop(treasury_id, None)

    def get_balances(self, entity_id: int) -> BalanceSchema:
        """
        Calculate momentary balances for a given entity across all currencies.
        - status and non-status transactions are counted separately.
        - currencies are counted separately.

        Internal in-RAM cache stores balances of each entity.
        Balance cache for a particular entity is invalidated when transaction from/to
        entity is created, edited (status) or deleted.
        """
        if entity_id in self._cache:
            return self._cache[entity_id]
        else:
            result = self._get_balances(entity_id)
            self._cache[entity_id] = result
            return result

    def get_treasury_balances(self, treasury_id: int) -> BalanceSchema:
        """
        Calculate balances for a given treasury across all currencies.
        Similar to get_balances but using treasury fields in transactions.
        """
        if treasury_id in self._treasury_cache:
            return self._treasury_cache[treasury_id]

        # Function to sum transactions based on treasury fields and status
        def sum_transactions(status: TransactionStatus) -> dict[str, Decimal]:
            # Sum of incoming to treasury
            credit_query = (
                select(
                    Transaction.currency,
                    func.sum(Transaction.amount).label("total_credit"),
                )
                .where(
                    Transaction.to_treasury_id == treasury_id,
                    Transaction.status == status,
                )
                .group_by(Transaction.currency)
            )
            # Sum of outgoing from treasury
            debit_query = (
                select(
                    Transaction.currency,
                    func.sum(Transaction.amount).label("total_debit"),
                )
                .where(
                    Transaction.from_treasury_id == treasury_id,
                    Transaction.status == status,
                )
                .group_by(Transaction.currency)
            )

            credits = self.db.execute(credit_query).all()
            debits = self.db.execute(debit_query).all()

            credit_dict: dict[str, Decimal] = {
                res.currency: res.total_credit for res in credits
            }
            debit_dict: dict[str, Decimal] = {
                res.currency: res.total_debit for res in debits
            }

            total_by_currency: dict[str, Decimal] = {}
            for currency in set(credit_dict.keys()) | set(debit_dict.keys()):
                credit = credit_dict.get(currency, Decimal(0))
                debit = debit_dict.get(currency, Decimal(0))
                total_by_currency[currency] = credit - debit
            return total_by_currency

        result = BalanceSchema(
            completed=sum_transactions(status=TransactionStatus.COMPLETED),  # type: ignore
            draft=sum_transactions(status=TransactionStatus.DRAFT),  # type: ignore
        )
        self._treasury_cache[treasury_id] = result
        return result

    def _get_balances(self, entity_id: int) -> BalanceSchema:
        # Check that entity exists
        self.entity_service.get(entity_id)

        # Function to sum transactions based on confirmation status
        def sum_transactions(status: TransactionStatus) -> dict[str, Decimal]:
            # Query to get sum of all incoming transactions
            credit_query = select(
                Transaction.currency,
                func.sum(Transaction.amount).label("total_credit"),
            ).where(
                Transaction.to_entity_id == entity_id,
                Transaction.status == status,
            )

            # Query to get sum of all outgoing transactions
            debit_query = select(
                Transaction.currency,
                func.sum(Transaction.amount).label("total_debit"),
            ).where(
                Transaction.from_entity_id == entity_id,
                Transaction.status == status,
            )

            # Group sums by currency
            credit_query = credit_query.group_by(Transaction.currency)
            debit_query = debit_query.group_by(Transaction.currency)

            # Execute queries
            credits = self.db.execute(credit_query).all()
            debits = self.db.execute(debit_query).all()

            # Convert query results to dictionary for easier processing
            credit_dict: dict[str, Decimal] = {
                result.currency: result.total_credit for result in credits
            }
            debit_dict: dict[str, Decimal] = {
                result.currency: result.total_debit for result in debits
            }

            # Calculate the net balance for each currency
            total_by_currency: dict[str, Decimal] = {}
            all_currencies = set(credit_dict.keys()).union(set(debit_dict.keys()))
            for currency in all_currencies:
                credit = credit_dict.get(currency, Decimal(0))
                debit = debit_dict.get(currency, Decimal(0))
                total_by_currency[currency] = credit - debit

            return total_by_currency

        result = BalanceSchema(
            completed=sum_transactions(status=TransactionStatus.COMPLETED),  # type: ignore
            draft=sum_transactions(status=TransactionStatus.DRAFT),  # type: ignore
        )
        return result
