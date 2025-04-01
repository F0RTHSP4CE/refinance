"""Split model with fixed amounts for participants"""

from decimal import ROUND_DOWN, Decimal

from app.models.base import Base, BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from sqlalchemy import DECIMAL, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

# table for tags remains the same
splits_tags = Table(
    "splits_tags",
    BaseModel.metadata,
    Column("split_id", ForeignKey("splits.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class SplitParticipant(Base):
    __tablename__ = "splits_participants"
    split_id: Mapped[int] = mapped_column(ForeignKey("splits.id"), primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), primary_key=True)

    # Optional fixed amount; if None, then this participant will share in the remaining amount.
    fixed_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(scale=2), nullable=True
    )

    split: Mapped["Split"] = relationship("Split", back_populates="participants")
    entity: Mapped[Entity] = relationship("Entity")


class Split(BaseModel):
    __tablename__ = "splits"

    # Split details
    recipient_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    recipient_entity: Mapped[Entity] = relationship(foreign_keys=[recipient_entity_id])
    # Use an association object to store fixed amounts for participants.
    participants: Mapped[list[SplitParticipant]] = relationship(
        "SplitParticipant", back_populates="split"
    )
    performed: Mapped[bool] = mapped_column(default=False)

    # General details
    actor_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    actor_entity: Mapped[Entity] = relationship(foreign_keys=[actor_entity_id])
    tags: Mapped[list[Tag]] = relationship(secondary=splits_tags)

    # Future transaction details
    amount: Mapped[Decimal] = mapped_column(DECIMAL(scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217

    @property
    def share_preview(self) -> Decimal:
        """
        PREVIEW AMOUNT ONLY.
        REAL SHARES ARE CALCULATED IN THE SPLIT SERVICE.

        For non-fixed participants, calculates the share as the remaining amount
        divided by the number of participants without a fixed amount.
        Returns a Decimal with exactly two decimal places.
        If there are no non-fixed participants or no remaining amount, returns Decimal('0.00').
        """
        fixed_total = sum(
            assoc.fixed_amount or Decimal("0.00")
            for assoc in self.participants
            if assoc.fixed_amount is not None
        )
        non_fixed_count = len(
            [assoc for assoc in self.participants if assoc.fixed_amount is None]
        )
        remaining = self.amount - fixed_total
        if non_fixed_count == 0 or remaining <= Decimal("0.00"):
            return Decimal("0.00")
        share = remaining / Decimal(non_fixed_count)
        return share.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
