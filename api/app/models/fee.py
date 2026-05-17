"""Models for monthly fee policy and allocations."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.invoice import Invoice
from app.models.split import Split
from app.models.transaction import Transaction
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


class FeePolicyOverrideKind(enum.Enum):
    LEGACY = "legacy"


class FeeTargetType(enum.Enum):
    ENTITY = "entity"
    SPLIT = "split"


class FeePolicyOverride(BaseModel):
    __tablename__ = "fee_policy_overrides"

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"), nullable=False, unique=True
    )
    entity: Mapped[Entity] = relationship(foreign_keys=[entity_id])
    kind: Mapped[FeePolicyOverrideKind] = mapped_column(
        Enum(
            FeePolicyOverrideKind,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            name="fee_policy_override_kind",
        ),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class FeeAllocation(BaseModel):
    __tablename__ = "fee_allocations"
    __table_args__: ClassVar[tuple[object, ...]] = (
        UniqueConstraint(
            "invoice_id",
            "component_key",
            name="fee_allocations_invoice_component_key",
        ),
        {"sqlite_autoincrement": True},
    )

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    invoice: Mapped[Invoice] = relationship(foreign_keys=[invoice_id])
    component_key: Mapped[str] = mapped_column(String(64), nullable=False)
    amounts: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    extra_amounts: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)

    target_type: Mapped[FeeTargetType | None] = mapped_column(
        Enum(
            FeeTargetType,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            name="fee_target_type",
        ),
        nullable=True,
    )
    target_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True
    )
    target_entity: Mapped[Entity | None] = relationship(foreign_keys=[target_entity_id])
    target_split_id: Mapped[int | None] = mapped_column(
        ForeignKey("splits.id"), nullable=True
    )
    target_split: Mapped[Split | None] = relationship(foreign_keys=[target_split_id])
    selected_by_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True
    )
    selected_by_entity: Mapped[Entity | None] = relationship(
        foreign_keys=[selected_by_entity_id]
    )
    selected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_selected: Mapped[bool] = mapped_column(default=False, nullable=False)
    selection_deadline_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    allocation_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    allocation_transaction: Mapped[Transaction | None] = relationship(
        foreign_keys=[allocation_transaction_id]
    )
