"""Balance service"""

from decimal import Decimal

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func, select

from refinance.db import get_db
from refinance.models.transaction import Transaction
from refinance.repository.entity import EntityRepository
from refinance.schemas.balance import BalanceSchema


class BalanceService:
    def __init__(
        self,
        db: Session = Depends(get_db),
        entity_repository: EntityRepository = Depends(),
    ):
        self.db = db
        self.entity_repository = entity_repository

    def get_balances(self, entity_id: int) -> BalanceSchema:
        """
        Calculates the current balances for a given entity across all currencies.
        Only confirmed transactions are considered.
        """
        # Check that entity exists
        self.entity_repository.get(entity_id)

        # Function to process transactions based on confirmation status
        def sum_transactions(confirmed: bool) -> dict[str, Decimal]:
            # Query to get sum of all incoming transactions grouped by currency
            credit_query = (
                select(
                    Transaction.currency,
                    func.sum(Transaction.amount).label("total_credit"),
                )
                .where(
                    Transaction.to_entity_id == entity_id,
                    Transaction.confirmed == confirmed,
                )
                .group_by(Transaction.currency)
            )

            # Query to get sum of all outgoing transactions grouped by currency
            debit_query = (
                select(
                    Transaction.currency,
                    func.sum(Transaction.amount).label("total_debit"),
                )
                .where(
                    Transaction.from_entity_id == entity_id,
                    Transaction.confirmed == confirmed,
                )
                .group_by(Transaction.currency)
            )

            # Execute queries
            credits = self.db.execute(credit_query).all()
            debits = self.db.execute(debit_query).all()

            # Convert query results to dictionary for easier processing
            credit_dict = {result.currency: result.total_credit for result in credits}
            debit_dict = {result.currency: result.total_debit for result in debits}

            # Calculate the net balance for each currency
            currencies: dict[str, Decimal] = {}
            all_currencies = set(credit_dict.keys()).union(set(debit_dict.keys()))
            for currency in all_currencies:
                credit = credit_dict.get(currency, 0)
                debit = debit_dict.get(currency, 0)
                currencies[currency] = credit - debit

            return currencies

        return BalanceSchema(
            confirmed=sum_transactions(confirmed=True),
            non_confirmed=sum_transactions(confirmed=False),
        )
