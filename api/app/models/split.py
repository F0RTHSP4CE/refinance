"""Split model with fixed amounts for participants"""

from decimal import ROUND_DOWN, Decimal
from typing import Literal

from app.models.base import Base, BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from app.models.transaction import Transaction
from app.schemas.split import SplitSharePreview
from sqlalchemy import DECIMAL, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

splits_tags = Table(
    "splits_tags",
    BaseModel.metadata,
    Column("split_id", ForeignKey("splits.id")),
    Column("tag_id", ForeignKey("tags.id")),
)

# stores all transaction ids here after performing a split
splits_transactions = Table(
    "splits_transactions",
    BaseModel.metadata,
    Column("split_id", ForeignKey("splits.id")),
    Column("transaction_id", ForeignKey("transactions.id")),
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
        "SplitParticipant",
        back_populates="split",
        cascade="all, delete-orphan",
        collection_class=list,
    )
    performed: Mapped[bool] = mapped_column(default=False)
    performed_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", secondary=splits_transactions, collection_class=list
    )

    # General details
    actor_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False
    )
    actor_entity: Mapped[Entity] = relationship(foreign_keys=[actor_entity_id])
    tags: Mapped[list[Tag]] = relationship("Tag", secondary=splits_tags)

    # Future transaction details
    amount: Mapped[Decimal] = mapped_column(DECIMAL(scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217

    @property
    def share_preview(self) -> SplitSharePreview:
        """
        PREVIEW AMOUNT ONLY.
        REAL SHARES ARE CALCULATED IN THE SPLIT SERVICE.

        For non-fixed participants, calculates the share as the remaining amount
        divided by the number of participants without a fixed amount.
        Returns a Decimal with exactly two decimal places.
        If there are no non-fixed participants or no remaining amount, returns Decimal('0.00').
        """
        try:
            fixed_total = sum(
                assoc.fixed_amount or Decimal("0.00")
                for assoc in self.participants
                if assoc.fixed_amount is not None
            )
            non_fixed_count = len(
                [assoc for assoc in self.participants if assoc.fixed_amount is None]
            )
            remaining = self.amount - fixed_total
            share = remaining / Decimal(non_fixed_count or 1)
            share = share.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            share_next = remaining / Decimal(non_fixed_count + 1)
            improvement = 100 - share_next / share * Decimal("100")
            return SplitSharePreview(
                current_share=share or Decimal("0"),
                next_share=share_next.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
                or Decimal("0"),
            )
        except:
            return SplitSharePreview(
                current_share=Decimal("0"),
                next_share=Decimal("0"),
            )

    @property
    def collected_amount(self) -> Decimal | Literal[0]:
        """
        Calculates the progress of the split as the percentage of the total amount
        covered by fixed amounts assigned to participants.

        Returns:
            A Decimal representing the percentage (0 to 100) rounded to one decimal.
        """
        return sum(
            assoc.fixed_amount or Decimal("0.0") for assoc in self.participants
        ) or Decimal("0")
