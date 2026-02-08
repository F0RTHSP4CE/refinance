"""Invoice model"""

import enum
from datetime import date
from typing import TYPE_CHECKING

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from sqlalchemy import JSON, Column, Date, Enum, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.transaction import Transaction

invoices_tags = Table(
    "invoices_tags",
    BaseModel.metadata,
    Column("invoice_id", ForeignKey("invoices.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class InvoiceStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(BaseModel):
    __tablename__ = "invoices"

    actor_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    actor_entity: Mapped[Entity] = relationship(foreign_keys=[actor_entity_id])

    from_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    from_entity: Mapped[Entity] = relationship(foreign_keys=[from_entity_id])

    to_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    to_entity: Mapped[Entity] = relationship(foreign_keys=[to_entity_id])

    amounts: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    billing_period: Mapped[date | None] = mapped_column(
        Date, nullable=True, default=None
    )

    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(
            InvoiceStatus,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            name="invoice_status",
        ),
        nullable=False,
        default=InvoiceStatus.PENDING,
    )

    tags: Mapped[list[Tag]] = relationship(secondary=invoices_tags)

    transaction: Mapped["Transaction | None"] = relationship(
        "Transaction", back_populates="invoice", uselist=False
    )

    @property
    def transaction_id(self) -> int | None:
        if self.transaction is None:
            return None
        return self.transaction.id
