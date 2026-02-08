"""Transaction service"""

from typing import TYPE_CHECKING, Any

from app.dependencies.services import (
    get_balance_service,
    get_tag_service,
    get_treasury_service,
)
from app.errors.transaction import (
    CompletedTransactionNotDeletable,
    CompletedTransactionNotEditable,
    TransactionWillOverdraftTreasury,
)
from app.models.entity import Entity
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import (
    TransactionCreateSchema,
    TransactionFiltersSchema,
    TransactionUpdateSchema,
)
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.services.treasury import TreasuryService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

if TYPE_CHECKING:
    from app.services.invoice import InvoiceService
    from app.services.stats import StatsService


class TransactionService(TaggableServiceMixin[Transaction], BaseService[Transaction]):
    model = Transaction

    def __init__(
        self,
        db: Session = Depends(get_uow),
        balance_service: BalanceService = Depends(get_balance_service),
        tag_service: TagService = Depends(get_tag_service),
        treasury_service: TreasuryService = Depends(get_treasury_service),
        invoice_service: Any | None = None,
    ):
        self.db = db
        self._balance_service = balance_service
        self._tag_service = tag_service
        self._treasury_service = treasury_service
        self._invoice_service = invoice_service

    def set_invoice_service(self, invoice_service: "InvoiceService") -> None:
        self._invoice_service = invoice_service

    def _get_invoice_service(self) -> "InvoiceService":
        if self._invoice_service is None:
            raise RuntimeError(
                "InvoiceService dependency is not configured for TransactionService."
            )
        return self._invoice_service

    def _invalidate_related_caches(
        self,
        from_entity_id: int | None,
        to_entity_id: int | None,
        *treasury_ids: int | None,
        invalidate_stats: bool = False,
    ) -> None:
        """Invalidate cache entries for affected entities and treasuries."""

        entity_ids: set[int] = set()
        for entity_id in (from_entity_id, to_entity_id):
            if entity_id is None:
                continue
            self._balance_service.invalidate_cache_entry(entity_id)
            entity_ids.add(entity_id)

        for tid in treasury_ids:
            if tid is not None:
                self._balance_service.invalidate_treasury_cache_entry(tid)

        if invalidate_stats and entity_ids:
            from app.services.stats import StatsService

            StatsService.invalidate_entity_cache(*entity_ids)

    def _apply_filters(  # type: ignore[override]
        self, query: Query[Transaction], filters: TransactionFiltersSchema
    ) -> Query[Transaction]:
        if filters.entity_id is not None:
            query = query.filter(
                or_(
                    self.model.from_entity_id == filters.entity_id,
                    self.model.to_entity_id == filters.entity_id,
                    self.model.actor_entity_id == filters.actor_entity_id,
                )
            )
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.from_entity_id is not None:
            query = query.filter(self.model.from_entity_id == filters.from_entity_id)
        if filters.to_entity_id is not None:
            query = query.filter(self.model.to_entity_id == filters.to_entity_id)
        if filters.invoice_id is not None:
            query = query.filter(self.model.invoice_id == filters.invoice_id)
        if filters.treasury_id is not None:
            query = query.filter(
                or_(
                    self.model.from_treasury_id == filters.treasury_id,
                    self.model.to_treasury_id == filters.treasury_id,
                )
            )
        if filters.amount_min is not None:
            query = query.filter(self.model.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(self.model.amount <= filters.amount_max)
        if filters.currency is not None:
            query = query.filter(self.model.currency == filters.currency)
        if filters.comment is not None:
            query = query.filter(self.model.comment.ilike(f"%{filters.comment}%"))
        if filters.status is not None:
            query = query.filter(self.model.status == filters.status)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def create(  # type: ignore[override]
        self, schema: TransactionCreateSchema, overrides: dict = {}
    ) -> Transaction:
        if (
            schema.status == TransactionStatus.COMPLETED
            and self._treasury_service.transaction_will_overdraft_treasury(
                treasury_id=schema.from_treasury_id,
                currency=schema.currency,
                amount=schema.amount,
            )
        ):
            raise TransactionWillOverdraftTreasury
        if schema.invoice_id is not None:
            invoice_service = self._get_invoice_service()
            invoice_service.validate_transaction_for_invoice(
                invoice_id=schema.invoice_id,
                tx_id=None,
                from_entity_id=schema.from_entity_id,
                to_entity_id=schema.to_entity_id,
                amount=schema.amount,
                currency=schema.currency,
                status=schema.status or TransactionStatus.DRAFT,
            )
            invoice = invoice_service.get(schema.invoice_id)
            invoice_tag_ids = {tag.id for tag in invoice.tags}
            if invoice_tag_ids:
                schema.tag_ids = list(set(schema.tag_ids) | invoice_tag_ids)
            if not schema.comment and invoice.comment:
                schema.comment = invoice.comment
        # invalidate caches for creation
        self._invalidate_related_caches(
            schema.from_entity_id,
            schema.to_entity_id,
            schema.from_treasury_id,
            schema.to_treasury_id,
            invalidate_stats=True,
        )
        return super().create(schema, overrides)

    def update(  # type: ignore[override]
        self, obj_id: int, schema: TransactionUpdateSchema, overrides: dict = {}
    ) -> Transaction:
        tx = self.get(obj_id)
        # prevent editing of a completed transaction
        if tx.status == TransactionStatus.COMPLETED:
            raise CompletedTransactionNotEditable
        if schema.invoice_id is not None and tx.invoice_id is not None:
            if schema.invoice_id != tx.invoice_id:
                from app.errors.invoice import InvoiceTransactionReassignmentNotAllowed

                raise InvoiceTransactionReassignmentNotAllowed
        if (
            tx.invoice_id is not None
            and schema.invoice_id is None
            and "invoice_id" in schema.model_fields_set
        ):
            from app.errors.invoice import InvoiceTransactionReassignmentNotAllowed

            raise InvoiceTransactionReassignmentNotAllowed
        # prevent overdrafting treasury on confirmation
        if (
            schema.status == TransactionStatus.COMPLETED
            and self._treasury_service.transaction_will_overdraft_treasury(
                treasury_id=(
                    schema.from_treasury_id
                    if schema.from_treasury_id is not None
                    else tx.from_treasury_id
                ),
                currency=(
                    schema.currency if schema.currency is not None else tx.currency
                ),
                amount=schema.amount if schema.amount is not None else tx.amount,
            )
        ):
            raise TransactionWillOverdraftTreasury
        resolved_invoice_id = schema.invoice_id or tx.invoice_id
        if resolved_invoice_id is not None:
            invoice_service = self._get_invoice_service()
            invoice_service.validate_transaction_for_invoice(
                invoice_id=resolved_invoice_id,
                tx_id=tx.id,
                from_entity_id=tx.from_entity_id,
                to_entity_id=tx.to_entity_id,
                amount=schema.amount if schema.amount is not None else tx.amount,
                currency=(
                    schema.currency if schema.currency is not None else tx.currency
                ),
                status=schema.status if schema.status is not None else tx.status,
            )
        # invalidate caches for update
        self._invalidate_related_caches(
            tx.from_entity_id,
            tx.to_entity_id,
            tx.from_treasury_id,
            tx.to_treasury_id,
            schema.from_treasury_id,
            schema.to_treasury_id,
            invalidate_stats=schema.status == TransactionStatus.COMPLETED
            or tx.status == TransactionStatus.COMPLETED,
        )
        updated_tx = super().update(obj_id, schema, overrides)
        if resolved_invoice_id is not None:
            invoice = self._invoice_service.get(resolved_invoice_id)
            invoice_tag_ids = {tag.id for tag in invoice.tags}
            if invoice_tag_ids:
                current_tag_ids = {tag.id for tag in updated_tx.tags}
                merged_tag_ids = list(current_tag_ids | invoice_tag_ids)
                self.set_tags(updated_tx, merged_tag_ids)
                self.db.flush()
                self.db.refresh(updated_tx)
            if (
                "comment" not in schema.model_fields_set
                and not updated_tx.comment
                and invoice.comment
            ):
                updated_tx.comment = invoice.comment
                self.db.flush()
                self.db.refresh(updated_tx)
        return updated_tx

    def delete(self, obj_id: int) -> int:  # type: ignore[override]
        tx = self.get(obj_id)
        # prevent deleting of a completed transaction
        if tx.status == TransactionStatus.COMPLETED:
            raise CompletedTransactionNotDeletable
        # invalidate caches for deletion
        self._invalidate_related_caches(
            tx.from_entity_id,
            tx.to_entity_id,
            tx.from_treasury_id,
            tx.to_treasury_id,
            invalidate_stats=tx.status == TransactionStatus.COMPLETED,
        )
        return super().delete(obj_id)
