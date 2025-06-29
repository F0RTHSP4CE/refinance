"""Transaction model"""

import enum
from decimal import Decimal

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from app.models.treasury import Treasury
from sqlalchemy import DECIMAL, Column, Enum, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

transactions_tags = Table(
    "transactions_tags",
    BaseModel.metadata,
    Column("transaction_id", ForeignKey("transactions.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class TransactionStatus(enum.Enum):
    DRAFT = "draft"
    COMPLETED = "completed"


class Transaction(BaseModel):
    __tablename__ = "transactions"

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

    amount: Mapped[Decimal] = mapped_column(DECIMAL(scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), nullable=False, default=TransactionStatus.DRAFT
    )

    tags: Mapped[list[Tag]] = relationship(secondary=transactions_tags)

    # Optional treasury fields
    from_treasury_id: Mapped[int | None] = mapped_column(
        ForeignKey("treasuries.id"), nullable=True
    )
    from_treasury: Mapped[Treasury] = relationship(foreign_keys=[from_treasury_id])

    to_treasury_id: Mapped[int | None] = mapped_column(
        ForeignKey("treasuries.id"), nullable=True
    )
    to_treasury: Mapped[Treasury] = relationship(foreign_keys=[to_treasury_id])
