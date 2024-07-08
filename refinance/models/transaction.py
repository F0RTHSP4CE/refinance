"""Transaction model"""

from sqlalchemy import DECIMAL, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from refinance.models.base import BaseModel
from refinance.models.entity import Entity
from refinance.models.tag import Tag

transactions_tags = Table(
    "transactions_tags",
    BaseModel.metadata,
    Column("transaction_id", ForeignKey("transactions.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


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

    amount: Mapped[DECIMAL] = mapped_column(DECIMAL(scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217
    confirmed: Mapped[bool] = mapped_column(default=False)

    tags: Mapped[list[Tag]] = relationship(secondary=transactions_tags)
