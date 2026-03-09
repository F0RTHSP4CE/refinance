"""Balance service"""

from datetime import date, datetime, time

from app.dependencies.services import get_entity_service
from app.models.transaction import TransactionStatus
from app.schemas.balance import BalanceSchema
from app.services.balance_queries import sum_entity_balances, sum_treasury_balances
from app.services.entity import EntityService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class BalanceService:
    _cache = {}
    # cache for treasury balances
    _treasury_cache = {}

    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(get_entity_service),
    ):
        self.db = db
        self.entity_service = entity_service

    def invalidate_cache_entry(self, entity_id: int):
        self._cache.pop(entity_id, None)

    def invalidate_treasury_cache_entry(self, treasury_id: int):
        self._treasury_cache.pop(treasury_id, None)

    def get_balances(
        self, entity_id: int, end_date: date | None = None
    ) -> BalanceSchema:
        """
        Calculate momentary balances for a given entity across all currencies.
        - status and non-status transactions are counted separately.
        - currencies are counted separately.

        Internal in-RAM cache stores balances of each entity.
        Balance cache for a particular entity is invalidated when transaction from/to
        entity is created, edited (status) or deleted.
        """
        if end_date is None:
            if entity_id in self._cache:
                return self._cache[entity_id]
            result = self._get_balances(entity_id)
            self._cache[entity_id] = result
            return result

        return self._get_balances(entity_id, end_date=end_date)

    def get_treasury_balances(self, treasury_id: int) -> BalanceSchema:
        """
        Calculate balances for a given treasury across all currencies.
        Similar to get_balances but using treasury fields in transactions.
        """
        if treasury_id in self._treasury_cache:
            return self._treasury_cache[treasury_id]

        result = BalanceSchema(
            completed=sum_treasury_balances(
                db=self.db,
                treasury_id=treasury_id,
                status=TransactionStatus.COMPLETED,
            ),
            draft=sum_treasury_balances(
                db=self.db,
                treasury_id=treasury_id,
                status=TransactionStatus.DRAFT,
            ),
        )
        self._treasury_cache[treasury_id] = result
        return result

    def _get_balances(
        self, entity_id: int, end_date: date | None = None
    ) -> BalanceSchema:
        # Check that entity exists
        self.entity_service.get(entity_id)

        end_datetime: datetime | None = None
        if end_date is not None:
            end_datetime = datetime.combine(end_date, time.max)

        result = BalanceSchema(
            completed=sum_entity_balances(
                db=self.db,
                entity_id=entity_id,
                status=TransactionStatus.COMPLETED,
                end_datetime=end_datetime,
            ),
            draft=sum_entity_balances(
                db=self.db,
                entity_id=entity_id,
                status=TransactionStatus.DRAFT,
                end_datetime=end_datetime,
            ),
        )
        return result
