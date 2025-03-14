"""Currency exchange service"""

from api.app.schemas.currency_exchange import CurrencyExchangeSchema
from api.app.services.transaction import TransactionService
from app.db import get_db
from app.models.entity import Entity
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreateSchema,
    TransactionFiltersSchema,
    TransactionUpdateSchema,
)
from app.services.base import BaseService
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

class CurrencyExchangeService:
    def __init__(
        self, db: Session = Depends(get_db), transaction_service: TransactionService = Depends()
    ):
        self.db = db
        self._transaction_service = transaction_service

    def exchange(self, currency_exchange_schema: CurrencyExchangeSchema):
        pass
    