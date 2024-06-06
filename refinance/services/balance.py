"""Balance service"""

from datetime import datetime
from decimal import Decimal

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func, select

from refinance.db import get_db
from refinance.models.transaction import Transaction
from refinance.schemas.balance import BalanceSchema
from refinance.services.entity import EntityService


class BalanceService:
    def __init__(
        self,
        db: Session = Depends(get_db),
        entity_service: EntityService = Depends(),
    ):
        self.db = db
        self.entity_service = entity_service

    def get_balances(
        self, entity_id: int, specific_date: datetime | None = None
    ) -> BalanceSchema:
        """
        Calculates the current balances for a given entity across all currencies.
        Only confirmed transactions are considered.
        """
        # Check that entity exists
        self.entity_service.get(entity_id)

        # Function to process transactions based on confirmation status
        def sum_transactions(confirmed: bool) -> dict[str, Decimal]:
            # Query to get sum of all incoming transactions
            credit_query = select(
                Transaction.currency,
                func.sum(Transaction.amount).label("total_credit"),
            ).where(
                Transaction.to_entity_id == entity_id,
                Transaction.confirmed == confirmed,
            )

            # Query to get sum of all outgoing transactions
            debit_query = select(
                Transaction.currency,
                func.sum(Transaction.amount).label("total_debit"),
            ).where(
                Transaction.from_entity_id == entity_id,
                Transaction.confirmed == confirmed,
            )

            # Date limiter — don't count transactions after this date
            if specific_date is not None:
                credit_query = credit_query.filter(
                    Transaction.created_at <= specific_date
                )
                debit_query = debit_query.filter(
                    Transaction.created_at <= specific_date
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

        return BalanceSchema(
            confirmed=sum_transactions(confirmed=True),
            non_confirmed=sum_transactions(confirmed=False),
        )
