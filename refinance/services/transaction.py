"""Transaction service"""

from fastapi import Depends
from sqlalchemy.orm import Session

from refinance.db import get_db
from refinance.models.transaction import Transaction
from refinance.repository.transaction import TransactionRepository
from refinance.schemas.base import PaginationSchema
from refinance.schemas.transaction import (
    TransactionCreateSchema,
    TransactionFiltersSchema,
    TransactionUpdateSchema,
)
from refinance.services.base import BaseService
from refinance.services.mixins.taggable_mixin import TaggableServiceMixin


class TransactionService(TaggableServiceMixin, BaseService[Transaction]):
    model = Transaction

    def __init__(
        self, repo: TransactionRepository = Depends(), db: Session = Depends(get_db)
    ):
        super().__init__(repo=repo, db=db)

    def create(self, schema: TransactionCreateSchema) -> Transaction:
        new_obj = self.model(**schema.dump())
        db_obj = self.repo.create(new_obj)
        return db_obj

    def get(self, transaction_id: int) -> Transaction:
        return self.repo.get(transaction_id)

    def get_all(
        self, filters: TransactionFiltersSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[Transaction]:
        return self.repo.get_all(filters, skip, limit)

    def update(
        self, transaction_id, transaction_update: TransactionUpdateSchema
    ) -> Transaction:
        return self.repo.update(transaction_id, transaction_update.dump())
