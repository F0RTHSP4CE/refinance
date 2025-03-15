"""Split model"""

from decimal import Decimal

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from sqlalchemy import DECIMAL, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

splits_tags = Table(
    "splits_tags",
    BaseModel.metadata,
    Column("split_id", ForeignKey("splits.id")),
    Column("tag_id", ForeignKey("tags.id")),
)

# table with senders of each split (many-to-many)
splits_participants = Table(
    "splits_participants",
    BaseModel.metadata,
    Column("split_id", ForeignKey("splits.id")),
    Column("participant_entity_id", ForeignKey("entities.id")),
)


class Split(BaseModel):
    __tablename__ = "splits"

    # split details
    recipient_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    recipient_entity: Mapped[Entity] = relationship(foreign_keys=[recipient_entity_id])
    participants: Mapped[list[Entity]] = relationship(secondary=splits_participants)
    performed: Mapped[bool] = mapped_column(default=False)

    # general details
    actor_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    actor_entity: Mapped[Entity] = relationship(foreign_keys=[actor_entity_id])
    tags: Mapped[list[Tag]] = relationship(secondary=splits_tags)

    # future transaction details
    amount: Mapped[Decimal] = mapped_column(DECIMAL(scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217
