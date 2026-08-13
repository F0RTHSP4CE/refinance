"""Deposit service"""

import logging
from html import escape
from typing import Any
from uuid import UUID

from app.dependencies.services import (
    get_notification_service,
    get_tag_service,
    get_transaction_service,
)
from app.errors.common import NotFoundError
from app.errors.deposit import DepositAlreadyCompleted, DepositCannotBeEdited
from app.models.deposit import Deposit, DepositStatus
from app.models.entity import Entity
from app.models.transaction import TransactionStatus
from app.schemas.deposit import DepositFiltersSchema, DepositUpdateSchema
from app.schemas.transaction import TransactionCreateSchema
from app.seeding import (
    anonymous_entity,
    deposit_tag,
    donation_tag,
    f0_entity,
    keepz_treasury,
)
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.notification import NotificationService
from app.services.tag import TagService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

logger = logging.getLogger(__name__)


class DepositService(TaggableServiceMixin[Deposit], BaseService[Deposit]):
    model = Deposit

    def __init__(
        self,
        db: Session = Depends(get_uow),
        transaction_service: TransactionService = Depends(get_transaction_service),
        tag_service: TagService = Depends(get_tag_service),
        notification_service: NotificationService = Depends(get_notification_service),
    ):
        self.db = db
        self._transaction_service = transaction_service
        self._tag_service = tag_service
        self._notification_service = notification_service

    def _apply_filters(
        self, query: Query[Deposit], filters: DepositFiltersSchema
    ) -> Query[Deposit]:
        if filters.entity_id is not None:
            query = query.filter(
                or_(
                    self.model.to_entity_id == filters.entity_id,
                    self.model.actor_entity_id == filters.entity_id,
                )
            )
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.from_entity_id is not None:
            query = query.filter(self.model.from_entity_id == filters.from_entity_id)
        if filters.to_entity_id is not None:
            query = query.filter(self.model.to_entity_id == filters.to_entity_id)
        if filters.amount_min is not None:
            query = query.filter(self.model.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(self.model.amount <= filters.amount_max)
        if filters.currency is not None:
            query = query.filter(self.model.currency == filters.currency)
        if filters.status is not None:
            query = query.filter(self.model.status == filters.status)
        if filters.provider is not None:
            query = query.filter(self.model.provider == filters.provider)
        if filters.to_treasury_id is not None:
            query = query.filter(self.model.to_treasury_id == filters.to_treasury_id)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def get_by_uuid(self, uuid: UUID) -> Deposit:
        db_obj = self.db.query(self.model).filter(self.model.uuid == uuid).first()
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} uuid={uuid}")
        return db_obj

    def delete(self, obj_id: int):
        """Deposits should not be deleted. They can either be cancelled or completed."""
        raise NotImplementedError

    def complete(self, obj_id: int):
        # change deposit status to completed and create transaction to top-up user balane
        db_obj = self.get(obj_id)
        if db_obj.status == DepositStatus.PENDING:
            tx = self._transaction_service.create(
                TransactionCreateSchema(
                    amount=db_obj.amount,
                    currency=db_obj.currency,
                    from_entity_id=db_obj.from_entity_id,
                    to_entity_id=db_obj.to_entity_id,
                    status=TransactionStatus.COMPLETED,
                    to_treasury_id=db_obj.to_treasury_id,
                    from_treasury_id=None,  # deposits are not from treasuries
                    tag_ids=[deposit_tag.id],
                    comment=f"deposit #{db_obj.id}: {db_obj.provider}",
                ),
                overrides={"actor_entity_id": db_obj.actor_entity_id},
            )
            self.update(obj_id, DepositUpdateSchema(status=DepositStatus.COMPLETED))
            if db_obj.to_entity_id == anonymous_entity.id:
                self._complete_donation(db_obj)
            return tx
        else:
            raise DepositAlreadyCompleted

    def _donation_recipient(self, details: dict) -> Entity:
        """Resolve the entity a donation is routed to (a room or F0 by default)."""
        recipient_id = details.get("donation_recipient_id")
        if recipient_id:
            try:
                recipient_id = int(recipient_id)
            except (TypeError, ValueError):
                recipient_id = None
            if recipient_id and recipient_id != f0_entity.id:
                recipient = (
                    self.db.query(Entity).filter(Entity.id == recipient_id).first()
                )
                if recipient is not None and recipient.active:
                    return recipient
                logger.warning(
                    "Donation recipient id=%s not found or inactive, "
                    "falling back to F0",
                    recipient_id,
                )
        return self.db.query(Entity).filter(Entity.id == f0_entity.id).one()

    def _complete_donation(self, deposit: Deposit) -> None:
        """After a guest donation deposit completes, transfer funds to the chosen
        recipient (F0 or one of its rooms) and notify."""
        details = deposit.details or {}
        comment = details.get("donation_comment", "")
        stripe_details = details.get("stripe", {})
        is_recurring = (
            stripe_details.get("charge_mode") == "guest_static"
            or stripe_details.get("mode") == "subscription_invoice"
        )
        recipient = self._donation_recipient(details)
        try:
            self._transaction_service.create(
                TransactionCreateSchema(
                    amount=deposit.amount,
                    currency=deposit.currency,
                    from_entity_id=anonymous_entity.id,
                    to_entity_id=recipient.id,
                    status=TransactionStatus.COMPLETED,
                    tag_ids=[donation_tag.id],
                    comment=comment,
                ),
                overrides={"actor_entity_id": anonymous_entity.id},
            )
        except Exception:
            logger.exception(
                "Failed to create donation transfer for deposit id=%s", deposit.id
            )
            return

        try:
            chat_id = self._notification_service.config.donation_notification_chat_id
            if chat_id:
                amount_str = f"{deposit.amount} {deposit.currency.upper()}"
                label = "Subscription donation" if is_recurring else "New donation"
                message = (
                    f"🎁 {label} → <b>{escape(recipient.name)}</b>: "
                    f"<b>{amount_str}</b>"
                )
                if comment:
                    message += f"\n<i>{escape(comment)}</i>"
                topic_id = (
                    self._notification_service.config.donation_notification_topic_id
                )
                self._notification_service.send_to_chat(
                    chat_id, message, topic_id=topic_id
                )
        except Exception:
            logger.exception(
                "Failed to send donation notification for deposit id=%s", deposit.id
            )

    def update(
        self, obj_id: int, schema: DepositUpdateSchema, overrides: dict = {}
    ) -> Deposit:
        db_obj = self.get(obj_id)
        if db_obj.status in (
            DepositStatus.FAILED,
            DepositStatus.COMPLETED,
            DepositStatus.CANCELLED,
        ):
            raise DepositCannotBeEdited
        return super().update(obj_id, schema, overrides)
