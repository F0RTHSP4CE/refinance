"""Deposit model"""

import enum
import uuid as u
from decimal import Decimal

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from sqlalchemy import DECIMAL, UUID, Column, Enum, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

deposits_tags = Table(
    "deposits_tags",
    BaseModel.metadata,
    Column("deposit_id", ForeignKey("deposits.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class DepositStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Deposit(BaseModel):
    __tablename__ = "deposits"

    # not used as id, but rather as a security measure to prevent deposit bruteforce via url
    uuid: Mapped[u.UUID] = relationship(UUID, primary_key=True)

    actor_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    actor_entity: Mapped[Entity] = relationship(foreign_keys=[actor_entity_id])

    to_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    to_entity: Mapped[Entity] = relationship(foreign_keys=[to_entity_id])

    provider: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217
    status: Mapped[DepositStatus] = mapped_column(
        Enum(DepositStatus), nullable=False, default=DepositStatus.PENDING
    )

    tags: Mapped[list[Tag]] = relationship(secondary=deposits_tags)
