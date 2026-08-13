"""Stripe card authorizations for recurring charges."""

import enum
from datetime import datetime
from decimal import Decimal

from app.models.base import BaseModel
from app.models.entity import Entity
from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class StripeAuthorizationMode(enum.Enum):
    ENTITY_DYNAMIC = "entity_dynamic"
    GUEST_STATIC = "guest_static"


class StripeAuthorization(BaseModel):
    __tablename__ = "stripe_authorizations"
    __table_args__ = (
        UniqueConstraint(
            "entity_id",
            "stripe_payment_method_id",
            name="uq_stripe_authorizations_entity_payment_method",
        ),
        CheckConstraint(
            "(mode = 'ENTITY_DYNAMIC' AND static_amount = 0 AND static_currency IS NULL) OR "
            "(mode = 'GUEST_STATIC' AND static_amount > 0 AND static_currency IS NOT NULL)",
            name="ck_stripe_authorizations_mode_static",
        ),
        Index(
            "ix_stripe_authorizations_entity_active_mode_priority",
            "entity_id",
            "active",
            "mode",
            "priority",
        ),
        {"sqlite_autoincrement": True},
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    entity: Mapped[Entity] = relationship(foreign_keys=[entity_id])

    stripe_customer_id: Mapped[str] = mapped_column(String, nullable=False)
    stripe_payment_method_id: Mapped[str] = mapped_column(String, nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)

    mode: Mapped[StripeAuthorizationMode] = mapped_column(
        Enum(StripeAuthorizationMode),
        nullable=False,
        default=StripeAuthorizationMode.ENTITY_DYNAMIC,
    )

    static_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )
    static_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # guest_static donations only: entity the donation is routed to (room or F0)
    donation_recipient_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True
    )

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    consecutive_error_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    card_brand: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_exp_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_exp_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
