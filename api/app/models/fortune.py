"""Persisted commit-reveal games for the Fortune lottery."""

import enum
from decimal import Decimal

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.transaction import Transaction
from sqlalchemy import DECIMAL, JSON, Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class FortuneGameStatus(enum.Enum):
    OPEN = "open"
    SETTLED = "settled"


class FortuneGame(BaseModel):
    __tablename__ = "fortune_games"
    __table_args__ = (
        Index("ix_fortune_games_actor_status", "actor_entity_id", "status"),
        {"sqlite_autoincrement": True},
    )

    actor_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    actor_entity: Mapped[Entity] = relationship(foreign_keys=[actor_entity_id])
    status: Mapped[FortuneGameStatus] = mapped_column(
        Enum(FortuneGameStatus), nullable=False, default=FortuneGameStatus.OPEN
    )

    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    commitment_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    commitment_source: Mapped[str] = mapped_column(Text, nullable=False)
    server_tiles: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    selected_tiles: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)

    stake: Mapped[Decimal | None] = mapped_column(DECIMAL(scale=2), nullable=True)
    boosted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(scale=2), nullable=True)
    gross_prize: Mapped[Decimal | None] = mapped_column(DECIMAL(scale=2), nullable=True)
    won: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    settlement_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(scale=2), nullable=True
    )

    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, unique=True
    )
    transaction: Mapped[Transaction | None] = relationship(
        foreign_keys=[transaction_id]
    )
