"""InvoiceItem model — one recipient line within a multi-recipient invoice"""

from typing import TYPE_CHECKING

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.transaction import Transaction


class InvoiceItem(BaseModel):
    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("ix_invoice_items_invoice_id", "invoice_id"),
        {"sqlite_autoincrement": True},
    )

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    invoice: Mapped["Invoice"] = relationship(
        "Invoice", back_populates="items", foreign_keys=[invoice_id]
    )

    # Pre-selected recipient (optional — can be left null and chosen at pay time)
    to_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True
    )
    to_entity: Mapped[Entity | None] = relationship(foreign_keys=[to_entity_id])

    # Tag constraint — at pay time the chosen entity must have this tag
    to_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id"), nullable=True)
    to_tag: Mapped[Tag | None] = relationship(foreign_keys=[to_tag_id])

    # List of {currency, amount} dicts — same format as Invoice.amounts
    amounts: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    # Back-ref to the transaction that settled this item
    transaction: Mapped["Transaction | None"] = relationship(
        "Transaction", back_populates="invoice_item", uselist=False
    )

    @property
    def transaction_id(self) -> int | None:
        if self.transaction is None:
            return None
        return self.transaction.id
